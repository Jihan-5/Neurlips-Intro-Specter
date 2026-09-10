"""Additive multi-fault injector for TravelPlanner's NATIVE (dataset-true,
non-templated) constraints -- budget, trip length ("days"), and whichever
local constraints (cuisine / house rule / room type / transportation) a given
row carries.

Why this file exists
---------------------
`double_fault_injection.py::build_multi_fault` already generalizes
single-fault injection to N independent faults, but it is wired to the
TEMPLATED profile-dict shape produced by `profiles.templates.inject_profile`
(`{"constraints": [{"id","text","type","relevant","category"}, ...]}`) and to
`fault_injection.py::inject_fault`'s `wrong_value` / `wrong_constraint`
mechanisms, which operate on that same templated shape and on a scalar
`gold_answer`. TravelPlanner's native constraints are represented as
`ProfileSpan`s built directly from HuggingFace dataset row fields (see
`scripts/rebuttal_experiment_c_nonsynthetic_travelplanner.py::_native_constraints`,
which this module's `_native_constraints` is a copy of) -- there is no
"gold_answer" and no templated dict to feed `inject_fault`, so that mechanism
cannot be reused directly. This module reimplements the SAME "pick N disjoint
constraint slots, corrupt each independently, remember the true value for
scoring" pattern `build_multi_fault` uses, adapted to act directly on native
`ProfileSpan` lists.

Confirmed feasibility (measured in `rebuttal_experiment_c_nonsynthetic_travelplanner.py`'s
investigation, `osunlp/TravelPlanner` validation split, 180 rows):
    level=easy   (60/180): 3 native constraints (budget, days, destination)
    level=medium (60/180): 4 native constraints (+1 local constraint)
    level=hard   (60/180): 6 native constraints (+3 local constraints)
100% of rows have >=3 native constraints; "destination" is always present but
is NOT used as a fault slot here (there is no mechanically-checkable way to
"corrupt" a destination the agent must still visit -- the plan text
necessarily names it). The corruptible/checkable slots are:
    budget          (numeric ceiling)   -- present in 100% of rows
    days            (numeric exact)     -- present in 100% of rows
    cuisine         (categorical)       -- present only when local constraint set
    house_rule      (categorical)       -- present only when local constraint set
    room_type       (categorical)       -- present only when local constraint set
    transportation  (categorical)       -- present only when local constraint set
So the maximum independently-faultable slot count per row is 2 (easy),
3 (medium), or 5 (hard) -- one less than `native_constraint_count` in each
case, because "destination" is excluded. Callers must request `num_faults`
no larger than what a given row supports; `build_native_multi_fault` raises
`RuntimeError` (mirroring `build_multi_fault`'s "no eligible constraints"
error) if asked for more than the row has -- callers are expected to
pre-filter by `level`/`max_faultable_slots` exactly like every other
fault-count feasibility check in this campaign ("sample only from levels
with enough constraints, report real availability, don't force").

Selection order (deterministic, not random): budget, days, then whichever
local constraints are present in the fixed order (cuisine, house_rule,
room_type, transportation). This mirrors `build_multi_fault`'s "slots
requested in caller-given order, first N present" discipline and keeps N=2
identical in content across every row that reaches it (always
budget+days), so N is the only thing that varies between cells.

Corruption + resolution-check discipline
------------------------------------------
`fault_injection.py` / `double_fault_injection.py` are untouched; this module
does not call them. Corruption strategies below are the direct native-field
analogue of `_corrupted_budget` (already built in
`rebuttal_experiment_c_nonsynthetic_travelplanner.py`), generalized per slot
type. This module ONLY builds the corrupted constraint set + records the true
values; it deliberately does NOT implement resolution-checking (whether the
final plan actually satisfies the true value) -- that stays in the calling
script, same separation of concerns `double_fault_injection.py` uses (it
builds `FaultRecord`s; the calling script decides what "resolved" means for
its own verifier/rule).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from intro_specter.schemas import ProfileSpan

# ---------------------------------------------------------------------------
# Native constraint enumeration (copy of the logic already built in
# rebuttal_experiment_c_nonsynthetic_travelplanner.py::_native_constraints,
# duplicated here rather than imported so this module has no dependency on a
# script file, and so the rebuttal script itself stays untouched).
# ---------------------------------------------------------------------------

_LOCAL_KEYS = ("cuisine", "house rule", "room type", "transportation")


def native_constraints(ex: dict[str, Any], local: dict[str, Any]) -> list[tuple[str, str, bool]]:
    """Returns (id, text, is_hard) for every native TravelPlanner constraint
    present on this row -- the always-on 3 (budget/days/destination) plus
    whichever local constraints are non-null."""
    out = [
        ("budget", f"Total trip budget must not exceed ${ex['budget']}.", True),
        ("days", f"Trip must span exactly {ex['days']} day(s), from {ex['org']} to {ex['dest']}.", True),
        ("destination", f"Destination is {ex['dest']} (departing from {ex['org']}).", True),
    ]
    for key in _LOCAL_KEYS:
        val = local.get(key)
        if val not in (None, "None", ""):
            out.append((key.replace(" ", "_"), f"{key.capitalize()} constraint: {val}.", True))
    return out


# Fixed slot-selection priority: budget and days first (always present),
# then local constraints in a fixed order. "destination" is intentionally
# excluded -- see module docstring.
_SLOT_PRIORITY = ["budget", "days", "cuisine", "house_rule", "room_type", "transportation"]

_CUISINE_POOL = ["Chinese", "Italian", "Mexican", "Indian", "French", "Japanese", "American", "Thai", "Greek"]
_HOUSE_RULE_POOL = [
    "No parties", "No smoking", "No pets", "No visitors", "No unregistered guests",
    "Quiet hours after 10pm", "No children under 10",
]
_ROOM_TYPE_POOL = ["Entire home/apt", "Private room", "Shared room"]
_TRANSPORTATION_POOL = ["self-driving", "flight", "taxi", "train"]

_CATEGORICAL_POOLS = {
    "cuisine": _CUISINE_POOL,
    "house_rule": _HOUSE_RULE_POOL,
    "room_type": _ROOM_TYPE_POOL,
    "transportation": _TRANSPORTATION_POOL,
}


def _hash_int(*parts: Any) -> int:
    h = hashlib.sha256("::".join(str(p) for p in parts).encode()).hexdigest()
    return int(h[:12], 16)


def _corrupted_budget(true_budget: int, task_id: str) -> int:
    """Unmodified-in-spirit copy of the single-fault script's
    `_corrupted_budget`: inflate by a factor in [1.4, 2.2], round to nearest
    50 -- the agent believes it has substantially MORE money than it does."""
    h = _hash_int("tp_native_multifault_budget", task_id)
    factor = 1.4 + ((h % 1_000_000) / 1_000_000) * 0.8  # in [1.4, 2.2)
    corrupted = int(round(true_budget * factor / 50.0) * 50)
    return max(corrupted, true_budget + 100)


def _corrupted_days(true_days: int, task_id: str) -> int:
    """Additive offset in {+1, +2, +3} (deterministic per task_id) -- the
    agent is told the trip is LONGER than it really is, so a plan sized to
    the (wrong) stated length will, if uncorrected, either overspend the
    (also possibly wrong) budget on extra days or produce a plan that
    doesn't match the TRUE day count the verifier checks against."""
    h = _hash_int("tp_native_multifault_days", task_id)
    offset = 1 + (h % 3)  # 1, 2, or 3
    return true_days + offset


