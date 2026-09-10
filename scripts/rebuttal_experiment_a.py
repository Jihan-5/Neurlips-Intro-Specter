#!/usr/bin/env python3
"""Experiment A: profile-noise robustness (rebuttal campaign).

Corrupts each example's TRUE profile with a deterministic operator mix
(rho = fraction of relevant constraints corrupted), runs Reflexion and
Intro-Specter against the CORRUPTED profile, then re-scores each method's
actual output against the ORIGINAL, uncorrupted profile + rules to get a
TRUE-success metric independent of what the method believed. See the task
brief for the full design; this file is additive-only.

Usage (smoke test — 2 examples, 1 seed, both arms, only hits already-cached
completions where possible; corrupted profiles will still cause new prompts
and therefore real, small API spend):

    python3 scripts/rebuttal_experiment_a.py \\
        --dataset truthfulqa_real --model mistral-nemo-12b --rho 0.30 --smoke
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, TypeVar

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_T = TypeVar("_T")


def _with_retry(fn: Callable[[], _T], *, attempts: int = 3, base_delay: float = 2.0, label: str = "") -> _T:
    """Transient upstream errors (e.g. OpenRouter 'no choices') are retried with backoff;
    the last attempt's exception propagates so the caller's existing error handling/logging
    still fires if all retries are exhausted."""
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
from intro_specter.baselines import run_reflexion
from intro_specter.benchmarks.base import BenchmarkExample
from intro_specter.benchmarks.truthfulqa_real import TruthfulQAReal
from intro_specter.models import SQLiteCache, build_provider
from intro_specter.pipeline import IntroSpecterConfig, run_intro_specter
from intro_specter.profile_corruption import corrupt_profile
from intro_specter.prompts import DIRECT_AGENT_SYSTEM, direct_agent_user
from intro_specter.runner import _meta_summary, _self_report_evaluator
from intro_specter.schemas import Trajectory, TrajectoryStep, coerce_final_output, coerce_trajectory_steps
from intro_specter.verifier import HybridVerifier

# (slug, provider_name, model_id) — copied verbatim from
# scripts/generate_real_configs.py MODELS table so CLI --model matches the
# real-benchmark naming convention.
MODEL_TABLE = {
    "llama-3.3-70b":    ("together",   "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
    "llama-3.1-8b":     ("openrouter", "meta-llama/llama-3.1-8b-instruct"),
    "deepseek-v3":      ("together",   "deepseek-ai/DeepSeek-V3"),
    "deepseek-v3.1":    ("together",   "deepseek-ai/DeepSeek-V3.1"),
    "mistral-nemo-12b": ("openrouter", "mistralai/mistral-nemo"),
    "qwen-2.5-7b":      ("openrouter", "qwen/qwen-2.5-7b-instruct"),
    "gemini-2.5-flash": ("openrouter", "google/gemini-2.5-flash"),
    "gpt-oss-20b":      ("together",   "openai/gpt-oss-20b"),
}

# Dataset registry. Only truthfulqa_real is wired up for this first pass, per
# the task brief ("truthfulqa_real to start"); add entries here to extend.
# `bench_seed` is the seed passed to the loader's own constructor (matching
# the real config's protocol, e.g. real_truthfulqa_real__*.yaml uses seeds
# [42, 123, 456] — we fix the FIRST of those so example/task_id selection
# matches the existing outputs/real/ runs 1:1; the CLI `--seeds` below is a
# separate axis: independent corruption-noise / generation-trial draws on
# top of that same fixed example set. This is a design assumption — the task
# brief did not disambiguate "example seed" from "trial seed"; flagged here.
DATASET_REGISTRY: dict[str, dict[str, Any]] = {
    "truthfulqa_real": {
        "cls": TruthfulQAReal,
        "bench_seed": 42,
        "split": "test",
        "n_examples": 60,
    },
}


def _load_examples(dataset: str, n_examples: int) -> list[BenchmarkExample]:
    reg = DATASET_REGISTRY[dataset]
    bench = reg["cls"](n_examples=n_examples, seed=reg["bench_seed"], split=reg["split"])
    return list(bench)


def _constraint_meta(example: BenchmarkExample) -> dict[str, dict[str, Any]]:
    raw = example.task.get("condition_meta", {}).get("profile_constraints", [])
    return {c["id"]: {"relevant": c["relevant"], "category": c["category"]} for c in raw}


def _corruption_seed(task_id: str, seed: int, rho: float) -> int:
    h = hashlib.sha256(f"{task_id}|{seed}|{rho}".encode()).hexdigest()
    return int(h[:8], 16)


def _prime_trajectory(
    example: BenchmarkExample, *, provider_name: str, model: str, seed: int, cache: SQLiteCache | None
) -> tuple[Trajectory, int, int]:
    """Runs the direct-agent prompt once against `example.profile` (already the
    CORRUPTED profile at call time — this is what makes the agent's belief
    reflect the corrupted profile). Mirrors runner.py::_prime_initial_trajectory."""
    provider = build_provider(provider_name, cache=cache)
    payload, completion = provider.complete_json(
        system=DIRECT_AGENT_SYSTEM,
        user=direct_agent_user(profile=example.profile.model_dump(mode="json"), task=example.task),
        model=model,
        temperature=0.0,
        seed=seed,
        max_tokens=8192,
    )
    steps = coerce_trajectory_steps(payload.get("steps", []))
    final = coerce_final_output(payload.get("final_output"), fallback="") or ""
    if not steps:
        steps = [TrajectoryStep(step_id=1, kind="output", text=final)]  # type: ignore[arg-type]
    traj = Trajectory(task_id=example.task_id, steps=steps, final_output=final)
    return traj, completion.tokens_input, completion.tokens_output


def _true_success(example: BenchmarkExample, final_trajectory: Trajectory) -> bool:
    """Re-scores the method's actual output against the ORIGINAL, uncorrupted
    profile + rules — independent of whatever the method's own (corrupted-
    profile) verifier believed."""
    fresh_verifier = HybridVerifier(rules=list(example.rules))
    check, _ = fresh_verifier.check(
        profile=example.profile,
        task=example.task,
        trajectory=final_trajectory,
        final_output=final_trajectory.final_output,
    )
    return check.passed


def _run_reflexion_arm(
    example: BenchmarkExample,
    primed: Trajectory,
    *,
    provider_name: str,
    model: str,
    seed: int,
    cache: SQLiteCache | None,
) -> dict[str, Any]:
    provider = build_provider(provider_name, cache=cache)
    verifier = HybridVerifier(rules=list(example.rules))
    result = run_reflexion(
        profile=example.profile,
        task=example.task,
        trajectory=primed,
        verifier=verifier,
        provider=provider,
        model=model,
        temperature=0.0,  # matches MethodConfig default temperature used by the real runs
        seed=seed,
        max_trials=2,  # Table 11 default / real config `extra.max_trials`
    )
    return {
        "final_trajectory": result.final_trajectory,
        "method_believed_success": result.verifier.passed,
        "tokens_input": result.tokens_input,
        "tokens_output": result.tokens_output,
        "abstained": None,  # reflexion has no abstain concept
        "meta_summary": _meta_summary(result.meta),
    }


def _run_intro_specter_arm(
    example: BenchmarkExample,
    primed: Trajectory,
    *,
    provider_name: str,
    model: str,
    seed: int,
    cache: SQLiteCache | None,
) -> dict[str, Any]:
    provider = build_provider(provider_name, cache=cache)
    verifier = HybridVerifier(rules=list(example.rules))
    evaluator = example.evaluator if example.evaluator is not None else _self_report_evaluator
    sampler = LLMCounterfactualSampler(
        provider=provider, model=model, evaluator=evaluator, temperature=0.5, seed=seed
    )
    cfg = IntroSpecterConfig(
        model_extraction=model,
        model_verification=model,
        model_counterfactual=model,
        model_reexecution=model,
        extraction_provider=provider,
        reexecution_provider=provider,
        tau_abstain=0.25,  # Experiment A override — every existing config uses 0.0
        cost_lambda=0.0,
        n_counterfactual_trials=1,  # matches real config's `extra.n_counterfactual_trials`
        # all other fields left at IntroSpecterConfig dataclass defaults (Table 11)
    )
    gold_dag_arg = example.dag if (example.dag is not None and example.dag.nodes) else None
    is_result = run_intro_specter(
        profile=example.profile,
        task=example.task,
        trajectory=primed,
        verifier=verifier,
        sampler=sampler,
        config=cfg,
        gold_dag=gold_dag_arg,
        rerun_callable=example.rerun_fn,
    )
    return {
        "final_trajectory": is_result.final_trajectory,
        "method_believed_success": is_result.verifier.passed,
        "tokens_input": int(is_result.meta.get("tokens_input", 0)),
        "tokens_output": int(is_result.meta.get("tokens_output", 0)),
        "abstained": is_result.status == "abstain_or_full_regenerate",
        "meta_summary": _meta_summary(is_result.meta),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", default="truthfulqa_real", choices=list(DATASET_REGISTRY))
    ap.add_argument("--model", required=True, choices=list(MODEL_TABLE))
    ap.add_argument("--rho", type=float, required=True, choices=[0.10, 0.30])
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--n-examples", type=int, default=None)
    ap.add_argument("--cache-path", default="cache/completions.sqlite")
    ap.add_argument("--output-dir", default="outputs/rebuttal/experiment_a")
    ap.add_argument("--smoke", action="store_true", help="n=2 examples, 1 seed, both arms, then stop")
    args = ap.parse_args()

    if args.smoke:
        n_examples = 2
        seeds = [0]
    else:
        n_examples = args.n_examples or DATASET_REGISTRY[args.dataset]["n_examples"]
        seeds = [int(s) for s in args.seeds.split(",") if s != ""]

    provider_name, model_id = MODEL_TABLE[args.model]
    cache = SQLiteCache(args.cache_path)

    out_dir = Path(args.output_dir) / f"{args.dataset}__{args.model}"
    out_dir.mkdir(parents=True, exist_ok=True)
    rho_tag = f"rho{int(round(args.rho * 100))}"
    paths = {arm: out_dir / f"{rho_tag}__{arm}.jsonl" for arm in ("reflexion", "intro_specter")}

    done: dict[str, set[tuple[str, int]]] = {"reflexion": set(), "intro_specter": set()}
    for arm, p in paths.items():
        if p.exists():
            for line in p.open():
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                done[arm].add((row["task_id"], row["seed"]))
    if any(done.values()):
        print(f"Resuming: {len(done['reflexion'])} reflexion rows, "
              f"{len(done['intro_specter'])} intro_specter rows already present, will be skipped.")

    files = {arm: p.open("a") for arm, p in paths.items()}

    examples = _load_examples(args.dataset, n_examples)
    print(f"Loaded {len(examples)} examples for {args.dataset} (bench_seed="
          f"{DATASET_REGISTRY[args.dataset]['bench_seed']}), rho={args.rho}, seeds={seeds}")

    total_tokens_in = 0
    total_tokens_out = 0
    n_rows = 0
    n_errors = 0

    for example in examples:
        cmeta = _constraint_meta(example)
        for seed in seeds:
            arm_runners = {
                "reflexion": _run_reflexion_arm,
                "intro_specter": _run_intro_specter_arm,
            }
            pending_arms = [a for a in arm_runners if (example.task_id, seed) not in done[a]]
            if not pending_arms:
                continue

            cseed = _corruption_seed(example.task_id, seed, args.rho)
            corrupted_profile, corrupted_ids = corrupt_profile(example.profile, args.rho, cseed, cmeta)
            corrupted_example = replace(example, profile=corrupted_profile)

            try:
                primed, prime_in, prime_out = _with_retry(
                    lambda: _prime_trajectory(
                        corrupted_example, provider_name=provider_name, model=model_id,
                        seed=seed, cache=cache,
                    ),
                    label=f"prime task={example.task_id} seed={seed}",
                )
            except Exception as e:  # pragma: no cover
                print(f"[ERROR] prime failed task={example.task_id} seed={seed}: {e}", file=sys.stderr)
                n_errors += 1
                continue

            for arm in pending_arms:
                runner_fn = arm_runners[arm]
                try:
                    arm_out = _with_retry(
                        lambda: runner_fn(
                            corrupted_example, primed,
                            provider_name=provider_name, model=model_id, seed=seed, cache=cache,
                        ),
                        label=f"{arm} task={example.task_id} seed={seed}",
                    )
                except Exception as e:  # pragma: no cover
                    print(f"[ERROR] {arm} failed task={example.task_id} seed={seed}: {e}", file=sys.stderr)
                    n_errors += 1
                    continue

                true_success = _true_success(example, arm_out["final_trajectory"])
                tokens_input = arm_out["tokens_input"] + prime_in
                tokens_output = arm_out["tokens_output"] + prime_out
                row = {
                    "task_id": example.task_id,
                    "seed": seed,
                    "rho": args.rho,
                    "arm": arm,
                    "true_success": true_success,
                    "method_believed_success": bool(arm_out["method_believed_success"]),
                    "tokens_input": tokens_input,
                    "tokens_output": tokens_output,
                    "corrupted_constraint_ids": corrupted_ids,
                    "abstained": arm_out["abstained"],
                    "meta_summary": arm_out["meta_summary"],
                }
                files[arm].write(json.dumps(row, default=str) + "\n")
                files[arm].flush()
                total_tokens_in += tokens_input
                total_tokens_out += tokens_output
                n_rows += 1
                print(f"  {example.task_id} seed={seed} arm={arm}: "
                      f"true_success={true_success} believed={arm_out['method_believed_success']} "
                      f"abstained={arm_out['abstained']} tokens=({tokens_input},{tokens_output})")

    for f in files.values():
        f.close()

    print("\n--- run summary ---")
    print(f"rows written: {n_rows}  errors: {n_errors}")
    print(f"total tokens_input={total_tokens_in}  total tokens_output={total_tokens_out}  "
          f"grand_total={total_tokens_in + total_tokens_out}")
    if args.smoke:
        print(
            "Smoke mode: stopping here as instructed. Cost estimate needs the actual "
            "OpenRouter/Together rate card for this model — scripts/run_real_benchmarks.sh's "
            "header notes Mistral Nemo at $0.15/M tokens (blended in/out rate, not "
            "necessarily current); at that rate this smoke test would cost roughly "
            f"${(total_tokens_in + total_tokens_out) / 1_000_000 * 0.15:.4f} "
            "(rough order-of-magnitude only, confirm against the live rate card before "
            "trusting this number)."
        )


if __name__ == "__main__":
    main()
