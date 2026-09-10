"""Deterministic profile-corruption operators for Experiment A (profile-noise
robustness rebuttal). Additive-only module — not imported by any existing code.

NOTE on a signature deviation from the original design note: `UserProfile` /
`ProfileSpan` (schemas.py) do not carry `relevant` or `category` — those only
exist on the pre-flattening `ProfileConstraint` dicts inside a benchmark's
`task["condition_meta"]["profile_constraints"]`. So `corrupt_profile` takes an
extra `constraint_meta` mapping (span id -> {"relevant": bool, "category": str})
supplied by the caller, and returns `(UserProfile, list[str])` — the corrupted
profile plus the ids it touched — rather than bare `UserProfile`, since the
caller needs those ids for the experiment's JSONL log and there is no
extra-field-free way to smuggle them onto a `model_config = extra="forbid"`
pydantic object.
"""

from __future__ import annotations

import math
import random
from typing import Any

from .profiles.templates import ADVERSARIAL_TEMPLATES, PROFILE_TEMPLATES, ProfileConstraint
from .schemas import ProfileSpan, UserProfile

_OPERATORS = ("stale_swap", "contradict", "omit")


def _same_family_pool(category: str, exclude_text: str) -> list[ProfileConstraint]:
    """Templates sharing `category`, excluding the current value — the swap pool.

    Searches `PROFILE_TEMPLATES` first, then `ADVERSARIAL_TEMPLATES` (TruthfulQA's
    separate adversarial-constraint bank isn't covered by the same-category search
    over `PROFILE_TEMPLATES` alone), and only falls back to the full combined pool
    if neither bank has a same-category match.
    """
    pool = [t for t in PROFILE_TEMPLATES if t.category == category and t.text != exclude_text]
    if not pool:
        pool = [t for t in ADVERSARIAL_TEMPLATES if t.category == category and t.text != exclude_text]
    if not pool:
        pool = [t for t in PROFILE_TEMPLATES + ADVERSARIAL_TEMPLATES if t.text != exclude_text]
    return pool


def stale_swap(constraint: ProfileSpan, category: str, rng: random.Random) -> ProfileSpan:
    """Replace the span's text/hardness with a same-category template's value."""
    choice = rng.choice(_same_family_pool(category, constraint.text))
    return constraint.model_copy(update={"text": choice.text, "is_hard": choice.type == "hard"})


def contradict(
    constraints: list[ProfileSpan], target: ProfileSpan, category: str, rng: random.Random
) -> list[ProfileSpan]:
    """Append a same-category span with an incompatible value; both remain in the list."""
    choice = rng.choice(_same_family_pool(category, target.text))
    new_span = ProfileSpan(
        id=f"{target.id}_contradict",
        text=choice.text,
        kind=target.kind,
        is_hard=choice.type == "hard",
        contradicts=[target.id],
    )
    return constraints + [new_span]


def omit(constraints: list[ProfileSpan], target_id: str) -> list[ProfileSpan]:
    """Remove `target_id` entirely — never called on a distractor (irrelevant span)."""
    return [s for s in constraints if s.id != target_id]


def corrupt_profile(
    profile: UserProfile,
    rho: float,
    corruption_seed: int,
    constraint_meta: dict[str, dict[str, Any]],
) -> tuple[UserProfile, list[str]]:
    """Corrupt `ceil(rho * n_relevant)` (min 1) relevant spans, deterministically.

    Only spans whose `constraint_meta[id]["relevant"]` is truthy are eligible —
    corrupting a distractor tests nothing about profile-noise robustness.
    Operators are assigned round-robin from [stale_swap, contradict, omit]
    starting at an index derived from `corruption_seed`; all randomness inside
    this call is drawn from a single `random.Random(corruption_seed)`.
    """
    rng = random.Random(corruption_seed)
    spans = list(profile.spans)
    relevant_ids = sorted(s.id for s in spans if constraint_meta.get(s.id, {}).get("relevant"))
    if not relevant_ids:
        return profile.model_copy(deep=True), []

    n_corrupt = min(max(1, math.ceil(rho * len(relevant_ids))), len(relevant_ids))
    targets = rng.sample(relevant_ids, k=n_corrupt)

    start = corruption_seed % len(_OPERATORS)
    corrupted_ids: list[str] = []
    for i, span_id in enumerate(targets):
        op = _OPERATORS[(start + i) % len(_OPERATORS)]
        category = constraint_meta.get(span_id, {}).get("category", "communication")
        if op == "stale_swap":
            idx = next(j for j, s in enumerate(spans) if s.id == span_id)
            spans[idx] = stale_swap(spans[idx], category, rng)
        elif op == "contradict":
            target = next(s for s in spans if s.id == span_id)
            spans = contradict(spans, target, category, rng)
        else:  # omit
            spans = omit(spans, span_id)
        corrupted_ids.append(span_id)

    new_profile = profile.model_copy(update={"spans": spans}, deep=True)
    return new_profile, corrupted_ids


__all__ = ["contradict", "corrupt_profile", "omit", "stale_swap"]
