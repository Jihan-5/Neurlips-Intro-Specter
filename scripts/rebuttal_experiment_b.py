#!/usr/bin/env python3
"""Experiment B: iterative-VRP at matched retry budget (rebuttal campaign).

Compares IterVRP (flat-text violation feedback, FULL trajectory regeneration,
looped up to Intro-Specter's own 1-initial + T_spr=2-retry = 3-round budget)
against Intro-Specter (selective, attributed subgraph repair) at the SAME
round budget, on the TRUE, uninjected-corruption profile throughout. Unlike
Experiment A, there is no profile corruption here and therefore no
true-vs-believed success split: "success" is simply whether the method's own
final trajectory passes a fresh verifier check against the example's true
profile + rules.

This file is additive-only (does not modify any existing intro_specter/,
configs/real/, outputs/real/, paper_final.tex, or paper_sections/ file). It
follows the same structural pattern as scripts/rebuttal_experiment_a.py
(benchmark-loader usage, provider/cache construction, retry-with-backoff,
resume/dedup-on-rerun, JSONL output) for consistency across the rebuttal
campaign.

Usage (smoke test -- 2 examples, 1 seed, both arms; real but tiny API spend):

    python3 scripts/rebuttal_experiment_b.py \\
        --dataset truthfulqa_real --model mistral-nemo-12b --smoke
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable, TypeVar

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_T = TypeVar("_T")


def _with_retry(fn: Callable[[], _T], *, attempts: int = 3, base_delay: float = 2.0, label: str = "") -> _T:
    """Transient upstream errors (e.g. OpenRouter 'no choices') are retried with backoff;
    the last attempt's exception propagates so the caller's existing error handling/logging
    still fires if all retries are exhausted. Copied verbatim from
    scripts/rebuttal_experiment_a.py -- Experiment A's first run hit flaky OpenRouter
    errors and this pattern was added afterward; Experiment B needs the same protection."""
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
from intro_specter.baselines.iter_vrp import run_iter_vrp
from intro_specter.benchmarks.base import BenchmarkExample
from intro_specter.benchmarks.truthfulqa_real import TruthfulQAReal
from intro_specter.benchmarks.twowiki_real import TwoWikiReal
from intro_specter.benchmarks.longmemeval_real import LongMemEvalReal
from intro_specter.models import SQLiteCache, build_provider
from intro_specter.pipeline import IntroSpecterConfig, run_intro_specter
from intro_specter.prompts import DIRECT_AGENT_SYSTEM, direct_agent_user
from intro_specter.runner import _meta_summary, _self_report_evaluator
from intro_specter.schemas import Trajectory, TrajectoryStep, coerce_final_output, coerce_trajectory_steps
from intro_specter.verifier import HybridVerifier

# (slug, provider_name, model_id) -- copied verbatim from
# scripts/generate_real_configs.py MODELS table / scripts/rebuttal_experiment_a.py
# so CLI --model matches the real-benchmark naming convention.
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
# `bench_seed` matches Experiment A's choice (the first of the real config's
# seeds [42, 123, 456]) so the example/task_id selection matches the existing
# outputs/real/ runs 1:1. The CLI `--seeds` axis below is the method's own
# generation-trial seed (0/1/2), independent of the fixed example set.
DATASET_REGISTRY: dict[str, dict[str, Any]] = {
    "truthfulqa_real": {
        "cls": TruthfulQAReal,
        "bench_seed": 42,
        "split": "test",
        "n_examples": 60,
    },
    # Added for Table~\ref{tab:vrp}'s remaining two cells (2Wiki x Mist, LongMem x
    # Llama8B) -- same bench_seed/n_examples convention as truthfulqa_real above,
    # `split="all"` since these two cells use the full n_examples pool (matching
    # how paper_final.tex's original VRP ablation and the twowiki/longmemeval
    # single-fault outputs/real/ runs were constructed).
    "twowiki_real": {
        "cls": TwoWikiReal,
        "bench_seed": 42,
        "split": "all",
        "n_examples": 60,
    },
    "longmemeval_real": {
        "cls": LongMemEvalReal,
        "bench_seed": 42,
        "split": "all",
        "n_examples": 60,
    },
}


def _load_examples(dataset: str, n_examples: int) -> list[BenchmarkExample]:
    reg = DATASET_REGISTRY[dataset]
    bench = reg["cls"](n_examples=n_examples, seed=reg["bench_seed"], split=reg["split"])
    return list(bench)


def _prime_trajectory(
    example: BenchmarkExample, *, provider_name: str, model: str, seed: int, cache: SQLiteCache | None
) -> tuple[Trajectory, int, int]:
    """Runs the direct-agent prompt once against `example.profile` (the TRUE,
    uninjected-corruption profile -- Experiment B does not corrupt). Mirrors
    runner.py::_prime_initial_trajectory and Experiment A's `_prime_trajectory`."""
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


