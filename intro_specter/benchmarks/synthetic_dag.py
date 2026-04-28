"""Tier-C synthetic Assumption-DAG benchmark — two modes.

The plan PDF wants "controlled ground truth for faulty nodes, graph depth,
dependency edges, and repair cost". The user requires the synthetic benchmark
to support **two modes** so the attribution metric and the cost-efficiency
metric are not conflated:

* ``single_fault`` — the corrupted node is a ``manual`` node whose value is
  *not* re-derivable from upstream. Re-executing from any other ancestor leaves
  the corrupted text in place. Only swapping at the actual fault node removes
  the violation. Used to evaluate **attribution accuracy** (top-1 / top-3 /
  MRR / earliest-fault distance).

* ``multi_valid`` — the corrupted node is a ``function`` node whose faulty value
  propagates through downstream compute. Multiple swap points produce a clean
  trajectory. Used to evaluate **cost-efficiency**: the system's job is to
  pick a *good* repair point under an explicit cost objective, not to identify
  a unique cause.

Each example also belongs to one of three deterministic **splits**:
``train`` / ``val`` / ``test`` (60 / 20 / 20 partition by index). Validation
is for tuning ``tau_abstain`` and other hyperparameters; final headline numbers
must come from ``test``.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

from ..schemas import (
    AssumptionDAG,
    AssumptionEdge,
    AssumptionNode,
    CounterfactualRepair,
    EdgeType,
    GoldLabels,
    NodeStatus,
    ProfileSpan,
    Provenance,
    Severity,
    StepKind,
    Trajectory,
    TrajectoryStep,
    UserProfile,
    ViolationEvent,
)
from ..verifier import hard_constraint_keyword_rule
from .base import BenchmarkExample

# ---------------------------------------------------------------------------
# Meal-planning domain content
# ---------------------------------------------------------------------------

# Only dietary classes whose `banned` list can actually flag a fault. This is
# why "omnivore" was dropped: with no hard constraint, fault injection has
# nothing to violate.
USER_DIETARY_CLASSES = ["vegan", "vegetarian", "pescatarian"]

# Banned substrings that hard-flag a profile violation when seen in trajectory
# text. Each list is the keyword set for a profile span with `is_hard=True`.
DIETARY_BANNED: dict[str, list[str]] = {
    "vegan": [
        "cheese", "milk", "butter", "egg", "yogurt",
        "chicken", "beef", "pork", "fish", "salmon", "shrimp", "halloumi", "paneer",
    ],
    "vegetarian": ["chicken", "beef", "pork", "fish", "salmon", "shrimp"],
    "pescatarian": ["chicken", "beef", "pork"],
}

# Dish picked by the agent given a (potentially-faulty) dietary class. Each
# string is chosen so the dish name itself either contains banned ingredients
# (when the wrong dietary is read) or is fully neutral (when the correct one
# is read). Dish strings are lowercase so the keyword rule matches without
# case folding.
DISH_FOR_DIETARY: dict[str, str] = {
    "vegan": "lentil curry",
    "vegetarian": "halloumi cheese salad",
    "pescatarian": "grilled salmon",
    "carnivore": "beef burger",
}

# When injecting a fault on a vegan user, we pick from these as the wrong
# dietary the agent (mistakenly) reads. Each choice produces a dish containing
# at least one banned substring for the actual user dietary.
FAULT_DIETARY_OPTIONS: dict[str, list[str]] = {
    "vegan": ["vegetarian", "pescatarian", "carnivore"],
    "vegetarian": ["pescatarian", "carnivore"],
    "pescatarian": ["carnivore"],
}

# Direct override dish used in single_fault mode. Always banned for the user.
WRONG_DISH_FOR_DIETARY: dict[str, str] = {
    "vegan": "halloumi cheese salad",
    "vegetarian": "grilled salmon",
    "pescatarian": "beef burger",
}

CUISINES = ["italian", "indian", "thai", "japanese", "mexican"]
LOCATIONS = ["home", "downtown", "midtown", "suburbs"]
BUDGET_TIERS = ["low", "medium", "high"]


# ---------------------------------------------------------------------------
# Computation-graph abstraction
# ---------------------------------------------------------------------------


class NodeKind(str, Enum):
    """How a node's value is produced during (re-)execution.

    * ``function``: value is computed deterministically from upstream node
      values via ``compute``. Re-execution re-derives the value.
    * ``manual``: value is "committed to" in the trajectory text. Re-execution
      preserves the prefix value unless the node itself is the swap target.
      This is what makes ``single_fault`` discriminating: a fault at a manual
      node cannot be repaired by swapping any other node.
    """

    FUNCTION = "function"
    MANUAL = "manual"


@dataclass
class _NodeSpec:
    node_id: str
    step_id: int
    kind: NodeKind
    inputs: list[str]            # node ids whose values feed into compute
    provenance: Provenance
    profile_span_ids: list[str]
    confidence: float
    compute: Callable[[dict[str, str], dict[str, str]], str]
    """compute(input_values, profile_facts) -> value"""
    render_step: Callable[[str], str]
    """render_step(value) -> text shown in TrajectoryStep"""
    render_assumption: Callable[[str], str]
    """render_assumption(value) -> text shown on AssumptionNode"""
    step_kind: StepKind = StepKind.ASSUMPTION


@dataclass
class ComputeGraph:
    nodes: list[_NodeSpec]
    edges: list[tuple[str, str]]
    final_node_id: str

    # ----- helpers --------------------------------------------------------

    def by_id(self, node_id: str) -> _NodeSpec:
        for n in self.nodes:
            if n.node_id == node_id:
                return n
        raise KeyError(node_id)

    def topological_order(self) -> list[str]:
        # nodes are constructed in topo order by convention.
        return [n.node_id for n in self.nodes]

    def downstream(self, node_id: str, *, inclusive: bool = True) -> set[str]:
        """Return all nodes reachable from `node_id` via outgoing edges.

        If `inclusive` is True, includes `node_id` itself.
        """
        adj: dict[str, list[str]] = {n.node_id: [] for n in self.nodes}
        for s, t in self.edges:
            adj[s].append(t)
        seen: set[str] = set()
        stack = [node_id]
        while stack:
            cur = stack.pop()
            for nxt in adj.get(cur, []):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        if inclusive:
            seen.add(node_id)
        return seen

    # ----- rendering ------------------------------------------------------

    def render(
        self,
        *,
        task_id: str,
        profile_facts: dict[str, str],
        overrides: dict[str, str] | None = None,
    ) -> tuple[Trajectory, AssumptionDAG, dict[str, str]]:
        """Compute every node's value and produce a Trajectory + AssumptionDAG.

        ``overrides[node_id] = value`` forces a node to take ``value`` regardless
        of its compute function — used for fault injection.
        """
        overrides = overrides or {}
        values: dict[str, str] = {}
        steps: list[TrajectoryStep] = []
        assumption_nodes: list[AssumptionNode] = []
        for spec in self.nodes:
            if spec.node_id in overrides:
                value = overrides[spec.node_id]
            else:
                value = spec.compute({i: values[i] for i in spec.inputs}, profile_facts)
            values[spec.node_id] = value
            steps.append(
                TrajectoryStep(
                    step_id=spec.step_id,
                    kind=spec.step_kind,
                    text=spec.render_step(value),
                    reason_summary="",
                )
            )
            assumption_nodes.append(
                AssumptionNode(
                    id=spec.node_id,
                    step_id=spec.step_id,
                    assumption=spec.render_assumption(value),
                    provenance=spec.provenance,
                    profile_span_ids=list(spec.profile_span_ids),
                    confidence=spec.confidence,
                    depends_on=list(spec.inputs),
                )
            )
        edges = [AssumptionEdge(source=s, target=t, type=EdgeType.SUPPORTS) for s, t in self.edges]
        dag = AssumptionDAG(
            task_id=task_id, nodes=assumption_nodes, edges=edges, final_decision_node=self.final_node_id
        )
        final_value = values[self.final_node_id]
        traj = Trajectory(task_id=task_id, steps=steps, final_output=final_value)
        return traj, dag, values

    # ----- selective re-execution -----------------------------------------

    def re_execute(
        self,
        *,
        prefix_values: dict[str, str],
        profile_facts: dict[str, str],
        swap_node_id: str,
        swap_value: str,
    ) -> dict[str, str]:
        """Compute new node values after applying a swap at `swap_node_id`.

        Re-execution semantics:
        * Nodes outside the DAG-downstream of the swap retain their prefix value.
        * The swap node itself takes the swap value.
        * Function nodes downstream of the swap are re-derived from upstream
          values (taken from the new value map first, falling back to prefix).
        * **Manual** nodes downstream of the swap retain their prefix value —
          they were committed to in the trajectory and re-execution does not
          regenerate them. This is the key property that makes ``single_fault``
          mode discriminating.
        """
        zone = self.downstream(swap_node_id, inclusive=True)
        new_values: dict[str, str] = {}
        for spec in self.nodes:
            if spec.node_id not in zone:
                new_values[spec.node_id] = prefix_values[spec.node_id]
                continue
            if spec.node_id == swap_node_id:
                new_values[spec.node_id] = swap_value
                continue
            if spec.kind == NodeKind.MANUAL:
                # Preserve prefix text; do not re-derive.
                new_values[spec.node_id] = prefix_values[spec.node_id]
                continue
            input_values = {
                iid: new_values.get(iid, prefix_values[iid]) for iid in spec.inputs
            }
            new_values[spec.node_id] = spec.compute(input_values, profile_facts)
        return new_values

    def values_to_steps(self, values: dict[str, str]) -> tuple[list[TrajectoryStep], str]:
        steps = [
            TrajectoryStep(
                step_id=spec.step_id,
                kind=spec.step_kind,
                text=spec.render_step(values[spec.node_id]),
                reason_summary="",
            )
            for spec in self.nodes
        ]
        return steps, values[self.final_node_id]


# ---------------------------------------------------------------------------
# Domain — meal planning
# ---------------------------------------------------------------------------


@dataclass
class MealPlanningDomain:
    """Generates user profiles, gold facts, fault values, and graph specs."""

    seed: int = 0

    def generate_facts(
        self, rng: random.Random, idx: int
    ) -> tuple[UserProfile, dict[str, str]]:
        dietary = rng.choice(USER_DIETARY_CLASSES)
        budget = rng.choice(BUDGET_TIERS)
        cuisine = rng.choice(CUISINES)
        location = rng.choice(LOCATIONS)
        restaurant = f"{cuisine.title()} House {rng.randint(1, 50)}"
        gold_dish = DISH_FOR_DIETARY[dietary]
        spans = [
            ProfileSpan(
                id="p_diet",
                text=f"User is {dietary}",
                kind="constraint",
                is_hard=True,
                contradicts=list(DIETARY_BANNED[dietary]),
            ),
            ProfileSpan(
                id="p_budget",
                text=f"User prefers {budget}-budget options",
                kind="preference",
                is_hard=False,
            ),
            ProfileSpan(
                id="p_cuisine",
                text=f"User likes {cuisine} cuisine",
                kind="preference",
                is_hard=False,
            ),
            ProfileSpan(
                id="p_location",
                text=f"User is currently in {location}",
                kind="fact",
                is_hard=False,
            ),
        ]
        profile = UserProfile(user_id=f"user_{idx:04d}", spans=spans)
        facts = {
            "dietary": dietary,
            "budget": budget,
            "cuisine": cuisine,
            "restaurant": restaurant,
            "location": location,
            "dish": gold_dish,
        }
        return profile, facts

    # ----- graph specs ----------------------------------------------------

    def graph(self, mode: Literal["single_fault", "multi_valid"]) -> ComputeGraph:
        if mode == "multi_valid":
            return self._multi_valid_graph()
        if mode == "single_fault":
            return self._single_fault_graph()
        raise ValueError(f"unknown synthetic mode {mode!r}")

    def _multi_valid_graph(self) -> ComputeGraph:
        """All nodes are FUNCTION. Fault target = a1 (dietary misread)."""
        return ComputeGraph(
            nodes=[
                _NodeSpec(
                    node_id="a1", step_id=1, kind=NodeKind.FUNCTION,
                    inputs=[], provenance=Provenance.PROFILE,
                    profile_span_ids=["p_diet"], confidence=1.0,
                    compute=lambda inp, f: f["dietary"],
                    render_step=lambda v: f"Profile says user is {v}.",
                    render_assumption=lambda v: f"The user is {v}.",
                    step_kind=StepKind.OBSERVATION,
                ),
                _NodeSpec(
                    node_id="a2", step_id=2, kind=NodeKind.FUNCTION,
                    inputs=[], provenance=Provenance.PROFILE,
                    profile_span_ids=["p_budget"], confidence=1.0,
                    compute=lambda inp, f: f["budget"],
                    render_step=lambda v: f"Profile says user prefers {v}-budget.",
                    render_assumption=lambda v: f"The user prefers {v}-budget options.",
                    step_kind=StepKind.OBSERVATION,
                ),
                _NodeSpec(
                    node_id="a3", step_id=3, kind=NodeKind.FUNCTION,
                    inputs=["a1"], provenance=Provenance.MODEL_INFERRED,
                    profile_span_ids=["p_cuisine"], confidence=0.7,
                    compute=lambda inp, f: f["cuisine"],
                    render_step=lambda v: f"Selected cuisine: {v}.",
                    render_assumption=lambda v: f"The cuisine should be {v}.",
                ),
                _NodeSpec(
                    node_id="a4", step_id=4, kind=NodeKind.FUNCTION,
                    inputs=["a3"], provenance=Provenance.TOOL,
                    profile_span_ids=[], confidence=0.85,
                    compute=lambda inp, f: f["restaurant"],
                    render_step=lambda v: f"Selected restaurant: {v}.",
                    render_assumption=lambda v: f"{v} is a good option for the cuisine.",
                ),
                _NodeSpec(
                    node_id="a5", step_id=5, kind=NodeKind.FUNCTION,
                    inputs=["a1", "a4"], provenance=Provenance.MODEL_INFERRED,
                    profile_span_ids=["p_diet"], confidence=0.6,
                    # The propagation engine: dish is picked from the dietary
                    # *as read in step 1's value*. If that value is faulty, the
                    # dish is wrong (and contains banned substrings).
                    compute=lambda inp, f: DISH_FOR_DIETARY.get(inp["a1"], "lentil curry"),
                    render_step=lambda v: f"Selected dish: {v}.",
                    render_assumption=lambda v: f"{v} is suitable for the user.",
                ),
                _NodeSpec(
                    node_id="a6", step_id=6, kind=NodeKind.FUNCTION,
                    inputs=["a4", "a5"], provenance=Provenance.MODEL_INFERRED,
                    profile_span_ids=[], confidence=0.9,
                    compute=lambda inp, f: f"Recommendation: {inp['a5']} at {inp['a4']}.",
                    render_step=lambda v: v,
                    render_assumption=lambda v: f"Final answer is: {v}",
                    step_kind=StepKind.OUTPUT,
                ),
            ],
            edges=[
                ("a1", "a3"), ("a3", "a4"),
                ("a1", "a5"), ("a4", "a5"),
                ("a4", "a6"), ("a5", "a6"),
            ],
            final_node_id="a6",
        )

    def _single_fault_graph(self) -> ComputeGraph:
        """a5 is MANUAL — its value is committed in the trajectory and not
        re-derivable from upstream. Fault target = a5 (dish itself is wrong)."""
        return ComputeGraph(
            nodes=[
                _NodeSpec(
                    node_id="a1", step_id=1, kind=NodeKind.FUNCTION,
                    inputs=[], provenance=Provenance.PROFILE,
                    profile_span_ids=["p_diet"], confidence=1.0,
                    compute=lambda inp, f: f["dietary"],
                    render_step=lambda v: f"Profile says user is {v}.",
                    render_assumption=lambda v: f"The user is {v}.",
                    step_kind=StepKind.OBSERVATION,
                ),
                _NodeSpec(
                    node_id="a2", step_id=2, kind=NodeKind.FUNCTION,
                    inputs=[], provenance=Provenance.PROFILE,
                    profile_span_ids=["p_budget"], confidence=1.0,
                    compute=lambda inp, f: f["budget"],
                    render_step=lambda v: f"Profile says user prefers {v}-budget.",
                    render_assumption=lambda v: f"The user prefers {v}-budget options.",
                    step_kind=StepKind.OBSERVATION,
                ),
                _NodeSpec(
                    node_id="a3", step_id=3, kind=NodeKind.FUNCTION,
                    inputs=["a1"], provenance=Provenance.MODEL_INFERRED,
                    profile_span_ids=["p_cuisine"], confidence=0.7,
                    compute=lambda inp, f: f["cuisine"],
                    render_step=lambda v: f"Selected cuisine: {v}.",
                    render_assumption=lambda v: f"The cuisine should be {v}.",
                ),
                _NodeSpec(
                    node_id="a4", step_id=4, kind=NodeKind.FUNCTION,
                    inputs=["a3"], provenance=Provenance.TOOL,
                    profile_span_ids=[], confidence=0.85,
                    compute=lambda inp, f: f["restaurant"],
                    render_step=lambda v: f"Selected restaurant: {v}.",
                    render_assumption=lambda v: f"{v} is a good option for the cuisine.",
                ),
                _NodeSpec(
                    node_id="a5", step_id=5, kind=NodeKind.MANUAL,
                    inputs=["a1", "a4"], provenance=Provenance.MODEL_INFERRED,
                    profile_span_ids=["p_diet"], confidence=0.6,
                    # On initial render, the gold dish is used. After fault
                    # injection, an override forces the wrong dish. Re-execution
                    # NEVER recomputes (it's a manual node).
                    compute=lambda inp, f: f["dish"],
                    render_step=lambda v: f"Selected dish: {v}.",
                    render_assumption=lambda v: f"{v} is suitable for the user.",
                ),
                _NodeSpec(
                    node_id="a6", step_id=6, kind=NodeKind.FUNCTION,
                    inputs=["a4", "a5"], provenance=Provenance.MODEL_INFERRED,
                    profile_span_ids=[], confidence=0.9,
                    compute=lambda inp, f: f"Recommendation: {inp['a5']} at {inp['a4']}.",
                    render_step=lambda v: v,
                    render_assumption=lambda v: f"Final answer is: {v}",
                    step_kind=StepKind.OUTPUT,
                ),
            ],
            edges=[
                ("a1", "a3"), ("a3", "a4"),
                ("a1", "a5"), ("a4", "a5"),
                ("a4", "a6"), ("a5", "a6"),
            ],
            final_node_id="a6",
        )

    # ----- fault injection ------------------------------------------------

    def fault_target(self, mode: Literal["single_fault", "multi_valid"]) -> str:
        return "a5" if mode == "single_fault" else "a1"

    def fault_value(
        self,
        mode: Literal["single_fault", "multi_valid"],
        gold_facts: dict[str, str],
        rng: random.Random,
    ) -> str:
        if mode == "single_fault":
            return WRONG_DISH_FOR_DIETARY[gold_facts["dietary"]]
        return rng.choice(FAULT_DIETARY_OPTIONS[gold_facts["dietary"]])

    # ----- swap / evaluator / rerun closures ------------------------------

    def make_swap_fn(
        self,
        graph: ComputeGraph,
        gold_values: dict[str, str],
    ) -> Callable[[AssumptionNode], CounterfactualRepair | None]:
        """Rule-based swap: any candidate node's repair = the gold-correct value
        for that node. The evaluator is what decides whether the swap actually
        removes the violation; this function just proposes the repair text.
        """

        def swap(node: AssumptionNode) -> CounterfactualRepair | None:
            if node.id not in {n.node_id for n in graph.nodes}:
                return None
            gold_value = gold_values[node.id]
            spec = graph.by_id(node.id)
            return CounterfactualRepair(
                repair_id=f"r_{node.id}",
                new_assumption=spec.render_assumption(gold_value),
                nodes_to_rerun=sorted(graph.downstream(node.id)),
                repair_instruction=f"Replace {node.id} with the gold value and re-execute downstream.",
                expected_violation_removed=True,  # the simulator decides reality
                risk_notes="rule-based oracle proposes gold value; evaluator simulates.",
            )

        return swap

    def make_evaluator(
        self,
        *,
        graph: ComputeGraph,
        profile: UserProfile,
        profile_facts: dict[str, str],
        prefix_values: dict[str, str],
        gold_values: dict[str, str],
    ) -> Callable[[CounterfactualRepair, Trajectory, ViolationEvent], bool]:
        """Simulate `swap + re_execute + verifier`. The repair's
        ``new_assumption`` doesn't carry the swap *value* directly (it carries
        rendered text), so we map the repair back to its candidate node by
        ``repair_id == "r_<node_id>"`` and use ``gold_values[node_id]`` as the
        swap value. (Both LLM and rule-based samplers can re-use this contract.)
        """

        def evaluator(
            repair: CounterfactualRepair, trajectory: Trajectory, violation: ViolationEvent
        ) -> bool:
            node_id = repair.repair_id.removeprefix("r_")
            if node_id not in {n.node_id for n in graph.nodes}:
                return False
            new_values = graph.re_execute(
                prefix_values=prefix_values,
                profile_facts=profile_facts,
                swap_node_id=node_id,
                swap_value=gold_values[node_id],
            )
            return _verifier_passes(graph, profile, new_values)

        return evaluator

    def make_rerun_fn(
        self,
        *,
        graph: ComputeGraph,
        profile_facts: dict[str, str],
        prefix_values: dict[str, str],
        gold_values: dict[str, str],
    ) -> Callable[
        [list[TrajectoryStep], AssumptionNode, AssumptionDAG],
        tuple[list[TrajectoryStep], str | None],
    ]:
        """Rerun closure used by `rerun_downstream_subgraph_callable`. The
        pipeline tells us which fault node was chosen; we rerun the graph with
        the gold value at that node and return the resulting (downstream-only)
        steps + final output. The pipeline supplies the prefix; we therefore
        only emit the steps that lie inside the swap zone."""

        def rerun(
            valid_prefix: list[TrajectoryStep],
            fault_node: AssumptionNode,
            dag: AssumptionDAG,
        ) -> tuple[list[TrajectoryStep], str | None]:
            new_values = graph.re_execute(
                prefix_values=prefix_values,
                profile_facts=profile_facts,
                swap_node_id=fault_node.id,
                swap_value=gold_values[fault_node.id],
            )
            zone = graph.downstream(fault_node.id, inclusive=True)
            zone_step_ids = {graph.by_id(nid).step_id for nid in zone}
            prefix_step_ids = {s.step_id for s in valid_prefix}
            new_steps_all, _final = graph.values_to_steps(new_values)
            new_steps = [
                s for s in new_steps_all
                if s.step_id in zone_step_ids and s.step_id not in prefix_step_ids
            ]
            return new_steps, new_values[graph.final_node_id]

        return rerun

    def make_regenerate_fn(
        self,
        *,
        graph: ComputeGraph,
        profile_facts: dict[str, str],
    ) -> Callable[[UserProfile, dict[str, Any]], tuple[Trajectory, int, int]]:
        """Full-regeneration baseline: produce a fresh clean trajectory. Token
        counts approximate the cost of re-running the agent end-to-end so
        token-savings comparisons against selective repair are non-trivial."""

        def regenerate(profile: UserProfile, task: dict[str, Any]) -> tuple[Trajectory, int, int]:
            traj, _dag, _values = graph.render(
                task_id=task.get("task_id", "regen"), profile_facts=profile_facts
            )
            tokens_per_step = 100  # rough proxy used in cost-savings figures
            n_steps = len(graph.nodes)
            return traj, n_steps * tokens_per_step, n_steps * (tokens_per_step // 3)

        return regenerate


# ---------------------------------------------------------------------------
# Verifier helper used by the evaluator
# ---------------------------------------------------------------------------


def _verifier_passes(
    graph: ComputeGraph, profile: UserProfile, values: dict[str, str]
) -> bool:
    steps, final_output = graph.values_to_steps(values)
    fake_traj = Trajectory(task_id="sim", steps=steps, final_output=final_output)
    violations = hard_constraint_keyword_rule(profile, {}, fake_traj, final_output)
    return len(violations) == 0


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------


Split = Literal["train", "val", "test", "all"]


@dataclass
class SyntheticDAGBenchmark:
    n_examples: int = 100
    seed: int = 0
    mode: Literal["single_fault", "multi_valid"] = "single_fault"
    split: Split = "all"
    domain: MealPlanningDomain = field(default_factory=MealPlanningDomain)
    train_frac: float = 0.6
    val_frac: float = 0.2

    @property
    def name(self) -> str:
        return f"synthetic_dag_{self.mode}"

    def __len__(self) -> int:
        return len(self._indices())

    def __iter__(self) -> Iterator[BenchmarkExample]:
        for idx in self._indices():
            yield self._build_example(idx)

    # ----- splits ---------------------------------------------------------

    def _indices(self) -> list[int]:
        n = self.n_examples
        train_end = int(n * self.train_frac)
        val_end = int(n * (self.train_frac + self.val_frac))
        if self.split == "train":
            return list(range(0, train_end))
        if self.split == "val":
            return list(range(train_end, val_end))
        if self.split == "test":
            return list(range(val_end, n))
        return list(range(n))

    def split_of(self, idx: int) -> Split:
        n = self.n_examples
        train_end = int(n * self.train_frac)
        val_end = int(n * (self.train_frac + self.val_frac))
        if idx < train_end:
            return "train"
        if idx < val_end:
            return "val"
        return "test"

    # ----- example construction ------------------------------------------

    def _build_example(self, idx: int) -> BenchmarkExample:
        rng = random.Random(self.seed * 1_000_003 + idx)
        profile, gold_facts = self.domain.generate_facts(rng, idx)
        graph = self.domain.graph(self.mode)
        task_id = f"{self.name}_{idx:05d}"
        # Render the clean (gold) trajectory + node values.
        clean_traj, clean_dag, gold_values = graph.render(
            task_id=task_id, profile_facts=gold_facts
        )
        # Inject one fault.
        fault_node_id = self.domain.fault_target(self.mode)
        fault_value = self.domain.fault_value(self.mode, gold_facts, rng)
        # Override the fault node and let downstream FUNCTION nodes re-derive
        # naturally (so that, in multi_valid mode, the propagation produces a
        # banned substring downstream).
        faulty_overrides = {fault_node_id: fault_value}
        # In multi_valid, the propagation through compute is what generates the
        # banned substring at a5; we therefore render with only the fault as
        # override. In single_fault, a5 is MANUAL — the override IS the fault.
        faulty_traj, faulty_dag, faulty_values = graph.render(
            task_id=task_id, profile_facts=gold_facts, overrides=faulty_overrides
        )
        gold = GoldLabels(
            success=False,
            fault_node_id=fault_node_id,
            correct_final_output=clean_traj.final_output,
        )
        rules = [hard_constraint_keyword_rule]
        swap_fn = self.domain.make_swap_fn(graph, gold_values)
        evaluator = self.domain.make_evaluator(
            graph=graph,
            profile=profile,
            profile_facts=gold_facts,
            prefix_values=faulty_values,
            gold_values=gold_values,
        )
        rerun_fn = self.domain.make_rerun_fn(
            graph=graph,
            profile_facts=gold_facts,
            prefix_values=faulty_values,
            gold_values=gold_values,
        )
        regenerate_fn = self.domain.make_regenerate_fn(
            graph=graph, profile_facts=gold_facts
        )
        task = {
            "task_id": task_id,
            "task_type": "meal_recommendation",
            "prompt": "Recommend a single dish for the user's lunch today.",
            "split": self.split_of(idx),
            "mode": self.mode,
        }
        # Gold violations: for the synthetic benchmark the rule-based verifier
        # is the oracle, so we precompute its output on the faulty trajectory
        # for the oracle_detector baseline.
        gold_violations = hard_constraint_keyword_rule(
            profile, task, faulty_traj, faulty_traj.final_output
        )
        return BenchmarkExample(
            task_id=task_id,
            dataset=self.name,
            profile=profile,
            task=task,
            trajectory=faulty_traj,
            dag=faulty_dag,
            gold=gold,
            rules=rules,
            swap_fn=swap_fn,
            evaluator=evaluator,
            rerun_fn=rerun_fn,
            regenerate_fn=regenerate_fn,
            gold_violations=gold_violations,
            split=self.split_of(idx),
        )


__all__ = [
    "ComputeGraph",
    "DIETARY_BANNED",
    "DISH_FOR_DIETARY",
    "MealPlanningDomain",
    "NodeKind",
    "NodeStatus",
    "Severity",
    "SyntheticDAGBenchmark",
    "USER_DIETARY_CLASSES",
    "WRONG_DISH_FOR_DIETARY",
]
