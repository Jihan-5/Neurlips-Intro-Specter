#!/usr/bin/env python3
"""Experiment C, step 1: sample natural(-ish) failing trajectories + DRAFT LLM annotation.

Rebuttal campaign, Experiment C (Mahh W1 / AC bullet 1): "the entire evaluation
lives inside a regime the authors constructed ... without a benchmark of
naturally occurring hallucinations." This script samples FAILING trajectories
from already-completed baseline runs sitting in `outputs/real/` (no new
generation calls for the sampling step itself -- read-only over existing
JSONL) and then, optionally, runs a cheap DRAFT LLM-as-annotator pass to
speed up the real two-author annotation the plan (orchestration/E2Eplan.md,
Phase 1 / Experiment C) requires.

ADDITIVE ONLY: this script only reads outputs/real/**/*.jsonl and writes new
files under outputs/rebuttal/experiment_c/. It never modifies anything under
intro_specter/, configs/real/, outputs/real/, paper_final.tex, or
paper_sections/.

*** IMPORTANT CAVEAT (read before using this for the rebuttal text) ***
Both source loaders that back these JSONL files inject synthetic profile
material, contrary to the "un-injected" framing in the plan:

  * `intro_specter/benchmarks/longmemeval_real.py` calls
    `inject_profile(..., dataset="hotpotqa")` for every example -- this is
    the SAME synthetic-profile-injection construct as the main paper's
    Profile-injected-X benchmarks, not a natural/un-injected regime.
  * `intro_specter/benchmarks/travelplanner_real.py` keeps TravelPlanner's
    own native constraints (real budget/dietary/date constraints from the
    HF dataset) but additionally augments each example with 1-2 templated
    profile constraints AND applies a 30% `fault_inject` condition
    (deliberately injects one wrong assumption) by default; none of the
    configs under configs/real/ override `fault_inject`, so ~30% of
    TravelPlanner failures in these files may stem from a deliberately
    injected wrong assumption, not an organic model error.

  There is no per-record field in these JSONL files that flags whether a
  given TravelPlanner example fell in the 30% fault-injected slice, so this
  script CANNOT filter injected-fault examples out. The sample and any
  downstream rebuttal text must disclose this: TravelPlanner failures here
  are "native task, augmented + probabilistically fault-injected profile
  layer" -- closer to natural than the Profile-injected-X suite, but not
  purely organic. LongMemEval failures here are NOT a natural-fault sample
  at all; they carry the same injected-profile construct as the headline
  results. Treat the LongMemEval slice in this sample as a secondary,
  heavily-caveated addition, and lead any rebuttal claim with TravelPlanner.

Usage:
    python3 scripts/rebuttal_sample_natural_failures.py \\
        --n-total 50 --seed 42 --annotate

    (omit --annotate to only produce the sample file, no API calls)
"""

from __future__ import annotations

import argparse
import glob
import json
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = REPO_ROOT / "outputs" / "rebuttal" / "experiment_c"
SAMPLE_PATH = OUT_DIR / "natural_failures_sample.jsonl"
DRAFT_ANNOT_PATH = OUT_DIR / "draft_annotations_llm.jsonl"

FAIL_METHODS = ("direct", "reflexion")

TRAVEL_GLOB = "outputs/real/travelplanner_real__*/travelplanner_real__test__seed*__{method}.jsonl"
LME_GLOB = "outputs/real/longmemeval_real__*/longmemeval_real__all__seed*__{method}.jsonl"

DRAFT_ANNOTATOR_MODEL = "qwen/qwen-2.5-7b-instruct"
DRAFT_ANNOTATOR_PROVIDER = "openrouter"

CATEGORIES = [
    "assumption_driven",
    "retrieval_knowledge",
    "arithmetic_logic",
    "formatting_parsing",
    "other",
]

DRAFT_SYSTEM_PROMPT = """You are a DRAFT annotator helping researchers triage failed AI agent \
trajectories before a real human annotation pass. This is NOT the final annotation -- it is a \
fast, unvalidated first guess used only to prioritize which trajectories a human should look at \
first. You will be shown a task, the agent's final output, and why an automated scorer marked it \
a failure. Decide which single category best explains the failure:

- assumption_driven: the agent committed to an identifiable but INCORRECT assumption about the \
user's constraints, preferences, or context (e.g. assumed a preference that wasn't stated, ignored \
or misread a stated constraint, generalized from partial information).
- retrieval_knowledge: the agent got a fact wrong, missed information that was available in context, \
or lacked the knowledge needed to answer -- not really about a user-specific assumption.
- arithmetic_logic: the failure is a computational, counting, or logical-reasoning error (e.g. wrong \
total cost, wrong date arithmetic, invalid inference chain).
- formatting_parsing: the content is arguably correct but the output format, structure, or \
extraction/parsing broke the automated scorer (e.g. missing required field, wrong units, scorer \
couldn't find the answer in the text).
- other: none of the above fit well, or the failure cause is unclear from the given information.

Respond with ONLY a JSON object: {"category": "<one of the five keys above>", "rationale": "<one \
sentence, <=30 words, explaining your guess>"}. No extra text."""


