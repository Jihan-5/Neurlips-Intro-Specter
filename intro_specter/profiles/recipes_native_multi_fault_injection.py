"""Additive multi-fault injector for Food.com recipes' NATIVE (dataset-true,
non-templated) constraints -- prep+cook time, calories, servings, and up to
two ingredient-exclusion slots. This is the recipes-domain analogue of
`intro_specter/profiles/native_multi_fault_injection.py` (built for
TravelPlanner), reimplementing the same "pick N disjoint constraint slots,
corrupt each independently, remember the true value for scoring" pattern
adapted to `intro_specter.benchmarks.recipes_real`'s native fields.

Confirmed feasibility (direct inspection of `AkashPS11/recipes_data_food.com`,
2026-07-26, over the 823 rows that carry `TotalTime`+`Calories`+`RecipeServings`
-- see `recipes_real.py`'s module docstring for the data-quality caveat about
the dataset's mostly-null tail):
    0 ingredients parsed  (4/823):   3 faultable slots (time_limit, calories, servings)
    1 ingredient parsed  (11/823):   4 faultable slots (+excl_ingredient_1)
    >=2 ingredients parsed (808/823): 5 faultable slots (+excl_ingredient_2)
So N=1..3 is achievable on effectively the entire 823-row pool, N=4 on 819/823
rows, and N=5 on 808/823 rows -- all comfortably above the 36-60
examples-per-condition target with headroom for reuse across seeds 0/1/2.
`category` (`RecipeCategory`) is always present on this pool but is
intentionally EXCLUDED as a fault slot, mirroring TravelPlanner's exclusion
of `destination`: there is no mechanically-checkable way to "corrupt" the
category while still requiring the agent's suggested recipe to visibly
belong to it.

Selection order (deterministic, not random): time_limit, calories, servings,
excl_ingredient_1, excl_ingredient_2 -- mirrors
`native_multi_fault_injection.py`'s "slots requested in caller-given order,
first N present" discipline, so N=1 is always just time_limit, N=2 is always
time_limit+calories, etc., across every row that reaches it (content is
deterministic given N; only the underlying row's true values vary).

Corruption strategies:
  time_limit / calories -- numeric ceilings, inflated by a factor in
      [1.4, 2.2] (same factor range as TravelPlanner's `_corrupted_budget`,
      for the same reason: the agent believes it has substantially more
      slack than it really does).
  servings -- additive offset in {+1, +2, +3} (same shape as TravelPlanner's
      `_corrupted_days`).
  excl_ingredient_1 / excl_ingredient_2 -- categorical: the agent is told to
      avoid a DIFFERENT (distractor) ingredient than the one it actually,
      truly must avoid. The true excluded ingredient is drawn from the row's
      own real `RecipeIngredientParts` list; the distractor is drawn from a
      fixed common-ingredient pool, deterministically chosen and never equal
      (case-insensitively) to the true ingredient or to any ingredient
      already in the row's own list (to avoid a distractor that would be
      trivially already-absent-or-present in a way that muddies scoring).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from intro_specter.schemas import ProfileSpan

_SLOT_PRIORITY = ["time_limit", "calories", "servings", "excl_ingredient_1", "excl_ingredient_2"]

_DISTRACTOR_INGREDIENT_POOL = [
    "peanuts", "shellfish", "soy sauce", "gluten", "dairy", "shrimp",
    "walnuts", "sesame oil", "anchovies", "MSG", "cornstarch", "gelatin",
    "cashews", "almonds", "coconut milk", "fish sauce",
]


def _hash_int(*parts: Any) -> int:
    h = hashlib.sha256("::".join(str(p) for p in parts).encode()).hexdigest()
    return int(h[:12], 16)


def _corrupted_ceiling(true_value: float, task_id: str, slot: str) -> float:
    """Inflate by a factor in [1.4, 2.2), same shape as TravelPlanner's
    `_corrupted_budget`."""
    h = _hash_int("recipes_native_multifault", slot, task_id)
    factor = 1.4 + ((h % 1_000_000) / 1_000_000) * 0.8
    return round(true_value * factor, 1)


def _corrupted_servings(true_servings: int, task_id: str) -> int:
    h = _hash_int("recipes_native_multifault_servings", task_id)
    offset = 1 + (h % 3)  # 1, 2, or 3
    return true_servings + offset


def _corrupted_ingredient(true_ingredient: str, all_ingredients: list[str], task_id: str, slot: str) -> str:
    lower_recipe = {i.strip().lower() for i in all_ingredients}
    candidates = [
        c for c in _DISTRACTOR_INGREDIENT_POOL
        if c.strip().lower() != true_ingredient.strip().lower() and c.strip().lower() not in lower_recipe
    ]
    if not candidates:
        candidates = _DISTRACTOR_INGREDIENT_POOL
    h = _hash_int("recipes_native_multifault_ing", slot, task_id)
    return candidates[h % len(candidates)]


@dataclass(frozen=True)
class RecipeNativeMultiFaultRecord:
    task_id: str
    native_constraint_count: int
    num_faults: int
    faulted_slots: list[str]
    true_values: dict[str, Any]
    corrupted_values: dict[str, Any]
    spans: list[ProfileSpan]


def max_faultable_slots(ex: dict[str, Any]) -> int:
    """How many of `_SLOT_PRIORITY`'s slots are present on this row --
    the ceiling on `num_faults` a caller may request for it."""
    from intro_specter.benchmarks.recipes_real import native_constraints
    present_ids = {cid for cid, _, _ in native_constraints(ex)}
    return sum(1 for slot in _SLOT_PRIORITY if slot in present_ids)


def build_recipe_native_multi_fault(
    *, task_id: str, ex: dict[str, Any], num_faults: int,
) -> RecipeNativeMultiFaultRecord:
    """Builds `num_faults` independent, genuinely-applied faults on the
    native Food.com constraints for one row. Raises `RuntimeError` if the
    row has fewer than `num_faults` eligible slots -- callers must
    pre-filter (see module docstring for real per-slot-count availability)."""
    from intro_specter.benchmarks.recipes_real import native_constraints, parse_duration_minutes, parse_r_vector

    native = native_constraints(ex)
    native_by_id = {cid: (text, is_hard) for cid, text, is_hard in native}
    present_slots = [s for s in _SLOT_PRIORITY if s in native_by_id]
    if num_faults > len(present_slots):
        raise RuntimeError(
            f"build_recipe_native_multi_fault: task_id={task_id!r} has only {len(present_slots)} "
            f"faultable slots ({present_slots}), requested num_faults={num_faults}"
        )
    faulted_slots = present_slots[:num_faults]

    ingredients = parse_r_vector(ex.get("RecipeIngredientParts"))
    true_values: dict[str, Any] = {}
    corrupted_values: dict[str, Any] = {}
    spans: list[ProfileSpan] = []

    for cid, text, is_hard in native:
        if cid == "time_limit":
            true_minutes = parse_duration_minutes(ex.get("TotalTime"))
            true_values["time_limit"] = true_minutes
            if cid in faulted_slots:
                corrupted = _corrupted_ceiling(float(true_minutes), task_id, cid)
                corrupted_values["time_limit"] = corrupted
                text = f"Total prep+cook time must not exceed {corrupted:.0f} minutes."
        elif cid == "calories":
            true_cal = float(ex["Calories"])
            true_values["calories"] = true_cal
            if cid in faulted_slots:
                corrupted = _corrupted_ceiling(true_cal, task_id, cid)
                corrupted_values["calories"] = corrupted
                text = f"Calories per serving must not exceed {corrupted:.0f} kcal."
        elif cid == "servings":
            true_serv = int(ex["RecipeServings"])
            true_values["servings"] = true_serv
            if cid in faulted_slots:
                corrupted = _corrupted_servings(true_serv, task_id)
                corrupted_values["servings"] = corrupted
                text = f"Recipe must serve exactly {corrupted} people."
        elif cid == "excl_ingredient_1":
            true_ing = ingredients[0]
            true_values["excl_ingredient_1"] = true_ing
            if cid in faulted_slots:
                corrupted = _corrupted_ingredient(true_ing, ingredients, task_id, cid)
                corrupted_values["excl_ingredient_1"] = corrupted
                text = f"Recipe must NOT use ingredient: {corrupted}."
        elif cid == "excl_ingredient_2":
            true_ing = ingredients[1]
            true_values["excl_ingredient_2"] = true_ing
            if cid in faulted_slots:
                corrupted = _corrupted_ingredient(true_ing, ingredients, task_id, cid)
                corrupted_values["excl_ingredient_2"] = corrupted
                text = f"Recipe must NOT use ingredient: {corrupted}."
        spans.append(ProfileSpan(id=cid, text=text, kind="constraint", is_hard=is_hard, contradicts=[]))

    return RecipeNativeMultiFaultRecord(
        task_id=task_id,
        native_constraint_count=len(native),
        num_faults=num_faults,
        faulted_slots=faulted_slots,
        true_values=true_values,
        corrupted_values=corrupted_values,
        spans=spans,
    )


__all__ = [
    "RecipeNativeMultiFaultRecord",
    "build_recipe_native_multi_fault",
    "max_faultable_slots",
]
