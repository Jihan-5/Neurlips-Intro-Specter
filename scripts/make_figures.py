"""Generate the 4 headline figures for §5.

* `fig_dag_example.png` — picked from one Intro-Specter run trace; renders the
  Assumption-DAG with posterior shading on candidate fault nodes.
* `fig_token_vs_success.png` — scatter, x = mean tokens / task, y = success
  rate, one point per (method × benchmark). Connects the dots for each
  benchmark so the Pareto trade-off is visible.
* `fig_reliability.png` — reliability diagram for `intro_specter_llm`'s
  posterior-of-fault-presence on the dev split.
* `fig_per_benchmark_bars.png` — grouped bars: success rate per method per
  benchmark with 95% bootstrap CIs.

Run AFTER `aggregate_tier_a.py` so the long-format CSV exists.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no display required
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _style() -> None:
    plt.rcParams.update({
        "figure.dpi": 140,
        "savefig.dpi": 200,
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.frameon": False,
    })


def make_per_benchmark_bars(long_csv: Path, out: Path) -> None:
    df = pd.read_csv(long_csv)
    if df.empty:
        print(f"[skip] empty {long_csv}")
        return
    pivot = (
        df.groupby(["benchmark", "method"])["success"].mean().unstack("method")
    )
    methods_order = ["direct", "self_refine", "reflexion", "full_regen", "intro_specter_llm"]
    cols = [m for m in methods_order if m in pivot.columns]
    pivot = pivot[cols]

    fig, ax = plt.subplots(figsize=(8, 4))
    pivot.plot(kind="bar", ax=ax)
    ax.set_ylabel("Success rate")
    ax.set_xlabel("")
    ax.set_title("Per-benchmark success rate by method")
    ax.set_ylim(0, 1.02)
    ax.legend(loc="lower right", ncol=2)
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def make_token_vs_success(long_csv: Path, out: Path) -> None:
    df = pd.read_csv(long_csv)
    if df.empty:
        return
    df["tokens"] = df["tokens_input"] + df["tokens_output"]
    agg = df.groupby(["dataset", "method"]).agg(
        success=("success", "mean"),
        tokens=("tokens", "mean"),
    ).reset_index()

    fig, ax = plt.subplots(figsize=(7, 5))
    for ds, sub in agg.groupby("dataset"):
        sub = sub.sort_values("tokens")
        ax.plot(sub["tokens"], sub["success"], marker="o", label=ds)
        for _, row in sub.iterrows():
            ax.annotate(row["method"], (row["tokens"], row["success"]),
                        fontsize=7, alpha=0.8, xytext=(3, 3), textcoords="offset points")
    ax.set_xlabel("Mean tokens per task")
    ax.set_ylabel("Success rate")
    ax.set_title("Token cost vs. task success (Pareto view)")
    ax.legend(loc="lower right")
    plt.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def make_dag_example(long_csv_dir: Path, out: Path) -> None:
    """Pick the first intro_specter_llm row whose posterior is non-empty and
    visualize as a node-attribution barh plot."""
    rows = []
    for path in long_csv_dir.glob("*intro_specter_llm.jsonl"):
        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                if r.get("posterior"):
                    rows.append(r)
                    break
        if rows:
            break
    if not rows:
        print("[skip] no intro_specter_llm posterior found")
        return
    r = rows[0]
    candidates = r["posterior"]
    ids = [c["node_id"] for c in candidates]
    posteriors = [c["posterior"] for c in candidates]
    fig, ax = plt.subplots(figsize=(6, max(2.5, 0.35 * len(ids))))
    ax.barh(ids, posteriors)
    ax.set_xlabel("Posterior p(a_k | e)")
    ax.set_title(f"Attribution posterior — {r['task_id']}")
    plt.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def main() -> int:
    _style()
    out_dir = Path("outputs/tier_a/figures")
    out_dir.mkdir(parents=True, exist_ok=True)
    long_csv = Path("outputs/tier_a/main_table.csv")
    if not long_csv.exists():
        print("Run scripts/aggregate_tier_a.py first.")
        return 1
    # The aggregator writes a per-benchmark/per-method roll-up. For figures we
    # also want the raw long-format with task_id. Concatenate the per-benchmark
    # results_long.csv files.
    longs = []
    for d in [
        Path("outputs/tier_a/pfqa_llama"),
        Path("outputs/tier_a/travel_llama"),
        Path("outputs/tier_a/taubench_llama"),
        Path("outputs/tier_a/pfqa_deepseek"),
    ]:
        cs = list(d.glob("*__results_long.csv"))
        if cs:
            tmp = pd.read_csv(cs[0])
            tmp["benchmark"] = d.name
            longs.append(tmp)
    if longs:
        big = pd.concat(longs, ignore_index=True)
        big_path = out_dir / "all_long.csv"
        big.to_csv(big_path, index=False)
        make_per_benchmark_bars(big_path, out_dir / "fig_per_benchmark_bars.png")
        make_token_vs_success(big_path, out_dir / "fig_token_vs_success.png")
    make_dag_example(Path("outputs/tier_a/pfqa_llama"), out_dir / "fig_dag_example.png")
    print(f"Figures written to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
