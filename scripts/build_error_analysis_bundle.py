"""Prepare the manual-error-analysis bundle for §6 of the paper.

Selects 50 IS-failure trials from each of the 4 strongest IS-winning
cells (200 cases total) and emits a single JSONL with everything a
human labeler needs to bucket each failure into one of the 5 categories
the paper documents:

  1. verifier missed       — the rule-based verifier didn't detect a
                             violation a human would flag
  2. wrong root cause      — the posterior picked the wrong fault node
  3. repair introduced new error — the rerun produced a worse trajectory
  4. abstention too conservative — IS abstained when commit would have succeeded
  5. valid prefix corrupted — the rerun discarded valid earlier steps

Output: outputs/error_analysis/bundle.jsonl
Each row has:
  * task_id, dataset, model, seed
  * profile (constraints + categories)
  * task_prompt
  * gold_answer
  * direct_trajectory (final_output + verifier verdict)
  * is_trajectory (final_output + verifier verdict + repair_status +
                   posterior + fault_node_predicted + repaired_subgraph)
  * pre-filled empty fields for the labeler:
      - bucket
      - notes
      - subbucket (free-text)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


# Cells to sample failures from — top IS-significant cells where a paper
# reader would want to understand why the residual ~10% of cases still fail.
TARGET_CELLS = [
    ("Profile-MuSiQue × Gemini Flash", "outputs/tier_b/musique_gemini_flash"),
    ("Profile-MuSiQue × Qwen 7B",      "outputs/tier_b/musique_qwen_7b"),
    ("Profile-ALFWorld × Mistral Nemo","outputs/tier_b/alfworld_mistral_nemo"),
    ("Real-HotpotQA × Qwen 7B",        "outputs/tier_b/real_hotpotqa_qwen_7b"),
]

N_PER_CELL = 50


def _load_method(cell_dir: Path, method: str) -> dict[tuple[str, int], dict]:
    """task_id, seed → row dict for one method in one cell."""
    rows: dict[tuple[str, int], dict] = {}
    for path in sorted(cell_dir.glob(f"*__seed*__{method}.jsonl")):
        for line in path.open():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = (r["task_id"], int(r["seed"]))
            rows[key] = r
    return rows


def _build_bundle() -> list[dict]:
    out: list[dict] = []
    for cell_label, cell_path in TARGET_CELLS:
        cell_dir = Path(cell_path)
        if not cell_dir.exists():
            print(f"[skip] {cell_label}: dir missing")
            continue
        is_rows = _load_method(cell_dir, "intro_specter_llm")
        direct_rows = _load_method(cell_dir, "direct")

        # Failures: IS row with success=False
        failures = [(k, r) for k, r in is_rows.items() if not bool(r.get("success", False))]
        if len(failures) < 5:
            print(f"[skip] {cell_label}: only {len(failures)} failures")
            continue

        # Sample up to N_PER_CELL deterministically.
        failures = sorted(failures)[:N_PER_CELL]

        for (task_id, seed), is_r in failures:
            direct_r = direct_rows.get((task_id, seed), {})
            entry = {
                "cell": cell_label,
                "task_id": task_id,
                "seed": seed,
                "dataset": is_r.get("dataset"),
                "model": is_r.get("model"),
                "task_prompt": (is_r.get("extra", {}) or {}).get("task_prompt", ""),
                "gold_answer": (is_r.get("extra", {}) or {}).get("gold_final_output",
                              direct_r.get("extra", {}).get("gold_final_output", "")),
                "direct": {
                    "final_output": direct_r.get("final_output", ""),
                    "success": bool(direct_r.get("success", False)),
                    "violation_rate": direct_r.get("violation_rate", 0),
                    "tokens_total": int(direct_r.get("tokens_input", 0))
                                    + int(direct_r.get("tokens_output", 0)),
                },
                "intro_specter": {
                    "final_output": is_r.get("final_output", ""),
                    "success": bool(is_r.get("success", False)),
                    "violation_rate": is_r.get("violation_rate", 0),
                    "repair_status": is_r.get("repair_status"),
                    "fault_node_predicted": is_r.get("fault_node_predicted"),
                    "posterior_top3": (sorted(is_r.get("posterior", []) or [],
                                              key=lambda p: -float(p.get("posterior", 0)))[:3]),
                    "tokens_total": int(is_r.get("tokens_input", 0))
                                    + int(is_r.get("tokens_output", 0)),
                },
                # Empty fields for the labeler.
                "label": {
                    "bucket": "",   # one of the 5 categories
                    "subbucket": "",
                    "notes": "",
                },
            }
            out.append(entry)
        print(f"  {cell_label}: bundled {len(failures)} failures")
    return out


def main() -> int:
    out_dir = Path("outputs/error_analysis")
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle = _build_bundle()
    if not bundle:
        print("No failures bundled; ensure target cells have data.")
        return 1
    bundle_path = out_dir / "bundle.jsonl"
    with bundle_path.open("w") as f:
        for entry in bundle:
            f.write(json.dumps(entry) + "\n")
    # Also a CSV companion for spreadsheet labeling.
    import csv
    csv_path = out_dir / "bundle.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "cell", "task_id", "seed", "task_prompt", "gold_answer",
            "direct_final", "direct_success",
            "is_final", "is_success", "is_repair_status", "is_fault_node",
            "label_bucket", "label_subbucket", "label_notes",
        ])
        for e in bundle:
            w.writerow([
                e["cell"], e["task_id"], e["seed"],
                e["task_prompt"][:300], (e["gold_answer"] or "")[:200],
                (e["direct"]["final_output"] or "")[:300], e["direct"]["success"],
                (e["intro_specter"]["final_output"] or "")[:300],
                e["intro_specter"]["success"],
                e["intro_specter"]["repair_status"],
                e["intro_specter"]["fault_node_predicted"],
                "", "", "",
            ])
    print(f"\nWrote {bundle_path} ({len(bundle)} cases)")
    print(f"Wrote {csv_path}")
    print("\nLabeling instructions:")
    print("  Open bundle.csv in your editor / spreadsheet.")
    print("  For each row, set label_bucket to one of:")
    print("    - 'verifier_missed'       (rule false-negative)")
    print("    - 'wrong_root_cause'      (posterior picked wrong fault node)")
    print("    - 'repair_introduced_new_error'")
    print("    - 'abstention_too_conservative'")
    print("    - 'valid_prefix_corrupted'")
    print("  Add 1 short note about why.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
