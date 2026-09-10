#!/usr/bin/env python3
"""Aggregates `outputs/rebuttal/experiment_d/real_multi_fault_n{2,3,4}.jsonl`
(written by `scripts/rebuttal_experiment_d_real.py`) into a consolidated
`outputs/rebuttal/experiment_d/fault_sweep_real_SUMMARY.md`, split into two
clearly separate sections:

  1. "Rebuttal-usable evidence" -- `reflexion` (real, unmodified) vs.
     `intro_specter` (real, unmodified `pipeline.py`). This is the only
     comparison usable as evidence about the current submission.
  2. "Future-work exploration" -- `intro_specter` vs. `intro_specter_fixed`
     (real, code-changed `pipeline_experimental_cumulative_repair.py`).
     Explicitly NOT for current-submission claims.

Uses `intro_specter.metrics.stats.mcnemar` (existing, unmodified) for the
paired significance test on `all_resolved`, same mechanism
`intro_specter/runner.py` already uses for its own paired comparisons.

Usage:
    python3 scripts/aggregate_experiment_d_real_sweep.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from intro_specter.metrics.stats import mcnemar

OUT_DIR = Path("outputs/rebuttal/experiment_d")
NS = [2, 3, 4]
ARMS = ["reflexion", "intro_specter", "intro_specter_fixed"]


def _load(n: int) -> list[dict[str, Any]]:
    path = OUT_DIR / f"real_multi_fault_n{n}.jsonl"
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


def _arm_stats(rows: list[dict[str, Any]], n_faults: int) -> dict[str, Any]:
    if not rows:
        return {"n": 0}
    n = len(rows)
    n_all_resolved = sum(1 for r in rows if r["all_resolved"])
    mean_frac_resolved = sum(r["n_resolved"] / r["num_faults"] for r in rows) / n
    # Per-fault-type marginal resolution rate.
    per_type: dict[str, list[bool]] = {}
    for r in rows:
        for k, v in r["per_fault_resolved"].items():
            per_type.setdefault(k, []).append(v)
    per_type_rate = {k: 100.0 * sum(v) / len(v) for k, v in per_type.items()}
    return {
        "n": n,
        "pct_all_resolved": 100.0 * n_all_resolved / n,
        "mean_frac_faults_resolved": mean_frac_resolved,
        "per_fault_type_pct_resolved": per_type_rate,
    }


def _paired(rows_a: list[dict[str, Any]], rows_b: list[dict[str, Any]]) -> dict[str, Any]:
    """Paired McNemar on `all_resolved`, aligned by (task_id, seed)."""
    by_key_a = {(r["task_id"], r["seed"]): r["all_resolved"] for r in rows_a}
    by_key_b = {(r["task_id"], r["seed"]): r["all_resolved"] for r in rows_b}
    keys = sorted(set(by_key_a) & set(by_key_b))
    if not keys:
        return {"n_paired": 0}
    a_vals = [by_key_a[k] for k in keys]
    b_vals = [by_key_b[k] for k in keys]
    b01 = sum(1 for a, b in zip(a_vals, b_vals) if not a and b)  # a loses, b wins
    b10 = sum(1 for a, b in zip(a_vals, b_vals) if a and not b)  # a wins, b loses
    res = mcnemar(a_vals, b_vals)
    return {
        "n_paired": len(keys),
        "a_only_resolved": b10,
        "b_only_resolved": b01,
        "both_resolved": sum(1 for a, b in zip(a_vals, b_vals) if a and b),
        "neither_resolved": sum(1 for a, b in zip(a_vals, b_vals) if not a and not b),
        "mcnemar_discordant": res.statistic,
        "mcnemar_p": res.pvalue,
    }


def main() -> None:
    all_data: dict[int, dict[str, list[dict[str, Any]]]] = {}
    for n in NS:
        rows = _load(n)
        by_arm: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}
        for r in rows:
            by_arm.setdefault(r["arm"], []).append(r)
        all_data[n] = by_arm

    lines: list[str] = []
    lines.append("# Experiment D (real): multi-fault sweep, N=2/3/4, twowiki_real x mistral-nemo-12b\n")
    lines.append(
        "Real LLM calls throughout (real `run_reflexion`, real `run_intro_specter`, real "
        "`run_intro_specter_cumulative_repair`). Every injected fault is genuinely baked into "
        "the prompt/context the agent is shown (no clean-render escape hatch, unlike the earlier "
        "synthetic multi-fault benchmark). See `scripts/rebuttal_experiment_d_real.py` module "
        "docstring for the full injection/scoring methodology, and "
        "`intro_specter/profiles/double_fault_injection.py` for the underlying N-fault injector.\n"
    )
    lines.append(
        "**N=5 was not run.** Constructing a 5th independent, mechanically-clean profile fault "
        "type (or requiring 4-way co-occurrence of the 4 available types: english / concise / "
        "bullets / preamble) was found impractical -- a direct simulation over 6000 profile draws "
        "found 0 examples where all 4 available types co-occur simultaneously (`inject_profile` "
        "only samples 3-5 constraints per example total). Forcing N=5 would have required either "
        "(a) an LLM-judge-based checker for a 5th subjective constraint type, which an earlier "
        "version of this experiment already found unreliable in smoke testing (see script "
        "docstring), or (b) inflating the profile size beyond what the unmodified "
        "`inject_profile` generator produces, which would no longer be testing the real "
        "benchmark. Scoped down to N=2/3/4 rather than force a compromised N=5.\n"
    )

    # ---- Section 1: rebuttal-usable ----
    lines.append("\n## Section 1 -- Rebuttal-usable evidence (real Reflexion vs. real, UNMODIFIED Intro-Specter)\n")
    lines.append(
        "This is the only section usable as evidence about the current submission. Both arms "
        "run the exact, unmodified `intro_specter/baselines/reflexion.py` and "
        "`intro_specter/pipeline.py` respectively.\n"
    )
    lines.append("| N | arm | n | %all_resolved | mean frac. faults resolved | per-fault-type %resolved |")
    lines.append("|---|---|---|---|---|---|")
    for n in NS:
        for arm in ["reflexion", "intro_specter"]:
            s = _arm_stats(all_data[n][arm], n)
            if s["n"] == 0:
                lines.append(f"| {n} | {arm} | 0 | -- | -- | -- |")
                continue
            per_type = ", ".join(f"{k}={v:.1f}%" for k, v in s["per_fault_type_pct_resolved"].items())
            lines.append(
                f"| {n} | {arm} | {s['n']} | {s['pct_all_resolved']:.1f}% | "
                f"{s['mean_frac_faults_resolved']:.3f} | {per_type} |"
            )
    lines.append("\n### Paired comparison (McNemar on `all_resolved`, same (task_id, seed))\n")
    lines.append("| N | n_paired | reflexion-only | intro_specter-only | both | neither | discordant | p |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for n in NS:
        p = _paired(all_data[n]["reflexion"], all_data[n]["intro_specter"])
        if p.get("n_paired", 0) == 0:
            lines.append(f"| {n} | 0 | -- | -- | -- | -- | -- | -- |")
            continue
        lines.append(
            f"| {n} | {p['n_paired']} | {p['a_only_resolved']} | {p['b_only_resolved']} | "
            f"{p['both_resolved']} | {p['neither_resolved']} | {p['mcnemar_discordant']:.0f} | "
            f"{p['mcnemar_p']:.4f} |"
        )

    # ---- Section 2: future-work only ----
    lines.append(
        "\n## Section 2 -- Future-work exploration (code-changed `intro_specter_fixed`, "
        "NOT for current-submission claims)\n"
    )
    lines.append(
        "`intro_specter_fixed` runs `intro_specter/pipeline_experimental_cumulative_repair.py`'s "
        "`run_intro_specter_cumulative_repair` -- a fully separate copy of the pipeline "
        "(never imports or modifies `pipeline.py`) with one targeted change: SPR rounds "
        "re-execute from the previous round's partially-repaired trajectory instead of the "
        "original faulty trajectory every round. **Do not cite results in this section as "
        "evidence about the submitted method.**\n"
    )
    lines.append("| N | arm | n | %all_resolved | mean frac. faults resolved |")
    lines.append("|---|---|---|---|---|")
    for n in NS:
        for arm in ["intro_specter", "intro_specter_fixed"]:
            s = _arm_stats(all_data[n][arm], n)
            if s["n"] == 0:
                lines.append(f"| {n} | {arm} | 0 | -- | -- |")
                continue
            lines.append(
                f"| {n} | {arm} | {s['n']} | {s['pct_all_resolved']:.1f}% | "
                f"{s['mean_frac_faults_resolved']:.3f} |"
            )
    lines.append("\n### Paired comparison (McNemar on `all_resolved`): intro_specter (unmodified) vs. intro_specter_fixed\n")
    lines.append("| N | n_paired | unmodified-only | fixed-only | both | neither | discordant | p |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for n in NS:
        p = _paired(all_data[n]["intro_specter"], all_data[n]["intro_specter_fixed"])
        if p.get("n_paired", 0) == 0:
            lines.append(f"| {n} | 0 | -- | -- | -- | -- | -- | -- |")
            continue
        lines.append(
            f"| {n} | {p['n_paired']} | {p['a_only_resolved']} | {p['b_only_resolved']} | "
            f"{p['both_resolved']} | {p['neither_resolved']} | {p['mcnemar_discordant']:.0f} | "
            f"{p['mcnemar_p']:.4f} |"
        )

    # ---- Token/cost accounting ----
    lines.append("\n## Token accounting\n")
    lines.append("| N | arm | total tokens (in+out) |")
    lines.append("|---|---|---|")
    for n in NS:
        for arm in ARMS:
            rows = all_data[n][arm]
            tot = sum(r["tokens_input"] + r["tokens_output"] for r in rows)
            lines.append(f"| {n} | {arm} | {tot} |")

    out_path = OUT_DIR / "fault_sweep_real_SUMMARY.md"
    out_path.write_text("\n".join(lines) + "\n")
    print(f"Wrote {out_path}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
