"""Layer 3: selective downstream repair (MCGR — Min-Cost Graph-Edit Repair).

Implements the cost-aware repair-node selection from the plan PDF and a generic
`re-execute downstream subgraph` driver. The "Bayes-optimal" framing the draft
paper uses requires a defined loss; we provide an explicit expected-utility
objective that the paper can cite.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .dag import descendants_of_node
from .models import ChatProvider
from .prompts import REEXECUTION_SYSTEM, reexecution_user
from .schemas import (
    AssumptionDAG,
    AssumptionNode,
    AttributionPosterior,
    RepairDecision,
    Trajectory,
    TrajectoryStep,
    UserProfile,
)


@dataclass
class CostModel:
    """Edit cost for a candidate fault node.

    cost(a_k) = w_desc * |descendants(a_k)|
              + w_tokens * expected_regen_tokens(a_k)
              + w_corruption * is_root_of_valid_prefix(a_k)
    """

    w_desc: float = 1.0
    w_tokens: float = 0.0
    w_corruption: float = 0.0
    tokens_per_step: float = 200.0

    def cost(self, node: AssumptionNode, dag: AssumptionDAG) -> float:
        n_desc = len(descendants_of_node(dag, node.id)) + 1
        regen_tokens = n_desc * self.tokens_per_step
        # "Risk of corrupting valid prefix steps": root nodes are higher risk.
        is_root = not node.depends_on
        return (
            self.w_desc * n_desc
            + self.w_tokens * regen_tokens
            + self.w_corruption * (1.0 if is_root else 0.0)
        )


def choose_repair_node(
    *,
    posterior: AttributionPosterior,
    dag: AssumptionDAG,
    cost_model: CostModel = CostModel(),
    tau_abstain: float = 0.0,
    utility_success: float = 1.0,
) -> RepairDecision:
    """Select the node that maximizes expected utility:

        argmax_k  p(a_k | e) * utility_success - lambda * cost(a_k)

    where the cost is normalized to the max cost in the candidate set so that
    `utility_success` and `lambda` are on comparable scales.

    If no candidate's posterior exceeds `tau_abstain`, abstain.
    """
    if not posterior.candidates:
        return RepairDecision(status="abstain_or_full_regenerate", explanation="no candidates")
    if max(c.posterior for c in posterior.candidates) < tau_abstain:
        return RepairDecision(
            status="abstain_or_full_regenerate",
            posterior=posterior,
            explanation=f"max posterior < tau_abstain ({tau_abstain})",
        )

    nodes_by_id = {n.id: n for n in dag.nodes}
    costs: dict[str, float] = {}
    for c in posterior.candidates:
        node = nodes_by_id.get(c.node_id)
        if node is None:
            continue
        costs[c.node_id] = cost_model.cost(node, dag)
    if not costs:
        return RepairDecision(status="abstain_or_full_regenerate", explanation="no costable nodes")
    max_cost = max(costs.values()) or 1.0

    best_score = -float("inf")
    best_id: str | None = None
    best_cost = 0.0
    for c in posterior.candidates:
        cost = costs.get(c.node_id, max_cost)
        score = c.posterior * utility_success - (cost / max_cost)
        if score > best_score:
            best_score = score
            best_id = c.node_id
            best_cost = cost

    return RepairDecision(
        status="repaired",
        fault_node=best_id,
        posterior=posterior,
        expected_cost=best_cost,
        expected_utility=best_score,
        explanation="argmax of posterior * utility - normalized_cost",
    )


# ---------------------------------------------------------------------------
# Re-executing the downstream subgraph
# ---------------------------------------------------------------------------


def split_valid_prefix(
    trajectory: Trajectory, dag: AssumptionDAG, fault_node_id: str
) -> tuple[list[TrajectoryStep], list[TrajectoryStep]]:
    """Return (prefix_steps, downstream_steps).

    A step is "downstream" if its `step_id` is at or after the step of any node
    in `descendants(fault_node) ∪ {fault_node}`. Everything before that earliest
    affected step is the valid prefix.
    """
    affected_node_ids = {fault_node_id} | {n.id for n in descendants_of_node(dag, fault_node_id)}
    affected_step_ids = {n.step_id for n in dag.nodes if n.id in affected_node_ids}
    if not affected_step_ids:
        return list(trajectory.steps), []
    earliest = min(affected_step_ids)
    prefix = [s for s in trajectory.steps if s.step_id < earliest]
    downstream = [s for s in trajectory.steps if s.step_id >= earliest]
    return prefix, downstream


def rerun_downstream_subgraph_llm(
    *,
    profile: UserProfile,
    task: dict[str, Any],
    trajectory: Trajectory,
    dag: AssumptionDAG,
    fault_node_id: str,
    repaired_assumption: str,
    tool_observations: list[dict[str, Any]] | None = None,
    provider: ChatProvider,
    model: str,
    temperature: float = 0.0,
    seed: int | None = None,
) -> Trajectory:
    """Use an LLM to regenerate steps from the fault point onward."""
    nodes_by_id = {n.id: n for n in dag.nodes}
    fault_node = nodes_by_id[fault_node_id]
    valid_prefix, _ = split_valid_prefix(trajectory, dag, fault_node_id)
    downstream_node_ids = [
        n.id
        for n in [fault_node] + descendants_of_node(dag, fault_node_id)
    ]
    repaired_node = fault_node.model_copy(update={"assumption": repaired_assumption})
    payload, _ = provider.complete_json(
        system=REEXECUTION_SYSTEM,
        user=reexecution_user(
            profile=profile.model_dump(mode="json"),
            task=task,
            valid_prefix=[s.model_dump(mode="json") for s in valid_prefix],
            repaired_node=repaired_node.model_dump(mode="json"),
            downstream_node_ids=downstream_node_ids,
            tool_observations=tool_observations or [],
        ),
        model=model,
        temperature=temperature,
        seed=seed,
    )
    new_steps_raw = payload.get("repaired_steps", [])
    new_steps = [TrajectoryStep.model_validate(s) for s in new_steps_raw]
    final_output = payload.get("final_output")
    return Trajectory(
        task_id=trajectory.task_id,
        steps=valid_prefix + new_steps,
        final_output=final_output,
    )


def rerun_downstream_subgraph_callable(
    *,
    trajectory: Trajectory,
    dag: AssumptionDAG,
    fault_node_id: str,
    rerun_fn: Callable[[list[TrajectoryStep], AssumptionNode, AssumptionDAG], tuple[list[TrajectoryStep], str | None]],
) -> Trajectory:
    """Used by synthetic benchmarks: a deterministic Python callable supplies the
    repaired downstream steps and final output. No LLM call required.
    """
    nodes_by_id = {n.id: n for n in dag.nodes}
    fault_node = nodes_by_id[fault_node_id]
    valid_prefix, _ = split_valid_prefix(trajectory, dag, fault_node_id)
    new_steps, final_output = rerun_fn(valid_prefix, fault_node, dag)
    return Trajectory(
        task_id=trajectory.task_id,
        steps=valid_prefix + new_steps,
        final_output=final_output,
    )
