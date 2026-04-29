"""Aggregate Tier-C synthetic results: attribution accuracy + cost-efficiency.

The synthetic benchmark has rule-based gold fault-node labels per task that
the JSONL rows don't carry directly. We re-instantiate
`SyntheticDAGBenchmark` per (mode, seed) to recover gold labels, then
join against the IS jsonl `posterior` and `fault_node_predicted` fields.

Outputs:
  * `outputs/tier_c/synthetic_table.csv`     — per-method per-mode summary
  * `outputs/tier_c/attribution_table.csv`   — top-1 / top-3 / MRR for IS
  * `outputs/tier_c/synthetic_headline.md`   — markdown for §5
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Literal

import pandas as pd

from intro_specter.benchmarks.synthetic_dag import SyntheticDAGBenchmark
from intro_specter.metrics.attribution import mrr, topk_accuracy


SEEDS = [0, 1, 2]
N_EXAMPLES = 100  # match configs/synthetic_*_test.yaml
SPLIT: Literal["test"] = "test"

MODES = ["single_fault", "multi_valid"]


def _gold_lookup(mode: str) -> dict[str, str]:
    """task_id → gold fault_node_id, joined across seeds."""
    out: dict[str, str] = {}
    for seed in SEEDS:
        bench = SyntheticDAGBenchmark(
            n_examples=N_EXAMPLES, seed=seed, mode=mode, split=SPLIT,  # type: ignore[arg-type]
        )
        for ex in bench:
            if ex.gold.fault_node_id is not None:
                out[ex.task_id] = ex.gold.fault_node_id
    return out


def _ranked_predictions(row: dict) -> list[str]:
    """Return predicted fault-node ids in posterior-descending order."""
    posterior = row.get("posterior", []) or []
    if not posterior:
        return []
    sorted_post = sorted(posterior, key=lambda p: -float(p.get("posterior", 0.0)))
    return [p["node_id"] for p in sorted_post if p.get("node_id")]


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for line in path.open():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _attribution_for_mode(mode: str) -> dict | None:
    """Compute top-1, top-3, MRR for IS predicted vs gold on a synthetic mode."""
    gold = _gold_lookup(mode)
    if not gold:
        return None

    preds: list[list[str]] = []
    golds: list[str] = []
    for seed in SEEDS:
        path = Path(f"outputs/synthetic_{mode}/synthetic_dag__{mode}__test__seed{seed}__intro_specter.jsonl")
        rows = _load_jsonl(path)
        for r in rows:
            tid = r["task_id"]
            if tid not in gold:
                continue
            ranked = _ranked_predictions(r)
            if not ranked:
                # No posterior — fall back to scalar prediction if present.
                pred = r.get("fault_node_predicted")
                if pred:
                    ranked = [pred]
            if ranked:
                preds.append(ranked)
                golds.append(gold[tid])
    if not preds:
        return None
    return {
        "n": len(preds),
        "top1_acc": topk_accuracy(preds, golds, k=1),
        "top3_acc": topk_accuracy(preds, golds, k=3),
        "mrr": mrr(preds, golds),
    }


def _per_method_for_mode(mode: str) -> pd.DataFrame:
    rows: list[dict] = []
    summary_path = Path(f"outputs/synthetic_{mode}/synthetic_dag__{mode}__test__summary.json")
    if not summary_path.exists():
        return pd.DataFrame()
    summary = json.loads(summary_path.read_text())
    for method, m in summary["methods"].items():
        rows.append({
            "mode": mode,
            "method": method,
            "n": m.get("n"),
            "success": m.get("success_rate"),
            "violation": m.get("violation_rate"),
            "tokens_total": (m.get("tokens_input_mean", 0) + m.get("tokens_output_mean", 0)),
            "delta_success_vs_direct": m.get("delta_success"),
            "delta_tokens_vs_direct": m.get("delta_tokens"),
            "mcnemar_success_p": m.get("mcnemar_success_p"),
            "wilcoxon_tokens_p": m.get("wilcoxon_tokens_p"),
            "holm_success_adj": m.get("holm_success_p_adj"),
            "degradation_rate": m.get("degradation_rate"),
        })
    return pd.DataFrame(rows)


def main() -> int:
    out_dir = Path("outputs/tier_c")
    out_dir.mkdir(parents=True, exist_ok=True)

    method_dfs = []
    attribution_rows: list[dict] = []

    for mode in MODES:
        per_method = _per_method_for_mode(mode)
        if not per_method.empty:
            method_dfs.append(per_method)

        attr = _attribution_for_mode(mode)
        if attr is not None:
            attribution_rows.append({"mode": mode, **attr})

    if not method_dfs:
        print("No synthetic summaries found.")
        return 1

    method_table = pd.concat(method_dfs, ignore_index=True)
    method_table.to_csv(out_dir / "synthetic_table.csv", index=False)

    attr_table = pd.DataFrame(attribution_rows)
    if not attr_table.empty:
        attr_table.to_csv(out_dir / "attribution_table.csv", index=False)

    md_lines = ["# Tier-C synthetic results (auto-generated)\n"]
    md_lines.append("## Per-method per-mode summary\n")
    md_lines.append(method_table.to_markdown(index=False, floatfmt=".3f"))
    md_lines.append("\n")
    if not attr_table.empty:
        md_lines.append("## Intro-Specter attribution accuracy\n")
        md_lines.append(attr_table.to_markdown(index=False, floatfmt=".3f"))
        md_lines.append("\n")
    (out_dir / "synthetic_headline.md").write_text("\n".join(md_lines))

    print(f"Wrote {out_dir / 'synthetic_table.csv'}")
    print(f"Wrote {out_dir / 'attribution_table.csv'}")
    print(f"Wrote {out_dir / 'synthetic_headline.md'}\n")

    print("=== Per-method per-mode ===")
    print(method_table.to_string(index=False, float_format="%.3f"))
    if not attr_table.empty:
        print("\n=== Intro-Specter attribution accuracy ===")
        print(attr_table.to_string(index=False, float_format="%.3f"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
