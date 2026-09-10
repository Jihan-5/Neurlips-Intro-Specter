#!/usr/bin/env python3
"""PersonalWAB rebuttal experiment: single-turn personalized recommendation.

Runs 5 arms on the PersonalWAB (WWW'25) single-turn recommendation track
(`intro_specter/benchmarks/personalwab_real.py` -- real 1,000-user Amazon
behavioral profiles; ground truth = the item the user genuinely interacted
with; mechanical ASIN-containment hit@1 scoring replicating PersonalWAB's own
containment criterion):

  * direct             -- the primed direct-agent trajectory, verified as-is
  * reflexion          -- run_reflexion (default max_trials=2)
  * violation_reprompt -- run_violation_reprompt with max_trials=1 (VRP)
  * iter_vrp           -- run_iter_vrp (budget-matched, max_trials=2)
  * intro_specter      -- full Intro-Specter pipeline (spr_max_rounds=2)

This file is additive-only (does not modify any existing intro_specter/,
configs/real/, outputs/real/, paper_final.tex, or paper_sections/ file). It
copies the structural pattern of scripts/rebuttal_experiment_b.py: MODEL_TABLE,
_with_retry backoff, resume/dedup on (task_id, seed, arm), per-row JSONL with
task_id/seed/arm/success/tokens_input/tokens_output/rounds_used.

Output layout (per campaign brief; differs from experiment_b's
{dataset}__{model} nesting):
    outputs/rebuttal/experiment_personalwab/{model}/{arm}.jsonl

Usage (smoke test -- 2 examples, 1 seed, all 5 arms, tiny API spend):

    source .env.local
    python3 scripts/rebuttal_experiment_personalwab.py --model mistral-nemo-12b --smoke
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
    scripts/rebuttal_experiment_b.py (itself from experiment_a, added after flaky
    OpenRouter errors on the first campaign runs)."""
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
from intro_specter.baselines.reflexion import run_reflexion
from intro_specter.baselines.violation_reprompt import run_violation_reprompt
from intro_specter.benchmarks.base import BenchmarkExample
from intro_specter.benchmarks.personalwab_real import PersonalWABReal
from intro_specter.models import SQLiteCache, build_provider
from intro_specter.pipeline import IntroSpecterConfig, run_intro_specter
from intro_specter.prompts import DIRECT_AGENT_SYSTEM, direct_agent_user
from intro_specter.runner import _meta_summary, _self_report_evaluator
from intro_specter.schemas import Trajectory, TrajectoryStep, coerce_final_output, coerce_trajectory_steps
from intro_specter.verifier import HybridVerifier

# (slug, provider_name, model_id) -- copied verbatim from
# scripts/rebuttal_experiment_b.py so CLI --model matches the campaign naming.
MODEL_TABLE = {
    "llama-3.3-70b":    ("together",   "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
    "llama-3.1-8b":     ("openrouter", "meta-llama/llama-3.1-8b-instruct"),
    "deepseek-v3":      ("together",   "deepseek-ai/DeepSeek-V3"),
    "deepseek-v3.1":    ("together",   "deepseek-ai/DeepSeek-V3.1"),
    "mistral-nemo-12b": ("openrouter", "mistralai/mistral-nemo"),
    "qwen-2.5-7b":      ("openrouter", "qwen/qwen-2.5-7b-instruct"),
    "gemini-2.5-flash": ("openrouter", "google/gemini-2.5-flash"),
    "gpt-oss-20b":      ("together",   "openai/gpt-oss-20b"),
    # Fallback cell added 2026-07-26 when the OpenRouter key hit its $50 total
    # limit mid-campaign (verified: limit_remaining=0, no reset; see
    # orchestration/live_updates.md). Same open-weights model as qwen-2.5-7b
    # but served by Together's serverless FP8 "Turbo" endpoint -- kept as its
    # OWN cell (own output dir) so no JSONL mixes serving providers. Of the
    # three assigned models this is the only one with a serverless Together
    # equivalent (live-tested; Llama-3.1-8B / Mistral-Nemo need dedicated
    # endpoints there).
    "qwen-2.5-7b-together": ("together", "Qwen/Qwen2.5-7B-Instruct-Turbo"),
}

BENCH_SEED = 42       # matches the campaign's bench_seed convention (experiment_b)
N_EXAMPLES_DEFAULT = 60


def _load_examples(n_examples: int) -> list[BenchmarkExample]:
    bench = PersonalWABReal(n_examples=n_examples, seed=BENCH_SEED, split="all")
    return list(bench)


def _prime_trajectory(
    example: BenchmarkExample, *, provider_name: str, model: str, seed: int, cache: SQLiteCache | None
) -> tuple[Trajectory, int, int]:
    """Runs the direct-agent prompt once against `example.profile` (the real
    PersonalWAB behavioral profile + pre-task purchase history). Mirrors
    rebuttal_experiment_b.py::_prime_trajectory."""
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
    """Fresh verifier check of the arm's actual final output against the
    example's rules (PersonalWAB ASIN-containment hit@1)."""
    fresh_verifier = HybridVerifier(rules=list(example.rules))
    check, _ = fresh_verifier.check(
        profile=example.profile,
        task=example.task,
        trajectory=final_trajectory,
        final_output=final_trajectory.final_output,
    )
    return check.passed


def _run_direct_arm(
    example: BenchmarkExample,
    primed: Trajectory,
    *,
    provider_name: str,
    model: str,
    seed: int,
    cache: SQLiteCache | None,
) -> dict[str, Any]:
    """The primed trajectory as-is: single round, no repair. Token counts are 0
    here because the runner adds the shared prime tokens to every arm's row
    (same accounting as experiment_b)."""
    return {
        "final_trajectory": primed,
        "tokens_input": 0,
        "tokens_output": 0,
        "rounds_used": 1,
        "meta_summary": {},
    }


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
        temperature=0.0,
        seed=seed,
        # max_trials left at run_reflexion's default (2).
    )
    return {
        "final_trajectory": result.final_trajectory,
        "tokens_input": result.tokens_input,
        "tokens_output": result.tokens_output,
        # meta["trials"] counts verify/reflect rounds; the initial trajectory
        # is round 1, and each reflection+retry adds one round.
        "rounds_used": int(result.meta.get("trials", 1)),
        "meta_summary": _meta_summary(result.meta),
    }


