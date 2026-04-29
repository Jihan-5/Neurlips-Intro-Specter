"""HotpotQA + 2WikiMultiHopQA-style reconstruction with profile injection.

The plan PDF lists this as a Tier-B benchmark: multi-hop factual reasoning
where the user profile may or may not be relevant to the answer. The
diagnostic is whether the agent uses profile facts ONLY when the task
requires personalization, and ignores them on factually-irrelevant ones.

We do not download HotpotQA itself; the dataset is large and we want
controlled gold labels. Instead we generate multi-hop-style questions
programmatically with two diagnostic conditions analogous to PFQABench-Recon
but multi-hop:

* ``factual_irrelevant_multihop`` — a 2-hop factual question
  ("X studied at Y, Y is in country Z, what is Z?"); profile is irrelevant.
  Failure: agent's answer drifts toward a profile fact instead of the
  factually-correct chain answer.
* ``profile_required_multihop`` — a 2-hop personalized question
  ("Suggest a city for the user that matches their dietary class");
  the agent must use the profile to filter the multi-hop answer.

The verifier rule is the same shape as PFQABench-Recon: gold answer must
appear in the response, banned profile-leak substrings must not.
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
from .pfqa_recon import _build_profile  # reuse profile generator

# ---------------------------------------------------------------------------
# 2-hop factual question bank (no profile dependency)
# Each entry: (question, gold_answer, allowed_aliases, profile_distractor_keywords)
# ---------------------------------------------------------------------------

MULTIHOP_FACTUAL = [
    (
        "Albert Einstein worked at Princeton University. In which US state is Princeton located?",
        "New Jersey", ["new jersey", "nj"],
    ),
    (
        "The Mona Lisa is in the Louvre. The Louvre is in which European capital?",
        "Paris", ["paris"],
    ),
    (
        "William Shakespeare was born in Stratford-upon-Avon. Stratford-upon-Avon is in which country?",
        "England", ["england", "united kingdom", "uk"],
    ),
    (
        "The Apollo 11 mission was launched from Kennedy Space Center. Kennedy Space Center is in which US state?",
        "Florida", ["florida"],
    ),
    (
        "The Great Wall of China is in China. What is the capital of China?",
        "Beijing", ["beijing"],
    ),
    (
        "The Eiffel Tower was completed in 1889. Who was the lead engineer?",
        "Gustave Eiffel", ["gustave eiffel", "eiffel"],
    ),
    (
        "Mount Everest is on the border between Nepal and which other country?",
        "China", ["china", "tibet"],
    ),
    (
        "The Amazon River flows mostly through which country?",
        "Brazil", ["brazil"],
    ),
    (
        "Isaac Newton wrote Principia Mathematica. What is the modern name of the scientific field he founded?",
        "physics", ["physics", "classical mechanics"],
    ),
    (
        "The Titanic sank in 1912 in which ocean?",
        "Atlantic", ["atlantic"],
    ),
]


# ---------------------------------------------------------------------------
# Profile-required multi-hop question templates
# ---------------------------------------------------------------------------

@dataclass
class ProfileMultihopTemplate:
    label: str
    question_format: str
    relevant_field: str
    gold_fn: callable  # type: ignore[type-arg]
    banned_substrings_fn: callable  # type: ignore[type-arg]


def _city_for_dietary(dietary: str) -> str:
    return {
        "vegan": "Berlin",       # vegan-friendly
        "vegetarian": "Mumbai",
        "pescatarian": "Tokyo",
        "omnivore": "Buenos Aires",
    }.get(dietary, "Berlin")


def _city_banned(dietary: str) -> list[str]:
    if dietary == "vegan":
        return ["buenos aires", "argentinian steakhouse", "bbq joint"]
    if dietary == "vegetarian":
        return ["argentinian steakhouse"]
    return []


def _meal_for_lang_dietary(_) -> str:  # type: ignore[no-untyped-def]
    # Multi-hop conjunction: language + dietary.
    return "vegetable curry"


PROFILE_MULTIHOP_TEMPLATES = [
    ProfileMultihopTemplate(
        label="city",
        question_format="Suggest a city the user should visit. Mention only one city.",
        relevant_field="dietary",
        gold_fn=_city_for_dietary,
        banned_substrings_fn=_city_banned,
    ),
]


# ---------------------------------------------------------------------------
# Verifier rules
# ---------------------------------------------------------------------------


def _multihop_factual_rule(meta: dict[str, Any]):
    aliases = [a.lower() for a in meta["allowed_aliases"]]
    profile_keywords = [k.lower() for k in meta.get("profile_keywords", [])]

    def rule(profile, task, trajectory, final_output):
        text = (final_output or "").lower()
        out: list[ViolationEvent] = []
        if not any(a in text for a in aliases):
            out.append(ViolationEvent(
                violation_id="v_mh_factual_miss",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint=f"answer must contain factual gold ({meta['gold']})",
                trajectory_text=(final_output or "")[:200],
                severity=Severity.HIGH,
                explanation="multi-hop factual answer absent",
            ))
        contamination = [k for k in profile_keywords if k in text and len(k) > 2]
        if contamination:
            out.append(ViolationEvent(
                violation_id="v_mh_profile_contamination",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint="irrelevant profile context must not bias factual answer",
                trajectory_text=(final_output or "")[:200],
                severity=Severity.HIGH,
                explanation=f"answer leaked irrelevant profile term(s): {contamination}",
            ))
        return out

    rule.__name__ = "hotpotqa_factual_irrelevant_rule"
    return rule


def _multihop_profile_required_rule(meta: dict[str, Any]):
    gold = meta["gold"].lower()
    banned = [b.lower() for b in meta["banned"]]

    def rule(profile, task, trajectory, final_output):
        text = (final_output or "").lower()
        out: list[ViolationEvent] = []
        if gold not in text:
            out.append(ViolationEvent(
                violation_id="v_mh_profile_required_miss",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint=f"answer must reflect required profile fact ({gold})",
                trajectory_text=(final_output or "")[:200],
                severity=Severity.HIGH,
                explanation="profile-derived gold absent",
            ))
        for b in banned:
            if b and b in text:
                out.append(ViolationEvent(
                    violation_id="v_mh_profile_violation",
                    step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                    violated_profile_span_id="p_diet",
                    violated_constraint="answer violates a hard profile constraint",
                    trajectory_text=(final_output or "")[:200],
                    severity=Severity.HIGH,
                    explanation=f"answer contains banned substring {b!r}",
                ))
                break
        return out

    rule.__name__ = "hotpotqa_profile_required_rule"
    return rule


Condition = Literal["factual_irrelevant_multihop", "profile_required_multihop"]
Split = Literal["train", "val", "test", "all"]


@dataclass
class HotpotQARecon:
    n_examples: int = 100
    seed: int = 0
    split: Split = "all"
    train_frac: float = 0.6
    val_frac: float = 0.2

    @property
    def name(self) -> str:
        return "hotpotqa_recon"

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
        rng = random.Random(self.seed * 1_000_007 + idx)
        profile, facts = _build_profile(rng, idx)
        condition: Condition = (
            "factual_irrelevant_multihop" if idx % 2 == 0 else "profile_required_multihop"
        )
        task_id = f"hotpotqa_recon_{idx:05d}"

        if condition == "factual_irrelevant_multihop":
            question, gold, aliases = rng.choice(MULTIHOP_FACTUAL)
            profile_keywords = [
                facts["dietary"], facts["language"].lower(),
                facts["occupation"], facts["city"][0].lower(),
            ]
            condition_meta = {
                "gold": gold, "allowed_aliases": aliases,
                "profile_keywords": profile_keywords,
            }
            rule = _multihop_factual_rule(condition_meta)
            gold_label = gold
        else:
            tmpl = rng.choice(PROFILE_MULTIHOP_TEMPLATES)
            question = tmpl.question_format
            field_value = facts[tmpl.relevant_field]
            gold_label = tmpl.gold_fn(field_value)
            banned = tmpl.banned_substrings_fn(field_value)
            condition_meta = {"gold": gold_label, "banned": banned}
            rule = _multihop_profile_required_rule(condition_meta)

        task = {
            "task_id": task_id,
            "task_type": "hotpotqa",
            "condition": condition,
            "prompt": question,
            "split": self.split_of(idx),
            "condition_meta": condition_meta,
        }
        gold = GoldLabels(success=None, correct_final_output=gold_label)
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


__all__ = ["HotpotQARecon", "MULTIHOP_FACTUAL", "PROFILE_MULTIHOP_TEMPLATES"]
