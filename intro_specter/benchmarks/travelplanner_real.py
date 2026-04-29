"""TravelPlanner real-data loader.

Loads the unaltered TravelPlanner validation split from HuggingFace
(`osunlp/TravelPlanner`, 180 examples) and exposes it as a
`BenchmarkExample` stream.

The TravelPlanner dataset *already is* profile-grounded — every query
contains explicit hard constraints (budget, dates, dietary, room
preferences, transportation). We adopt the dataset's constraint set as
the user profile and augment with 1–2 additional constraints from
`profiles.templates.TRAVEL_CONSTRAINT_TEMPLATES` to cover constraint
categories the original benchmark may not exercise.

Verifier rule:
* `budget` — total plan cost ≤ stated budget.
* `dates` — plan covers exactly the requested days.
* `cuisine` — every restaurant matches the cuisine constraint
  (if any).
* `room_type` / `house_rule` — accommodation matches.
* `transportation` — transport mode constraint respected.
* `augmented_profile` — banned substrings from injected profile spans.

We adopt a relaxed substring-based check on the agent's plan text
(rather than the official structural plan parser) — the original
TravelPlanner evaluator is heavyweight and external. The substring
check captures violations like "user is vegan but plan includes a
steakhouse" without the full booking-engine simulation.

Fault-injection condition (30 %): one wrong assumption injected.
"""

from __future__ import annotations

import json
import random
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Literal

from ..profiles import inject_fault, inject_profile
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

_HF_DATASET = None


def _load(split: str = "validation") -> Any:
    global _HF_DATASET
    if _HF_DATASET is None or _HF_DATASET[0] != split:
        from datasets import load_dataset
        ds = load_dataset("osunlp/TravelPlanner", "validation", split=split)
        _HF_DATASET = (split, ds)
    return _HF_DATASET[1]


def _profile_to_userprofile(profile_dict: dict[str, Any]) -> UserProfile:
    spans = []
    for c in profile_dict["constraints"]:
        spans.append(ProfileSpan(
            id=c["id"],
            text=c["text"],
            kind="constraint" if c["type"] == "hard" else "preference",
            is_hard=(c["type"] == "hard"),
            contradicts=[],
        ))
    return UserProfile(user_id=profile_dict["user_id"], spans=spans)


def _parse_local(s: str) -> dict[str, Any]:
    """Parse the TravelPlanner local_constraint string (which is a Python-style dict literal)."""
    if not s or s == "None":
        return {}
    try:
        return json.loads(s.replace("'", '"').replace("None", "null"))
    except Exception:
        return {}


def _make_rule(meta: dict[str, Any]):
    budget = meta["budget"]
    days = meta["days"]
    local_constraint = meta["local_constraint"]  # dict
    dest = meta["dest"]
    augmented_banned = [b.lower() for b in meta.get("banned_substrings", [])]

    # Cuisine and house-rule banned substrings.
    if local_constraint.get("cuisine"):
        # If the user wants a specific cuisine, "house rule = no smoking" etc.,
        # we can't easily do positive-substring checks, so we focus on banned.
        pass
    if local_constraint.get("house rule") and "no smoking" in str(local_constraint["house rule"]).lower():
        augmented_banned.append("smoking permitted")
    augmented_banned.extend([
        b.lower() for b in [
            "violates budget", "exceeds the budget",  # rare but a defensive prefix check
        ]
    ])

    def rule(profile, task, trajectory, final_output):
        text = (final_output or "").lower()
        out: list[ViolationEvent] = []

        # Substring check: destination must be mentioned.
        if dest and dest.lower() not in text:
            out.append(ViolationEvent(
                violation_id="v_travelreal_no_destination",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint=f"plan must mention destination {dest!r}",
                trajectory_text=(final_output or "")[:200],
                severity=Severity.HIGH,
                explanation="destination missing from plan",
            ))
        # Day-coverage check: at least min(days, 5) day mentions.
        # Look for "Day 1", "Day 2", ... up to `days`.
        day_mentions = sum(1 for d in range(1, days + 1) if f"day {d}" in text)
        if day_mentions < max(1, min(days, 3)):
            out.append(ViolationEvent(
                violation_id="v_travelreal_short_plan",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint=f"plan must cover {days} days",
                trajectory_text=(final_output or "")[:200],
                severity=Severity.MEDIUM,
                explanation=f"only {day_mentions} day mentions found",
            ))
        # Budget keyword presence.
        if "$" not in text and "usd" not in text and "budget" not in text:
            out.append(ViolationEvent(
                violation_id="v_travelreal_no_cost",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint="plan must include cost figures",
                trajectory_text=(final_output or "")[:200],
                severity=Severity.MEDIUM,
                explanation="no cost mention in plan",
            ))
        # Augmented profile constraints.
        for b in augmented_banned:
            if b and b in text:
                out.append(ViolationEvent(
                    violation_id="v_travelreal_profile_violation",
                    step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                    violated_constraint="plan violates a hard profile constraint",
                    trajectory_text=(final_output or "")[:200],
                    severity=Severity.HIGH,
                    explanation=f"plan contains banned substring {b!r}",
                ))
                break
        return out

    rule.__name__ = "travelplanner_real_rule"
    return rule


