#!/usr/bin/env python3
"""Experiment D (real), musique_real multi-fault sweep -- SHARED core logic.

Why this file exists (additive-only, never edits any tracked file)
--------------------------------------------------------------------
This is the musique_real leg of the same multi-fault rebuttal campaign that
already produced the twowiki_real full matrix (see
`scripts/rebuttal_experiment_d_real*.py` and
`outputs/rebuttal/experiment_d/full_matrix/`). It follows the exact same
"one shared core module + thin per-model CLI wrapper" split the twowiki
campaign used (e.g. `rebuttal_experiment_d_real_fullmatrix_mistral.py`
importing `rebuttal_experiment_d_real.py` via `importlib`), just organized
as a plain importable module (loaded the same dynamic-`importlib` way by its
4 sibling per-model scripts) since ALL FOUR model legs share 100% of the
fault-construction and arm-running logic here, differing only in
`MODEL_TABLE`.

Two structurally different fault-construction paths, matching what a direct
760-row simulation over musique_real's full 3-hop pool (dgslibisey/MuSiQue
validation split, `id` startswith "3hop") found BEFORE writing this file:

  * N=2, N=3 -- `intro_specter/profiles/double_fault_injection.py`'s
    dataset-agnostic `build_multi_fault` (1 context "wrong_value" fault + N-1
    profile-constraint "wrong_constraint" faults, unmodified mechanism,
    identical to the twowiki_real N=2/3/4 approach). Simulation over all 760
    rows (seed=42, `inject_profile(dataset="hotpotqa")`, same 4
    mechanically-clean profile-fault types twowiki_real used -- english/
    concise/bullets/preamble): >=1 type present in 553/760 (72.8%, enough for
    N=2), >=2 in 148/760 (19.5%, enough for N=3), >=3 in only 3/760 (0.4%).
    N=4 via this path would need that 3-way co-occurrence and is NOT
    supported here (unlike twowiki_real, which could reach N=4 this way only
    because its scannable pool was far larger; musique_real's dev 3-hop
    subset is capped at 760 rows total, so 3/760 qualifying examples is not
    enough for n=36-60).

  * N=4, N=5 -- `intro_specter/profiles/musique_hop_fault_injection.py`
    (new, additive; see its own module docstring for the full argument),
    using musique_real's OWN native `question_decomposition` field: every
    3hop row has exactly 3 independent sub-question/answer hop facts
    (760/760, i.e. this resource needs no subset filtering at all, unlike
    twowiki_real's `bridge_comparison`-only 2671/12576). 3 hop-context faults
    (always) + 1 profile fault (N=4, 553/760 candidates) or 2 profile faults
    (N=5, 148/760 candidates) -- both comfortably support n=36-60.

  * N=6 (3 hop + 3 profile) would need the same 3-way profile co-occurrence
    measured above (3/760, 0.4%) -- NOT supported here, for the same reason
    N=4 isn't supported via the double-fault path. This mirrors twowiki_real's
    own N=6 ceiling (which also needed a co-occurrence rate that direct
    simulation found impractical at n=36-60) -- reported honestly, not tuned.

7 arms per fault count (identical calling convention to the twowiki_real
7-arm scripts, `intro_specter/baselines/*` and `intro_specter/pipeline.py`
both unmodified):
    direct, self_refine, full_regen, react, selfcheckgpt, reflexion, intro_specter
(`tot` and `intro_specter_fixed` excluded, same as the twowiki campaign.)

Output: `outputs/rebuttal/experiment_d/full_matrix_musique/{model}/n{N}__{arm}.jsonl`,
one row per (task_id, seed), resumable/dedup'd per arm file exactly like the
twowiki per-model scripts.
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
    """Same retry-with-backoff pattern as the twowiki per-model scripts."""
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
from intro_specter.benchmarks.musique_real import (
    MuSiQueReal,
    _flatten_paragraphs,
    _load_3hop,
    _make_rule,
    _profile_to_userprofile,
)
from intro_specter.models import SQLiteCache, build_provider
from intro_specter.pipeline import IntroSpecterConfig, run_intro_specter
from intro_specter.profiles import inject_profile
from intro_specter.profiles.double_fault_injection import (
    MultiFaultRecord,
    ProfileFaultTarget,
    build_multi_fault,
)
from intro_specter.profiles.musique_hop_fault_injection import (
    N_HOP_FACTS,
    MusiqueHopFaultRecord,
    build_musique_hop_fault,
)
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

BENCH_SEED = 42
_CTX_RE = re.compile(r"Paragraphs:\n(.*)\n\nQuestion:", re.DOTALL)

DOUBLE_FAULT_NUMS = {2, 3}
HOP_FAULT_NUMS = {4, 5}
SUPPORTED_NUMS = DOUBLE_FAULT_NUMS | HOP_FAULT_NUMS
# N=6 (3 hop + 3 profile faults) intentionally excluded: only 3/760 (0.4%)
# musique_real 3-hop rows have 3-way co-occurrence of the 4 mechanically-clean
# profile-fault types (direct simulation, see module docstring) -- not
# practical at n=36-60.

_N_PROFILE_FAULTS_BY_HOP_N = {4: 1, 5: 2}
_N_PROFILE_FAULTS_BY_DOUBLE_N = {2: 1, 3: 2}


# ---------------------------------------------------------------------------
# Mechanically-checkable profile-fault type registry (unmodified copy of the
# registry `rebuttal_experiment_d_real.py` / `_hop.py` use for twowiki_real --
# musique_real's profiles are drawn from the SAME `inject_profile(dataset=
# "hotpotqa")` template bank, so the same 4 types and checkers apply as-is).
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


def _build_prompt(profile_dict: dict[str, Any], context_text: str, question: str) -> str:
    """Exact copy of the prompt-assembly template in
    `intro_specter/benchmarks/musique_real.py::_build_example` -- reused so
    the corrupted example is byte-identical in structure to what the
    unmodified loader would have produced, differing only in the injected
    fault content."""
    return (
        "User profile (read this and respect any hard constraint):\n"
        + "\n".join(f"- {c['text']}" for c in profile_dict["constraints"])
        + "\n\nUse the following paragraphs to answer a 3-hop question. "
        "Answer in one sentence with the named entity.\n\n"
        f"Paragraphs:\n{context_text}\n\n"
        f"Question: {question}"
    )


def _extract_context(prompt: str) -> str:
    m = _CTX_RE.search(prompt)
    if not m:
        raise RuntimeError("could not locate 'Paragraphs:' block in prompt -- template drift?")
    return m.group(1)


def _banned_for(profile_dict: dict[str, Any]) -> list[str]:
    banned: list[str] = []
    for c in profile_dict["constraints"]:
        if "english only" in c["text"].lower():
            banned += _TRUE_BANNED_SUBSTRINGS
    return banned


# ---------------------------------------------------------------------------
# N=2/3 -- double-fault path (dataset-agnostic build_multi_fault, reused as-is)
# ---------------------------------------------------------------------------


def _build_double_fault_examples(
    n_examples: int, seed: int, num_faults: int, scan_limit: int | None = None,
) -> list[tuple[BenchmarkExample, MultiFaultRecord, list[str]]]:
    if num_faults not in DOUBLE_FAULT_NUMS:
        raise ValueError(f"num_faults={num_faults} not supported by the double-fault path (2, 3 only)")
    n_profile_faults = _N_PROFILE_FAULTS_BY_DOUBLE_N[num_faults]
    # musique_real's dev 3-hop pool is capped at 760 rows total (see module
    # docstring) -- MuSiQueReal(n_examples=...) itself clamps to that, so
    # scan_limit here is just "use the full pool" rather than a real ceiling.
    scan_limit = scan_limit or 760
    bench = MuSiQueReal(n_examples=scan_limit, seed=seed, split="all", fault_inject=False)
    out: list[tuple[BenchmarkExample, MultiFaultRecord, list[str]]] = []
    for example in bench:
        if len(out) >= n_examples:
            break
        cmeta = example.task["condition_meta"]
        answer = cmeta["gold_answer"]
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


def _fault_ctx_resolved(final_output: str | None, true_answers: list[str]) -> bool:
    """Same predicate `musique_real.py::_make_rule` uses for
    `v_real_musique_factual_miss`: TRUE gold answer (or an alias) present in
    the final output."""
    text = (final_output or "").lower()
    answers = [a.strip().lower() for a in true_answers if a and a.strip()]
    if not answers:
        return True
    return any(a in text for a in answers)


# ---------------------------------------------------------------------------
# N=4/5 -- hop-fault path (musique_real's OWN native question_decomposition)
# ---------------------------------------------------------------------------


def _build_hop_fault_examples(
    n_examples: int, seed: int, num_faults: int, scan_limit: int | None = None,
) -> list[tuple[BenchmarkExample, MusiqueHopFaultRecord, list[str]]]:
    if num_faults not in HOP_FAULT_NUMS:
        raise ValueError(f"num_faults={num_faults} not supported by the hop-fault path (4, 5 only)")
    n_profile_faults = _N_PROFILE_FAULTS_BY_HOP_N[num_faults]
    rows = _load_3hop("validation")
    scan_limit = scan_limit or len(rows)

    out: list[tuple[BenchmarkExample, MusiqueHopFaultRecord, list[str]]] = []
    for idx, ex in enumerate(rows[:scan_limit]):
        if len(out) >= n_examples:
            break
        task_id = f"real_musique_hop_{idx:05d}_{ex['id']}"
        profile_dict = inject_profile(task_id=task_id, seed=seed, dataset="hotpotqa")

        present_types = sorted(
            name for name, (pred, _) in PROFILE_FAULT_TYPES.items()
            if any(pred(c) for c in profile_dict["constraints"])
        )
        if len(present_types) < n_profile_faults:
            continue
        chosen_types = present_types[:n_profile_faults]

        question = ex["question"]
        gold_answer = ex["answer"]
        answer_aliases = list(ex.get("answer_aliases", []) or [])
        all_answers = [gold_answer] + answer_aliases
        context_text = _flatten_paragraphs(ex["paragraphs"], max_chars=3500)

        targets = [ProfileFaultTarget(name=n, predicate=PROFILE_FAULT_TYPES[n][0]) for n in chosen_types]
        try:
            hfr = build_musique_hop_fault(
                task_id=task_id, seed=seed, profile_dict=profile_dict, context_text=context_text,
                decomposition=list(ex["question_decomposition"]), profile_targets=targets,
            )
        except RuntimeError as e:
            print(f"[SKIP] {task_id}: {e}", file=sys.stderr)
            continue

        corrupted_profile = _profile_to_userprofile(hfr.corrupted_profile_dict)
        prompt = _build_prompt(hfr.corrupted_profile_dict, hfr.corrupted_context_text, question)
        banned = _banned_for(hfr.corrupted_profile_dict)

        cmeta = {
            "gold_answer": gold_answer,
            "answers": all_answers,
            "musique_id": ex["id"],
            "musique_hops": 3,
            "banned_substrings": banned,
            "profile_constraints": hfr.corrupted_profile_dict["constraints"],
            "gold_fault_node": None,
            "fault_record": None,
        }
        rule = _make_rule(cmeta)
        task = {
            "task_id": task_id,
            "task_type": "real_musique",
            "condition": "factual_3hop_real_hopfault",
            "prompt": prompt,
            "split": "test",
            "condition_meta": cmeta,
        }
        gold = GoldLabels(success=None, correct_final_output=gold_answer, fault_node_id=None)
        example = BenchmarkExample(
            task_id=task_id,
            dataset="musique_real_hop",
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
# Priming + arms (identical calling convention to the twowiki per-model scripts)
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


def run_cli(*, model_table: dict[str, tuple[str, str]], default_model: str, default_output_dirname: str) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default=default_model, choices=list(model_table))
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--n-examples", type=int, default=60)
    ap.add_argument("--num-faults", type=int, required=True, choices=sorted(SUPPORTED_NUMS))
    ap.add_argument("--scan-limit", type=int, default=None)
    ap.add_argument("--cache-path", default="cache/completions.sqlite")
    ap.add_argument("--output-dir", default=f"outputs/rebuttal/experiment_d/full_matrix_musique/{default_output_dirname}")
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

    if args.num_faults in DOUBLE_FAULT_NUMS:
        print(f"Building {n_examples} {args.num_faults}-fault (1 ctx + "
              f"{_N_PROFILE_FAULTS_BY_DOUBLE_N[args.num_faults]} profile) musique_real examples "
              f"(bench_seed={BENCH_SEED}, scan_limit={args.scan_limit or 760})...")
        examples = _build_double_fault_examples(n_examples, BENCH_SEED, args.num_faults, args.scan_limit)
        fault_types_fn = lambda chosen_types: ["ctx"] + chosen_types  # noqa: E731
    else:
        print(f"Building {n_examples} {args.num_faults}-fault (3 hop + "
              f"{_N_PROFILE_FAULTS_BY_HOP_N[args.num_faults]} profile) musique_real hop examples "
              f"(bench_seed={BENCH_SEED}, scan_limit={args.scan_limit or 760})...")
        examples = _build_hop_fault_examples(n_examples, BENCH_SEED, args.num_faults, args.scan_limit)
        fault_types_fn = lambda chosen_types: [f"hop{i}" for i in range(N_HOP_FACTS)] + chosen_types  # noqa: E731

    print(f"Built {len(examples)} examples. seeds={seeds}, model={args.model}, arms={arms}")
    if len(examples) < n_examples:
        print(f"[WARN] only found {len(examples)}/{n_examples} qualifying examples within the scan pool.")

    f_outs = {a: p.open("a") for a, p in out_paths.items()}
    total_tokens_in = 0
    total_tokens_out = 0
    n_rows = 0
    n_errors = 0

    for example, fault_record, chosen_types in examples:
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
                per_fault: dict[str, bool] = {}
                if args.num_faults in DOUBLE_FAULT_NUMS:
                    true_answers = example.task["condition_meta"]["answers"]
                    per_fault["ctx"] = _fault_ctx_resolved(final_traj.final_output, true_answers)
                else:
                    full_text = _trajectory_full_text(final_traj)
                    for i, (sub_q, true_ans, decoy_ans) in fault_record.facts.items():
                        per_fault[f"hop{i}"] = true_ans.lower() in full_text.lower()
                for name in chosen_types:
                    _, checker = PROFILE_FAULT_TYPES[name]
                    true_text = fault_record.true_constraint_texts[name]
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
                    "fault_types": fault_types_fn(chosen_types),
                    "per_fault_resolved": per_fault,
                    "all_resolved": all_resolved,
                    "n_resolved": n_resolved,
                    "method_believed_success": bool(arm_out["method_believed_success"]),
                    "true_constraint_texts": fault_record.true_constraint_texts,
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
