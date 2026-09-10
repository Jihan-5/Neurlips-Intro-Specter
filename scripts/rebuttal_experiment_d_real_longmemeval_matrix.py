#!/usr/bin/env python3
"""Experiment D (real), FULL 7-ARM MATRIX, dataset=longmemeval_real, ALL 4 MODELS.

Why this file exists (additive-only, never edits any existing tracked file)
-----------------------------------------------------------------------------
Tonight's twowiki_real multi-fault campaign
(`scripts/rebuttal_experiment_d_real.py` + its per-model full-matrix
siblings `_fullmatrix_mistral.py` / `_qwen.py` / `_llama31_8b.py` /
`_llama70b_matrix.py`) built N=2/3/4 real multi-fault examples via
`intro_specter/profiles/double_fault_injection.py::build_multi_fault`
(1 context fault, forced `wrong_value`, + N-1 profile-constraint faults,
forced `wrong_constraint`, restricted to 4 mechanically-checkable constraint
templates: english / concise / bullets / preamble) and ran the same 7-arm
baseline matrix (direct, self_refine, reflexion, full_regen, react,
selfcheckgpt, intro_specter) at each N.

This script is the analogous build for `longmemeval_real`
(`intro_specter/benchmarks/longmemeval_real.py`, UNMODIFIED, read in full
before writing this file). It reuses `double_fault_injection.py` UNMODIFIED
(same function, same fault types, same disjointness guarantee) -- only the
prompt-assembly / context-extraction glue differs, because LongMemEval's
prompt template embeds a multi-session chat transcript ("Chat history:\n...")
plus a "Current date:" line instead of 2WikiMultiHopQA's "Paragraphs:\n...".

N=5 feasibility investigation (per explicit task instruction: same rigor as
the original twowiki N=5 investigation, honest report either way)
-------------------------------------------------------------------------
twowiki_real's N=5 (`hop_fault_injection.py`) works because
`xanhho/2WikiMultihopQA`'s `bridge_comparison` subtype exposes an `evidences`
field: FOUR independent, mechanically-checkable (subject, relation, object)
facts per example (two director facts + two DOB facts feeding one compositional
question), each of which can be independently corrupted and independently
checked against the produced text.

LongMemEval-Oracle (`xiaowu0162/longmemeval-cleaned/longmemeval_oracle.json`,
500 rows) was inspected directly (schema dump + spot checks across all 6
`question_type` values: temporal-reasoning, multi-session, knowledge-update,
single-session-user, single-session-assistant, single-session-preference).
Its schema is:
    question_id, question_type, question, answer, question_date,
    haystack_dates, haystack_session_ids, haystack_sessions, answer_session_ids
`answer` is ALWAYS a single scalar value (a string entity/phrase, a number, a
duration, or in the preference case a whole descriptive paragraph) -- never a
list/dict of independent per-session sub-facts. `answer_session_ids` names
WHICH sessions are evidence, but does not expose any independent
per-session ground-truth VALUE the way `evidences` does for twowiki's
bridge_comparison rows; e.g. a `multi-session` example's answer might be "3"
(a count aggregated across 3 sessions) with no per-session sub-count exposed,
and a `knowledge-update` example's answer is the single POST-update value
(the whole point of that question type is that only the latest of several
conflicting per-session values is correct -- corrupting an early, deliberately
superseded value would not even be a fault, since the agent is SUPPOSED to
discard it).

Conclusion: LongMemEval-Oracle has no analog of twowiki's
`evidences`-array structure. There is no way to construct >=2 independent,
mechanically-checkable CONTEXT-level faults for a single example the way
`hop_fault_injection.py` does for twowiki -- every example has exactly one
target answer, so at most 1 context fault is checkable, same ceiling as the
N=2/3/4 approach already uses (1 context fault + up to 3 profile-constraint
faults, capped at 4 by the same 4-available-mechanically-clean-profile-fault-
types limit `rebuttal_experiment_d_real.py` already documents for twowiki).
This script therefore supports N in {2, 3, 4} ONLY; no N=5 runner is built
for longmemeval_real, and none should be inferred from this file's absence
of one -- this is a genuine structural ceiling, not an oversight.

Models (all 4, one script, `--model` flag; arm-runner functions are already
parameterized by `provider_name`/`model_id` in the twowiki siblings, so unlike
those per-model files this single file avoids 4x duplication):
    mistral-nemo-12b  -> openrouter / mistralai/mistral-nemo
    qwen-2.5-7b       -> openrouter / qwen/qwen-2.5-7b-instruct
    llama-3.1-8b      -> openrouter / meta-llama/llama-3.1-8b-instruct
    llama-3.3-70b     -> together   / meta-llama/Llama-3.3-70B-Instruct-Turbo

7 arms per (model, N): direct, self_refine, reflexion, full_regen, react,
selfcheckgpt, intro_specter (`tot` and `intro_specter_fixed` excluded, same
as the twowiki campaign).

Output: outputs/rebuttal/experiment_d/full_matrix_longmemeval/{model}/n{N}__{arm}.jsonl

Usage:
    python3 scripts/rebuttal_experiment_d_real_longmemeval_matrix.py --smoke --model mistral-nemo-12b --num-faults 2
    python3 scripts/rebuttal_experiment_d_real_longmemeval_matrix.py --model llama-3.3-70b --num-faults 3 --seeds 0,1,2
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
    """Same retry-with-backoff pattern used by every sibling script tonight
    (`rebuttal_experiment_a/b/d_real*.py`) -- transient upstream errors
    (OpenRouter/Together rate limits, 'no choices', 5xx) are retried with
    exponential backoff rather than failing the whole run."""
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
from intro_specter.benchmarks.longmemeval_real import LongMemEvalReal, _make_rule, _profile_to_userprofile
from intro_specter.models import SQLiteCache, build_provider
from intro_specter.pipeline import IntroSpecterConfig, run_intro_specter
from intro_specter.profiles.double_fault_injection import (
    MultiFaultRecord,
    ProfileFaultTarget,
    build_multi_fault,
)
from intro_specter.prompts import DIRECT_AGENT_SYSTEM, direct_agent_user
from intro_specter.runner import _llm_regenerate_fn, _meta_summary, _self_report_evaluator
from intro_specter.schemas import (
    Trajectory,
    TrajectoryStep,
    coerce_final_output,
    coerce_trajectory_steps,
)
from intro_specter.verifier import HybridVerifier

MODEL_TABLE = {
    "mistral-nemo-12b": ("openrouter", "mistralai/mistral-nemo"),
    "qwen-2.5-7b": ("openrouter", "qwen/qwen-2.5-7b-instruct"),
    "llama-3.1-8b": ("openrouter", "meta-llama/llama-3.1-8b-instruct"),
    "llama-3.3-70b": ("together", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
}

BENCH_SEED = 42  # matches Experiment A/B/D's fixed "example seed" convention

# LongMemEvalReal's prompt template (see intro_specter/benchmarks/longmemeval_real.py
# `_build_example`, lines ~226-235, read verbatim before writing this regex):
#   "...\n\nChat history:\n{sessions_text}\n\nCurrent date: {date}\nQuestion: {question}"
_CTX_RE = re.compile(r"Chat history:\n(.*)\n\nCurrent date: (.*)\nQuestion:", re.DOTALL)


# ---------------------------------------------------------------------------
# Mechanically-checkable profile-fault type registry -- unmodified copy of
# `rebuttal_experiment_d_real.py`'s registry (that file is tracked and
# unmodified; this is a fresh copy in a new file, not an edit). Applies
# identically here because both benchmarks draw profiles from the SAME
# `inject_profile(dataset="hotpotqa")` template pool (longmemeval_real.py
# uses "hotpotqa" profile templates explicitly -- see its own module
# docstring / `_build_example`).
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

# Same empirically-measured scan pools `rebuttal_experiment_d_real.py` uses
# for twowiki_real (identical `inject_profile(dataset="hotpotqa")` template
# pool drives the co-occurrence statistics, so the same scan sizes apply).
# NOTE: LongMemEval-Oracle only has 500 underlying rows; `LongMemEvalReal`
# samples WITH REPLACEMENT via a seeded RNG keyed on idx (see its
# `_hf_index`), so scanning up to 40000 indices revisits the same 500
# underlying questions many times over -- each revisit gets an
# INDEPENDENTLY drawn profile (profile draw is keyed on the per-idx
# `task_id`, not the underlying row), so this is not circular for the
# purpose of finding profile-fault-type co-occurrence, but it does mean
# num_faults=4 example sets for longmemeval_real will repeat underlying
# question content across n_examples far more than twowiki_real's fresh
# 12576-row pool did. Reported honestly in the summary, not concealed.
_SCAN_LIMIT_BY_N = {2: 3000, 3: 6000, 4: 40000}
MAX_SUPPORTED_NUM_FAULTS = 4


# ---------------------------------------------------------------------------
# Build the N-fault-injected example set
# ---------------------------------------------------------------------------


def _extract_context_and_date(prompt: str) -> tuple[str, str]:
    m = _CTX_RE.search(prompt)
    if not m:
        raise RuntimeError("could not locate 'Chat history:' block in prompt -- template drift?")
    return m.group(1), m.group(2)


def _build_prompt(profile_dict: dict[str, Any], sessions_text: str, current_date: str, question: str) -> str:
    """Exact copy of the prompt-assembly template in
    `intro_specter/benchmarks/longmemeval_real.py::_build_example` -- reused
    so the corrupted example is byte-identical in structure to what the
    unmodified loader would have produced, differing only in the injected
    fault content."""
    return (
        "User profile (read this and respect any hard constraint):\n"
        + "\n".join(f"- {c['text']}" for c in profile_dict["constraints"])
        + "\n\nThe following are prior chat sessions between the user and "
        "an assistant. Use them to answer the question. Answer in one "
        "concise sentence with the specific entity, date, or fact.\n\n"
        f"Chat history:\n{sessions_text}\n\n"
        f"Current date: {current_date}\n"
        f"Question: {question}"
    )


def _build_multi_fault_examples(
    n_examples: int, seed: int, num_faults: int, scan_limit: int | None = None,
) -> list[tuple[BenchmarkExample, MultiFaultRecord, list[str]]]:
    """Loads `longmemeval_real` via the existing, unmodified `LongMemEvalReal`
    loader, then applies N-fault injection on top of each qualifying
    example's (already-real) profile/chat-history context. Returns
    (example, fault_record, profile_fault_names_used) triples, selection
    decided deterministically BEFORE any arm runs (same convention as the
    twowiki sibling)."""
    if num_faults < 2 or num_faults > MAX_SUPPORTED_NUM_FAULTS:
        raise ValueError(
            f"num_faults={num_faults} not supported -- see module docstring "
            f"(N=5 found INFEASIBLE for longmemeval_real: no evidences-array "
            f"analog exists in the LongMemEval-Oracle schema; every example "
            f"has exactly one scalar answer, so at most 1 context fault is "
            f"ever mechanically checkable)"
        )
    n_profile_faults = num_faults - 1
    scan_limit = scan_limit or _SCAN_LIMIT_BY_N[num_faults]
    bench = LongMemEvalReal(n_examples=scan_limit, seed=seed, split="all", fault_inject=False)
    out: list[tuple[BenchmarkExample, MultiFaultRecord, list[str]]] = []
    for example in bench:
        if len(out) >= n_examples:
            break
        cmeta = example.task["condition_meta"]
        answer = cmeta["answer"]
        constraints = cmeta["profile_constraints"]

        present_types = sorted(
            name for name, (pred, _) in PROFILE_FAULT_TYPES.items()
            if any(pred(c) for c in constraints)
        )
        if len(present_types) < n_profile_faults:
            continue  # not enough independently-checkable profile faults available
        chosen_types = present_types[:n_profile_faults]

        profile_dict = {
            "user_id": example.profile.user_id,
            "constraints": constraints,
            "history": [],
        }
        question = example.task["prompt"].split("Question: ", 1)[-1]
        sessions_text, current_date = _extract_context_and_date(example.task["prompt"])

        targets = [ProfileFaultTarget(name=n, predicate=PROFILE_FAULT_TYPES[n][0]) for n in chosen_types]
        try:
            mfr = build_multi_fault(
                task_id=example.task_id, seed=seed, profile_dict=profile_dict,
                answer=answer, context_text=sessions_text, profile_targets=targets,
            )
        except RuntimeError as e:
            print(f"[SKIP] {example.task_id}: {e}", file=sys.stderr)
            continue

        corrupted_profile = _profile_to_userprofile(mfr.corrupted_profile_dict)
        new_prompt = _build_prompt(mfr.corrupted_profile_dict, mfr.corrupted_context_text, current_date, question)

        banned: list[str] = []
        for c in mfr.corrupted_profile_dict["constraints"]:
            if "english only" in c["text"].lower():
                banned += _TRUE_BANNED_SUBSTRINGS

        new_cmeta = {
            **cmeta,
            "profile_constraints": mfr.corrupted_profile_dict["constraints"],
            "banned_substrings": banned,
            "multi_fault_ctx": mfr.fault_context.__dict__,
            "multi_fault_profile": {k: v.__dict__ for k, v in mfr.profile_faults.items()},
            "true_constraint_texts": mfr.true_constraint_texts,
            "true_constraint_ids": mfr.true_constraint_ids,
        }
        rule = _make_rule(new_cmeta)  # unmodified _make_rule, re-parameterized

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
# Priming + arms (unmodified pattern, generic over provider_name/model)
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


def _fault_ctx_resolved(final_output: str | None, true_answer: str) -> bool:
    """Same predicate `longmemeval_real.py::_make_rule` uses for
    `v_real_lme_factual_miss`: true gold answer present in the final output."""
    text = (final_output or "").lower()
    answer = (true_answer or "").strip().lower()
    if not answer:
        return True
    return answer in text


def _baseline_result_to_dict(result: Any) -> dict[str, Any]:
    return {
        "final_trajectory": result.final_trajectory,
        "method_believed_success": result.verifier.passed,
        "tokens_input": result.tokens_input,
        "tokens_output": result.tokens_output,
        "meta_summary": _meta_summary(result.meta),
    }


def _run_direct_arm(example, primed, *, provider_name, model, seed, cache):
    verifier = HybridVerifier(rules=list(example.rules))
    result = run_direct(profile=example.profile, task=example.task, trajectory=primed, verifier=verifier)
    return _baseline_result_to_dict(result)


def _run_self_refine_arm(example, primed, *, provider_name, model, seed, cache):
    provider = build_provider(provider_name, cache=cache)
    verifier = HybridVerifier(rules=list(example.rules))
    result = run_self_refine(
        profile=example.profile, task=example.task, trajectory=primed, verifier=verifier,
        provider=provider, model=model, temperature=0.0, seed=seed,
    )
    return _baseline_result_to_dict(result)


def _run_full_regen_arm(example, primed, *, provider_name, model, seed, cache):
    verifier = HybridVerifier(rules=list(example.rules))
    regen_fn = example.regenerate_fn
    if regen_fn is None:
        regen_fn = _llm_regenerate_fn(provider_name=provider_name, model=model, seed=seed, cache=cache)
    result = run_full_regen(
        profile=example.profile, task=example.task, trajectory=primed, verifier=verifier,
        regenerate_fn=regen_fn, max_attempts=1,
    )
    return _baseline_result_to_dict(result)


def _run_react_arm(example, primed, *, provider_name, model, seed, cache):
    provider = build_provider(provider_name, cache=cache)
    verifier = HybridVerifier(rules=list(example.rules))
    result = run_react(
        profile=example.profile, task=example.task, trajectory=primed, verifier=verifier,
        provider=provider, model=model, temperature=0.0, seed=seed, max_steps=4,
    )
    return _baseline_result_to_dict(result)


def _run_selfcheckgpt_arm(example, primed, *, provider_name, model, seed, cache):
    provider = build_provider(provider_name, cache=cache)
    verifier = HybridVerifier(rules=list(example.rules))
    result = run_selfcheckgpt(
        profile=example.profile, task=example.task, trajectory=primed, verifier=verifier,
        provider=provider, model=model, temperature=0.0, sample_temperature=1.0,
        seed=seed, n_samples=5, abstain_on_inconsistency=False,
    )
    return _baseline_result_to_dict(result)


def _run_reflexion_arm(example, primed, *, provider_name, model, seed, cache):
    provider = build_provider(provider_name, cache=cache)
    verifier = HybridVerifier(rules=list(example.rules))
    result = run_reflexion(
        profile=example.profile, task=example.task, trajectory=primed, verifier=verifier,
        provider=provider, model=model, temperature=0.0, seed=seed, max_trials=2,
    )
    return _baseline_result_to_dict(result)


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
    "reflexion": _run_reflexion_arm,
    "full_regen": _run_full_regen_arm,
    "react": _run_react_arm,
    "selfcheckgpt": _run_selfcheckgpt_arm,
    "intro_specter": _run_intro_specter_arm,
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True, choices=list(MODEL_TABLE))
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--n-examples", type=int, default=60)
    ap.add_argument("--num-faults", type=int, required=True, choices=[2, 3, 4])
    ap.add_argument("--scan-limit", type=int, default=None)
    ap.add_argument("--cache-path", default="cache/completions.sqlite")
    ap.add_argument("--arms", default=",".join(ARM_RUNNERS), help="comma-separated subset of arms to run")
    ap.add_argument("--output-dir", default=None, help="defaults to outputs/rebuttal/experiment_d/full_matrix_longmemeval/{model}")
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

    provider_name, model_id = MODEL_TABLE[args.model]
    cache = SQLiteCache(args.cache_path)

    out_dir = Path(args.output_dir or f"outputs/rebuttal/experiment_d/full_matrix_longmemeval/{args.model}")
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Building {n_examples} {args.num_faults}-fault-injected longmemeval_real examples "
          f"(bench_seed={BENCH_SEED}, scan_limit={args.scan_limit or _SCAN_LIMIT_BY_N[args.num_faults]}, "
          f"model={args.model} provider={provider_name} model_id={model_id})...")
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
                    "model": args.model,
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
                print(f"  model={args.model} N={args.num_faults} arm={arm} {example.task_id} seed={seed}: "
                      f"per_fault={per_fault} all_resolved={all_resolved} n_resolved={n_resolved}/{args.num_faults} "
                      f"tokens=({tokens_input},{tokens_output})")

        f_out.close()
        print(f"--- [{args.model}][{arm}] N={args.num_faults}: rows written={n_rows} errors={n_errors} "
              f"tokens_in={total_tokens_in} tokens_out={total_tokens_out} ---")


if __name__ == "__main__":
    main()
