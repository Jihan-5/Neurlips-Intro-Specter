#!/usr/bin/env python3
"""Experiment C, non-synthetic MULTI-FAULT leg -- SHARED core logic.

Combines the two axes tonight's campaign had never tested together:
non-synthetic (TravelPlanner-native) constraints, corrupted with MULTIPLE
(N>=2) independent, simultaneous faults, across all 4 LLMs and the full
7-arm matrix (`direct`, `self_refine`, `full_regen`, `react`, `selfcheckgpt`,
`reflexion`, `intro_specter`) -- matching the rigor already applied to the
synthetic multi-fault matrix (TwoWiki/HotpotQA/MuSiQue/LongMemEval).

This is the natural extension of
`scripts/rebuttal_experiment_c_nonsynthetic_travelplanner.py` (single native
budget fault, 2 arms only) in three ways:
  1. N independent native-constraint faults per row instead of 1, via the
     new `intro_specter/profiles/native_multi_fault_injection.py` (adapts
     `double_fault_injection.py::build_multi_fault`'s disjoint-slot pattern
     to TravelPlanner's native `ProfileSpan` constraints -- see that module's
     docstring for the full feasibility investigation).
  2. All 7 baseline arms (this file), not just reflexion/intro_specter,
     reusing `intro_specter/baselines/*` with the exact same calling
     convention as `rebuttal_experiment_d_real_musique_common.py`.
  3. Same `_recover_placeholder_final_output` fix already found necessary
     for this benchmark (copied verbatim from the single-fault script) so
     intro_specter's scores aren't corrupted by the known
     `repair.py`/`pipeline.py` placeholder-final-output bug described there.

Feasible fault counts by level (see native_multi_fault_injection.py docstring
for the underlying measurement): easy rows support up to 2 independently
faultable slots (budget, days), medium up to 3 (+1 local constraint), hard up
to 5 (+3 local constraints; destination is excluded as a fault slot -- it is
never mechanically corruptible while the plan must still visit it). So:
    N=2 -- ALL 180 rows qualify (easy/medium/hard all have >=2 slots)
    N=3 -- medium+hard only (~120/180 rows; easy has only 2 slots)
    N=4, N=5 -- hard only (~60/180 rows; medium tops out at 3 slots)
This file reports the real achieved level distribution per run rather than
assuming it; `_build_multifault_examples` scans rows level-by-level (easy
first for N=2, since it's the fullest pool) and stops once `n_examples` is
reached or the eligible pool is exhausted, printing a `[WARN]` in that case
-- same "report real availability, don't force" discipline as every other
fault-count feasibility check tonight.

Resolution checking (mechanical, not LLM-judged), per faulted slot:
  budget          -- extracted "Total cost: $X" (regex, `_extract_total_cost`,
                     copied from the single-fault script) <= true budget.
  days            -- final plan mentions at least `min(true_days, 3)` distinct
                     "Day N" markers (same threshold the single-fault script's
                     `_make_native_rule` already used for its structural
                     day-count check).
  cuisine / house_rule / room_type / transportation
                  -- final plan text contains the TRUE (uncorrupted) value as
                     a case-insensitive substring. This is a keyword-mention
                     check, the same mechanical-but-coarse style already used
                     elsewhere in this campaign for categorical constraints
                     (e.g. `_resolved_bullets`/`_resolved_preamble` in the
                     musique_real common module) -- not a semantic judge, but
                     falsifiable and consistent across arms/models.

Output: `outputs/rebuttal/experiment_c/nonsynthetic_multifault/{model}/n{N}__{arm}.jsonl`,
one row per (task_id, seed), resumable/dedup'd exactly like every other
per-model script tonight.
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
from intro_specter.benchmarks.travelplanner_real import _load, _parse_local
from intro_specter.models import SQLiteCache, build_provider
from intro_specter.pipeline import IntroSpecterConfig, run_intro_specter
from intro_specter.profiles.native_multi_fault_injection import (
    NativeMultiFaultRecord,
    build_native_multi_fault,
    max_faultable_slots,
)
from intro_specter.prompts import DIRECT_AGENT_SYSTEM, direct_agent_user
from intro_specter.runner import _meta_summary, _self_report_evaluator
from intro_specter.schemas import (
    AssumptionDAG,
    GoldLabels,
    Severity,
    Trajectory,
    TrajectoryStep,
    UserProfile,
    ViolationEvent,
    coerce_final_output,
    coerce_trajectory_steps,
)
from intro_specter.verifier import HybridVerifier

BENCH_SEED = 42
HF_SPLIT = "validation"
N_HF_ROWS = 180

SUPPORTED_NUMS = {2, 3, 4, 5}
# N=1 is the already-completed single-fault script; N=6 would need 6
# faultable slots but the max any row supports is 5 (see module docstring
# for native_multi_fault_injection.py) -- not attempted, not forced.

_LEVELS_BY_N = {
    2: ["easy", "medium", "hard"],
    3: ["medium", "hard"],
    4: ["hard"],
    5: ["hard"],
}

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
    """Investigation finding (this file, smoke-test stage): unlike the
    single-fault script's assumption, TravelPlanner agents on this prompt
    template routinely put the actual day-by-day plan in the trajectory's
    LAST `steps` entry (kind=output) and leave `final_output` as a short
    "Total cost: $X" summary line -- confirmed by direct inspection of a
    primed mistral-nemo-12b trajectory during this script's build. Checking
    day-count / local-constraint (cuisine, house rule, ...) resolution
    against `final_output` ALONE would make those fault slots almost never
    resolve for ANY arm (not a real method difference, just where the model
    happens to put the text), so all mechanical resolution checks here scan
    the concatenation of every step's text plus `final_output` -- the same
    'read the whole trajectory, not just the one field' approach
    `rebuttal_experiment_d_real_musique_common.py::_trajectory_full_text`
    already uses for its own multi-fault scoring. (Budget's own "Total cost"
    figure lives at the very end of this concatenation regardless -- the
    single-fault script's final_output-only extraction worked for budget
    specifically because that line usually also appears there, but scanning
    the full text is a strict superset and never loses information.)"""
    parts = [trajectory.final_output or ""]
    for step in trajectory.steps:
        parts.append(getattr(step, "text", "") or "")
    return "\n".join(parts)


def _resolved_budget(full_text: str | None, true_budget: int) -> bool:
    cost = _extract_total_cost(full_text or "")
    return cost is not None and cost <= true_budget


def _resolved_days(full_text: str | None, true_days: int) -> bool:
    text_l = (full_text or "").lower()
    day_mentions = sum(1 for d in range(1, true_days + 1) if f"day {d}" in text_l)
    return day_mentions >= max(1, min(true_days, 3))


def _resolved_categorical(full_text: str | None, true_value: Any) -> bool:
    true_str = str(true_value or "").strip().lower()
    if not true_str:
        return True  # nothing to check (should not happen for a faulted slot)
    return true_str in (full_text or "").lower()


_RESOLVERS: dict[str, Callable[[str | None, Any], bool]] = {
    "budget": _resolved_budget,
    "days": _resolved_days,
    "cuisine": _resolved_categorical,
    "house_rule": _resolved_categorical,
    "room_type": _resolved_categorical,
    "transportation": _resolved_categorical,
}


# ---------------------------------------------------------------------------
# Example construction: scan the HF pool, keep rows whose level supports
# `num_faults`, build a native multi-fault BenchmarkExample for each.
# ---------------------------------------------------------------------------


def _make_multi_rule(dest: str, days_true: int, mfr: NativeMultiFaultRecord):
    def rule(profile, task, trajectory, final_output):
        text = _trajectory_full_text(trajectory)
        text_l = text.lower()
        out: list[ViolationEvent] = []
        if dest and dest.lower() not in text_l:
            out.append(ViolationEvent(
                violation_id="v_tpnative_mf_no_destination",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint=f"plan must mention destination {dest!r}",
                trajectory_text=text[:200], severity=Severity.HIGH,
                explanation="destination missing from plan",
            ))
        for slot in mfr.faulted_slots:
            resolver = _RESOLVERS[slot]
            true_val = mfr.true_values[slot]
            if not resolver(text, true_val):
                out.append(ViolationEvent(
                    violation_id=f"v_tpnative_mf_{slot}_unresolved",
                    step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                    violated_constraint=f"plan must satisfy TRUE {slot}={true_val!r} "
                                        f"(agent was shown corrupted value {mfr.corrupted_values[slot]!r})",
                    trajectory_text=text[:200], severity=Severity.HIGH,
                    explanation=f"Correction: the real {slot} is {true_val!r}, not the figure/value "
                                f"originally stated.",
                ))
        return out
    rule.__name__ = "travelplanner_nonsynthetic_multifault_rule"
    return rule


def _build_multifault_examples(
    n_examples: int, seed: int, num_faults: int, scan_limit: int | None = None,
) -> list[tuple[BenchmarkExample, NativeMultiFaultRecord]]:
    if num_faults not in SUPPORTED_NUMS:
        raise ValueError(f"num_faults={num_faults} not supported (choices: {sorted(SUPPORTED_NUMS)})")
    allowed_levels = set(_LEVELS_BY_N[num_faults])
    ds = _load(HF_SPLIT)
    scan_limit = scan_limit or (len(ds) * 4)  # allow repeated re-sampling like the single-fault script

    out: list[tuple[BenchmarkExample, NativeMultiFaultRecord]] = []
    import random
    idx = 0
    while len(out) < n_examples and idx < scan_limit:
        rng = random.Random(seed * 1_000_031 + idx)
        hf_idx = rng.randint(0, len(ds) - 1)
        ex = ds[hf_idx]
        idx += 1
        level = str(ex.get("level", "easy"))
        if level not in allowed_levels:
            continue
        local = _parse_local(str(ex["local_constraint"]))
        if max_faultable_slots(ex, local) < num_faults:
            continue  # shouldn't happen given the level filter, but double-check

        task_id = f"tp_nonsynth_mf{num_faults}_{idx:06d}"
        mfr = build_native_multi_fault(task_id=task_id, ex=ex, local=local, num_faults=num_faults)
        profile = UserProfile(user_id=f"tp_native_mf_{task_id}", spans=mfr.spans)

        query = str(ex["query"])
        for true_str, corrupted_str in mfr.query_substitutions:
            query = query.replace(true_str, corrupted_str)

        ref_info = str(ex.get("reference_information", ""))[:2500]
        prompt = (
            "User (native TravelPlanner) constraints:\n"
            + "\n".join(f"- {s.text}" for s in mfr.spans)
            + f"\n\nLocal constraints from booking system: {local}\n\n"
            f"Travelers: {ex['people_number']}\n"
            f"Origin: {ex['org']}, Destination: {ex['dest']}\n\n"
            f"Reference information:\n{ref_info}\n\n"
            f"Query: {query}\n\n"
            "Produce a concrete day-by-day plan. Each day must list "
            "accommodation, meals (with restaurants), and attractions, with a cost line. "
            "End with a 'Total cost: $...' summary."
        )

        condition_meta = {
            "level": level,
            "native_constraint_count": mfr.native_constraint_count,
            "num_faults": num_faults,
            "faulted_slots": mfr.faulted_slots,
            "true_values": mfr.true_values,
            "corrupted_values": mfr.corrupted_values,
            "days": int(ex["days"]),
            "dest": ex["dest"],
            "org": ex["org"],
            "local_constraint": local,
        }
        rule = _make_multi_rule(dest=ex["dest"], days_true=int(ex["days"]), mfr=mfr)

        task = {
            "task_id": task_id,
            "task_type": "travelplanner_nonsynthetic_multifault",
            "condition": f"planning_native_n{num_faults}_fault",
            "prompt": prompt,
            "split": "all",
            "condition_meta": condition_meta,
        }
        gold = GoldLabels(success=None, correct_final_output=None, fault_node_id=",".join(mfr.faulted_slots))
        bench_example = BenchmarkExample(
            task_id=task_id,
            dataset="travelplanner_nonsynthetic_multifault",
            profile=profile,
            task=task,
            trajectory=Trajectory(task_id=task_id, steps=[], final_output=None),
            dag=AssumptionDAG(task_id=task_id, nodes=[], edges=[]),
            gold=gold,
            rules=[rule],
            split="all",
        )
        out.append((bench_example, mfr))
    return out


# ---------------------------------------------------------------------------
# Priming + 7-arm runners (identical calling convention to
# rebuttal_experiment_d_real_musique_common.py)
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


def _recover_placeholder_final_output(final_traj: Trajectory, primed: Trajectory) -> Trajectory:
    """Copied verbatim from `rebuttal_experiment_c_nonsynthetic_travelplanner.py`
    -- see that function's docstring for the full bug description
    (`intro_specter/repair.py`'s downstream-regeneration fallback can return a
    non-empty placeholder string like "Total cost: $..." with no number,
    silently overwriting an already-correct primed answer). Same mechanical
    heuristic: if the pipeline output has no parseable total-cost figure but
    the primed trajectory does, prefer the primed trajectory's final_output."""
    current_cost = _extract_total_cost(final_traj.final_output or "")
    if current_cost is not None:
        return final_traj
    primed_cost = _extract_total_cost(primed.final_output or "")
    if primed_cost is None:
        return final_traj
    return Trajectory(task_id=final_traj.task_id, steps=final_traj.steps, final_output=primed.final_output)


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
        default=f"outputs/rebuttal/experiment_c/nonsynthetic_multifault/{default_output_dirname}",
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

    print(f"Building {n_examples} native-multi-fault (N={args.num_faults}) travelplanner examples "
          f"(bench_seed={BENCH_SEED}, allowed_levels={_LEVELS_BY_N[args.num_faults]})...")
    examples = _build_multifault_examples(n_examples, BENCH_SEED, args.num_faults, args.scan_limit)
    from collections import Counter
    level_counts = Counter(mfr.level for _, mfr in examples)
    print(f"Built {len(examples)} examples. level distribution={dict(level_counts)}, "
          f"seeds={seeds}, model={args.model}, arms={arms}")
    if len(examples) < n_examples:
        print(f"[WARN] only found {len(examples)}/{n_examples} qualifying examples within the scan pool "
              f"for N={args.num_faults} (allowed levels={_LEVELS_BY_N[args.num_faults]}).")

    f_outs = {a: p.open("a") for a, p in out_paths.items()}
    total_tokens_in = 0
    total_tokens_out = 0
    n_rows = 0
    n_errors = 0

    for example, mfr in examples:
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
                per_fault: dict[str, bool] = {}
                for slot in mfr.faulted_slots:
                    per_fault[slot] = _RESOLVERS[slot](full_text, mfr.true_values[slot])
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
                    "level": mfr.level,
                    "native_constraint_count": mfr.native_constraint_count,
                    "faulted_slots": mfr.faulted_slots,
                    "true_values": mfr.true_values,
                    "corrupted_values": mfr.corrupted_values,
                    "per_fault_resolved": per_fault,
                    "all_resolved": all_resolved,
                    "n_resolved": n_resolved,
                    "method_believed_success": bool(arm_out["method_believed_success"]),
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
                print(f"  N={args.num_faults} {example.task_id} seed={seed} arm={arm} level={mfr.level}: "
                      f"per_fault={per_fault} all_resolved={all_resolved} n_resolved={n_resolved}/{args.num_faults} "
                      f"tokens=({tokens_input},{tokens_output})")

    for f in f_outs.values():
        f.close()

    print(f"\n--- run summary (N={args.num_faults}, model={args.model}) ---")
    print(f"rows written: {n_rows}  errors: {n_errors}")
    print(f"total tokens_input={total_tokens_in}  total tokens_output={total_tokens_out}  "
          f"grand_total={total_tokens_in + total_tokens_out}")


__all__ = ["run_cli", "SUPPORTED_NUMS"]
