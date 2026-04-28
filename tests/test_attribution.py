"""Posterior attribution: prior shape, normalization, top-k correctness."""

from __future__ import annotations

from intro_specter.attribution import (
    DEFAULT_PROVENANCE_PRIOR,
    RuleBasedCounterfactualSampler,
    posterior_update,
    structural_prior,
)
from intro_specter.schemas import (
    AssumptionDAG,
    AssumptionEdge,
    AssumptionNode,
    CounterfactualRepair,
    Provenance,
    Severity,
    Trajectory,
    TrajectoryStep,
    UserProfile,
    ViolationEvent,
)


def _profile() -> UserProfile:
    return UserProfile(user_id="u", spans=[])


def _violation(step_id: int = 5) -> ViolationEvent:
    return ViolationEvent(
        violation_id="v1",
        step_id=step_id,
        violated_constraint="hard constraint",
        severity=Severity.HIGH,
    )


def test_structural_prior_orders_provenances_correctly() -> None:
    a_inf = AssumptionNode(
        id="a", step_id=1, assumption="x", provenance=Provenance.MODEL_INFERRED, confidence=0.5
    )
    a_prof = AssumptionNode(
        id="b", step_id=1, assumption="x", provenance=Provenance.PROFILE, confidence=0.5
    )
    a_tool = AssumptionNode(
        id="c", step_id=1, assumption="x", provenance=Provenance.TOOL, confidence=0.5
    )
    assert structural_prior(a_inf) > structural_prior(a_tool)
    assert structural_prior(a_tool) > structural_prior(a_prof)


def test_posterior_picks_node_whose_swap_removes_violation() -> None:
    # Three candidates ancestors of the violating step. Only "a3" has a swap that
    # removes the violation; the posterior should rank it first.
    nodes = [
        AssumptionNode(
            id="a1",
            step_id=1,
            assumption="user is X",
            provenance=Provenance.PROFILE,
            confidence=1.0,
        ),
        AssumptionNode(
            id="a2",
            step_id=2,
            assumption="cuisine is Y",
            provenance=Provenance.MODEL_INFERRED,
            confidence=0.8,
            depends_on=["a1"],
        ),
        AssumptionNode(
            id="a3",
            step_id=3,
            assumption="dish is Z",
            provenance=Provenance.MODEL_INFERRED,
            confidence=0.5,
            depends_on=["a1", "a2"],
        ),
    ]
    edges = [
        AssumptionEdge(source="a1", target="a2"),
        AssumptionEdge(source="a1", target="a3"),
        AssumptionEdge(source="a2", target="a3"),
    ]
    dag = AssumptionDAG(task_id="t", nodes=nodes, edges=edges, final_decision_node="a3")
    traj = Trajectory(
        task_id="t",
        steps=[TrajectoryStep(step_id=i, kind="output", text="x") for i in (1, 2, 3)],
    )

    def swap(node: AssumptionNode) -> CounterfactualRepair | None:
        return CounterfactualRepair(
            repair_id=f"r_{node.id}",
            new_assumption="repaired",
            nodes_to_rerun=[node.id],
            repair_instruction="x",
            expected_violation_removed=True,
            risk_notes="",
        )

    def evaluator(repair, trajectory, violation) -> bool:  # type: ignore[no-untyped-def]
        return repair.repair_id == "r_a3"

    sampler = RuleBasedCounterfactualSampler(swap_fn=swap, evaluator=evaluator)
    posterior, _ = posterior_update(
        candidates=nodes,
        dag=dag,
        sampler=sampler,
        profile=_profile(),
        task={},
        trajectory=traj,
        violations=[_violation(step_id=3)],
        n_trials=1,
    )
    assert posterior.candidates[0].node_id == "a3"
    assert posterior.top_k[0] == "a3"
    assert abs(sum(c.posterior for c in posterior.candidates) - 1.0) < 1e-6


def test_default_prior_table_uses_all_provenance_values() -> None:
    # Sanity: every Provenance has a defined prior weight.
    for p in Provenance:
        assert p in DEFAULT_PROVENANCE_PRIOR
