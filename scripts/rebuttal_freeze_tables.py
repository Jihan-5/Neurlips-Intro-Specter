#!/usr/bin/env python3
"""Freeze-time table snapshot for the rebuttal (additive-only).

Re-aggregates every table cited in rebuttal/responses/*.md directly from the
raw campaign JSONL files and writes them to rebuttal/tables/ with a provenance
header (source glob + row counts + timestamp arg). Run once at the declared
freeze (Jul 27 12:00 EDT):

    python3 scripts/rebuttal_freeze_tables.py --stamp "2026-07-27T12:00EDT"

Every number in the response drafts must trace to one of these files; anything
that doesn't gets cut at audit, not softened.
"""

from __future__ import annotations

import argparse
import json
import glob as globmod
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "rebuttal" / "tables"

ARMS = ["direct", "self_refine", "reflexion", "full_regen", "react", "selfcheckgpt", "intro_specter"]

MULTIFAULT = {
    "TwoWiki": "outputs/rebuttal/experiment_d/full_matrix",
    "HotpotQA": "outputs/rebuttal/experiment_d/full_matrix_hotpotqa",
    "MuSiQue": "outputs/rebuttal/experiment_d/full_matrix_musique",
    "LongMemEval": "outputs/rebuttal/experiment_d/full_matrix_longmemeval",
    "TravelPlanner-synth": "outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic",
}
NONSYNTH = {
    "TravelPlanner-real": "outputs/rebuttal/experiment_c/nonsynthetic_multifault",
    "Recipes": "outputs/rebuttal/experiment_recipes",
    "Amazon": "outputs/rebuttal/experiment_amazon",
}
EXCLUDE_MODELS = {"qwen-2.5-72b"}  # post-hoc 5th model, incomplete; excluded per plan


# TwoWiki x Mistral's intro_specter/reflexion rows live in the ORIGINAL Experiment D
# sweep files (legacy layout, confirmed "twowiki_real x mistral-nemo-12b" in
# fault_sweep_real_SUMMARY.md; task_ids real_2wiki_*; full 180 rows/arm at n=2-4,
# 120/arm at n=5-6 hop tiers) rather than full_matrix/mistral-nemo-12b/.
# `intro_specter_fixed` is the future-work-only arm and is always excluded.
_TWOWIKI_LEGACY = [
    "outputs/rebuttal/experiment_d/real_multi_fault_n2.jsonl",
    "outputs/rebuttal/experiment_d/real_multi_fault_n3.jsonl",
    "outputs/rebuttal/experiment_d/real_multi_fault_n4.jsonl",
    "outputs/rebuttal/experiment_d/real_multi_fault_n5.jsonl",
]


def _iter_rows(base: str):
    for f in globmod.glob(f"{REPO}/{base}/**/*.jsonl", recursive=True):
        model = Path(f).parent.name
        if model in EXCLUDE_MODELS:
            continue
        with open(f) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line), model
                except json.JSONDecodeError:
                    continue
    if base == MULTIFAULT["TwoWiki"]:
        for rel in _TWOWIKI_LEGACY:
            try:
                fh = open(REPO / rel)
            except FileNotFoundError:
                continue
            with fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if d.get("arm") in ("intro_specter", "reflexion"):
                        yield d, "mistral-nemo-12b"


