#!/usr/bin/env python3
"""Experiment D (real), travelplanner_real SYNTHETIC multi-fault sweep -- SHARED core.

Why this file exists (additive-only, never edits any tracked file)
--------------------------------------------------------------------
This fills the one remaining gap in the "5 dataset x 3 condition" matrix
identified in the build plan: TravelPlanner's Condition 2 (synthetic
multi-fault, same mechanism as twowiki_real/musique_real/hotpotqa_real/
longmemeval_real -- corrupt the TEMPLATED profile-bank layer, via
`double_fault_injection.py`, NOT TravelPlanner's genuine native budget/days/
destination/local-constraint fields). That native-field experiment is a
SEPARATE, already-running task
(`scripts/rebuttal_experiment_c_nonsynthetic_multifault_*.py`, writing to
`outputs/rebuttal/experiment_c/nonsynthetic_multifault/`) -- this file does
not touch it and writes to a differently-named output tree
(`outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic/`).

`intro_specter/benchmarks/travelplanner_real.py` calls
`inject_profile(task_id=..., seed=..., dataset="travelplanner")`, which draws
3-5 constraints from the SAME `PROFILE_TEMPLATES` bank twowiki_real/
musique_real/hotpotqa_real use (english-only / concise / no-bullets /
no-preamble are its 4 mechanically-clean, checkable types), PLUS 1-2
additional constraints from `TRAVEL_CONSTRAINT_TEMPLATES` (vegan, wheelchair,
no-alcohol, no-feathers -- these feed `banned_substrings` for the verifier
rule but are not independently checkable the way the 4 clean types are, so
they are not used as fault-injection targets here, matching how twowiki_real/
musique_real never targeted their own "irrelevant" distractor constraints
either).

Fault-construction path and feasibility (measured directly, BEFORE writing
this file, via 20,000-row direct simulation over
`inject_profile(seed=42, dataset="travelplanner")` -- see
`_is_english_constraint` etc. below for the exact predicates used):

    >=1 of the 4 clean types present: 14700/20000 (73.5%) -- N=2 supported
    >=2 present:                       3978/20000 (19.9%) -- N=3 supported
    >=3 present:                        212/20000 (1.06%) -- N=4 supported
                                                              (low probability
                                                              but travelplanner_real's
                                                              profile-generation pool is
                                                              NOT capped the way
                                                              musique_real's 760-row
                                                              3hop pool was -- `idx` can
                                                              range arbitrarily, each
                                                              idx re-draws an independent
                                                              profile via
                                                              `inject_profile(task_id=
                                                              f"travel_real_{idx:05d}", ...)`
                                                              -- so scanning ~6000-8000
                                                              idx values comfortably
                                                              finds 60+ qualifying N=4
                                                              examples with zero API cost)
    >=4 present:                            0/20000 (0.0%)  -- N=5 NOT SUPPORTED.

N=5 via this (double-fault) path would need all 4 clean profile-fault types
to co-occur in one example's 3-5-item PROFILE_TEMPLATES draw (further
squeezed by TRAVEL_CONSTRAINT_TEMPLATES also claiming 1-2 slots) -- 0/20000
occurrences is a real structural ceiling, not a small-sample artifact.

Unlike twowiki_real (bridge_comparison, 4 independent evidence facts) or
musique_real (native question_decomposition, 3 independent hop facts),
TravelPlanner is NOT a multi-hop QA benchmark -- it has no per-example field
holding N>=4 independent, mechanically-checkable facts to fault
independently of the profile-constraint pool. A hop-style path (the one that
let twowiki_real/musique_real reach N=5) is therefore genuinely not
available here; this is reported honestly as N=5 infeasible for
travelplanner_real (matching the same honest N=5 infeasibility finding
already made for longmemeval_real), not forced or approximated.

Two independent, structurally disjoint faults per example, exactly matching
the twowiki_real/musique_real double-fault design (`build_multi_fault`,
imported UNMODIFIED from `double_fault_injection.py`):

  * 1 "context" fault (always `wrong_value`) -- corrupts the free-text
    `Reference information:` block (TravelPlanner's own per-row
    `reference_information` field, analogous to musique_real's/twowiki_real's
    "Paragraphs" context) with a distractor note about the answer
    (`f"plan within ${budget}"`, the same `gold_answer` value the ORIGINAL,
    unmodified `travelplanner_real.py` loader already passes to
    `inject_fault` for its own single-fault condition). Because
    TravelPlanner's "answer" is a budget-compliance statement rather than a
    single named entity, this experiment defines "ctx fault resolved" as:
    the produced plan's own stated total cost (mechanically extracted via
    `_extract_total_cost`, copied from
    `rebuttal_experiment_c_nonsynthetic_travelplanner.py`) stays <= the
    TRUE, UNMODIFIED, native budget (never itself touched by this
    experiment -- only the ADDITIONAL free-text distractor note is
    injected). This reuses an existing, already-validated mechanical check
    rather than inventing a new one.

  * (N-1) "profile" faults (always `wrong_constraint`), each restricted to
    one of the 4 mechanically-clean PROFILE_TEMPLATES types (english /
    concise / bullets / preamble) -- IDENTICAL checkers and predicates to
    `rebuttal_experiment_d_real_musique_common.py`'s `PROFILE_FAULT_TYPES`
    registry (copied, not re-derived, since both draw from the exact same
    template bank).

Verifier rule (`_make_rule` below) is a NEW function specific to this
script -- it does NOT reuse `travelplanner_real.py::_make_rule` unmodified,
because that function only inspects `final_output`, and this campaign's own
prior investigation (see `rebuttal_experiment_c_nonsynthetic_multifault_
common.py::_trajectory_full_text`'s docstring) found TravelPlanner agents on
this prompt template routinely put the actual day-by-day plan in the LAST
`steps` entry and leave `final_output` as a short summary line -- checking
day-count/local-constraint resolution against `final_output` alone would
undercount success for every arm equally (not a real method difference).
This script's rule and all `per_fault_resolved` checks scan
`_trajectory_full_text` (final_output + all step texts), the same fix
already applied for the sibling non-synthetic experiment.

`intro_specter/repair.py`'s placeholder-final-output bug (a downstream-
regeneration call can return a non-substantive placeholder string like
"Total cost: $..." with no number, silently overwriting an already-correct
primed answer) applies here too (same prompt template, same pipeline code
path) -- `_recover_placeholder_final_output` below is copied verbatim from
`rebuttal_experiment_c_nonsynthetic_travelplanner.py` / `..._multifault_
common.py`, not rediscovered.

7 arms (identical calling convention to every other Experiment D script):
    direct, self_refine, full_regen, react, selfcheckgpt, reflexion, intro_specter

Output: `outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic/
{model}/n{N}__{arm}.jsonl`, resumable/dedup'd per arm file.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable, TypeVar

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_T = TypeVar("_T")


def _with_retry(fn: Callable[[], _T], *, attempts: int = 5, base_delay: float = 3.0, label: str = "") -> _T:
    """Same retry-with-backoff pattern as every other script in this campaign."""
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as e:
            if attempt == attempts - 1:
                raise
            delay = base_delay * (2 ** attempt)
            print(f"[RETRY] {label} attempt {attempt + 1}/{attempts} failed ({e}); retrying in {delay:.0f}s",
                  file=sys.stderr)
            time.sleep(delay)
    raise RuntimeError("unreachable")  # pragma: no cover


from intro_specter.attribution import LLMCounterfactualSampler
from intro_specter.baselines import (
    run_direct,
    run_full_regen,
    run_react,
    run_reflexion,
    run_selfcheckgpt,
    run_self_refine,
)
from intro_specter.benchmarks.base import BenchmarkExample
from intro_specter.benchmarks.travelplanner_real import (
    TravelPlannerReal,
    _profile_to_userprofile,
)
from intro_specter.models import SQLiteCache, build_provider
from intro_specter.pipeline import IntroSpecterConfig, run_intro_specter
from intro_specter.profiles.double_fault_injection import (
    MultiFaultRecord,
    ProfileFaultTarget,
    build_multi_fault,
)
from intro_specter.prompts import DIRECT_AGENT_SYSTEM, direct_agent_user
from intro_specter.runner import _meta_summary, _self_report_evaluator
from intro_specter.schemas import (
    Severity,
    Trajectory,
    TrajectoryStep,
    ViolationEvent,
    coerce_final_output,
    coerce_trajectory_steps,
)
from intro_specter.verifier import HybridVerifier

BENCH_SEED = 42

SUPPORTED_NUMS = {2, 3, 4}
# N=5 excluded: direct 20,000-row simulation over
# inject_profile(seed=42, dataset="travelplanner") found 0/20000 examples
# with all 4 mechanically-clean profile-fault types co-occurring (see module
# docstring) -- not a hop-structured dataset, so no alternate path exists
# either (unlike twowiki_real/musique_real, which reached N=5 via a native
# multi-hop-fact field TravelPlanner simply doesn't have).

_N_PROFILE_FAULTS_BY_N = {2: 1, 3: 2, 4: 3}

_REF_RE = re.compile(r"Reference information:\n(.*?)\n\nQuery: ", re.DOTALL)
_QUERY_RE = re.compile(r"Query: (.*?)\n\nProduce a concrete", re.DOTALL)
_TRAVELERS_RE = re.compile(r"Travelers: (\d+)")

_MONEY_RE = re.compile(r"\$\s?([\d,]+(?:\.\d+)?)")


def _extract_total_cost(text: str) -> float | None:
    """Copied verbatim from rebuttal_experiment_c_nonsynthetic_travelplanner.py."""
    text = text or ""
    m = list(re.finditer(r"total\s*cost[^$\d]{0,20}\$\s?([\d,]+(?:\.\d+)?)", text, re.IGNORECASE))
    if m:
        return float(m[-1].group(1).replace(",", ""))
    m2 = list(_MONEY_RE.finditer(text))
    if m2:
        return float(m2[-1].group(1).replace(",", ""))
    return None


def _trajectory_full_text(trajectory: Trajectory) -> str:
    """Same 'scan the whole trajectory, not just final_output' fix already
    proven necessary for this benchmark (copied structurally from
    `rebuttal_experiment_c_nonsynthetic_multifault_common.py`)."""
    parts = [trajectory.final_output or ""]
    for step in trajectory.steps:
        parts.append(getattr(step, "text", "") or "")
        parts.append(getattr(step, "reason_summary", "") or "")
    return "\n".join(parts)


def _recover_placeholder_final_output(final_traj: Trajectory, primed: Trajectory) -> Trajectory:
    """Copied verbatim from `rebuttal_experiment_c_nonsynthetic_travelplanner.py`
    -- see that function's docstring for the full bug description
    (`intro_specter/repair.py`'s downstream-regeneration fallback can return a
    non-empty placeholder string with no parseable cost figure, silently
    overwriting an already-correct primed answer)."""
    current_cost = _extract_total_cost(final_traj.final_output or "")
    if current_cost is not None:
        return final_traj
    primed_cost = _extract_total_cost(primed.final_output or "")
    if primed_cost is None:
        return final_traj
    return Trajectory(task_id=final_traj.task_id, steps=final_traj.steps, final_output=primed.final_output)


# ---------------------------------------------------------------------------
# Mechanically-checkable profile-fault type registry (unmodified copy of the
# registry `rebuttal_experiment_d_real_musique_common.py` uses -- travelplanner_
# real's profiles are drawn from the SAME `inject_profile` PROFILE_TEMPLATES
# bank, so the same 4 types and checkers apply as-is).
# ---------------------------------------------------------------------------

_TRUE_BANNED_SUBSTRINGS = ["hola ", "bonjour", "ciao ", "你好", "こんにちは"]
_PREAMBLE_PHRASES = [
    "based on the", "according to the", "the question asks", "to answer this question",
    "the answer to your question", "in response to your question", "the paragraphs state",
    "as stated in", "looking at the", "from the given",
]


def _is_english_constraint(c: dict[str, Any]) -> bool:
    return "english only" in c["text"].lower()


def _is_concise_constraint(c: dict[str, Any]) -> bool:
    t = c["text"].lower()
    return "concise answers under 20 words" in t or "single sentence" in t


def _is_bullets_constraint(c: dict[str, Any]) -> bool:
    return "not use bullet points" in c["text"].lower()


def _is_preamble_constraint(c: dict[str, Any]) -> bool:
    return "dislikes preamble" in c["text"].lower()


def _resolved_english(full_text: str | None, true_text: str) -> bool:
    text = (full_text or "").lower()
    return not any(b.lower() in text for b in _TRUE_BANNED_SUBSTRINGS)


_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+")


def _resolved_concise(full_text: str | None, true_text: str) -> bool:
    text = (full_text or "").strip()
    if "single sentence" in true_text.lower():
        n_sentences = len([s for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()])
        return n_sentences <= 1
    return len(text.split()) <= 20


_BULLET_RE = re.compile(r"(^|\n)\s*([-*•]|\d+[.)])\s")


def _resolved_bullets(full_text: str | None, true_text: str) -> bool:
    return _BULLET_RE.search(full_text or "") is None


def _resolved_preamble(full_text: str | None, true_text: str) -> bool:
    text = (full_text or "").strip().lower()
    return not any(text.startswith(p) for p in _PREAMBLE_PHRASES)


PROFILE_FAULT_TYPES: dict[str, tuple[Callable[[dict[str, Any]], bool], Callable[[str | None, str], bool]]] = {
    "english": (_is_english_constraint, _resolved_english),
    "concise": (_is_concise_constraint, _resolved_concise),
    "bullets": (_is_bullets_constraint, _resolved_bullets),
    "preamble": (_is_preamble_constraint, _resolved_preamble),
}


def _banned_for(profile_dict: dict[str, Any]) -> list[str]:
    """Unmodified copy of the banned-substring derivation in
    `travelplanner_real.py::_build_example` -- covers the TRAVEL_CONSTRAINT_
    TEMPLATES items (vegan / wheelchair / no-alcohol / no-feathers), which
    are NOT fault-injection targets here but still feed the verifier rule
    exactly as the original loader intends."""
    banned: list[str] = []
    for c in profile_dict["constraints"]:
        t = c["text"].lower()
        if "vegan" in t:
            banned += ["steakhouse", "bbq joint", "carnivore", "veal", "foie gras"]
        if "wheelchair" in t or "mobility" in t:
            banned += ["climb the stairs", "stairs only", "uneven hike"]
        if "alcohol" in t and "no drink" in t:
            banned += ["wine bar", "cocktail lounge", "brewery tour"]
        if "feathers" in t:
            banned += ["down pillow", "down duvet"]
    return banned


def _fault_ctx_resolved(full_text: str, true_budget: int) -> bool:
    """'ctx' fault resolution: TravelPlanner's per-row `answer` corrupted by
    `build_multi_fault` is `f"plan within ${budget}"` (a budget-compliance
    statement, not a named entity like twowiki_real/musique_real's QA
    answers) -- so resolution here means the produced plan's own stated
    total cost stays within the TRUE (never-corrupted) native budget despite
    the distractor note appended to the reference-information context. This
    reuses the same `_extract_total_cost` mechanical check already validated
    for this benchmark, rather than a substring match that wouldn't make
    sense for a budget statement."""
    cost = _extract_total_cost(full_text)
    return cost is not None and cost <= true_budget


def _make_rule(dest: str, days: int, budget: int, banned_substrings: list[str]):
    banned_l = [b.lower() for b in banned_substrings]

    def rule(profile, task, trajectory, final_output):
        text = _trajectory_full_text(trajectory)
        text_l = text.lower()
        out: list[ViolationEvent] = []
        if dest and dest.lower() not in text_l:
            out.append(ViolationEvent(
                violation_id="v_travelsynth_mf_no_destination",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint=f"plan must mention destination {dest!r}",
                trajectory_text=text[:200], severity=Severity.HIGH,
                explanation="destination missing from plan",
            ))
        day_mentions = sum(1 for d in range(1, days + 1) if f"day {d}" in text_l)
        if day_mentions < max(1, min(days, 3)):
            out.append(ViolationEvent(
                violation_id="v_travelsynth_mf_short_plan",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint=f"plan must cover {days} days",
                trajectory_text=text[:200], severity=Severity.MEDIUM,
                explanation=f"only {day_mentions} day mentions found",
            ))
        cost = _extract_total_cost(text)
        if cost is None:
            out.append(ViolationEvent(
                violation_id="v_travelsynth_mf_no_cost",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint="plan must include a parseable total cost figure",
                trajectory_text=text[:200], severity=Severity.MEDIUM,
                explanation="no dollar figure found in plan",
            ))
        elif cost > budget:
            out.append(ViolationEvent(
                violation_id="v_travelsynth_mf_ctx_fault_unresolved",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint=f"plan total cost (${cost:.0f}) exceeds the TRUE budget (${budget})",
                trajectory_text=text[:200], severity=Severity.HIGH,
                explanation=f"true budget is ${budget}; a distractor note was injected into the "
                            f"reference information suggesting a different answer.",
            ))
        for b in banned_l:
            if b and b in text_l:
                out.append(ViolationEvent(
                    violation_id="v_travelsynth_mf_profile_violation",
                    step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                    violated_constraint="plan violates a hard profile constraint",
                    trajectory_text=text[:200], severity=Severity.HIGH,
                    explanation=f"plan contains banned substring {b!r}",
                ))
                break
        return out

    rule.__name__ = "travelplanner_synthetic_multifault_rule"
    return rule


# ---------------------------------------------------------------------------
# Example construction: reuse TravelPlannerReal(fault_inject=False) UNMODIFIED
# to get the base (task_id, profile, prompt, condition_meta), then extract
# the reference-information/query text back out of the assembled prompt
# (same style `rebuttal_experiment_d_real_musique_common.py::_extract_context`
# uses) and corrupt via `build_multi_fault`.
# ---------------------------------------------------------------------------


def _build_prompt(
    profile_dict: dict[str, Any], context_text: str, query: str, travelers: str,
    budget: int, org: str, dest: str, days: int, local: dict[str, Any],
) -> str:
    """Exact copy of the prompt-assembly template in
    `intro_specter/benchmarks/travelplanner_real.py::_build_example`."""
    return (
        "User profile constraints:\n"
        + "\n".join(f"- {c['text']}" for c in profile_dict["constraints"])
        + f"\n\nLocal constraints from booking system:\n{local}\n\n"
        f"Budget: ${budget}\n"
        f"Travelers: {travelers}\n"
        f"Origin: {org}, Destination: {dest}, Days: {days}\n\n"
        f"Reference information:\n{context_text}\n\n"
        f"Query: {query}\n\n"
        "Produce a concrete day-by-day plan. Each day must list "
        "accommodation, meals (with restaurants), and attractions, with a cost line. "
        "End with a 'Total cost: $...' summary."
    )


def _build_examples(
    n_examples: int, seed: int, num_faults: int, scan_limit: int | None = None,
) -> list[tuple[BenchmarkExample, MultiFaultRecord, list[str]]]:
    if num_faults not in SUPPORTED_NUMS:
        raise ValueError(f"num_faults={num_faults} not supported (choices: {sorted(SUPPORTED_NUMS)})")
    n_profile_faults = _N_PROFILE_FAULTS_BY_N[num_faults]
    # >=3-type co-occurrence (needed for N=4) is only ~1.06% (see module
    # docstring) -- scan a generously large pool by default; cheap, no API
    # cost (pure profile-generation + HF row lookup).
    scan_limit = scan_limit or 8000

    bench = TravelPlannerReal(n_examples=scan_limit, seed=seed, split="all", fault_inject=False)
    out: list[tuple[BenchmarkExample, MultiFaultRecord, list[str]]] = []
    for example in bench:
        if len(out) >= n_examples:
            break
        cmeta = example.task["condition_meta"]
        constraints = cmeta["profile_constraints"]

        present_types = sorted(
            name for name, (pred, _) in PROFILE_FAULT_TYPES.items()
            if any(pred(c) for c in constraints)
        )
        if len(present_types) < n_profile_faults:
            continue
        chosen_types = present_types[:n_profile_faults]

        prompt = example.task["prompt"]
        ref_match = _REF_RE.search(prompt)
        query_match = _QUERY_RE.search(prompt)
        travelers_match = _TRAVELERS_RE.search(prompt)
        if not (ref_match and query_match and travelers_match):
            raise RuntimeError(
                f"could not locate expected prompt sections for {example.task_id!r} -- template drift?"
            )
        context_text = ref_match.group(1)
        query = query_match.group(1)
        travelers = travelers_match.group(1)

        budget = cmeta["budget"]
        answer = f"plan within ${budget}"

        profile_dict = {
            "user_id": example.profile.user_id,
            "constraints": constraints,
            "history": [],
        }
        targets = [ProfileFaultTarget(name=n, predicate=PROFILE_FAULT_TYPES[n][0]) for n in chosen_types]
        mfr = build_multi_fault(
            task_id=example.task_id, seed=seed, profile_dict=profile_dict,
            answer=answer, context_text=context_text, profile_targets=targets,
        )

        corrupted_profile = _profile_to_userprofile(mfr.corrupted_profile_dict)
        new_prompt = _build_prompt(
            mfr.corrupted_profile_dict, mfr.corrupted_context_text, query, travelers,
            budget=budget, org=cmeta["org"], dest=cmeta["dest"], days=cmeta["days"],
            local=cmeta["local_constraint"],
        )
        banned = _banned_for(mfr.corrupted_profile_dict)

        new_cmeta = {
            **cmeta,
            "profile_constraints": mfr.corrupted_profile_dict["constraints"],
            "banned_substrings": banned,
            "multi_fault_ctx": mfr.fault_context.__dict__,
            "multi_fault_profile": {k: v.__dict__ for k, v in mfr.profile_faults.items()},
            "true_constraint_texts": mfr.true_constraint_texts,
            "true_constraint_ids": mfr.true_constraint_ids,
        }
        rule = _make_rule(
            dest=cmeta["dest"], days=cmeta["days"], budget=budget, banned_substrings=banned,
        )

        new_task = {**example.task, "prompt": new_prompt, "condition_meta": new_cmeta}
        new_example = BenchmarkExample(
            task_id=example.task_id,
            dataset=example.dataset,
            profile=corrupted_profile,
            task=new_task,
            trajectory=Trajectory(task_id=example.task_id, steps=[], final_output=None),
            dag=example.dag,
            gold=example.gold,
            rules=[rule],
            split=example.split,
        )
        out.append((new_example, mfr, chosen_types))
    return out


# ---------------------------------------------------------------------------
# Priming + arms (identical calling convention to every other Experiment D script)
# ---------------------------------------------------------------------------


def _prime_trajectory(
    example: BenchmarkExample, *, provider_name: str, model: str, seed: int, cache: SQLiteCache | None,
) -> tuple[Trajectory, int, int]:
    provider = build_provider(provider_name, cache=cache)
    payload, completion = provider.complete_json(
        system=DIRECT_AGENT_SYSTEM,
        user=direct_agent_user(profile=example.profile.model_dump(mode="json"), task=example.task),
        model=model, temperature=0.0, seed=seed, max_tokens=8192,
    )
    steps = coerce_trajectory_steps(payload.get("steps", []))
    final = coerce_final_output(payload.get("final_output"), fallback="") or ""
    if not steps:
        steps = [TrajectoryStep(step_id=1, kind="output", text=final)]  # type: ignore[arg-type]
    traj = Trajectory(task_id=example.task_id, steps=steps, final_output=final)
    return traj, completion.tokens_input, completion.tokens_output


def _llm_regenerate_fn(provider_name: str, model: str, seed: int, cache: SQLiteCache | None):
    """Unmodified copy of `intro_specter/runner.py::_llm_regenerate_fn`."""
    state = {"attempt": 0}

    def regenerate(profile, task):  # type: ignore[no-untyped-def]
        state["attempt"] += 1
        provider = build_provider(provider_name, cache=cache)
        attempt_seed = (seed or 0) * 7919 + state["attempt"]
        payload, completion = provider.complete_json(
            system=DIRECT_AGENT_SYSTEM,
            user=direct_agent_user(profile=profile.model_dump(mode="json"), task=task),
            model=model, temperature=0.7, seed=attempt_seed, max_tokens=8192,
        )
        steps = coerce_trajectory_steps(payload.get("steps", []))
        final = coerce_final_output(payload.get("final_output"), fallback="") or ""
        if not steps:
            steps = [TrajectoryStep(step_id=1, kind="output", text=final)]  # type: ignore[arg-type]
        traj = Trajectory(task_id=task.get("task_id", ""), steps=steps, final_output=final)
        return traj, completion.tokens_input, completion.tokens_output

    return regenerate


def _run_direct_arm(example, primed, *, provider_name, model, seed, cache):
    verifier = HybridVerifier(rules=list(example.rules))
    result = run_direct(profile=example.profile, task=example.task, trajectory=primed, verifier=verifier)
    return {
        "final_trajectory": result.final_trajectory,
        "method_believed_success": result.verifier.passed,
        "tokens_input": result.tokens_input,
        "tokens_output": result.tokens_output,
        "meta_summary": _meta_summary(result.meta),
    }


def _run_self_refine_arm(example, primed, *, provider_name, model, seed, cache):
    provider = build_provider(provider_name, cache=cache)
    verifier = HybridVerifier(rules=list(example.rules))
    result = run_self_refine(
        profile=example.profile, task=example.task, trajectory=primed, verifier=verifier,
        provider=provider, model=model, temperature=0.0, seed=seed,
    )
    return {
        "final_trajectory": result.final_trajectory,
        "method_believed_success": result.verifier.passed,
        "tokens_input": result.tokens_input,
        "tokens_output": result.tokens_output,
        "meta_summary": _meta_summary(result.meta),
    }


def _run_full_regen_arm(example, primed, *, provider_name, model, seed, cache):
    verifier = HybridVerifier(rules=list(example.rules))
    regen_fn = example.regenerate_fn or _llm_regenerate_fn(provider_name=provider_name, model=model, seed=seed, cache=cache)
    result = run_full_regen(
        profile=example.profile, task=example.task, trajectory=primed, verifier=verifier,
        regenerate_fn=regen_fn, max_attempts=1,
    )
    return {
        "final_trajectory": result.final_trajectory,
        "method_believed_success": result.verifier.passed,
        "tokens_input": result.tokens_input,
        "tokens_output": result.tokens_output,
        "meta_summary": _meta_summary(result.meta),
    }


def _run_react_arm(example, primed, *, provider_name, model, seed, cache):
    provider = build_provider(provider_name, cache=cache)
    verifier = HybridVerifier(rules=list(example.rules))
    result = run_react(
        profile=example.profile, task=example.task, trajectory=primed, verifier=verifier,
        provider=provider, model=model, temperature=0.0, seed=seed, max_steps=4,
    )
    return {
        "final_trajectory": result.final_trajectory,
        "method_believed_success": result.verifier.passed,
        "tokens_input": result.tokens_input,
        "tokens_output": result.tokens_output,
        "meta_summary": _meta_summary(result.meta),
    }


def _run_selfcheckgpt_arm(example, primed, *, provider_name, model, seed, cache):
    provider = build_provider(provider_name, cache=cache)
    verifier = HybridVerifier(rules=list(example.rules))
    result = run_selfcheckgpt(
        profile=example.profile, task=example.task, trajectory=primed, verifier=verifier,
        provider=provider, model=model, temperature=0.0, sample_temperature=1.0, seed=seed,
        n_samples=5, abstain_on_inconsistency=False,
    )
    return {
        "final_trajectory": result.final_trajectory,
        "method_believed_success": result.verifier.passed,
        "tokens_input": result.tokens_input,
        "tokens_output": result.tokens_output,
        "meta_summary": _meta_summary(result.meta),
    }


def _run_reflexion_arm(example, primed, *, provider_name, model, seed, cache):
    provider = build_provider(provider_name, cache=cache)
    verifier = HybridVerifier(rules=list(example.rules))
    result = run_reflexion(
        profile=example.profile, task=example.task, trajectory=primed, verifier=verifier,
        provider=provider, model=model, temperature=0.0, seed=seed, max_trials=2,
    )
    return {
        "final_trajectory": result.final_trajectory,
        "method_believed_success": result.verifier.passed,
        "tokens_input": result.tokens_input,
        "tokens_output": result.tokens_output,
        "meta_summary": _meta_summary(result.meta),
    }


def _run_intro_specter_arm(example, primed, *, provider_name, model, seed, cache):
    provider = build_provider(provider_name, cache=cache)
    verifier = HybridVerifier(rules=list(example.rules))
    evaluator = example.evaluator if example.evaluator is not None else _self_report_evaluator
    sampler = LLMCounterfactualSampler(
        provider=provider, model=model, evaluator=evaluator, temperature=0.5, seed=seed,
    )
    cfg = IntroSpecterConfig(
        model_extraction=model, model_verification=model, model_counterfactual=model,
        model_reexecution=model, extraction_provider=provider, reexecution_provider=provider,
        tau_abstain=0.0, cost_lambda=0.0, n_counterfactual_trials=1,
    )
    is_result = run_intro_specter(
        profile=example.profile, task=example.task, trajectory=primed, verifier=verifier,
        sampler=sampler, config=cfg, gold_dag=None, rerun_callable=example.rerun_fn,
    )
    final_traj = _recover_placeholder_final_output(is_result.final_trajectory, primed)
    return {
        "final_trajectory": final_traj,
        "method_believed_success": is_result.verifier.passed,
        "tokens_input": int(is_result.meta.get("tokens_input", 0)),
        "tokens_output": int(is_result.meta.get("tokens_output", 0)),
        "meta_summary": _meta_summary(is_result.meta),
    }


ARM_RUNNERS: dict[str, Callable[..., dict[str, Any]]] = {
    "direct": _run_direct_arm,
    "self_refine": _run_self_refine_arm,
    "full_regen": _run_full_regen_arm,
    "react": _run_react_arm,
    "selfcheckgpt": _run_selfcheckgpt_arm,
    "reflexion": _run_reflexion_arm,
    "intro_specter": _run_intro_specter_arm,
}


def run_cli(*, model_table: dict[str, tuple[str, str]], default_model: str, default_output_dirname: str) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default=default_model, choices=list(model_table))
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--n-examples", type=int, default=60)
    ap.add_argument("--num-faults", type=int, required=True, choices=sorted(SUPPORTED_NUMS))
    ap.add_argument("--scan-limit", type=int, default=None)
    ap.add_argument("--cache-path", default="cache/completions.sqlite")
    ap.add_argument(
        "--output-dir",
        default=f"outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic/{default_output_dirname}",
    )
    ap.add_argument("--output-name", default=None)
    ap.add_argument("--arms", default=None, help="comma-separated subset of arms to run (default: all)")
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    if args.smoke:
        n_examples = 3
        seeds = [0]
    else:
        n_examples = args.n_examples
        seeds = [int(s) for s in args.seeds.split(",") if s != ""]

    provider_name, model_id = model_table[args.model]
    cache = SQLiteCache(args.cache_path)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    arms = [a for a in (args.arms.split(",") if args.arms else list(ARM_RUNNERS)) if a]
    for a in arms:
        if a not in ARM_RUNNERS:
            raise ValueError(f"unknown arm {a!r}; choices: {list(ARM_RUNNERS)}")

    out_paths = {a: out_dir / (args.output_name or f"n{args.num_faults}__{a}.jsonl") for a in arms}
    done: dict[str, set[tuple[str, int]]] = {a: set() for a in arms}
    for a, p in out_paths.items():
        if p.exists():
            with p.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    done[a].add((row["task_id"], row["seed"]))
            if done[a]:
                print(f"Resuming arm={a}: {len(done[a])} (task_id, seed) rows already present, will be skipped.")

    print(f"Building {n_examples} {args.num_faults}-fault (1 ctx + "
          f"{_N_PROFILE_FAULTS_BY_N[args.num_faults]} profile) travelplanner_real SYNTHETIC examples "
          f"(bench_seed={BENCH_SEED}, scan_limit={args.scan_limit or 8000})...")
    examples = _build_examples(n_examples, BENCH_SEED, args.num_faults, args.scan_limit)
    print(f"Built {len(examples)} examples. seeds={seeds}, model={args.model}, arms={arms}")
    if len(examples) < n_examples:
        print(f"[WARN] only found {len(examples)}/{n_examples} qualifying examples within the scan pool "
              f"for N={args.num_faults}.")

    f_outs = {a: p.open("a") for a, p in out_paths.items()}
    total_tokens_in = 0
    total_tokens_out = 0
    n_rows = 0
    n_errors = 0

    for example, mfr, chosen_types in examples:
        cmeta = example.task["condition_meta"]
        true_budget = cmeta["budget"]
        for seed in seeds:
            pending_arms = [a for a in arms if (example.task_id, seed) not in done[a]]
            if not pending_arms:
                continue
            try:
                primed, prime_in, prime_out = _with_retry(
                    lambda: _prime_trajectory(
                        example, provider_name=provider_name, model=model_id, seed=seed, cache=cache,
                    ),
                    label=f"prime task={example.task_id} seed={seed}",
                )
            except Exception as e:  # pragma: no cover
                print(f"[ERROR] prime failed task={example.task_id} seed={seed}: {e}", file=sys.stderr)
                n_errors += 1
                continue

            for arm in pending_arms:
                runner_fn = ARM_RUNNERS[arm]
                try:
                    arm_out = _with_retry(
                        lambda: runner_fn(
                            example, primed, provider_name=provider_name, model=model_id,
                            seed=seed, cache=cache,
                        ),
                        label=f"{arm} task={example.task_id} seed={seed}",
                    )
                except Exception as e:  # pragma: no cover
                    print(f"[ERROR] {arm} failed task={example.task_id} seed={seed}: {e}", file=sys.stderr)
                    n_errors += 1
                    continue

                final_traj = arm_out["final_trajectory"]
                full_text = _trajectory_full_text(final_traj)
                per_fault: dict[str, bool] = {"ctx": _fault_ctx_resolved(full_text, true_budget)}
                for name in chosen_types:
                    _, checker = PROFILE_FAULT_TYPES[name]
                    true_text = mfr.true_constraint_texts[name]
                    per_fault[name] = checker(full_text, true_text)

                n_resolved = sum(1 for v in per_fault.values() if v)
                all_resolved = all(per_fault.values())
                tokens_input = arm_out["tokens_input"] + prime_in
                tokens_output = arm_out["tokens_output"] + prime_out
                row = {
                    "task_id": example.task_id,
                    "seed": seed,
                    "arm": arm,
                    "model": args.model,
                    "num_faults": args.num_faults,
                    "fault_types": ["ctx"] + chosen_types,
                    "per_fault_resolved": per_fault,
                    "all_resolved": all_resolved,
                    "n_resolved": n_resolved,
                    "method_believed_success": bool(arm_out["method_believed_success"]),
                    "true_constraint_texts": mfr.true_constraint_texts,
                    "true_budget": true_budget,
                    "level": cmeta.get("level"),
                    "final_output": (final_traj.final_output or "")[:4000],
                    "tokens_input": tokens_input,
                    "tokens_output": tokens_output,
                    "meta_summary": arm_out["meta_summary"],
                }
                f_outs[arm].write(json.dumps(row, default=str) + "\n")
                f_outs[arm].flush()
                total_tokens_in += tokens_input
                total_tokens_out += tokens_output
                n_rows += 1
                print(f"  N={args.num_faults} {example.task_id} seed={seed} arm={arm}: "
                      f"per_fault={per_fault} all_resolved={all_resolved} n_resolved={n_resolved}/{args.num_faults} "
                      f"tokens=({tokens_input},{tokens_output})")

    for f in f_outs.values():
        f.close()

    print(f"\n--- run summary (N={args.num_faults}, model={args.model}) ---")
    print(f"rows written: {n_rows}  errors: {n_errors}")
    print(f"total tokens_input={total_tokens_in}  total tokens_output={total_tokens_out}  "
          f"grand_total={total_tokens_in + total_tokens_out}")


__all__ = ["run_cli", "SUPPORTED_NUMS"]
