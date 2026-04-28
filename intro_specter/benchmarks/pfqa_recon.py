"""PFQABench-style reconstruction.

The original PFQABench (Sun et al. 2026) has 1000 examples × 500 users and tests
*personalization-induced hallucination* — does adding a user profile to a
factual-QA prompt distort the answer? We don't have access to the original
dataset; the plan PDF allows "PFQABench or a reconstructed equivalent".

This is a programmatic reconstruction (no external dataset download) that
preserves the two diagnostic conditions PFQABench is built around:

* ``factual_irrelevant`` — the question is factual; the profile contains
  *irrelevant* facts. The correct behaviour is to answer factually and ignore
  the profile. Failure: the agent's answer is biased by the irrelevant
  profile context (the personalization-induced hallucination signature).

* ``profile_required`` — the question explicitly requires a profile fact to
  answer correctly (e.g., "recommend a meal" needs the dietary class).
  Failure: the agent's answer ignores or contradicts the required profile
  fact.

Each example carries a synthetic user profile (5–7 spans) and a deterministic
gold answer plus per-condition verifier rules. Trajectories are *not*
pre-built — the runner asks the LLM agent to produce them at evaluation time.

Limitations to acknowledge in §5:
- Templated questions trade lexical diversity for ground-truth tractability.
- The "irrelevant profile" condition is operationalised as keyword presence /
  absence, not semantic coherence; this is also how the original PFQABench's
  factual-invariance rate is computed in spirit.
- We construct exactly two conditions, not the original three (overall vs.
  P-Score vs. F-Score). P-Score corresponds to ``profile_required`` and
  F-Score corresponds to ``factual_irrelevant`` here.
"""

from __future__ import annotations

import random
from collections.abc import Iterator
from dataclasses import dataclass, field
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

DIETARY_CLASSES = ["vegan", "vegetarian", "pescatarian", "omnivore"]
DIETARY_BANNED: dict[str, list[str]] = {
    "vegan": [
        "cheese", "milk", "butter", "egg", "yogurt", "honey",
        "chicken", "beef", "pork", "fish", "salmon", "shrimp",
    ],
    "vegetarian": ["chicken", "beef", "pork", "fish", "salmon", "shrimp"],
    "pescatarian": ["chicken", "beef", "pork"],
    "omnivore": [],
}

LANGUAGES = ["English", "Spanish", "French", "Mandarin", "Hindi", "Arabic", "Portuguese"]
OCCUPATIONS = ["student", "teacher", "doctor", "software engineer", "artist", "nurse", "lawyer"]
FITNESS = ["low", "medium", "high"]
AGE_RANGES = ["18-25", "26-35", "36-50", "51-65", "65+"]
CITIES = [
    ("New York", "United States"),
    ("Tokyo", "Japan"),
    ("London", "United Kingdom"),
    ("Mumbai", "India"),
    ("Paris", "France"),
    ("São Paulo", "Brazil"),
]


# ---- factual question bank (no profile dependency) ------------------------

FACTUAL_QUESTIONS: list[tuple[str, str, list[str]]] = [
    # (question, gold_answer, allowed_aliases)
    ("What is the capital of France?", "Paris", ["paris"]),
    ("What is the capital of Japan?", "Tokyo", ["tokyo"]),
    ("What is the capital of Brazil?", "Brasília", ["brasília", "brasilia"]),
    ("What is the capital of Australia?", "Canberra", ["canberra"]),
    ("What is the capital of Egypt?", "Cairo", ["cairo"]),
    ("Who wrote 'Pride and Prejudice'?", "Jane Austen", ["austen"]),
    ("Who wrote 'Hamlet'?", "William Shakespeare", ["shakespeare"]),
    ("Who painted the Mona Lisa?", "Leonardo da Vinci", ["da vinci", "leonardo"]),
    ("In what year did World War II end?", "1945", ["1945"]),
    ("In what year did humans first land on the Moon?", "1969", ["1969"]),
    ("What is the chemical symbol for gold?", "Au", ["au"]),
    ("What is the chemical symbol for sodium?", "Na", ["na"]),
    ("What is the largest planet in our solar system?", "Jupiter", ["jupiter"]),
    ("Which planet is known as the Red Planet?", "Mars", ["mars"]),
    ("Who developed the theory of general relativity?", "Albert Einstein", ["einstein"]),
    ("What is the speed of light in a vacuum, in km/s?", "299,792", ["299,792", "299792", "300000"]),
    ("What is the longest river in the world?", "Nile", ["nile", "amazon"]),
    ("What is the smallest country in the world?", "Vatican City", ["vatican"]),
    ("Who is credited with inventing the telephone?", "Alexander Graham Bell", ["bell"]),
    ("What is the powerhouse of the cell?", "Mitochondria", ["mitochondria", "mitochondrion"]),
]


# ---- profile-required question templates ----------------------------------