def _success(example: BenchmarkExample, final_trajectory: Trajectory) -> bool:
    """Fresh verifier check of the method's actual final output against the
    example's TRUE profile + rules. No corruption in Experiment B, so this is
    the only success signal needed (no true-vs-believed split)."""
    fresh_verifier = HybridVerifier(rules=list(example.rules))
    check, _ = fresh_verifier.check(
        profile=example.profile,
        task=example.task,
        trajectory=final_trajectory,
        final_output=final_trajectory.final_output,
    )
    return check.passed


def _run_iter_vrp_arm(
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
    result = run_iter_vrp(
        profile=example.profile,
        task=example.task,
        trajectory=primed,
        verifier=verifier,
        provider=provider,
        model=model,
        temperature=0.0,  # matches MethodConfig default temperature used by the real runs
        seed=seed,
        # max_trials left at run_iter_vrp's MAX_TRIALS_DEFAULT=2 (1 initial + 2 retries
        # = 3 rounds total, matching Intro-Specter's spr_max_rounds=2 default budget).
    )
    return {
        "final_trajectory": result.final_trajectory,
        "success": result.verifier.passed,
        "tokens_input": result.tokens_input,
        "tokens_output": result.tokens_output,
        "rounds_used": int(result.meta.get("rounds_used", 1)),
        "meta_summary": _meta_summary(result.meta),
    }


def _rounds_used_intro_specter(meta: dict[str, Any]) -> int:
    """Approximates Intro-Specter's "rounds used" from its stage log, for a
    round-for-round comparison against IterVRP's rounds_used.

    Intro-Specter's own round budget (see IntroSpecterConfig in
    intro_specter/pipeline.py) is: 1 initial verify+decide round, then up to
    `spr_max_rounds` (default 2) additional SPR rounds -- the same 3-round
    ceiling IterVRP is budget-matched to. Concretely:
      - if the initial trajectory is accepted outright, no "decision" stage is
        ever appended (pipeline.py returns before Layer 2b) -- 1 round.
      - otherwise one "decision" stage is appended (the initial targeted-repair
        round), plus one "spr_round_{n}_decision" stage per SPR round actually
        attempted (appended every iteration of the SPR loop, whether or not
        that round's repair stuck) -- 1 + (# decision stages) rounds.
    This is a design decision (not returned directly by run_intro_specter) --
    flagged here since the task brief did not specify how to derive it.
    """
    stages = meta.get("stages", []) if meta else []
    n = sum(1 for s in stages if s.get("stage") == "decision")
    n += sum(
        1 for s in stages
        if isinstance(s.get("stage"), str)
        and s["stage"].startswith("spr_round_")
        and s["stage"].endswith("_decision")
    )
    return max(n, 1)


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
        # NOTE (design decision, flagged): unlike Experiment A (which set
        # tau_abstain=0.25 specifically to study abstention under profile noise),
        # Experiment B leaves tau_abstain and n_counterfactual_trials at the
        # real-config production defaults (Table 11: tau_abstain=0.0,
        # spr_max_rounds=2) since this experiment is about retry-budget vs.
        # selective-repair, not abstention behavior. n_counterfactual_trials=1
        # is kept matching Experiment A / the real configs' `extra` override for
        # cost parity across the rebuttal campaign's arms.
        tau_abstain=0.0,
        cost_lambda=0.0,
        n_counterfactual_trials=1,
        # spr_max_rounds left at the IntroSpecterConfig default (2), which is
        # exactly the budget IterVRP is matched to.
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
        "success": is_result.verifier.passed,
        "tokens_input": int(is_result.meta.get("tokens_input", 0)),
        "tokens_output": int(is_result.meta.get("tokens_output", 0)),
        "rounds_used": _rounds_used_intro_specter(is_result.meta),
        "meta_summary": _meta_summary(is_result.meta),
    }


