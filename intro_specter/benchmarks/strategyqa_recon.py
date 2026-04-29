"""StrategyQA-style reconstruction: implicit multi-step yes/no QA with profile.

StrategyQA (Geva et al. 2021) tests whether a model can perform *implicit*
multi-step reasoning to answer yes/no questions whose bridging facts are
NOT given in the question (e.g., "Did Aristotle use a laptop?" requires
knowing both that Aristotle lived in 384–322 BCE and that laptops were
invented in the 1980s, then comparing).

We don't access the original StrategyQA dataset; this is a programmatic
reconstruction preserving the diagnostic structure that matters here:

* ``factual_implicit`` — a yes/no question where the answer requires
  implicit multi-step reasoning over world knowledge; the user profile
  is irrelevant. Gold: yes/no. Failure modes: wrong polarity, profile
  contamination.
* ``profile_implicit`` — a yes/no question whose answer depends on a
  profile fact combined with a world-knowledge step (e.g., "Should the
  user choose option A?" where the answer depends on the user's dietary
  class plus a fact about option A).

Why this is the right next benchmark:
* StrategyQA's binary output makes the "wrong root cause" failure mode
  much sharper than open-ended QA — you flip yes↔no, you measure exactly
  how often Intro-Specter rescues a flip vs. how often Reflexion does.
* The implicit reasoning chain adds candidate fault nodes that aren't
  visible in HotpotQA's explicit text — Intro-Specter's DAG has more
  to attribute over.

Limitations to acknowledge in §5:
* Templated yes/no questions sacrifice lexical diversity for tractability.
* "Implicit" here means the question doesn't surface the bridging fact;
  the bridging fact is still drawn from a small curated bank.
"""

from __future__ import annotations

import random
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Literal

from ..schemas import (
    AssumptionDAG,
    GoldLabels,
    Severity,
    Trajectory,
    ViolationEvent,
)
from .base import BenchmarkExample
from .pfqa_recon import _build_profile

# ---------------------------------------------------------------------------
# Implicit-reasoning yes/no questions (no profile dependency)
# Each entry: (question, gold_yes_no, aliases_for_no_or_yes)
# ---------------------------------------------------------------------------

IMPLICIT_YES_NO: list[tuple[str, str]] = [
    ("Did Aristotle ever use a laptop?", "no"),
    ("Could Albert Einstein have driven a Tesla Model S?", "no"),
    ("Is the boiling point of water lower than the melting point of iron?", "yes"),
    ("Could a blue whale fit inside an Olympic-size swimming pool?", "yes"),
    ("Did William Shakespeare ever read Harry Potter?", "no"),
    ("Is the Pacific Ocean larger than the entire continent of Africa?", "yes"),
    ("Could Julius Caesar have called his troops on a mobile phone?", "no"),
    ("Is Mount Everest taller than the height of ten Eiffel Towers stacked?", "no"),
    ("Did Leonardo da Vinci ever watch a Hollywood film?", "no"),
    ("Could a person have flown from London to New York in 1900?", "no"),
    ("Is the Sahara Desert larger than the United States?", "yes"),
    ("Did Marco Polo ever taste a tomato?", "no"),
    ("Is the Great Wall of China visible from low Earth orbit with the naked eye?", "no"),
    ("Could Genghis Khan have used Google Maps to plan his campaigns?", "no"),
    ("Is the population of China larger than that of the European Union?", "yes"),
    ("Did Cleopatra live closer in time to the moon landing than to the building of the Great Pyramid?", "yes"),
    ("Could Benjamin Franklin have read a tweet?", "no"),
    ("Is the area of Russia greater than the surface of Pluto?", "yes"),
    ("Did Mozart ever hear a recording of his own music?", "no"),
    ("Could Christopher Columbus have crossed the Atlantic in a single day in 1492?", "no"),
    ("Is the Amazon rainforest larger than India?", "yes"),
    ("Did Isaac Newton ever use a calculator?", "no"),
    ("Could Genghis Khan have ridden in a hot air balloon during his lifetime?", "no"),
    ("Is the Vatican City smaller than New York's Central Park?", "yes"),
    ("Did Charles Darwin ever read Origin of Species in printed form?", "yes"),
    ("Could Napoleon Bonaparte have flown to his exile on Saint Helena?", "no"),
    ("Is the average human heart rate higher than 30 beats per minute at rest?", "yes"),
    ("Did Galileo ever look through a telescope at Pluto?", "no"),
    ("Could a polar bear be naturally found at the South Pole?", "no"),
    ("Is the Nile River longer than the distance between Paris and Berlin?", "yes"),
]


