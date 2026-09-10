"""Experiment D (rebuttal campaign): N-fault synthetic Assumption-DAG.

Reviewer LDZz asked how Intro-Specter handles *multiple* violations along one
trajectory. `synthetic_dag.py` only ever injects a **single** fault per graph
(`single_fault` / `multi_valid` modes). This module is an ADDITIVE extension
(a new file -- `synthetic_dag.py` itself is not touched) that builds a third
mode, ``multi_fault``: a configurable ``num_faults`` (2..5) independently
injected, independently propagating faults per graph, in the same "MANUAL
node, not re-derivable from upstream" style as `_single_fault_graph` (so
attribution is discriminating for every fault, matching the single-fault
protocol rather than the cost-efficiency-flavoured `multi_valid` protocol).

Everything downstream of graph construction (posterior attribution, SPR,
selective re-execution, verifier) is 100% reused from the existing library
(`intro_specter.attribution`, `intro_specter.repair`, `intro_specter.pipeline`)
via `MealPlanningDomain`'s existing *generic* `make_swap_fn` / `make_evaluator`
/ `make_rerun_fn` closures (those methods only take a `ComputeGraph` + value
maps -- they were already mode-agnostic, so no subclassing or modification of
`MealPlanningDomain` is needed either).

Graph layout, N branches (branch 1 always the 5-node "dietary" shape from the
original 2-fault build, branches 2..N a lighter 2-node "axis -> MANUAL fault"
shape, one independent hard profile constraint per branch, all joined only at
the terminal recommendation node):

    a1  (dietary, FUNCTION)  --> a3 (cuisine) --> a4 (restaurant)
    a1 + a4                  --> a5 (dish, MANUAL)          [fault #1 target]
    a2  (budget, FUNCTION)   -- distractor, no downstream edges

    a1b (allergy, FUNCTION)  --> a3b (prep style) --> a4b (station)
    a1b + a4b                --> a7 (side dish, MANUAL)     [fault #2 target]

    a1c (sensitivity, FUNCTION) + a4 --> a7c (topping, MANUAL)   [fault #3]
    a1d (temp_pref, FUNCTION)   + a4 --> a7d (beverage, MANUAL)  [fault #4]
    a1e (sugar_pref, FUNCTION)  + a4 --> a7e (dessert, MANUAL)   [fault #5]

    a4 + <fault node of every active branch>  --> terminal (FUNCTION, OUTPUT)

Because every fault sits on a structurally disjoint MANUAL node whose
downstream zone only rejoins at the terminal node, swapping any single fault
node alone can only ever clear *its own* violation -- this is exactly the
property Experiment D's "genuinely interacting" metric is designed to surface
(see scripts/rebuttal_experiment_d.py).

`num_faults=2` reproduces the exact original 2-fault graph shape/node ids
(branch 1 + branch 2/"allergy") for full backward compatibility with the
existing Experiment D scripts, which all call `build_multi_fault_example`
with the default `num_faults=2`.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Callable

from ..schemas import (
    Provenance,
    ProfileSpan,
    StepKind,
    Trajectory,
    UserProfile,
)
from .synthetic_dag import (
    BUDGET_TIERS,
    CUISINES,
    DISH_FOR_DIETARY,
    DIETARY_BANNED,
    LOCATIONS,
    USER_DIETARY_CLASSES,
    WRONG_DISH_FOR_DIETARY,
    ComputeGraph,
    MealPlanningDomain,
    NodeKind,
    _NodeSpec,
)

# ---------------------------------------------------------------------------
# Second independent hard-constraint dimension: allergy (mirrors DIETARY_*)
# ---------------------------------------------------------------------------

ALLERGY_CLASSES = ["nut_free", "shellfish_free", "gluten_free"]

ALLERGY_BANNED: dict[str, list[str]] = {
    "nut_free": ["peanut", "almond", "cashew", "walnut", "pistachio", "hazelnut"],
    "shellfish_free": ["shrimp", "crab", "lobster", "clam", "oyster"],
    "gluten_free": ["wheat", "barley", "seitan", "breaded noodles", "soy sauce"],
}

SIDE_FOR_ALLERGY: dict[str, str] = {
    "nut_free": "steamed rice",
    "shellfish_free": "garden salad",
    "gluten_free": "quinoa pilaf",
}

# Direct override side dish used in multi_fault mode -- always banned for the
# corresponding allergy, same contract as WRONG_DISH_FOR_DIETARY.
WRONG_SIDE_FOR_ALLERGY: dict[str, str] = {
    "nut_free": "cashew stir-fry",
    "shellfish_free": "shrimp skewers",
    "gluten_free": "seitan noodles",
}

PREP_STYLES = ["grilled", "baked", "fried", "steamed"]

# ---------------------------------------------------------------------------
# Extra independent hard-constraint dimensions (branches 3/4/5, letters c/d/e)
# ---------------------------------------------------------------------------


def _extra_axis_configs() -> list[dict[str, Any]]:
    """Three additional independent-constraint axes, each with the same
    contract as the allergy axis: classes / banned-substrings / gold-correct
    item / always-banned wrong-override item / profile span text. Defined as
    a function (not a module constant) purely so the lambdas below don't leak
    into `__all__` namespace confusion; the returned list is deterministic."""
    return [
        {
            "letter": "c",
            "facts_key": "sensitivity",
            "item_key": "topping",
            "classes": ["dairy_sensitive", "soy_sensitive", "citrus_sensitive"],
            "banned": {
                "dairy_sensitive": ["cream sauce", "cheese drizzle", "butter glaze"],
                "soy_sensitive": ["soy glaze", "tofu topping", "edamame"],
                "citrus_sensitive": ["lemon zest", "lime drizzle", "orange reduction"],
            },
            "item_for_class": {
                "dairy_sensitive": "olive oil drizzle",
                "soy_sensitive": "herb topping",
                "citrus_sensitive": "balsamic drizzle",
            },
            "wrong_item_for_class": {
                "dairy_sensitive": "cream sauce topping",
                "soy_sensitive": "soy glaze topping",
                "citrus_sensitive": "lemon zest topping",
            },
            "span_text": lambda v: f"User is sensitive to {v.replace('_sensitive', '')}",
        },
        {
            "letter": "d",
            "facts_key": "temp_pref",
            "item_key": "beverage",
            "classes": ["hot_only", "cold_only", "room_temp_only"],
            "banned": {
                "hot_only": ["iced", "chilled beverage", "cold brew"],
                "cold_only": ["piping hot", "steaming hot", "boiling"],
                "room_temp_only": ["iced", "piping hot"],
            },
            "item_for_class": {
                "hot_only": "hot herbal tea",
                "cold_only": "iced herbal tea",
                "room_temp_only": "room-temperature water",
            },
            "wrong_item_for_class": {
                "hot_only": "iced herbal tea",
                "cold_only": "piping hot tea",
                "room_temp_only": "iced herbal tea",
            },
            "span_text": lambda v: f"User only drinks {v.replace('_', ' ')} beverages",
        },
        {
            "letter": "e",
            "facts_key": "sugar_pref",
            "item_key": "dessert",
            "classes": ["sugar_free", "low_sugar", "no_restriction"],
            "banned": {
                "sugar_free": ["caramel sauce", "sugar syrup", "candied topping"],
                "low_sugar": ["caramel sauce", "sugar syrup"],
                "no_restriction": ["artificial sweetener"],
            },
            "item_for_class": {
                "sugar_free": "sugar-free jello",
                "low_sugar": "fresh fruit cup",
                "no_restriction": "classic dessert",
            },
            "wrong_item_for_class": {
                "sugar_free": "caramel sauce sundae",
                "low_sugar": "candied topping sundae",
                "no_restriction": "artificial sweetener treat",
            },
            "span_text": lambda v: f"User prefers {v.replace('_', ' ')} desserts",
        },
    ]


MAX_FAULTS = 5
MIN_FAULTS = 2


def _check_num_faults(num_faults: int) -> None:
    if not (MIN_FAULTS <= num_faults <= MAX_FAULTS):
        raise ValueError(
            f"num_faults must be in [{MIN_FAULTS}, {MAX_FAULTS}], got {num_faults}"
        )


def fault_node_ids_for(num_faults: int) -> tuple[str, ...]:
    """The MANUAL fault-node ids that will exist in a graph built with
    `build_multi_fault_graph(num_faults)`, in branch order."""
    _check_num_faults(num_faults)
    ids = ["a5"]
    if num_faults >= 2:
        ids.append("a7")
    for cfg in _extra_axis_configs()[: max(0, num_faults - 2)]:
        ids.append(f"a7{cfg['letter']}")
    return tuple(ids)


@dataclass
class MultiFaultFacts:
    profile: UserProfile
    gold_facts: dict[str, str]


def generate_multi_fault_facts(
    rng: random.Random, idx: int, num_faults: int = 2
) -> MultiFaultFacts:
    """Independent draw of one class value per branch (dietary, allergy, and
    any extra axes up to `num_faults`) so every hard constraint -- and
    therefore every injected fault -- is causally unrelated to the others."""
    _check_num_faults(num_faults)
    dietary = rng.choice(USER_DIETARY_CLASSES)
    budget = rng.choice(BUDGET_TIERS)
    cuisine = rng.choice(CUISINES)
    location = rng.choice(LOCATIONS)
    restaurant = f"{cuisine.title()} House {rng.randint(1, 50)}"

    spans = [
        ProfileSpan(
            id="p_diet",
            text=f"User is {dietary}",
            kind="constraint",
            is_hard=True,
            contradicts=list(DIETARY_BANNED[dietary]),
        ),
        ProfileSpan(
            id="p_budget",
            text=f"User prefers {budget}-budget options",
            kind="preference",
            is_hard=False,
        ),
        ProfileSpan(
            id="p_cuisine",
            text=f"User likes {cuisine} cuisine",
            kind="preference",
            is_hard=False,
        ),
        ProfileSpan(
            id="p_location",
            text=f"User is currently in {location}",
            kind="fact",
            is_hard=False,
        ),
    ]
    facts = {
        "dietary": dietary,
        "budget": budget,
        "cuisine": cuisine,
        "restaurant": restaurant,
        "location": location,
        "dish": DISH_FOR_DIETARY[dietary],
    }

    if num_faults >= 2:
        allergy = rng.choice(ALLERGY_CLASSES)
        prep_style = rng.choice(PREP_STYLES)
        station = f"{prep_style} station {rng.randint(1, 20)}"
        spans.append(
            ProfileSpan(
                id="p_allergy",
                text=f"User has a {allergy.replace('_', ' ')} allergy",
                kind="constraint",
                is_hard=True,
                contradicts=list(ALLERGY_BANNED[allergy]),
            )
        )
        facts.update(
            {
                "allergy": allergy,
                "prep_style": prep_style,
                "station": station,
                "side": SIDE_FOR_ALLERGY[allergy],
            }
        )

    for cfg in _extra_axis_configs()[: max(0, num_faults - 2)]:
        cls = rng.choice(cfg["classes"])
        span_id = f"p_{cfg['facts_key']}"
        spans.append(
            ProfileSpan(
                id=span_id,
                text=cfg["span_text"](cls),
                kind="constraint",
                is_hard=True,
                contradicts=list(cfg["banned"][cls]),
            )
        )
        facts[cfg["facts_key"]] = cls
        facts[cfg["item_key"]] = cfg["item_for_class"][cls]

    profile = UserProfile(user_id=f"user_mf_{idx:04d}", spans=spans)
    return MultiFaultFacts(profile=profile, gold_facts=facts)


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------


def _make_extra_branch_nodes(cfg: dict[str, Any], *, step_id_root: int, step_id_fault: int) -> list[_NodeSpec]:
    letter = cfg["letter"]
    facts_key = cfg["facts_key"]
    item_key = cfg["item_key"]
    span_id = f"p_{facts_key}"
    root = _NodeSpec(
        node_id=f"a1{letter}", step_id=step_id_root, kind=NodeKind.FUNCTION,
        inputs=[], provenance=Provenance.PROFILE,
        profile_span_ids=[span_id], confidence=1.0,
        compute=lambda inp, f, _k=facts_key: f[_k],
        render_step=lambda v: f"Profile flags a {v.replace('_', ' ')} constraint.",
        render_assumption=lambda v: f"The user's constraint value is {v.replace('_', ' ')}.",
        step_kind=StepKind.OBSERVATION,
    )
    fault = _NodeSpec(
        node_id=f"a7{letter}", step_id=step_id_fault, kind=NodeKind.MANUAL,
        inputs=[f"a1{letter}", "a4"], provenance=Provenance.MODEL_INFERRED,
        profile_span_ids=[span_id], confidence=0.6,
        compute=lambda inp, f, _k=item_key: f[_k],
        render_step=lambda v: f"Selected item: {v}.",
        render_assumption=lambda v: f"{v} is safe given the user's constraint.",
    )
    return [root, fault]


def build_multi_fault_graph(num_faults: int = 2) -> ComputeGraph:
    """`num_faults` (2..5) independent MANUAL-node fault branches joined only
    at the terminal recommendation node. See module docstring for the shape.
    `num_faults=2` reproduces the original 2-fault graph exactly."""
    _check_num_faults(num_faults)

    nodes: list[_NodeSpec] = [
        # ---- branch 1: dietary -> cuisine -> restaurant -> dish (MANUAL) ----
        _NodeSpec(
            node_id="a1", step_id=1, kind=NodeKind.FUNCTION,
            inputs=[], provenance=Provenance.PROFILE,
            profile_span_ids=["p_diet"], confidence=1.0,
            compute=lambda inp, f: f["dietary"],
            render_step=lambda v: f"Profile says user is {v}.",
            render_assumption=lambda v: f"The user is {v}.",
            step_kind=StepKind.OBSERVATION,
        ),
        _NodeSpec(
            node_id="a2", step_id=2, kind=NodeKind.FUNCTION,
            inputs=[], provenance=Provenance.PROFILE,
            profile_span_ids=["p_budget"], confidence=1.0,
            compute=lambda inp, f: f["budget"],
            render_step=lambda v: f"Profile says user prefers {v}-budget.",
            render_assumption=lambda v: f"The user prefers {v}-budget options.",
            step_kind=StepKind.OBSERVATION,
        ),
        _NodeSpec(
            node_id="a3", step_id=3, kind=NodeKind.FUNCTION,
            inputs=["a1"], provenance=Provenance.MODEL_INFERRED,
            profile_span_ids=["p_cuisine"], confidence=0.7,
            compute=lambda inp, f: f["cuisine"],
            render_step=lambda v: f"Selected cuisine: {v}.",
            render_assumption=lambda v: f"The cuisine should be {v}.",
        ),
        _NodeSpec(
            node_id="a4", step_id=4, kind=NodeKind.FUNCTION,
            inputs=["a3"], provenance=Provenance.TOOL,
            profile_span_ids=[], confidence=0.85,
            compute=lambda inp, f: f["restaurant"],
            render_step=lambda v: f"Selected restaurant: {v}.",
            render_assumption=lambda v: f"{v} is a good option for the cuisine.",
        ),
        _NodeSpec(
            node_id="a5", step_id=5, kind=NodeKind.MANUAL,
            inputs=["a1", "a4"], provenance=Provenance.MODEL_INFERRED,
            profile_span_ids=["p_diet"], confidence=0.6,
            compute=lambda inp, f: f["dish"],
            render_step=lambda v: f"Selected dish: {v}.",
            render_assumption=lambda v: f"{v} is suitable for the user.",
        ),
    ]
    edges: list[tuple[str, str]] = [
        ("a1", "a3"), ("a3", "a4"), ("a1", "a5"), ("a4", "a5"),
    ]
    fault_ids = ["a5"]
    terminal_inputs = ["a4", "a5"]
    next_step_id = 6

    if num_faults >= 2:
        nodes.extend([
            _NodeSpec(
                node_id="a1b", step_id=next_step_id, kind=NodeKind.FUNCTION,
                inputs=[], provenance=Provenance.PROFILE,
                profile_span_ids=["p_allergy"], confidence=1.0,
                compute=lambda inp, f: f["allergy"],
                render_step=lambda v: f"Profile flags a {v.replace('_', ' ')} allergy.",
                render_assumption=lambda v: f"The user has a {v.replace('_', ' ')} allergy.",
                step_kind=StepKind.OBSERVATION,
            ),
            _NodeSpec(
                node_id="a3b", step_id=next_step_id + 1, kind=NodeKind.FUNCTION,
                inputs=["a1b"], provenance=Provenance.MODEL_INFERRED,
                profile_span_ids=[], confidence=0.7,
                compute=lambda inp, f: f["prep_style"],
                render_step=lambda v: f"Selected prep style: {v}.",
                render_assumption=lambda v: f"The side should be {v}.",
            ),
            _NodeSpec(
                node_id="a4b", step_id=next_step_id + 2, kind=NodeKind.FUNCTION,
                inputs=["a3b"], provenance=Provenance.TOOL,
                profile_span_ids=[], confidence=0.85,
                compute=lambda inp, f: f["station"],
                render_step=lambda v: f"Prep assigned to: {v}.",
                render_assumption=lambda v: f"{v} handles the side dish.",
            ),
            _NodeSpec(
                node_id="a7", step_id=next_step_id + 3, kind=NodeKind.MANUAL,
                inputs=["a1b", "a4b"], provenance=Provenance.MODEL_INFERRED,
                profile_span_ids=["p_allergy"], confidence=0.6,
                compute=lambda inp, f: f["side"],
                render_step=lambda v: f"Selected side dish: {v}.",
                render_assumption=lambda v: f"{v} is safe for the user's allergy.",
            ),
        ])
        edges.extend([
            ("a1b", "a3b"), ("a3b", "a4b"), ("a1b", "a7"), ("a4b", "a7"),
        ])
        fault_ids.append("a7")
        terminal_inputs.append("a7")
        next_step_id += 4

    for cfg in _extra_axis_configs()[: max(0, num_faults - 2)]:
        branch_nodes = _make_extra_branch_nodes(
            cfg, step_id_root=next_step_id, step_id_fault=next_step_id + 1
        )
        nodes.extend(branch_nodes)
        letter = cfg["letter"]
        edges.append((f"a1{letter}", f"a7{letter}"))
        edges.append(("a4", f"a7{letter}"))
        fault_ids.append(f"a7{letter}")
        terminal_inputs.append(f"a7{letter}")
        next_step_id += 2

    terminal_step_id = next_step_id

    def _terminal_compute(inp: dict[str, str], f: dict[str, str]) -> str:
        items = ", ".join(inp[fid] for fid in fault_ids)
        return f"Recommendation: {items} at {inp['a4']}."

    nodes.append(
        _NodeSpec(
            node_id="a8", step_id=terminal_step_id, kind=NodeKind.FUNCTION,
            inputs=list(terminal_inputs), provenance=Provenance.MODEL_INFERRED,
            profile_span_ids=[], confidence=0.9,
            compute=_terminal_compute,
            render_step=lambda v: v,
            render_assumption=lambda v: f"Final answer is: {v}",
            step_kind=StepKind.OUTPUT,
        )
    )
    for fid in fault_ids:
        edges.append((fid, "a8"))

    return ComputeGraph(nodes=nodes, edges=edges, final_node_id="a8")


FAULT_TARGETS: tuple[str, str] = ("a5", "a7")  # kept for backward compat (num_faults=2)


def multi_fault_values(gold_facts: dict[str, str], num_faults: int = 2) -> dict[str, str]:
    """The `num_faults` independently-injected wrong values (direct MANUAL
    override, same contract as `MealPlanningDomain.fault_value` in
    single_fault mode -- NOT re-derived, the override IS the fault)."""
    _check_num_faults(num_faults)
    values = {"a5": WRONG_DISH_FOR_DIETARY[gold_facts["dietary"]]}
    if num_faults >= 2:
        values["a7"] = WRONG_SIDE_FOR_ALLERGY[gold_facts["allergy"]]
    for cfg in _extra_axis_configs()[: max(0, num_faults - 2)]:
        cls = gold_facts[cfg["facts_key"]]
        values[f"a7{cfg['letter']}"] = cfg["wrong_item_for_class"][cls]
    return values


# ---------------------------------------------------------------------------
# Example construction
# ---------------------------------------------------------------------------


@dataclass
class MultiFaultExample:
    """Everything `scripts/rebuttal_experiment_d.py` needs to run the exact
    same `run_intro_specter` harness the single-fault protocol uses, plus the
    gold fault-node ids (kept out of `GoldLabels`, which only carries a
    single `fault_node_id`, so this file need not touch `schemas.py`)."""

    task_id: str
    profile: UserProfile
    task: dict[str, Any]
    graph: ComputeGraph
    trajectory: Trajectory  # faulty (all faults injected)
    gold_dag: Any  # AssumptionDAG built from the faulty render, passthrough-style
    gold_fault_ids: tuple[str, ...]
    gold_values: dict[str, str]
    faulty_values: dict[str, str]
    profile_facts: dict[str, str]
    swap_fn: Any
    evaluator: Any
    rerun_fn: Any
    rules: list[Any]
    num_faults: int = 2


def build_multi_fault_example(
    idx: int, *, seed: int = 0, num_faults: int = 2
) -> MultiFaultExample:
    _check_num_faults(num_faults)
    domain = MealPlanningDomain(seed=seed)  # only used for its generic closures
    rng = random.Random(seed * 1_000_003 + idx)
    facts = generate_multi_fault_facts(rng, idx, num_faults=num_faults)
    profile, gold_facts = facts.profile, facts.gold_facts
    graph = build_multi_fault_graph(num_faults=num_faults)
    task_id = f"synthetic_dag_multi_fault_n{num_faults}_{idx:05d}"

    _clean_traj, _clean_dag, gold_values = graph.render(
        task_id=task_id, profile_facts=gold_facts
    )
    faulty_overrides = multi_fault_values(gold_facts, num_faults=num_faults)
    faulty_traj, faulty_dag, faulty_values = graph.render(
        task_id=task_id, profile_facts=gold_facts, overrides=faulty_overrides
    )

    from ..verifier import hard_constraint_keyword_rule

    swap_fn = domain.make_swap_fn(graph, gold_values)
    evaluator = domain.make_evaluator(
        graph=graph,
        profile=profile,
        profile_facts=gold_facts,
        prefix_values=faulty_values,
        gold_values=gold_values,
    )
    rerun_fn = domain.make_rerun_fn(
        graph=graph,
        profile_facts=gold_facts,
        prefix_values=faulty_values,
        gold_values=gold_values,
    )

    task = {
        "task_id": task_id,
        "task_type": "meal_recommendation_multi_fault",
        "prompt": "Recommend a full, constraint-safe meal for the user's lunch today.",
        "split": "test",
        "mode": "multi_fault",
        "num_faults": num_faults,
    }

    return MultiFaultExample(
        task_id=task_id,
        profile=profile,
        task=task,
        graph=graph,
        trajectory=faulty_traj,
        gold_dag=faulty_dag,
        gold_fault_ids=fault_node_ids_for(num_faults),
        gold_values=gold_values,
        faulty_values=faulty_values,
        profile_facts=gold_facts,
        swap_fn=swap_fn,
        evaluator=evaluator,
        rerun_fn=rerun_fn,
        rules=[hard_constraint_keyword_rule],
        num_faults=num_faults,
    )


def iter_multi_fault_examples(n: int, *, seed: int = 0, num_faults: int = 2):
    for idx in range(n):
        yield build_multi_fault_example(idx, seed=seed, num_faults=num_faults)


__all__ = [
    "ALLERGY_BANNED",
    "ALLERGY_CLASSES",
    "FAULT_TARGETS",
    "MAX_FAULTS",
    "MIN_FAULTS",
    "MultiFaultExample",
    "SIDE_FOR_ALLERGY",
    "WRONG_SIDE_FOR_ALLERGY",
    "build_multi_fault_example",
    "build_multi_fault_graph",
    "fault_node_ids_for",
    "generate_multi_fault_facts",
    "iter_multi_fault_examples",
    "multi_fault_values",
]
