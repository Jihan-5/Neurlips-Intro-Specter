"""DAG operations on Assumption-DAGs.

Implements `build_networkx`, ancestors-of-violated-steps, cycle removal, and
JSON round-tripping. The plan PDF requires acyclicity and ancestor retrieval
for the candidate-set used by posterior attribution.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import networkx as nx

from .schemas import AssumptionDAG, AssumptionEdge, AssumptionNode, ViolationEvent


def build_networkx(dag: AssumptionDAG) -> nx.DiGraph:
    g: nx.DiGraph = nx.DiGraph()
    for node in dag.nodes:
        g.add_node(node.id, **node.model_dump())
    for edge in dag.edges:
        g.add_edge(edge.source, edge.target, type=edge.type.value)
    return g


def remove_cycles(dag: AssumptionDAG) -> tuple[AssumptionDAG, list[AssumptionEdge]]:
    """Remove edges to break any cycles, preferring to drop edges whose source has
    the lowest confidence (matching the "remove the lowest-confidence edge" rule
    from the code-generation prompt in the plan PDF).

    Returns the cleaned DAG and the list of removed edges (for logging).
    """
    g = build_networkx(dag)
    confidences = {n.id: n.confidence for n in dag.nodes}
    removed: list[AssumptionEdge] = []
    while True:
        try:
            cycle = nx.find_cycle(g, orientation="original")
        except nx.NetworkXNoCycle:
            break
        # cycle is a list of (u, v, key/orientation) tuples; pick the edge whose
        # source has the lowest confidence to drop.
        worst = min(cycle, key=lambda e: confidences.get(e[0], 0.0))
        u, v = worst[0], worst[1]
        g.remove_edge(u, v)
        removed.append(AssumptionEdge(source=u, target=v))
    if not removed:
        return dag, removed
    surviving = {(e.source, e.target) for e in dag.edges} - {(r.source, r.target) for r in removed}
    cleaned_edges = [e for e in dag.edges if (e.source, e.target) in surviving]
    return dag.model_copy(update={"edges": cleaned_edges}), removed


def ancestors_of_steps(dag: AssumptionDAG, step_ids: Iterable[int]) -> list[AssumptionNode]:
    """Return every assumption node that is at or above any of the given trajectory
    steps in dependency order. The candidate set for posterior attribution.
    """
    step_set = set(step_ids)
    g = build_networkx(dag)
    seed_ids = {n.id for n in dag.nodes if n.step_id in step_set}
    ancestor_ids: set[str] = set(seed_ids)
    for sid in seed_ids:
        ancestor_ids |= nx.ancestors(g, sid)
    if dag.final_decision_node:
        ancestor_ids.add(dag.final_decision_node)
    by_id = {n.id: n for n in dag.nodes}
    return [by_id[i] for i in ancestor_ids if i in by_id]


def descendants_of_node(dag: AssumptionDAG, node_id: str) -> list[AssumptionNode]:
    """Nodes downstream of `node_id` (excluding the node itself)."""
    g = build_networkx(dag)
    desc_ids = nx.descendants(g, node_id) if node_id in g else set()
    by_id = {n.id: n for n in dag.nodes}
    return [by_id[i] for i in desc_ids if i in by_id]


def candidate_nodes_for_violations(
    dag: AssumptionDAG, violations: list[ViolationEvent]
) -> list[AssumptionNode]:
    return ancestors_of_steps(dag, [v.step_id for v in violations])


def topological_order(dag: AssumptionDAG) -> list[str]:
    return list(nx.topological_sort(build_networkx(dag)))


def to_json(dag: AssumptionDAG) -> dict[str, Any]:
    return dag.model_dump(mode="json")


def from_json(data: dict[str, Any]) -> AssumptionDAG:
    return AssumptionDAG.model_validate(data)
