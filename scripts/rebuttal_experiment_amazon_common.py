#!/usr/bin/env python3
"""Amazon-products non-synthetic (native) multi-fault experiment -- SHARED
core logic.

This is the Amazon-domain sibling of
`rebuttal_experiment_c_nonsynthetic_multifault_common.py`: same 7-arm
(`direct`, `self_refine`, `full_regen`, `react`, `selfcheckgpt`, `reflexion`,
`intro_specter`) x 4-model x N-fault matrix, same retry/resume/dedup
discipline, same `_recover_placeholder_final_output` guard against the
known `repair.py` placeholder-final-output bug -- built against REAL Amazon
product metadata (`davidberenstein1957/Amazon-Reviews-2023-Retail-Products`,
a verified Parquet mirror of the official McAuley-Lab Amazon-Reviews-2023
raw_meta schema; see `intro_specter/benchmarks/amazon_products_real.py`'s
module docstring for why this mirror is used instead of the original
script-based HF dataset, which current `datasets` releases can no longer
load at all -- a real, verified blocker, not an assumption) instead of
TravelPlanner's.

Native constraint slots (see `amazon_native_multi_fault_injection.py`):
    price     -- numeric ceiling, present 100% of rows
    brand     -- categorical, present ~98% of rows
    category  -- categorical, present ~100% of rows (falls back to
                 main_category when the categories leaf is generic)
    feature   -- short spec snippet, present ~96% of rows
Measured (4,000-row sample, seed=7): 94.8% of rows support all 4 slots
simultaneously, 5.1% support exactly 3, ~0.1% fewer. So N=1..4 are ALL
broadly feasible across virtually the whole pool -- no level-gating is
needed the way TravelPlanner's hard/medium/easy split requires; this
script filters per-row on `max_faultable_slots(ex) >= num_faults` and
reports the real achieved count/skip-rate rather than assuming full
coverage.

Resolution checking (mechanical, not LLM-judged), per faulted slot:
  price     -- extracted "Price: $X" (regex, `_extract_price`, reused from
               `amazon_products_real.py`) <= true (uncorrupted) budget
               ceiling.
  brand / category / feature
            -- final recommendation text contains the TRUE (uncorrupted)
               value as a case-insensitive substring. Same mechanical
               keyword-mention style already used for TravelPlanner's own
               categorical native-fault resolution checks.

Output: `outputs/rebuttal/experiment_amazon/{model}/n{N}__{arm}.jsonl`, one
row per (task_id, seed), resumable/dedup'd exactly like every other
per-model script in this campaign.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter
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
from intro_specter.benchmarks.amazon_products_real import _extract_price, _load
from intro_specter.benchmarks.base import BenchmarkExample
from intro_specter.models import SQLiteCache, build_provider
from intro_specter.pipeline import IntroSpecterConfig, run_intro_specter
from intro_specter.profiles.amazon_native_multi_fault_injection import (
    AmazonNativeMultiFaultRecord,
    build_amazon_native_multi_fault,
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
HF_SPLIT = "train"

SUPPORTED_NUMS = {1, 2, 3, 4}


def _trajectory_full_text(trajectory: Trajectory) -> str:
    """Same 'scan the whole trajectory, not just final_output' discipline as
    `rebuttal_experiment_c_nonsynthetic_multifault_common.py::_trajectory_full_text`
    -- Amazon recommendation agents on this prompt template occasionally put
    the actual recommendation in a trajectory step and leave `final_output`
    as a short summary, same class of pipeline behavior found there."""
    parts = [trajectory.final_output or ""]
    for step in trajectory.steps:
        parts.append(getattr(step, "text", "") or "")
    return "\n".join(parts)


def _resolved_price(full_text: str | None, true_budget: float, final_output: str | None = None) -> bool:
    """Prefer the price stated in `final_output` (the actual answer) over one
    picked up from an earlier trajectory step that merely echoes the
    corrupted budget -- `_extract_price` takes the LAST dollar match in
    whatever text it's given, and `full_text` = final_output + all steps
    concatenated, so a later step mentioning the corrupted ceiling would
    otherwise win over a correct price already stated in final_output."""
    if final_output:
        fo_price = _extract_price(final_output)
        if fo_price is not None:
            return fo_price <= true_budget
    price = _extract_price(full_text or "")
    return price is not None and price <= true_budget


def _resolved_categorical(full_text: str | None, true_value: Any) -> bool:
    true_str = str(true_value or "").strip().lower()
    if not true_str:
        return True
    return true_str in (full_text or "").lower()


_RESOLVERS: dict[str, Callable[[str | None, Any], bool]] = {
    "price": _resolved_price,
    "brand": _resolved_categorical,
    "category": _resolved_categorical,
    "feature": _resolved_categorical,
}


def _make_multi_rule(mfr: AmazonNativeMultiFaultRecord):
    def rule(profile, task, trajectory, final_output):
        text = _trajectory_full_text(trajectory)
        out: list[ViolationEvent] = []
        for slot in mfr.faulted_slots:
            resolver = _RESOLVERS[slot]
            true_val = mfr.true_values[slot]
            resolved = (
                resolver(text, true_val, final_output)
                if slot == "price"
                else resolver(text, true_val)
            )
            if not resolved:
                out.append(ViolationEvent(
                    violation_id=f"v_amznative_mf_{slot}_unresolved",
                    step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                    violated_constraint=f"recommendation must satisfy TRUE {slot}={true_val!r} "
                                        f"(agent was shown corrupted value {mfr.corrupted_values.get(slot)!r})",
                    trajectory_text=text[:200], severity=Severity.HIGH,
                    explanation=f"Correction: the real {slot} is {true_val!r}, not the figure/value "
                                f"originally stated.",
                ))
        return out
    rule.__name__ = "amazon_nonsynthetic_multifault_rule"
    return rule


def _build_multifault_examples(
    n_examples: int, seed: int, num_faults: int, scan_limit: int | None = None,
) -> list[tuple[BenchmarkExample, AmazonNativeMultiFaultRecord]]:
    if num_faults not in SUPPORTED_NUMS:
        raise ValueError(f"num_faults={num_faults} not supported (choices: {sorted(SUPPORTED_NUMS)})")
    ds = _load(HF_SPLIT)
    n_rows = len(ds)
    scan_limit = scan_limit or (n_examples * 20)

    out: list[tuple[BenchmarkExample, AmazonNativeMultiFaultRecord]] = []
    n_skipped_no_price = 0
    n_skipped_too_few_slots = 0
    idx = 0
    while len(out) < n_examples and idx < scan_limit:
        rng = random.Random(seed * 1_000_031 + idx)
        hf_idx = rng.randint(0, n_rows - 1)
        ex = ds[hf_idx]
        idx += 1
        if ex.get("price") is None:
            n_skipped_no_price += 1
            continue
        if max_faultable_slots(ex) < num_faults:
            n_skipped_too_few_slots += 1
            continue

        task_id = f"amz_nonsynth_mf{num_faults}_{idx:06d}"
        mfr = build_amazon_native_multi_fault(task_id=task_id, ex=ex, num_faults=num_faults)
        profile = UserProfile(user_id=f"amz_native_mf_{task_id}", spans=mfr.spans)

        prompt = (
            "You are a shopping assistant. A customer wants a product recommendation "
            "that satisfies ALL of the following constraints:\n"
            + "\n".join(f"- {s.text}" for s in mfr.spans)
            + "\n\nRecommend ONE specific product (invent a plausible product name/model "
            "if needed) that satisfies every constraint above. State the product name, "
            "brand, category, and how it meets the required feature/spec. "
            "End with a line 'Price: $X.XX'."
        )

        condition_meta = {
            "native_constraint_count": mfr.native_constraint_count,
            "num_faults": num_faults,
            "faulted_slots": mfr.faulted_slots,
            "true_values": mfr.true_values,
            "corrupted_values": mfr.corrupted_values,
        }
        rule = _make_multi_rule(mfr)

        task = {
            "task_id": task_id,
            "task_type": "amazon_nonsynthetic_multifault",
            "condition": f"recommendation_native_n{num_faults}_fault",
            "prompt": prompt,
            "split": "all",
            "condition_meta": condition_meta,
        }
        gold = GoldLabels(success=None, correct_final_output=None, fault_node_id=",".join(mfr.faulted_slots))
        bench_example = BenchmarkExample(
            task_id=task_id,
            dataset="amazon_nonsynthetic_multifault",
            profile=profile,
            task=task,
            trajectory=Trajectory(task_id=task_id, steps=[], final_output=None),
            dag=AssumptionDAG(task_id=task_id, nodes=[], edges=[]),
            gold=gold,
            rules=[rule],
            split="all",
        )
        out.append((bench_example, mfr))

    if n_skipped_no_price or n_skipped_too_few_slots:
        print(f"[INFO] scan skipped {n_skipped_no_price} rows (no price), "
              f"{n_skipped_too_few_slots} rows (< {num_faults} faultable slots)")
    return out


# ---------------------------------------------------------------------------
# Priming + 7-arm runners (identical calling convention to
# rebuttal_experiment_c_nonsynthetic_multifault_common.py)
# ---------------------------------------------------------------------------


def _prime_trajectory(
    example: BenchmarkExample, *, provider_name: str, model: str, seed: int, cache: SQLiteCache | None,
) -> tuple[Trajectory, int, int]:
    provider = build_provider(provider_name, cache=cache)
    payload, completion = provider.complete_json(
        system=DIRECT_AGENT_SYSTEM,
        user=direct_agent_user(profile=example.profile.model_dump(mode="json"), task=example.task),
        model=model, temperature=0.0, seed=seed, max_tokens=4096,
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
            model=model, temperature=0.7, seed=attempt_seed, max_tokens=4096,
        )
        steps = coerce_trajectory_steps(payload.get("steps", []))
        final = coerce_final_output(payload.get("final_output"), fallback="") or ""
        if not steps:
            steps = [TrajectoryStep(step_id=1, kind="output", text=final)]  # type: ignore[arg-type]
        traj = Trajectory(task_id=task.get("task_id", ""), steps=steps, final_output=final)
        return traj, completion.tokens_input, completion.tokens_output

    return regenerate


def _recover_placeholder_final_output(final_traj: Trajectory, primed: Trajectory) -> Trajectory:
    """Copied verbatim (Amazon-adapted) from
    `rebuttal_experiment_c_nonsynthetic_multifault_common.py`'s function of
    the same name -- see that docstring for the full bug description
    (`intro_specter/repair.py`'s downstream-regeneration fallback can return
    a non-empty placeholder string with no parseable price, silently
    overwriting an already-correct primed answer). Same mechanical
    heuristic: if the pipeline output has no parseable price but the primed
    trajectory does, prefer the primed trajectory's final_output."""
    current_price = _extract_price(final_traj.final_output or "")
    if current_price is not None:
        return final_traj
    primed_price = _extract_price(primed.final_output or "")
    if primed_price is None:
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
        default=f"outputs/rebuttal/experiment_amazon/{default_output_dirname}",
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

    print(f"Building {n_examples} native-multi-fault (N={args.num_faults}) amazon examples "
          f"(bench_seed={BENCH_SEED})...")
    examples = _build_multifault_examples(n_examples, BENCH_SEED, args.num_faults, args.scan_limit)
    print(f"Built {len(examples)} examples. seeds={seeds}, model={args.model}, arms={arms}")
    if len(examples) < n_examples:
        print(f"[WARN] only found {len(examples)}/{n_examples} qualifying examples within the scan pool "
              f"for N={args.num_faults}.")

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
