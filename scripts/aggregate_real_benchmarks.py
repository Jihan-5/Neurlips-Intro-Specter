"""Aggregate real-benchmark results into publication-ready tables.

Reads `outputs/real/{dataset}__{model_slug}/*.jsonl`, builds the full
matrix, computes paired-bootstrap CIs and McNemar tests against the
target method (Intro-Specter), applies Holm-Bonferroni correction
across all cells per table, and emits CSVs for the paper.

Outputs (under `outputs/real/tables/`):

* `main_table.csv`           — per-cell success rate with Wilson CI for
                               each of the 7 methods
* `head_to_head.csv`         — IS-vs-each-baseline paired McNemar p,
                               Holm-corrected
* `intro_specter_wins.csv`   — significant IS wins
* `attribution.csv`          — top-1 / top-3 / MRR on fault-injected
                               examples (IS only)
* `token_cost.csv`           — mean / median / std tokens per method per
                               dataset
* `profile_violation.csv`    — profile-violation rate per method per
                               dataset
* `when_method_fails.csv`    — cells where any baseline strictly beats IS
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from intro_specter.metrics.stats import (
    holm_bonferroni,
    mcnemar,
    paired_bootstrap_ci,
    wilcoxon_signed_rank,
)


METHODS = [
    "direct", "react", "self_refine", "reflexion",
    "full_regen", "tot", "selfcheckgpt", "intro_specter_llm",
]


def load_results(output_root: Path = Path("outputs/real")) -> pd.DataFrame:
    """Load every JSONL row produced by the real-benchmark runs."""
    records: list[dict[str, Any]] = []
    for path in sorted(output_root.rglob("*.jsonl")):
        if "skipped_errors" in path.name:
            continue
        # Cell directory is the JSONL's parent. Name format: {dataset}__{model_slug}.
        cell_dir = path.parent.name
        if "__" in cell_dir:
            ds_part, _, model_slug = cell_dir.partition("__")
        else:
            ds_part = cell_dir
            model_slug = "unknown"
        for line in path.open():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            r["dataset"] = r.get("dataset") or ds_part
            r["model"] = model_slug
            records.append(r)
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    if {"task_id", "seed", "method"} <= set(df.columns):
        df = df.drop_duplicates(subset=["task_id", "seed", "method"], keep="last")
    return df


def main_table(df: pd.DataFrame, datasets: list[str], models: list[str]) -> pd.DataFrame:
    """Wide-format main results table."""
    rows: list[dict] = []
    for ds in datasets:
        for mdl in models:
            row = {"dataset": ds, "model": mdl}
            for m in METHODS:
                sub = df[(df["dataset"] == ds) & (df["model"] == mdl) & (df["method"] == m)]
                if sub.empty:
                    row[f"{m}_n"] = 0
                    row[f"{m}_success"] = None
                    continue
                row[f"{m}_n"] = len(sub)
                row[f"{m}_success"] = float(sub["success"].mean())
            rows.append(row)
    return pd.DataFrame(rows)


def head_to_head(df: pd.DataFrame, target: str = "intro_specter_llm") -> pd.DataFrame:
    """Pairwise McNemar IS-vs-each-baseline, Holm-corrected across all cells."""
    baselines = [m for m in METHODS if m != target]
    rows: list[dict] = []
    pvals: list[float] = []
    for ds in df["dataset"].unique():
        for mdl in df["model"].unique():
            tgt = df[(df["dataset"] == ds) & (df["model"] == mdl) & (df["method"] == target)]
            if tgt.empty:
                continue
            for b in baselines:
                bl = df[(df["dataset"] == ds) & (df["model"] == mdl) & (df["method"] == b)]
                if bl.empty:
                    continue
                # Align on (task_id, seed).
                merged = tgt.merge(bl, on=["task_id", "seed"], suffixes=("_t", "_b"))
                if len(merged) < 5:
                    continue
                t_succ = merged["success_t"].astype(bool).tolist()
                b_succ = merged["success_b"].astype(bool).tolist()
                ci = paired_bootstrap_ci(
                    [int(x) for x in b_succ], [int(x) for x in t_succ]
                )
                mc = mcnemar(b_succ, t_succ)
                rows.append({
                    "dataset": ds,
                    "model": mdl,
                    "baseline": b,
                    "is_success": float(merged["success_t"].mean()),
                    "bl_success": float(merged["success_b"].mean()),
                    "delta": ci.point,
                    "ci_low": ci.low,
                    "ci_high": ci.high,
                    "p_raw": mc.pvalue,
                    "n": len(merged),
                })
                pvals.append(mc.pvalue)
    out = pd.DataFrame(rows)
    if pvals:
        rejected, adjusted = holm_bonferroni(pvals, alpha=0.05)
        out["p_holm"] = adjusted
        out["holm_reject"] = rejected
    return out


def attribution_table(df: pd.DataFrame) -> pd.DataFrame:
    """Top-1 / top-3 / MRR on fault-injected examples (IS only)."""
    if "posterior" not in df.columns:
        return pd.DataFrame()
    is_df = df[df["method"] == "intro_specter_llm"].copy()
    if is_df.empty:
        return pd.DataFrame()

    rows: list[dict] = []
    for ds in is_df["dataset"].unique():
        for mdl in is_df["model"].unique():
            sub = is_df[(is_df["dataset"] == ds) & (is_df["model"] == mdl)]
            scored = []
            for _, r in sub.iterrows():
                # Gold fault id is in extra.meta_summary or in the task condition meta.
                # We re-fetch from the saved meta_summary if present.
                meta = r.get("extra", {}) or {}
                ms = meta.get("meta_summary", "{}")
                try:
                    ms = json.loads(ms) if isinstance(ms, str) else ms
                except Exception:
                    ms = {}
                gold = ms.get("gold_fault_node") if isinstance(ms, dict) else None
                if not gold:
                    continue
                posterior = r.get("posterior") or []
                if not posterior:
                    continue
                ranked = sorted(posterior, key=lambda p: -float(p.get("posterior", 0.0)))
                ids = [p.get("node_id") for p in ranked]
                if gold not in ids:
                    rank = len(ids) + 1
                else:
                    rank = ids.index(gold) + 1
                scored.append(rank)
            if not scored:
                continue
            scored_arr = np.array(scored)
            rows.append({
                "dataset": ds,
                "model": mdl,
                "n": int(len(scored_arr)),
                "top1": float((scored_arr == 1).mean()),
                "top3": float((scored_arr <= 3).mean()),
                "mrr": float((1.0 / scored_arr).mean()),
            })
    return pd.DataFrame(rows)


def token_cost_table(df: pd.DataFrame) -> pd.DataFrame:
    """Mean/median/std tokens per method per dataset."""
    df = df.copy()
    df["total_tokens"] = df.get("tokens_input", 0) + df.get("tokens_output", 0)
    return (
        df.groupby(["dataset", "method"])
          .agg(mean_tokens=("total_tokens", "mean"),
               median_tokens=("total_tokens", "median"),
               std_tokens=("total_tokens", "std"),
               n=("task_id", "count"))
          .reset_index()
    )


def profile_violation_table(df: pd.DataFrame) -> pd.DataFrame:
    """Per-method per-dataset profile-violation rate."""
    if "violation_rate" not in df.columns and "profile_violation" not in df.columns:
        return pd.DataFrame()
    col = "violation_rate" if "violation_rate" in df.columns else "profile_violation"
    return (
        df.groupby(["dataset", "method"])
          .agg(profile_violation_rate=(col, "mean"),
               n=("task_id", "count"))
          .reset_index()
    )


def when_fails(h2h: pd.DataFrame) -> pd.DataFrame:
    """Cells where IS strictly loses (delta < 0 with p_holm < 0.05)."""
    if h2h.empty or "p_holm" not in h2h.columns:
        return pd.DataFrame()
    losses = h2h[(h2h["delta"] < 0) & (h2h["p_holm"] < 0.05)].copy()
    losses["winner"] = losses["baseline"]
    return losses.sort_values(["dataset", "model", "baseline"])


def main() -> int:
    df = load_results()
    if df.empty:
        print("No results found in outputs/real/")
        return 0

    out_dir = Path("outputs/real/tables")
    out_dir.mkdir(parents=True, exist_ok=True)

    datasets = sorted(df["dataset"].unique())
    models = sorted(df["model"].unique())

    main_t = main_table(df, datasets, models)
    main_t.to_csv(out_dir / "main_table.csv", index=False)

    h2h = head_to_head(df)
    h2h.to_csv(out_dir / "head_to_head.csv", index=False)

    sig = h2h[h2h.get("holm_reject", pd.Series([False]*len(h2h))) & (h2h["delta"] > 0)]
    sig.to_csv(out_dir / "intro_specter_wins.csv", index=False)

    attr = attribution_table(df)
    attr.to_csv(out_dir / "attribution.csv", index=False)

    tok = token_cost_table(df)
    tok.to_csv(out_dir / "token_cost.csv", index=False)

    pvr = profile_violation_table(df)
    pvr.to_csv(out_dir / "profile_violation.csv", index=False)

    losses = when_fails(h2h)
    losses.to_csv(out_dir / "when_method_fails.csv", index=False)

    print(f"\nWrote 7 tables to {out_dir}/")
    print(f"\nDatasets: {datasets}")
    print(f"Models:   {models}")
    print(f"\nMain table rows: {len(main_t)}")
    print(f"Head-to-head rows: {len(h2h)}")
    if not h2h.empty and "holm_reject" in h2h.columns:
        print(f"\n=== IS-vs-baseline (Holm-significant @ 0.05) ===")
        for b in [m for m in METHODS if m != "intro_specter_llm"]:
            sub = h2h[h2h["baseline"] == b]
            if sub.empty:
                continue
            wins = sub[sub["holm_reject"] & (sub["delta"] > 0)]
            losses_b = sub[sub["holm_reject"] & (sub["delta"] < 0)]
            print(f"  vs {b:18s}: IS wins {len(wins):2d}, loses {len(losses_b):2d}, "
                  f"ties/NS {len(sub)-len(wins)-len(losses_b):2d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