# ---------------------------------------------------------------------------
# Profile-required yes/no question templates
# ---------------------------------------------------------------------------


@dataclass
class ProfileYesNoTemplate:
    label: str
    question_format: str
    relevant_field: str
    gold_fn: callable  # type: ignore[type-arg]
    banned_substrings_fn: callable  # type: ignore[type-arg]


def _vegan_burger_gold(diet: str) -> str:
    # "Should the user order a beef burger?" — yes for omnivore, no otherwise.
    return "yes" if diet == "omnivore" else "no"


def _vegan_burger_banned(diet: str) -> list[str]:
    if diet in {"vegan", "vegetarian"}:
        return ["yes, the user can"]
    return []


def _seafood_gold(diet: str) -> str:
    # "Is grilled salmon appropriate for this user's diet?" — yes for pescatarian/omnivore.
    return "yes" if diet in {"pescatarian", "omnivore"} else "no"


def _seafood_banned(diet: str) -> list[str]:
    if diet == "vegan":
        return []
    return []


def _hike_gold(fit: str) -> str:
    # "Should the user attempt a 20-mile mountain hike this weekend?"
    # yes for high fitness, no for low/medium.
    return "yes" if fit == "high" else "no"


def _hike_banned(fit: str) -> list[str]:
    return []


PROFILE_YES_NO_TEMPLATES = [
    ProfileYesNoTemplate(
        label="beef_burger",
        question_format=(
            "Considering the user's dietary class, would a beef burger be an "
            "appropriate dinner choice for them tonight? Answer yes or no on a single line."
        ),
        relevant_field="dietary",
        gold_fn=_vegan_burger_gold,
        banned_substrings_fn=_vegan_burger_banned,
    ),
    ProfileYesNoTemplate(
        label="grilled_salmon",
        question_format=(
            "Would grilled salmon be an appropriate dinner choice for this user "
            "given their dietary class? Answer yes or no on a single line."
        ),
        relevant_field="dietary",
        gold_fn=_seafood_gold,
        banned_substrings_fn=_seafood_banned,
    ),
    ProfileYesNoTemplate(
        label="long_hike",
        question_format=(
            "Should the user attempt a strenuous 20-mile mountain hike this weekend, "
            "given their stated fitness level? Answer yes or no on a single line."
        ),
        relevant_field="fitness",
        gold_fn=_hike_gold,
        banned_substrings_fn=_hike_banned,
    ),
]


# ---------------------------------------------------------------------------
# Verifier rules
# ---------------------------------------------------------------------------


def _yes_no_polarity(text: str) -> str | None:
    """Return 'yes' / 'no' / None depending on the first polarity token found.

    We look at the very start of the (lowercased) response and the first
    sentence; matches the StrategyQA convention.
    """
    t = (text or "").strip().lower()
    if not t:
        return None
    first = t.split("\n")[0].strip()
    # Tolerate "Yes," / "No." / "yes — because ..." etc.
    for tok in ("yes", "no"):
        if first.startswith(tok + " ") or first == tok or first.startswith(tok + ",") or first.startswith(tok + "."):
            return tok
    # Fallback: scan the first 30 chars.
    head = t[:30]
    if " yes " in head or head.startswith("yes"):
        return "yes"
    if " no " in head or head.startswith("no"):
        return "no"
    return None


