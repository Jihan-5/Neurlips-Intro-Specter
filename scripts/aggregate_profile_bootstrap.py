#!/usr/bin/env python3
"""Aggregate the profile bootstrap study (scripts/profile_bootstrap_study.py).

Per cell (dataset__model directory under outputs/rebuttal/profile_bootstrap/),
reports for each arm:
  * mean true-success across all (example, variant) rows;
  * mean per-example variance of success across variant draws;
and for the IS-vs-Reflexion contrast:
  * the 2.5 / 97.5 percentile of the per-variant-draw effect
    effect(v) = mean_ex[IS success | v] - mean_ex[Reflexion success | v]
    (paired: only examples with both arms present at draw v enter mean_ex);
  * the fraction of variant draws with effect(v) >= 0.

Plain-text output only.

Usage:
    python3 scripts/aggregate_profile_bootstrap.py \\
        [--root outputs/rebuttal/profile_bootstrap] [--cell <dataset>__<model> ...]
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

ARMS = ("direct", "reflexion", "intro_specter")


def _percentile(sorted_vals: list[float], q: float) -> float:
    """Linear-interpolation percentile (q in [0, 100]) on a pre-sorted list."""
    if not sorted_vals:
        return float("nan")
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = (q / 100.0) * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def _load_cell(path: Path) -> dict[str, dict[tuple[str, int], bool]]:
    """arm -> {(task_id, variant_idx): true_success}; later rows win on dupes."""
    per_arm: dict[str, dict[tuple[str, int], bool]] = {a: {} for a in ARMS}
    for line in path.open():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if row["arm"] in per_arm:
            per_arm[row["arm"]][(row["task_id"], row["variant_idx"])] = bool(row["true_success"])
    return per_arm


def aggregate_cell(name: str, path: Path) -> None:
    per_arm = _load_cell(path)
    print(f"\n=== {name} ===")
    if not any(per_arm.values()):
        print("  (no rows)")
        return

    for arm in ARMS:
        rows = per_arm[arm]
        if not rows:
            print(f"  {arm:>14}: no rows")
            continue
        successes = [float(s) for s in rows.values()]
        mean_succ = statistics.mean(successes)
        by_example: dict[str, list[float]] = defaultdict(list)
        for (task_id, _v), s in rows.items():
            by_example[task_id].append(float(s))
        variances = [statistics.pvariance(v) for v in by_example.values() if len(v) > 1]
        mean_var = statistics.mean(variances) if variances else float("nan")
        print(f"  {arm:>14}: n_rows={len(rows):5d}  n_examples={len(by_example):3d}  "
              f"mean_success={mean_succ:.3f}  mean_per_example_variance={mean_var:.4f}")

    # IS - Reflexion effect distribution across variant draws (paired).
    is_rows = per_arm["intro_specter"]
    rf_rows = per_arm["reflexion"]
    paired_keys = set(is_rows) & set(rf_rows)
    by_variant: dict[int, list[float]] = defaultdict(list)
    for (task_id, v) in paired_keys:
        by_variant[v].append(float(is_rows[(task_id, v)]) - float(rf_rows[(task_id, v)]))
    effects = sorted(statistics.mean(diffs) for diffs in by_variant.values() if diffs)
    if not effects:
        print("  IS-vs-Reflexion: no paired rows")
        return
    frac_ge = sum(1 for e in effects if e >= 0) / len(effects)
    print(f"  IS - Reflexion effect over {len(effects)} variant draws "
          f"({len(paired_keys)} paired rows):")
    print(f"    mean={statistics.mean(effects):+.3f}  "
          f"p2.5={_percentile(effects, 2.5):+.3f}  "
          f"p97.5={_percentile(effects, 97.5):+.3f}  "
          f"frac_draws_IS>=Reflexion={frac_ge:.3f}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default="outputs/rebuttal/profile_bootstrap")
    ap.add_argument("--cell", nargs="*", default=None,
                    help="restrict to specific <dataset>__<model> cell names")
    args = ap.parse_args()

    root = Path(args.root)
    if not root.exists():
        raise SystemExit(f"no such directory: {root}")
    cells = sorted(d for d in root.iterdir() if (d / "variants.jsonl").exists())
    if args.cell:
        cells = [c for c in cells if c.name in set(args.cell)]
    if not cells:
        raise SystemExit(f"no cells with variants.jsonl under {root}")
    for cell in cells:
        aggregate_cell(cell.name, cell / "variants.jsonl")


if __name__ == "__main__":
    main()
