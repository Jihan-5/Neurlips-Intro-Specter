#!/usr/bin/env python3
"""FUTURE-WORK EXPLORATION -- NOT part of the current NeurIPS submission's
evidence. Standalone driver for the isolated experimental module
`intro_specter/pipeline_experimental_cumulative_repair.py`.

This script is NOT imported by, and does not import, any of
`scripts/rebuttal_experiment_*.py` or anything that touches the reviewed
`intro_specter/pipeline.py` code path. It exists purely to answer an R&D
question raised by Experiment D: does making SPR repairs cumulative across
rounds (rerun from the previous round's partially-repaired trajectory instead
of the original faulty trajectory every round) fix multi-fault resolution,
and does it preserve the paper's reported single-fault numbers?

Two evaluations, both $0 / rule-based (RuleBasedCounterfactualSampler, no LLM
calls anywhere in this script):

  1. Multi-fault improvement test: same 60 multi-fault synthetic graphs as
     Experiment D (`intro_specter/benchmarks/synthetic_dag_multi_fault.py`,
     same seed=0), run through the cumulative-repair variant. Reports
     pct_both_resolved_within_budget, directly comparable to Experiment D's
     0% baseline (`outputs/rebuttal/experiment_d/multi_fault_summary.json`).

  2. Single-fault regression check: same 60 single-fault synthetic graphs the
     paper's Appendix G diagnostics use
     (`intro_specter/benchmarks/synthetic_dag.py`, mode="single_fault",
     n_examples=60, split="all"), run through the SAME cumulative-repair
     variant. Reports top-1 attribution accuracy and repair rate, to check
     against the paper's reported single-fault numbers (100% top-1
     attribution, 100% repair).

Usage:
    python3 scripts/experimental_cumulative_repair_eval.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from intro_specter.attribution import RuleBasedCounterfactualSampler, posterior_update
from intro_specter.benchmarks.synthetic_dag import SyntheticDAGBenchmark
from intro_specter.benchmarks.synthetic_dag_multi_fault import (
    MultiFaultExample,
    build_multi_fault_example,
)
from intro_specter.dag import candidate_nodes_for_violations
from intro_specter.pipeline_experimental_cumulative_repair import (
    IntroSpecterConfigCumulative,
    run_intro_specter_cumulative_repair,
)
from intro_specter.verifier import HybridVerifier
from intro_specter.verifier import hard_constraint_keyword_rule


def _rounds_used(meta: dict[str, Any]) -> int:
    """Copied verbatim from scripts/rebuttal_experiment_d.py::_rounds_used for
    consistency with Experiment D's round-budget definition."""
    stages = meta.get("stages", []) if meta else []
    n = sum(1 for s in stages if s.get("stage") == "decision")
    n += sum(
        1 for s in stages
        if isinstance(s.get("stage"), str)
        and s["stage"].startswith("spr_round_")
        and s["stage"].endswith("_decision")
    )
    return max(n, 1)


def _initial_posterior_top2(example: MultiFaultExample, verifier: HybridVerifier) -> list[str]:
    """Copied from rebuttal_experiment_d.py: recomputes the round-1 posterior
    purely to read off top-2 before SPR decay reweights it."""
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
    return [c.node_id for c in posterior.candidates[:2]]