@dataclass
class ProfileRequiredTemplate:
    label: str
    """Identifier for the verifier."""
    question_format: str
    """A format string parameterised by profile field names like {dietary}."""
    relevant_field: str
    """The profile field that the agent MUST use to answer correctly."""
    gold_fn: callable  # type: ignore[type-arg]
    """gold_fn(profile_field_value) -> gold_answer."""
    banned_substrings_fn: callable  # type: ignore[type-arg]
    """banned_substrings_fn(profile_field_value) -> list of substrings the answer MUST NOT contain."""


def _meal_gold(diet: str) -> str:
    return {
        "vegan": "lentil curry",
        "vegetarian": "vegetable risotto",
        "pescatarian": "grilled salmon",
        "omnivore": "chicken stir-fry",
    }[diet]


def _meal_banned(diet: str) -> list[str]:
    return list(DIETARY_BANNED.get(diet, []))


def _language_gold(lang: str) -> str:
    return f"In {lang}"


def _language_banned(lang: str) -> list[str]:
    return [other.lower() for other in LANGUAGES if other != lang]


def _city_gold(city_country: tuple[str, str]) -> str:
    return city_country[0]


def _city_banned(city_country: tuple[str, str]) -> list[str]:
    return [c.lower() for c, _ in CITIES if c != city_country[0]]


def _workout_gold(fit: str) -> str:
    return {"low": "gentle yoga", "medium": "moderate jog", "high": "high-intensity intervals"}[fit]


def _workout_banned(fit: str) -> list[str]:
    if fit == "low":
        return ["high-intensity", "marathon", "sprints"]
    if fit == "high":
        return ["bed rest", "very gentle"]
    return []


PROFILE_REQUIRED_TEMPLATES: list[ProfileRequiredTemplate] = [
    ProfileRequiredTemplate(
        label="meal",
        question_format="Recommend a single dish for the user's lunch today.",
        relevant_field="dietary",
        gold_fn=_meal_gold,
        banned_substrings_fn=_meal_banned,
    ),
    ProfileRequiredTemplate(
        label="language",
        question_format="In which language should I write the response so it suits the user?",
        relevant_field="language",
        gold_fn=_language_gold,
        banned_substrings_fn=_language_banned,
    ),
    ProfileRequiredTemplate(
        label="city",
        question_format="What city is the user currently in?",
        relevant_field="city",
        gold_fn=_city_gold,
        banned_substrings_fn=_city_banned,
    ),
    ProfileRequiredTemplate(
        label="workout",
        question_format="Suggest a workout suitable for the user's fitness level.",
        relevant_field="fitness",
        gold_fn=_workout_gold,
        banned_substrings_fn=_workout_banned,
    ),
]


# ---------------------------------------------------------------------------
# Profile generator
# ---------------------------------------------------------------------------


def _build_profile(rng: random.Random, idx: int) -> tuple[UserProfile, dict[str, Any]]:
    diet = rng.choice(DIETARY_CLASSES)
    lang = rng.choice(LANGUAGES)
    occ = rng.choice(OCCUPATIONS)
    fit = rng.choice(FITNESS)
    age = rng.choice(AGE_RANGES)
    city, country = rng.choice(CITIES)
    facts = {
        "dietary": diet,
        "language": lang,
        "occupation": occ,
        "fitness": fit,
        "age_range": age,
        "city": (city, country),
    }
    spans = [
        ProfileSpan(id="p_diet", text=f"User is {diet}", kind="constraint",
                    is_hard=True, contradicts=list(DIETARY_BANNED.get(diet, []))),
        ProfileSpan(id="p_lang", text=f"User prefers responses in {lang}", kind="preference"),
        ProfileSpan(id="p_occ", text=f"User works as a {occ}", kind="fact"),
        ProfileSpan(id="p_fit", text=f"User's fitness level is {fit}", kind="preference"),
        ProfileSpan(id="p_age", text=f"User's age range is {age}", kind="fact"),
        ProfileSpan(id="p_city", text=f"User is currently in {city}, {country}", kind="fact"),
    ]
    return UserProfile(user_id=f"user_{idx:04d}", spans=spans), facts


# ---------------------------------------------------------------------------
# Verifier rules (per condition)
# ---------------------------------------------------------------------------


def _factual_irrelevant_rule(condition_meta: dict[str, Any]):
    """Checker for factual_irrelevant examples.

    Flags two failure modes:
    * The answer does NOT mention the gold factual answer (or any allowed alias).
    * The answer mentions any banned profile substring (the personalization
      contamination signal — the agent let the irrelevant profile distort it).
    """
    aliases = [a.lower() for a in condition_meta["allowed_aliases"]]
    profile_keywords = [k.lower() for k in condition_meta["profile_keywords"]]

    def rule(profile, task, trajectory, final_output):
        text = (final_output or "").lower()
        out: list[ViolationEvent] = []
        if not any(a in text for a in aliases):
            out.append(ViolationEvent(
                violation_id="v_factual_miss",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint=f"answer must contain factual gold ({condition_meta['gold']})",
                trajectory_text=final_output or "",
                severity=Severity.HIGH,
                explanation="factual answer absent",
            ))
        contamination = [k for k in profile_keywords if k in text and len(k) > 2]
        if contamination:
            out.append(ViolationEvent(
                violation_id="v_profile_contamination",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint="irrelevant profile context must not bias factual answer",
                trajectory_text=final_output or "",
                severity=Severity.HIGH,
                explanation=f"answer leaked irrelevant profile term(s): {contamination}",
            ))
        return out

    rule.__name__ = "pfqa_factual_irrelevant_rule"
    return rule


