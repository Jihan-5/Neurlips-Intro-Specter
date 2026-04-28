"""DAG operations: ancestors, descendants, cycle removal, JSON round-trip."""

from __future__ import annotations

import pytest

from intro_specter.dag import (
    ancestors_of_steps,
    build_networkx,
    descendants_of_node,
    remove_cycles,
)
from intro_specter.schemas import (
    AssumptionDAG,
    AssumptionEdge,
    AssumptionNode,
    EdgeType,
    Provenance,
)


def _node(id_: str, step_id: int, *, conf: float = 0.7, depends_on: list[str] | None = None) -> AssumptionNode:
    return AssumptionNode(
        id=id_,
        step_id=step_id,
        assumption=f"assumption {id_}",
        provenance=Provenance.MODEL_INFERRED,
        confidence=conf,
        depends_on=depends_on or [],
    )


def test_ancestors_includes_seed_and_final_decision_node() -> None:
    nodes = [_node("a1", 1), _node("a2", 2, depends_on=["a1"]), _node("a3", 3, depends_on=["a2"])]
    edges = [
        AssumptionEdge(source="a1", target="a2", type=EdgeType.SUPPORTS),
        AssumptionEdge(source="a2", target="a3", type=EdgeType.SUPPORTS),
    ]
    dag = AssumptionDAG(task_id="t", nodes=nodes, edges=edges, final_decision_node="a3")
    res = ancestors_of_steps(dag, [3])
    ids = {n.id for n in res}
    assert ids == {"a1", "a2", "a3"}


def test_descendants_excludes_self() -> None:
    nodes = [_node("a1", 1), _node("a2", 2, depends_on=["a1"]), _node("a3", 3, depends_on=["a2"])]
    edges = [
        AssumptionEdge(source="a1", target="a2"),
        AssumptionEdge(source="a2", target="a3"),
    ]
    dag = AssumptionDAG(task_id="t", nodes=nodes, edges=edges)
    desc = descendants_of_node(dag, "a1")
    assert {n.id for n in desc} == {"a2", "a3"}


def test_cycle_removal_drops_lowest_confidence_edge() -> None:
    # a1 -> a2 -> a3 -> a1 (cycle). a3 has the lowest confidence.
    nodes = [
        _node("a1", 1, conf=0.9),
        _node("a2", 2, conf=0.8),
        _node("a3", 3, conf=0.2),
    ]
    edges = [
        AssumptionEdge(source="a1", target="a2"),
        AssumptionEdge(source="a2", target="a3"),
        AssumptionEdge(source="a3", target="a1"),
    ]
    dag = AssumptionDAG(task_id="t", nodes=nodes, edges=edges)
    cleaned, removed = remove_cycles(dag)
    assert len(removed) == 1
    # The edge sourced at the lowest-confidence node (a3) should be the one dropped.
    assert removed[0].source == "a3"
    # And the cleaned graph must be acyclic.
    g = build_networkx(cleaned)
    with pytest.raises(Exception):
        # find_cycle raises NetworkXNoCycle if absent — bail out positively.
        import networkx as nx

        nx.find_cycle(g, orientation="original")


def test_dag_validator_rejects_dangling_edges() -> None:
    nodes = [_node("a1", 1)]
    edges = [AssumptionEdge(source="a1", target="missing")]
    with pytest.raises(Exception):
        AssumptionDAG(task_id="t", nodes=nodes, edges=edges)
