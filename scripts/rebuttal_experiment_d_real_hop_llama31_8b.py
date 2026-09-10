#!/usr/bin/env python3
"""Experiment D (real, hop-fault variant), Llama-3.1-8B extension of
`rebuttal_experiment_d_real_hop.py`.

Why this file exists (additive-only, never edits the original)
----------------------------------------------------------------
`scripts/rebuttal_experiment_d_real_hop.py` is tracked and UNMODIFIED. This
is a fresh sibling for the Llama-3.1-8B leg of the parallel model campaign
(served via OpenRouter, not Together -- Together is reserved for the
sibling Llama-3.3-70B leg). It duplicates the original's N=5/N=6
hop-fault-injection machinery verbatim (2WikiMultiHopQA bridge_comparison
rows, `build_hop_multi_fault`) and extends the arm set from
{reflexion, intro_specter} to the full 7-baseline set requested for this
campaign leg: direct, self_refine, full_regen, react, selfcheckgpt,
reflexion, intro_specter. `tot` and `intro_specter_fixed` are intentionally
excluded (cost-justified / future-work-only). This script's scope only
needs N=5 (per the campaign brief's N in {2,3,4,5}), but N=6 is left
available via `--num-faults 6` since the underlying machinery supports it
at no extra cost to write.

Usage:
    python3 scripts/rebuttal_experiment_d_real_hop_llama31_8b.py --smoke --num-faults 5
    python3 scripts/rebuttal_experiment_d_real_hop_llama31_8b.py --num-faults 5 --seeds 0,1,2 --n-examples 40
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


import pandas as pd

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
from intro_specter.benchmarks.twowiki_real import _flatten_context, _make_rule, _parse_context, _profile_to_userprofile
from intro_specter.models import SQLiteCache, build_provider
from intro_specter.pipeline import IntroSpecterConfig, run_intro_specter
from intro_specter.profiles import inject_profile
from intro_specter.profiles.double_fault_injection import ProfileFaultTarget
from intro_specter.profiles.hop_fault_injection import HopFaultRecord, build_hop_multi_fault
from intro_specter.prompts import DIRECT_AGENT_SYSTEM, direct_agent_user
from intro_specter.runner import _meta_summary, _self_report_evaluator
from intro_specter.schemas import (
    AssumptionDAG,
    GoldLabels,
    Trajectory,
    TrajectoryStep,
    coerce_final_output,
    coerce_trajectory_steps,
)
from intro_specter.verifier import HybridVerifier

MODEL_TABLE = {
    "llama-3.1-8b": ("openrouter", "meta-llama/llama-3.1-8b-instruct"),
}

BENCH_SEED = 42
N_HOP_FAULTS = 4


# ---------------------------------------------------------------------------
# Mechanically-checkable profile-fault type registry (unmodified copy)
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


def _resolved_english(final_output: str | None, true_text: str) -> bool:
    text = (final_output or "").lower()
    return not any(b.lower() in text for b in _TRUE_BANNED_SUBSTRINGS)


_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+")


def _resolved_concise(final_output: str | None, true_text: str) -> bool:
    text = (final_output or "").strip()
    if "single sentence" in true_text.lower():
        n_sentences = len([s for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()])
        return n_sentences <= 1
    return len(text.split()) <= 20


_BULLET_RE = re.compile(r"(^|\n)\s*([-*•]|\d+[.)])\s")


def _resolved_bullets(final_output: str | None, true_text: str) -> bool:
    return _BULLET_RE.search(final_output or "") is None


def _resolved_preamble(final_output: str | None, true_text: str) -> bool:
    text = (final_output or "").strip().lower()
    return not any(text.startswith(p) for p in _PREAMBLE_PHRASES)


PROFILE_FAULT_TYPES: dict[str, tuple[Callable[[dict[str, Any]], bool], Callable[[str | None, str], bool]]] = {
    "english": (_is_english_constraint, _resolved_english),
    "concise": (_is_concise_constraint, _resolved_concise),
    "bullets": (_is_bullets_constraint, _resolved_bullets),
    "preamble": (_is_preamble_constraint, _resolved_preamble),
}

_N_PROFILE_FAULTS_BY_N = {5: 1, 6: 2}
MIN_SUPPORTED_NUM_FAULTS = 5
MAX_SUPPORTED_NUM_FAULTS = 6


# ---------------------------------------------------------------------------
# 2WikiMultiHopQA bridge_comparison row loading (unmodified copy)
# ---------------------------------------------------------------------------

_HF_ROWS: list[dict] | None = None


def _load_bridge_comparison_rows() -> list[dict]:
    global _HF_ROWS
    if _HF_ROWS is not None:
        return _HF_ROWS
    from huggingface_hub import hf_hub_download
    path = hf_hub_download(repo_id="xanhho/2WikiMultihopQA", filename="dev.parquet", repo_type="dataset")
    df = pd.read_parquet(path)
    sub = df[df["type"] == "bridge_comparison"].reset_index(drop=True)

    def _ev_len(e: Any) -> int:
        return len(json.loads(e)) if isinstance(e, str) else len(e)

    sub = sub[sub["evidences"].apply(_ev_len) == 4].reset_index(drop=True)
    _HF_ROWS = sub.to_dict(orient="records")
    return _HF_ROWS


def _build_prompt(profile_dict: dict[str, Any], context_text: str, question: str) -> str:
    return (
        "User profile (read this and respect any hard constraint):\n"
        + "\n".join(f"- {c['text']}" for c in profile_dict["constraints"])
        + "\n\nUse the following paragraphs to answer the multi-hop question. "
        "Answer in one sentence with the named entity or yes/no.\n\n"
        f"Paragraphs:\n{context_text}\n\n"
        f"Question: {question}"
    )


def _build_hop_examples(
    n_examples: int, seed: int, num_faults: int, scan_limit: int,
) -> list[tuple[BenchmarkExample, HopFaultRecord, list[str]]]:
    if num_faults not in _N_PROFILE_FAULTS_BY_N:
        raise ValueError(f"num_faults={num_faults} not supported by this script (only 5, 6)")
    n_profile_faults = _N_PROFILE_FAULTS_BY_N[num_faults]

    rows = _load_bridge_comparison_rows()
    out: list[tuple[BenchmarkExample, HopFaultRecord, list[str]]] = []
    for idx, row in enumerate(rows[:scan_limit]):
        if len(out) >= n_examples:
            break
        task_id = f"real_2wiki_hop_{idx:05d}_{row['_id']}"
        profile_dict = inject_profile(task_id=task_id, seed=seed, dataset="hotpotqa")

        present_types = sorted(
            name for name, (pred, _) in PROFILE_FAULT_TYPES.items()
            if any(pred(c) for c in profile_dict["constraints"])
        )
        if len(present_types) < n_profile_faults:
            continue
        chosen_types = present_types[:n_profile_faults]

        evidences = [tuple(e) for e in json.loads(row["evidences"])]
        question = row["question"]
        answer = row["answer"]
        parsed_ctx = _parse_context(row["context"])
        context_text = _flatten_context(parsed_ctx, max_chars=3500)

        banned: list[str] = []
        for c in profile_dict["constraints"]:
            if "english only" in c["text"].lower():
                banned += _TRUE_BANNED_SUBSTRINGS

        targets = [ProfileFaultTarget(name=n, predicate=PROFILE_FAULT_TYPES[n][0]) for n in chosen_types]
        try:
            hfr = build_hop_multi_fault(
                task_id=task_id, seed=seed, profile_dict=profile_dict, context_text=context_text,
                evidences=evidences, answer=answer, profile_targets=targets,
            )
        except RuntimeError as e:
            print(f"[SKIP] {task_id}: {e}", file=sys.stderr)
            continue

        corrupted_profile = _profile_to_userprofile(hfr.corrupted_profile_dict)
        for c in hfr.corrupted_profile_dict["constraints"]:
            if "english only" in c["text"].lower():
                banned += _TRUE_BANNED_SUBSTRINGS
        prompt = _build_prompt(hfr.corrupted_profile_dict, hfr.corrupted_context_text, question)

        cmeta = {
            "answer": answer,
            "twowiki_id": row["_id"],
            "twowiki_type": "bridge_comparison",
            "banned_substrings": banned,
            "profile_constraints": hfr.corrupted_profile_dict["constraints"],
            "gold_fault_node": None,
            "fault_record": None,
        }
        rule = _make_rule(cmeta)
        task = {
            "task_id": task_id,
            "task_type": "real_2wiki",
            "condition": "factual_2hop_real_hopfault",
            "prompt": prompt,
            "split": "test",
            "condition_meta": cmeta,
        }
        gold = GoldLabels(success=None, correct_final_output=answer, fault_node_id=None)
        example = BenchmarkExample(
            task_id=task_id,
            dataset="twowiki_real_bridge_hop",
            profile=corrupted_profile,
            task=task,
            trajectory=Trajectory(task_id=task_id, steps=[], final_output=None),
            dag=AssumptionDAG(task_id=task_id, nodes=[], edges=[]),
            gold=gold,
            rules=[rule],
            split="test",
        )
        out.append((example, hfr, chosen_types))
    return out


# ---------------------------------------------------------------------------
# Priming + arms
# ---------------------------------------------------------------------------


def _prime_trajectory(
    example: BenchmarkExample, *, provider_name: str, model: str, seed: int, cache: SQLiteCache | None,
) -> tuple[Trajectory, int, int]:
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


def _trajectory_full_text(trajectory: Trajectory) -> str:
    parts = [trajectory.final_output or ""]
    for step in trajectory.steps:
        parts.append(getattr(step, "text", "") or "")
        parts.append(getattr(step, "reason_summary", "") or "")
    return "\n".join(parts)


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
            model=model,
            temperature=0.7,
            seed=attempt_seed,
            max_tokens=8192,
        )
        steps = coerce_trajectory_steps(payload.get("steps", []))
        final = coerce_final_output(payload.get("final_output"), fallback="") or ""
        if not steps:
            steps = [TrajectoryStep(step_id=1, kind="output", text=final)]  # type: ignore[arg-type]
        traj = Trajectory(task_id=task.get("task_id", ""), steps=steps, final_output=final)
        return traj, completion.tokens_input, completion.tokens_output

    return regenerate


def _run_direct_arm(
    example: BenchmarkExample, primed: Trajectory, *, provider_name: str, model: str, seed: int,
    cache: SQLiteCache | None,
) -> dict[str, Any]:
    verifier = HybridVerifier(rules=list(example.rules))
    result = run_direct(profile=example.profile, task=example.task, trajectory=primed, verifier=verifier)
    return {
        "final_trajectory": result.final_trajectory,
        "method_believed_success": result.verifier.passed,
        "tokens_input": result.tokens_input,
        "tokens_output": result.tokens_output,
        "meta_summary": _meta_summary(result.meta),
    }


def _run_self_refine_arm(
    example: BenchmarkExample, primed: Trajectory, *, provider_name: str, model: str, seed: int,
    cache: SQLiteCache | None,
) -> dict[str, Any]:
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


def _run_full_regen_arm(
    example: BenchmarkExample, primed: Trajectory, *, provider_name: str, model: str, seed: int,
    cache: SQLiteCache | None,
) -> dict[str, Any]:
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


def _run_react_arm(
    example: BenchmarkExample, primed: Trajectory, *, provider_name: str, model: str, seed: int,
    cache: SQLiteCache | None,
) -> dict[str, Any]:
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


def _run_selfcheckgpt_arm(
    example: BenchmarkExample, primed: Trajectory, *, provider_name: str, model: str, seed: int,
    cache: SQLiteCache | None,
) -> dict[str, Any]:
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


def _run_reflexion_arm(
    example: BenchmarkExample, primed: Trajectory, *, provider_name: str, model: str, seed: int,
    cache: SQLiteCache | None,
) -> dict[str, Any]:
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


def _run_intro_specter_arm(
    example: BenchmarkExample, primed: Trajectory, *, provider_name: str, model: str, seed: int,
    cache: SQLiteCache | None,
) -> dict[str, Any]:
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
    return {
        "final_trajectory": is_result.final_trajectory,
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="llama-3.1-8b", choices=list(MODEL_TABLE))
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--n-examples", type=int, default=40)
    ap.add_argument("--num-faults", type=int, required=True, choices=[5, 6])
    ap.add_argument("--scan-limit", type=int, default=2671)
    ap.add_argument("--cache-path", default="cache/completions.sqlite")
    ap.add_argument("--output-dir", default="outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b")
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

    provider_name, model_id = MODEL_TABLE[args.model]
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

    print(f"Building {n_examples} {args.num_faults}-fault (4 hop-context + "
          f"{_N_PROFILE_FAULTS_BY_N[args.num_faults]} profile) twowiki_real bridge_comparison "
          f"examples (bench_seed={BENCH_SEED}, scan_limit={args.scan_limit})...")
    examples = _build_hop_examples(n_examples, BENCH_SEED, args.num_faults, args.scan_limit)
    print(f"Built {len(examples)} examples. seeds={seeds}, model={args.model}, arms={arms}")
    if len(examples) < n_examples:
        print(f"[WARN] only found {len(examples)}/{n_examples} qualifying examples within the scan pool.")

    f_outs = {a: p.open("a") for a, p in out_paths.items()}
    total_tokens_in = 0
    total_tokens_out = 0
    n_rows = 0
    n_errors = 0

    for example, hfr, chosen_types in examples:
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
                for i, (subject, relation, true_obj, decoy_obj) in hfr.facts.items():
                    per_fault[f"hop{i}"] = true_obj.lower() in full_text.lower()
                for name in chosen_types:
                    _, checker = PROFILE_FAULT_TYPES[name]
                    true_text = hfr.true_constraint_texts[name]
                    per_fault[name] = checker(final_traj.final_output, true_text)

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
                    "fault_types": [f"hop{i}" for i in range(N_HOP_FAULTS)] + chosen_types,
                    "per_fault_resolved": per_fault,
                    "all_resolved": all_resolved,
                    "n_resolved": n_resolved,
                    "method_believed_success": bool(arm_out["method_believed_success"]),
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
    if args.smoke:
        print(
            "Smoke mode: stopping here. Rough cost estimate at OpenRouter Llama-3.1-8B-instruct's "
            "blended token rate (~$0.055/M in + $0.055/M out; not necessarily current): "
            f"${(total_tokens_in + total_tokens_out) / 1_000_000 * 0.055:.4f}"
        )


if __name__ == "__main__":
    main()
