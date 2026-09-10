#!/usr/bin/env python3
"""Aggregates Condition 1 (single-fault synthetic baseline) from ALREADY-COMPLETED
runs under `outputs/real/{dataset}__{model}/` -- no new experiments, pure read +
arithmetic over existing JSONL result files.

Build-plan step 1 of the "5-dataset x 3-condition ablation matrix" rebuttal
campaign (see `~/.claude/plans/hidden-watching-zephyr.md`). Condition 1 already
fully exists for all 5 datasets x 4 models x 7 arms -- this script just puts it
in the same tabular format as the Condition 2/3 summaries being produced
alongside it.

Datasets and their on-disk (split, seeds) layout differ:
  - twowiki_real, musique_real, longmemeval_real: split "all", seed42 only,
    60 examples.
  - hotpotqa_real, travelplanner_real: split "test", seeds {42, 123, 456},
    12 examples per seed (~36 total) -- smaller AND uneven vs. the other three.
    Flagged explicitly in the output, not hidden.

Arms (7): direct, self_refine, reflexion, full_regen, react, selfcheckgpt,
intro_specter -- the last one is stored on disk as `intro_specter_llm.jsonl`
(confirmed by reading the files; NOT `intro_specter.jsonl`).

Success is read from the `success` boolean field in each JSONL row (confirmed
by inspecting sample rows across datasets).

This script is READ-ONLY with respect to `outputs/real/` -- it never writes,
moves, or modifies anything there. All output goes to `outputs/rebuttal/`.

Usage:
    python3 scripts/aggregate_condition1_baseline.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REAL_DIR = Path("outputs/real")
OUT_DIR = Path("outputs/rebuttal")

DATASETS = ["twowiki_real", "hotpotqa_real", "musique_real", "longmemeval_real", "travelplanner_real"]
MODELS = ["mistral-nemo-12b", "qwen-2.5-7b", "llama-3.1-8b", "llama-3.3-70b"]
ARMS = ["direct", "self_refine", "reflexion", "full_regen", "react", "selfcheckgpt", "intro_specter"]

# arm name -> on-disk filename stem
ARM_FILE_STEM = {a: ("intro_specter_llm" if a == "intro_specter" else a) for a in ARMS}

# dataset -> (split, seeds)
DATASET_LAYOUT = {
    "twowiki_real": ("all", [42]),
    "musique_real": ("all", [42]),
    "longmemeval_real": ("all", [42]),
    "hotpotqa_real": ("test", [42, 123, 456]),
    "travelplanner_real": ("test", [42, 123, 456]),
}

SMALL_SAMPLE_DATASETS = {"hotpotqa_real", "travelplanner_real"}


def _load_rows(dataset: str, model: str, arm: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Loads all rows for (dataset, model, arm) across whatever seeds this
    dataset uses. Returns (rows, source_file_paths)."""
    split, seeds = DATASET_LAYOUT[dataset]
    stem = ARM_FILE_STEM[arm]
    dir_path = REAL_DIR / f"{dataset}__{model}"
    rows: list[dict[str, Any]] = []
    sources: list[str] = []
    for seed in seeds:
        fpath = dir_path / f"{dataset}__{split}__seed{seed}__{stem}.jsonl"
        if not fpath.exists():
            continue
        sources.append(str(fpath))
        with fpath.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
    return rows, sources


