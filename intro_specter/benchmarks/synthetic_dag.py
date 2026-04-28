"""Tier-C synthetic Assumption-DAG benchmark.

The plan PDF says: "controlled ground truth for faulty nodes, graph depth,
dependency edges, and repair cost". This module generates a meal-planning
domain where each example has a deterministic computation graph, a known
fault-injection point, and a deterministic re-execution function — so the
attribution and repair components can be evaluated without any LLM calls.

Why meal-planning? It produces clean hard-constraint violations (a "vegan"
user asked to eat cheese) that the rule-based verifier can detect with
keyword matching, which keeps the synthetic Tier-C tier truly LLM-free.
"""

from __future__ import annotations

import random
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

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
# Meal-planning domain
# ---------------------------------------------------------------------------

DIETARY_CLASSES = {
    # All entries must have a non-empty `banned` list — otherwise no hard
    # constraint exists and fault injection has nothing to violate. (Omnivore
    # was dropped for this reason.)
    "vegan": {
        "banned": ["cheese", "milk", "yogurt", "butter", "egg", "chicken", "beef", "pork", "fish"],
        "allowed_dishes": ["lentil curry", "tofu stir-fry", "vegetable risotto", "chickpea salad"],
    },
    "vegetarian": {
        "banned": ["chicken", "beef", "pork", "fish", "shrimp"],
        "allowed_dishes": ["paneer curry", "vegetable lasagna", "mushroom risotto", "halloumi salad"],
    },
    "pescatarian": {
        "banned": ["chicken", "beef", "pork"],
        "allowed_dishes": ["grilled salmon", "tuna salad", "shrimp tacos", "fish curry"],
    },
}

BUDGET_TIERS = ["low", "medium", "high"]
CUISINES = ["italian", "indian", "thai", "japanese", "mexican"]
LOCATIONS = ["home", "downtown", "midtown", "suburbs"]


@dataclass(frozen=True)
class MealPlanFacts:
    """The "ground-truth values" used to deterministically produce a trajectory.

    These are kept out of the prompt; the agent (a deterministic Python
    template) only sees the profile and emits steps in terms of these values.
    """

    dietary_class: str
    budget_tier: str
    cuisine: str
    restaurant: str
    dish: str
    location: str


