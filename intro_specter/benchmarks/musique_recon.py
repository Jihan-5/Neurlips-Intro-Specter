"""MuSiQue-style reconstruction: 3-hop multi-hop QA with profile injection.

MuSiQue (Trivedi et al. 2022) targets harder, more compositional multi-hop
questions than HotpotQA — the answer chain is longer (3 hops in MuSiQue-Ans)
and decomposition is hand-crafted to require *all* intermediate hops.

We don't have access to the original MuSiQue dataset; the plan PDF allows
"reconstructed equivalent". This module is a programmatic reconstruction
preserving the diagnostic structure that matters for Intro-Specter:

* ``factual_3hop`` — a 3-hop factual chain ("X is at Y; Y is in Z; Z's
  capital is W; what is W?"); profile is irrelevant. Failure modes are
  (i) wrong answer, (ii) profile contamination — the agent let the
  irrelevant user profile drift its answer.
* ``profile_required_3hop`` — a 3-hop chain whose final hop depends on a
  profile fact (e.g., the user's dietary class selects between two cities
  that match the chain's earlier hops).

Why this is the right next benchmark:
* MuSiQue's longer chain creates more candidate fault nodes in the
  Assumption-DAG. Intro-Specter's structured attribution should benefit
  more from a deeper DAG than from HotpotQA's 2-hop questions.
* The same verifier shape (gold-substring + banned-substring) used by
  PFQABench-Recon and HotpotQA-Recon transfers directly here, so the
  results are directly comparable.

Limitations to acknowledge in §5:
* Templated 3-hop questions sacrifice lexical diversity for ground-truth
  tractability.
* Hop-2 and hop-3 facts are curated from a small worldknowledge bank, not
  retrieved from Wikipedia (which the original MuSiQue assumes).
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
from .pfqa_recon import _build_profile  # reuse profile generator

# ---------------------------------------------------------------------------
# 3-hop factual question bank (no profile dependency)
# Each entry: (question, gold_answer, allowed_aliases)
# Each question chains three lookups; the final answer is at the end of the chain.
# ---------------------------------------------------------------------------

MULTIHOP_3HOP_FACTUAL: list[tuple[str, str, list[str]]] = [
    (
        "Marie Curie was born in Warsaw. Warsaw is the capital of Poland. "
        "What currency does Poland use?",
        "Polish złoty", ["złoty", "zloty", "pln"],
    ),
    (
        "Charles Darwin sailed on HMS Beagle. The Beagle visited the Galápagos Islands. "
        "Which country governs the Galápagos Islands today?",
        "Ecuador", ["ecuador"],
    ),
    (
        "Frida Kahlo was Mexican. Mexico's capital is Mexico City. "
        "What body of water borders Mexico City's country to the east?",
        "Gulf of Mexico", ["gulf of mexico", "gulf"],
    ),
    (
        "Vincent van Gogh painted The Starry Night while in Saint-Rémy, France. "
        "France borders Spain to the south. What is the capital of Spain?",
        "Madrid", ["madrid"],
    ),
    (
        "The Beatles were formed in Liverpool. Liverpool is in England. "
        "England is part of the United Kingdom — what is the UK's capital?",
        "London", ["london"],
    ),
    (
        "Mahatma Gandhi was born in Porbandar. Porbandar is in Gujarat. "
        "Gujarat is a state in which country?",
        "India", ["india"],
    ),
    (
        "Wolfgang Mozart was born in Salzburg. Salzburg is in Austria. "
        "What is the official language of Austria?",
        "German", ["german"],
    ),
    (
        "Nelson Mandela was president of South Africa. South Africa's largest city is Johannesburg. "
        "Johannesburg is in which province?",
        "Gauteng", ["gauteng"],
    ),
    (
        "Pyotr Tchaikovsky composed Swan Lake. Tchaikovsky was Russian. "
        "What is the capital of Russia?",
        "Moscow", ["moscow"],
    ),
    (
        "The Inca Empire's capital was Cusco. Cusco is in modern-day Peru. "
        "What ocean is on Peru's western coast?",
        "Pacific Ocean", ["pacific"],
    ),
    (
        "Sigmund Freud lived in Vienna. Vienna is the capital of Austria. "
        "What river flows through Vienna?",
        "Danube", ["danube"],
    ),
    (
        "Pelé played football for Santos FC. Santos is a city in Brazil. "
        "What is the official language of Brazil?",
        "Portuguese", ["portuguese"],
    ),
    (
        "The Dalai Lama is the spiritual leader of Tibet. Tibet is administered by China. "
        "What is the capital of China?",
        "Beijing", ["beijing"],
    ),
    (
        "Akira Kurosawa directed Seven Samurai. Kurosawa was Japanese. "
        "What is the largest island of Japan?",
        "Honshu", ["honshu"],
    ),
    (
        "Gabriel García Márquez wrote One Hundred Years of Solitude. He was Colombian. "
        "What is the capital of Colombia?",
        "Bogotá", ["bogotá", "bogota"],
    ),
    (
        "Mount Kilimanjaro is in Tanzania. Tanzania is in East Africa. "
        "What ocean is on Tanzania's coast?",
        "Indian Ocean", ["indian ocean", "indian"],
    ),
    (
        "Confucius lived in the Lu state. The Lu state was in modern Shandong. "
        "Shandong is a province of which country?",
        "China", ["china"],
    ),
    (
        "Antoni Gaudí designed the Sagrada Família. The Sagrada Família is in Barcelona. "
        "Barcelona is in which Spanish autonomous community?",
        "Catalonia", ["catalonia", "catalunya"],
    ),
    (
        "Leonardo da Vinci painted The Last Supper. The Last Supper is in Milan. "
        "Milan is in which Italian region?",
        "Lombardy", ["lombardy", "lombardia"],
    ),
    (
        "Cleopatra ruled the Ptolemaic Kingdom. Its capital was Alexandria. "
        "Alexandria is in modern-day Egypt — what river runs through Egypt?",
        "Nile", ["nile"],
    ),
]


# ---------------------------------------------------------------------------
# Profile-required 3-hop templates
# ---------------------------------------------------------------------------


@dataclass
class ProfileMultihopTemplate:
    label: str
    question_format: str
    relevant_field: str
    gold_fn: callable  # type: ignore[type-arg]
    banned_substrings_fn: callable  # type: ignore[type-arg]


def _restaurant_for_dietary(dietary: str) -> str:
    # Hop 1: user's diet.
    # Hop 2: cuisines compatible with that diet.
    # Hop 3: a city in our profile bank known for that cuisine.
    return {
        "vegan": "Berlin",
        "vegetarian": "Mumbai",
        "pescatarian": "Tokyo",
        "omnivore": "Buenos Aires",
    }[dietary]


def _restaurant_banned(dietary: str) -> list[str]:
    if dietary == "vegan":
        return ["buenos aires", "argentinian steakhouse", "bbq joint", "tokyo sushi"]
    if dietary == "vegetarian":
        return ["argentinian steakhouse"]
    if dietary == "pescatarian":
        return ["argentinian steakhouse"]
    return []


def _book_for_lang(lang: str) -> str:
    return {
        "English": "Hamlet",
        "Spanish": "Don Quixote",
        "French": "Les Misérables",
        "Mandarin": "Journey to the West",
        "Hindi": "Godan",
        "Arabic": "One Thousand and One Nights",
        "Portuguese": "The Lusiads",
    }[lang]


def _book_banned(lang: str) -> list[str]:
    return []


PROFILE_3HOP_TEMPLATES = [
    ProfileMultihopTemplate(
        label="restaurant_city",
        question_format=(
            "We want to plan a culinary trip for the user. Considering the user's "
            "dietary class and which world cuisines align with it, name a single "
            "city that would be the best primary destination."
        ),
        relevant_field="dietary",
        gold_fn=_restaurant_for_dietary,
        banned_substrings_fn=_restaurant_banned,
    ),
    ProfileMultihopTemplate(
        label="canonical_book",
        question_format=(
            "Recommend a single canonical work of literature originally written in "
            "the user's preferred language. Return only the title."
        ),
        relevant_field="language",
        gold_fn=_book_for_lang,
        banned_substrings_fn=_book_banned,
    ),
]


# ---------------------------------------------------------------------------
# Verifier rules
# ---------------------------------------------------------------------------


def _factual_3hop_rule(meta: dict[str, Any]):
    aliases = [a.lower() for a in meta["allowed_aliases"]]
    profile_keywords = [k.lower() for k in meta.get("profile_keywords", [])]

    def rule(profile, task, trajectory, final_output):
        text = (final_output or "").lower()
        out: list[ViolationEvent] = []
        if not any(a in text for a in aliases):
            out.append(ViolationEvent(
                violation_id="v_musique_factual_miss",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint=f"answer must contain factual gold ({meta['gold']})",
                trajectory_text=(final_output or "")[:200],
                severity=Severity.HIGH,
                explanation="3-hop factual answer absent",
            ))
        contamination = [k for k in profile_keywords if k in text and len(k) > 2]
        if contamination:
            out.append(ViolationEvent(
                violation_id="v_musique_profile_contamination",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint="irrelevant profile context must not bias factual answer",
                trajectory_text=(final_output or "")[:200],
                severity=Severity.HIGH,
                explanation=f"answer leaked irrelevant profile term(s): {contamination}",
            ))
        return out

    rule.__name__ = "musique_factual_3hop_rule"
    return rule


def _profile_required_3hop_rule(meta: dict[str, Any]):
    gold = meta["gold"].lower()
    banned = [b.lower() for b in meta["banned"]]

    def rule(profile, task, trajectory, final_output):
        text = (final_output or "").lower()
        out: list[ViolationEvent] = []
        if gold not in text:
            out.append(ViolationEvent(
                violation_id="v_musique_profile_required_miss",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint=f"answer must reflect required profile fact ({gold})",
                trajectory_text=(final_output or "")[:200],
                severity=Severity.HIGH,
                explanation="profile-derived gold absent",
            ))
        for b in banned:
            if b and b in text:
                out.append(ViolationEvent(
                    violation_id="v_musique_profile_violation",
                    step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                    violated_profile_span_id="p_diet",
                    violated_constraint="answer violates a hard profile constraint",
                    trajectory_text=(final_output or "")[:200],
                    severity=Severity.HIGH,
                    explanation=f"answer contains banned substring {b!r}",
                ))
                break
        return out

    rule.__name__ = "musique_profile_required_3hop_rule"
    return rule


Condition = Literal["factual_3hop", "profile_required_3hop"]
Split = Literal["train", "val", "test", "all"]


@dataclass
class MuSiQueRecon:
    n_examples: int = 100
    seed: int = 0
    split: Split = "all"
    train_frac: float = 0.6
    val_frac: float = 0.2

    @property
    def name(self) -> str:
        return "musique_recon"

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
        rng = random.Random(self.seed * 1_000_013 + idx)
        profile, facts = _build_profile(rng, idx)
        condition: Condition = (
            "factual_3hop" if idx % 2 == 0 else "profile_required_3hop"
        )
        task_id = f"musique_recon_{idx:05d}"

        if condition == "factual_3hop":
            question, gold, aliases = rng.choice(MULTIHOP_3HOP_FACTUAL)
            profile_keywords = [
                facts["dietary"], facts["language"].lower(),
                facts["occupation"], facts["city"][0].lower(),
            ]
            condition_meta = {
                "gold": gold, "allowed_aliases": aliases,
                "profile_keywords": profile_keywords,
            }
            rule = _factual_3hop_rule(condition_meta)
            gold_label = gold
        else:
            tmpl = rng.choice(PROFILE_3HOP_TEMPLATES)
            question = tmpl.question_format
            field_value = facts[tmpl.relevant_field]
            gold_label = tmpl.gold_fn(field_value)
            banned = tmpl.banned_substrings_fn(field_value)
            condition_meta = {"gold": gold_label, "banned": banned}
            rule = _profile_required_3hop_rule(condition_meta)

        task = {
            "task_id": task_id,
            "task_type": "musique",
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


__all__ = ["MuSiQueRecon", "MULTIHOP_3HOP_FACTUAL", "PROFILE_3HOP_TEMPLATES"]
