#!/usr/bin/env python3
"""Validate and freeze completed E1 trace shards into persistent storage.

The source shard tree is read-only. Logical trace keys are validated before any
destination is published; exact duplicates are deduplicated and conflicting
duplicates are fatal. A manifest records every retained file and its SHA-256.
"""

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path


def trace_key(row):
    return (row["dataset"], row["model"], int(row["seed"]), row["method"], row["task_id"])


def slug(value):
    return "".join(c if c.isalnum() or c in "._-" else "-" for c in str(value))


def load_unique(paths):
    unique = {}
    exact_duplicates = 0
    for path in sorted(paths):
        raw = path.read_bytes()
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"malformed trace {path}: {exc}") from exc
        key = trace_key(row)
        digest = hashlib.sha256(raw).hexdigest()
        if key in unique:
            if unique[key][0] != digest:
                raise SystemExit(f"conflicting duplicate trace key: {key}")
            exact_duplicates += 1
            continue
        unique[key] = (digest, raw, path, row)
    return unique, exact_duplicates


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--natural-shards", required=True)
    ap.add_argument("--attention-traces", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--expected-shards", type=int, default=30)
    args = ap.parse_args()

    shard_root = Path(args.natural_shards)
    shard_dirs = sorted(p for p in shard_root.iterdir() if p.is_dir())
    if len(shard_dirs) != args.expected_shards:
        raise SystemExit(f"expected {args.expected_shards} shards, found {len(shard_dirs)}")
    incomplete = []
    for shard in shard_dirs:
        log = shard.with_suffix(".log")
        if not log.exists() or "complete seed=" not in log.read_text(errors="replace"):
            incomplete.append(shard.name)
    if incomplete:
        raise SystemExit(f"incomplete shard logs: {incomplete}")

    natural_paths = [p for shard in shard_dirs for p in (shard / "traces").glob("*.json")]
    attention_paths = sorted(Path(args.attention_traces).glob("*.json"))
    natural, natural_dups = load_unique(natural_paths)
    attention, attention_dups = load_unique(attention_paths)
    if not natural:
        raise SystemExit("natural trace pool is empty")
    if len(attention) < 10:
        raise SystemExit(f"need at least 10 attention traces, found {len(attention)}")
    if any(row[3].get("success") is not False for row in attention.values()):
        raise SystemExit("attention pool contains a non-failed trace")
    if any(
        row[3].get("gold_fault_category") is None or row[3].get("gold_fault_step") is None
        for row in attention.values()
    ):
        raise SystemExit("attention pool contains missing ground truth")

    out = Path(args.out_dir)
    if out.exists():
        raise SystemExit(f"destination already exists; refusing overwrite: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="e1-freeze-", dir=out.parent) as tmp_name:
        tmp = Path(tmp_name)
        natural_dir = tmp / "natural"
        attention_dir = tmp / "attention"
        natural_dir.mkdir()
        attention_dir.mkdir()
        manifest_rows = []
        for kind, rows, target in (
            ("natural", natural, natural_dir),
            ("attention", attention, attention_dir),
        ):
            for key, (digest, raw, source, row) in sorted(rows.items()):
                dataset, model, seed, method, task_id = key
                name = "__".join(map(slug, (model, f"seed{seed}", method, task_id))) + ".json"
                destination = target / name
                destination.write_bytes(raw)
                manifest_rows.append({
                    "kind": kind,
                    "key": list(key),
                    "file": str(destination.relative_to(tmp)),
                    "sha256": digest,
                    "success": row.get("success"),
                    "source": str(source),
                })
        summary = {
            "status": "PASS",
            "natural_shards": len(shard_dirs),
            "natural_traces": len(natural),
            "natural_failures": sum(row[3].get("success") is False for row in natural.values()),
            "attention_traces": len(attention),
            "exact_duplicates_deduplicated": natural_dups + attention_dups,
            "conflicting_duplicates": 0,
            "malformed": 0,
            "files": manifest_rows,
        }
        (tmp / "manifest.json").write_text(json.dumps(summary, indent=2) + "\n")
        shutil.move(str(tmp), str(out))
    print(json.dumps({k: v for k, v in summary.items() if k != "files"}, indent=2))


if __name__ == "__main__":
    main()
