#!/usr/bin/env python3
"""Freeze current A1/A2 base rows and create deterministic disjoint shard assignments."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

from prepare_e2_a1_a2 import _expected

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "outputs/rebuttal/profile_bootstrap_a1_a2_final"
MANIFEST = RUN / "sharding_manifest.json"
PLAN = {
    "longmemeval_real__llama-3.1-8b": 8,
    "longmemeval_real__mistral-nemo-12b": 6,
    "musique_real__llama-3.1-8b": 6,
    "musique_real__mistral-nemo-12b": 6,
    "twowiki_real__llama-3.1-8b": 6,
    "twowiki_real__mistral-nemo-12b": 4,
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_base(path: Path) -> dict[tuple[str, int, str], dict]:
    records = {}
    for line_no, raw in enumerate(path.read_bytes().splitlines(), 1):
        try:
            row = json.loads(raw)
            key = (str(row["task_id"]), int(row["variant_idx"]), str(row["arm"]))
        except Exception as exc:
            raise RuntimeError(f"malformed base row {path}:{line_no}: {exc}") from exc
        if key in records:
            raise RuntimeError(f"duplicate base key {path}:{line_no}: {key}")
        records[key] = row
    return records


def main() -> None:
    if MANIFEST.exists():
        raise SystemExit(f"refusing to replace existing shard manifest: {MANIFEST}")
    cells = []
    global_keys = set()
    total_assigned = 0
    for cell, shard_count in PLAN.items():
        dataset, model = cell.split("__", 1)
        cell_dir = RUN / cell
        base = cell_dir / "variants.jsonl"
        cache = ROOT / f"cache/bootstrap_{dataset}_{model}.sqlite"
        if not cache.exists():
            raise FileNotFoundError(cache)
        records = read_base(base)
        expected = _expected(dataset, 100)
        if not records.keys() <= expected:
            raise RuntimeError(f"unexpected base keys in {cell}: {len(records.keys()-expected)}")
        missing = expected - records.keys()
        units: dict[tuple[str, int], list[str]] = {}
        for task, variant, arm in sorted(missing):
            units.setdefault((task, variant), []).append(arm)
        buckets: list[list[dict]] = [[] for _ in range(shard_count)]
        loads = [0] * shard_count
        for (task, variant), arms in sorted(units.items(), key=lambda item: (-len(item[1]), item[0])):
            index = min(range(shard_count), key=lambda i: (loads[i], i))
            buckets[index].append({"task_id": task, "variant_idx": variant,
                                   "arms": sorted(arms)})
            loads[index] += len(arms)
            for arm in arms:
                key = (cell, task, variant, arm)
                if key in global_keys:
                    raise RuntimeError(f"overlapping assignment: {key}")
                global_keys.add(key)
        shard_dir = cell_dir / "shards_v1"
        assignment_dir = shard_dir / "assignments"
        assignment_dir.mkdir(parents=True, exist_ok=False)
        shards = []
        for index, items in enumerate(buckets):
            assignment = assignment_dir / f"shard-{index:03d}.json"
            assignment.write_text(json.dumps(items, indent=2) + "\n")
            shards.append({
                "index": index, "assignment": str(assignment.relative_to(ROOT)),
                "assignment_sha256": sha(assignment), "logical_units": len(items),
                "assigned_rows": loads[index],
                "output": str((shard_dir / f"shard-{index:03d}.jsonl").relative_to(ROOT)),
                "cache": f"cache/e2_a1_a2_shards/{cell}/shard-{index:03d}.sqlite",
                "screen": f"jazz_e2_a1a2_s_{cell.replace('__','_').replace('.','_')}_{index:03d}",
            })
        total_assigned += len(missing)
        cells.append({
            "cell": cell, "dataset": dataset, "model": model,
            "base_output": str(base.relative_to(ROOT)), "base_sha256": sha(base),
            "base_rows": len(records), "expected_rows": len(expected),
            "assigned_rows": len(missing), "base_cache": str(cache.relative_to(ROOT)),
            "base_cache_sha256": sha(cache), "shard_count": shard_count,
            "shards": shards,
        })
    manifest = {
        "schema_version": 1,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "protocol": "A1/A2 deterministic disjoint acceleration",
        "partition_unit": "(cell, task_id, variant_idx), with every missing arm kept in one shard",
        "cells": cells, "total_shards": sum(PLAN.values()),
        "total_assigned_rows": total_assigned,
        "no_overlap_key_count": len(global_keys),
    }
    if total_assigned != len(global_keys):
        raise RuntimeError("global assignment overlap")
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"total_shards": manifest["total_shards"],
                      "assigned_rows": total_assigned,
                      "base_rows": sum(c["base_rows"] for c in cells)}, indent=2))


if __name__ == "__main__":
    main()
