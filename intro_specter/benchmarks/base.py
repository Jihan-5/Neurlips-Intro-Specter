"""Benchmark interface.

Every benchmark yields `BenchmarkExample`s — the unified profile-grounded
trajectory format from the plan PDF's Dataset Construction section. Each example
also exposes the plumbing that selective-repair experiments need:

* a list of deterministic ``rules`` for the rule-based verifier
* a ``swap_fn`` that proposes counterfactual repairs for the rule-based sampler
* an ``evaluator`` that says whether a swap removes the violation
* a ``rerun_fn`` for re-executing the downstream subgraph after repair
* a ``regenerate_fn`` for the full-regeneration baseline

Natural benchmarks (PFQABench, TravelPlanner+, ...) supply LLM-based versions of
these but use the same dataclass.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any, Protocol

from ..attribution import RepairTrial
from ..repair import rerun_downstream_subgraph_callable
from ..schemas import (
    AssumptionDAG,
    AssumptionNode,
    CounterfactualRepair,
    GoldLabels,
    Trajectory,
    TrajectoryStep,
    UserProfile,
    ViolationEvent,
)
from ..verifier import RuleFn

SwapFn = Callable[[AssumptionNode], CounterfactualRepair | None]
EvaluatorFn = Callable[[CounterfactualRepair, Trajectory, ViolationEvent], bool]
RerunFn = Callable[
    [list[TrajectoryStep], AssumptionNode, AssumptionDAG],
    tuple[list[TrajectoryStep], str | None],
]
RegenerateFn = Callable[[UserProfile, dict[str, Any]], tuple[Trajectory, int, int]]


@dataclass
class BenchmarkExample:
    task_id: str
    dataset: str
    profile: UserProfile
    task: dict[str, Any]
    trajectory: Trajectory
    dag: AssumptionDAG
    gold: GoldLabels
    rules: list[RuleFn] = field(default_factory=list)
    swap_fn: SwapFn | None = None
    evaluator: EvaluatorFn | None = None
    rerun_fn: RerunFn | None = None
    regenerate_fn: RegenerateFn | None = None

    def passthrough_rerun(self, fault_node_id: str) -> Trajectory:
        if self.rerun_fn is None:
            raise ValueError("benchmark example has no rerun_fn")
        return rerun_downstream_subgraph_callable(
            trajectory=self.trajectory,
            dag=self.dag,
            fault_node_id=fault_node_id,
            rerun_fn=self.rerun_fn,
        )


class Benchmark(Protocol):
    name: str

    def __iter__(self) -> Iterator[BenchmarkExample]: ...

    def __len__(self) -> int: ...
