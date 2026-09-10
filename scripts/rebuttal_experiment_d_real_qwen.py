#!/usr/bin/env python3
"""Experiment D (real), 7-arm extension for qwen-2.5-7b, N=2/3/4.

Why this file exists
-----------------------
`scripts/rebuttal_experiment_d_real.py` (tracked, UNMODIFIED by this file --
additive-only campaign) runs the real N=2/3/4 multi-fault sweep on
twowiki_real x mistral-nemo-12b with 2 arms (reflexion, intro_specter). This
script is a fresh sibling file (not an edit) that reuses 100% of that
script's fault-construction/scoring machinery verbatim, but:

  (a) targets a different model: qwen-2.5-7b (openrouter,
      qwen/qwen-2.5-7b-instruct -- confirmed against the exact key already
      used successfully in tonight's Experiment A/B runs), and
  (b) adds 5 additional arms by calling the EXISTING, unmodified baseline
      implementations in `intro_specter/baselines/` (`run_direct`,
      `run_self_refine`, `run_full_regen`, `run_react`, `run_selfcheckgpt`),
      wired the same way `intro_specter/runner.py::run_method_on_example`
      already wires them for the real-benchmark configs. `tot` is
      intentionally excluded per explicit user instruction citing the
      paper's own token-cost finding; `intro_specter_fixed` is excluded per
      task scope (future-work-only arm, out of scope here).

Final arm set (7): direct, self_refine, reflexion, full_regen, react,
selfcheckgpt, intro_specter.

Everything else (N-fault injection via `double_fault_injection.py`,
mechanical profile-fault-type scoring, prompt template, scan-limit table) is
copied verbatim from `rebuttal_experiment_d_real.py` -- see that file's
module docstring for the full design rationale, not repeated here.

Usage:
    python3 scripts/rebuttal_experiment_d_real_qwen.py --smoke --num-faults 2
    python3 scripts/rebuttal_experiment_d_real_qwen.py --num-faults 3 --seeds 0,1,2
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


def _with_retry(fn: Callable[[], _T], *, attempts: int = 5, base_delay: float = 2.0, label: str = "") -> _T:
    """Copied verbatim (attempts bumped 3->5: OpenRouter's qwen-2.5-7b-instruct
    endpoint is observed to be flakier under sustained load than mistral-nemo)."""
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
from intro_specter.benchmarks.twowiki_real import TwoWikiReal, _make_rule, _profile_to_userprofile
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
    Trajectory,
    TrajectoryStep,
    coerce_final_output,
    coerce_trajectory_steps,
)
from intro_specter.verifier import HybridVerifier

MODEL_TABLE = {
    "qwen-2.5-7b": ("openrouter", "qwen/qwen-2.5-7b-instruct"),
}

BENCH_SEED = 42  # matches Experiment A/B's fixed "example seed" convention
_CTX_RE = re.compile(r"Paragraphs:\n(.*)\n\nQuestion:", re.DOTALL)


# ---------------------------------------------------------------------------
# Mechanically-checkable profile-fault type registry (verbatim copy of
# rebuttal_experiment_d_real.py's registry -- that file is tracked/
# unmodified, so this is a fresh copy in a new file, not an edit).
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

_SCAN_LIMIT_BY_N = {2: 3000, 3: 6000, 4: 40000}
MAX_SUPPORTED_NUM_FAULTS = 4


# ---------------------------------------------------------------------------
# Build the N-fault-injected example set (verbatim logic, fresh copy)
# ---------------------------------------------------------------------------


def _extract_context(prompt: str) -> str:
    m = _CTX_RE.search(prompt)
    if not m:
        raise RuntimeError("could not locate 'Paragraphs:' block in prompt -- template drift?")
    return m.group(1)


def _build_prompt(profile_dict: dict[str, Any], context_text: str, question: str) -> str:
    return (
        "User profile (read this and respect any hard constraint):\n"
        + "\n".join(f"- {c['text']}" for c in profile_dict["constraints"])
        + "\n\nUse the following paragraphs to answer the multi-hop question. "
        "Answer in one sentence with the named entity or yes/no.\n\n"
        f"Paragraphs:\n{context_text}\n\n"
        f"Question: {question}"
    )


def _build_multi_fault_examples(
    n_examples: int, seed: int, num_faults: int, scan_limit: int | None = None,
) -> list[tuple[BenchmarkExample, MultiFaultRecord, list[str]]]:
    if num_faults < 2 or num_faults > MAX_SUPPORTED_NUM_FAULTS:
        raise ValueError(
            f"num_faults={num_faults} not supported by this script (only 2,3,4 -- "
            f"N=5 uses the hop-fault sibling script)."
        )
    n_profile_faults = num_faults - 1
    scan_limit = scan_limit or _SCAN_LIMIT_BY_N[num_faults]
    bench = TwoWikiReal(n_examples=scan_limit, seed=seed, split="all", fault_inject=False)
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
            continue
        chosen_types = present_types[:n_profile_faults]

        profile_dict = {
            "user_id": example.profile.user_id,
            "constraints": constraints,
            "history": [],
        }
        question = example.task["prompt"].split("Question: ", 1)[-1]
        context_text = _extract_context(example.task["prompt"])

        targets = [ProfileFaultTarget(name=n, predicate=PROFILE_FAULT_TYPES[n][0]) for n in chosen_types]
        mfr = build_multi_fault(
            task_id=example.task_id, seed=seed, profile_dict=profile_dict,
            answer=answer, context_text=context_text, profile_targets=targets,
        )

        corrupted_profile = _profile_to_userprofile(mfr.corrupted_profile_dict)
        new_prompt = _build_prompt(mfr.corrupted_profile_dict, mfr.corrupted_context_text, question)

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
        rule = _make_rule(new_cmeta)

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


def _fault_ctx_resolved(final_output: str | None, true_answer: str) -> bool:
    text = (final_output or "").lower()
    answer = (true_answer or "").strip().lower()
    if not answer:
        return True
    if answer in text:
        return True
    if answer in {"yes", "no"} and text.strip().startswith(answer):
        return True
    return False


def _llm_regenerate_fn(provider_name: str, model: str, seed: int, cache: SQLiteCache | None):
    """Copied from `intro_specter/runner.py::_llm_regenerate_fn` (unmodified file,
    fresh copy here since that helper is private / not exported)."""
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
        traj = Trajectory(task_id=task.get("task_id", "regen"), steps=steps, final_output=final)
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


def _run_full_regen_arm(
    example: BenchmarkExample, primed: Trajectory, *, provider_name: str, model: str, seed: int,
    cache: SQLiteCache | None,
) -> dict[str, Any]:
    verifier = HybridVerifier(rules=list(example.rules))
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
        provider=provider, model=model, temperature=0.0, sample_temperature=1.0,
        seed=seed, n_samples=5,
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
    "reflexion": _run_reflexion_arm,
    "full_regen": _run_full_regen_arm,
    "react": _run_react_arm,
    "selfcheckgpt": _run_selfcheckgpt_arm,
    "intro_specter": _run_intro_specter_arm,
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="qwen-2.5-7b", choices=list(MODEL_TABLE))
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--n-examples", type=int, default=60)
    ap.add_argument("--num-faults", type=int, default=2, choices=[2, 3, 4])
    ap.add_argument("--scan-limit", type=int, default=None)
    ap.add_argument("--cache-path", default="cache/completions.sqlite")
    ap.add_argument("--output-dir", default="outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b")
    ap.add_argument("--arms", default=None, help="comma-separated subset of arms; default = all 7")
    ap.add_argument("--smoke", action="store_true", help="n=3 examples, 1 seed, all arms, then stop")
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

    arm_names = list(ARM_RUNNERS) if not args.arms else [a.strip() for a in args.arms.split(",") if a.strip()]
    for a in arm_names:
        if a not in ARM_RUNNERS:
            raise SystemExit(f"unknown arm {a!r}; available: {list(ARM_RUNNERS)}")

    # One output file PER ARM: n{N}__{arm}.jsonl, per task spec.
    paths = {arm: out_dir / f"n{args.num_faults}__{arm}.jsonl" for arm in arm_names}
    done: dict[str, set[tuple[str, int]]] = {arm: set() for arm in arm_names}
    for arm, p in paths.items():
        if p.exists():
            for line in p.open():
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                done[arm].add((row["task_id"], row["seed"]))
    n_done_total = sum(len(s) for s in done.values())
    if n_done_total:
        print(f"Resuming: {n_done_total} (task_id, seed) rows already present across {len(arm_names)} arms.")

    print(f"Building {n_examples} {args.num_faults}-fault-injected twowiki_real examples "
          f"(bench_seed={BENCH_SEED}, scan_limit={args.scan_limit or _SCAN_LIMIT_BY_N[args.num_faults]})...")
    examples = _build_multi_fault_examples(n_examples, BENCH_SEED, args.num_faults, args.scan_limit)
    print(f"Built {len(examples)} examples. seeds={seeds}, model={args.model}, arms={arm_names}")
    if len(examples) < n_examples:
        print(f"[WARN] only found {len(examples)}/{n_examples} qualifying examples within the scan pool "
              f"-- consider a larger --scan-limit for num_faults={args.num_faults}.")

    files = {arm: p.open("a") for arm, p in paths.items()}
    total_tokens_in = 0
    total_tokens_out = 0
    n_rows = 0
    n_errors = 0

    for example, mfr, chosen_types in examples:
        for seed in seeds:
            pending_arms = [a for a in arm_names if (example.task_id, seed) not in done[a]]
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
                files[arm].write(json.dumps(row, default=str) + "\n")
                files[arm].flush()
                total_tokens_in += tokens_input
                total_tokens_out += tokens_output
                n_rows += 1
                print(f"  N={args.num_faults} {example.task_id} seed={seed} arm={arm}: "
                      f"per_fault={per_fault} all_resolved={all_resolved} n_resolved={n_resolved}/{args.num_faults} "
                      f"tokens=({tokens_input},{tokens_output})")

    for f in files.values():
        f.close()

    print(f"\n--- run summary (N={args.num_faults}, model={args.model}) ---")
    print(f"rows written: {n_rows}  errors: {n_errors}")
    print(f"total tokens_input={total_tokens_in}  total tokens_output={total_tokens_out}  "
          f"grand_total={total_tokens_in + total_tokens_out}")


if __name__ == "__main__":
    main()
