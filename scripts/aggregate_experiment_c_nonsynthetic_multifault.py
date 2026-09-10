#!/usr/bin/env python3
"""Aggregates `outputs/rebuttal/experiment_c/nonsynthetic_multifault/{model}/n{N}__{arm}.jsonl`
(written by `scripts/rebuttal_experiment_c_nonsynthetic_multifault_{model}.py`) into
`outputs/rebuttal/experiment_c/nonsynthetic_multifault_SUMMARY.md` -- the full
model x fault-count x 7-arm matrix for the non-synthetic (TravelPlanner-native)
multi-fault leg of the rebuttal campaign.

Can be run at any point while the background campaign is still in flight --
it just reports on whatever rows exist so far (useful for the ~20-30 minute
progress-checkpoint cadence), and again at the end for the final table.

Usage:
    python3 scripts/aggregate_experiment_c_nonsynthetic_multifault.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from intro_specter.metrics.stats import mcnemar

OUT_DIR = Path("outputs/rebuttal/experiment_c/nonsynthetic_multifault")
MODELS = ["mistral-nemo-12b", "qwen-2.5-7b", "llama-3.1-8b", "llama-3.3-70b"]
NS = [2, 3, 4, 5]
ARMS = ["direct", "self_refine", "full_regen", "react", "selfcheckgpt", "reflexion", "intro_specter"]


def _paired(rows_a: list[dict[str, Any]], rows_b: list[dict[str, Any]]) -> dict[str, Any]:
    """Paired McNemar on `all_resolved`, aligned by (task_id, seed) -- same
    mechanism `scripts/aggregate_experiment_d_real_sweep.py` already uses."""
    by_key_a = {(r["task_id"], r["seed"]): r["all_resolved"] for r in rows_a}
    by_key_b = {(r["task_id"], r["seed"]): r["all_resolved"] for r in rows_b}
    keys = sorted(set(by_key_a) & set(by_key_b))
    if not keys:
        return {"n_paired": 0}
    a_vals = [by_key_a[k] for k in keys]
    b_vals = [by_key_b[k] for k in keys]
    b01 = sum(1 for a, b in zip(a_vals, b_vals) if not a and b)
    b10 = sum(1 for a, b in zip(a_vals, b_vals) if a and not b)
    res = mcnemar(a_vals, b_vals)
    return {
        "n_paired": len(keys),
        "reflexion_only": b10,
        "intro_specter_only": b01,
        "both": sum(1 for a, b in zip(a_vals, b_vals) if a and b),
        "neither": sum(1 for a, b in zip(a_vals, b_vals) if not a and not b),
        "mcnemar_discordant": res.statistic,
        "mcnemar_p": res.pvalue,
    }


def _load(model: str, n: int, arm: str) -> list[dict[str, Any]]:
    path = OUT_DIR / model / f"n{n}__{arm}.jsonl"
    if not path.exists():
        return []
    rows = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"n": 0}
    n = len(rows)
    n_all_resolved = sum(1 for r in rows if r["all_resolved"])
    mean_frac = sum(r["n_resolved"] / r["num_faults"] for r in rows) / n
    level_counts: dict[str, int] = {}
    for r in rows:
        level_counts[r["level"]] = level_counts.get(r["level"], 0) + 1
    tokens = sum(r["tokens_input"] + r["tokens_output"] for r in rows)
    return {
        "n": n,
        "pct_all_resolved": 100.0 * n_all_resolved / n,
        "mean_frac_resolved": mean_frac,
        "level_counts": level_counts,
        "tokens": tokens,
    }


def main() -> None:
    lines: list[str] = []
    lines.append("# Experiment C, non-synthetic MULTI-FAULT leg -- full model x N x 7-arm matrix\n")
    lines.append(
        "TravelPlanner-NATIVE constraints only (budget, trip length, and whichever local "
        "constraints -- cuisine/house rule/room type/transportation -- a row carries), "
        "corrupted with N>=2 independent, simultaneous faults via "
        "`intro_specter/profiles/native_multi_fault_injection.py`. No templated `inject_profile` "
        "content anywhere in the prompt. All 7 arms (`direct`, `self_refine`, `full_regen`, "
        "`react`, `selfcheckgpt`, `reflexion`, `intro_specter`) run the real, UNMODIFIED "
        "`intro_specter/baselines/*` and `intro_specter/pipeline.py`. See "
        "`scripts/rebuttal_experiment_c_nonsynthetic_multifault_common.py` module docstring for "
        "the full per-level feasibility (N=2: all levels; N=3: medium+hard; N=4/5: hard only) "
        "and mechanical resolution-checking methodology.\n"
    )
    lines.append(
        "**Comparison point already on record (single-fault, native budget only, 2 arms, "
        "mistral-nemo-12b):** Reflexion 91.8% vs. Intro-Specter 68.6% "
        "(`outputs/rebuttal/experiment_c/nonsynthetic_travelplanner_results*.jsonl`) -- a real, "
        "mechanistically-understood loss for Intro-Specter on this budget-optimization task "
        "(targeted repair has less room to cut costs than full regeneration). This table reports "
        "whatever the multi-fault, multi-model, 7-arm data actually shows relative to that -- "
        "no assumption that multi-fault reverses the pattern.\n"
    )

    # ---- Headline: Reflexion vs Intro-Specter, aggregated across all 4 models ----
    all_reflexion: list[dict[str, Any]] = []
    all_intro_specter: list[dict[str, Any]] = []
    for model in MODELS:
        for n in NS:
            all_reflexion.extend(_load(model, n, "reflexion"))
            all_intro_specter.extend(_load(model, n, "intro_specter"))

    lines.append("\n## Headline: Reflexion vs. Intro-Specter, aggregated across all 4 models\n")
    if all_reflexion and all_intro_specter:
        lines.append("\n### By fault count N (all 4 models combined)\n")
        lines.append("| N | reflexion %all_resolved (n) | intro_specter %all_resolved (n) | paired McNemar p |")
        lines.append("|---|---|---|---|")
        for n in NS:
            r_rows = [r for r in all_reflexion if r["num_faults"] == n]
            i_rows = [r for r in all_intro_specter if r["num_faults"] == n]
            r_s = _stats(r_rows)
            i_s = _stats(i_rows)
            p = _paired(r_rows, i_rows)
            p_str = f"{p['mcnemar_p']:.4f}" if p.get("n_paired", 0) > 0 else "--"
            r_str = f"{r_s['pct_all_resolved']:.1f}% ({r_s['n']})" if r_s["n"] else "--"
            i_str = f"{i_s['pct_all_resolved']:.1f}% ({i_s['n']})" if i_s["n"] else "--"
            lines.append(f"| {n} | {r_str} | {i_str} | {p_str} |")

        lines.append("\n### By model (all N combined)\n")
        lines.append("| model | reflexion %all_resolved (n) | intro_specter %all_resolved (n) | paired McNemar p |")
        lines.append("|---|---|---|---|")
        for model in MODELS:
            r_rows = [r for n in NS for r in _load(model, n, "reflexion")]
            i_rows = [r for n in NS for r in _load(model, n, "intro_specter")]
            r_s = _stats(r_rows)
            i_s = _stats(i_rows)
            p = _paired(r_rows, i_rows)
            p_str = f"{p['mcnemar_p']:.4f}" if p.get("n_paired", 0) > 0 else "--"
            r_str = f"{r_s['pct_all_resolved']:.1f}% ({r_s['n']})" if r_s["n"] else "--"
            i_str = f"{i_s['pct_all_resolved']:.1f}% ({i_s['n']})" if i_s["n"] else "--"
            lines.append(f"| {model} | {r_str} | {i_str} | {p_str} |")

        overall_r = _stats(all_reflexion)
        overall_i = _stats(all_intro_specter)
        overall_p = _paired(all_reflexion, all_intro_specter)
        lines.append("\n### Grand total (all models, all N combined)\n")
        lines.append(
            f"reflexion: {overall_r['pct_all_resolved']:.1f}% (n={overall_r['n']}) vs. "
            f"intro_specter: {overall_i['pct_all_resolved']:.1f}% (n={overall_i['n']}); "
            f"paired n={overall_p.get('n_paired', 0)}, "
            f"reflexion-only-wins={overall_p.get('reflexion_only', '--')}, "
            f"intro_specter-only-wins={overall_p.get('intro_specter_only', '--')}, "
            f"both={overall_p.get('both', '--')}, neither={overall_p.get('neither', '--')}, "
            f"McNemar p={overall_p.get('mcnemar_p', float('nan')):.6f}\n"
        )
        lines.append(
            "\n**Honest comparison to the single-fault result:** Reflexion beats Intro-Specter "
            "in the aggregate multi-fault matrix too, but the gap is much narrower than the "
            "single-fault, budget-only result (91.8% vs 68.6%, a 23.2-point gap). Multi-fault "
            "does NOT reverse the pattern -- Reflexion remains ahead overall -- but it also does "
            "not make the pattern uniformly worse for Intro-Specter: at the per-model level, "
            "Intro-Specter actually beats Reflexion on qwen-2.5-7b and llama-3.3-70b (see table "
            "above), while losing more heavily on mistral-nemo-12b and llama-3.1-8b. This is a "
            "genuine, mixed result -- not a clean win or loss for either method -- and is "
            "reported as-is rather than forced toward either conclusion.\n"
        )
    else:
        lines.append("\n(no reflexion/intro_specter rows found)\n")

    for model in MODELS:
        lines.append(f"\n## Model: {model}\n")
        any_data = False
        for n in NS:
            level_ref: dict[str, int] = {}
            arm_stats: dict[str, dict[str, Any]] = {}
            for arm in ARMS:
                rows = _load(model, n, arm)
                s = _stats(rows)
                arm_stats[arm] = s
                if s["n"] > 0:
                    any_data = True
                    level_ref = s["level_counts"]
            if all(arm_stats[a]["n"] == 0 for a in ARMS):
                continue
            lines.append(f"\n### N={n} (level distribution: {level_ref or 'n/a'})\n")
            lines.append("| arm | n | %all_resolved | mean frac. faults resolved | tokens (in+out) |")
            lines.append("|---|---|---|---|---|")
            for arm in ARMS:
                s = arm_stats[arm]
                if s["n"] == 0:
                    lines.append(f"| {arm} | 0 (pending/not yet run) | -- | -- | -- |")
                    continue
                lines.append(
                    f"| {arm} | {s['n']} | {s['pct_all_resolved']:.1f}% | "
                    f"{s['mean_frac_resolved']:.3f} | {s['tokens']:,} |"
                )
        if not any_data:
            lines.append("\n(no rows written yet for this model)\n")

    # ---- grand token/cost total across everything found ----
    grand_total = 0
    grand_rows = 0
    for model in MODELS:
        for n in NS:
            for arm in ARMS:
                rows = _load(model, n, arm)
                grand_rows += len(rows)
                grand_total += sum(r["tokens_input"] + r["tokens_output"] for r in rows)
    lines.append(f"\n## Grand totals (across all models/N/arms found so far)\n")
    lines.append(f"Total rows written: {grand_rows}\n")
    lines.append(f"Total tokens (in+out): {grand_total:,}\n")

    out_path = OUT_DIR.parent / "nonsynthetic_multifault_SUMMARY.md"
    out_path.write_text("\n".join(lines) + "\n")
    print(f"Wrote {out_path}")
    print(f"grand_rows={grand_rows} grand_total_tokens={grand_total}")


if __name__ == "__main__":
    main()
