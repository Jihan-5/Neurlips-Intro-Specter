#!/usr/bin/env python3
"""Aggregates outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic/
into a summary table (rows=arm, cols=model, one table per N) plus an overall
markdown report, mirroring the aggregation style already used for the
sibling twowiki/musique/longmemeval full-matrix experiments tonight.

Additive-only: reads existing JSONL, writes one new summary file.

Usage:
    python3 scripts/aggregate_experiment_d_travelplanner_synthetic.py
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path("outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic")
MODELS = ["mistral-nemo-12b", "qwen-2.5-7b", "llama-3.1-8b", "llama-3.3-70b"]
ARMS = ["direct", "self_refine", "full_regen", "react", "selfcheckgpt", "reflexion", "intro_specter"]
NUMS = [2, 3, 4]


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main() -> None:
    # table[num][arm][model] = (n_rows, n_all_resolved, sum_n_resolved, sum_num_faults)
    table: dict[int, dict[str, dict[str, dict]]] = {
        n: {a: {} for a in ARMS} for n in NUMS
    }
    for model in MODELS:
        for n in NUMS:
            for arm in ARMS:
                path = ROOT / model / f"n{n}__{arm}.jsonl"
                rows = load(path)
                n_rows = len(rows)
                n_all = sum(1 for r in rows if r.get("all_resolved"))
                sum_resolved = sum(r.get("n_resolved", 0) for r in rows)
                sum_total = sum(r.get("num_faults", n) for r in rows)
                table[n][arm][model] = {
                    "n_rows": n_rows,
                    "all_resolved_rate": (n_all / n_rows) if n_rows else None,
                    "per_fault_resolved_rate": (sum_resolved / sum_total) if sum_total else None,
                }

    lines = []
    lines.append("# TravelPlanner-real SYNTHETIC multi-fault matrix -- aggregated results\n")
    lines.append(
        "Condition 2 (synthetic multi-fault, templated profile-bank layer + "
        "`double_fault_injection.py`'s `build_multi_fault`, N=2-4). N=5 confirmed "
        "infeasible: direct 20,000-row simulation found 0/20000 examples with all "
        "4 mechanically-clean profile-fault types co-occurring (TravelPlanner has "
        "no multi-hop/multi-fact native structure to draw a hop-fault path from, "
        "unlike twowiki_real/musique_real).\n"
    )
    for n in NUMS:
        lines.append(f"\n## N={n} faults (1 context + {n - 1} profile)\n")
        lines.append("| arm | " + " | ".join(MODELS) + " |")
        lines.append("|---|" + "---|" * len(MODELS))
        for arm in ARMS:
            cells = []
            for model in MODELS:
                d = table[n][arm][model]
                if d["n_rows"] == 0:
                    cells.append("n/a (0 rows)")
                else:
                    ar = d["all_resolved_rate"]
                    pf = d["per_fault_resolved_rate"]
                    cells.append(f"all={ar:.1%} / per-fault={pf:.1%} (n={d['n_rows']})")
            lines.append(f"| {arm} | " + " | ".join(cells) + " |")

    out_path = Path("outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic_SUMMARY.md")
    out_path.write_text("\n".join(lines) + "\n")
    print(f"Wrote {out_path}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
