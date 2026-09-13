#!/usr/bin/env python3
"""Profile-fault-fraction diagnostic over Experiment A cells (Route 1 vs Route 2 fork).

For each (dataset, model) cell: pairs every Experiment A failure with the clean-
profile outcome of the same task_id (majority over available clean seeds in
outputs/real/) and classifies failures as noise-caused (clean solves it) vs
baseline (clean also fails). Reports both arms so Reflexion's behaviour under
the same corruption is visible next to Intro-Specter's.
"""
from __future__ import annotations

import collections
import glob
import json
import sys
from pathlib import Path

CELLS = [
    ("truthfulqa_real", "qwen-2.5-7b"),
    ("truthfulqa_real", "mistral-nemo-12b"),
    ("musique_real", "llama-3.1-8b"),
    ("musique_real", "mistral-nemo-12b"),
    ("twowiki_real", "llama-3.1-8b"),
    ("twowiki_real", "mistral-nemo-12b"),
    ("longmemeval_real", "llama-3.1-8b"),
    ("longmemeval_real", "mistral-nemo-12b"),
    ("hotpotqa_real", "llama-3.1-8b"),
    ("hotpotqa_real", "mistral-nemo-12b"),
]
ARMS = ("intro_specter", "reflexion")
CLEAN_METHOD = {"intro_specter": "intro_specter_llm", "reflexion": "reflexion"}
REAL_DIR_MODEL: dict[str, str] = {}


def clean_majority(dataset: str, model: str, method: str, arm: str) -> dict[str, bool]:
    """Clean-profile success per task. Prefers the in-harness rho=0 control arm
    (same provider snapshot and date as the corrupted arms — immune to backend
    drift); falls back to the historical outputs/real/ runs (majority over
    seeds) for cells without a rho0 file (the original TruthfulQA cells)."""
    rho0 = Path(f"outputs/rebuttal/experiment_a/{dataset}__{model}/rho0__{arm}.jsonl")
    if rho0.exists():
        out: dict[str, bool] = {}
        for line in open(rho0):
            r = json.loads(line)
            out[r["task_id"]] = bool(r["true_success"])
        return out
    real_model = REAL_DIR_MODEL.get(model, model)
    votes: dict[str, list[bool]] = collections.defaultdict(list)
    for f in glob.glob(f"outputs/real/{dataset}__{real_model}/*__{method}.jsonl"):
        for line in open(f):
            r = json.loads(line)
            votes[r["task_id"]].append(bool(r["success"]))
    return {t: sum(v) > len(v) / 2 for t, v in votes.items()}


def main() -> None:
    pooled: dict[str, collections.Counter] = {a: collections.Counter() for a in ARMS}
    print(f"{'cell':42s} {'arm':13s} {'rho':5s} {'n':>3s} {'fail':>4s} {'noise':>5s} "
          f"{'base':>4s} {'unm':>3s} {'abst':>4s}")
    for dataset, model in CELLS:
        cell_dir = Path(f"outputs/rebuttal/experiment_a/{dataset}__{model}")
        if not cell_dir.exists():
            continue
        for arm in ARMS:
            maj = clean_majority(dataset, model, CLEAN_METHOD[arm], arm)
            for rho_tag in ("rho10", "rho30"):
                p = cell_dir / f"{rho_tag}__{arm}.jsonl"
                if not p.exists():
                    continue
                rows = [json.loads(l) for l in open(p)]
                fails = [r for r in rows if not r["true_success"]]
                noise = [r for r in fails if maj.get(r["task_id"]) is True]
                base = [r for r in fails if maj.get(r["task_id"]) is False]
                unm = [r for r in fails if r["task_id"] not in maj]
                abst = [r for r in noise if r.get("abstained")]
                print(f"{dataset+'__'+model:42s} {arm:13s} {rho_tag:5s} {len(rows):3d} "
                      f"{len(fails):4d} {len(noise):5d} {len(base):4d} {len(unm):3d} {len(abst):4d}")
                pooled[arm].update(n=len(rows), fail=len(fails), noise=len(noise),
                                   base=len(base), unm=len(unm), abst=len(abst))
    for arm in ARMS:
        p = pooled[arm]
        if not p["n"]:
            continue
        nc_pct = 100 * p["noise"] / p["fail"] if p["fail"] else 0.0
        print(f"\n== POOLED {arm}: rows={p['n']} fail={p['fail']} ({100*p['fail']/p['n']:.1f}%) | "
              f"noise-caused={p['noise']}/{p['fail']} ({nc_pct:.1f}% of failures; "
              f"{p['abst']} abstained) | clean-also-fails={p['base']} unmatched={p['unm']}")


if __name__ == "__main__":
    main()