@dataclass
class MealPlanningDomain:
    seed: int = 0

    def generate_profile(self, rng: random.Random, idx: int) -> tuple[UserProfile, MealPlanFacts]:
        dietary = rng.choice(list(DIETARY_CLASSES.keys()))
        budget = rng.choice(BUDGET_TIERS)
        cuisine = rng.choice(CUISINES)
        location = rng.choice(LOCATIONS)
        restaurant = f"{cuisine.title()} House {rng.randint(1, 50)}"
        dish = rng.choice(DIETARY_CLASSES[dietary]["allowed_dishes"])
        facts = MealPlanFacts(
            dietary_class=dietary,
            budget_tier=budget,
            cuisine=cuisine,
            restaurant=restaurant,
            dish=dish,
            location=location,
        )

        spans = [
            ProfileSpan(
                id="p_diet",
                text=f"User is {dietary}",
                kind="constraint",
                is_hard=True,
                contradicts=DIETARY_CLASSES[dietary]["banned"],
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
        return profile, facts

    def generate_task(self, profile: UserProfile, facts: MealPlanFacts) -> dict[str, Any]:
        return {
            "task_type": "meal_recommendation",
            "prompt": "Recommend a single dish for the user's lunch today.",
        }

    def build_clean_dag(self, task_id: str, facts: MealPlanFacts) -> tuple[Trajectory, AssumptionDAG]:
        """Deterministic 'agent' for the synthetic domain — produces a 6-step
        trajectory and matching DAG with no fault."""
        steps = [
            TrajectoryStep(
                step_id=1,
                kind=StepKind.OBSERVATION,
                text=f"Profile says user is {facts.dietary_class}.",
                reason_summary="read dietary class from profile",
            ),
            TrajectoryStep(
                step_id=2,
                kind=StepKind.OBSERVATION,
                text=f"Profile says user prefers {facts.budget_tier}-budget.",
                reason_summary="read budget from profile",
            ),
            TrajectoryStep(
                step_id=3,
                kind=StepKind.ASSUMPTION,
                text=f"Selected cuisine: {facts.cuisine}.",
                reason_summary="match cuisine to user preference",
            ),
            TrajectoryStep(
                step_id=4,
                kind=StepKind.ASSUMPTION,
                text=f"Selected restaurant: {facts.restaurant}.",
                reason_summary="pick a restaurant in the chosen cuisine",
            ),
            TrajectoryStep(
                step_id=5,
                kind=StepKind.ASSUMPTION,
                text=f"Selected dish: {facts.dish}.",
                reason_summary="pick a dish that fits dietary constraint",
            ),
            TrajectoryStep(
                step_id=6,
                kind=StepKind.OUTPUT,
                text=f"Recommendation: {facts.dish} at {facts.restaurant}.",
                reason_summary="emit final recommendation",
            ),
        ]
        nodes = [
            AssumptionNode(
                id="a1",
                step_id=1,
                assumption=f"The user is {facts.dietary_class}.",
                provenance=Provenance.PROFILE,
                profile_span_ids=["p_diet"],
                confidence=1.0,
                depends_on=[],
            ),
            AssumptionNode(
                id="a2",
                step_id=2,
                assumption=f"The user prefers {facts.budget_tier}-budget options.",
                provenance=Provenance.PROFILE,
                profile_span_ids=["p_budget"],
                confidence=1.0,
                depends_on=[],
            ),
            AssumptionNode(
                id="a3",
                step_id=3,
                assumption=f"The cuisine should be {facts.cuisine}.",
                provenance=Provenance.MODEL_INFERRED,
                profile_span_ids=["p_cuisine"],
                confidence=0.7,
                depends_on=["a1"],
            ),
            AssumptionNode(
                id="a4",
                step_id=4,
                assumption=f"{facts.restaurant} is a good {facts.cuisine} option.",
                provenance=Provenance.TOOL,
                profile_span_ids=[],
                confidence=0.85,
                depends_on=["a3"],
            ),
            AssumptionNode(
                id="a5",
                step_id=5,
                assumption=f"{facts.dish} is suitable for a {facts.dietary_class} user.",
                provenance=Provenance.MODEL_INFERRED,
                profile_span_ids=["p_diet"],
                confidence=0.6,
                depends_on=["a1", "a4"],
            ),
            AssumptionNode(
                id="a6",
                step_id=6,
                assumption=f"Final answer is {facts.dish} at {facts.restaurant}.",
                provenance=Provenance.MODEL_INFERRED,
                profile_span_ids=[],
                confidence=0.9,
                depends_on=["a5"],
            ),
        ]
        edges = [
            AssumptionEdge(source="a1", target="a3", type=EdgeType.SUPPORTS),
            AssumptionEdge(source="a3", target="a4", type=EdgeType.SUPPORTS),
            AssumptionEdge(source="a1", target="a5", type=EdgeType.SUPPORTS),
            AssumptionEdge(source="a4", target="a5", type=EdgeType.SUPPORTS),
            AssumptionEdge(source="a5", target="a6", type=EdgeType.SUPPORTS),
        ]
        traj = Trajectory(
            task_id=task_id,
            steps=steps,
            final_output=f"Recommendation: {facts.dish} at {facts.restaurant}.",
        )
        dag = AssumptionDAG(task_id=task_id, nodes=nodes, edges=edges, final_decision_node="a6")
        return traj, dag

    def inject_fault(
        self,
        rng: random.Random,
        traj: Trajectory,
        dag: AssumptionDAG,
        facts: MealPlanFacts,
    ) -> tuple[Trajectory, AssumptionDAG, str, MealPlanFacts]:
        """Pick one node and corrupt it so the final output violates the dietary
        hard constraint. Returns (faulty_traj, faulty_dag, fault_node_id,
        gold_corrected_facts).
        """
        # We bias toward the dietary-relevant nodes because those are the only
        # ones that produce a hard-constraint violation when corrupted.
        candidates = ["a1", "a3", "a5"]
        fault_node_id = rng.choice(candidates)

        # Choose a "wrong" dish that contains a banned ingredient for the user's
        # actual dietary class.
        banned_options = {
            "vegan": "cheese pizza",
            "vegetarian": "chicken curry",
            "pescatarian": "beef stew",
        }
        wrong_dish = banned_options[facts.dietary_class]

        new_steps = list(traj.steps)
        new_nodes = [n.model_copy(deep=True) for n in dag.nodes]

        if fault_node_id == "a1":
            # Misread the profile dietary class.
            wrong_class = next(c for c in DIETARY_CLASSES if c != facts.dietary_class)
            for n in new_nodes:
                if n.id == "a1":
                    n.assumption = f"The user is {wrong_class}."
                    n.provenance = Provenance.MODEL_INFERRED
                    n.confidence = 0.6
            new_steps[0] = new_steps[0].model_copy(
                update={"text": f"Profile says user is {wrong_class}."}
            )
            for n in new_nodes:
                if n.id == "a5":
                    n.assumption = f"{wrong_dish} is suitable for a {wrong_class} user."
                    n.confidence = 0.5
            new_steps[4] = new_steps[4].model_copy(update={"text": f"Selected dish: {wrong_dish}."})
            new_steps[5] = new_steps[5].model_copy(
                update={"text": f"Recommendation: {wrong_dish} at {facts.restaurant}."}
            )
            for n in new_nodes:
                if n.id == "a6":
                    n.assumption = f"Final answer is {wrong_dish} at {facts.restaurant}."
            final_output = f"Recommendation: {wrong_dish} at {facts.restaurant}."

        elif fault_node_id == "a3":
            wrong_cuisine = next(c for c in CUISINES if c != facts.cuisine)
            for n in new_nodes:
                if n.id == "a3":
                    n.assumption = f"The cuisine should be {wrong_cuisine}."
                    n.confidence = 0.5
            new_steps[2] = new_steps[2].model_copy(update={"text": f"Selected cuisine: {wrong_cuisine}."})
            for n in new_nodes:
                if n.id == "a5":
                    n.assumption = f"{wrong_dish} is the best {wrong_cuisine} pick."
                    n.confidence = 0.4
            new_steps[4] = new_steps[4].model_copy(update={"text": f"Selected dish: {wrong_dish}."})
            new_steps[5] = new_steps[5].model_copy(
                update={"text": f"Recommendation: {wrong_dish} at {facts.restaurant}."}
            )
            final_output = f"Recommendation: {wrong_dish} at {facts.restaurant}."

        else:  # a5 — the dish-suitability assumption itself is wrong.
            for n in new_nodes:
                if n.id == "a5":
                    n.assumption = (
                        f"{wrong_dish} is suitable for a {facts.dietary_class} user."
                    )
                    n.confidence = 0.45
            new_steps[4] = new_steps[4].model_copy(update={"text": f"Selected dish: {wrong_dish}."})
            new_steps[5] = new_steps[5].model_copy(
                update={"text": f"Recommendation: {wrong_dish} at {facts.restaurant}."}
            )
            final_output = f"Recommendation: {wrong_dish} at {facts.restaurant}."

        new_traj = Trajectory(task_id=traj.task_id, steps=new_steps, final_output=final_output)
        new_dag = AssumptionDAG(
            task_id=dag.task_id, nodes=new_nodes, edges=dag.edges, final_decision_node=dag.final_decision_node
        )
        return new_traj, new_dag, fault_node_id, facts

    # ----- helpers used by the rule-based sampler / repair callable ----------

    def make_swap_fn(
        self, gold_facts: MealPlanFacts
    ):  # type: ignore[no-untyped-def]
        """Return a swap function that proposes a counterfactual repair restoring
        the gold-correct value at any candidate node."""
        node_repairs = {
            "a1": (
                f"The user is {gold_facts.dietary_class}.",
                ["a1", "a5", "a6"],
            ),
            "a3": (
                f"The cuisine should be {gold_facts.cuisine}.",
                ["a3", "a4", "a5", "a6"],
            ),
            "a5": (
                f"{gold_facts.dish} is suitable for a {gold_facts.dietary_class} user.",
                ["a5", "a6"],
            ),
        }

        def swap(node: AssumptionNode) -> CounterfactualRepair | None:
            entry = node_repairs.get(node.id)
            if entry is None:
                return None
            new_assumption, rerun = entry
            return CounterfactualRepair(
                repair_id=f"r_{node.id}",
                new_assumption=new_assumption,
                nodes_to_rerun=rerun,
                repair_instruction=f"Replace assumption {node.id} with the gold value and rerun.",
                expected_violation_removed=True,
                risk_notes="rule-based oracle swap",
            )

        return swap

    def make_evaluator(self, gold_facts: MealPlanFacts):  # type: ignore[no-untyped-def]
        """A swap removes the violation iff the resulting final output uses the
        gold dish/cuisine — i.e., iff the swap was applied to the actual
        fault-location."""

        def evaluator(
            repair: CounterfactualRepair, trajectory: Trajectory, violation: ViolationEvent
        ) -> bool:
            text = repair.new_assumption.lower()
            if gold_facts.dietary_class in text:
                return True
            if gold_facts.cuisine in text:
                return True
            if gold_facts.dish.lower() in text:
                return True
            return False

        return evaluator

    def make_rerun_fn(self, gold_facts: MealPlanFacts):  # type: ignore[no-untyped-def]
        """Return a `rerun_fn` that re-executes the trajectory deterministically
        from any fault point onward, using the gold-correct values."""
        clean_steps_by_id = {
            1: TrajectoryStep(
                step_id=1,
                kind=StepKind.OBSERVATION,
                text=f"Profile says user is {gold_facts.dietary_class}.",
                reason_summary="re-read dietary class from profile",
            ),
            2: TrajectoryStep(
                step_id=2,
                kind=StepKind.OBSERVATION,
                text=f"Profile says user prefers {gold_facts.budget_tier}-budget.",
                reason_summary="re-read budget from profile",
            ),
            3: TrajectoryStep(
                step_id=3,
                kind=StepKind.ASSUMPTION,
                text=f"Selected cuisine: {gold_facts.cuisine}.",
                reason_summary="match cuisine to user preference",
            ),
            4: TrajectoryStep(
                step_id=4,
                kind=StepKind.ASSUMPTION,
                text=f"Selected restaurant: {gold_facts.restaurant}.",
                reason_summary="pick a restaurant in the chosen cuisine",
            ),
            5: TrajectoryStep(
                step_id=5,
                kind=StepKind.ASSUMPTION,
                text=f"Selected dish: {gold_facts.dish}.",
                reason_summary="pick a dish that fits dietary constraint",
            ),
            6: TrajectoryStep(
                step_id=6,
                kind=StepKind.OUTPUT,
                text=f"Recommendation: {gold_facts.dish} at {gold_facts.restaurant}.",
                reason_summary="emit final recommendation",
            ),
        }
        final_output = f"Recommendation: {gold_facts.dish} at {gold_facts.restaurant}."

        def rerun(
            valid_prefix: list[TrajectoryStep],
            fault_node: AssumptionNode,
            dag: AssumptionDAG,
        ) -> tuple[list[TrajectoryStep], str | None]:
            prefix_ids = {s.step_id for s in valid_prefix}
            new_steps = [
                clean_steps_by_id[i]
                for i in sorted(clean_steps_by_id)
                if i not in prefix_ids
            ]
            return new_steps, final_output

        return rerun

    def make_regenerate_fn(self, gold_facts: MealPlanFacts):  # type: ignore[no-untyped-def]
        """Full-regeneration baseline always produces the clean trajectory. Costs
        ~600 'tokens' (6 steps × 100) so that token comparisons against selective
        repair are meaningful in the synthetic tier."""
        traj, _ = self.build_clean_dag(task_id="regen", facts=gold_facts)

        def regenerate(profile: UserProfile, task: dict[str, Any]) -> tuple[Trajectory, int, int]:
            return traj, 600, 200

        return regenerate


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------


@dataclass
class SyntheticDAGBenchmark:
    n_examples: int = 100
    seed: int = 0
    domain: MealPlanningDomain = field(default_factory=MealPlanningDomain)
    name: str = "synthetic_dag"

    def __len__(self) -> int:
        return self.n_examples

    def __iter__(self) -> Iterator[BenchmarkExample]:
        for i in range(self.n_examples):
            yield self._build_example(i)

    def _build_example(self, idx: int) -> BenchmarkExample:
        rng = random.Random(self.seed * 1_000_003 + idx)
        profile, facts = self.domain.generate_profile(rng, idx)
        task = self.domain.generate_task(profile, facts)
        task_id = f"synthetic_dag_{idx:05d}"
        clean_traj, clean_dag = self.domain.build_clean_dag(task_id, facts)
        faulty_traj, faulty_dag, fault_node_id, gold_facts = self.domain.inject_fault(
            rng, clean_traj, clean_dag, facts
        )
        # The "gold corrected" final output is what the trajectory would have been
        # without the fault — recomputed against the (possibly shifted) gold_facts.
        gold_traj, _ = self.domain.build_clean_dag(task_id=task_id, facts=gold_facts)
        gold = GoldLabels(
            success=False,
            fault_node_id=fault_node_id,
            correct_final_output=gold_traj.final_output,
        )
        rules = [hard_constraint_keyword_rule]
        return BenchmarkExample(
            task_id=task_id,
            dataset=self.name,
            profile=profile,
            task=task,
            trajectory=faulty_traj,
            dag=faulty_dag,
            gold=gold,
            rules=rules,
            swap_fn=self.domain.make_swap_fn(gold_facts),
            evaluator=self.domain.make_evaluator(gold_facts),
            rerun_fn=self.domain.make_rerun_fn(gold_facts),
            regenerate_fn=self.domain.make_regenerate_fn(gold_facts),
        )


# Re-export some types used by tests / runner.
__all__ = [
    "DIETARY_CLASSES",
    "MealPlanFacts",
    "MealPlanningDomain",
    "SyntheticDAGBenchmark",
    "NodeStatus",
    "Severity",
]
