#!/usr/bin/env python3
"""Rebuttal fault sweep, synthetic ($0/fast). Build-plan section 1.

Extends Experiment D (`scripts/rebuttal_experiment_d.py`, N=2 faults only) to
N in {2,3,4,5} faults, and adds a second, explicitly-labeled "fixed" arm that
combines two SEPARATE, ADDITIVE, standalone files built for this sweep:

  * `intro_specter/benchmarks/synthetic_dag_multi_fault.py`'s
    `build_multi_fault_graph`/`build_multi_fault_example`, generalized to a
    `num_faults` parameter (2..5 independent MANUAL-node fault branches,
    joined only at the terminal node) -- this file also backs the
    "unmodified" arm (default `num_faults=2` reproduces the original graph
    exactly), so both arms share IDENTICAL example construction.
  * `intro_specter/benchmarks/synthetic_dag_fixed_harness.py`'s
    `make_rerun_fn_fixed` (evolving repaired-value map instead of a static
    snapshot, no dropped trajectory steps on interleaved branches) --
    substituted in place of the default `MealPlanningDomain.make_rerun_fn`
    closure ONLY for the "fixed" arm.

Two variants x four fault counts = 8 cells, n=60 graphs each:

  * "unmodified": unmodified `intro_specter.pipeline.run_intro_specter` +
    unmodified `synthetic_dag_multi_fault.py` graphs/rerun_fn. This is the
    ONLY arm usable as rebuttal evidence about the submitted method.
  * "fixed": `intro_specter.pipeline_experimental_cumulative_repair.
    run_intro_specter_cumulative_repair` (already built, untouched here) +
    `make_rerun_fn_fixed` (this sweep's new harness fix). FUTURE-WORK ONLY --
    never evidence about the current submission.

100% synthetic / rule-based (`RuleBasedCounterfactualSampler`, no LLM
provider constructed anywhere): $0, no API calls, n=60 x 4 x 2 = 480 graphs
total, expected to run in well under a minute.

Usage:
    python3 scripts/rebuttal_fault_sweep_synthetic.py --n 60
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from intro_specter.attribution import RuleBasedCounterfactualSampler, posterior_update
from intro_specter.benchmarks.synthetic_dag_fixed_harness import make_rerun_fn_fixed
from intro_specter.benchmarks.synthetic_dag_multi_fault import (
    MultiFaultExample,
    build_multi_fault_example,
)
from intro_specter.dag import candidate_nodes_for_violations
from intro_specter.pipeline import IntroSpecterConfig, run_intro_specter
from intro_specter.pipeline_experimental_cumulative_repair import (
    IntroSpecterConfigCumulative,
    run_intro_specter_cumulative_repair,
)
from intro_specter.verifier import HybridVerifier

FAULT_COUNTS = [2, 3, 4, 5]
VARIANTS = ["unmodified", "fixed"]


def _rounds_used(meta: dict[str, Any]) -> int:
    """Copied verbatim from scripts/rebuttal_experiment_d.py::_rounds_used
    for consistency with Experiment D's round-budget definition."""
    stages = meta.get("stages", []) if meta else []
    n = sum(1 for s in stages if s.get("stage") == "decision")
    n += sum(
        1 for s in stages
        if isinstance(s.get("stage"), str)
        and s["stage"].startswith("spr_round_")
        and s["stage"].endswith("_decision")
    )
    return max(n, 1)


def _initial_posterior_topN(
    example: MultiFaultExample, verifier: HybridVerifier, top_n: int
) -> list[str]:
    """Recomputes the round-1 posterior (same candidate/sampler pipeline
    `run_intro_specter` itself uses) purely to read off the top-N node ids
    before SPR's decay reweighting overwrites `q`. Copied/generalized from
    scripts/rebuttal_experiment_d.py::_initial_posterior_top2."""
    verifier_result, _ = verifier.check(
        profile=example.profile,
        task=example.task,
        trajectory=example.trajectory,
        final_output=example.trajectory.final_output,
    )
    candidates = candidate_nodes_for_violations(example.gold_dag, verifier_result.violations)
    sampler = RuleBasedCounterfactualSampler(swap_fn=example.swap_fn, evaluator=example.evaluator)
    posterior, _trials = posterior_update(
        candidates=candidates,
        dag=example.gold_dag,
        sampler=sampler,
        profile=example.profile,
        task=example.task,
        trajectory=example.trajectory,
        violations=verifier_result.violations,
        n_trials=1,
    )
    return [c.node_id for c in posterior.candidates[:top_n]]


