"""Bundle PFQABench failure cases per IS-winner model into a single CSV with
empty category cells for the user to assign manually.

Format per row: model, task_id, seed, method, profile_summary, question,
expected_answer, agent_final_output, fault_node_predicted, top_posterior,
posterior_concentration, repair_status, _category_assigned_by_user (empty).

Categories the user should assign (from the plan PDF):
  v1: verifier_missed_violation
  v2: wrong_root_cause_attributed
  v3: repair_introduced_new_error
  v4: abstention_too_conservative
  v5: valid_prefix_corrupted
  other: explain in the comments column

Output: outputs/tier_a/error_analysis/failure_bundle.csv (~200 rows).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


# Four IS winners — focus error analysis here.
WINNER_DIRS = {
    "DeepSeek V3":      "outputs/tier_a/pfqa_deepseek",
    "Mistral Nemo 12B": "outputs/tier_a/pfqa_mistral7b",
    "Qwen 2.5 7B":      "outputs/tier_a/pfqa_qwen7b",
    "Gemini 2.5 Flash": "outputs/tier_a/pfqa_gemini_flash",
}


def _profile_summary(task_id: str) -> str:
    """Re-run the benchmark generator to recover the profile + question."""
    from intro_specter.benchmarks.pfqa_recon import PFQABenchRecon

    parts = task_id.rsplit("_", 1)
    if len(parts) != 2:
        return ""
    try:
        idx = int(parts[1])
    except ValueError:
        return ""
    bench = PFQABenchRecon(n_examples=200, seed=0, split="all")
    for ex in bench:
        if ex.task_id == task_id:
            spans = "; ".join(s.text for s in ex.profile.spans)
            return f"{ex.task['condition']} | profile: {spans} | Q: {ex.task['prompt']}"
    return ""


def _bundle_one(label: str, d: Path, max_per_model: int = 50) -> list[dict]:
    rows: list[dict] = []
    intro_path = next(iter(d.glob("*intro_specter_llm.jsonl")), None)
    if intro_path is None:
        return rows

    seen = 0
    for path in sorted(d.glob("*intro_specter_llm.jsonl")):
        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                if r.get("success"):
                    continue
                # Include every success=False row regardless of repair_status:
                # the buckets distinguish "verifier missed" (status=accepted),
                # "repair_failed" (attempted but didn't restore the gold), and
                # "abstain_or_full_regenerate" (chose not to commit).
                if r.get("repair_status") not in (
                    "repaired", "repair_failed", "abstain_or_full_regenerate", "accepted", None
                ):
                    continue
                post = r.get("posterior") or []
                ranked = sorted(post, key=lambda c: -c.get("posterior", 0.0))
                top1 = ranked[0]["posterior"] if ranked else None
                conc = (ranked[0]["posterior"] - ranked[1]["posterior"]) if len(ranked) >= 2 else top1
                rows.append({
                    "model": label,
                    "task_id": r["task_id"],
                    "seed": r.get("seed"),
                    "profile_and_question": _profile_summary(r["task_id"]),
                    "expected_gold": "",  # filled in by user from condition_meta if needed
                    "agent_final_output": (r.get("final_output") or "")[:300],
                    "repair_status": r.get("repair_status"),
                    "fault_node_predicted": r.get("fault_node_predicted"),
                    "top_posterior": round(top1, 3) if top1 else None,
                    "posterior_concentration": round(conc, 3) if conc else None,
                    "_category_assigned_by_user": "",
                    "_user_notes": "",
                })
                seen += 1
                if seen >= max_per_model:
                    return rows
    return rows


def main() -> int:
    out_rows = []
    for label, d in WINNER_DIRS.items():
        d_path = Path(d)
        if not d_path.exists():
            continue
        rows = _bundle_one(label, d_path)
        out_rows.extend(rows)
        print(f"  {label:18s} -> {len(rows)} failure cases")
    out_dir = Path("outputs/tier_a/error_analysis")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "failure_bundle.csv"
    pd.DataFrame(out_rows).to_csv(out, index=False)
    print(f"\nWrote {out}")
    print(
        "Categories to assign in the _category_assigned_by_user column:\n"
        "  v1 verifier_missed_violation\n"
        "  v2 wrong_root_cause_attributed\n"
        "  v3 repair_introduced_new_error\n"
        "  v4 abstention_too_conservative\n"
        "  v5 valid_prefix_corrupted\n"
        "  other (explain in _user_notes)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
