"""Generate §5 (Experiments) LaTeX snippet from completed Tier-A runs.

Produces `outputs/tier_a/section5.tex` containing:
  * the per-benchmark main results table (booktabs)
  * the cross-family comparison table
  * stub paragraphs that name actual numbers from the run

Numbers go in §5 only — abstract and intro stay description-level until
the user explicitly opts in to placing measured numbers earlier.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


TIER_A = {
    "PFQABench-Recon (Llama 3.3 70B)":      "outputs/tier_a/pfqa_llama",
    "PFQABench-Recon (Llama 3.1 8B)":       "outputs/tier_a/pfqa_llama3_8b",
    "PFQABench-Recon (DeepSeek V3)":        "outputs/tier_a/pfqa_deepseek",
    "PFQABench-Recon (DeepSeek V3.1)":      "outputs/tier_a/pfqa_deepseek_v31",
    "PFQABench-Recon (gpt-oss-20b)":        "outputs/tier_a/pfqa_gptoss20b",
    "PFQABench-Recon (Mistral Nemo 12B)":   "outputs/tier_a/pfqa_mistral7b",
    "PFQABench-Recon (Gemini 2.5 Flash)":   "outputs/tier_a/pfqa_gemini_flash",
    "PFQABench-Recon (Qwen 2.5 7B)":        "outputs/tier_a/pfqa_qwen7b",
    "TravelPlanner+ Recon (Llama 3.3 70B)": "outputs/tier_a/travel_llama",
    "TauBench-Recon (Llama 3.3 70B)":       "outputs/tier_a/taubench_llama",
}
METHOD_DISPLAY = {
    "direct": "Direct",
    "self_refine": "Self-Refine",
    "reflexion": "Reflexion",
    "full_regen": "Full-Regen",
    "intro_specter_llm": r"\textbf{Intro-Specter}",
}


def _load_summary(d: Path) -> dict | None:
    cs = list(d.glob("*__summary.json"))
    if not cs:
        return None
    return json.loads(cs[0].read_text())


def _fmt_pct(x: float | None) -> str:
    if x is None:
        return "--"
    return f"{x * 100:.1f}"


def _fmt_p(x: float | None) -> str:
    if x is None:
        return "--"
    if x < 0.001:
        return r"\textless 0.001"
    return f"{x:.3f}"


def _main_table_tex() -> str:
    rows = []
    for label, dir_str in TIER_A.items():
        s = _load_summary(Path(dir_str))
        if s is None:
            continue
        for method, m in s["methods"].items():
            rows.append({
                "benchmark": label,
                "method": METHOD_DISPLAY.get(method, method),
                "success": _fmt_pct(m.get("success_rate")),
                "violation": _fmt_pct(m.get("violation_rate")),
                "tokens": int(m.get("tokens_input_mean", 0) + m.get("tokens_output_mean", 0)),
                "delta": _fmt_pct(m.get("delta_success")),
                "ci_low": _fmt_pct(m.get("delta_success_ci_low")),
                "ci_high": _fmt_pct(m.get("delta_success_ci_high")),
                "p_holm": _fmt_p(m.get("holm_success_p_adj")),
            })
    if not rows:
        return "% no rows; aggregate after runs complete\n"
    df = pd.DataFrame(rows)
    out = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Tier-A main results. $\Delta$success is success rate vs.\ \textsc{Direct} on paired (task, seed) data. CIs are 10K-resample paired bootstrap. $p$-values are Holm-Bonferroni-adjusted across the (method $\times$ metric) family.}",
        r"\label{tab:tier-a-main}",
        r"\small",
        r"\begin{tabular}{llrrrrrr}",
        r"\toprule",
        r"Benchmark & Method & Success (\%) & Violation (\%) & Tokens & $\Delta$Success (\%) & 95\% CI (\%) & Holm $p$ \\",
        r"\midrule",
    ]
    cur_bench = None
    for _, r in df.iterrows():
        bench = r["benchmark"] if r["benchmark"] != cur_bench else ""
        cur_bench = r["benchmark"]
        out.append(
            f"{bench} & {r['method']} & {r['success']} & {r['violation']} & {r['tokens']} & {r['delta']} & "
            f"[{r['ci_low']}, {r['ci_high']}] & {r['p_holm']} \\\\"
        )
    out.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    return "\n".join(out) + "\n"


def _cross_family_tex() -> str:
    cf_path = Path("outputs/tier_a/cross_family.csv")
    if not cf_path.exists():
        return "% cross_family.csv not found\n"
    df = pd.read_csv(cf_path)
    if df.empty:
        return "% empty cross_family.csv\n"
    out = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Cross-family comparison on PFQABench-Recon: Llama 3.3 70B Instruct Turbo vs.\ DeepSeek V3, paired by (task, seed). Independent training pipelines (Meta vs.\ DeepSeek) provide a genuine cross-family check.}",
        r"\label{tab:cross-family}",
        r"\small",
        r"\begin{tabular}{lrrrrr}",
        r"\toprule",
        r"Method & Llama (\%) & DeepSeek (\%) & $\Delta$ (\%) & 95\% CI (\%) & McNemar $p$ \\",
        r"\midrule",
    ]
    for _, r in df.iterrows():
        out.append(
            f"{METHOD_DISPLAY.get(r['method'], r['method'])} & "
            f"{_fmt_pct(r['llama_success'])} & {_fmt_pct(r['deepseek_success'])} & "
            f"{_fmt_pct(r['delta_deepseek_minus_llama'])} & "
            f"[{_fmt_pct(r['ci_low'])}, {_fmt_pct(r['ci_high'])}] & "
            f"{_fmt_p(r['mcnemar_p'])} \\\\"
        )
    out.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    return "\n".join(out) + "\n"


def _prose_template() -> str:
    """A neutral §5 paragraph stub. The user fills in the headline-result
    sentence after eyeballing the actual numbers — the script does not embed
    direction-of-result claims."""
    return r"""\subsection{Results}

Table~\ref{tab:tier-a-main} summarises Tier-A success and violation rates per
method across PFQABench-Recon, TravelPlanner+ Recon, and TauBench-Recon. All
methods share the agent-priming step (one Llama 3.3 70B call per
\ensuremath{(\text{task},\text{seed})} pair), so the per-method token figures
reflect only the additional cost incurred by that method's correction
pipeline. Paired bootstrap CIs and Holm-Bonferroni-adjusted McNemar $p$-values
are computed against the \textsc{Direct} baseline on the same
\ensuremath{(\text{task},\text{seed})} pairs.

Table~\ref{tab:cross-family} reports the cross-family slice on
PFQABench-Recon, comparing Llama 3.3 70B (the headline workhorse) with
DeepSeek V3 (an independently trained model). The two models share neither
weights nor training pipeline; consistent gains across the pair would
indicate that Intro-Specter's improvements are not Llama-specific.

% TODO(user): write the headline interpretation sentence after inspecting
% the table values; do not auto-generate direction-of-result claims.
"""


def main() -> int:
    out = []
    out.append("% Auto-generated by scripts/generate_section5.py")
    out.append("% Re-run after changes to the headline data.")
    out.append("")
    out.append(_prose_template())
    out.append(_main_table_tex())
    out.append(_cross_family_tex())
    Path("outputs/tier_a").mkdir(parents=True, exist_ok=True)
    Path("outputs/tier_a/section5.tex").write_text("\n".join(out))
    print("Wrote outputs/tier_a/section5.tex")
    return 0


if __name__ == "__main__":
    sys.exit(main())
