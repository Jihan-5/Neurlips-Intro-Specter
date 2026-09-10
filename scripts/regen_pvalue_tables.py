"""Regenerate the appendix per-cell p-value tables (Tables 11-14 in paper_final.tex).

Why this script exists:
The paper's main per-benchmark tables (Tables 4-7) report Intro-Specter numbers
from the cascade-with-SPR runs (now relabelled as SPR — `outputs/real/cascade/...`).
The appendix p-value tables, by contrast, were last regenerated against the *base*
non-SPR Intro-Specter runs (`outputs/real/.../intro_specter_llm.jsonl`). The two
sources of truth disagree: e.g., LongMem x Qwen 7B reports IS=76.7 in Table 5 but
the appendix CIs/p-values were computed against IS=71.7. To a careful reader the
result is mathematically impossible: equal marginals (76.7 vs 76.7) cannot give
McNemar p < 1.0.

This script overlays the cascade IS results on top of the base cell's seven
baselines, then re-runs paired-bootstrap CIs and exact McNemar tests. The output
is a per-cell row matching the format used by the appendix tables.

Reads:   outputs/real/<dataset>__<model>/*.jsonl                (base baselines)
         outputs/real/cascade/<dataset>__<model>/*.jsonl        (SPR overlay if present)
Writes:  outputs/real/tables/regenerated_pvalues_<benchmark>.csv
         outputs/real/tables/regenerated_pvalues_summary.txt
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterable

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from intro_specter.metrics.stats import mcnemar, paired_bootstrap_ci  # noqa: E402


# (paper benchmark name, dataset string in JSONL `dataset` field, output dir prefix)
BENCHMARKS = [
    ("truthfulqa", "truthfulqa_real"),
    ("twowiki",    "twowiki_real"),
    ("longmem",    "longmemeval_real"),
    ("musique",    "musique_real"),
]

# Paper-table model order (matches Tables 4-7).
MODELS = [
    ("Llama 8B",    "llama-3.1-8b"),
    ("Llama 70B",   "llama-3.3-70b"),
    ("Mistral 12B", "mistral-nemo-12b"),
    ("Qwen 7B",     "qwen-2.5-7b"),
]

BASELINES = ["direct", "self_refine", "reflexion", "full_regen", "react", "selfcheckgpt", "tot"]


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def cell_dataframe(base_dir: Path, cascade_dir: Path | None) -> pd.DataFrame:
    """Concatenate every method JSONL in the cell, with SPR (cascade) overriding base IS."""
    rows: list[dict] = []
    for path in sorted(base_dir.glob("*__intro_specter_llm.jsonl")) + \
                sorted(base_dir.glob(f"*__seed*__{m}.jsonl") for m in []) + \
                sorted(base_dir.glob("*__seed*__*.jsonl")):
        # The double-iteration above is a no-op; canonical loop:
        pass
    # Canonical loop: every per-method JSONL in the base dir.
    for path in sorted(base_dir.glob("*.jsonl")):
        if path.name.endswith("__skipped_errors.jsonl"):
            continue
        rows.extend(load_jsonl(path))
    # Override IS rows with cascade JSONLs if available.
    if cascade_dir is not None and cascade_dir.exists():
        cascade_rows: list[dict] = []
        for path in sorted(cascade_dir.glob("*__intro_specter_llm.jsonl")):
            cascade_rows.extend(load_jsonl(path))
        if cascade_rows:
            # Drop base IS rows, replace with cascade.
            rows = [r for r in rows if r.get("method") != "intro_specter_llm"]
            rows.extend(cascade_rows)
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def per_cell_paired(df: pd.DataFrame, baseline: str) -> tuple[float, float, float, float, int] | None:
    """Return (delta_pp, ci_low_pp, ci_high_pp, p_mcnemar, n_paired) for IS-vs-baseline."""
    if df.empty:
        return None
    is_df = df[df["method"] == "intro_specter_llm"]
    bl_df = df[df["method"] == baseline]
    if is_df.empty or bl_df.empty:
        return None
    merged = is_df.merge(
        bl_df[["task_id", "seed", "success"]],
        on=["task_id", "seed"],
        suffixes=("_is", "_bl"),
    )
    if len(merged) < 5:
        return None
    is_succ = merged["success_is"].astype(bool).tolist()
    bl_succ = merged["success_bl"].astype(bool).tolist()
    ci = paired_bootstrap_ci(
        [int(x) for x in bl_succ], [int(x) for x in is_succ]
    )
    mc = mcnemar(bl_succ, is_succ)
    return (
        100.0 * ci.point,
        100.0 * ci.low,
        100.0 * ci.high,
        float(mc.pvalue),
        int(len(merged)),
    )


def fmt_cell(val: tuple[float, float, float, float, int] | None) -> str:
    if val is None:
        return "---"
    delta, lo, hi, p, _n = val
    sig = r"\checkmark" if p < 0.05 else ""
    p_str = "$<\!.001$" if p < 0.001 else f"${p:.3f}$"
    sign = "+" if delta >= 0 else "$-$"
    delta_abs = abs(delta)
    lo_str = ("+" if lo >= 0 else "$-$") + f"{abs(lo):.0f}"
    hi_str = ("+" if hi >= 0 else "$-$") + f"{abs(hi):.0f}"
    return f"{p_str}{sig}\\,[{lo_str},{hi_str}]"


def emit_latex_table(per_benchmark_rows: dict[str, list[dict]], outpath: Path) -> None:
    """Write a single .tex fragment with one tabular per benchmark, matching paper format."""
    lines: list[str] = []
    bench_caption = {
        "truthfulqa": "TruthfulQA",
        "twowiki":    "2WikiMultiHopQA",
        "longmem":    "LongMemEval",
        "musique":    "MuSiQue",
    }
    bench_label = {
        "truthfulqa": "tab:pvalues-tqa",
        "twowiki":    "tab:pvalues-2wiki",
        "longmem":    "tab:pvalues-lme",
        "musique":    "tab:pvalues-musique",
    }
    for bench, rows in per_benchmark_rows.items():
        lines.append(r"\begin{table}[h]\centering\scriptsize")
        lines.append(
            r"\caption{Profile-injected " + bench_caption[bench]
            + r". Cells: $p$\,[CI\textsubscript{low}, CI\textsubscript{high}]. CIs in pp;"
            r" 10{,}000 paired-bootstrap resamples. $\checkmark$ = $p < 0.05$ (uncorrected)."
            r" Each row is regenerated from the same per-cell JSONLs that produce the headline"
            r" success rates in the corresponding main-text table; \method numbers reflect the"
            r" full pipeline (single-round attribution + SPR).}"
        )
        lines.append(r"\label{" + bench_label[bench] + r"}\setlength{\tabcolsep}{2pt}")
        cols = "l" + "c" * len(BASELINES)
        lines.append(r"\begin{tabular}{" + cols + r"}\toprule")
        header = " & ".join(["", *(b.replace("_", " ").title()
                                   .replace("Self Refine", "SR")
                                   .replace("Reflexion", "Rfx")
                                   .replace("Full Regen", "FR")
                                   .replace("React", "ReAct")
                                   .replace("Selfcheckgpt", "SChk")
                                   .replace("Tot", "ToT")
                                   for b in BASELINES)])
        lines.append(header + r" \\\midrule")
        for r in rows:
            lines.append(r["latex"])
        lines.append(r"\bottomrule\end{tabular}\end{table}")
        lines.append("")
    outpath.write_text("\n".join(lines))


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    out_dir = repo / "outputs" / "real" / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)

    per_benchmark_rows: dict[str, list[dict]] = {b: [] for b, _ in BENCHMARKS}
    summary_lines: list[str] = []

    for bench_key, ds_slug in BENCHMARKS:
        for model_label, model_slug in MODELS:
            base_dir = repo / "outputs" / "real" / f"{ds_slug}__{model_slug}"
            cascade_dir = repo / "outputs" / "real" / "cascade" / f"{ds_slug}__{model_slug}"
            df = cell_dataframe(base_dir, cascade_dir if cascade_dir.exists() else None)
            if df.empty:
                summary_lines.append(f"{bench_key:11s} {model_label:12s}: no data")
                continue
            cells = []
            cell_strs = []
            for b in BASELINES:
                tup = per_cell_paired(df, b)
                cells.append(tup)
                cell_strs.append(fmt_cell(tup))
            n_max = max((c[4] for c in cells if c is not None), default=0)
            is_rate = float(df[df["method"] == "intro_specter_llm"]["success"].mean()) * 100
            summary_lines.append(
                f"{bench_key:11s} {model_label:12s}: IS={is_rate:5.1f}%, n_max={n_max}, "
                f"used cascade={cascade_dir.exists()}"
            )
            latex_row = f"{model_label}    & " + " & ".join(cell_strs) + r" \\"
            per_benchmark_rows[bench_key].append({
                "model": model_label,
                "is_rate": is_rate,
                "cells": cells,
                "latex": latex_row,
            })

    # Write CSV and LaTeX outputs.
    csv_rows: list[dict] = []
    for bench, rows in per_benchmark_rows.items():
        for r in rows:
            for b, c in zip(BASELINES, r["cells"]):
                if c is None:
                    continue
                d, lo, hi, p, n = c
                csv_rows.append({
                    "benchmark": bench,
                    "model":     r["model"],
                    "baseline":  b,
                    "is_rate":   r["is_rate"],
                    "delta_pp":  d,
                    "ci_low_pp": lo,
                    "ci_high_pp":hi,
                    "p_mcnemar": p,
                    "n_paired":  n,
                })
    if csv_rows:
        pd.DataFrame(csv_rows).to_csv(out_dir / "regenerated_pvalues.csv", index=False)
    emit_latex_table(per_benchmark_rows, out_dir / "regenerated_pvalues.tex")
    (out_dir / "regenerated_pvalues_summary.txt").write_text("\n".join(summary_lines))

    print("\n".join(summary_lines))
    print(f"\nWrote: {out_dir / 'regenerated_pvalues.csv'}")
    print(f"Wrote: {out_dir / 'regenerated_pvalues.tex'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