def run_one_unmodified(example: MultiFaultExample) -> dict[str, Any]:
    verifier = HybridVerifier(rules=list(example.rules))
    sampler = RuleBasedCounterfactualSampler(swap_fn=example.swap_fn, evaluator=example.evaluator)
    cfg = IntroSpecterConfig(
        tau_abstain=0.0,
        cost_lambda=0.0,
        n_counterfactual_trials=1,
        spr_max_rounds=2,  # T_spr = 2, matching Experiment D / synthetic configs
    )
    result = run_intro_specter(
        profile=example.profile,
        task=example.task,
        trajectory=example.trajectory,
        verifier=verifier,
        sampler=sampler,
        config=cfg,
        gold_dag=example.gold_dag,
        rerun_callable=example.rerun_fn,
    )
    top_n = _initial_posterior_topN(
        example, HybridVerifier(rules=list(example.rules)), top_n=example.num_faults
    )
    all_faults_in_topN = set(example.gold_fault_ids).issubset(set(top_n))
    resolved = bool(result.verifier.passed)
    return {
        "status": result.status,
        "resolved": resolved,
        "posterior_topN_initial": top_n,
        "all_faults_in_topN": all_faults_in_topN,
        "rounds_used": _rounds_used(result.meta),
        "tokens_input": int(result.meta.get("tokens_input", 0)),
        "tokens_output": int(result.meta.get("tokens_output", 0)),
        "final_fault_node": result.fault_node,
    }


