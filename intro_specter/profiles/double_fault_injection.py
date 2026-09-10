"""Additive double-fault-injection wrapper around the existing, UNMODIFIED
`intro_specter.profiles.fault_injection.inject_fault` mechanism.

Context / why this file exists
-------------------------------
`fault_injection.py` injects exactly one fault per (task_id, seed) and, on
the real-data benchmark loaders (see `intro_specter/benchmarks/twowiki_real.py`),
the returned `FaultRecord` is used ONLY to label `gold_fault_node` in
`condition_meta` for attribution scoring -- it is never actually applied to
the prompt/profile/context the agent sees. That's fine for the single-fault
attribution-accuracy protocol the paper uses, but it means the *real*
multi-fault rebuttal experiment (does Intro-Specter resolve multiple
simultaneous, genuinely-present violations better than Reflexion?) needs an
injector that actually mutates what the agent is shown -- otherwise there is
nothing for either method to detect or repair, and the comparison would be
vacuous.

This module calls `inject_fault` (unmodified, imported as-is) twice, with
`rate=1.0` (always inject) and different deterministic derived seeds, to
obtain two *independent* `FaultRecord`s, then genuinely applies each one:

  * Fault 1 ("context" fault) -- forced to `fault_type == "wrong_value"`.
    `inject_fault`'s `wrong_value` branch already implements exactly the
    "For QA: replace one of the gold-supporting facts with a near-neighbor
    distractor" idea described in its own module docstring (see
    `_wrong_value_pool`); we take its `injected_text` and splice it into the
    retrieved context as an appended corrupting note, so a method that
    blindly trusts the (now-corrupted) context is pulled toward the wrong
    answer. Resolved iff the method's *final answer* still contains the true
    gold answer despite the corruption -- this reuses the exact same
    predicate `twowiki_real.py::_make_rule` already applies for its
    `v_real_2wiki_factual_miss` check (not a new scoring mechanism).

  * Fault 2 ("profile" fault) -- forced to `fault_type == "wrong_constraint"`,
    restricted to a *relevant* profile constraint (by passing `inject_fault`
    a filtered view of the profile containing only `relevant: true`
    constraints -- corrupting an irrelevant/distractor constraint would be
    unfalsifiable, since nothing in the task or verifier ever checks it).
    We then splice the resulting `injected_text` into a COPY of the real,
    full profile (replacing the one span's text), so the agent's belief
    about that constraint is now genuinely wrong. Resolved iff the method's
    final output is judged (by a fresh `HybridVerifier` LLM check --
    the exact "re-verify against ground truth" pattern
    `scripts/rebuttal_experiment_a.py::_true_success` already uses, just
    applied to a single isolated constraint span instead of the whole
    profile) to comply with the TRUE (uncorrupted) constraint text.

The two faults are structurally disjoint by construction (one lives in the
retrieved context, the other in the profile constraint list), so "did the
method resolve both" is a genuine two-target multi-fault question, not an
artifact of one mechanism standing in for two.

`fault_injection.py` itself is untouched -- this module only calls it with
different keyword arguments (varying `seed` and `profile`) and post-
processes the `FaultRecord`s it returns.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from .fault_injection import FaultRecord, inject_fault

_MAX_TRIES = 500


def _derived_seed(task_id: str, seed: int, tag: str, i: int) -> int:
    """Deterministic derived seed for the i-th retry of a given (task_id, seed, tag)
    search. Uses sha256 (not Python's randomized `hash()`) so results are
    reproducible across processes/runs, matching the determinism guarantee
    `fault_injection.py` itself documents for `_should_inject`."""
    h = hashlib.sha256(f"double_fault::{task_id}::{seed}::{tag}::{i}".encode()).hexdigest()
    return int(h[:12], 16)


def _find_fault(
    *, task_id: str, seed: int, profile: dict[str, Any], gold_answer: Any,
    wanted_type: str, tag: str,
) -> FaultRecord:
    """Calls `inject_fault` (unmodified) repeatedly with varied derived seeds
    (rate=1.0, so every call injects something) until it returns a record of
    `wanted_type`. `inject_fault` picks `fault_type` uniformly at random from
    4 types per call, so this takes ~4 tries in expectation."""
    for i in range(_MAX_TRIES):
        fr = inject_fault(
            task_id=task_id,
            seed=_derived_seed(task_id, seed, tag, i),
            profile=profile,
            gold_answer=gold_answer,
            rate=1.0,
        )
        if fr is not None and fr.fault_type == wanted_type:
            return fr
    raise RuntimeError(
        f"double_fault_injection: could not find fault_type={wanted_type!r} "
        f"for task_id={task_id!r} tag={tag!r} within {_MAX_TRIES} tries"
    )


@dataclass(frozen=True)
class DoubleFaultRecord:
    task_id: str
    fault_context: FaultRecord          # wrong_value, applied to retrieved context
    fault_profile: FaultRecord          # wrong_constraint, applied to a relevant profile span
    true_constraint_text: str           # original (uncorrupted) text of the targeted span
    true_constraint_id: str | None      # id of the targeted span in the ORIGINAL profile_dict
    true_constraint_is_hard: bool
    corrupted_profile_dict: dict[str, Any]
    corrupted_context_text: str


def build_double_fault(
    *, task_id: str, seed: int, profile_dict: dict[str, Any], answer: Any, context_text: str,
    constraint_filter: Any = None,
) -> DoubleFaultRecord:
    """Builds two independent, genuinely-applied faults for one example.

    `profile_dict` must have the shape `intro_specter.profiles.templates.inject_profile`
    produces (`{"user_id", "constraints": [{"id","text","type","relevant","category"}, ...], "history"}`).

    `constraint_filter`, if given, is a `(constraint_dict) -> bool` predicate
    restricting which constraints are eligible targets for Fault 2 (defaults
    to `relevant: true`, i.e. constraints that could plausibly matter to the
    task -- corrupting a distractor constraint nothing in the task or
    verifier ever checks would be unfalsifiable). Callers needing a
    mechanically-checkable Fault 2 (e.g. restricting to a specific
    rule-checkable constraint) can pass a narrower predicate.
    """
    # --- Fault 1: context corruption (forced wrong_value) ---
    fault_context = _find_fault(
        task_id=task_id, seed=seed, profile=profile_dict, gold_answer=answer,
        wanted_type="wrong_value", tag="ctx",
    )
    corrupted_context = (
        context_text.rstrip()
        + "\n[Additional note found in a related source: some references instead give "
        f"the answer as {fault_context.injected_text!r}.]"
    )

    # --- Fault 2: profile-constraint corruption (forced wrong_constraint,
    #     restricted via `constraint_filter`, default relevant-only) ---
    pred = constraint_filter or (lambda c: c.get("relevant"))
    relevant_constraints = [c for c in profile_dict["constraints"] if pred(c)]
    if not relevant_constraints:
        raise RuntimeError(f"double_fault_injection: no eligible constraints for {task_id!r}")
    relevant_view = {**profile_dict, "constraints": relevant_constraints}
    fault_profile = _find_fault(
        task_id=task_id, seed=seed, profile=relevant_view, gold_answer=answer,
        wanted_type="wrong_constraint", tag="prof",
    )
    true_text = fault_profile.original_text
    new_constraints: list[dict[str, Any]] = []
    applied = False
    target_id: str | None = None
    target_is_hard = False
    for c in profile_dict["constraints"]:
        if not applied and c["text"] == true_text:
            new_constraints.append({**c, "text": fault_profile.injected_text})
            applied = True
            target_id = c["id"]
            target_is_hard = c["type"] == "hard"
        else:
            new_constraints.append(c)
    if not applied:
        raise RuntimeError(
            f"double_fault_injection: could not locate targeted constraint "
            f"{true_text!r} in full profile for {task_id!r}"
        )
    corrupted_profile_dict = {**profile_dict, "constraints": new_constraints}

    return DoubleFaultRecord(
        task_id=task_id,
        fault_context=fault_context,
        fault_profile=fault_profile,
        true_constraint_text=true_text,
        true_constraint_id=target_id,
        true_constraint_is_hard=target_is_hard,
        corrupted_profile_dict=corrupted_profile_dict,
        corrupted_context_text=corrupted_context,
    )


@dataclass(frozen=True)
class ProfileFaultTarget:
    """One profile-constraint fault slot, named + independently checkable by
    the caller. `name` is an arbitrary caller-chosen label (e.g. "english",
    "concise") used purely for bookkeeping/scoring downstream; `predicate`
    selects which constraint(s) in the profile are eligible targets for this
    slot (same role `constraint_filter` plays in `build_double_fault`)."""
    name: str
    predicate: Any  # (constraint_dict) -> bool


@dataclass(frozen=True)
class MultiFaultRecord:
    """Generalization of `DoubleFaultRecord` to `num_faults = 1 (context) + len(profile_targets)`
    independent faults. Built the same way: `inject_fault` (unmodified) called
    once per fault with `rate=1.0` and a distinct derived seed/tag, each
    profile fault restricted to its own `ProfileFaultTarget.predicate` so the
    N targeted constraints are guaranteed structurally disjoint (each
    predicate is checked against the REMAINING, not-yet-targeted constraints,
    so the same span can never be double-targeted)."""
    task_id: str
    fault_context: FaultRecord
    profile_faults: dict[str, FaultRecord]        # name -> FaultRecord
    true_constraint_texts: dict[str, str]         # name -> original text
    true_constraint_ids: dict[str, str | None]    # name -> span id
    corrupted_profile_dict: dict[str, Any]
    corrupted_context_text: str


def build_multi_fault(
    *, task_id: str, seed: int, profile_dict: dict[str, Any], answer: Any, context_text: str,
    profile_targets: list[ProfileFaultTarget],
) -> MultiFaultRecord:
    """Generalized N-fault builder: 1 context fault (always `wrong_value`) +
    `len(profile_targets)` profile-constraint faults (always `wrong_constraint`,
    one per target slot, each restricted to that slot's own predicate over the
    constraints NOT already claimed by an earlier slot in this same call --
    guarantees the N targeted spans are pairwise disjoint)."""
    fault_context = _find_fault(
        task_id=task_id, seed=seed, profile=profile_dict, gold_answer=answer,
        wanted_type="wrong_value", tag="ctx",
    )
    corrupted_context = (
        context_text.rstrip()
        + "\n[Additional note found in a related source: some references instead give "
        f"the answer as {fault_context.injected_text!r}.]"
    )

    working_constraints = list(profile_dict["constraints"])
    claimed_ids: set[str] = set()
    profile_faults: dict[str, FaultRecord] = {}
    true_texts: dict[str, str] = {}
    true_ids: dict[str, str | None] = {}
    new_constraints_by_id: dict[str, dict[str, Any]] = {c["id"]: dict(c) for c in profile_dict["constraints"]}

    for target in profile_targets:
        eligible = [c for c in working_constraints if c["id"] not in claimed_ids and target.predicate(c)]
        if not eligible:
            raise RuntimeError(
                f"build_multi_fault: no eligible constraints for slot {target.name!r} "
                f"(task_id={task_id!r}) -- caller should have pre-filtered examples for this"
            )
        view = {**profile_dict, "constraints": eligible}
        fr = _find_fault(
            task_id=task_id, seed=seed, profile=view, gold_answer=answer,
            wanted_type="wrong_constraint", tag=f"prof_{target.name}",
        )
        true_text = fr.original_text
        matched = next(c for c in eligible if c["text"] == true_text)
        claimed_ids.add(matched["id"])
        new_constraints_by_id[matched["id"]] = {**matched, "text": fr.injected_text}
        profile_faults[target.name] = fr
        true_texts[target.name] = true_text
        true_ids[target.name] = matched["id"]

    corrupted_profile_dict = {
        **profile_dict,
        "constraints": [new_constraints_by_id[c["id"]] for c in profile_dict["constraints"]],
    }

    return MultiFaultRecord(
        task_id=task_id,
        fault_context=fault_context,
        profile_faults=profile_faults,
        true_constraint_texts=true_texts,
        true_constraint_ids=true_ids,
        corrupted_profile_dict=corrupted_profile_dict,
        corrupted_context_text=corrupted_context,
    )


__all__ = [
    "DoubleFaultRecord",
    "MultiFaultRecord",
    "ProfileFaultTarget",
    "build_double_fault",
    "build_multi_fault",
]
