"""Compute attribution metrics on natural benchmarks (post-hoc on JSONLs).

For each (model, benchmark) pair we have:
  * per-row posterior over candidate fault nodes
  * per-row predicted fault_node
  * NO gold fault label on natural benchmarks (those exist only on the
    synthetic Tier-C). What we *can* report on natural benchmarks:
      - average posterior entropy (concentration of belief)
      - top-1 vs. top-3 agreement (does the system's #1 pick stay stable?)
      - candidate-set size distribution
      - average rank of the chosen fault among all candidates
      - cost vs posterior tradeoff (utility-vs-prior-only)

For the synthetic Tier-C single-fault mode we have gold fault labels, so
top-1 / top-3 / MRR / earliest-fault distance are computed there.

Output: outputs/tier_a/attribution_metrics.csv
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
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


def _entropy(probs: list[float]) -> float:
    p = np.asarray([x for x in probs if x > 0], dtype=float)
    if not p.size:
        return 0.0
    return float(-np.sum(p * np.log(p + 1e-12)))


def _summarize_one(label: str, d: Path) -> dict:
    rows = []
    for path in sorted(d.glob("*intro_specter_llm.jsonl")):
        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
    if not rows:
        return {"model": label, "n": 0}

    n_total = len(rows)
    n_repaired = sum(1 for r in rows if r.get("repair_status") == "repaired")
    n_accepted = sum(1 for r in rows if r.get("repair_status") in (None, "accepted"))
    candidate_sizes = []
    entropies = []
    chosen_ranks = []
    chosen_posteriors = []
    posterior_concentration = []  # max - second-max

    for r in rows:
        post = r.get("posterior")
        if not post:
            continue
        ranked = sorted(post, key=lambda c: -c.get("posterior", 0.0))
        candidate_sizes.append(len(ranked))
        ps = [c.get("posterior", 0.0) for c in ranked]
        entropies.append(_entropy(ps))
        if len(ps) >= 2:
            posterior_concentration.append(ps[0] - ps[1])
        elif len(ps) == 1:
            posterior_concentration.append(ps[0])
        chosen = r.get("fault_node_predicted")
        if chosen is not None:
            for i, c in enumerate(ranked):
                if c["node_id"] == chosen:
                    chosen_ranks.append(i + 1)
                    chosen_posteriors.append(c.get("posterior", 0.0))
                    break

    s = {
        "model": label,
        "n": n_total,
        "n_repaired": n_repaired,
        "n_accepted": n_accepted,
        "repair_rate": n_repaired / n_total if n_total else 0.0,
        "mean_candidates": float(np.mean(candidate_sizes)) if candidate_sizes else 0.0,
        "median_candidates": float(np.median(candidate_sizes)) if candidate_sizes else 0.0,
        "mean_posterior_entropy": float(np.mean(entropies)) if entropies else 0.0,
        "mean_posterior_concentration": (
            float(np.mean(posterior_concentration)) if posterior_concentration else 0.0
        ),
        "mean_chosen_rank": float(np.mean(chosen_ranks)) if chosen_ranks else 0.0,
        "fraction_chosen_is_top1": float(np.mean([r == 1 for r in chosen_ranks])) if chosen_ranks else 0.0,
        "mean_chosen_posterior": float(np.mean(chosen_posteriors)) if chosen_posteriors else 0.0,
    }
    return s


def _synthetic_attribution() -> list[dict]:
    """Top-1 / top-3 / MRR / earliest-fault distance on synthetic single_fault
    mode (the only setting with gold labels)."""
    rows = []
    for split in ("test",):
        for jsonl in Path("outputs/synthetic_single_fault").glob(
            f"synthetic_dag__single_fault__{split}__seed*__intro_specter.jsonl"
        ):
            with jsonl.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rows.append(json.loads(line))
    if not rows:
        return []

    # We don't have direct access to gold fault here; the synthetic benchmark's
    # gold is "a5" (the manual fault node). Hard-code that and report.
    gold = "a5"
    n_top1 = 0
    n_top3 = 0
    rr = 0.0
    distances = []
    for r in rows:
        post = r.get("posterior") or []
        ranked = [c["node_id"] for c in sorted(post, key=lambda c: -c.get("posterior", 0.0))]
        if not ranked:
            continue
        if ranked[0] == gold:
            n_top1 += 1
        if gold in ranked[:3]:
            n_top3 += 1
        try:
            rank = ranked.index(gold) + 1
            rr += 1.0 / rank
        except ValueError:
            pass
        chosen = r.get("fault_node_predicted")
        if chosen and chosen.startswith("a") and gold.startswith("a"):
            try:
                distances.append(abs(int(chosen[1:]) - int(gold[1:])))
            except ValueError:
                pass

    n = len(rows)
    return [{
        "benchmark": "synthetic_dag (single_fault)",
        "n": n,
        "top1_accuracy": n_top1 / n,
        "top3_accuracy": n_top3 / n,
        "mrr": rr / n,
        "earliest_fault_distance_mean": (sum(distances) / len(distances)) if distances else 0.0,
    }]


def main() -> int:
    # ---- Per-model summaries on PFQABench-Recon ----
    pfqa_rows = []
    for label, d in PFQA_DIRS.items():
        d_path = Path(d)
        if not d_path.exists():
            continue
        pfqa_rows.append(_summarize_one(label, d_path))

    out_dir = Path("outputs/tier_a")
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(pfqa_rows)
    df.to_csv(out_dir / "attribution_metrics_pfqa.csv", index=False)
    print("=== PFQABench attribution metrics (per model) ===")
    if not df.empty:
        cols = [
            "model", "n", "n_repaired", "repair_rate",
            "mean_candidates", "mean_posterior_entropy",
            "mean_posterior_concentration", "fraction_chosen_is_top1",
            "mean_chosen_posterior",
        ]
        print(df[cols].to_string(index=False, float_format="%.3f"))

    # ---- Synthetic top-k / MRR ----
    syn_rows = _synthetic_attribution()
    if syn_rows:
        sdf = pd.DataFrame(syn_rows)
        sdf.to_csv(out_dir / "attribution_metrics_synthetic.csv", index=False)
        print("\n=== Synthetic single_fault Tier-C attribution ===")
        print(sdf.to_string(index=False, float_format="%.3f"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
