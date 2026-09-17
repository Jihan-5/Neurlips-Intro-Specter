#!/usr/bin/env python3
"""E1 sampling: build the annotation pool from dumped trajectory traces.

Scans one or more traces/ directories (written by `--dump-traces`, see
intro_specter/runner.py and scripts/rebuttal_experiment_personalwab.py), keeps
naturally-FAILED runs, stratifies roughly proportionally across
(dataset x model x method) cells, and draws N + reserve items with a
deterministic seed (42, frozen in orchestration/e1_prereg.md).

Attention-check items come from a separate --attention-traces directory of
injected-fault traces with known ground truth (gt supplied via a sidecar CSV
or the trace's fault metadata; see --attention-gt).

Usage:
  python3 scripts/e1_sample_annotation_set.py \
      --traces outputs/real/travelplanner_real__deepseek-v3/traces \
               outputs/rebuttal/experiment_personalwab/llama-3.1-8b/traces \
      --n 135 --reserve 30 \
      --attention-traces outputs/synthetic_single_fault/traces \
      --n-attention 10 \
      --out outputs/iclr/e1_dataset/raw_pool.jsonl
"""

import argparse
import json
import random
from collections import Counter
from pathlib import Path

SEED = 42  # frozen — orchestration/e1_prereg.md §1


def load_traces(dirs):
    traces = []
    for d in dirs:
        d = Path(d)
        if not d.is_dir():
            raise SystemExit(f"traces dir not found: {d}")
        for p in sorted(d.glob("*.json")):
            t = json.loads(p.read_text())
            t["_source_path"] = str(p)
            traces.append(t)
    return traces


def cell_of(t):
    return (t.get("dataset", "?"), t.get("model", "?"), t.get("method", "?"))


def stratified_sample(pool, n, rng):
    """Proportional allocation across cells (largest-remainder), then uniform
    within cell. Deterministic given pool order and rng."""
    by_cell = {}
    for t in sorted(pool, key=lambda t: t["_source_path"]):
        by_cell.setdefault(cell_of(t), []).append(t)
    total = sum(len(v) for v in by_cell.values())
    n = min(n, total)
    quotas = {c: n * len(v) / total for c, v in by_cell.items()}
    take = {c: int(q) for c, q in quotas.items()}
    rest = sorted(quotas, key=lambda c: quotas[c] - take[c], reverse=True)
    for c in rest:
        if sum(take.values()) >= n:
            break
        if take[c] < len(by_cell[c]):
            take[c] += 1
    picked = []
    for c, items in sorted(by_cell.items()):
        k = min(take.get(c, 0), len(items))
        picked.extend(rng.sample(items, k))
    return picked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", nargs="+", required=True)
    ap.add_argument("--n", type=int, default=135)
    ap.add_argument("--reserve", type=int, default=30)
    ap.add_argument("--attention-traces", nargs="*", default=[])
    ap.add_argument("--n-attention", type=int, default=10)
    ap.add_argument(
        "--attention-gt",
        help="JSON file {task_id: {category: 1..5, step: int}} with ground truth "
        "for attention-check items; without it, attention traces must carry "
        "gold fault metadata (gold_fault_category / gold_fault_step).",
    )
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rng = random.Random(SEED)

    traces = load_traces(args.traces)
    failed = [t for t in traces if t.get("success") is False]
    print(f"loaded {len(traces)} traces, {len(failed)} natural failures")
    per_cell = Counter(cell_of(t) for t in failed)
    for c, k in sorted(per_cell.items()):
        print(f"  {c}: {k} failures")

    want = args.n + args.reserve
    picked = stratified_sample(failed, want, rng)
    main_items, reserve_items = picked[: args.n], picked[args.n :]
    print(f"sampled {len(main_items)} main + {len(reserve_items)} reserve (want {want})")

    checks = []
    if args.attention_traces:
        gt = json.loads(Path(args.attention_gt).read_text()) if args.attention_gt else {}
        cand = load_traces(args.attention_traces)
        usable = []
        for t in cand:
            g = gt.get(t["task_id"])
            if g is None and "gold_fault_category" in t:
                g = {"category": t["gold_fault_category"], "step": t.get("gold_fault_step")}
            if g is not None:
                t["_gt"] = g
                usable.append(t)
        checks = rng.sample(usable, min(args.n_attention, len(usable)))
        print(f"attention checks: {len(checks)} of {len(usable)} usable")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        for role, items in (("main", main_items), ("reserve", reserve_items), ("attention", checks)):
            for t in items:
                t["_role"] = role
                f.write(json.dumps(t, default=str) + "\n")
    manifest = {
        "seed": SEED,
        "n_main": len(main_items),
        "n_reserve": len(reserve_items),
        "n_attention": len(checks),
        "per_cell_failures": {str(k): v for k, v in sorted(per_cell.items())},
        "trace_dirs": args.traces,
    }
    out.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"wrote {out} + manifest")


if __name__ == "__main__":
    main()
