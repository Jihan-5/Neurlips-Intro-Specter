"""TravelPlanner+ reconstruction.

The original TravelPlanner+ (Singh et al. 2024, EMNLP Industry Track) wraps
travel-planning tasks with personalized profiles and reports hard-constraint
satisfaction. We don't have a license to redistribute their data; the plan
PDF allows a "TravelPlanner-style" reconstruction.

This module synthesises 1-day itinerary tasks with three hard constraints
(dietary, mobility, budget) plus one soft preference (cuisine). The agent
must produce an itinerary with breakfast / morning_activity / lunch /
afternoon_activity / dinner / hotel slots. The verifier is rule-based:

* Dietary banned-substrings in any meal slot → violation.
* Inaccessible markers in attractions when the profile flags mobility need.
* "Luxury" markers in any slot when the profile budget is "low".

Fault-injection candidates per task: agent misreads dietary, mobility, or
budget. Either the LLM produces a violating itinerary directly, in which case
the verifier fires; or the post-repair pipeline catches the misread
assumption and fixes only the affected slot.
"""

from __future__ import annotations

import random
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Literal

from ..schemas import (
    AssumptionDAG,
    GoldLabels,
    ProfileSpan,
    Severity,
    Trajectory,
    UserProfile,
    ViolationEvent,
)
from .base import BenchmarkExample

DIETARY_CLASSES = ["vegan", "vegetarian", "pescatarian", "omnivore"]
DIETARY_BANNED: dict[str, list[str]] = {
    "vegan": ["cheese", "milk", "butter", "egg", "honey", "chicken", "beef", "pork", "fish", "salmon", "shrimp"],
    "vegetarian": ["chicken", "beef", "pork", "fish", "salmon", "shrimp"],
    "pescatarian": ["chicken", "beef", "pork"],
    "omnivore": [],
}

MOBILITY = ["none", "wheelchair"]
INACCESSIBLE_MARKERS = ["stairs only", "no elevator", "steep climb", "rocky trail", "cliff hike"]

BUDGET_TIERS = ["low", "medium", "high"]
LUXURY_MARKERS = ["five-star", "luxury", "michelin", "premium suite", "rooftop bar"]

DESTINATIONS = ["Tokyo", "Paris", "New York", "Barcelona", "Mumbai", "Cape Town"]
CUISINES = ["italian", "japanese", "indian", "mexican", "french", "thai"]


Split = Literal["train", "val", "test", "all"]


def _build_profile(rng: random.Random, idx: int) -> tuple[UserProfile, dict[str, Any]]:
    diet = rng.choice(DIETARY_CLASSES)
    mob = rng.choice(MOBILITY)
    budget = rng.choice(BUDGET_TIERS)
    cuisine = rng.choice(CUISINES)
    dest = rng.choice(DESTINATIONS)

    spans = [
        ProfileSpan(id="p_diet", text=f"User is {diet}", kind="constraint",
                    is_hard=True, contradicts=list(DIETARY_BANNED.get(diet, []))),
        ProfileSpan(id="p_mobility",
                    text=("User uses a wheelchair" if mob == "wheelchair"
                          else "User has no mobility constraints"),
                    kind="constraint", is_hard=(mob == "wheelchair"),
                    contradicts=list(INACCESSIBLE_MARKERS) if mob == "wheelchair" else []),
        ProfileSpan(id="p_budget", text=f"User prefers {budget}-budget options",
                    kind="constraint", is_hard=(budget == "low"),
                    contradicts=list(LUXURY_MARKERS) if budget == "low" else []),
        ProfileSpan(id="p_cuisine", text=f"User likes {cuisine} cuisine", kind="preference"),
    ]
    profile = UserProfile(user_id=f"travel_user_{idx:04d}", spans=spans)
    facts = {
        "dietary": diet,
        "mobility": mob,
        "budget": budget,
        "cuisine": cuisine,
        "destination": dest,
    }
    return profile, facts


