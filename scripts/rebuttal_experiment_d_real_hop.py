#!/usr/bin/env python3
"""Experiment D (real, hop-fault variant): N=5/N=6 real multi-fault sweep,
Reflexion vs. real unmodified Intro-Specter, twowiki_real x mistral-nemo-12b.

Why this script exists
-----------------------
`scripts/rebuttal_experiment_d_real.py` (N=2/3/4, unmodified, still the
rebuttal-usable evidence for those counts) builds N faults as 1 context
fault + (N-1) profile-constraint faults, and documents why N=5 is
impractical THAT WAY: `inject_profile` only samples 3-5 constraints from 4
available mechanically-clean profile-fault types (english/concise/bullets/
preamble), and 4-way co-occurrence was 0/6000 in a direct simulation.

This script reaches N=5 and N=6 via a DIFFERENT, dataset-structural
resource that does not depend on profile-constraint co-occurrence at all:
2WikiMultiHopQA's `bridge_comparison` question type. Each such row's
`evidences` field is FOUR independent (subject, relation, object) facts
(e.g. two "director" facts + two "date of birth" facts feeding a
which-was-born-later comparison), each tied to its own supporting
paragraph. See `intro_specter/profiles/hop_fault_injection.py`'s module
docstring for the full mechanism and an example. We inject one
near-neighbor-distractor corruption per fact (the OTHER paired fact's true
value, e.g. swapping the two directors' DOBs) -- 4 independent,
textually-disjoint, mechanically-checkable context faults, with zero
reliance on profile constraints.

  * N=5 = 4 hop-context faults + 1 profile-constraint fault (needs >=1 of
    the 4 mechanically-clean profile-fault types present in the example's
    profile).
  * N=6 = 4 hop-context faults + 2 profile-constraint faults (needs >=2
    present).

Direct simulation over the 2671 eligible bridge_comparison rows (type ==
"bridge_comparison" AND exactly 4 evidence facts -- 2671/2751 bridge_comparison
rows, 2751/12576 dev rows total), drawing each row's real `inject_profile`
profile at seed=42 exactly as `twowiki_real.py` does, found:

    >=1 of {english, concise, bullets, preamble} present: 1950/2671 (73.0%)
    >=2 present:                                            532/2671 (19.9%)
    >=3 present:                                             33/2671 ( 1.2%)
    >=4 present:                                              0/2671 ( 0.0%)

So N=5 and N=6 both have large, comfortable scan pools for n=36-60 examples
(this script scans in dataset order, deterministic, not cherry-picked by
outcome -- selection is decided by profile-fault-type availability BEFORE
any arm runs, exactly as `rebuttal_experiment_d_real.py` does for N=2/3/4).
N=7 (needing >=3 present, 1.2%) is left unattempted here as out of scope
for the requested N=5/6; note it is NOT zero the way 4-way co-occurrence
was for the profile-only approach, so a future N=7 attempt is plausible in
principle -- see this script's own probe if that's ever wanted.

Resolution scoring for the 4 hop-context faults: mechanical substring check
of each fact's TRUE object value against the FULL trajectory text (all step
texts concatenated + final_output, not just final_output) -- the system
prompt (`DIRECT_AGENT_SYSTEM`) asks the agent to show reasoning in visible
`steps`, so a fact can be internally resolved without being restated in the
one-sentence final answer; checking only `final_output` would undercount
resolution for facts the final answer format doesn't require repeating (a
compositional comparison question's answer is just "El Extraño Viaje", not
the DOBs). This is the same "true value present in produced text" predicate
`rebuttal_experiment_d_real.py::_fault_ctx_resolved` uses, just applied to
the full trajectory text instead of `final_output` alone, and applied once
per fact. Profile-constraint fault resolution (english/concise/bullets/
preamble) is scored identically to `rebuttal_experiment_d_real.py`
(mechanical, final_output only) -- copied here rather than imported since
it lives in a script, not a package module; logic is unmodified.

Two arms only (per user instruction: skip the future-work-only
`intro_specter_fixed` arm for this run):
  * `reflexion`     -- real `run_reflexion`, UNMODIFIED.
  * `intro_specter` -- real `run_intro_specter`, UNMODIFIED.

Usage:
    python3 scripts/rebuttal_experiment_d_real_hop.py --smoke --num-faults 5
    python3 scripts/rebuttal_experiment_d_real_hop.py --num-faults 6 --seeds 0,1,2 --n-examples 40
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
from intro_specter.baselines import run_reflexion
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
    "mistral-nemo-12b": ("openrouter", "mistralai/mistral-nemo"),
}

BENCH_SEED = 42  # matches N=2/3/4 script's fixed "example seed" convention
N_HOP_FAULTS = 4  # fixed: bridge_comparison canonical layout always has 4


# ---------------------------------------------------------------------------
# Mechanically-checkable profile-fault type registry (unmodified copy of the
# logic in rebuttal_experiment_d_real.py -- that file is tracked/unmodified,
# so this is a fresh copy in a new file, not an edit).
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
# 2WikiMultiHopQA bridge_comparison row loading (direct HF access, mirrors
# twowiki_real.py's `_load` -- unmodified file, this is a fresh read-only copy)
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
    """Byte-identical to twowiki_real.py's `_build_example` prompt template."""
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
    "reflexion": _run_reflexion_arm,
    "intro_specter": _run_intro_specter_arm,
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="mistral-nemo-12b", choices=list(MODEL_TABLE))
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--n-examples", type=int, default=40)
    ap.add_argument("--num-faults", type=int, required=True, choices=[5, 6])
    ap.add_argument("--scan-limit", type=int, default=2671)
    ap.add_argument("--cache-path", default="cache/completions.sqlite")
    ap.add_argument("--output-dir", default="outputs/rebuttal/experiment_d")
    ap.add_argument("--output-name", default=None)
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

    print(f"Building {n_examples} {args.num_faults}-fault (4 hop-context + "
          f"{_N_PROFILE_FAULTS_BY_N[args.num_faults]} profile) twowiki_real bridge_comparison "
          f"examples (bench_seed={BENCH_SEED}, scan_limit={args.scan_limit})...")
    examples = _build_hop_examples(n_examples, BENCH_SEED, args.num_faults, args.scan_limit)
    print(f"Built {len(examples)} examples. seeds={seeds}, model={args.model}, arms={list(ARM_RUNNERS)}")
    if len(examples) < n_examples:
        print(f"[WARN] only found {len(examples)}/{n_examples} qualifying examples within the scan pool.")

    f_out = out_path.open("a")
    total_tokens_in = 0
    total_tokens_out = 0
    n_rows = 0
    n_errors = 0

    for example, hfr, chosen_types in examples:
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
            "Smoke mode: stopping here. Rough cost estimate at Mistral Nemo's $0.15/M "
            "blended token rate: "
            f"${(total_tokens_in + total_tokens_out) / 1_000_000 * 0.15:.4f}"
        )


if __name__ == "__main__":
    main()