def _factual_implicit_rule(meta: dict[str, Any]):
    gold = meta["gold"]
    profile_keywords = [k.lower() for k in meta.get("profile_keywords", [])]

    def rule(profile, task, trajectory, final_output):
        text = (final_output or "")
        polarity = _yes_no_polarity(text)
        out: list[ViolationEvent] = []
        if polarity != gold:
            out.append(ViolationEvent(
                violation_id="v_strategyqa_polarity_miss",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint=f"answer must be {gold!r}",
                trajectory_text=text[:200],
                severity=Severity.HIGH,
                explanation=f"polarity wrong: got {polarity!r}",
            ))
        contamination = [k for k in profile_keywords if k in text.lower() and len(k) > 2]
        if contamination:
            out.append(ViolationEvent(
                violation_id="v_strategyqa_profile_contamination",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint="irrelevant profile context must not bias answer",
                trajectory_text=text[:200],
                severity=Severity.HIGH,
                explanation=f"answer leaked irrelevant profile term(s): {contamination}",
            ))
        return out

    rule.__name__ = "strategyqa_factual_implicit_rule"
    return rule


def _profile_implicit_rule(meta: dict[str, Any]):
    gold = meta["gold"]
    banned = [b.lower() for b in meta.get("banned", [])]

    def rule(profile, task, trajectory, final_output):
        text = (final_output or "")
        polarity = _yes_no_polarity(text)
        out: list[ViolationEvent] = []
        if polarity != gold:
            out.append(ViolationEvent(
                violation_id="v_strategyqa_profile_polarity_miss",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint=f"answer must be {gold!r} given profile",
                trajectory_text=text[:200],
                severity=Severity.HIGH,
                explanation=f"polarity wrong (profile-grounded): got {polarity!r}",
            ))
        for b in banned:
            if b and b in text.lower():
                out.append(ViolationEvent(
                    violation_id="v_strategyqa_profile_violation",
                    step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                    violated_profile_span_id="p_diet",
                    violated_constraint="answer violates a hard profile constraint",
                    trajectory_text=text[:200],
                    severity=Severity.HIGH,
                    explanation=f"answer contains banned substring {b!r}",
                ))
                break
        return out

    rule.__name__ = "strategyqa_profile_implicit_rule"
    return rule


Condition = Literal["factual_implicit", "profile_implicit"]
Split = Literal["train", "val", "test", "all"]


@dataclass
class StrategyQARecon:
    n_examples: int = 100
    seed: int = 0
    split: Split = "all"
    train_frac: float = 0.6
    val_frac: float = 0.2

    @property
    def name(self) -> str:
        return "strategyqa_recon"

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
        rng = random.Random(self.seed * 1_000_017 + idx)
        profile, facts = _build_profile(rng, idx)
        condition: Condition = "factual_implicit" if idx % 2 == 0 else "profile_implicit"
        task_id = f"strategyqa_recon_{idx:05d}"

        if condition == "factual_implicit":
            question, gold = rng.choice(IMPLICIT_YES_NO)
            profile_keywords = [
                facts["dietary"], facts["language"].lower(),
                facts["occupation"], facts["city"][0].lower(),
            ]
            condition_meta = {
                "gold": gold,
                "profile_keywords": profile_keywords,
            }
            rule = _factual_implicit_rule(condition_meta)
            gold_label = gold
        else:
            tmpl = rng.choice(PROFILE_YES_NO_TEMPLATES)
            question = tmpl.question_format
            field_value = facts[tmpl.relevant_field]
            gold_label = tmpl.gold_fn(field_value)
            banned = tmpl.banned_substrings_fn(field_value)
            condition_meta = {"gold": gold_label, "banned": banned}
            rule = _profile_implicit_rule(condition_meta)

        task = {
            "task_id": task_id,
            "task_type": "strategyqa",
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


__all__ = ["StrategyQARecon", "IMPLICIT_YES_NO", "PROFILE_YES_NO_TEMPLATES"]
