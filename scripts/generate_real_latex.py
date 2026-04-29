"""Generate LaTeX booktabs tables from the aggregated real-benchmark CSVs.

Outputs to `outputs/real/tables/*.tex` — one .tex file per paper table:

* `table1_main_results.tex`         — Dataset × Method success matrix.
                                       Bold per-row best, * for Holm-sig vs
                                       Direct, † for Holm-sig vs Reflexion.
* `table2_head_to_head.tex`         — IS vs each baseline summary.
* `table3_attribution.tex`          — Top-1 / top-3 / MRR (IS only).
* `table4_token_cost.tex`           — Tokens per method per dataset.
* `table5_profile_violation.tex`    — Profile-violation rate per cell.

Each .tex file is self-contained and \\input{}-able from main.tex.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


METHOD_ORDER = [
    "direct", "react", "self_refine", "reflexion",
    "tot", "selfcheckgpt", "full_regen", "intro_specter_llm",
]
METHOD_LABELS = {
    "direct": "Direct",
    "react": "ReAct",
    "self_refine": "Self-Refine",
    "reflexion": "Reflexion",
    "tot": "ToT",
    "selfcheckgpt": "SelfCheckGPT",
    "full_regen": "Full-Regen",
    "intro_specter_llm": "\\textsc{Intro-Specter}",
}
DATASET_LABELS = {
    "hotpotqa_real":     "Real-HotpotQA",
    "truthfulqa_real":   "Real-TruthfulQA",
    "strategyqa_real":   "Real-StrategyQA",
    "travelplanner_real":"Real-TravelPlanner",
}


def _fmt(x: float) -> str:
    if pd.isna(x):
        return "--"
    return f"{x*100:.1f}"


def table1_main(main_t: pd.DataFrame, h2h: pd.DataFrame, out: Path) -> None:
    if main_t.empty:
        return
    sig_vs = {}
    if not h2h.empty and "p_holm" in h2h.columns:
        for _, r in h2h.iterrows():
            key = (r["dataset"], r["model"], r["baseline"])
            sig_vs[key] = (bool(r.get("p_holm", 1.0) < 0.05), float(r["delta"]))

    lines = ["\\begin{tabular}{ll" + "c" * len(METHOD_ORDER) + "}", "\\toprule"]
    header = " & ".join(["Dataset", "Model"] + [METHOD_LABELS[m] for m in METHOD_ORDER]) + " \\\\"
    lines.append(header)
    lines.append("\\midrule")

    for ds in sorted(main_t["dataset"].unique()):
        for mdl in sorted(main_t["model"].unique()):
            sub = main_t[(main_t["dataset"] == ds) & (main_t["model"] == mdl)]
            if sub.empty:
                continue
            cells = []
            successes = []
            for m in METHOD_ORDER:
                col = f"{m}_success"
                v = sub[col].dropna().iloc[0] if col in sub.columns and not sub[col].dropna().empty else float("nan")
                successes.append(v)
            best_idx = max(range(len(successes)),
                           key=lambda i: (successes[i] if not pd.isna(successes[i]) else -1))
            for i, (m, v) in enumerate(zip(METHOD_ORDER, successes)):
                s = _fmt(v)
                if i == best_idx and not pd.isna(v):
                    s = f"\\textbf{{{s}}}"
                # Mark significance against direct and reflexion when this method is IS.
                if m == "intro_specter_llm":
                    sig_d = sig_vs.get((ds, mdl, "direct"), (False, 0.0))
                    sig_r = sig_vs.get((ds, mdl, "reflexion"), (False, 0.0))
                    if sig_d[0] and sig_d[1] > 0:
                        s += "$^{*}$"
                    if sig_r[0] and sig_r[1] > 0:
                        s += "$^{\\dagger}$"
                cells.append(s)
            lines.append(" & ".join([DATASET_LABELS.get(ds, ds), mdl] + cells) + " \\\\")
        lines.append("\\midrule")
    if lines[-1] == "\\midrule":
        lines.pop()
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    out.write_text("\n".join(lines))


def table2_head_to_head(h2h: pd.DataFrame, out: Path) -> None:
    if h2h.empty:
        return
    base_order = ["direct", "react", "self_refine", "reflexion", "tot", "selfcheckgpt", "full_regen"]
    rows = []
    for b in base_order:
        sub = h2h[h2h["baseline"] == b]
        if sub.empty:
            continue
        n_total = len(sub)
        n_win = int(((sub["delta"] > 0) & (sub.get("holm_reject", False).fillna(False))).sum())
        n_lose = int(((sub["delta"] < 0) & (sub.get("holm_reject", False).fillna(False))).sum())
        n_tie = n_total - n_win - n_lose
        mean_d = float(sub["delta"].mean()) * 100
        rows.append((METHOD_LABELS[b], n_win, n_tie, n_lose, n_total, mean_d))
    lines = ["\\begin{tabular}{lccccc}", "\\toprule"]
    lines.append("Baseline & IS wins & ties / NS & IS loses & total cells & mean $\\Delta$ (\\%) \\\\")
    lines.append("\\midrule")
    for r in rows:
        lines.append(f"{r[0]} & {r[1]} & {r[2]} & {r[3]} & {r[4]} & {r[5]:+.1f} \\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    out.write_text("\n".join(lines))


def table3_attribution(attr: pd.DataFrame, out: Path) -> None:
    if attr.empty:
        return
    lines = ["\\begin{tabular}{llcccc}", "\\toprule"]
    lines.append("Dataset & Model & $n$ & top-1 & top-3 & MRR \\\\")
    lines.append("\\midrule")
    for _, r in attr.iterrows():
        lines.append(
            f"{DATASET_LABELS.get(r['dataset'], r['dataset'])} & {r['model']} & "
            f"{int(r['n'])} & {r['top1']*100:.1f} & {r['top3']*100:.1f} & {r['mrr']:.3f} \\\\"
        )
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    out.write_text("\n".join(lines))


def table4_token_cost(tok: pd.DataFrame, out: Path) -> None:
    if tok.empty:
        return
    pivot = tok.pivot(index="method", columns="dataset", values="mean_tokens")
    pivot = pivot.reindex([m for m in METHOD_ORDER if m in pivot.index])
    lines = ["\\begin{tabular}{l" + "c" * len(pivot.columns) + "}", "\\toprule"]
    cols = [DATASET_LABELS.get(c, c) for c in pivot.columns]
    lines.append("Method & " + " & ".join(cols) + " \\\\")
    lines.append("\\midrule")
    for m in pivot.index:
        row = [METHOD_LABELS[m]] + [f"{v:,.0f}" if pd.notna(v) else "--" for v in pivot.loc[m]]
        lines.append(" & ".join(row) + " \\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    out.write_text("\n".join(lines))


def table5_profile_violation(pvr: pd.DataFrame, out: Path) -> None:
    if pvr.empty:
        return
    pivot = pvr.pivot(index="method", columns="dataset", values="profile_violation_rate")
    pivot = pivot.reindex([m for m in METHOD_ORDER if m in pivot.index])
    lines = ["\\begin{tabular}{l" + "c" * len(pivot.columns) + "}", "\\toprule"]
    cols = [DATASET_LABELS.get(c, c) for c in pivot.columns]
    lines.append("Method & " + " & ".join(cols) + " \\\\")
    lines.append("\\midrule")
    for m in pivot.index:
        row = [METHOD_LABELS[m]] + [f"{v*100:.1f}\\%" if pd.notna(v) else "--" for v in pivot.loc[m]]
        lines.append(" & ".join(row) + " \\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    out.write_text("\n".join(lines))


def main() -> int:
    tables = Path("outputs/real/tables")
    if not tables.exists():
        print(f"Run aggregate_real_benchmarks.py first.")
        return 1
    main_t = pd.read_csv(tables / "main_table.csv") if (tables / "main_table.csv").exists() else pd.DataFrame()
    h2h = pd.read_csv(tables / "head_to_head.csv") if (tables / "head_to_head.csv").exists() else pd.DataFrame()
    attr = pd.read_csv(tables / "attribution.csv") if (tables / "attribution.csv").exists() else pd.DataFrame()
    tok = pd.read_csv(tables / "token_cost.csv") if (tables / "token_cost.csv").exists() else pd.DataFrame()
    pvr = pd.read_csv(tables / "profile_violation.csv") if (tables / "profile_violation.csv").exists() else pd.DataFrame()

    table1_main(main_t, h2h, tables / "table1_main_results.tex")
    table2_head_to_head(h2h, tables / "table2_head_to_head.tex")
    table3_attribution(attr, tables / "table3_attribution.tex")
    table4_token_cost(tok, tables / "table4_token_cost.tex")
    table5_profile_violation(pvr, tables / "table5_profile_violation.tex")

    print(f"Wrote 5 LaTeX tables to {tables}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
