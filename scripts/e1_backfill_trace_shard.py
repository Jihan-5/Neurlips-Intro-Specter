#!/usr/bin/env python3
"""Reconstruct one disjoint E1 trace shard in an isolated output directory."""

import argparse
from pathlib import Path

from intro_specter.cli import _spec_from_yaml
from intro_specter.runner import run


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--methods", nargs="+", required=True)
    args = ap.parse_args()

    spec = _spec_from_yaml(Path(args.config))
    available = {method.name: method for method in spec.methods}
    missing = set(args.methods) - set(available)
    if missing:
        raise SystemExit(f"unknown methods: {sorted(missing)}")
    spec.seeds = [args.seed]
    spec.methods = [available[name] for name in args.methods]
    spec.output_dir = args.output_dir
    spec.dump_traces = True
    summary = run(spec)
    print(
        f"complete seed={args.seed} methods={args.methods} "
        f"rows={summary.get('n_total_rows')} examples={summary.get('n_examples')}"
    )


if __name__ == "__main__":
    main()
