"""Aggregate Tier-A results across 4 runs (3 Llama benchmarks + 1 DeepSeek cross-family).

Reads the per-benchmark `*__summary.json` files produced by the runner,
emits:
  * a combined main-results table (`outputs/tier_a/main_table.csv`) with
    per-method per-benchmark success / violation / tokens / Δsuccess vs
    direct / Holm-adjusted p-values;
  * a cross-family comparison table (`outputs/tier_a/cross_family.csv`)
    with per-method success deltas Llama → DeepSeek on PFQABench-Recon,
    paired by (task_id, seed);
  * a markdown headline summary (`outputs/tier_a/headline.md`) that
    serves as the §5 results draft.

Run after all four headline configs have completed.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

from intro_specter.metrics.stats import (
    holm_bonferroni,
    mcnemar,
    paired_bootstrap_ci,
    wilcoxon_signed_rank,
)


TIER_A_BENCHMARKS = {
    # PFQABench × 8 models
    "PFQABench-Recon (Llama 3.3 70B)":      "outputs/tier_a/pfqa_llama",
    "PFQABench-Recon (Llama 3.1 8B)":       "outputs/tier_a/pfqa_llama3_8b",
    "PFQABench-Recon (DeepSeek V3)":        "outputs/tier_a/pfqa_deepseek",
    "PFQABench-Recon (DeepSeek V3.1)":      "outputs/tier_a/pfqa_deepseek_v31",
    "PFQABench-Recon (gpt-oss-20b)":        "outputs/tier_a/pfqa_gptoss20b",
    "PFQABench-Recon (Mistral Nemo 12B)":   "outputs/tier_a/pfqa_mistral7b",
    "PFQABench-Recon (Gemini 2.5 Flash)":   "outputs/tier_a/pfqa_gemini_flash",
    "PFQABench-Recon (Qwen 2.5 7B)":        "outputs/tier_a/pfqa_qwen7b",
    # TravelPlanner+ × 8 models
    "TravelPlanner+ (Llama 3.3 70B)":       "outputs/tier_a/travel_llama",
    "TravelPlanner+ (Llama 3.1 8B)":        "outputs/tier_a/travel_llama3_8b",
    "TravelPlanner+ (DeepSeek V3)":         "outputs/tier_a/travel_deepseek",
    "TravelPlanner+ (DeepSeek V3.1)":       "outputs/tier_a/travel_deepseek_v31",
    "TravelPlanner+ (gpt-oss-20b)":         "outputs/tier_a/travel_gptoss20b",
    "TravelPlanner+ (Mistral Nemo 12B)":    "outputs/tier_a/travel_mistral7b",
    "TravelPlanner+ (Gemini 2.5 Flash)":    "outputs/tier_a/travel_gemini_flash",
    "TravelPlanner+ (Qwen 2.5 7B)":         "outputs/tier_a/travel_qwen7b",
    # TauBench × 8 models
    "TauBench (Llama 3.3 70B)":             "outputs/tier_a/taubench_llama",
    "TauBench (Llama 3.1 8B)":              "outputs/tier_a/taubench_llama3_8b",
    "TauBench (DeepSeek V3)":               "outputs/tier_a/taubench_deepseek",
    "TauBench (DeepSeek V3.1)":             "outputs/tier_a/taubench_deepseek_v31",
    "TauBench (gpt-oss-20b)":               "outputs/tier_a/taubench_gptoss20b",
    "TauBench (Mistral Nemo 12B)":          "outputs/tier_a/taubench_mistral7b",
    "TauBench (Gemini 2.5 Flash)":          "outputs/tier_a/taubench_gemini_flash",
    "TauBench (Qwen 2.5 7B)":               "outputs/tier_a/taubench_qwen7b",
    # Tier-B: HotpotQA-Recon × 4 IS-winners
    "HotpotQA (DeepSeek V3)":               "outputs/tier_b/hotpotqa_deepseek_v3",
    "HotpotQA (Mistral Nemo 12B)":          "outputs/tier_b/hotpotqa_mistral_nemo",
    "HotpotQA (Qwen 2.5 7B)":               "outputs/tier_b/hotpotqa_qwen_7b",
    "HotpotQA (Gemini 2.5 Flash)":          "outputs/tier_b/hotpotqa_gemini_flash",
}


def _load_summary(path: Path) -> dict | None:
    candidates = list(path.glob("*__summary.json"))
    if not candidates:
        return None
    return json.loads(candidates[0].read_text())


def _load_long(path: Path) -> pd.DataFrame | None:
    candidates = list(path.glob("*__results_long.csv"))
    if not candidates:
        return None
    return pd.read_csv(candidates[0])


def main() -> int:
    rows: list[dict] = []
    for label, dir_str in TIER_A_BENCHMARKS.items():
        d = Path(dir_str)
        s = _load_summary(d)
        if s is None:
            print(f"[skip] no summary for {label} ({d})")
            continue
        for method, m in s["methods"].items():
            rows.append({
                "benchmark": label,
                "method": method,
                "n": m.get("n"),
                "success": m.get("success_rate"),
                "violation": m.get("violation_rate"),
                "tokens_total": (m.get("tokens_input_mean", 0) + m.get("tokens_output_mean", 0)),
                "delta_success_vs_direct": m.get("delta_success"),
                "ci_low": m.get("delta_success_ci_low"),
                "ci_high": m.get("delta_success_ci_high"),
                "mcnemar_p": m.get("mcnemar_success_p"),
                "wilcoxon_tokens_p": m.get("wilcoxon_tokens_p"),
                "holm_success_adj": m.get("holm_success_p_adj"),
            })
    if not rows:
        print("No completed benchmark summaries found.")
        return 1
    df = pd.DataFrame(rows)
    out_dir = Path("outputs/tier_a")
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "main_table.csv", index=False)

    # Cross-family comparison: Llama vs DeepSeek on PFQABench-Recon.
    llama_df = _load_long(Path("outputs/tier_a/pfqa_llama"))
    ds_df = _load_long(Path("outputs/tier_a/pfqa_deepseek"))
    if llama_df is not None and ds_df is not None:
        cf_rows = []
        common_methods = sorted(set(llama_df["method"]) & set(ds_df["method"]))
        for m in common_methods:
            a = llama_df[llama_df["method"] == m].sort_values(["task_id", "seed"]).reset_index(drop=True)
            b = ds_df[ds_df["method"] == m].sort_values(["task_id", "seed"]).reset_index(drop=True)
            merged = a.merge(b, on=["task_id", "seed"], suffixes=("_llama", "_deepseek"))
            if merged.empty:
                continue
            ci = paired_bootstrap_ci(
                merged["success_llama"].astype(int).tolist(),
                merged["success_deepseek"].astype(int).tolist(),
            )
            mc = mcnemar(
                merged["success_llama"].astype(bool).tolist(),
                merged["success_deepseek"].astype(bool).tolist(),
            )
            cf_rows.append({
                "method": m,
                "llama_success": float(merged["success_llama"].astype(int).mean()),
                "deepseek_success": float(merged["success_deepseek"].astype(int).mean()),
                "delta_deepseek_minus_llama": ci.point,
                "ci_low": ci.low,
                "ci_high": ci.high,
                "mcnemar_p": mc.pvalue,
            })
        cf_df = pd.DataFrame(cf_rows)
        cf_df.to_csv(out_dir / "cross_family.csv", index=False)

    # Markdown headline.
    md = ["# Tier-A Headline Results (draft for §5)\n"]
    md.append("## Per-benchmark main results\n")
    pretty_cols = [
        "benchmark", "method", "n", "success", "violation", "tokens_total",
        "delta_success_vs_direct", "ci_low", "ci_high", "mcnemar_p", "holm_success_adj",
    ]
    md.append(df[pretty_cols].to_markdown(index=False, floatfmt=".3f"))
    md.append("\n")
    if (out_dir / "cross_family.csv").exists():
        md.append("## Cross-family comparison: Llama 3.3 70B → DeepSeek V3 on PFQABench-Recon\n")
        md.append(pd.read_csv(out_dir / "cross_family.csv").to_markdown(index=False, floatfmt=".3f"))
        md.append("\n")
    (out_dir / "headline.md").write_text("\n".join(md))
    print(f"Wrote {out_dir / 'main_table.csv'}, {out_dir / 'headline.md'}")
    print(f"  Methods seen: {sorted(df['method'].unique())}")
    print(f"  Benchmarks aggregated: {sorted(df['benchmark'].unique())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