def success_tables(stamp: str) -> None:
    for group_name, datasets in (("multifault_synth", MULTIFAULT), ("nonsynth", NONSYNTH)):
        lines = [f"# {group_name} success rates — frozen {stamp}", ""]
        for ds, base in datasets.items():
            stats = defaultdict(lambda: [0, 0])
            by_n = defaultdict(lambda: defaultdict(lambda: [0, 0]))
            by_model = defaultdict(lambda: defaultdict(lambda: [0, 0]))
            for d, model in _iter_rows(base):
                arm, ar, nf = d.get("arm"), d.get("all_resolved"), d.get("num_faults")
                if arm is None or ar is None:
                    continue
                stats[arm][1] += 1
                by_model[model][arm][1] += 1
                if nf is not None:
                    by_n[nf][arm][1] += 1
                if ar:
                    stats[arm][0] += 1
                    by_model[model][arm][0] += 1
                    if nf is not None:
                        by_n[nf][arm][0] += 1
            lines.append(f"## {ds}  (source: {base}/**/*.jsonl)")
            lines.append("| arm | success | n |")
            lines.append("|---|---|---|")
            for arm in ARMS:
                s, n = stats[arm]
                if n:
                    lines.append(f"| {arm} | {100*s/n:.1f}% | {n} |")
            lines.append("")
            lines.append("| num_faults | " + " | ".join(ARMS) + " |")
            lines.append("|" + "---|" * (len(ARMS) + 1))
            for nf in sorted(by_n):
                row = [str(nf)]
                for arm in ARMS:
                    s, n = by_n[nf][arm]
                    row.append(f"{100*s/n:.1f}% ({n})" if n else "n/a")
                lines.append("| " + " | ".join(row) + " |")
            lines.append("")
            lines.append("| model | intro_specter | reflexion |")
            lines.append("|---|---|---|")
            for model in sorted(by_model):
                a = by_model[model]["intro_specter"]
                b = by_model[model]["reflexion"]
                astr = f"{100*a[0]/a[1]:.1f}% ({a[1]})" if a[1] else "n/a"
                bstr = f"{100*b[0]/b[1]:.1f}% ({b[1]})" if b[1] else "n/a"
                lines.append(f"| {model} | {astr} | {bstr} |")
            lines.append("")
        (OUT / f"{group_name}_success.md").write_text("\n".join(lines))
        print(f"wrote {OUT}/{group_name}_success.md")


def cost_table(stamp: str) -> None:
    lines = [f"# Token cost per example (all arms) — frozen {stamp}", ""]
    lines.append("| dataset | " + " | ".join(ARMS) + " | Rfx/IS ratio |")
    lines.append("|" + "---|" * (len(ARMS) + 2))
    for ds, base in {**MULTIFAULT, **NONSYNTH}.items():
        tok = defaultdict(lambda: [0, 0, 0])
        for d, _model in _iter_rows(base):
            arm = d.get("arm")
            if arm is None:
                continue
            tok[arm][0] += 1
            tok[arm][1] += d.get("tokens_input", 0) or 0
            tok[arm][2] += d.get("tokens_output", 0) or 0
        row = [ds]
        for arm in ARMS:
            n, ti, to = tok[arm]
            row.append(f"{(ti+to)/n:.0f}" if n else "n/a")
        is_n, is_ti, is_to = tok["intro_specter"]
        rf_n, rf_ti, rf_to = tok["reflexion"]
        ratio = ((rf_ti + rf_to) / rf_n) / ((is_ti + is_to) / is_n) if is_n and rf_n else 0
        row.append(f"{ratio:.2f}x")
        lines.append("| " + " | ".join(row) + " |")
    (OUT / "cost.md").write_text("\n".join(lines))
    print(f"wrote {OUT}/cost.md")


def iter_vrp_table(stamp: str) -> None:
    lines = [f"# Iter-VRP 4-cell ablation — frozen {stamp}", ""]
    lines.append("| cell | arm | success | n | mean rounds |")
    lines.append("|---|---|---|---|---|")
    for cell_dir in sorted(globmod.glob(f"{REPO}/outputs/rebuttal/experiment_b/*/")):
        cell = Path(cell_dir).name
        for f in sorted(globmod.glob(f"{cell_dir}/*.jsonl")):
            arm = Path(f).stem
            total = succ = 0
            rounds: list[int] = []
            with open(f) as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    d = json.loads(line)
                    total += 1
                    if d.get("success"):
                        succ += 1
                    if "rounds_used" in d:
                        rounds.append(d["rounds_used"])
            if total:
                mr = f"{sum(rounds)/len(rounds):.2f}" if rounds else "n/a"
                lines.append(f"| {cell} | {arm} | {100*succ/total:.1f}% | {total} | {mr} |")
    (OUT / "iter_vrp.md").write_text("\n".join(lines))
    print(f"wrote {OUT}/iter_vrp.md")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stamp", required=True, help='freeze timestamp label, e.g. "2026-07-27T12:00EDT"')
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    success_tables(args.stamp)
    cost_table(args.stamp)
    iter_vrp_table(args.stamp)
    print("freeze snapshot complete")
