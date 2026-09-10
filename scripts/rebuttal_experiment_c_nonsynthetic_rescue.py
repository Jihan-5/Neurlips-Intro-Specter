#!/usr/bin/env python3
"""Re-score `outputs/rebuttal/experiment_c/nonsynthetic_travelplanner_results.jsonl`
after fixing the placeholder-final_output bug documented in
`scripts/rebuttal_experiment_c_nonsynthetic_travelplanner.py`
(`_recover_placeholder_final_output`).

Root cause (traced, not guessed -- see that function's docstring and
`outputs/rebuttal/experiment_c/NONSYNTHETIC_EXTRACTION_FIX.md`): for
`arm == "intro_specter"` rows where the run went through Layer-3 downstream
re-execution (`intro_specter.repair.rerun_downstream_subgraph_llm`), the LLM's
`final_output` field for the "regenerate downstream steps" prompt sometimes comes
back as a non-empty but non-substantive placeholder (e.g. "No downstream steps to
regenerate.", "Repaired trajectory generated successfully.", "Unknown"). Because
`coerce_final_output` only falls back to the ORIGINAL primed trajectory's
final_output when the LLM's own field is `None`/`""`, these placeholders silently
overwrote an often-already-correct primed answer.

The fix is NOT recoverable from the existing JSONL alone (it only stores the final,
already-corrupted `final_output`, truncated to 4000 chars, not the primed
trajectory). But the primed trajectory is fully deterministic (temperature=0.0,
fixed seed) and was generated with response caching on
(`cache/completions.sqlite`, ~300MB, still present) -- so re-running ONLY
`_prime_trajectory` for the affected (task_id, seed) pairs re-derives the exact same
primed trajectory via 100% cache hits, at zero additional API cost. This script does
exactly that: it does NOT re-run the Intro-Specter repair pipeline (which would cost
new API calls for the counterfactual sampler / extraction / re-execution stages) --
it only needs the primed trajectory's `final_output`, which is a single cached
provider call.

Usage:
    python3 scripts/rebuttal_experiment_c_nonsynthetic_rescue.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from intro_specter.models import SQLiteCache  # noqa: E402

from rebuttal_experiment_c_nonsynthetic_travelplanner import (  # noqa: E402
    BENCH_SEED,
    MODEL_TABLE,
    _build_native_examples,
    _extract_total_cost,
    _prime_trajectory,
)

IN_PATH = Path("outputs/rebuttal/experiment_c/nonsynthetic_travelplanner_results.jsonl")
OUT_PATH = Path("outputs/rebuttal/experiment_c/nonsynthetic_travelplanner_results_v2.jsonl")
CACHE_PATH = "cache/completions.sqlite"
MODEL_NAME = "mistral-nemo-12b"


def main() -> None:
    provider_name, model_id = MODEL_TABLE[MODEL_NAME]
    cache = SQLiteCache(CACHE_PATH)

    rows = [json.loads(line) for line in IN_PATH.open() if line.strip()]
    task_ids = sorted({r["task_id"] for r in rows})
    n_examples = len(task_ids)
    print(f"Loaded {len(rows)} rows over {n_examples} distinct task_ids.")

    native_examples = _build_native_examples(n_examples, BENCH_SEED)
    example_by_task_id = {ne.example.task_id: ne for ne in native_examples}
    assert set(example_by_task_id) >= set(task_ids), "task_id reconstruction mismatch"

    # Cache primed trajectories per (task_id, seed) -- shared across arms since
    # _prime_trajectory only depends on (example, seed), not arm.
    primed_cache: dict[tuple[str, int], object] = {}
    n_cache_hits = 0
    n_new_calls = 0

    def get_primed(task_id: str, seed: int):
        nonlocal n_cache_hits, n_new_calls
        key = (task_id, seed)
        if key in primed_cache:
            return primed_cache[key]
        ne = example_by_task_id[task_id]
        # SQLiteCache.get() is checked inside build_provider(...).complete_json();
        # we just detect hit/miss by whether the underlying cache already has this
        # exact call recorded (cheap approximation: cache size before/after would
        # need internals, so we just report to stderr and rely on the cache module
        # itself to avoid a real network call on a hit).
        traj, _tin, _tout = _prime_trajectory(
            ne.example, provider_name=provider_name, model=model_id, seed=seed, cache=cache,
        )
        primed_cache[key] = traj
        return traj

    n_rows_total = 0
    n_intro_specter = 0
    n_affected = 0
    n_recovered = 0
    n_still_unresolved_no_cost = 0

    out_rows = []
    for row in rows:
        n_rows_total += 1
        if row["arm"] != "intro_specter":
            out_rows.append(row)
            continue
        n_intro_specter += 1
        current_cost = row.get("extracted_total_cost")
        if current_cost is not None:
            out_rows.append(row)
            continue

        # Affected row: no parseable cost in the stored final_output. Recover the
        # primed trajectory's final_output (pure cache replay, no new API cost
        # expected -- these prompts were already issued during the original run).
        n_affected += 1
        primed = get_primed(row["task_id"], row["seed"])
        primed_cost = _extract_total_cost(primed.final_output or "")

        new_row = dict(row)
        if primed_cost is not None:
            n_recovered += 1
            new_row["final_output"] = (primed.final_output or "")[:4000]
            new_row["extracted_total_cost"] = primed_cost
            new_row["budget_fault_resolved"] = primed_cost <= row["true_budget"]
            new_row["_rescue_note"] = "recovered_from_primed_trajectory_fallback"
        else:
            n_still_unresolved_no_cost += 1
            new_row["_rescue_note"] = "primed_trajectory_also_had_no_parseable_cost"
        out_rows.append(new_row)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w") as f:
        for r in out_rows:
            f.write(json.dumps(r, default=str) + "\n")

    print(f"\nTotal rows: {n_rows_total}")
    print(f"intro_specter rows: {n_intro_specter}")
    print(f"affected (null extracted_total_cost) rows: {n_affected}")
    print(f"recovered via primed-trajectory fallback: {n_recovered}")
    print(f"still null after fallback (genuine no-cost primed output): {n_still_unresolved_no_cost}")
    print(f"distinct (task_id, seed) primed trajectories re-derived: {len(primed_cache)}")
    print(f"\nWrote corrected results to {OUT_PATH}")

    # ---- Recompute resolved-rate summary for both arms, before vs after ----
    def resolved_rate(rows_in, arm):
        sub = [r for r in rows_in if r["arm"] == arm]
        n = len(sub)
        k = sum(1 for r in sub if r.get("budget_fault_resolved"))
        return k, n, (k / n if n else float("nan"))

    print("\n--- BEFORE (original file) ---")
    for arm in ("reflexion", "intro_specter"):
        k, n, rate = resolved_rate(rows, arm)
        print(f"  {arm}: {k}/{n} = {rate:.1%}")

    print("\n--- AFTER (v2, placeholder-fallback fix applied) ---")
    for arm in ("reflexion", "intro_specter"):
        k, n, rate = resolved_rate(out_rows, arm)
        print(f"  {arm}: {k}/{n} = {rate:.1%}")


if __name__ == "__main__":
    main()