def _success_rate(rows: list[dict[str, Any]]) -> float | None:
    if not rows:
        return None
    n_success = sum(1 for r in rows if r.get("success") is True)
    return 100.0 * n_success / len(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # cell_data[(dataset, model, arm)] = {"rate": float|None, "n": int, "sources": [...]}
    cell_data: dict[tuple[str, str, str], dict[str, Any]] = {}

    for dataset in DATASETS:
        for model in MODELS:
            for arm in ARMS:
                rows, sources = _load_rows(dataset, model, arm)
                rate = _success_rate(rows)
                cell_data[(dataset, model, arm)] = {
                    "rate": rate,
                    "n": len(rows),
                    "sources": sources,
                }

    # ---- JSONL output: one row per dataset x model x arm ----
    jsonl_path = OUT_DIR / "condition1_baseline.jsonl"
    with jsonl_path.open("w") as f:
        for dataset in DATASETS:
            for model in MODELS:
                for arm in ARMS:
                    d = cell_data[(dataset, model, arm)]
                    record = {
                        "dataset": dataset,
                        "model": model,
                        "arm": arm,
                        "success_rate_pct": d["rate"],
                        "n": d["n"],
                        "small_sample": dataset in SMALL_SAMPLE_DATASETS,
                        "source_files": d["sources"],
                    }
                    f.write(json.dumps(record) + "\n")

    # ---- Markdown output ----
    lines: list[str] = []
    lines.append("# Condition 1 (single-fault synthetic baseline) -- aggregated from existing `outputs/real/` runs\n")
    lines.append(
        "**Zero new experiments.** This is committed, already-completed data from the "
        "paper's own real-benchmark suite (`outputs/real/{dataset}__{model}/`), aggregated "
        "here into the same comparison format used for the Condition 2 (multi-fault "
        "synthetic) and Condition 3 (non-synthetic multi-fault) legs of the rebuttal "
        "campaign. Success is read directly from the `success` boolean field written by "
        "each run; no re-scoring or re-computation of correctness was performed.\n"
    )
    lines.append(
        "**Sample-size caveat (reported honestly, not hidden):** twowiki_real, "
        "musique_real, and longmemeval_real each have 60 examples x 1 seed (seed42). "
        "hotpotqa_real and travelplanner_real instead have 12 examples x 3 seeds "
        "(seed42/123/456) ≈ 36 total -- smaller AND structured differently (repeated "
        "sampling of a tiny pool vs. a single larger pool). Rates for these two datasets "
        "should be read with wider uncertainty than the other three.\n"
    )

    # Table 1: full (dataset, model) x arm matrix
    lines.append("## Table 1: full (dataset, model) x arm success-rate matrix (%)\n")
    header = "| Dataset | Model | n | " + " | ".join(ARMS) + " |"
    sep = "|---|---|---|" + "---|" * len(ARMS)
    lines.append(header)
    lines.append(sep)
    for dataset in DATASETS:
        flag = " *(small n)*" if dataset in SMALL_SAMPLE_DATASETS else ""
        for model in MODELS:
            n_ref = cell_data[(dataset, model, ARMS[0])]["n"]
            cells = []
            for arm in ARMS:
                d = cell_data[(dataset, model, arm)]
                cells.append(f"{d['rate']:.1f}" if d["rate"] is not None else "N/A")
            row = f"| {dataset}{flag} | {model} | {n_ref} | " + " | ".join(cells) + " |"
            lines.append(row)
    lines.append("")

    # Table 2: compact per-arm x model summary, averaged across datasets
    # Two variants: overall average, and average restricted to the 3 large-n datasets,
    # since mixing 60-example and 36-example datasets in one mean is itself a caveat.
    lines.append("## Table 2: compact summary -- arm x model, averaged across datasets (%)\n")
    lines.append(
        "Two averages shown per cell: **all 5 datasets** (unweighted mean of the 5 "
        "per-dataset rates) and **large-n only** (twowiki/musique/longmemeval, "
        "60 examples each) in parentheses, since the small hotpotqa/travelplanner cells "
        "carry more noise.\n"
    )
    large_n_datasets = [d for d in DATASETS if d not in SMALL_SAMPLE_DATASETS]
    header2 = "| Arm | " + " | ".join(MODELS) + " |"
    sep2 = "|---|" + "---|" * len(MODELS)
    lines.append(header2)
    lines.append(sep2)
    for arm in ARMS:
        cells = []
        for model in MODELS:
            all_rates = [
                cell_data[(dataset, model, arm)]["rate"]
                for dataset in DATASETS
                if cell_data[(dataset, model, arm)]["rate"] is not None
            ]
            large_rates = [
                cell_data[(dataset, model, arm)]["rate"]
                for dataset in large_n_datasets
                if cell_data[(dataset, model, arm)]["rate"] is not None
            ]
            all_avg = sum(all_rates) / len(all_rates) if all_rates else None
            large_avg = sum(large_rates) / len(large_rates) if large_rates else None
            if all_avg is None:
                cells.append("N/A")
            else:
                large_str = f"{large_avg:.1f}" if large_avg is not None else "N/A"
                cells.append(f"{all_avg:.1f} ({large_str})")
        cells_str = " | ".join(cells)
        lines.append(f"| {arm} | {cells_str} |")
    lines.append("")

    # Table 3: per-arm average across all datasets AND models (headline row)
    lines.append("## Table 3: per-arm grand average across all 5 datasets x 4 models (%)\n")
    lines.append("| Arm | Grand avg (all 5 datasets) | Grand avg (large-n 3 datasets only) |")
    lines.append("|---|---|---|")
    arm_ranking = []
    for arm in ARMS:
        all_rates = [
            cell_data[(dataset, model, arm)]["rate"]
            for dataset in DATASETS
            for model in MODELS
            if cell_data[(dataset, model, arm)]["rate"] is not None
        ]
        large_rates = [
            cell_data[(dataset, model, arm)]["rate"]
            for dataset in large_n_datasets
            for model in MODELS
            if cell_data[(dataset, model, arm)]["rate"] is not None
        ]
        all_avg = sum(all_rates) / len(all_rates) if all_rates else None
        large_avg = sum(large_rates) / len(large_rates) if large_rates else None
        arm_ranking.append((arm, all_avg))
        all_str = f"{all_avg:.2f}" if all_avg is not None else "N/A"
        large_str = f"{large_avg:.2f}" if large_avg is not None else "N/A"
        lines.append(f"| {arm} | {all_str} | {large_str} |")
    lines.append("")

    arm_ranking_sorted = sorted(
        [(a, r) for a, r in arm_ranking if r is not None], key=lambda x: -x[1]
    )
    lines.append("**Ranking (grand avg, all 5 datasets, high to low):** " +
                 ", ".join(f"{a} ({r:.2f}%)" for a, r in arm_ranking_sorted) + "\n")

    md_path = OUT_DIR / "condition1_baseline_SUMMARY.md"
    md_path.write_text("\n".join(lines) + "\n")

    print(f"Wrote {jsonl_path} ({len(DATASETS) * len(MODELS) * len(ARMS)} rows)")
    print(f"Wrote {md_path}")
    print()
    print("Grand average ranking (all 5 datasets):")
    for a, r in arm_ranking_sorted:
        print(f"  {a}: {r:.2f}%")


if __name__ == "__main__":
    main()
