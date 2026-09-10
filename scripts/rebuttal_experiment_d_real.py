#!/usr/bin/env python3
"""Experiment D (real): REAL multi-fault comparison, Reflexion vs. Intro-Specter
vs. an EXPERIMENTAL, code-changed Intro-Specter variant (rebuttal campaign,
reviewer LDZz follow-up + user-requested 2/3/4/5-fault sweep).

Why this script exists
-----------------------
`scripts/rebuttal_experiment_d.py` + `scripts/rebuttal_experiment_d_reflexion.py`
ran a synthetic multi-fault comparison and found Intro-Specter at 0% "both
faults resolved" vs. a `full_regen` blind-regeneration baseline at 71.7%. That
gap was traced to a benchmark-design artifact: the synthetic Assumption-DAG
generator injects faults as a value OVERRIDE on top of a clean render, so
blind regeneration trivially reconstructs ground truth by re-rendering from
the (never-corrupted) underlying generative facts -- something a real LLM
doing blind regeneration could never do, since it has no privileged access to
ground truth. This script is the REAL (actual LLM calls, real benchmark)
replacement: it doesn't have that artifact, because every injected fault here
is genuinely, irreversibly baked into what the agent is shown (the retrieved
context and/or the profile prompt), with no clean-render escape hatch.

Benchmark / cell: `twowiki_real` x `mistral-nemo-12b`.

Three arms (per fault count N):
  * `reflexion`          -- real `run_reflexion` (baselines/reflexion.py), UNMODIFIED.
  * `intro_specter`       -- real `run_intro_specter` (pipeline.py), UNMODIFIED.
    **This is the only arm usable as rebuttal evidence about the submitted method.**
  * `intro_specter_fixed` -- real `run_intro_specter_cumulative_repair`
    (pipeline_experimental_cumulative_repair.py), a FUTURE-WORK-ONLY, fully
    separate copy of the pipeline with one targeted change (SPR rounds re-run
    from the previous round's partially-repaired trajectory instead of the
    original). `pipeline.py` itself is never imported or modified by this arm.
    Results from this arm must never be presented as evidence about the
    current submission -- see `outputs/rebuttal/experiment_d/fault_sweep_real_SUMMARY.md`'s
    explicit two-section split.

N-fault injection
------------------
`intro_specter/profiles/double_fault_injection.py` (new, additive file)
generalizes to `build_multi_fault`: it calls the EXISTING, UNMODIFIED
`intro_specter.profiles.fault_injection.inject_fault` once per fault (1
context fault + N-1 profile-constraint faults), each with `rate=1.0` and a
distinct deterministic derived seed, and applies each returned `FaultRecord`
for real (not just as a metadata label):

  * Fault "ctx" -- forced `wrong_value`: a near-neighbor-distractor note is
    appended to the retrieved context. Resolved iff the method's final answer
    still contains the TRUE gold answer -- same predicate
    `twowiki_real.py::_make_rule` already uses for `v_real_2wiki_factual_miss`.

  * Faults "prof_<name>" (N-1 of them) -- forced `wrong_constraint`, each
    restricted to one MECHANICALLY-checkable profile-constraint type (see
    `PROFILE_FAULT_TYPES` below). An initial version of this script tried
    scoring arbitrary relevant soft constraints via a fresh isolated
    `HybridVerifier` LLM check; smoke testing found that unreliable (see git
    history / the version-2 docstring this replaced), so every profile fault
    type here is scored by a small, deterministic, symmetric-across-arms
    mechanical checker instead:
      - "english"  -- banned-substrings check (reuses `twowiki_real.py`'s own
                       `v_real_2wiki_profile_violation` logic).
      - "concise"  -- word count <= 20 (targets "concise answers under 20
                       words") OR sentence count <= 1 (targets "single
                       sentence answer") depending on which template matched.
      - "bullets"  -- no bullet/numbered-list markers in the output.
      - "preamble" -- output doesn't open with a stock preamble phrase
                       ("based on the", "according to", "the question asks",
                       ...); acknowledged as the least precise of the four
                       (heuristic, not a hard syntactic check) -- flagged
                       explicitly in the summary write-up.

  Each example is built by first checking (mechanically, on the TRUE,
  uncorrupted profile) which of the 4 profile-fault types are actually
  present as constraints in that example's profile, then using WHICHEVER
  (N-1) of them are present (deterministic, sorted-by-name selection -- not
  cherry-picked per outcome, decided before any arm runs). Because
  `inject_profile` only samples 3-5 constraints per example and these are
  specific named templates, joint co-occurrence gets rare fast:
  empirically (see the coordinator plan / this script's own probe), >=2 of
  the 4 types co-occur in ~21% of examples, >=3 in ~1.1%, and 4-way
  co-occurrence was 0/6000 in a direct simulation. N=5 (which would need a
  5th independent, mechanically-clean profile-fault type, or 4-way
  co-occurrence of these 4) was found IMPRACTICAL to construct with clean
  scoring and is intentionally NOT run by this script -- see
  `fault_sweep_real_SUMMARY.md` for the full accounting. N=2/3/4 ARE run,
  each scanning a larger index pool than `n_examples` to find enough
  qualifying examples (`scan_limit`, auto-scaled per N).

Usage:
    python3 scripts/rebuttal_experiment_d_real.py --smoke --num-faults 2
    python3 scripts/rebuttal_experiment_d_real.py --num-faults 3 --seeds 0,1,2
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


def _with_retry(fn: Callable[[], _T], *, attempts: int = 3, base_delay: float = 2.0, label: str = "") -> _T:
    """Copied verbatim from scripts/rebuttal_experiment_a.py / _b.py -- transient
    upstream errors (e.g. OpenRouter 'no choices') are retried with backoff."""
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
from intro_specter.benchmarks.twowiki_real import TwoWikiReal, _make_rule, _profile_to_userprofile
from intro_specter.models import SQLiteCache, build_provider
from intro_specter.pipeline import IntroSpecterConfig, run_intro_specter
from intro_specter.pipeline_experimental_cumulative_repair import (
    IntroSpecterConfigCumulative,
    run_intro_specter_cumulative_repair,
)
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
    "mistral-nemo-12b": ("openrouter", "mistralai/mistral-nemo"),
}

BENCH_SEED = 42  # matches Experiment A/B's fixed "example seed" convention
_CTX_RE = re.compile(r"Paragraphs:\n(.*)\n\nQuestion:", re.DOTALL)


# ---------------------------------------------------------------------------
# Mechanically-checkable profile-fault type registry
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
    # "concise answers under 20 words"
    return len(text.split()) <= 20


_BULLET_RE = re.compile(r"(^|\n)\s*([-*•]|\d+[.)])\s")


def _resolved_bullets(final_output: str | None, true_text: str) -> bool:
    return _BULLET_RE.search(final_output or "") is None


def _resolved_preamble(final_output: str | None, true_text: str) -> bool:
    text = (final_output or "").strip().lower()
    return not any(text.startswith(p) for p in _PREAMBLE_PHRASES)


# name -> (predicate over a TRUE constraint dict, resolved-checker(final_output, true_text) -> bool)
PROFILE_FAULT_TYPES: dict[str, tuple[Callable[[dict[str, Any]], bool], Callable[[str | None, str], bool]]] = {
    "english": (_is_english_constraint, _resolved_english),
    "concise": (_is_concise_constraint, _resolved_concise),
    "bullets": (_is_bullets_constraint, _resolved_bullets),
    "preamble": (_is_preamble_constraint, _resolved_preamble),
}

# Empirically measured (n=6000 probe, seed=42, dataset="hotpotqa" profile
# templates -- see this script's module docstring) minimum scan pool needed
# to reliably find `n_examples` qualifying examples per fault count. N=5 is
# intentionally absent (see docstring): 4-way co-occurrence of the 4
# available mechanically-clean profile-fault types was 0/6000.
_SCAN_LIMIT_BY_N = {2: 3000, 3: 6000, 4: 40000}
MAX_SUPPORTED_NUM_FAULTS = 4


# ---------------------------------------------------------------------------
# Build the N-fault-injected example set
# ---------------------------------------------------------------------------


def _extract_context(prompt: str) -> str:
    m = _CTX_RE.search(prompt)
    if not m:
        raise RuntimeError("could not locate 'Paragraphs:' block in prompt -- template drift?")
    return m.group(1)


def _build_prompt(profile_dict: dict[str, Any], context_text: str, question: str) -> str:
    """Exact copy of the prompt-assembly template in
    `intro_specter/benchmarks/twowiki_real.py::_build_example` (lines ~221-228)
    -- reused so the corrupted example is byte-identical in structure to what
    the unmodified loader would have produced, differing only in the injected
    fault content."""
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
    """Loads `twowiki_real` via the existing, unmodified `TwoWikiReal` loader,
    then applies N-fault injection on top of each qualifying example's
    (already-real) profile/context. Returns (example, fault_record,
    profile_fault_names_used) triples. `profile_fault_names_used` is the
    subset of `PROFILE_FAULT_TYPES` actually present (and used) for this
    example, chosen deterministically (sorted by name) BEFORE any arm runs."""
    if num_faults < 2 or num_faults > MAX_SUPPORTED_NUM_FAULTS:
        raise ValueError(
            f"num_faults={num_faults} not supported -- see module docstring "
            f"(N=5 found impractical: needs 4-way co-occurrence of the "
            f"available mechanically-clean profile-fault types, 0/6000 in a "
            f"direct simulation)"
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
            continue  # not enough independently-checkable profile faults available
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

        # banned_substrings for the example's OWN (corrupted-profile-aware)
        # internal verifier rule -- same construction twowiki_real.py uses,
        # applied to the CORRUPTED profile the agent actually sees (so the
        # method's own repair loop is scored the same way the unmodified
        # loader would score it, not given free knowledge of the true fault).
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
# Priming + arms (same structural pattern as Experiment A/B)
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
    """Same predicate `twowiki_real.py::_make_rule` uses for
    `v_real_2wiki_factual_miss`: true gold answer present in the final output."""
    text = (final_output or "").lower()
    answer = (true_answer or "").strip().lower()
    if not answer:
        return True
    if answer in text:
        return True
    if answer in {"yes", "no"} and text.strip().startswith(answer):
        return True
    return False


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
        # spr_max_rounds left at default (2), same 1+2=3-round budget Reflexion's
        # max_trials=2 (1 initial verify + 2 retries) is matched to.
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


def _run_intro_specter_fixed_arm(
    example: BenchmarkExample, primed: Trajectory, *, provider_name: str, model: str, seed: int,
    cache: SQLiteCache | None,
) -> dict[str, Any]:
    """FUTURE-WORK-ONLY arm: `pipeline_experimental_cumulative_repair.py`'s
    `run_intro_specter_cumulative_repair`, a fully separate copy of
    `pipeline.run_intro_specter` (never imported/modified by this arm) with
    one targeted change (SPR rounds accumulate repairs instead of re-deriving
    from the original trajectory each round). NOT usable as evidence about
    the submitted method -- see this script's module docstring and
    `fault_sweep_real_SUMMARY.md`'s two-section split."""
    provider = build_provider(provider_name, cache=cache)
    verifier = HybridVerifier(rules=list(example.rules))
    evaluator = example.evaluator if example.evaluator is not None else _self_report_evaluator
    sampler = LLMCounterfactualSampler(
        provider=provider, model=model, evaluator=evaluator, temperature=0.5, seed=seed,
    )
    cfg = IntroSpecterConfigCumulative(
        model_extraction=model, model_verification=model, model_counterfactual=model,
        model_reexecution=model, extraction_provider=provider, reexecution_provider=provider,
        tau_abstain=0.0, cost_lambda=0.0, n_counterfactual_trials=1,
    )
    is_result = run_intro_specter_cumulative_repair(
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
    "reflexion": _run_reflexion_arm,
    "intro_specter": _run_intro_specter_arm,
    "intro_specter_fixed": _run_intro_specter_fixed_arm,
}
FUTURE_WORK_ONLY_ARMS = {"intro_specter_fixed"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="mistral-nemo-12b", choices=list(MODEL_TABLE))
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--n-examples", type=int, default=60)
    ap.add_argument("--num-faults", type=int, default=2, choices=[2, 3, 4])
    ap.add_argument("--scan-limit", type=int, default=None)
    ap.add_argument("--cache-path", default="cache/completions.sqlite")
    ap.add_argument("--output-dir", default="outputs/rebuttal/experiment_d")
    ap.add_argument("--output-name", default=None, help="defaults to real_multi_fault_n{N}.jsonl")
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
    out_name = args.output_name or f"real_multi_fault_n{args.num_faults}.jsonl"
    out_path = out_dir / out_name

    done: set[tuple[str, int, str]] = set()
    if out_path.exists():
        with out_path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                done.add((row["task_id"], row["seed"], row["arm"]))
    if done:
        print(f"Resuming: {len(done)} (task_id, seed, arm) rows already present, will be skipped.")

    print(f"Building {n_examples} {args.num_faults}-fault-injected twowiki_real examples "
          f"(bench_seed={BENCH_SEED}, scan_limit={args.scan_limit or _SCAN_LIMIT_BY_N[args.num_faults]})...")
    examples = _build_multi_fault_examples(n_examples, BENCH_SEED, args.num_faults, args.scan_limit)
    print(f"Built {len(examples)} examples. seeds={seeds}, model={args.model}, arms={list(ARM_RUNNERS)}")
    if len(examples) < n_examples:
        print(f"[WARN] only found {len(examples)}/{n_examples} qualifying examples within the scan pool "
              f"-- consider a larger --scan-limit for num_faults={args.num_faults}.")

    f_out = out_path.open("a")
    total_tokens_in = 0
    total_tokens_out = 0
    n_rows = 0
    n_errors = 0

    for example, mfr, chosen_types in examples:
        for seed in seeds:
            pending_arms = [a for a in ARM_RUNNERS if (example.task_id, seed, a) not in done]
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
                    "future_work_only": arm in FUTURE_WORK_ONLY_ARMS,
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
                print(f"  N={args.num_faults} {example.task_id} seed={seed} arm={arm}: "
                      f"per_fault={per_fault} all_resolved={all_resolved} n_resolved={n_resolved}/{args.num_faults} "
                      f"tokens=({tokens_input},{tokens_output})")

    f_out.close()

    print(f"\n--- run summary (N={args.num_faults}) ---")
    print(f"rows written: {n_rows}  errors: {n_errors}")
    print(f"total tokens_input={total_tokens_in}  total tokens_output={total_tokens_out}  "
          f"grand_total={total_tokens_in + total_tokens_out}")
    if args.smoke:
        print(
            "Smoke mode: stopping here as instructed. Rough cost estimate at Mistral Nemo's "
            "$0.15/M blended token rate (per scripts/run_real_benchmarks.sh header, not "
            "necessarily current): "
            f"${(total_tokens_in + total_tokens_out) / 1_000_000 * 0.15:.4f}"
        )


if __name__ == "__main__":
    main()
