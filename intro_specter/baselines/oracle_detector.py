"""Oracle-detector baseline.

The plan PDF lists "Oracle detector — Upper-bounds repair if violation
detection is perfect." It runs the full Intro-Specter attribution + repair
pipeline but bypasses verification: instead of asking the verifier whether
the trajectory contains violations, it consumes a benchmark-supplied
``gold_violations`` list and feeds those straight into posterior attribution.

For the synthetic benchmark, the rule-based keyword verifier is *exact* and
oracle_detector therefore reduces to standard intro_specter — which is the
point: the comparison shows attribution doesn't lose meaningful headroom even
under perfect detection. For natural benchmarks, ``gold_violations`` will be
human-annotated and the gap between the two becomes interpretable.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..attribution import (
    CounterfactualSampler,
    RuleBasedCounterfactualSampler,
    posterior_update,
)
from ..dag import candidate_nodes_for_violations
from ..repair import (
    CostModel,
    choose_repair_node,
    rerun_downstream_subgraph_callable,
)
from ..schemas import (
    AssumptionDAG,
    AssumptionNode,
    Trajectory,
    TrajectoryStep,
    UserProfile,
    VerifierResult,
    ViolationEvent,
)
from ..verifier import HybridVerifier
from .base import BaselineResult, register


def run_oracle_detector(
    *,
    profile: UserProfile,
    task: dict[str, Any],
    trajectory: Trajectory,
    verifier: HybridVerifier,
    dag: AssumptionDAG,
    gold_violations: list[ViolationEvent],
    sampler: CounterfactualSampler,
    rerun_fn: Callable[
        [list[TrajectoryStep], AssumptionNode, AssumptionDAG], tuple[list[TrajectoryStep], str | None]
    ],
    cost_model: CostModel | None = None,
    tau_abstain: float = 0.0,
    n_counterfactual_trials: int = 1,
    **_: Any,
) -> BaselineResult:
    if not gold_violations:
        # Nothing flagged — pass through.
        return BaselineResult(
            method="oracle_detector",
            final_trajectory=trajectory,
            verifier=VerifierResult(**{"pass": True, "violations": []}),  # type: ignore[arg-type]
            meta={"note": "no gold violations; passthrough"},
        )

    candidates = candidate_nodes_for_violations(dag, gold_violations)
    posterior, _ = posterior_update(
        candidates=candidates,
        dag=dag,
        sampler=sampler,
        profile=profile,
        task=task,
        trajectory=trajectory,
        violations=gold_violations,
        n_trials=n_counterfactual_trials,
    )
    decision = choose_repair_node(
        posterior=posterior,
        dag=dag,
        cost_model=cost_model or CostModel(),
        tau_abstain=tau_abstain,
    )
    if decision.status != "repaired" or decision.fault_node is None:
        verdict, _ = verifier.check(
            profile=profile, task=task, trajectory=trajectory, final_output=trajectory.final_output
        )
        return BaselineResult(
            method="oracle_detector",
            final_trajectory=trajectory,
            verifier=verdict,
            meta={"decision_status": decision.status, "posterior_top_k": posterior.top_k},
        )
    new_traj = rerun_downstream_subgraph_callable(
        trajectory=trajectory,
        dag=dag,
        fault_node_id=decision.fault_node,
        rerun_fn=rerun_fn,
    )
    verdict, _ = verifier.check(
        profile=profile, task=task, trajectory=new_traj, final_output=new_traj.final_output
    )
    return BaselineResult(
        method="oracle_detector",
        final_trajectory=new_traj,
        verifier=verdict,
        meta={
            "fault_node_predicted": decision.fault_node,
            "posterior_top_k": posterior.top_k,
        },
    )


register("oracle_detector", run_oracle_detector)