ARM_RUNNERS: dict[str, Callable[..., dict[str, Any]]] = {
    "iter_vrp": _run_iter_vrp_arm,
    "intro_specter": _run_intro_specter_arm,
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", default="truthfulqa_real", choices=list(DATASET_REGISTRY))
    ap.add_argument("--model", required=True, choices=list(MODEL_TABLE))
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--n-examples", type=int, default=None)
    ap.add_argument("--cache-path", default="cache/completions.sqlite")
    ap.add_argument("--output-dir", default="outputs/rebuttal/experiment_b")
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
    paths = {arm: out_dir / f"{arm}.jsonl" for arm in ARM_RUNNERS}

    done: dict[str, set[tuple[str, int]]] = {arm: set() for arm in ARM_RUNNERS}
    for arm, p in paths.items():
        if p.exists():
            for line in p.open():
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                done[arm].add((row["task_id"], row["seed"]))
    if any(done.values()):
        print("Resuming: " + ", ".join(f"{len(v)} {k} rows" for k, v in done.items())
              + " already present, will be skipped.")

    files = {arm: p.open("a") for arm, p in paths.items()}

    examples = _load_examples(args.dataset, n_examples)
    print(f"Loaded {len(examples)} examples for {args.dataset} (bench_seed="
          f"{DATASET_REGISTRY[args.dataset]['bench_seed']}), seeds={seeds}, "
          f"profile=TRUE (no corruption)")

    total_tokens_in = 0
    total_tokens_out = 0
    n_rows = 0
    n_errors = 0

    for example in examples:
        for seed in seeds:
            pending_arms = [a for a in ARM_RUNNERS if (example.task_id, seed) not in done[a]]
            if not pending_arms:
                continue

            try:
                primed, prime_in, prime_out = _with_retry(
                    lambda: _prime_trajectory(
                        example, provider_name=provider_name, model=model_id,
                        seed=seed, cache=cache,
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
                            example, primed,
                            provider_name=provider_name, model=model_id, seed=seed, cache=cache,
                        ),
                        label=f"{arm} task={example.task_id} seed={seed}",
                    )
                except Exception as e:  # pragma: no cover
                    print(f"[ERROR] {arm} failed task={example.task_id} seed={seed}: {e}", file=sys.stderr)
                    n_errors += 1
                    continue

                success = _success(example, arm_out["final_trajectory"])
                tokens_input = arm_out["tokens_input"] + prime_in
                tokens_output = arm_out["tokens_output"] + prime_out
                row = {
                    "task_id": example.task_id,
                    "seed": seed,
                    "arm": arm,
                    "success": success,
                    "tokens_input": tokens_input,
                    "tokens_output": tokens_output,
                    "rounds_used": arm_out["rounds_used"],
                    "meta_summary": arm_out["meta_summary"],
                }
                files[arm].write(json.dumps(row, default=str) + "\n")
                files[arm].flush()
                total_tokens_in += tokens_input
                total_tokens_out += tokens_output
                n_rows += 1
                print(f"  {example.task_id} seed={seed} arm={arm}: "
                      f"success={success} rounds_used={arm_out['rounds_used']} "
                      f"tokens=({tokens_input},{tokens_output})")

    for f in files.values():
        f.close()

    print("\n--- run summary ---")
    print(f"rows written: {n_rows}  errors: {n_errors}")
    print(f"total tokens_input={total_tokens_in}  total tokens_output={total_tokens_out}  "
          f"grand_total={total_tokens_in + total_tokens_out}")
    if args.smoke:
        print(
            "Smoke mode: stopping here as instructed. Cost estimate needs the actual "
            "OpenRouter/Together rate card for this model -- scripts/run_real_benchmarks.sh's "
            "header notes Mistral Nemo at $0.15/M tokens (blended in/out rate, not "
            "necessarily current); at that rate this smoke test would cost roughly "
            f"${(total_tokens_in + total_tokens_out) / 1_000_000 * 0.15:.4f} "
            "(rough order-of-magnitude only, confirm against the live rate card before "
            "trusting this number)."
        )


if __name__ == "__main__":
    main()
