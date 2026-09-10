"""Food.com recipes real-data loader.

Loads `AkashPS11/recipes_data_food.com` from HuggingFace (an MIT-licensed
mirror of the "Food.com Recipes and Reviews" corpus) and exposes real
recipe rows as `BenchmarkExample` streams, structurally mirroring
`intro_specter/benchmarks/travelplanner_real.py`.

**Data-quality finding (read before trusting the advertised row count)**:
the HF repo's metadata advertises 1,048,543 rows, but direct inspection
(binary search on `Name is not None`) shows only the FIRST 1,228 rows carry
real data -- every row from index 1228 through 1,048,542 is entirely null
(every column, including `Name`). This is a data-quality defect in the HF
mirror itself, not a bug in this loader. We report it honestly rather than
silently sampling from what would mostly be empty rows: the usable pool for
this loader is 1,228 rows, of which 823 carry the full quartet of fields we
need (`TotalTime`, `Calories`, `RecipeServings`, plus a non-empty
`RecipeIngredientParts` list for all but 4 of those 823). 823 real usable
rows is still >4x TravelPlanner's own 180-row validation pool, so sampling
with a seeded RNG (same pattern as `travelplanner_real.py`) over the
qualifying-row index list, with replacement across seeds, is not a
meaningful limitation for n=36-60 examples per condition.

Real native constraint fields used (all directly from the dataset schema,
no synthetic/templated profile bank involved -- this is the "non-synthetic"
analogue of TravelPlanner's native budget/days/local-constraint fields):

* `category`      -- `RecipeCategory` (e.g. "Chicken Breast", "Beverages").
                      Always-on, NOT independently faultable (mirrors
                      TravelPlanner's `destination`): the produced recipe
                      must still plausibly belong to this category, so
                      there is no mechanically-checkable way to "corrupt"
                      it while still requiring the agent's output to match
                      the true category.
* `time_limit`    -- parsed `TotalTime` (ISO-8601 duration, e.g. "PT4H25M")
                      in minutes. Numeric ceiling constraint, directly
                      analogous to TravelPlanner's `budget`.
* `calories`      -- `Calories` (kcal per serving in the source data).
                      Numeric ceiling constraint, second budget-like slot.
* `servings`      -- `RecipeServings`. Numeric exact-match constraint,
                      analogous to TravelPlanner's `days`.
* `excl_ingredient_1` / `excl_ingredient_2`
                  -- one or two ingredients drawn from the real, parsed
                     `RecipeIngredientParts` list, framed as a dietary
                     exclusion ("must NOT use ingredient X"). Categorical
                     constraint, analogous to TravelPlanner's local
                     constraints (cuisine / house_rule / room_type /
                     transportation) -- present only when the row's
                     ingredient list is long enough (>=1 for slot 1, >=2
                     distinct for slot 2).

Verifier rule (single-fault, `_make_rule`): mechanical substring/numeric
checks on the agent's recipe text -- category mention, extracted
"Total time: N minutes" <= true ceiling, extracted "Calories per serving: N"
<= true ceiling, "servings" mention matching the true count, and absence of
each excluded ingredient as a substring. Same "relaxed substring/regex
check on free text, not a full recipe-execution simulator" philosophy
`travelplanner_real.py` itself documents and uses.

Fault injection: single native fault via
`intro_specter.profiles.recipes_native_multi_fault_injection.build_recipe_native_multi_fault`
with `num_faults=1` (see that module for the full N=1..5 multi-fault
design used by the scaled campaign).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Literal

from ..profiles.recipes_native_multi_fault_injection import (
    RecipeNativeMultiFaultRecord,
    build_recipe_native_multi_fault,
    max_faultable_slots,
)
from ..schemas import (
    AssumptionDAG,
    GoldLabels,
    Severity,
    Trajectory,
    UserProfile,
    ViolationEvent,
)
from .base import BenchmarkExample

_HF_DATASET = None

# Direct-inspection finding (binary search on `ds[i]["Name"] is not None`,
# `AkashPS11/recipes_data_food.com`, 2026-07-26): every row from this index
# onward is entirely null. See module docstring.
_LAST_VALID_ROW_EXCLUSIVE = 1228


def _load(split: str = "train") -> Any:
    global _HF_DATASET
    if _HF_DATASET is None or _HF_DATASET[0] != split:
        from datasets import load_dataset
        ds = load_dataset("AkashPS11/recipes_data_food.com", split=split)
        _HF_DATASET = (split, ds)
    return _HF_DATASET[1]


_QUALIFYING_INDICES: list[int] | None = None


def _qualifying_indices() -> list[int]:
    """Row indices (within the valid 0..1227 prefix, see module docstring)
    that carry `TotalTime`, `Calories`, and `RecipeServings` -- the three
    always-required numeric constraint slots. Computed once and cached."""
    global _QUALIFYING_INDICES
    if _QUALIFYING_INDICES is not None:
        return _QUALIFYING_INDICES
    ds = _load("train")
    out = []
    for i in range(min(_LAST_VALID_ROW_EXCLUSIVE, len(ds))):
        row = ds[i]
        if row.get("TotalTime") and row.get("Calories") is not None and row.get("RecipeServings") is not None:
            out.append(i)
    _QUALIFYING_INDICES = out
    return out


_DURATION_RE = re.compile(
    r"^P(?:(?P<days>\d+)D)?T?(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?$"
)


def parse_duration_minutes(s: str | None) -> int | None:
    """Parses an ISO-8601 duration string (e.g. 'PT4H25M', 'PT45M', 'PT24H')
    into total minutes. Returns None if unparseable/empty."""
    if not s:
        return None
    m = _DURATION_RE.match(str(s).strip())
    if not m:
        return None
    d = m.groupdict()
    if not any(d.values()):
        return None
    minutes = 0
    minutes += int(d["days"] or 0) * 24 * 60
    minutes += int(d["hours"] or 0) * 60
    minutes += int(d["minutes"] or 0)
    minutes += int(d["seconds"] or 0) // 60
    return minutes


_R_VECTOR_ITEM_RE = re.compile(r'"(.*?)"')


def parse_r_vector(s: str | None) -> list[str]:
    """Parses the dataset's R-style vector-literal strings, e.g.
    'c("blueberries", "granulated sugar", NA, "lemon juice")' into a
    Python list of strings (skipping bare `NA` tokens with no quotes)."""
    if not s:
        return []
    items = _R_VECTOR_ITEM_RE.findall(str(s))
    return [it.strip() for it in items if it.strip()]


_DISTRACTOR_INGREDIENT_POOL = [
    "peanuts", "shellfish", "soy sauce", "gluten", "dairy", "shrimp",
    "walnuts", "sesame oil", "anchovies", "MSG", "cornstarch", "gelatin",
]


def native_constraints(ex: dict[str, Any]) -> list[tuple[str, str, bool]]:
    """Returns (id, text, is_hard) for every native Food.com constraint
    present on this row -- always-on `category` plus the three numeric
    slots (time_limit/calories/servings) plus 0-2 ingredient-exclusion
    slots depending on how many distinct ingredients the row's
    `RecipeIngredientParts` carries."""
    out: list[tuple[str, str, bool]] = []
    category = ex.get("RecipeCategory")
    if category:
        out.append(("category", f"Recipe must belong to the category: {category}.", True))
    total_min = parse_duration_minutes(ex.get("TotalTime"))
    if total_min is not None:
        out.append(("time_limit", f"Total prep+cook time must not exceed {total_min} minutes.", True))
    calories = ex.get("Calories")
    if calories is not None:
        out.append(("calories", f"Calories per serving must not exceed {calories:.0f} kcal.", True))
    servings = ex.get("RecipeServings")
    if servings is not None:
        out.append(("servings", f"Recipe must serve exactly {int(servings)} people.", True))
    ingredients = parse_r_vector(ex.get("RecipeIngredientParts"))
    if len(ingredients) >= 1:
        out.append(("excl_ingredient_1", f"Recipe must NOT use ingredient: {ingredients[0]}.", True))
    if len(ingredients) >= 2:
        out.append(("excl_ingredient_2", f"Recipe must NOT use ingredient: {ingredients[1]}.", True))
    return out


def _make_rule(meta: dict[str, Any]):
    category = meta["category"]
    banned = [b.lower() for b in meta.get("banned_ingredients", [])]

    def rule(profile, task, trajectory, final_output):
        text = (final_output or "").lower()
        for step in trajectory.steps:
            text += "\n" + (getattr(step, "text", "") or "").lower()
        out: list[ViolationEvent] = []

        if category and category.lower() not in text:
            out.append(ViolationEvent(
                violation_id="v_recipesreal_no_category",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint=f"recipe must belong to category {category!r}",
                trajectory_text=(final_output or "")[:200],
                severity=Severity.MEDIUM,
                explanation="category not mentioned in output",
            ))
        for ing in banned:
            if ing and ing in text:
                out.append(ViolationEvent(
                    violation_id="v_recipesreal_banned_ingredient",
                    step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                    violated_constraint=f"recipe must not use ingredient {ing!r}",
                    trajectory_text=(final_output or "")[:200],
                    severity=Severity.HIGH,
                    explanation=f"output contains banned ingredient {ing!r}",
                ))
        if "total time" not in text and "minutes" not in text:
            out.append(ViolationEvent(
                violation_id="v_recipesreal_no_time",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint="recipe must state total time",
                trajectory_text=(final_output or "")[:200],
                severity=Severity.MEDIUM,
                explanation="no time mention in output",
            ))
        return out

    rule.__name__ = "recipes_real_rule"
    return rule


Split = Literal["train", "val", "test", "all"]


@dataclass
class RecipesReal:
    n_examples: int = 60
    seed: int = 0
    split: Split = "all"
    train_frac: float = 0.6
    val_frac: float = 0.2
    fault_inject: bool = True
    num_faults: int = 1

    @property
    def name(self) -> str:
        return "recipes_real"

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

    def _row_index(self, idx: int) -> int:
        import random
        qualifying = _qualifying_indices()
        rng = random.Random(self.seed * 1_000_033 + idx)
        return qualifying[rng.randrange(len(qualifying))]

    def _build_example(self, idx: int) -> BenchmarkExample:
        ds = _load("train")
        row_idx = self._row_index(idx)
        ex = ds[row_idx]

        task_id = f"recipes_real_{idx:05d}"
        num_faults = self.num_faults if self.fault_inject else 0
        eligible = max_faultable_slots(ex)
        num_faults = min(num_faults, eligible) if num_faults else 0

        mfr: RecipeNativeMultiFaultRecord | None = None
        if num_faults > 0:
            mfr = build_recipe_native_multi_fault(task_id=task_id, ex=ex, num_faults=num_faults)
            spans = mfr.spans
        else:
            from ..schemas import ProfileSpan
            spans = [
                ProfileSpan(id=cid, text=text, kind="constraint", is_hard=is_hard, contradicts=[])
                for cid, text, is_hard in native_constraints(ex)
            ]

        profile = UserProfile(user_id=f"recipes_real_{task_id}", spans=spans)

        ingredients = parse_r_vector(ex.get("RecipeIngredientParts"))
        instructions = parse_r_vector(ex.get("RecipeInstructions"))
        category = ex.get("RecipeCategory") or ""

        prompt = (
            "User dietary/recipe constraints:\n"
            + "\n".join(f"- {s.text}" for s in spans)
            + f"\n\nReal ingredient list on file (for reference, {len(ingredients)} items): "
            f"{', '.join(ingredients[:15])}"
            + (" ..." if len(ingredients) > 15 else "")
            + f"\n\nRecipe category: {category}\n\n"
            "Suggest ONE recipe (a name, full ingredient list with quantities, and "
            "numbered instructions) that satisfies every constraint above. "
            "End with three lines exactly in this form:\n"
            "Total time: <N> minutes\n"
            "Calories per serving: <N>\n"
            "Servings: <N>"
        )

        banned_ingredients = []
        true_values: dict[str, Any] = {}
        corrupted_values: dict[str, Any] = {}
        faulted_slots: list[str] = []
        if mfr is not None:
            banned_ingredients = [
                mfr.true_values[s] for s in mfr.faulted_slots if s.startswith("excl_ingredient")
            ]
            true_values = mfr.true_values
            corrupted_values = mfr.corrupted_values
            faulted_slots = mfr.faulted_slots

        condition_meta = {
            "category": category,
            "native_constraint_count": len(native_constraints(ex)),
            "num_faults": num_faults,
            "faulted_slots": faulted_slots,
            "true_values": true_values,
            "corrupted_values": corrupted_values,
            "banned_ingredients": banned_ingredients,
        }
        rule = _make_rule(condition_meta)

        task = {
            "task_id": task_id,
            "task_type": "recipes_real",
            "condition": f"recipe_native_n{num_faults}_fault" if num_faults else "recipe_native_no_fault",
            "prompt": prompt,
            "split": self.split_of(idx),
            "condition_meta": condition_meta,
        }
        gold = GoldLabels(
            success=None,
            correct_final_output=None,
            fault_node_id=",".join(faulted_slots) if faulted_slots else None,
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


__all__ = [
    "RecipesReal",
    "native_constraints",
    "parse_duration_minutes",
    "parse_r_vector",
]