def _itinerary_rule(facts: dict[str, Any]):
    """Rule-based verifier for TravelPlanner-Recon.

    Aggregates hard-constraint violations across dietary, mobility, and budget.
    Each violation cites the specific profile span that was contradicted, so
    Intro-Specter's attribution has a clean detection signal to work with.
    """
    diet = facts["dietary"]
    mob = facts["mobility"]
    budget = facts["budget"]
    diet_banned = [b.lower() for b in DIETARY_BANNED.get(diet, [])]
    inaccess = [m.lower() for m in INACCESSIBLE_MARKERS] if mob == "wheelchair" else []
    luxury = [m.lower() for m in LUXURY_MARKERS] if budget == "low" else []

    def rule(profile, task, trajectory, final_output):
        text = (final_output or "").lower()
        for s in trajectory.steps:
            text += "\n" + (s.text or "").lower()
        out: list[ViolationEvent] = []
        for b in diet_banned:
            if b in text:
                out.append(ViolationEvent(
                    violation_id=f"v_diet_{b}",
                    step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                    violated_profile_span_id="p_diet",
                    violated_constraint=f"itinerary contains {b!r} which violates dietary={diet}",
                    trajectory_text=text[:200],
                    severity=Severity.HIGH,
                    explanation=f"banned substring {b!r}",
                ))
                break
        for m in inaccess:
            if m in text:
                out.append(ViolationEvent(
                    violation_id=f"v_mobility_{m.replace(' ', '_')}",
                    step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                    violated_profile_span_id="p_mobility",
                    violated_constraint=f"itinerary contains {m!r} which is not wheelchair-accessible",
                    trajectory_text=text[:200],
                    severity=Severity.HIGH,
                    explanation=f"inaccessible marker {m!r}",
                ))
                break
        for ll in luxury:
            if ll in text:
                out.append(ViolationEvent(
                    violation_id=f"v_budget_{ll.replace(' ', '_')}",
                    step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                    violated_profile_span_id="p_budget",
                    violated_constraint=f"itinerary contains {ll!r} which exceeds low budget",
                    trajectory_text=text[:200],
                    severity=Severity.HIGH,
                    explanation=f"luxury marker {ll!r}",
                ))
                break
        return out

    rule.__name__ = "travelplanner_recon_rule"
    return rule


@dataclass
class TravelPlannerRecon:
    n_examples: int = 150
    seed: int = 0
    split: Split = "all"
    train_frac: float = 0.6
    val_frac: float = 0.2

    @property
    def name(self) -> str:
        return "travelplanner_recon"

    def __len__(self) -> int:
        return len(self._indices())

    def __iter__(self) -> Iterator[BenchmarkExample]:
        for idx in self._indices():
            yield self._build_example(idx)

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

    def _build_example(self, idx: int) -> BenchmarkExample:
        rng = random.Random(self.seed * 1_000_003 + idx)
        profile, facts = _build_profile(rng, idx)
        task_id = f"travelplanner_recon_{idx:05d}"
        prompt = (
            f"Plan a one-day itinerary for the user in {facts['destination']}. "
            "Produce six labelled slots: breakfast, morning_activity, lunch, "
            "afternoon_activity, dinner, hotel. Each slot should be a single "
            "concrete recommendation. Respect the user's profile constraints."
        )
        task = {
            "task_id": task_id,
            "task_type": "travelplanner",
            "prompt": prompt,
            "split": self.split_of(idx),
            "facts": facts,
        }
        rule = _itinerary_rule(facts)
        gold = GoldLabels(
            success=None,
            correct_final_output=None,  # too many valid itineraries; rule decides success
        )
        return BenchmarkExample(
            task_id=task_id,
            dataset=self.name,
            profile=profile,
            task=task,
            trajectory=Trajectory(task_id=task_id, steps=[], final_output=None),
            dag=AssumptionDAG(task_id=task_id, nodes=[], edges=[]),
            gold=gold,
            rules=[rule],
            split=self.split_of(idx),
        )


__all__ = ["DIETARY_BANNED", "DESTINATIONS", "TravelPlannerRecon"]
