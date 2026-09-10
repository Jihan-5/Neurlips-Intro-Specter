#!/usr/bin/env python3
"""Experiment C, step 0 (rebuttal campaign, corrected): genuinely un-injected
"natural fault" baseline run.

WHY THIS SCRIPT EXISTS
-----------------------
Investigation (see scripts/rebuttal_sample_natural_failures.py's docstring for
the first, flawed pass) found that EVERY "*_real" benchmark loader under
intro_specter/benchmarks/ calls `inject_profile(...)` unconditionally for
every example -- hotpotqa_real, longmemeval_real, musique_real,
strategyqa_real, travelplanner_real, truthfulqa_real, twowiki_real all do
this. `fault_inject` (a further 30% deliberate wrong-assumption corruption)
defaults to True on top of that in most of them. There is therefore NO
existing, already-run, genuinely clean ("un-injected") data source anywhere
under outputs/real/ -- the paper's entire real-benchmark suite is built on
the profile-injection construct. This confirms the reviewer's ("Mahh")
concern is structurally correct as stated.

This script builds a clean source from scratch: it reuses the RAW
task-loading logic already implemented in truthfulqa_real.py (`_load`) and
musique_real.py (`_load_3hop`, `_flatten_paragraphs`) -- i.e. the exact same
HuggingFace dataset pulls the paper's main results use -- but skips
`inject_profile(...)` and `inject_fault(...)` entirely. No synthetic user
profile is attached to the prompt at all. It then runs ONLY the cheap
`direct` (single-shot) method and scores the output with the SAME gold-answer
substring rule the two loaders already use for their non-profile checks
(`_make_rule`, imported directly, not reimplemented) -- those rule functions
take a `profile` argument but never read it, so they work unmodified with
`profile=None`.

IMPORTANT LIMITATION (expected, not a bug): with no profile attached, there
is no "assumption about the user's constraints/preferences" for the agent to
get wrong -- "assumption-driven failure" per the paper's original definition
structurally cannot occur here. Failures collected by this script are
retrieval/knowledge/reasoning failures (wrong fact, missed multi-hop
reasoning step, TruthfulQA misconception), not profile-violation failures.
This script does NOT attempt to relabel or reframe those failures as
assumption-driven. See the summary this script prints, and the `_meta` block
of the output sample file, for the honest accounting.

ADDITIVE ONLY: reads HuggingFace datasets + calls the model API; writes only
under outputs/rebuttal/experiment_c/ and cache/completions.sqlite. Never
touches intro_specter/, configs/real/, outputs/real/, paper_final.tex, or
paper_sections/.

Usage:
    python3 scripts/rebuttal_natural_baseline_run.py --smoke   # 5+5 examples
    python3 scripts/rebuttal_natural_baseline_run.py --n-per-dataset 100
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from intro_specter.benchmarks.musique_real import (  # noqa: E402
    _flatten_paragraphs,
    _load_3hop,
    _make_rule as _make_musique_rule,
)
from intro_specter.benchmarks.truthfulqa_real import (  # noqa: E402
    _load as _load_truthfulqa,
    _make_rule as _make_truthfulqa_rule,
)
from intro_specter.models import SQLiteCache, build_provider  # noqa: E402
from intro_specter.schemas import Trajectory, TrajectoryStep  # noqa: E402

OUT_DIR = REPO_ROOT / "outputs" / "rebuttal" / "experiment_c"
RUN_PATH = OUT_DIR / "natural_baseline_run_v2.jsonl"
SAMPLE_PATH = OUT_DIR / "natural_failures_sample_v2.jsonl"
OLD_SAMPLE_PATH = OUT_DIR / "natural_failures_sample.jsonl"

# Cheap, cross-family model. Matches the "mistral-nemo-12b" slug used
# throughout outputs/real/ and the other rebuttal scripts' MODEL_TABLE.
PROVIDER_NAME = "openrouter"
MODEL_ID = "mistralai/mistral-nemo"
MODEL_SLUG = "mistral-nemo-12b"

BARE_SYSTEM = """\
You are a helpful assistant answering a single question. You are given NO \
information about who is asking or any of their preferences -- answer the \
question directly, truthfully, and concisely (1-3 sentences). Do not invent \
a user profile or persona. Output plain text only, no JSON, no preamble.
"""


def _with_retry(fn, *, attempts: int = 3, base_delay: float = 2.0, label: str = ""):
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            if attempt == attempts - 1:
                raise
            delay = base_delay * (2 ** attempt)
            print(f"[RETRY] {label} attempt {attempt + 1}/{attempts} failed ({e}); retrying in {delay:.0f}s",
                  file=sys.stderr)
            time.sleep(delay)
    raise RuntimeError("unreachable")  # pragma: no cover


def _run_direct(provider, task_id: str, question: str, seed: int) -> tuple[str, int, int]:
    completion = _with_retry(
        lambda: provider.complete(
            system=BARE_SYSTEM,
            user=f"Question: {question}",
            model=MODEL_ID,
            temperature=0.0,
            seed=seed,
            max_tokens=300,
        ),
        label=f"direct task={task_id}",
    )
    return completion.text.strip(), completion.tokens_input, completion.tokens_output


def _truthfulqa_examples(n: int, start: int = 0) -> list[dict[str, Any]]:
    ds = _load_truthfulqa("validation")
    n = min(n, len(ds) - start)
    out = []
    for i in range(start, start + n):
        ex = ds[i]
        out.append({
            "task_id": f"natural_truthfulqa_{i:05d}",
            "dataset": "truthfulqa_real_NOPROFILE",
            "question": ex["question"],
            "meta": {
                "correct_answers": list(ex["correct_answers"]),
                "incorrect_answers": list(ex["incorrect_answers"]),
                "banned_substrings": [],  # no profile -> nothing to leak
                "category": ex["category"],
                "best_answer": ex["best_answer"],
            },
            "rule_factory": _make_truthfulqa_rule,
        })
    return out


def _musique_examples(n: int, start: int = 0) -> list[dict[str, Any]]:
    rows = _load_3hop("validation")
    n = min(n, len(rows) - start)
    out = []
    for i in range(start, start + n):
        ex = rows[i]
        gold_answer = ex["answer"]
        answer_aliases = list(ex.get("answer_aliases", []) or [])
        all_answers = [gold_answer] + answer_aliases
        context_text = _flatten_paragraphs(ex["paragraphs"], max_chars=3500)
        question = (
            "Use the following paragraphs to answer a 3-hop question. Answer in "
            "one sentence with the named entity.\n\n"
            f"Paragraphs:\n{context_text}\n\nQuestion: {ex['question']}"
        )
        out.append({
            "task_id": f"natural_musique_{i:05d}_{ex['id']}",
            "dataset": "musique_real_NOPROFILE",
            "question": question,
            "meta": {
                "gold_answer": gold_answer,
                "answers": all_answers,
                "banned_substrings": [],
            },
            "rule_factory": _make_musique_rule,
        })
    return out


def run_dataset(examples: list[dict[str, Any]], provider, seed: int, run_f) -> list[dict[str, Any]]:
    rows = []
    for i, ex in enumerate(examples):
        try:
            answer, tin, tout = _run_direct(provider, ex["task_id"], ex["question"], seed)
        except Exception as e:  # noqa: BLE001 -- transient upstream errors; skip and move on
            print(f"  [{i + 1}/{len(examples)}] {ex['task_id']} ERROR (skipped): {e}", file=sys.stderr)
            row = {
                "task_id": ex["task_id"], "dataset": ex["dataset"], "model": MODEL_SLUG,
                "method": "direct", "seed": seed, "question": ex["question"][:2000],
                "final_output": None, "success": None, "error": str(e),
                "violations": [], "gold_meta": {}, "tokens_input": 0, "tokens_output": 0,
            }
            rows.append(row)
            run_f.write(json.dumps(row, default=str) + "\n")
            run_f.flush()
            continue
        traj = Trajectory(
            task_id=ex["task_id"],
            steps=[TrajectoryStep(step_id=1, kind="output", text=answer)],
            final_output=answer,
        )
        rule = ex["rule_factory"](ex["meta"])
        violations = rule(None, None, traj, answer)
        success = len(violations) == 0
        row = {
            "task_id": ex["task_id"],
            "dataset": ex["dataset"],
            "model": MODEL_SLUG,
            "method": "direct",
            "seed": seed,
            "question": ex["question"][:2000],
            "final_output": answer,
            "success": success,
            "violations": [v.model_dump(mode="json") for v in violations],
            "gold_meta": {k: v for k, v in ex["meta"].items() if k != "banned_substrings"},
            "tokens_input": tin,
            "tokens_output": tout,
        }
        rows.append(row)
        run_f.write(json.dumps(row, default=str) + "\n")
        run_f.flush()
        print(f"  [{i + 1}/{len(examples)}] {ex['task_id']} success={success} "
              f"tokens=({tin},{tout})", file=sys.stderr)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-per-dataset", type=int, default=100)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--cache-path", default="cache/completions.sqlite")
    ap.add_argument("--n-sample", type=int, default=50)
    ap.add_argument("--sample-seed", type=int, default=42)
    ap.add_argument("--smoke", action="store_true", help="5+5 examples, then stop before sampling")
    args = ap.parse_args()

    n = 5 if args.smoke else args.n_per_dataset

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cache = SQLiteCache(args.cache_path)
    provider = build_provider(PROVIDER_NAME, cache=cache)

    tqa_examples = _truthfulqa_examples(n)
    mus_examples = _musique_examples(n)
    print(f"Loaded {len(tqa_examples)} TruthfulQA (no-profile) + {len(mus_examples)} "
          f"MuSiQue-3hop (no-profile) raw examples, model={MODEL_SLUG}", file=sys.stderr)

    with open(RUN_PATH, "a") as run_f:
        tqa_rows = run_dataset(tqa_examples, provider, args.seed, run_f)
        mus_rows = run_dataset(mus_examples, provider, args.seed, run_f)

    all_rows = tqa_rows + mus_rows
    scored_rows = [r for r in all_rows if r["success"] is not None]
    n_errors = len(all_rows) - len(scored_rows)
    total_in = sum(r["tokens_input"] for r in all_rows)
    total_out = sum(r["tokens_output"] for r in all_rows)
    n_fail = sum(1 for r in scored_rows if not r["success"])
    print("\n--- run summary ---")
    print(f"total examples: {len(all_rows)}  api_errors_skipped: {n_errors}  "
          f"scored: {len(scored_rows)}  failures: {n_fail}  "
          f"failure_rate={(n_fail / len(scored_rows)):.3f}" if scored_rows else "no scored rows")
    print(f"tokens_input={total_in} tokens_output={total_out} "
          f"grand_total={total_in + total_out}")
    print(f"rough cost estimate @ $0.15/M blended tokens (OpenRouter Mistral-Nemo, "
          f"order-of-magnitude only): ${(total_in + total_out) / 1_000_000 * 0.15:.4f}")

    if args.smoke:
        print("Smoke mode: stopping before sampling, as instructed.")
        return

    import random
    fails = [r for r in scored_rows if not r["success"]]
    rng = random.Random(args.sample_seed)
    k = min(args.n_sample, len(fails))
    sample = rng.sample(fails, k) if len(fails) > k else list(fails)

    tqa_fail_n = sum(1 for r in fails if r["dataset"].startswith("truthfulqa"))
    mus_fail_n = sum(1 for r in fails if r["dataset"].startswith("musique"))

    meta = {
        "_meta": True,
        "corrected_version_of": "outputs/rebuttal/experiment_c/natural_failures_sample.jsonl "
        "(that file is SUPERSEDED for the natural-fault claim -- both its sources, "
        "longmemeval_real and travelplanner_real, inject a synthetic profile "
        "unconditionally and cannot support an 'un-injected' framing; see its own "
        "_meta caveat, added retroactively, cross-referencing this file).",
        "purpose": "Experiment C, corrected: sample of FAILING direct-method trajectories "
        "from a NEWLY RUN, genuinely profile-free baseline (see "
        "scripts/rebuttal_natural_baseline_run.py). Raw tasks reuse truthfulqa_real.py's "
        "and musique_real.py's own HuggingFace loading logic; inject_profile(...) and "
        "inject_fault(...) were never called -- no synthetic profile of any kind is "
        "attached to any prompt in this file.",
        "important_limitation": "With no profile attached, 'assumption-driven failure' "
        "(an incorrect commitment about user constraints/preferences) cannot occur by "
        "construction -- there is no profile to make an assumption about. Every failure "
        "in this sample is a retrieval/knowledge/reasoning failure (wrong fact, missed "
        "hop, TruthfulQA misconception), not a profile-violation failure. This sample "
        "can support the claim 'the model fails on naturally-occurring, un-injected "
        "tasks too' but CANNOT be relabeled or used as-is to support claims specifically "
        "about assumption-driven / profile-violation failure rates, which is what the "
        "paper's core Profile-injected-X suite measures. Do not force a different "
        "conclusion onto this data.",
        "model": MODEL_SLUG,
        "counts": {
            "truthfulqa_examples_run": len(tqa_examples),
            "truthfulqa_failures": tqa_fail_n,
            "musique_examples_run": len(mus_examples),
            "musique_failures": mus_fail_n,
            "total_examples_run": len(all_rows),
            "total_failures_available": len(fails),
            "total_sampled": len(sample),
        },
        "tokens": {"input": total_in, "output": total_out, "total": total_in + total_out},
    }
    with open(SAMPLE_PATH, "w") as fh:
        fh.write(json.dumps(meta) + "\n")
        for row in sample:
            fh.write(json.dumps(row, default=str) + "\n")

    print(f"\nWrote {len(sample)} sampled failing (profile-free) trajectories -> {SAMPLE_PATH}")
    print(json.dumps(meta["counts"], indent=2))


if __name__ == "__main__":
    main()
