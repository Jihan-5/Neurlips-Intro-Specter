#!/usr/bin/env python3
"""Prepare and verify the single post-production Amendment A1 repair."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CELL = ROOT / "outputs/rebuttal/profile_bootstrap_a1_a2_final/longmemeval_real__llama-3.1-8b"
BASE = CELL / "variants.jsonl"
CONFLICTS = CELL / "a1_conflict_keys.json"
QUARANTINE = CELL / "a1_integrity_quarantine.jsonl"
AUDIT = CELL / "a1_integrity_repair_audit.json"
ASSIGNMENT = CELL / "a1_integrity_repair_assignment.json"
REPAIR = CELL / "a1_integrity_repair.jsonl"
TASK = "real_lme_00016_f8c5f88b"
VARIANT = 39
ARMS = {"direct", "reflexion", "intro_specter"}


def key(row: dict[str, Any]) -> tuple[str, int, str]:
    return str(row["task_id"]), int(row["variant_idx"]), str(row["arm"])


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def originals() -> list[bytes]:
    found = []
    for raw in BASE.read_bytes().splitlines():
        row = json.loads(raw)
        if row.get("task_id") == TASK and int(row.get("variant_idx", -1)) == VARIANT:
            found.append(raw)
    return found


def prepare() -> None:
    raw_rows = originals()
    rows = [json.loads(raw) for raw in raw_rows]
    if len(rows) != 3 or {row["arm"] for row in rows} != ARMS:
        raise RuntimeError("expected exactly the three original conflicting arms")
    hashes = {row.get("profile_hash") for row in rows}
    if len(hashes) < 2:
        raise RuntimeError("source logical unit is no longer conflicting")

    if QUARANTINE.exists():
        if QUARANTINE.read_bytes().splitlines() != raw_rows:
            raise RuntimeError("existing quarantine does not match immutable originals")
    else:
        with QUARANTINE.open("xb") as handle:
            for raw in raw_rows:
                handle.write(raw + b"\n")

    existing = json.loads(CONFLICTS.read_text()) if CONFLICTS.exists() else []
    by_key = {key(item): item for item in existing}
    for arm in sorted(ARMS):
        k = (TASK, VARIANT, arm)
        by_key[k] = {"task_id": TASK, "variant_idx": VARIANT, "arm": arm}
    CONFLICTS.write_text(json.dumps([by_key[k] for k in sorted(by_key)], indent=2) + "\n")
    ASSIGNMENT.write_text(json.dumps([{
        "task_id": TASK, "variant_idx": VARIANT, "arms": sorted(ARMS),
    }], indent=2) + "\n")
    AUDIT.write_text(json.dumps({
        "amendment": "A1", "action": "quarantine-and-rerun-entire-logical-unit",
        "prepared_utc": datetime.now(timezone.utc).isoformat(),
        "task_id": TASK, "variant_idx": VARIANT,
        "original_arms": sorted(ARMS), "original_profile_hashes": sorted(hashes),
        "original_base_sha256": sha(BASE),
        "quarantine": str(QUARANTINE.relative_to(ROOT)),
        "quarantine_sha256": sha(QUARANTINE),
        "replacement": str(REPAIR.relative_to(ROOT)),
        "replacement_status": "pending",
    }, indent=2) + "\n")


def verify() -> None:
    rows = [json.loads(raw) for raw in REPAIR.read_bytes().splitlines()]
    keys = [key(row) for row in rows]
    expected = {(TASK, VARIANT, arm) for arm in ARMS}
    if len(rows) != 3 or len(set(keys)) != 3 or set(keys) != expected:
        raise RuntimeError(f"replacement keys invalid: {keys}")
    hashes = {row.get("profile_hash") for row in rows}
    if len(hashes) != 1 or None in hashes or "" in hashes:
        raise RuntimeError(f"replacement profile hashes invalid: {hashes}")
    if any(row.get("recovered") is not True for row in rows):
        raise RuntimeError("every replacement row must be marked recovered=true")
    audit = json.loads(AUDIT.read_text())
    audit.update({
        "verified_utc": datetime.now(timezone.utc).isoformat(),
        "replacement_status": "verified", "replacement_rows": 3,
        "replacement_arms": sorted(ARMS), "replacement_profile_hash": next(iter(hashes)),
        "replacement_sha256": sha(REPAIR),
    })
    AUDIT.write_text(json.dumps(audit, indent=2) + "\n")


def run() -> None:
    env = {**os.environ, "HF_DATASETS_OFFLINE": "1", "HF_HUB_OFFLINE": "1"}
    command = [
        sys.executable, "scripts/profile_bootstrap_study.py",
        "--dataset", "longmemeval_real", "--model", "llama-3.1-8b",
        "--n-variants", "100",
        "--cache-read-only-base", "cache/bootstrap_longmemeval_real_llama-3.1-8b.sqlite",
        "--cache-path", "cache/e2_a1_a2_repairs/longmemeval_real__llama-3.1-8b.sqlite",
        "--base-output", str(BASE.relative_to(ROOT)),
        "--output-file", str(REPAIR.relative_to(ROOT)),
        "--assignment-file", str(ASSIGNMENT.relative_to(ROOT)),
        "--conflict-file", str(CONFLICTS.relative_to(ROOT)),
    ]
    subprocess.run(command, cwd=ROOT, env=env, check=True)
    verify()
    subprocess.run([sys.executable, "scripts/merge_e2_a1_a2_shards.py", "--require-complete"],
                   cwd=ROOT, env=env, check=True)
    subprocess.run([sys.executable, "scripts/e2_a1_a2_finalize.py"],
                   cwd=ROOT, env=env, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "verify", "run"))
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare()
    elif args.mode == "verify":
        verify()
    else:
        run()


if __name__ == "__main__":
    main()
