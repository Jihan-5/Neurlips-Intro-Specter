#!/usr/bin/env python3
"""Experiment D full-matrix expansion (N=2/3/4), model=mistral-nemo-12b ONLY.

Rebuttal follow-up: tonight's multi-fault campaign (see
`scripts/rebuttal_experiment_d_real.py`) ran real Reflexion vs. real
Intro-Specter on twowiki_real x mistral-nemo-12b for N in {2,3,4,5} and found
IS winning at N=3/4 and tied at N=2/5. The user asked for the full 7-arm
baseline matrix (direct, self_refine, reflexion, full_regen, react,
selfcheckgpt, intro_specter) at every fault count, reusing the SAME injected
examples tonight's run already used (so the new arms are directly comparable
row-for-row, not a fresh independent sample).

This is an ADDITIVE, NEW file. It does not edit `rebuttal_experiment_d_real.py`
-- instead it dynamically imports that (unmodified) script as a module via
`importlib` (scripts/ has no `__init__.py`, so it isn't a normal package) to
reuse, byte-for-byte, its `_build_multi_fault_examples`, `PROFILE_FAULT_TYPES`,
`_fault_ctx_resolved`, `_prime_trajectory`, `MODEL_TABLE`, `BENCH_SEED`, and
`_with_retry` -- guaranteeing this script builds the IDENTICAL example set
(same BENCH_SEED=42, same scan pools, same deterministic profile-fault-type
selection) that produced tonight's `real_multi_fault_n{N}.jsonl` reflexion +
intro_specter rows. `reflexion` and `intro_specter` are therefore NOT re-run
here (they already exist, at the same n_examples/seeds, in
`outputs/rebuttal/experiment_d/real_multi_fault_n{N}.jsonl`) -- this script
covers only the 5 NEW arms:
    direct, self_refine, full_regen, react, selfcheckgpt
(`tot` and `intro_specter_fixed` excluded per explicit user instruction.)

Baselines are the SAME registered implementations used in the paper's main
real-benchmark runs (`intro_specter/baselines/*.py`, unmodified), called with
the exact same convention `intro_specter/runner.py::run_method_on_example`
uses (same defaults as `configs/real/real_2wiki__*.yaml`: self_refine
n_rounds=1 default, full_regen max_attempts=1, react max_steps=4,
selfcheckgpt n_samples=5 / sample_temperature=1.0).

Output: one file per (N, arm):
    outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b/n{N}__{arm}.jsonl

Usage:
    python3 scripts/rebuttal_experiment_d_real_fullmatrix_mistral.py --num-faults 2 --arms direct,self_refine
    python3 scripts/rebuttal_experiment_d_real_fullmatrix_mistral.py --num-faults 3 --seeds 0,1,2
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable, TypeVar

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_T = TypeVar("_T")

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, rel_path: str):
    spec = importlib.util.spec_from_file_location(name, _REPO_ROOT / rel_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


# Unmodified sibling script, loaded as a module (not edited, not re-executed
# as __main__ -- module-level code below `if __name__ == "__main__":` never runs).
_BASE = _load_module("rebuttal_experiment_d_real_base", "scripts/rebuttal_experiment_d_real.py")

_with_retry = _BASE._with_retry
MODEL_TABLE = _BASE.MODEL_TABLE
BENCH_SEED = _BASE.BENCH_SEED
_build_multi_fault_examples = _BASE._build_multi_fault_examples
PROFILE_FAULT_TYPES = _BASE.PROFILE_FAULT_TYPES
_fault_ctx_resolved = _BASE._fault_ctx_resolved
_prime_trajectory = _BASE._prime_trajectory
_SCAN_LIMIT_BY_N = _BASE._SCAN_LIMIT_BY_N

from intro_specter.baselines import (
    run_direct,
    run_full_regen,
    run_react,
    run_selfcheckgpt,
    run_self_refine,
)
from intro_specter.models import SQLiteCache, build_provider
from intro_specter.runner import _llm_regenerate_fn, _meta_summary
from intro_specter.verifier import HybridVerifier

MODEL_NAME = "mistral-nemo-12b"


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
    regen_fn = example.regenerate_fn
    if regen_fn is None:
        regen_fn = _llm_regenerate_fn(provider_name=provider_name, model=model, seed=seed, cache=cache)
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
        provider=provider, model=model, temperature=0.0, sample_temperature=1.0,
        seed=seed, n_samples=5, abstain_on_inconsistency=False,
    )
    return {
        "final_trajectory": result.final_trajectory,
        "method_believed_success": result.verifier.passed,
        "tokens_input": result.tokens_input,
        "tokens_output": result.tokens_output,
        "meta_summary": _meta_summary(result.meta),
    }


ARM_RUNNERS: dict[str, Callable[..., dict[str, Any]]] = {
    "direct": _run_direct_arm,
    "self_refine": _run_self_refine_arm,
    "full_regen": _run_full_regen_arm,
    "react": _run_react_arm,
    "selfcheckgpt": _run_selfcheckgpt_arm,
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--n-examples", type=int, default=60)
    ap.add_argument("--num-faults", type=int, required=True, choices=[2, 3, 4])
    ap.add_argument("--scan-limit", type=int, default=None)
    ap.add_argument("--arms", default=",".join(ARM_RUNNERS), help="comma-separated subset of arms to run")
    ap.add_argument("--cache-path", default="cache/completions.sqlite")
    ap.add_argument(
        "--output-dir", default="outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b",
    )
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    for a in arms:
        if a not in ARM_RUNNERS:
            raise SystemExit(f"unknown arm {a!r}; choices={list(ARM_RUNNERS)}")

    if args.smoke:
        n_examples = 3
        seeds = [0]
    else:
        n_examples = args.n_examples
        seeds = [int(s) for s in args.seeds.split(",") if s != ""]

    provider_name, model_id = MODEL_TABLE[MODEL_NAME]
    cache = SQLiteCache(args.cache_path)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Building {n_examples} {args.num_faults}-fault-injected twowiki_real examples "
          f"(bench_seed={BENCH_SEED}, IDENTICAL to rebuttal_experiment_d_real.py's set)...")
    examples = _build_multi_fault_examples(n_examples, BENCH_SEED, args.num_faults, args.scan_limit)
    print(f"Built {len(examples)} examples. seeds={seeds}, arms={arms}")
    if len(examples) < n_examples:
        print(f"[WARN] only found {len(examples)}/{n_examples} qualifying examples.")

    for arm in arms:
        out_path = out_dir / f"n{args.num_faults}__{arm}.jsonl"
        done: set[tuple[str, int]] = set()
        if out_path.exists():
            with out_path.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    done.add((row["task_id"], row["seed"]))
        if done:
            print(f"[{arm}] Resuming: {len(done)} (task_id, seed) rows already present.")

        runner_fn = ARM_RUNNERS[arm]
        f_out = out_path.open("a")
        total_tokens_in = 0
        total_tokens_out = 0
        n_rows = 0
        n_errors = 0

        for example, mfr, chosen_types in examples:
            for seed in seeds:
                if (example.task_id, seed) in done:
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
                true_answer = example.task["condition_meta"]["answer"]
                per_fault: dict[str, bool] = {"ctx": _fault_ctx_resolved(final_traj.final_output, true_answer)}
                for name in chosen_types:
                    _, checker = PROFILE_FAULT_TYPES[name]
                    true_text = mfr.true_constraint_texts[name]
                    per_fault[name] = checker(final_traj.final_output, true_text)

                n_resolved = sum(1 for v in per_fault.values() if v)
                all_resolved = all(per_fault.values())
                tokens_input = arm_out["tokens_input"] + prime_in
                tokens_output = arm_out["tokens_output"] + prime_out
                row = {
                    "task_id": example.task_id,
                    "seed": seed,
                    "arm": arm,
                    "num_faults": args.num_faults,
                    "fault_types": ["ctx"] + chosen_types,
                    "per_fault_resolved": per_fault,
                    "all_resolved": all_resolved,
                    "n_resolved": n_resolved,
                    "method_believed_success": bool(arm_out["method_believed_success"]),
                    "true_constraint_texts": mfr.true_constraint_texts,
                    "tokens_input": tokens_input,
                    "tokens_output": tokens_output,
                    "meta_summary": arm_out["meta_summary"],
                }
                f_out.write(json.dumps(row, default=str) + "\n")
                f_out.flush()
                total_tokens_in += tokens_input
                total_tokens_out += tokens_output
                n_rows += 1
                print(f"  N={args.num_faults} arm={arm} {example.task_id} seed={seed}: "
                      f"per_fault={per_fault} all_resolved={all_resolved} n_resolved={n_resolved}/{args.num_faults} "
                      f"tokens=({tokens_input},{tokens_output})")

        f_out.close()
        print(f"--- [{arm}] N={args.num_faults}: rows written={n_rows} errors={n_errors} "
              f"tokens_in={total_tokens_in} tokens_out={total_tokens_out} ---")


if __name__ == "__main__":
    main()
