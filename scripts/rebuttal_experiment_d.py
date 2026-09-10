#!/usr/bin/env python3
"""Experiment D: multi-fault stress test (rebuttal campaign, reviewer LDZz).

LDZz asked: "how does the method handle multiple violations along a
trajectory?" The paper's mechanism diagnostics (Appendix G) use a synthetic
Assumption-DAG generator (`intro_specter/benchmarks/synthetic_dag.py`,
n=60 graphs) that only ever injects **one** fault per graph. This script
drives the ADDITIVE `multi_fault` extension of that generator
(`intro_specter/benchmarks/synthetic_dag_multi_fault.py`, a new file --
`synthetic_dag.py` itself is untouched) through the *exact same* evaluation
harness the single-fault protocol uses:

    verifier.check -> candidate_nodes_for_violations -> posterior_update
    -> choose_repair_node -> rerun_downstream_subgraph_callable -> re-verify
    -> (Sequential Posterior Refinement, up to `spr_max_rounds=2`)

i.e. `intro_specter.pipeline.run_intro_specter` called with a
`RuleBasedCounterfactualSampler` (rule-based swap_fn + evaluator, same as the
synthetic single-fault config's `intro_specter` method in
`configs/synthetic_single_fault_val.yaml`) and `IntroSpecterConfig`
(tau_abstain=0.0, cost_lambda=0.0, n_counterfactual_trials=1,
spr_max_rounds=2) -- these are the exact defaults the real synthetic configs
use, not new hyperparameters invented for this experiment.

This is 100% synthetic / rule-based: no LLM provider is constructed anywhere
in this script (RuleBasedCounterfactualSampler needs none, and
gold_dag=<passthrough> skips the LLM extraction prompt too), so running n=60
graphs costs $0 / makes zero API calls.

Metrics computed per graph and aggregated:
  * both_resolved   -- final verifier passes (== both faults cleared) within
                        the 1-initial + spr_max_rounds=2 round budget.
  * both_in_top2    -- both gold fault node ids appear in the top-2 of the
                        *initial* attribution posterior q (computed via the
                        same `attribution.posterior_update` call pipeline.py
                        itself makes for round 1 -- recomputed once more here,
                        deterministically, purely to read off q before SPR's
                        decay reweights it away).
  * interacting     -- exhaustive single-node trial on the gold graph: try
                        swapping every node in the graph one at a time
                        (via the same swap_fn/evaluator pair used inside the
                        pipeline) and check whether any single swap clears
                        ALL violations. If none does, the two faults are
                        "interacting" per this definition (their effects
                        cannot be fixed independently of one another).
  * rounds_used     -- 1 (initial) + number of SPR rounds actually attempted,
                        counted from `meta["stages"]` exactly as
                        `scripts/rebuttal_experiment_b.py::_rounds_used_intro_specter`
                        already does for Experiment B (copied verbatim here
                        for consistency across the rebuttal campaign).
  * tokens_input / tokens_output -- from `meta["tokens_input"/"tokens_output"]`
                        (expected to be 0 throughout: rule-based sampler +
                        passthrough dag => no LLM calls).

Usage:
    python3 scripts/rebuttal_experiment_d.py --n 60
    python3 scripts/rebuttal_experiment_d.py --n 10   # pilot
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from intro_specter.attribution import RuleBasedCounterfactualSampler, posterior_update
from intro_specter.benchmarks.synthetic_dag_multi_fault import (
    MultiFaultExample,
    build_multi_fault_example,
)
from intro_specter.dag import candidate_nodes_for_violations
from intro_specter.pipeline import IntroSpecterConfig, run_intro_specter
from intro_specter.verifier import HybridVerifier


def _rounds_used(meta: dict[str, Any]) -> int:
    """Copied verbatim from scripts/rebuttal_experiment_b.py::_rounds_used_intro_specter
    (same derivation logic, same round-budget definition) for consistency
    across the rebuttal campaign's Experiment B / Experiment D scripts."""
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
    """Recomputes exactly the round-1 posterior `pipeline.run_intro_specter`
    itself would compute (same `candidate_nodes_for_violations` +
    `posterior_update` calls, same sampler), purely so we can read off the
    top-2 node ids *before* SPR's decay reweighting overwrites `q`. Pure /
    side-effect-free (RuleBasedCounterfactualSampler + rule-based verifier),
    so calling it once here and again inside `run_intro_specter` below is
    not double-charging any API cost (there is none) and returns identical
    numbers both times."""
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