def run_multi_fault(n: int, seed: int, out_path: Path) -> dict[str, Any]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    with out_path.open("w") as f:
        for idx in range(n):
            example = build_multi_fault_example(idx, seed=seed)
            verifier = HybridVerifier(rules=list(example.rules))
            sampler = RuleBasedCounterfactualSampler(swap_fn=example.swap_fn, evaluator=example.evaluator)
            cfg = IntroSpecterConfigCumulative(
                tau_abstain=0.0,
                cost_lambda=0.0,
                n_counterfactual_trials=1,
                spr_max_rounds=2,
            )
            result = run_intro_specter_cumulative_repair(
                profile=example.profile,
                task=example.task,
                trajectory=example.trajectory,
                verifier=verifier,
                sampler=sampler,
                config=cfg,
                gold_dag=example.gold_dag,
                rerun_callable=example.rerun_fn,
            )
            top2 = _initial_posterior_top2(example, HybridVerifier(rules=list(example.rules)))
            both_in_top2 = set(example.gold_fault_ids).issubset(set(top2))
            both_resolved = bool(result.verifier.passed)
            row = {
                "task_id": example.task_id,
                "gold_fault_ids": list(example.gold_fault_ids),
                "status": result.status,
                "both_resolved": both_resolved,
                "posterior_top2_initial": top2,
                "both_in_top2": both_in_top2,
                "rounds_used": _rounds_used(result.meta),
                "final_fault_node": result.fault_node,
                "final_output": result.final_trajectory.final_output,
                "tokens_input": int(result.meta.get("tokens_input", 0)),
                "tokens_output": int(result.meta.get("tokens_output", 0)),
            }
            rows.append(row)
            f.write(json.dumps(row, default=str) + "\n")
            print(
                f"  [multi-fault] {row['task_id']}: status={row['status']} "
                f"both_resolved={row['both_resolved']} both_in_top2={row['both_in_top2']} "
                f"rounds={row['rounds_used']}"
            )

    n_rows = len(rows)
    n_both_resolved = sum(1 for r in rows if r["both_resolved"])
    n_both_top2 = sum(1 for r in rows if r["both_in_top2"])
    mean_rounds = sum(r["rounds_used"] for r in rows) / n_rows if n_rows else 0.0
    return {
        "n_graphs": n_rows,
        "pct_both_resolved_within_budget": 100.0 * n_both_resolved / n_rows if n_rows else 0.0,
        "pct_both_faults_in_top2_posterior": 100.0 * n_both_top2 / n_rows if n_rows else 0.0,
        "mean_rounds_used": mean_rounds,
        "baseline_pct_both_resolved_pipeline_py": 0.0,  # Experiment D's finding (0/60)
    }


def run_single_fault_regression(n: int, seed: int, out_path: Path) -> dict[str, Any]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    bench = SyntheticDAGBenchmark(n_examples=n, seed=seed, mode="single_fault", split="all")
    rows: list[dict[str, Any]] = []
    with out_path.open("w") as f:
        for example in bench:
            verifier = HybridVerifier(rules=list(example.rules))
            sampler = RuleBasedCounterfactualSampler(swap_fn=example.swap_fn, evaluator=example.evaluator)
            cfg = IntroSpecterConfigCumulative(
                tau_abstain=0.0,
                cost_lambda=0.0,
                n_counterfactual_trials=1,
                spr_max_rounds=2,
            )
            result = run_intro_specter_cumulative_repair(
                profile=example.profile,
                task=example.task,
                trajectory=example.trajectory,
                verifier=verifier,
                sampler=sampler,
                config=cfg,
                gold_dag=example.dag,
                rerun_callable=example.rerun_fn,
            )
            gold_fault = example.gold.fault_node_id
            top1_correct = result.fault_node == gold_fault if result.fault_node else False
            repaired = bool(result.verifier.passed)
            row = {
                "task_id": example.task_id,
                "gold_fault_id": gold_fault,
                "status": result.status,
                "final_fault_node": result.fault_node,
                "top1_correct": top1_correct,
                "repaired": repaired,
                "rounds_used": _rounds_used(result.meta),
            }
            rows.append(row)
            f.write(json.dumps(row, default=str) + "\n")
            print(
                f"  [single-fault] {row['task_id']}: status={row['status']} "
                f"top1_correct={row['top1_correct']} repaired={row['repaired']}"
            )

    n_rows = len(rows)
    n_top1 = sum(1 for r in rows if r["top1_correct"])
    n_repaired = sum(1 for r in rows if r["repaired"])
    return {
        "n_graphs": n_rows,
        "pct_top1_attribution": 100.0 * n_top1 / n_rows if n_rows else 0.0,
        "pct_repaired": 100.0 * n_repaired / n_rows if n_rows else 0.0,
        "paper_reported_top1_attribution": 100.0,
        "paper_reported_repair_rate": 100.0,
    }


def main() -> None:
    out_dir = Path("outputs/rebuttal/future_work_exploration")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=== Cumulative-repair variant: multi-fault improvement test (n=60, seed=0) ===")
    multi_summary = run_multi_fault(
        n=60, seed=0, out_path=out_dir / "cumulative_repair_multi_fault.jsonl"
    )
    print(json.dumps(multi_summary, indent=2))

    print("\n=== Cumulative-repair variant: single-fault regression check (n=60, seed=0) ===")
    single_summary = run_single_fault_regression(
        n=60, seed=0, out_path=out_dir / "cumulative_repair_single_fault_regression_check.jsonl"
    )
    print(json.dumps(single_summary, indent=2))

    summary_path = out_dir / "cumulative_repair_summary.json"
    summary_path.write_text(json.dumps(
        {"multi_fault": multi_summary, "single_fault_regression": single_summary}, indent=2
    ))
    print(f"\nWrote combined summary to {summary_path}")


if __name__ == "__main__":
    main()
