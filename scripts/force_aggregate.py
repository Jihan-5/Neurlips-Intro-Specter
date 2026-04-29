"""Recover summary.json files from partial JSONLs after crashed runs.

When a run() invocation dies mid-way (OpenRouter rate-limit cap, Together
truncation, etc.), the per-method JSONLs are still on disk but the
`{label}__summary.json` is never written, so aggregate_tier_a.py skips
the directory.

This script reads every JSONL in every tier_*/ subdir, deduplicates
on (task_id, seed, method), and synthesises a summary.json using the
same logic as runner.run()'s aggregate block. Idempotent: safe to
re-run after the fact.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from intro_specter.metrics.repair import degradation_rate, delta_success_rate
from intro_specter.metrics.stats import (
    holm_bonferroni,
    mcnemar,
    paired_bootstrap_ci,
    wilcoxon_signed_rank,
)


def _scan(d: Path) -> pd.DataFrame | None:
    rows: list[dict] = []
    for path in sorted(d.glob("*.jsonl")):
        if path.name.endswith("__skipped_errors.jsonl") or "__results_" in path.name:
            continue
        for line in path.open():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if not rows:
        return None
    df = pd.DataFrame(rows)
    if {"task_id", "seed", "method"} <= set(df.columns):
        df = df.drop_duplicates(subset=["task_id", "seed", "method"], keep="last")
    return df


def _aggregate(d: Path) -> dict | None:
    df = _scan(d)
    if df is None or df.empty:
        return None
    label = d.name
    methods_present = sorted(df["method"].unique())
    by_method = {
        m: df[df["method"] == m].sort_values(["task_id", "seed"]).reset_index(drop=True)
        for m in methods_present
    }
    direct_df = by_method.get("direct")
    pvals_for_holm: dict[tuple[str, str], float] = {}
    method_summaries: dict[str, dict] = {}

    for m, sub in by_method.items():
        s = {
            "n": int(len(sub)),
            "success_rate": float(sub["success"].mean()),
            "violation_rate": float(sub.get("violation_rate", pd.Series([0]*len(sub))).mean()),
            "tokens_input_mean": float(sub["tokens_input"].mean()) if "tokens_input" in sub else 0.0,
            "tokens_output_mean": float(sub["tokens_output"].mean()) if "tokens_output" in sub else 0.0,
            "latency_ms_mean": float(sub.get("latency_ms", pd.Series([0]*len(sub))).mean()),
        }
        if direct_df is None or m == "direct":
            method_summaries[m] = s
            continue
        merged = sub.merge(
            direct_df[["task_id", "seed", "success", "tokens_input", "tokens_output", "violation_rate"]],
            on=["task_id", "seed"], suffixes=("", "_direct"),
        )
        if merged.empty:
            method_summaries[m] = s
            continue
        ci_succ = paired_bootstrap_ci(
            merged["success_direct"].astype(int).tolist(),
            merged["success"].astype(int).tolist(),
        )
        mc = mcnemar(
            merged["success_direct"].astype(bool).tolist(),
            merged["success"].astype(bool).tolist(),
        )
        ci_tok = paired_bootstrap_ci(
            (merged["tokens_input_direct"] + merged["tokens_output_direct"]).astype(float).tolist(),
            (merged["tokens_input"] + merged["tokens_output"]).astype(float).tolist(),
        )
        wx = wilcoxon_signed_rank(
            (merged["tokens_input_direct"] + merged["tokens_output_direct"]).astype(float).tolist(),
            (merged["tokens_input"] + merged["tokens_output"]).astype(float).tolist(),
        )
        s.update({
            "delta_success": ci_succ.point,
            "delta_success_ci_low": ci_succ.low,
            "delta_success_ci_high": ci_succ.high,
            "mcnemar_success_p": mc.pvalue,
            "delta_tokens": ci_tok.point,
            "wilcoxon_tokens_p": wx.pvalue,
            "degradation_rate": degradation_rate(
                merged["success_direct"].astype(bool).tolist(),
                merged["success"].astype(bool).tolist(),
            ),
        })
        pvals_for_holm[(m, "success")] = mc.pvalue
        pvals_for_holm[(m, "tokens")] = wx.pvalue
        method_summaries[m] = s

    if pvals_for_holm:
        keys = list(pvals_for_holm.keys())
        ps = [pvals_for_holm[k] for k in keys]
        rejected, adjusted = holm_bonferroni(ps, alpha=0.05)
        for (m, metric), adj_p, rej in zip(keys, adjusted, rejected, strict=True):
            method_summaries[m][f"holm_{metric}_p_adj"] = adj_p
            method_summaries[m][f"holm_{metric}_reject"] = rej

    summary = {
        "benchmark": label,
        "n_examples": int(df["task_id"].nunique()),
        "n_total_rows": int(len(df)),
        "methods": method_summaries,
    }
    df.to_csv(d / f"{label}__results_long.csv", index=False)
    summary_path = d / f"{label}__summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str))
    return summary


def main() -> int:
    n_total = 0
    n_synthesised = 0
    for parent in [Path("outputs/tier_a"), Path("outputs/tier_b"), Path("outputs/synthetic_single_fault"), Path("outputs/synthetic_multi_valid")]:
        if not parent.exists():
            continue
        for d in sorted(parent.iterdir()):
            if not d.is_dir() or d.name == "calibration" or d.name == "figures":
                continue
            n_total += 1
            existing = list(d.glob("*__summary.json"))
            if existing:
                # Already aggregated; refresh from JSONLs in case of mid-flight changes.
                pass
            s = _aggregate(d)
            if s is not None:
                n_synthesised += 1
                methods = list(s.get("methods", {}).keys())
                rows = s.get("n_total_rows", 0)
                print(f"  [{rows:>4d} rows]  {d.name}: {len(methods)} methods")
    print(f"\nProduced {n_synthesised} / {n_total} dir summaries.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