def _run_vrp_arm(
    example: BenchmarkExample,
    primed: Trajectory,
    *,
    provider_name: str,
    model: str,
    seed: int,
    cache: SQLiteCache | None,
) -> dict[str, Any]:
    """VRP = violation_reprompt with max_trials=1 (single revision), per brief."""
    provider = build_provider(provider_name, cache=cache)
    verifier = HybridVerifier(rules=list(example.rules))
    result = run_violation_reprompt(
        profile=example.profile,
        task=example.task,
        trajectory=primed,
        verifier=verifier,
        provider=provider,
        model=model,
        max_trials=1,
        temperature=0.0,
        seed=seed,
    )
    return {
        "final_trajectory": result.final_trajectory,
        "tokens_input": result.tokens_input,
        "tokens_output": result.tokens_output,
        "rounds_used": 1 + int(result.meta.get("trials", 0)),
        "meta_summary": _meta_summary(result.meta),
    }


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
        temperature=0.0,
        seed=seed,
        # max_trials left at MAX_TRIALS_DEFAULT=2 (1 initial + 2 retries =
        # 3 rounds, matching Intro-Specter's spr_max_rounds=2 budget).
    )
    return {
        "final_trajectory": result.final_trajectory,
        "tokens_input": result.tokens_input,
        "tokens_output": result.tokens_output,
        "rounds_used": int(result.meta.get("rounds_used", 1)),
        "meta_summary": _meta_summary(result.meta),
    }


def _rounds_used_intro_specter(meta: dict[str, Any]) -> int:
    """Copied verbatim from scripts/rebuttal_experiment_b.py (see its docstring
    for the design rationale): 1 round if accepted outright, else 1 + one round
    per decision stage (initial repair decision + each SPR round attempted)."""
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
        # Same production defaults as experiment_b (Table 11): tau_abstain=0.0,
        # cost_lambda=0.0, n_counterfactual_trials=1, spr_max_rounds default 2.
        tau_abstain=0.0,
        cost_lambda=0.0,
        n_counterfactual_trials=1,
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
        "tokens_input": int(is_result.meta.get("tokens_input", 0)),
        "tokens_output": int(is_result.meta.get("tokens_output", 0)),
        "rounds_used": _rounds_used_intro_specter(is_result.meta),
        "meta_summary": _meta_summary(is_result.meta),
    }


ARM_RUNNERS: dict[str, Callable[..., dict[str, Any]]] = {
    "direct": _run_direct_arm,
    "reflexion": _run_reflexion_arm,
    "violation_reprompt": _run_vrp_arm,
    "iter_vrp": _run_iter_vrp_arm,
    "intro_specter": _run_intro_specter_arm,
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True, choices=list(MODEL_TABLE))
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--n-examples", type=int, default=None)
    ap.add_argument("--arms", default=",".join(ARM_RUNNERS),
                    help="comma-separated subset of arms to run")
    ap.add_argument("--cache-path", default=None,
                    help="default: cache/completions_personalwab_{model}.sqlite "
                         "(per-model to avoid SQLite lock contention across the "
                         "3 parallel model processes)")
    ap.add_argument("--output-dir", default="outputs/rebuttal/experiment_personalwab")
    ap.add_argument("--smoke", action="store_true", help="n=2 examples, 1 seed, then stop")
    args = ap.parse_args()

    if args.smoke:
        n_examples = 2
        seeds = [0]
    else:
        n_examples = args.n_examples or N_EXAMPLES_DEFAULT
        seeds = [int(s) for s in args.seeds.split(",") if s != ""]

    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    unknown = [a for a in arms if a not in ARM_RUNNERS]
    if unknown:
        raise SystemExit(f"unknown arms: {unknown}; valid: {list(ARM_RUNNERS)}")

    provider_name, model_id = MODEL_TABLE[args.model]
    cache_path = args.cache_path or f"cache/completions_personalwab_{args.model}.sqlite"
    Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
    cache = SQLiteCache(cache_path)

    out_dir = Path(args.output_dir) / args.model
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {arm: out_dir / f"{arm}.jsonl" for arm in arms}

    done: dict[str, set[tuple[str, int]]] = {arm: set() for arm in arms}
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

    examples = _load_examples(n_examples)
    print(f"Loaded {len(examples)} PersonalWAB recommend examples "
          f"(bench_seed={BENCH_SEED}), model={args.model}, seeds={seeds}, arms={arms}")

    total_tokens_in = 0
    total_tokens_out = 0
    n_rows = 0
    n_errors = 0

    for example in examples:
        for seed in seeds:
            pending_arms = [a for a in arms if (example.task_id, seed) not in done[a]]
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


if __name__ == "__main__":
    main()