def run_one_fixed(example: MultiFaultExample) -> dict[str, Any]:
    verifier = HybridVerifier(rules=list(example.rules))
    sampler = RuleBasedCounterfactualSampler(swap_fn=example.swap_fn, evaluator=example.evaluator)
    cfg = IntroSpecterConfigCumulative(
        tau_abstain=0.0,
        cost_lambda=0.0,
        n_counterfactual_trials=1,
        spr_max_rounds=2,
    )
    fixed_rerun_fn = make_rerun_fn_fixed(
        graph=example.graph,
        profile_facts=example.profile_facts,
        faulty_values=example.faulty_values,
        gold_values=example.gold_values,
    )
    result = run_intro_specter_cumulative_repair(
        profile=example.profile,
        task=example.task,
        trajectory=example.trajectory,
        verifier=verifier,
        sampler=sampler,
        config=cfg,
        gold_dag=example.gold_dag,
        rerun_callable=fixed_rerun_fn,
    )
    top_n = _initial_posterior_topN(
        example, HybridVerifier(rules=list(example.rules)), top_n=example.num_faults
    )
    all_faults_in_topN = set(example.gold_fault_ids).issubset(set(top_n))
    resolved = bool(result.verifier.passed)
    return {
        "status": result.status,
        "resolved": resolved,
        "posterior_topN_initial": top_n,
        "all_faults_in_topN": all_faults_in_topN,
        "rounds_used": _rounds_used(result.meta),
        "tokens_input": int(result.meta.get("tokens_input", 0)),
        "tokens_output": int(result.meta.get("tokens_output", 0)),
        "final_fault_node": result.fault_node,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=60, help="graphs per cell")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--output",
        default="outputs/rebuttal/experiment_d/fault_sweep_synthetic.jsonl",
    )
    args = ap.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict[str, Any]] = []
    with out_path.open("w") as f:
        for num_faults in FAULT_COUNTS:
            for variant in VARIANTS:
                n_resolved = 0
                n_topN = 0
                round_sum = 0
                for idx in range(args.n):
                    example = build_multi_fault_example(idx, seed=args.seed, num_faults=num_faults)
                    if variant == "unmodified":
                        r = run_one_unmodified(example)
                    else:
                        r = run_one_fixed(example)
                    row = {
                        "task_id": example.task_id,
                        "num_faults": num_faults,
                        "variant": variant,
                        "gold_fault_ids": list(example.gold_fault_ids),
                        "status": r["status"],
                        "both_faults_in_topN_of_posterior": r["all_faults_in_topN"],
                        "posterior_topN_initial": r["posterior_topN_initial"],
                        "pct_resolved": 100.0 if r["resolved"] else 0.0,
                        "resolved": r["resolved"],
                        "rounds_used": r["rounds_used"],
                        "final_fault_node": r["final_fault_node"],
                        "tokens_input": r["tokens_input"],
                        "tokens_output": r["tokens_output"],
                    }
                    all_rows.append(row)
                    f.write(json.dumps(row, default=str) + "\n")
                    n_resolved += int(r["resolved"])
                    n_topN += int(r["all_faults_in_topN"])
                    round_sum += r["rounds_used"]
                print(
                    f"num_faults={num_faults} variant={variant}: "
                    f"resolved={n_resolved}/{args.n} "
                    f"({100.0 * n_resolved / args.n:.1f}%)  "
                    f"all_in_topN={n_topN}/{args.n} "
                    f"({100.0 * n_topN / args.n:.1f}%)  "
                    f"mean_rounds={round_sum / args.n:.2f}"
                )

    # ---- summary ----
    cells: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for row in all_rows:
        key = (row["num_faults"], row["variant"])
        cells.setdefault(key, []).append(row)

    summary_lines = [
        "# Fault sweep (synthetic) -- Build-plan section 1",
        "",
        f"n={args.n} graphs per cell, seed={args.seed}. $0 / rule-based, no LLM calls.",
        "",
        "**Rebuttal-usable evidence**: `unmodified` rows only (unmodified "
        "`pipeline.py` + unmodified `synthetic_dag_multi_fault.py` graphs/rerun_fn).",
        "",
        "**Future-work exploration, NOT current-submission evidence**: `fixed` "
        "rows (`pipeline_experimental_cumulative_repair.py` + "
        "`synthetic_dag_fixed_harness.py`).",
        "",
        "| num_faults | variant | pct_resolved | pct_all_faults_in_topN | mean_rounds_used |",
        "|---|---|---|---|---|",
    ]
    summary_json: dict[str, Any] = {"n_per_cell": args.n, "seed": args.seed, "cells": []}
    for num_faults in FAULT_COUNTS:
        for variant in VARIANTS:
            rows = cells.get((num_faults, variant), [])
            n = len(rows)
            pct_resolved = 100.0 * sum(1 for r in rows if r["resolved"]) / n if n else 0.0
            pct_topN = 100.0 * sum(1 for r in rows if r["both_faults_in_topN_of_posterior"]) / n if n else 0.0
            mean_rounds = sum(r["rounds_used"] for r in rows) / n if n else 0.0
            summary_lines.append(
                f"| {num_faults} | {variant} | {pct_resolved:.1f}% | {pct_topN:.1f}% | {mean_rounds:.2f} |"
            )
            summary_json["cells"].append({
                "num_faults": num_faults,
                "variant": variant,
                "n_graphs": n,
                "pct_resolved": pct_resolved,
                "pct_all_faults_in_topN_of_posterior": pct_topN,
                "mean_rounds_used": mean_rounds,
            })

    summary_md_path = out_path.with_name("fault_sweep_synthetic_SUMMARY.md")
    summary_md_path.write_text("\n".join(summary_lines) + "\n")
    summary_json_path = out_path.with_name("fault_sweep_synthetic_summary.json")
    summary_json_path.write_text(json.dumps(summary_json, indent=2))

    print(f"\nWrote {len(all_rows)} rows to {out_path}")
    print(f"Wrote summary to {summary_md_path}")
    print(f"Wrote summary json to {summary_json_path}")


if __name__ == "__main__":
    main()