def _exhaustive_interaction_check(example: MultiFaultExample) -> tuple[bool, str | None]:
    """Try every node in the graph as a *single* swap target and check
    (via the same evaluator the pipeline uses, which re-executes downstream
    and re-verifies ALL hard constraints) whether any one of them clears
    every violation. Returns (interacting, clearing_node_id_or_None)."""
    from intro_specter.schemas import ViolationEvent

    dummy_violation = ViolationEvent(
        violation_id="v_exhaustive_probe", step_id=0, violated_profile_span_id="",
        violated_constraint="", trajectory_text="", confidence=1.0, explanation="",
    )
    for node in example.gold_dag.nodes:
        repair = example.swap_fn(node)
        if repair is None:
            continue
        if example.evaluator(repair, example.trajectory, dummy_violation):
            return False, node.id
    return True, None


def run_one(example: MultiFaultExample) -> dict[str, Any]:
    verifier = HybridVerifier(rules=list(example.rules))
    sampler = RuleBasedCounterfactualSampler(swap_fn=example.swap_fn, evaluator=example.evaluator)
    cfg = IntroSpecterConfig(
        tau_abstain=0.0,
        cost_lambda=0.0,
        n_counterfactual_trials=1,
        spr_max_rounds=2,  # T_spr = 2, matching configs/synthetic_single_fault_val.yaml
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

    top2 = _initial_posterior_top2(example, HybridVerifier(rules=list(example.rules)))
    both_in_top2 = set(example.gold_fault_ids).issubset(set(top2))
    interacting, clearing_node = _exhaustive_interaction_check(example)

    both_resolved = bool(result.verifier.passed)

    return {
        "task_id": example.task_id,
        "gold_fault_ids": list(example.gold_fault_ids),
        "status": result.status,
        "both_resolved": both_resolved,
        "final_verifier_passed": result.verifier.passed,
        "n_violations_initial": None,  # filled below by caller if desired
        "posterior_top2_initial": top2,
        "both_in_top2": both_in_top2,
        "interacting": interacting,
        "single_node_clears_all": clearing_node,
        "rounds_used": _rounds_used(result.meta),
        "tokens_input": int(result.meta.get("tokens_input", 0)),
        "tokens_output": int(result.meta.get("tokens_output", 0)),
        "final_fault_node": result.fault_node,
        "final_output": result.final_trajectory.final_output,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=60, help="number of multi-fault graphs")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--output",
        default="outputs/rebuttal/experiment_d/multi_fault_results.jsonl",
    )
    args = ap.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    with out_path.open("w") as f:
        for idx in range(args.n):
            example = build_multi_fault_example(idx, seed=args.seed)
            row = run_one(example)
            rows.append(row)
            f.write(json.dumps(row, default=str) + "\n")
            print(
                f"  {row['task_id']}: status={row['status']} "
                f"both_resolved={row['both_resolved']} "
                f"both_in_top2={row['both_in_top2']} "
                f"interacting={row['interacting']} "
                f"rounds={row['rounds_used']} "
                f"tokens=({row['tokens_input']},{row['tokens_output']})"
            )

    n = len(rows)
    n_both_resolved = sum(1 for r in rows if r["both_resolved"])
    n_both_top2 = sum(1 for r in rows if r["both_in_top2"])
    n_interacting = sum(1 for r in rows if r["interacting"])
    mean_rounds = sum(r["rounds_used"] for r in rows) / n if n else 0.0
    total_tokens_in = sum(r["tokens_input"] for r in rows)
    total_tokens_out = sum(r["tokens_output"] for r in rows)

    summary = {
        "n_graphs": n,
        "pct_both_resolved_within_2_spr_rounds": 100.0 * n_both_resolved / n if n else 0.0,
        "pct_both_faults_in_top2_posterior": 100.0 * n_both_top2 / n if n else 0.0,
        "pct_genuinely_interacting": 100.0 * n_interacting / n if n else 0.0,
        "mean_rounds_used": mean_rounds,
        "total_tokens_input": total_tokens_in,
        "total_tokens_output": total_tokens_out,
        "mean_tokens_per_graph": (total_tokens_in + total_tokens_out) / n if n else 0.0,
    }
    summary_path = out_path.with_name(out_path.stem.replace("_results", "") + "_summary.json")
    summary_path.write_text(json.dumps(summary, indent=2))

    print("\n--- Experiment D summary ---")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print(f"\nWrote {n} rows to {out_path}")
    print(f"Wrote summary to {summary_path}")


if __name__ == "__main__":
    main()
