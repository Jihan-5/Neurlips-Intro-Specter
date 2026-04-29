"""ALFWorld-style reconstruction: multi-step household task with profile constraints.

The original ALFWorld (Shridhar et al. 2021) is a long-horizon embodied
text-agent benchmark on TextWorld over the ALFRED household tasks. We don't
spin up the TextWorld stack here (Docker + dependency hell on macOS); the
plan PDF allows a "reconstructed equivalent". This module produces
templated multi-step household tasks (5–7 step plans: find -> pick up ->
navigate -> place) that exercise the same Intro-Specter property:

* Profile-grounded constraints make some destinations forbidden
  ("don't put fragile items on the floor", "user is allergic to nuts;
  don't store food near peanut-containing items").
* The agent's plan can violate the constraint at one of several steps.
* The verifier checks the final-state mentions for banned destinations
  or banned combinations.
* Intro-Specter's job: localise which step's assumption introduced the
  violation and rerun only the downstream subgraph.

This is consistent with our TravelPlanner-Recon shape but with longer
trajectories and constraints over destinations rather than dishes.
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

# ---------------------------------------------------------------------------
# Domain content
# ---------------------------------------------------------------------------

OBJECTS = ["apple", "knife", "ceramic mug", "laptop", "sponge", "kettle", "smartphone", "book"]
LOCATIONS = ["countertop", "cabinet", "fridge", "drawer", "shelf", "floor", "stovetop", "sink"]

FRAGILE = {"ceramic mug", "laptop", "smartphone"}
SHARP = {"knife"}
FOOD_LIKE = {"apple", "kettle"}

# Profile constraint kits: each kit produces (description, banned-substrings).
def _fragile_constraint() -> tuple[str, list[str]]:
    return ("User has a child at home; do not place fragile items on the floor or low shelves.",
            ["floor", "low shelf"])

def _allergy_constraint() -> tuple[str, list[str]]:
    return ("User is severely allergic to peanuts; do not store food near anything containing peanuts.",
            ["peanut", "peanuts", "peanut butter"])

def _accessibility_constraint() -> tuple[str, list[str]]:
    return ("User uses a wheelchair; do not place items on top shelves or above counter height.",
            ["top shelf", "above counter", "high shelf"])

CONSTRAINTS = [_fragile_constraint, _allergy_constraint, _accessibility_constraint]


def _build_profile(rng: random.Random, idx: int) -> tuple[UserProfile, dict[str, Any]]:
    constraint_fn = rng.choice(CONSTRAINTS)
    constraint_text, banned = constraint_fn()
    spans = [
        ProfileSpan(
            id="p_constraint",
            text=constraint_text,
            kind="constraint",
            is_hard=True,
            contradicts=list(banned),
        ),
        ProfileSpan(id="p_room", text=f"User's house has 4 rooms.", kind="fact"),
        ProfileSpan(id="p_pref",
                    text=f"User prefers items kept in the {rng.choice(['kitchen', 'living room'])}.",
                    kind="preference"),
    ]
    profile = UserProfile(user_id=f"alfworld_user_{idx:04d}", spans=spans)
    facts = {
        "constraint_text": constraint_text,
        "banned": banned,
        "object": rng.choice(OBJECTS),
        "destination": rng.choice(LOCATIONS),
    }
    return profile, facts


def _alfworld_rule(facts: dict[str, Any]):
    banned = [b.lower() for b in facts["banned"]]

    def rule(profile, task, trajectory, final_output):
        text = (final_output or "").lower()
        for s in trajectory.steps:
            text += "\n" + (s.text or "").lower()
        out: list[ViolationEvent] = []
        for b in banned:
            if b and b in text:
                out.append(ViolationEvent(
                    violation_id=f"v_alf_{b.replace(' ', '_')}",
                    step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                    violated_profile_span_id="p_constraint",
                    violated_constraint=f"plan mentions {b!r} which violates a profile constraint",
                    trajectory_text=text[:200],
                    severity=Severity.HIGH,
                    explanation=f"profile-banned substring {b!r}",
                ))
                break
        return out

    rule.__name__ = "alfworld_recon_rule"
    return rule


Split = Literal["train", "val", "test", "all"]


@dataclass
class ALFWorldRecon:
    n_examples: int = 100
    seed: int = 0
    split: Split = "all"
    train_frac: float = 0.6
    val_frac: float = 0.2

    @property
    def name(self) -> str:
        return "alfworld_recon"

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
        rng = random.Random(self.seed * 1_000_011 + idx)
        profile, facts = _build_profile(rng, idx)
        task_id = f"alfworld_recon_{idx:05d}"
        prompt = (
            f"Plan a sequence of household actions to put the {facts['object']} into a "
            f"reasonable storage location. Output 5-7 labelled steps "
            f"(navigate, find, pick_up, navigate, place) and a final action "
            f"summary. Respect the user's profile constraints when choosing "
            f"the destination."
        )
        task = {
            "task_id": task_id, "task_type": "alfworld",
            "prompt": prompt, "split": self.split_of(idx), "facts": facts,
        }
        rule = _alfworld_rule(facts)
        gold = GoldLabels(success=None, correct_final_output=None)
        return BenchmarkExample(
            task_id=task_id, dataset=self.name, profile=profile, task=task,
            trajectory=Trajectory(task_id=task_id, steps=[], final_output=None),
            dag=AssumptionDAG(task_id=task_id, nodes=[], edges=[]),
            gold=gold, rules=[rule], split=self.split_of(idx),
        )


__all__ = ["ALFWorldRecon", "OBJECTS", "LOCATIONS", "CONSTRAINTS"]