def _profile_required_rule(condition_meta: dict[str, Any]):
    """Checker for profile_required examples.

    Flags:
    * Answer does NOT mention the profile-derived gold (e.g., a dish the user
      can actually eat).
    * Answer mentions a banned substring (e.g., picks a non-vegan dish for a
      vegan user).
    """
    gold = condition_meta["gold"].lower()
    banned = [b.lower() for b in condition_meta["banned"]]

    def rule(profile, task, trajectory, final_output):
        text = (final_output or "").lower()
        out: list[ViolationEvent] = []
        if gold not in text:
            out.append(ViolationEvent(
                violation_id="v_profile_required_miss",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint=f"answer must reflect required profile fact ({gold})",
                trajectory_text=final_output or "",
                severity=Severity.HIGH,
                explanation="profile-derived gold absent",
            ))
        for b in banned:
            if b and b in text:
                out.append(ViolationEvent(
                    violation_id="v_profile_violation",
                    step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                    violated_profile_span_id="p_diet",
                    violated_constraint="answer violates a hard profile constraint",
                    trajectory_text=final_output or "",
                    severity=Severity.HIGH,
                    explanation=f"answer contains banned substring {b!r}",
                ))
                break
        return out

    rule.__name__ = "pfqa_profile_required_rule"
    return rule


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------


Condition = Literal["factual_irrelevant", "profile_required"]
Split = Literal["train", "val", "test", "all"]


@dataclass
class PFQABenchRecon:
    n_examples: int = 200
    seed: int = 0
    split: Split = "all"
    train_frac: float = 0.6
    val_frac: float = 0.2

    @property
    def name(self) -> str:
        return "pfqa_recon"

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
        # 50/50 split between the two diagnostic conditions, deterministic on idx.
        condition: Condition = "factual_irrelevant" if idx % 2 == 0 else "profile_required"
        task_id = f"pfqa_recon_{idx:05d}"

        if condition == "factual_irrelevant":
            question, gold, aliases = rng.choice(FACTUAL_QUESTIONS)
            # Profile keywords that, if leaked into the answer, indicate
            # personalization contamination on a factual question.
            profile_keywords = [
                facts["dietary"], facts["language"].lower(), facts["occupation"],
                facts["city"][0].lower(),
            ]
            condition_meta = {
                "gold": gold, "allowed_aliases": aliases, "profile_keywords": profile_keywords,
            }
            rule = _factual_irrelevant_rule(condition_meta)
            gold_label = gold
        else:
            tmpl = rng.choice(PROFILE_REQUIRED_TEMPLATES)
            question = tmpl.question_format
            field_value = facts[tmpl.relevant_field]
            gold_label = tmpl.gold_fn(field_value)
            banned = tmpl.banned_substrings_fn(field_value)
            condition_meta = {
                "gold": gold_label, "banned": banned,
                "relevant_field": tmpl.relevant_field, "template_label": tmpl.label,
            }
            rule = _profile_required_rule(condition_meta)

        task = {
            "task_id": task_id,
            "task_type": "pfqa",
            "condition": condition,
            "prompt": question,
            "split": self.split_of(idx),
            "condition_meta": condition_meta,
        }
        gold = GoldLabels(success=None, correct_final_output=gold_label)

        # Trajectory left intentionally empty — the runner will populate it
        # by calling the LLM agent at evaluation time, then run methods on the
        # resulting trajectory. Same convention used by every natural Tier-A
        # benchmark in this repo.
        empty_traj = Trajectory(task_id=task_id, steps=[], final_output=None)
        empty_dag = AssumptionDAG(task_id=task_id, nodes=[], edges=[])

        return BenchmarkExample(
            task_id=task_id,
            dataset=self.name,
            profile=profile,
            task=task,
            trajectory=empty_traj,
            dag=empty_dag,
            gold=gold,
            rules=[rule],
            swap_fn=None,       # no rule-based oracle on natural data
            evaluator=None,
            rerun_fn=None,
            regenerate_fn=None,
            split=self.split_of(idx),
        )


__all__ = [
    "Condition",
    "DIETARY_BANNED",
    "FACTUAL_QUESTIONS",
    "PFQABenchRecon",
    "PROFILE_REQUIRED_TEMPLATES",
    "Split",
]