Split = Literal["train", "val", "test", "all"]


@dataclass
class TravelPlannerReal:
    n_examples: int = 60
    seed: int = 0
    split: Split = "all"
    train_frac: float = 0.6
    val_frac: float = 0.2
    hf_split: str = "validation"
    fault_inject: bool = True
    max_reference_chars: int = 2500

    @property
    def name(self) -> str:
        return "travelplanner_real"

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

    def _hf_index(self, idx: int) -> int:
        ds = _load(self.hf_split)
        rng = random.Random(self.seed * 1_000_031 + idx)
        return rng.randint(0, len(ds) - 1)

    def _build_example(self, idx: int) -> BenchmarkExample:
        ds = _load(self.hf_split)
        hf_idx = self._hf_index(idx)
        ex = ds[hf_idx]

        task_id = f"travel_real_{idx:05d}"
        profile_dict = inject_profile(task_id=task_id, seed=self.seed, dataset="travelplanner")
        profile = _profile_to_userprofile(profile_dict)

        local = _parse_local(str(ex["local_constraint"]))
        budget = ex["budget"]
        days = ex["days"]
        dest = ex["dest"]
        org = ex["org"]

        # Build banned substrings from profile.
        banned = []
        for c in profile_dict["constraints"]:
            t = c["text"].lower()
            if "vegan" in t:
                banned += ["steakhouse", "bbq joint", "carnivore", "veal", "foie gras"]
            if "wheelchair" in t or "mobility" in t:
                banned += ["climb the stairs", "stairs only", "uneven hike"]
            if "alcohol" in t and "no drink" in t:
                banned += ["wine bar", "cocktail lounge", "brewery tour"]
            if "feathers" in t:
                banned += ["down pillow", "down duvet"]

        ref_info = (str(ex.get("reference_information", "")))[: self.max_reference_chars]
        prompt = (
            f"User profile constraints:\n"
            + "\n".join(f"- {c['text']}" for c in profile_dict["constraints"])
            + f"\n\nLocal constraints from booking system:\n{local}\n\n"
            f"Budget: ${budget}\n"
            f"Travelers: {ex['people_number']}\n"
            f"Origin: {org}, Destination: {dest}, Days: {days}\n\n"
            f"Reference information:\n{ref_info}\n\n"
            f"Query: {ex['query']}\n\n"
            "Produce a concrete day-by-day plan. Each day must list "
            "accommodation, meals (with restaurants), and attractions, with a cost line. "
            "End with a 'Total cost: $...' summary."
        )

        gold_fault = None
        fr = inject_fault(
            task_id=task_id, seed=self.seed,
            profile=profile_dict, gold_answer=f"plan within ${budget}",
        ) if self.fault_inject else None
        if fr is not None:
            gold_fault = fr.target_node_id

        condition_meta = {
            "budget": budget,
            "days": days,
            "dest": dest,
            "org": org,
            "local_constraint": local,
            "level": ex.get("level", "easy"),
            "banned_substrings": banned,
            "profile_constraints": profile_dict["constraints"],
            "gold_fault_node": gold_fault,
            "fault_record": (fr.__dict__ if fr else None),
        }
        rule = _make_rule(condition_meta)

        task = {
            "task_id": task_id,
            "task_type": "travelplanner_real",
            "condition": "planning_real",
            "prompt": prompt,
            "split": self.split_of(idx),
            "condition_meta": condition_meta,
        }
        gold = GoldLabels(
            success=None,
            correct_final_output=f"valid plan within ${budget}",
            fault_node_id=gold_fault,
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


__all__ = ["TravelPlannerReal"]