def _corrupted_categorical(slot: str, true_value: str, task_id: str) -> str:
    """Deterministically pick a different value from the slot's pool (never
    equal to the true value, case-insensitively)."""
    pool = _CATEGORICAL_POOLS[slot]
    candidates = [v for v in pool if v.strip().lower() != true_value.strip().lower()]
    if not candidates:
        candidates = pool  # degenerate pool; should not happen in practice
    h = _hash_int("tp_native_multifault_cat", slot, task_id)
    return candidates[h % len(candidates)]


@dataclass(frozen=True)
class NativeMultiFaultRecord:
    task_id: str
    level: str
    native_constraint_count: int
    num_faults: int
    faulted_slots: list[str]                    # ids of the corrupted slots, in selection order
    true_values: dict[str, Any]                 # slot -> true value (int for budget/days, str otherwise)
    corrupted_values: dict[str, Any]             # slot -> corrupted value shown to the agent
    spans: list[ProfileSpan]                     # FULL constraint span list, corrupted ones overwritten
    query_substitutions: list[tuple[str, str]]   # (true_str, corrupted_str) pairs applied to `query` text


def max_faultable_slots(ex: dict[str, Any], local: dict[str, Any]) -> int:
    """How many of `_SLOT_PRIORITY`'s slots are actually present on this row
    -- i.e. the ceiling on `num_faults` a caller may request for it."""
    native = native_constraints(ex, local)
    present_ids = {cid for cid, _, _ in native}
    return sum(1 for slot in _SLOT_PRIORITY if slot in present_ids)


