#!/usr/bin/env python3
"""Exact-key merge of frozen A1/A2 bases and deterministic disjoint shard outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from prepare_e2_a1_a2 import _expected
from profile_bootstrap_study import ARMS

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "outputs/rebuttal/profile_bootstrap_a1_a2_final"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    manifest = json.loads((RUN / "sharding_manifest.json").read_text())
    reports = []
    all_complete = True
    for cell in manifest["cells"]:
        records: dict[tuple[str, int, str], tuple[bytes, dict[str, Any], str]] = {}
        duplicates = []
        malformed = []
        cell_dir = RUN / cell["cell"]
        repair = cell_dir / "a1_integrity_repair.jsonl"
        repair_keys = set()
        if repair.exists():
            for raw in repair.read_bytes().splitlines():
                row = json.loads(raw)
                repair_keys.add((str(row["task_id"]), int(row["variant_idx"]), str(row["arm"])))
        sources = [ROOT / cell["base_output"]] + [ROOT / s["output"] for s in cell["shards"]]
        if repair.exists():
            sources.append(repair)
        base = sources[0]
        if sha(base) != cell["base_sha256"]:
            raise RuntimeError(f"frozen base changed for {cell['cell']}")
        for source in sources:
            if not source.exists():
                continue
            for line_no, raw in enumerate(source.read_bytes().splitlines(), 1):
                try:
                    row = json.loads(raw)
                    key = (str(row["task_id"]), int(row["variant_idx"]), str(row["arm"]))
                except Exception as exc:
                    malformed.append({"source": str(source), "line": line_no, "error": str(exc)})
                    continue
                if source == base and key in repair_keys:
                    continue
                if key in records:
                    duplicates.append({"key": list(key), "first": records[key][2],
                                       "second": str(source),
                                       "byte_identical": records[key][0] == raw})
                    continue
                records[key] = (raw, row, str(source))
        expected = _expected(cell["dataset"], 100)
        missing = sorted(expected - records.keys())
        unexpected = sorted(records.keys() - expected)
        hashes = defaultdict(set)
        arms = defaultdict(set)
        for (task, variant, arm), (_, row, _) in records.items():
            hashes[(task, variant)].add(row.get("profile_hash"))
            arms[(task, variant)].add(arm)
        bad_triples = [list(key) for key in hashes
                       if len(hashes[key]) != 1 or None in hashes[key] or arms[key] != set(ARMS)]
        complete = not (missing or unexpected or duplicates or malformed or bad_triples)
        all_complete &= complete
        target = RUN / cell["cell"] / "variants.merged.jsonl"
        if complete:
            tmp = target.with_suffix(target.suffix + ".tmp")
            with tmp.open("wb") as handle:
                for key in sorted(records):
                    handle.write(records[key][0] + b"\n")
            tmp.replace(target)
        report = {
            "cell": cell["cell"], "complete": complete, "rows": len(records),
            "expected": len(expected), "missing": len(missing),
            "unexpected": len(unexpected), "duplicates": duplicates,
            "malformed": malformed, "bad_arm_or_hash_triples": bad_triples,
            "merged_output": str(target.relative_to(ROOT)) if complete else None,
            "merged_sha256": sha(target) if complete else None,
        }
        (RUN / cell["cell"] / "shard_merge_integrity.json").write_text(
            json.dumps(report, indent=2) + "\n")
        reports.append(report)
    result = {"complete": all_complete, "cells": reports}
    (RUN / "shard_merge_report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"complete": all_complete,
                      "rows": sum(r["rows"] for r in reports),
                      "missing": sum(r["missing"] for r in reports),
                      "duplicates": sum(len(r["duplicates"]) for r in reports)}, indent=2))
    if args.require_complete and not all_complete:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
