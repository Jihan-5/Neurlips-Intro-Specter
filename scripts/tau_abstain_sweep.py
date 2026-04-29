"""Post-hoc τ_abstain calibration sweep across all Intro-Specter cells.

Reads every `*__intro_specter*.jsonl` produced by Tier-A/B runs (which were
all executed at τ_abstain=0, i.e. always-commit). For each row, the
`posterior` field gives the per-candidate-fault probabilities; we use
`max(posterior)` as the model's confidence in its top fault attribution
(or, equivalently, its "confidence to commit").

For each τ in a grid we re-interpret the same data:
  * IF max(posterior) >= τ → the agent commits its repair; we use the
    recorded `success` from the JSONL.
  * IF max(posterior) <  τ → the agent ABSTAINS; success is undefined for
    coverage purposes (we exclude from selective accuracy and add to the
    abstained pile).

Outputs:
  * `outputs/tier_a/calibration/risk_coverage.csv`   — per-cell, per-τ row
  * `outputs/tier_a/calibration/calibration.csv`     — per-cell ECE + Brier
  * `outputs/tier_a/calibration/risk_coverage.png`   — averaged curve
  * `outputs/tier_a/calibration/reliability.png`     — reliability diagram

This is post-hoc (τ chosen on the same split it's evaluated on) and is
labelled as such in the paper. A clean held-out variant requires a
separate val-split run; we report this analysis as the operating-point
trade-off curve.
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

from intro_specter.metrics.calibration import (
    brier_score,
    expected_calibration_error,
)


TAU_GRID = np.linspace(0.0, 1.0, 21)


def _iter_is_jsonls() -> list[Path]:
    paths: list[Path] = []
    for parent in [Path("outputs/tier_a"), Path("outputs/tier_b")]:
        if not parent.exists():
            continue
        for path in parent.rglob("*intro_specter_llm.jsonl"):
            paths.append(path)
    return sorted(paths)


def _load_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.open():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _max_posterior(row: dict) -> float | None:
    """Return max posterior probability, or None if no posterior was computed.

    Rows where no violation was detected have an empty posterior list; we
    treat those as 'high-confidence commits' (max=1.0) since the agent
    chose to commit without needing a repair.
    """
    posterior = row.get("posterior", []) or []
    if not posterior:
        return 1.0
    try:
        return max(float(p.get("posterior", 0.0)) for p in posterior)
    except (TypeError, ValueError):
        return None


def _per_cell(rows: list[dict]) -> dict:
    confs: list[float] = []
    succs: list[int] = []
    for r in rows:
        c = _max_posterior(r)
        if c is None:
            continue
        confs.append(float(c))
        succs.append(int(bool(r.get("success", False))))
    if not confs:
        return {}
    confs_arr = np.asarray(confs)
    succs_arr = np.asarray(succs)

    sweep_rows = []
    for tau in TAU_GRID:
        commit_mask = confs_arr >= tau
        n_total = len(confs_arr)
        n_commit = int(commit_mask.sum())
        coverage = n_commit / n_total
        selective_acc = float(succs_arr[commit_mask].mean()) if n_commit else float("nan")
        sweep_rows.append({
            "tau": float(tau),
            "n_total": n_total,
            "n_commit": n_commit,
            "coverage": coverage,
            "selective_accuracy": selective_acc,
        })
    ece = expected_calibration_error(confs_arr.tolist(), succs_arr.tolist(), n_bins=10)
    brier = brier_score(confs_arr.tolist(), succs_arr.tolist())

    return {
        "sweep": sweep_rows,
        "ece": ece,
        "brier": brier,
        "n": len(confs_arr),
        "mean_confidence": float(confs_arr.mean()),
        "mean_success": float(succs_arr.mean()),
        "raw_conf": confs_arr,
        "raw_succ": succs_arr,
    }


def _plot_risk_coverage(per_cell: dict[str, dict], out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=150)
    all_curves = []
    for label, data in per_cell.items():
        sw = pd.DataFrame(data["sweep"])
        ax.plot(sw["coverage"], sw["selective_accuracy"], alpha=0.18, color="grey", linewidth=0.7)
        all_curves.append(sw)
    if all_curves:
        merged = pd.concat(all_curves, ignore_index=True)
        agg = merged.groupby("tau").agg(
            coverage=("coverage", "mean"),
            selective_accuracy=("selective_accuracy", "mean"),
        ).reset_index()
        ax.plot(agg["coverage"], agg["selective_accuracy"],
                color="C0", linewidth=2.4, label=f"Mean across {len(per_cell)} cells")
    ax.set_xlabel("Coverage (fraction committed)")
    ax.set_ylabel("Selective accuracy on committed")
    ax.set_xlim(0, 1.02)
    ax.set_ylim(0, 1.02)
    ax.grid(alpha=0.3)
    ax.legend(loc="lower left", fontsize=9)
    ax.set_title("Selective risk–coverage curve (Intro-Specter, τ_abstain sweep)")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def _plot_reliability(per_cell: dict[str, dict], out_path: Path) -> None:
    all_conf = np.concatenate([d["raw_conf"] for d in per_cell.values() if len(d.get("raw_conf", []))])
    all_succ = np.concatenate([d["raw_succ"] for d in per_cell.values() if len(d.get("raw_succ", []))])
    if len(all_conf) == 0:
        return
    bins = np.linspace(0, 1, 11)
    centers, accs, confs, counts = [], [], [], []
    for i in range(len(bins) - 1):
        lo, hi = bins[i], bins[i + 1]
        mask = (all_conf >= lo) & (all_conf <= hi) if i == 0 else (all_conf > lo) & (all_conf <= hi)
        if not mask.any():
            continue
        centers.append((lo + hi) / 2)
        accs.append(float(all_succ[mask].mean()))
        confs.append(float(all_conf[mask].mean()))
        counts.append(int(mask.sum()))

    fig, ax = plt.subplots(figsize=(5, 5), dpi=150)
    ax.plot([0, 1], [0, 1], "--", color="grey", alpha=0.6, label="Perfect calibration")
    if centers:
        ax.bar(centers, accs, width=0.085, color="C0", edgecolor="black",
               alpha=0.8, label="Empirical accuracy")
    ax.set_xlabel("Predicted confidence (max posterior)")
    ax.set_ylabel("Empirical success rate")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(alpha=0.3)
    ece_avg = expected_calibration_error(all_conf.tolist(), all_succ.tolist(), n_bins=10)
    brier_avg = brier_score(all_conf.tolist(), all_succ.tolist())
    ax.set_title(f"Reliability diagram (pooled): ECE = {ece_avg:.3f}, Brier = {brier_avg:.3f}")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def main() -> int:
    paths = _iter_is_jsonls()
    if not paths:
        print("No intro_specter JSONLs found.")
        return 0

    per_cell: dict[str, dict] = {}
    for path in paths:
        cell = path.parent.name
        rows = _load_rows(path)
        if not rows:
            continue
        # Aggregate across seeds for the same cell.
        if cell in per_cell:
            existing = per_cell[cell]
            new = _per_cell(rows)
            if not new:
                continue
            existing["raw_conf"] = np.concatenate([existing["raw_conf"], new["raw_conf"]])
            existing["raw_succ"] = np.concatenate([existing["raw_succ"], new["raw_succ"]])
            existing["n"] += new["n"]
        else:
            per_cell[cell] = _per_cell(rows)

    # Recompute per-cell sweeps + ECE/Brier on the merged arrays.
    for cell, data in per_cell.items():
        if not data:
            continue
        confs_arr = data["raw_conf"]
        succs_arr = data["raw_succ"]
        sweep_rows = []
        for tau in TAU_GRID:
            commit_mask = confs_arr >= tau
            n_total = len(confs_arr)
            n_commit = int(commit_mask.sum())
            sweep_rows.append({
                "tau": float(tau),
                "n_total": n_total,
                "n_commit": n_commit,
                "coverage": n_commit / n_total if n_total else float("nan"),
                "selective_accuracy": float(succs_arr[commit_mask].mean()) if n_commit else float("nan"),
            })
        data["sweep"] = sweep_rows
        data["ece"] = expected_calibration_error(confs_arr.tolist(), succs_arr.tolist(), n_bins=10)
        data["brier"] = brier_score(confs_arr.tolist(), succs_arr.tolist())
        data["n"] = len(confs_arr)
        data["mean_confidence"] = float(confs_arr.mean())
        data["mean_success"] = float(succs_arr.mean())

    out_dir = Path("outputs/tier_a/calibration")
    out_dir.mkdir(parents=True, exist_ok=True)

    sweep_rows: list[dict] = []
    cal_rows: list[dict] = []
    for cell, data in per_cell.items():
        if not data:
            continue
        for r in data["sweep"]:
            sweep_rows.append({"cell": cell, **r})
        cal_rows.append({
            "cell": cell,
            "n": data["n"],
            "mean_confidence": data["mean_confidence"],
            "mean_success": data["mean_success"],
            "ece": data["ece"],
            "brier": data["brier"],
        })

    if not sweep_rows:
        print("No usable IS rows.")
        return 0

    pd.DataFrame(sweep_rows).to_csv(out_dir / "risk_coverage.csv", index=False)
    cal_df = pd.DataFrame(cal_rows).sort_values("cell")
    cal_df.to_csv(out_dir / "calibration.csv", index=False)

    _plot_risk_coverage(per_cell, out_dir / "risk_coverage.png")
    _plot_reliability(per_cell, out_dir / "reliability.png")

    print(f"\nWrote {out_dir / 'risk_coverage.csv'} ({len(sweep_rows)} rows)")
    print(f"Wrote {out_dir / 'calibration.csv'} ({len(cal_rows)} cells)")
    print(f"Wrote {out_dir / 'risk_coverage.png'}, {out_dir / 'reliability.png'}\n")

    print("Per-cell calibration summary:")
    print(cal_df.to_string(index=False, float_format="%.3f"))

    # Pooled headline.
    all_conf = np.concatenate([d["raw_conf"] for d in per_cell.values() if len(d.get("raw_conf", []))])
    all_succ = np.concatenate([d["raw_succ"] for d in per_cell.values() if len(d.get("raw_succ", []))])
    if len(all_conf):
        ece_p = expected_calibration_error(all_conf.tolist(), all_succ.tolist(), n_bins=10)
        brier_p = brier_score(all_conf.tolist(), all_succ.tolist())
        print(f"\nPOOLED ({len(all_conf)} trials): ECE = {ece_p:.3f}, Brier = {brier_p:.3f}, "
              f"mean_conf = {all_conf.mean():.3f}, mean_succ = {all_succ.mean():.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