def build_native_multi_fault(
    *, task_id: str, ex: dict[str, Any], local: dict[str, Any], num_faults: int,
) -> NativeMultiFaultRecord:
    """Builds `num_faults` independent, genuinely-applied faults on the
    native TravelPlanner constraints for one row, selecting slots via the
    fixed `_SLOT_PRIORITY` order (first `num_faults` present slots).
    Raises `RuntimeError` if the row has fewer than `num_faults` eligible
    slots -- callers must pre-filter by level (see module docstring)."""
    native = native_constraints(ex, local)
    native_by_id = {cid: (text, is_hard) for cid, text, is_hard in native}
    present_slots = [s for s in _SLOT_PRIORITY if s in native_by_id]
    if num_faults > len(present_slots):
        raise RuntimeError(
            f"build_native_multi_fault: task_id={task_id!r} has only {len(present_slots)} "
            f"faultable slots ({present_slots}), requested num_faults={num_faults}"
        )
    faulted_slots = present_slots[:num_faults]

    true_values: dict[str, Any] = {}
    corrupted_values: dict[str, Any] = {}
    query_subs: list[tuple[str, str]] = []

    spans: list[ProfileSpan] = []
    for cid, text, is_hard in native:
        if cid == "budget":
            true_budget = int(ex["budget"])
            true_values["budget"] = true_budget
            if "budget" in faulted_slots:
                corrupted = _corrupted_budget(true_budget, task_id)
                corrupted_values["budget"] = corrupted
                text = f"Total trip budget must not exceed ${corrupted}."
                query_subs.append((f"${true_budget:,}", f"${corrupted:,}"))
                query_subs.append((f"${true_budget}", f"${corrupted}"))
        elif cid == "days":
            true_days = int(ex["days"])
            true_values["days"] = true_days
            if "days" in faulted_slots:
                corrupted = _corrupted_days(true_days, task_id)
                corrupted_values["days"] = corrupted
                text = f"Trip must span exactly {corrupted} day(s), from {ex['org']} to {ex['dest']}."
                query_subs.append((f"{true_days}-day", f"{corrupted}-day"))
                query_subs.append((f"{true_days} day", f"{corrupted} day"))
        elif cid in _CATEGORICAL_POOLS:
            true_value = local.get(cid.replace("_", " ")) or local.get(cid) or ""
            true_values[cid] = true_value
            if cid in faulted_slots:
                corrupted = _corrupted_categorical(cid, str(true_value), task_id)
                corrupted_values[cid] = corrupted
                label = cid.replace("_", " ").capitalize()
                text = f"{label} constraint: {corrupted}."
        spans.append(ProfileSpan(id=cid, text=text, kind="constraint", is_hard=is_hard, contradicts=[]))

    return NativeMultiFaultRecord(
        task_id=task_id,
        level=str(ex.get("level", "easy")),
        native_constraint_count=len(native),
        num_faults=num_faults,
        faulted_slots=faulted_slots,
        true_values=true_values,
        corrupted_values=corrupted_values,
        spans=spans,
        query_substitutions=query_subs,
    )


__all__ = [
    "NativeMultiFaultRecord",
    "build_native_multi_fault",
    "max_faultable_slots",
    "native_constraints",
]
