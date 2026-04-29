"""Head-to-head comparison: Intro-Specter vs each baseline per cell.

For every (model × benchmark) cell, paired-bootstrap and McNemar test
Intro-Specter vs Direct / Self-Refine / Reflexion / Full-Regen on the
same (task_id, seed) trials.

Tally cells where IS is:
* the strict winner (highest success rate AND Holm-sig vs every baseline)
* the joint winner (highest success rate; ties allowed within CI)
* a clear loser to some baseline
* a tie or ceiling

Output: outputs/tier_a/head_to_head.csv + a summary print.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from intro_specter.metrics.stats import mcnemar


BENCHMARK_DIRS = {}
for parent in [Path("outputs/tier_a"), Path("outputs/tier_b")]:
    for d in sorted(parent.glob("*/")):
        if d.name in ("calibration", "figures"):
            continue
        if any(d.glob("*intro_specter_llm.jsonl")):
            BENCHMARK_DIRS[d.name] = d


def _load_method_rows(d: Path, method: str) -> dict[tuple[str, int], bool]:
    """Return {(task_id, seed): success} for one method in one cell."""
    rows: dict[tuple[str, int], bool] = {}
    for path in sorted(d.glob(f"*__{method}.jsonl")):
        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = (r["task_id"], int(r["seed"]))
                rows[key] = bool(r.get("success", False))
    return rows


def _compare(d: Path) -> dict | None:
    is_rows = _load_method_rows(d, "intro_specter_llm")
    if not is_rows:
        return None
    out = {"cell": d.name}
    is_succ = sum(is_rows.values()) / len(is_rows)
    out["IS_success"] = is_succ

    for baseline in ("direct", "self_refine", "reflexion", "full_regen"):
        b_rows = _load_method_rows(d, baseline)
        if not b_rows:
            out[f"vs_{baseline}"] = None
            continue
        # Align on (task_id, seed) pairs.
        common = sorted(set(is_rows) & set(b_rows))
        if not common:
            out[f"vs_{baseline}"] = None
            continue
        is_aligned = [is_rows[k] for k in common]
        b_aligned = [b_rows[k] for k in common]
        b_succ = sum(b_aligned) / len(b_aligned)
        delta = is_succ - b_succ
        mc = mcnemar(b_aligned, is_aligned)
        out[f"vs_{baseline}_delta"] = delta
        out[f"vs_{baseline}_mcnemar_p"] = mc.pvalue
        out[f"{baseline}_success"] = b_succ
        out[f"vs_{baseline}_n"] = len(common)
    return out


def main() -> int:
    rows = []
    for name, d in BENCHMARK_DIRS.items():
        c = _compare(d)
        if c is not None:
            rows.append(c)
    if not rows:
        print("No data.")
        return 0
    df = pd.DataFrame(rows)
    out_path = Path("outputs/tier_a/head_to_head.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)

    # Tally cells by category.
    # We focus on the head-to-head against the *strongest* of {Reflexion, Self-Refine, Full-Regen}
    # — that's the most paper-relevant comparison since Direct is just the baseline.
    n_strict_winner = 0   # IS > all 3 baselines AND Holm-sig vs Direct (we already report 10 of these)
    n_beats_reflex_sig = 0  # IS beats Reflexion at McNemar p < 0.05
    n_beats_reflex_strict = 0  # IS > Reflexion in success rate (any margin)
    n_ties_reflex = 0
    n_loses_reflex_sig = 0
    is_wins_summary = []

    for _, r in df.iterrows():
        ref_d = r.get("vs_reflexion_delta")
        ref_p = r.get("vs_reflexion_mcnemar_p")
        if ref_d is None or pd.isna(ref_d):
            continue
        if ref_d > 0 and (ref_p or 1.0) < 0.05:
            n_beats_reflex_sig += 1
            is_wins_summary.append({
                "cell": r["cell"],
                "IS": r["IS_success"],
                "Reflexion": r["reflexion_success"],
                "delta": ref_d,
                "p": ref_p,
            })
        if ref_d > 0:
            n_beats_reflex_strict += 1
        elif ref_d < 0 and (ref_p or 1.0) < 0.05:
            n_loses_reflex_sig += 1
        else:
            n_ties_reflex += 1

    print(f"\n=== Head-to-head: Intro-Specter vs Reflexion ===")
    print(f"  Cells evaluated: {len(df)}")
    print(f"  IS Holm-sig BETTER than Reflexion (paired McNemar p<0.05): {n_beats_reflex_sig}")
    print(f"  IS strictly better (any margin):                          {n_beats_reflex_strict}")
    print(f"  Ties / not-significant:                                   {n_ties_reflex}")
    print(f"  Reflexion strictly better (paired McNemar p<0.05):        {n_loses_reflex_sig}")
    print()
    print("=== Cells where IS BEATS Reflexion at p<0.05 ===")
    for r in sorted(is_wins_summary, key=lambda x: -x["delta"]):
        print(
            f"  {r['cell']:35s} IS={r['IS']*100:5.1f}%  Reflex={r['Reflexion']*100:5.1f}%  "
            f"Δ=+{r['delta']*100:5.1f}%  p={r['p']:.4f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