@dataclass
class FailRecord:
    source_file: str
    dataset: str
    task_id: str
    method: str
    model: str
    seed: Any
    success: Any
    constraint_satisfied: Any
    violation_rate: Any
    profile_violation: Any
    final_output: str
    extra: dict


def _load_failures(glob_pattern: str) -> list[FailRecord]:
    records: list[FailRecord] = []
    for method in FAIL_METHODS:
        pattern = str(REPO_ROOT / glob_pattern.format(method=method))
        for fpath in sorted(glob.glob(pattern)):
            rel = str(Path(fpath).relative_to(REPO_ROOT))
            with open(fpath) as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    d = json.loads(line)
                    if d.get("success") is not False:
                        continue
                    records.append(
                        FailRecord(
                            source_file=rel,
                            dataset=d.get("dataset", ""),
                            task_id=d.get("task_id", ""),
                            method=d.get("method", method),
                            model=d.get("model", ""),
                            seed=d.get("seed"),
                            success=d.get("success"),
                            constraint_satisfied=d.get("constraint_satisfied"),
                            violation_rate=d.get("violation_rate"),
                            profile_violation=d.get("profile_violation"),
                            final_output=d.get("final_output") or "",
                            extra=d.get("extra", {}),
                        )
                    )
    return records


def _failure_signal(r: FailRecord) -> dict:
    reasons = []
    if r.success is False:
        reasons.append("success=false")
    if r.constraint_satisfied is False:
        reasons.append("constraint_satisfied=false")
    if r.profile_violation is True:
        reasons.append("profile_violation=true")
    if isinstance(r.violation_rate, (int, float)) and r.violation_rate > 0:
        reasons.append(f"violation_rate={r.violation_rate}")
    return {
        "success": r.success,
        "constraint_satisfied": r.constraint_satisfied,
        "violation_rate": r.violation_rate,
        "profile_violation": r.profile_violation,
        "reasons": reasons,
    }


def _to_sample_row(r: FailRecord) -> dict:
    # These JSONL artifacts store only the final_output (no per-step trajectory
    # log), so "trajectory_summary" here is the final_output itself, truncated,
    # plus a note that no intermediate-step log exists in this artifact format.
    summary = (r.final_output or "").strip()
    if len(summary) > 1500:
        summary = summary[:1500] + " ...[truncated]"
    return {
        "task_id": r.task_id,
        "dataset": r.dataset,
        "model": r.model,
        "method": r.method,
        "seed": r.seed,
        "source_file": r.source_file,
        "trajectory_summary": summary,
        "trajectory_note": (
            "This run artifact stores only the final_output field; no separate "
            "per-step trajectory/tool-call log is present in this JSONL for the "
            "baseline methods sampled here (tool_calls=0 for direct/reflexion "
            "on these cells)."
        ),
        "final_output": r.final_output,
        "failure_signal": _failure_signal(r),
    }


def build_sample(n_total: int, seed: int) -> tuple[list[dict], dict]:
    travel_fails = _load_failures(TRAVEL_GLOB)
    lme_fails = _load_failures(LME_GLOB)

    rng = random.Random(seed)
    n_half = n_total // 2

    def sample(pool: list[FailRecord], k: int) -> list[FailRecord]:
        if len(pool) <= k:
            return list(pool)
        return rng.sample(pool, k)

    travel_sample = sample(travel_fails, n_half)
    lme_sample = sample(lme_fails, n_total - n_half)

    rows = [_to_sample_row(r) for r in (travel_sample + lme_sample)]
    stats = {
        "travelplanner_available_failures": len(travel_fails),
        "travelplanner_sampled": len(travel_sample),
        "longmemeval_available_failures": len(lme_fails),
        "longmemeval_sampled": len(lme_sample),
        "total_sampled": len(rows),
    }
    return rows, stats


