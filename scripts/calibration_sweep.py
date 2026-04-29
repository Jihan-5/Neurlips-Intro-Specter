"""Post-hoc τ_abstain calibration sweep on existing PFQABench-Recon JSONLs.

For every (task, seed) row produced by intro_specter_llm, the JSONL contains
the per-candidate posterior. We didn't change τ between runs (we used 0), but
since each row records the FULL posterior, we can simulate the abstain decision
at any τ ∈ [0, 1] by post-processing.

For each τ, we report:
* coverage     = fraction of cases where max-posterior ≥ τ (we commit)
* selective_success = success rate among committed cases only
* false_commit = committed-cases that ended up with verifier-fail
* ECE / Brier on the binary (committed → success?) prediction with the
  max-posterior as the predicted probability

Output:
* outputs/tier_a/calibration/{model}_curve.csv  — per-τ table
* outputs/tier_a/calibration/{model}_reliability.png
* outputs/tier_a/calibration/{model}_risk_coverage.png
* outputs/tier_a/calibration/summary.csv         — chosen τ at 5%/10% false-commit
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

from intro_specter.metrics.calibration import brier_score, expected_calibration_error


PFQA_DIRS = {
    "Llama 3.3 70B": "outputs/tier_a/pfqa_llama",
    "Llama 3.1 8B": "outputs/tier_a/pfqa_llama3_8b",
    "DeepSeek V3": "outputs/tier_a/pfqa_deepseek",
    "DeepSeek V3.1": "outputs/tier_a/pfqa_deepseek_v31",
    "Mistral Nemo": "outputs/tier_a/pfqa_mistral7b",
    "Qwen 2.5 7B": "outputs/tier_a/pfqa_qwen7b",
    "gpt-oss-20b": "outputs/tier_a/pfqa_gptoss20b",
    "Gemini 2.5 Flash": "outputs/tier_a/pfqa_gemini_flash",
}

TAU_GRID = np.linspace(0.0, 0.95, 20)


def _load_intro_specter_rows(d: Path) -> list[dict]:
    """Return rows from the intro_specter_llm JSONL only."""
    rows: list[dict] = []
    for path in sorted(d.glob("*intro_specter_llm.jsonl")):
        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
    return rows


def _max_posterior(row: dict) -> float | None:
    posterior = row.get("posterior")
    if not posterior:
        return None
    return max(c.get("posterior", 0.0) for c in posterior)


def sweep_one_model(label: str, d: Path, out_dir: Path) -> dict:
    rows = _load_intro_specter_rows(d)
    if not rows:
        return {"model": label, "n": 0}
    out_dir.mkdir(parents=True, exist_ok=True)

    # Calibration is meaningful only on rows where a repair was actually
    # attempted: max_post is the model's own confidence in fault localization,
    # which is irrelevant for "verifier accepted on first pass" cases.
    triples = []
    for r in rows:
        mp = _max_posterior(r)
        if mp is None:
            # Verifier accepted on first pass — no repair was attempted, so
            # this row is not part of the calibration question.
            continue
        triples.append({
            "max_post": mp,
            "success": bool(r.get("success", False)),
            "initial_violated": bool(r.get("profile_violation", False)),
            "repair_status": r.get("repair_status"),
        })
    if not triples:
        return {"model": label, "n": 0}

    # Sweep τ.
    rows_csv: list[dict] = []
    for tau in TAU_GRID:
        committed = 0
        committed_success = 0
        committed_failed = 0
        # When abstain (max_post < τ), we treat the example as still using the
        # initial unrepaired state — the most conservative downstream cost.
        abstain_success = 0
        for t in triples:
            if t["max_post"] >= tau:
                committed += 1
                if t["success"]:
                    committed_success += 1
                else:
                    committed_failed += 1
            else:
                # Abstained: use the initial direct-state success.
                # Initial direct success = NOT initial_violated (initial verifier passed).
                if not t["initial_violated"]:
                    abstain_success += 1
        n = len(triples)
        coverage = committed / n if n else 0.0
        # Selective risk = fraction of committed cases that fail.
        selective_risk = committed_failed / committed if committed else 0.0
        # Overall success when committing on covered, falling back to direct on abstained.
        overall_success = (committed_success + abstain_success) / n if n else 0.0
        rows_csv.append({
            "tau": float(tau),
            "coverage": coverage,
            "selective_success": (committed_success / committed) if committed else 0.0,
            "selective_risk": selective_risk,
            "false_commit_rate": selective_risk,  # rename for clarity
            "overall_success": overall_success,
            "n_committed": committed,
            "n_abstained": n - committed,
        })

    df = pd.DataFrame(rows_csv)
    df.to_csv(out_dir / f"{label.replace(' ', '_')}_curve.csv", index=False)

    # Pick τ that achieves false-commit ≤ 5% with maximum coverage.
    target_5 = df[df["false_commit_rate"] <= 0.05].sort_values("coverage", ascending=False)
    target_10 = df[df["false_commit_rate"] <= 0.10].sort_values("coverage", ascending=False)
    summary = {
        "model": label,
        "n": len(triples),
        "tau_at_5pct_fcr": float(target_5.iloc[0]["tau"]) if len(target_5) else None,
        "coverage_at_5pct_fcr": float(target_5.iloc[0]["coverage"]) if len(target_5) else None,
        "tau_at_10pct_fcr": float(target_10.iloc[0]["tau"]) if len(target_10) else None,
        "coverage_at_10pct_fcr": float(target_10.iloc[0]["coverage"]) if len(target_10) else None,
        "max_overall_success": float(df["overall_success"].max()),
    }

    # ECE / Brier of (max_post → success | committed) at τ = 0 (full coverage).
    probs = [t["max_post"] for t in triples]
    labels = [int(t["success"]) for t in triples]
    summary["ece"] = float(expected_calibration_error(probs, labels))
    summary["brier"] = float(brier_score(probs, labels))

    # ---- plots ---------------------------------------------------------------

    # Reliability diagram: bin by max_post, plot success rate vs bin centre.
    fig, ax = plt.subplots(figsize=(4.5, 4.5), dpi=140)
    bins = np.linspace(0, 1, 11)
    centers = (bins[:-1] + bins[1:]) / 2
    p_arr = np.asarray(probs); y_arr = np.asarray(labels, dtype=float)
    bin_idx = np.digitize(p_arr, bins) - 1
    bin_idx = np.clip(bin_idx, 0, len(centers) - 1)
    accs, counts = [], []
    for b in range(len(centers)):
        mask = bin_idx == b
        accs.append(y_arr[mask].mean() if mask.any() else np.nan)
        counts.append(int(mask.sum()))
    ax.plot([0, 1], [0, 1], "k--", lw=0.8, alpha=0.5, label="ideal")
    ax.bar(centers, accs, width=0.08, alpha=0.7, edgecolor="black")
    ax.set_xlabel("max-posterior bin")
    ax.set_ylabel("success rate in bin")
    ax.set_title(f"Reliability — {label}\nECE={summary['ece']:.3f}, Brier={summary['brier']:.3f}")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
    ax.legend(loc="upper left", fontsize=8)
    plt.tight_layout()
    fig.savefig(out_dir / f"{label.replace(' ', '_')}_reliability.png")
    plt.close(fig)

    # Selective risk-coverage curve.
    fig, ax = plt.subplots(figsize=(5, 4), dpi=140)
    ax.plot(df["coverage"], df["false_commit_rate"], marker="o")
    for _, r in df.iterrows():
        if r["tau"] in (0.0, 0.3, 0.5, 0.7):
            ax.annotate(f"τ={r['tau']:.2f}", (r["coverage"], r["false_commit_rate"]),
                        fontsize=7, alpha=0.8, xytext=(4, 2), textcoords="offset points")
    ax.set_xlabel("coverage (fraction of cases committed)")
    ax.set_ylabel("false-commit rate (selective risk)")
    ax.set_title(f"Selective risk-coverage — {label}")
    ax.axhline(0.05, color="red", lw=0.5, ls="--", alpha=0.5, label="5% FCR target")
    ax.axhline(0.10, color="orange", lw=0.5, ls="--", alpha=0.5, label="10% FCR target")
    ax.legend(loc="upper right", fontsize=8)
    ax.set_xlim(-0.02, 1.02)
    plt.tight_layout()
    fig.savefig(out_dir / f"{label.replace(' ', '_')}_risk_coverage.png")
    plt.close(fig)

    return summary


def main() -> int:
    out_dir = Path("outputs/tier_a/calibration")
    out_dir.mkdir(parents=True, exist_ok=True)
    summaries = []
    for label, d in PFQA_DIRS.items():
        d_path = Path(d)
        if not d_path.exists():
            print(f"[skip] {label} (no dir)")
            continue
        s = sweep_one_model(label, d_path, out_dir)
        summaries.append(s)
        print(
            f"  {label:18s} n={s.get('n', 0):3d}  ECE={s.get('ece', float('nan')):.3f}  "
            f"Brier={s.get('brier', float('nan')):.3f}  "
            f"τ@5%FCR={s.get('tau_at_5pct_fcr')}  cov@5%={s.get('coverage_at_5pct_fcr')}"
        )
    pd.DataFrame(summaries).to_csv(out_dir / "summary.csv", index=False)
    print(f"\nWrote {out_dir / 'summary.csv'} and per-model curves + plots.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
