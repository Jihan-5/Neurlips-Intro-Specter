"""Stratified robustness analysis on existing PFQABench-Recon JSONLs.

Computes per-stratum success rate for every (model, method) on the
test split, then reports the within-model delta vs. Direct on each
stratum so we can see whether Intro-Specter's gains hold across:

* condition (factual_irrelevant vs profile_required)
* user dietary class (vegan / vegetarian / pescatarian)
* (extensible) profile-required template label

Output: outputs/tier_a/robustness_stratify.csv
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd


PFQA_DIRS = {
    "Llama 3.3 70B":     "outputs/tier_a/pfqa_llama",
    "Llama 3.1 8B":      "outputs/tier_a/pfqa_llama3_8b",
    "DeepSeek V3":       "outputs/tier_a/pfqa_deepseek",
    "DeepSeek V3.1":     "outputs/tier_a/pfqa_deepseek_v31",
    "Mistral Nemo 12B":  "outputs/tier_a/pfqa_mistral7b",
    "Qwen 2.5 7B":       "outputs/tier_a/pfqa_qwen7b",
    "gpt-oss-20b":       "outputs/tier_a/pfqa_gptoss20b",
    "Gemini 2.5 Flash":  "outputs/tier_a/pfqa_gemini_flash",
}


def _task_meta_from_id(task_id: str) -> dict:
    """Recover condition + profile facts for a task by re-running the
    benchmark generator. Cheaper than embedding the metadata in JSONL."""
    from intro_specter.benchmarks.pfqa_recon import PFQABenchRecon

    parts = task_id.rsplit("_", 1)
    if len(parts) != 2:
        return {}
    try:
        idx = int(parts[1])
    except ValueError:
        return {}
    bench = PFQABenchRecon(n_examples=200, seed=0, split="all")
    for ex in bench:
        if ex.task_id == task_id:
            return {
                "condition": ex.task.get("condition"),
                "dietary": next(
                    (s.text.split()[-1] for s in ex.profile.spans if s.id == "p_diet"),
                    None,
                ),
            }
    return {}


def _load_rows(d: Path) -> list[dict]:
    rows = []
    for path in sorted(d.glob("*.jsonl")):
        method = path.stem.split("__")[-1]
        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                r["_method"] = method
                rows.append(r)
    return rows


def main() -> int:
    out: list[dict] = []
    for label, d in PFQA_DIRS.items():
        d_path = Path(d)
        if not d_path.exists():
            continue
        rows = _load_rows(d_path)
        if not rows:
            continue
        # Inflate per-row metadata once across all rows.
        task_ids = sorted({r["task_id"] for r in rows})
        meta_by_task = {tid: _task_meta_from_id(tid) for tid in task_ids}
        # Group by (method, condition).
        by_key: dict[tuple, list[bool]] = defaultdict(list)
        for r in rows:
            cond = meta_by_task.get(r["task_id"], {}).get("condition")
            diet = meta_by_task.get(r["task_id"], {}).get("dietary")
            by_key[(r["_method"], "condition", cond)].append(bool(r.get("success")))
            by_key[(r["_method"], "dietary", diet)].append(bool(r.get("success")))
        for (method, axis, value), succs in by_key.items():
            if value is None:
                continue
            out.append({
                "model": label,
                "method": method,
                "axis": axis,
                "stratum": value,
                "n": len(succs),
                "success_rate": sum(succs) / len(succs) if succs else 0.0,
            })
    df = pd.DataFrame(out)
    out_path = Path("outputs/tier_a/robustness_stratify.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Wrote {out_path}")
    if df.empty:
        return 0

    # Pretty print: per (model × axis × stratum), success rate per method.
    pivoted = df.pivot_table(
        index=["model", "axis", "stratum"],
        columns="method",
        values="success_rate",
        aggfunc="first",
    )
    print("\n=== Stratified success rates ===")
    print(pivoted.to_string(float_format="%.3f"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