def write_sample(rows: list[dict], stats: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta = {
        "_meta": True,
        "purpose": "Experiment C step 1: sample of FAILING baseline trajectories from "
        "already-completed, already-existing outputs/real/ artifacts (direct + reflexion "
        "methods only, success==false). No new generation calls were made to produce this "
        "file -- it is a read-only sample over existing JSONL.",
        "caveat_not_purely_natural": (
            "longmemeval_real injects a synthetic profile via inject_profile(dataset='hotpotqa') "
            "for every example -- it is NOT an un-injected/natural-fault sample, it carries the "
            "same construct as the paper's Profile-injected-X suite. travelplanner_real keeps "
            "TravelPlanner's native constraints but additionally augments each example with 1-2 "
            "templated profile constraints and applies a 30%% fault_inject condition by default "
            "(not disabled in configs/real/); there is no per-record flag distinguishing the "
            "fault-injected 30%% subset. See script docstring for full detail."
        ),
        "disclosure_required": (
            "Any rebuttal text using this sample MUST disclose the REAL annotation protocol "
            "(two authors, per orchestration/E2Eplan.md Experiment C), NOT the DRAFT LLM "
            "annotations in draft_annotations_llm.jsonl, which are unvalidated and exist only "
            "to speed up the human pass."
        ),
        "counts": stats,
    }
    with open(SAMPLE_PATH, "w") as fh:
        fh.write(json.dumps(meta) + "\n")
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def run_draft_annotation(rows: list[dict], cache_path: str) -> list[dict]:
    from intro_specter.models import SQLiteCache, build_provider

    cache = SQLiteCache(cache_path)
    provider = build_provider(DRAFT_ANNOTATOR_PROVIDER, cache=cache)

    annotations = []
    for i, row in enumerate(rows):
        user_prompt = (
            f"Dataset: {row['dataset']}\n"
            f"Task ID: {row['task_id']}\n"
            f"Method: {row['method']}\n"
            f"Failure signal: {json.dumps(row['failure_signal'])}\n\n"
            f"Agent's final output:\n{row['final_output'][:3000]}\n"
        )
        try:
            result = provider.complete(
                system=DRAFT_SYSTEM_PROMPT,
                user=user_prompt,
                model=DRAFT_ANNOTATOR_MODEL,
                temperature=0.0,
                seed=42,
                max_tokens=200,
            )
            parsed = result.parse_json()
            category = parsed.get("category", "other")
            if category not in CATEGORIES:
                category = "other"
            rationale = parsed.get("rationale", "")
            error = None
        except Exception as e:  # noqa: BLE001
            category = "other"
            rationale = ""
            error = str(e)

        annotations.append(
            {
                "task_id": row["task_id"],
                "dataset": row["dataset"],
                "method": row["method"],
                "model": row["model"],
                "draft_category": category,
                "draft_is_assumption_driven": category == "assumption_driven",
                "draft_rationale": rationale,
                "annotator": f"DRAFT-LLM:{DRAFT_ANNOTATOR_PROVIDER}/{DRAFT_ANNOTATOR_MODEL}",
                "error": error,
            }
        )
        print(f"  [{i + 1}/{len(rows)}] {row['task_id']} -> {category}", file=sys.stderr)
        time.sleep(0.05)
    return annotations


def write_draft_annotations(annotations: list[dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    n = len(annotations)
    n_assumption = sum(1 for a in annotations if a["draft_is_assumption_driven"])
    pct = (100.0 * n_assumption / n) if n else 0.0
    meta = {
        "_meta": True,
        "warning": (
            "*** THIS IS A DRAFT, UNVALIDATED LLM-AS-ANNOTATOR PASS. IT IS NOT THE REAL "
            "TWO-AUTHOR ANNOTATION PROTOCOL SPECIFIED IN orchestration/E2Eplan.md (Experiment "
            "C: 'Two-annotator (authors) protocol, 5-category cause label, adjudication, "
            "Cohen's kappa'). DO NOT cite these numbers in the rebuttal text. DO NOT compute "
            "Cohen's kappa or top-1 attribution agreement against these labels. This file exists "
            "only to speed up the real human annotation pass by pre-sorting trajectories. Any "
            "rebuttal text must disclose the real (author) annotators, never this draft. ***"
        ),
        "annotator_model": f"{DRAFT_ANNOTATOR_PROVIDER}/{DRAFT_ANNOTATOR_MODEL}",
        "categories": CATEGORIES,
        "n_annotated": n,
        "n_flagged_assumption_driven": n_assumption,
        "pct_flagged_assumption_driven_UNVALIDATED": round(pct, 1),
    }
    with open(DRAFT_ANNOT_PATH, "w") as fh:
        fh.write(json.dumps(meta) + "\n")
        for a in annotations:
            fh.write(json.dumps(a) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-total", type=int, default=50)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--annotate", action="store_true", help="Also run the DRAFT LLM annotation pass (real API calls).")
    ap.add_argument("--cache-path", default="cache/completions.sqlite")
    args = ap.parse_args()

    rows, stats = build_sample(args.n_total, args.seed)
    write_sample(rows, stats)
    print(f"Wrote {len(rows)} sampled failing trajectories -> {SAMPLE_PATH}")
    print(json.dumps(stats, indent=2))

    if args.annotate:
        print(f"\nRunning DRAFT LLM annotation pass with {DRAFT_ANNOTATOR_PROVIDER}/{DRAFT_ANNOTATOR_MODEL} "
              f"on {len(rows)} rows (cache: {args.cache_path}) ...", file=sys.stderr)
        annotations = run_draft_annotation(rows, args.cache_path)
        write_draft_annotations(annotations)
        n = len(annotations)
        n_assumption = sum(1 for a in annotations if a["draft_is_assumption_driven"])
        pct = (100.0 * n_assumption / n) if n else 0.0
        print(f"Wrote {n} DRAFT annotations -> {DRAFT_ANNOT_PATH}")
        print(f"DRAFT (unvalidated) assumption_driven flag rate: {pct:.1f}% "
              f"({n_assumption}/{n}) -- NOT a substitute for real human annotation.")


if __name__ == "__main__":
    main()
