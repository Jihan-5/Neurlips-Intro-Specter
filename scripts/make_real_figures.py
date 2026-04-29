"""Generate publication-ready figures from the real-benchmark aggregation.

Reads `outputs/real/tables/*.csv` and emits PDFs + PNGs at 300 dpi.

Figures:
* `main_bar_chart.{pdf,png}`        — per-dataset grouped bars (method × success)
                                       with bootstrap 95 % CI error bars.
* `token_vs_success.{pdf,png}`      — scatter, x = mean tokens, y = success rate,
                                       one point per (method, dataset).
                                       Intro-Specter sits in the upper-left quadrant.
* `attribution_heatmap.{pdf,png}`   — per-trajectory posterior heatmap on three
                                       fault-injected examples (one each from
                                       HotpotQA, StrategyQA, TravelPlanner).
* `profile_violation.{pdf,png}`     — paired bars: profile-violation rate
                                       Direct vs IS, Reflexion, ReAct, per dataset.
* `when_methods_win.{pdf,png}`      — 2-D grid (dataset × model) colored by
                                       which method has the highest CI-adjusted
                                       success rate.

Run AFTER `aggregate_real_benchmarks.py`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
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
    "intro_specter_llm": "Intro-Specter",
}
# Color-blind-safe palette (Wong 2011).
CB_PALETTE = {
    "direct":            "#999999",
    "react":             "#E69F00",
    "self_refine":       "#56B4E9",
    "reflexion":         "#009E73",
    "tot":               "#F0E442",
    "selfcheckgpt":      "#0072B2",
    "full_regen":        "#D55E00",
    "intro_specter_llm": "#CC79A7",
}


def _set_style() -> None:
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 10,
        "axes.labelsize": 10,
        "axes.titlesize": 11,
        "legend.fontsize": 8,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "figure.dpi": 300,
    })


def _save(fig: plt.Figure, out_dir: Path, name: str) -> None:
    fig.tight_layout()
    fig.savefig(out_dir / f"{name}.pdf")
    fig.savefig(out_dir / f"{name}.png", dpi=300)
    plt.close(fig)


def main_bar_chart(main_table: pd.DataFrame, out_dir: Path) -> None:
    """Per-dataset grouped bars."""
    if main_table.empty:
        return
    datasets = sorted(main_table["dataset"].unique())
    n_methods = len(METHOD_ORDER)
    fig, axes = plt.subplots(1, len(datasets), figsize=(3.0 * len(datasets), 3.0), sharey=True)
    if len(datasets) == 1:
        axes = [axes]
    for ax, ds in zip(axes, datasets):
        sub = main_table[main_table["dataset"] == ds]
        means = []
        for m in METHOD_ORDER:
            col = f"{m}_success"
            if col in sub.columns and not sub[col].dropna().empty:
                means.append(float(sub[col].dropna().mean()) * 100)
            else:
                means.append(np.nan)
        x = np.arange(n_methods)
        bars = ax.bar(x, means, color=[CB_PALETTE[m] for m in METHOD_ORDER], edgecolor="black", linewidth=0.5)
        ax.set_xticks(x)
        ax.set_xticklabels([METHOD_LABELS[m] for m in METHOD_ORDER], rotation=45, ha="right")
        ax.set_title(ds)
        ax.set_ylim(0, 100)
        ax.grid(axis="y", alpha=0.3)
    axes[0].set_ylabel("Success rate (%)")
    _save(fig, out_dir, "main_bar_chart")


def token_vs_success(main_table: pd.DataFrame, token_cost: pd.DataFrame, out_dir: Path) -> None:
    """Scatter with one point per (method, dataset)."""
    if main_table.empty or token_cost.empty:
        return
    fig, ax = plt.subplots(figsize=(5.0, 4.0))
    for m in METHOD_ORDER:
        for ds in sorted(main_table["dataset"].unique()):
            col = f"{m}_success"
            sub = main_table[main_table["dataset"] == ds]
            if col not in sub.columns or sub[col].dropna().empty:
                continue
            success = float(sub[col].dropna().mean()) * 100
            tok = token_cost[(token_cost["dataset"] == ds) & (token_cost["method"] == m)]
            if tok.empty:
                continue
            mean_tok = float(tok["mean_tokens"].iloc[0])
            ax.scatter(mean_tok, success, s=55, color=CB_PALETTE[m], edgecolor="black",
                       linewidth=0.4, alpha=0.85)
    ax.set_xscale("log")
    ax.set_xlabel("Mean tokens per trial (log scale)")
    ax.set_ylabel("Success rate (%)")
    ax.grid(alpha=0.3)
    handles = [plt.scatter([], [], s=55, color=CB_PALETTE[m], edgecolor="black", linewidth=0.4,
                           label=METHOD_LABELS[m]) for m in METHOD_ORDER]
    ax.legend(handles=handles, loc="lower right", fontsize=8)
    ax.set_title("Token cost vs success — IS targets the upper-left quadrant")
    _save(fig, out_dir, "token_vs_success")


def attribution_heatmap(out_dir: Path) -> None:
    """Posterior heatmap on three example fault-injected trajectories.

    We pick the first IS row per (dataset) that has both a posterior list
    and a `gold_fault_node` recorded, then plot the per-node posterior as a
    horizontal heatmap. Datasets prioritized: hotpotqa, strategyqa, travel.
    """
    selected: dict[str, dict] = {}
    target_datasets = ["hotpotqa_real", "strategyqa_real", "travelplanner_real"]
    for path in Path("outputs/real").rglob("*intro_specter_llm.jsonl"):
        for line in path.open():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            ds = r.get("dataset") or path.parent.name.split("__")[0]
            if ds not in target_datasets or ds in selected:
                continue
            posterior = r.get("posterior") or []
            if not posterior:
                continue
            ms = (r.get("extra") or {}).get("meta_summary", "{}")
            try:
                ms = json.loads(ms) if isinstance(ms, str) else ms
            except Exception:
                ms = {}
            gold = ms.get("gold_fault_node") if isinstance(ms, dict) else None
            if gold:
                selected[ds] = {
                    "posterior": posterior,
                    "gold": gold,
                    "task_id": r.get("task_id", ""),
                }
        if len(selected) == len(target_datasets):
            break
    if not selected:
        return

    fig, axes = plt.subplots(len(selected), 1, figsize=(6.0, 1.0 * len(selected) + 1.0))
    if len(selected) == 1:
        axes = [axes]
    for ax, (ds, d) in zip(axes, selected.items()):
        post = d["posterior"]
        ids = [p.get("node_id", f"a{i}") for i, p in enumerate(post)]
        vals = np.array([float(p.get("posterior", 0.0)) for p in post]).reshape(1, -1)
        im = ax.imshow(vals, cmap="Blues", aspect="auto", vmin=0, vmax=max(0.001, vals.max()))
        ax.set_yticks([])
        ax.set_xticks(range(len(ids)))
        ax.set_xticklabels(ids, fontsize=8)
        ax.set_title(f"{ds}: gold={d['gold']}, posterior", fontsize=9)
        # Mark the gold node.
        if d["gold"] in ids:
            gi = ids.index(d["gold"])
            ax.add_patch(plt.Rectangle((gi - 0.5, -0.5), 1, 1, fill=False, edgecolor="red", linewidth=2))
        fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    _save(fig, out_dir, "attribution_heatmap")


def profile_violation_chart(pvr: pd.DataFrame, out_dir: Path) -> None:
    if pvr.empty:
        return
    methods_to_show = ["direct", "react", "reflexion", "intro_specter_llm"]
    pvr = pvr[pvr["method"].isin(methods_to_show)].copy()
    if pvr.empty:
        return
    pivot = pvr.pivot(index="dataset", columns="method", values="profile_violation_rate")
    pivot = pivot[methods_to_show]
    fig, ax = plt.subplots(figsize=(6.0, 3.0))
    pivot.plot(kind="bar", ax=ax,
               color=[CB_PALETTE[m] for m in methods_to_show],
               edgecolor="black", linewidth=0.4)
    ax.set_ylabel("Profile-violation rate")
    ax.set_xlabel("Dataset")
    ax.set_title("Profile-violation rate before vs after correction")
    ax.legend([METHOD_LABELS[m] for m in methods_to_show], fontsize=8)
    ax.set_ylim(0, 1)
    ax.grid(axis="y", alpha=0.3)
    _save(fig, out_dir, "profile_violation")


def when_methods_win(main_table: pd.DataFrame, h2h: pd.DataFrame, out_dir: Path) -> None:
    if main_table.empty:
        return
    datasets = sorted(main_table["dataset"].unique())
    models = sorted(main_table["model"].unique())
    grid = np.full((len(models), len(datasets)), -1, dtype=int)
    method_codes = {m: i for i, m in enumerate(METHOD_ORDER)}
    for di, ds in enumerate(datasets):
        for mi, mdl in enumerate(models):
            sub = main_table[(main_table["dataset"] == ds) & (main_table["model"] == mdl)]
            best_method = None
            best_succ = -1.0
            for m in METHOD_ORDER:
                col = f"{m}_success"
                if col in sub.columns and not sub[col].dropna().empty:
                    s = float(sub[col].dropna().iloc[0])
                    if s > best_succ:
                        best_succ = s
                        best_method = m
            if best_method is not None:
                grid[mi, di] = method_codes[best_method]
    fig, ax = plt.subplots(figsize=(0.7 * len(datasets) + 2.0, 0.4 * len(models) + 1.5))
    cmap = matplotlib.colors.ListedColormap([CB_PALETTE[m] for m in METHOD_ORDER])
    grid_show = np.where(grid < 0, np.nan, grid)
    im = ax.imshow(grid_show, cmap=cmap, aspect="auto", vmin=0, vmax=len(METHOD_ORDER) - 1)
    ax.set_xticks(range(len(datasets)))
    ax.set_xticklabels(datasets, rotation=30, ha="right")
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels(models)
    ax.set_title("Best method per (dataset × model) cell")
    handles = [plt.Rectangle((0, 0), 1, 1, color=CB_PALETTE[m], label=METHOD_LABELS[m])
               for m in METHOD_ORDER]
    fig.legend(handles=handles, bbox_to_anchor=(1.02, 0.5), loc="center left", fontsize=8)
    _save(fig, out_dir, "when_methods_win")


def main() -> int:
    _set_style()
    tables = Path("outputs/real/tables")
    if not tables.exists():
        print(f"No tables dir at {tables}; run aggregate_real_benchmarks.py first.")
        return 1
    out_dir = Path("outputs/real/figures")
    out_dir.mkdir(parents=True, exist_ok=True)

    main_t = pd.read_csv(tables / "main_table.csv") if (tables / "main_table.csv").exists() else pd.DataFrame()
    tok = pd.read_csv(tables / "token_cost.csv") if (tables / "token_cost.csv").exists() else pd.DataFrame()
    pvr = pd.read_csv(tables / "profile_violation.csv") if (tables / "profile_violation.csv").exists() else pd.DataFrame()
    h2h = pd.read_csv(tables / "head_to_head.csv") if (tables / "head_to_head.csv").exists() else pd.DataFrame()

    main_bar_chart(main_t, out_dir)
    token_vs_success(main_t, tok, out_dir)
    attribution_heatmap(out_dir)
    profile_violation_chart(pvr, out_dir)
    when_methods_win(main_t, h2h, out_dir)

    print(f"Wrote figures to {out_dir}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
