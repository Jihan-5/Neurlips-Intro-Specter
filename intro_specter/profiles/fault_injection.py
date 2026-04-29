"""Controlled fault injection for the real-benchmark suite.

For 30 % of trials, we inject one wrong assumption into the agent's
trajectory and record the injected node id as `gold_fault_node`. This
gives us ground-truth attribution labels for the Intro-Specter
posterior.

Four fault types:

* `wrong_value`        — flip a value in an assumption node (e.g., date,
                          number, named entity). For QA: replace one of
                          the gold-supporting facts with a near-neighbor
                          distractor.
* `wrong_constraint`   — replace a profile constraint with a related-but-
                          stricter or related-but-looser one
                          (vegetarian → vegan, low-budget → strict-budget).
                          The agent's assumption about the user becomes
                          incorrect.
* `omitted_constraint` — drop a hard constraint from the agent's working
                          set. The agent acts as if the constraint
                          doesn't exist.
* `hallucinated_pref`  — invent a preference not in the profile (e.g.,
                          "user likes Italian food" when the profile
                          says nothing about Italian food).

The injection is deterministic given (task_id, seed). We mark a trial
as fault-injected with probability ~0.30 using a hash of (task_id, seed).

The fault is applied by the runner BEFORE the IS pipeline runs. The
runner stores `gold_fault_node` in the example metadata so the
aggregator can score attribution top-1 / top-3 / MRR.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import Any, Literal


FaultType = Literal[
    "wrong_value",
    "wrong_constraint",
    "omitted_constraint",
    "hallucinated_pref",
]


@dataclass(frozen=True)
class FaultRecord:
    """Description of an injected fault, recorded so the verifier knows
    what the gold fault is and the aggregator can score attribution."""
    fault_type: FaultType
    target_node_id: str           # id of the assumption node being modified
    original_text: str            # what the node said before injection
    injected_text: str            # what we replaced it with (or "" for omission)
    rationale: str                # human-readable description for analysis


# Probability that a given (task_id, seed) gets fault-injected.
DEFAULT_FAULT_RATE = 0.30


def _should_inject(task_id: str, seed: int, rate: float) -> bool:
    """Deterministic Bernoulli with parameter `rate`."""
    h = hashlib.sha256(f"{task_id}:{seed}".encode()).hexdigest()
    bucket = int(h[:8], 16) / 0xFFFFFFFF
    return bucket < rate


def _wrong_value_pool(answer_text: str) -> list[str]:
    """Cheap near-neighbor generator for `wrong_value` faults."""
    answer_text = (answer_text or "").strip()
    near_neighbors = [
        "approximately " + answer_text,
        "the predecessor of " + answer_text,
        "not " + answer_text,
        answer_text + " (in part)",
    ]
    # Domain-specific near-neighbors for years and yes/no.
    if answer_text.isdigit() and len(answer_text) == 4:
        # Year — flip by ±1 century.
        try:
            y = int(answer_text)
            near_neighbors.append(str(y - 100))
            near_neighbors.append(str(y + 1))
        except ValueError:
            pass
    if answer_text.lower() in {"yes", "no"}:
        near_neighbors = ["no" if answer_text.lower() == "yes" else "yes"]
    return [n for n in near_neighbors if n.strip()]


def inject_fault(
    *,
    task_id: str,
    seed: int,
    profile: dict[str, Any],
    gold_answer: Any,
    candidate_node_ids: list[str] | None = None,
    rate: float = DEFAULT_FAULT_RATE,
) -> FaultRecord | None:
    """Decide whether and how to inject a fault for this trial.

    Returns:
        FaultRecord describing the injection, or None if no fault should
        be injected for this (task_id, seed).

    The returned record is purely *declarative* — the runner consumes
    it and applies the fault to the agent's working trajectory at the
    appropriate point in the pipeline.
    """
    if not _should_inject(task_id, seed, rate):
        return None

    rng = random.Random(f"fault::{task_id}::{seed}")

    # Pick a fault type.
    fault_type = rng.choice([
        "wrong_value",
        "wrong_constraint",
        "omitted_constraint",
        "hallucinated_pref",
    ])

    candidate_node_ids = candidate_node_ids or [f"a{i}" for i in range(3, 7)]
    target = rng.choice(candidate_node_ids)

    if fault_type == "wrong_value":
        pool = _wrong_value_pool(str(gold_answer))
        injected = rng.choice(pool) if pool else "[corrupted value]"
        return FaultRecord(
            fault_type="wrong_value",
            target_node_id=target,
            original_text=str(gold_answer),
            injected_text=injected,
            rationale=f"Replaced gold value {gold_answer!r} with near-neighbor {injected!r}.",
        )

    if fault_type == "wrong_constraint":
        cs = profile.get("constraints", [])
        if not cs:
            return None
        c = rng.choice(cs)
        # Flip the constraint to a stricter near-neighbor.
        flips = {
            "vegetarian": "vegan",
            "vegan": "carnivore",
            "gluten-free": "gluten-required",
            "tree-nut allergy": "peanut allergy",
            "concise": "extremely verbose with citations",
            "English only": "Mandarin only",
            "soft": "hard",  # type-flip for soft constraints
        }
        original = c["text"]
        injected = original
        for k, v in flips.items():
            if k in original:
                injected = original.replace(k, v)
                break
        else:
            injected = original + " — actually, the opposite preference"
        return FaultRecord(
            fault_type="wrong_constraint",
            target_node_id=target,
            original_text=original,
            injected_text=injected,
            rationale=f"Replaced profile constraint {original!r} with conflicting variant {injected!r}.",
        )

    if fault_type == "omitted_constraint":
        cs = [c for c in profile.get("constraints", []) if c.get("type") == "hard"]
        if not cs:
            return None
        c = rng.choice(cs)
        return FaultRecord(
            fault_type="omitted_constraint",
            target_node_id=target,
            original_text=c["text"],
            injected_text="",
            rationale=f"Dropped hard constraint {c['text']!r} from agent's working set.",
        )

    # hallucinated_pref
    invented = rng.choice([
        "User strongly prefers Italian food.",
        "User dislikes any answer mentioning numbers.",
        "User insists on Oxford-comma usage in every reply.",
        "User wants every response prefaced by a haiku.",
        "User considers this question deeply personal.",
    ])
    return FaultRecord(
        fault_type="hallucinated_pref",
        target_node_id=target,
        original_text="",
        injected_text=invented,
        rationale=f"Hallucinated preference {invented!r} not present in profile.",
    )


__all__ = [
    "DEFAULT_FAULT_RATE",
    "FaultRecord",
    "FaultType",
    "inject_fault",
]
