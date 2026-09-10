#!/usr/bin/env python3
"""Experiment D follow-up: Reflexion-equivalent baseline vs. Intro-Specter on
the SAME 60 multi-fault graphs (rebuttal campaign, reviewer LDZz).

`scripts/rebuttal_experiment_d.py` ran Intro-Specter alone against 60
multi-fault synthetic graphs (`intro_specter/benchmarks/synthetic_dag_multi_fault.py`,
seed=0) and found 0% "both faults fully resolved within the 1 + T_spr=2 = 3
round budget" (by construction: SPR rebuilds from the ORIGINAL trajectory each
round rather than accumulating repairs, so two structurally disjoint faults
can never both clear). That script had NO baseline comparison. This script
adds one, using ONLY mechanisms that already exist, unmodified, in this
repository -- no new baseline logic is invented here.

INVESTIGATION (see module docstring detail below) found there are TWO
candidate "Reflexion-equivalent, symbolic, $0-cost" mechanisms already wired
into the codebase for the synthetic environment, and both are degenerate in
instructive, opposite ways. We run BOTH, unmodified, for full honesty:

(A) ``reflexion`` baseline as literally invoked by the existing Tier-C
    synthetic configs (`configs/synthetic_single_fault_test.yaml` etc.):
    `run_reflexion(..., provider=None, model="")`. Reading
    `intro_specter/baselines/reflexion.py::run_reflexion`, when no LLM
    `provider` is supplied the function does **no retry at all** -- it
    verifies the original (faulty) trajectory once and returns it unchanged.
    This is the literal, exact mechanism that produced the paper's existing
    claim ("Reflexion ... achieve[s] 0% ... forward-only correction has no
    environment feedback to verbalise over", `paper_sections/main.tex` line
    133) for single-fault/multi-valid synthetic mode. Extended verbatim to
    multi-fault it will -- necessarily, by construction, not by any cognitive
    "failure to fix two things at once" -- also score 0%, because it never
    attempts a repair in the synthetic (no-provider) setting.

(B) ``full_regen`` baseline (`intro_specter/baselines/full_regen.py::run_full_regen`)
    driven by `MealPlanningDomain.make_regenerate_fn` (`intro_specter/benchmarks/
    synthetic_dag.py`), which IS the codebase's actual rule-based "blind full
    trajectory regeneration, no targeted diagnosis, retry N times" mechanism
    -- i.e. exactly the mechanism the task brief describes as the fair
    Reflexion analog. `make_regenerate_fn` takes no `regenerate_fn` overrides
    and just re-renders the graph from `profile_facts`; because the
    single_fault AND multi_fault fault-injection methodology (both
    `synthetic_dag.py` and `synthetic_dag_multi_fault.py`) inject faults as a
    pure MANUAL-node **override** on top of the clean render (not a change to
    `profile_facts` or to the generative rule itself), a fresh
    override-free render trivially reconstructs the gold value at every
    MANUAL node. This is a pre-existing structural property of the
    synthetic benchmark's fault-injection design (not something invented or
    tuned for this experiment -- `make_regenerate_fn` is untouched, imported
    as-is), and it means "blind regeneration" resolves 100% of graphs in a
    single attempt on this synthetic benchmark, regardless of how many
    independent faults were injected.

Neither (A) nor (B) is run through a real LLM: both are the exact rule-based
mechanisms the synthetic Tier-C protocol already uses elsewhere in this
codebase (see `configs/synthetic_single_fault_test.yaml`,
`outputs/synthetic_single_fault/*reflexion*.jsonl`,
`outputs/synthetic_single_fault/*full_regen*.jsonl` for the single-fault
precedent this script mirrors). No new hyperparameters are introduced: (A)
takes no round-budget parameter (it never retries), and (B) is given
`max_attempts=3` to match Intro-Specter's exact round budget
(1 initial + T_spr=2 SPR rounds = 3, per `scripts/rebuttal_experiment_d.py`).

Both baselines run against `build_multi_fault_example(idx, seed=0)` for
idx in [0, 60) -- the EXACT SAME 60 graphs (same generator, same seed) that
`scripts/rebuttal_experiment_d.py` already scored Intro-Specter on, so this
is a true paired, apples-to-apples comparison at the level of individual
graphs.

Usage:
    python3 scripts/rebuttal_experiment_d_reflexion.py --n 60
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from intro_specter.baselines.full_regen import run_full_regen
from intro_specter.baselines.reflexion import run_reflexion
from intro_specter.benchmarks.synthetic_dag import MealPlanningDomain
from intro_specter.benchmarks.synthetic_dag_multi_fault import (
    MultiFaultExample,
    build_multi_fault_example,
)
from intro_specter.verifier import HybridVerifier

ROUND_BUDGET = 3  # matches Intro-Specter's 1 + T_spr=2, per rebuttal_experiment_d.py


def run_reflexion_noop(example: MultiFaultExample) -> dict[str, Any]:
    """Mechanism (A): exact `run_reflexion(..., provider=None)` call the
    existing Tier-C synthetic configs make. No retry is attempted (see module
    docstring) -- included for continuity with the paper's existing
    single-fault Reflexion claim, not presented as a meaningful multi-fault
    resolution test."""
    verifier = HybridVerifier(rules=list(example.rules))
    result = run_reflexion(
        profile=example.profile,
        task=example.task,
        trajectory=example.trajectory,
        verifier=verifier,
        provider=None,
        model="",
    )
    return {
        "mechanism": "reflexion_noop_synthetic_protocol",
        "both_resolved": bool(result.verifier.passed),
        "attempts_used": 0,  # no retry occurs when provider is None
        "tokens_input": int(result.tokens_input),
        "tokens_output": int(result.tokens_output),
    }


def run_full_regen_blind(example: MultiFaultExample, domain: MealPlanningDomain) -> dict[str, Any]:
    """Mechanism (B): exact `run_full_regen` + unmodified
    `MealPlanningDomain.make_regenerate_fn`, matched to Intro-Specter's
    3-attempt round budget."""
    verifier = HybridVerifier(rules=list(example.rules))
    regenerate_fn = domain.make_regenerate_fn(
        graph=example.graph, profile_facts=example.profile_facts
    )
    result = run_full_regen(
        profile=example.profile,
        task=example.task,
        trajectory=example.trajectory,
        verifier=verifier,
        regenerate_fn=regenerate_fn,
        max_attempts=ROUND_BUDGET,
    )
    return {
        "mechanism": "full_regen_blind_matched_budget",
        "both_resolved": bool(result.verifier.passed),
        "attempts_used": int(result.meta.get("attempts", 0)),
        "tokens_input": int(result.tokens_input),
        "tokens_output": int(result.tokens_output),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--output",
        default="outputs/rebuttal/experiment_d/multi_fault_vs_reflexion.jsonl",
    )
    args = ap.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    domain = MealPlanningDomain(seed=args.seed)  # only used for make_regenerate_fn closure

    rows: list[dict[str, Any]] = []
    with out_path.open("w") as f:
        for idx in range(args.n):
            example = build_multi_fault_example(idx, seed=args.seed)
            reflexion_row = run_reflexion_noop(example)
            full_regen_row = run_full_regen_blind(example, domain)
            row = {
                "task_id": example.task_id,
                "gold_fault_ids": list(example.gold_fault_ids),
                "reflexion_noop": reflexion_row,
                "full_regen_blind": full_regen_row,
            }
            rows.append(row)
            f.write(json.dumps(row, default=str) + "\n")
            print(
                f"  {row['task_id']}: "
                f"reflexion_noop.both_resolved={reflexion_row['both_resolved']} "
                f"full_regen_blind.both_resolved={full_regen_row['both_resolved']} "
                f"(attempts={full_regen_row['attempts_used']})"
            )

    n = len(rows)
    n_reflexion_resolved = sum(1 for r in rows if r["reflexion_noop"]["both_resolved"])
    n_full_regen_resolved = sum(1 for r in rows if r["full_regen_blind"]["both_resolved"])
    mean_full_regen_attempts = (
        sum(r["full_regen_blind"]["attempts_used"] for r in rows) / n if n else 0.0
    )
    total_full_regen_tokens = sum(
        r["full_regen_blind"]["tokens_input"] + r["full_regen_blind"]["tokens_output"] for r in rows
    )

    summary = {
        "n_graphs": n,
        "round_budget_matched_to_intro_specter": ROUND_BUDGET,
        "intro_specter_pct_both_resolved": 0.0,  # from outputs/rebuttal/experiment_d/multi_fault_summary.json
        "reflexion_noop_pct_both_resolved": 100.0 * n_reflexion_resolved / n if n else 0.0,
        "full_regen_blind_pct_both_resolved": 100.0 * n_full_regen_resolved / n if n else 0.0,
        "full_regen_blind_mean_attempts_used": mean_full_regen_attempts,
        "full_regen_blind_total_tokens": total_full_regen_tokens,
    }
    summary_path = out_path.with_name("multi_fault_vs_reflexion_summary.json")
    summary_path.write_text(json.dumps(summary, indent=2))

    print("\n--- Experiment D vs. Reflexion-equivalent summary ---")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print(f"\nWrote {n} rows to {out_path}")
    print(f"Wrote summary to {summary_path}")


if __name__ == "__main__":
    main()
