#!/usr/bin/env python3
"""Emit a durable E2 integrity/trust failure audit without changing live outputs."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / "outputs/rebuttal/profile_bootstrap"
LOGS = ROOT / "outputs/rebuttal/relaunch_logs"
OUT = ROOT / "outputs/jazz/e2_failure_audit.json"
REVIEW = ROOT / "outputs/jazz/paraphrase_review.json"
SAMPLE = ROOT / "outputs/jazz/paraphrase_sample.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_cell(cell: Path) -> dict:
    rows: dict[tuple, list[dict]] = defaultdict(list)
    malformed = 0
    physical = 0
    for line_no, line in enumerate((cell / "variants.jsonl").read_text().splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        physical += 1
        rows[(row["task_id"], row["variant_idx"], row["arm"])].append(
            {"line": line_no, "row": row}
        )
    duplicate = {key: values for key, values in rows.items() if len(values) > 1}
    conflicts = 0
    profile_hash_conflicts = 0
    for values in duplicate.values():
        canonical = values[0]["row"]
        if any(value["row"] != canonical for value in values[1:]):
            conflicts += 1
        if len({value["row"].get("profile_hash") for value in values}) > 1:
            profile_hash_conflicts += 1
    name = cell.name
    log_candidates = list(LOGS.glob(f"bootstrap_{name.replace('__', '_')}*.log"))
    # Historical filenames abbreviate two cells; fall back to dataset/model tokens.
    if not log_candidates:
        dataset, model = name.split("__")
        log_candidates = [p for p in LOGS.glob("bootstrap_*.log")
                          if dataset.replace("longmemeval_real", "longmemeval_real") in p.name
                          and model in p.name]
    headers = []
    for log in log_candidates:
        text = log.read_bytes().replace(b"\x00", b"").decode("utf-8", errors="replace")
        headers.extend(re.findall(r"Loaded \d+ examples.*", text))
    return {
        "cell": name,
        "physical_rows": physical,
        "unique_rows": len(rows),
        "duplicate_keys": len(duplicate),
        "extra_rows": sum(len(values) - 1 for values in duplicate.values()),
        "conflicting_duplicate_keys": conflicts,
        "profile_hash_conflicts": profile_hash_conflicts,
        "malformed_rows": malformed,
        "observed_top_level_launch_headers": len(headers),
        "source_sha256": sha256(cell / "variants.jsonl"),
    }


def main() -> None:
    cells = [audit_cell(cell) for cell in sorted(BOOT.glob("*__*"))
             if (cell / "variants.jsonl").exists()]
    review = json.loads(REVIEW.read_text())
    sample = json.loads(SAMPLE.read_text())
    failed_canonicals = Counter()
    for decision in review["decisions"]:
        if not decision["preserved"]:
            failed_canonicals[sample["samples"][decision["index"]]["canonical_text"]] += 1
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_only": True,
        "mutated_experiment_outputs": False,
        "integrity": {
            "cells": cells,
            "conflicting_cells": [c["cell"] for c in cells if c["conflicting_duplicate_keys"]],
            "root_cause": (
                "Two top-level workers were launched against the same append-only cell output. "
                "Their resume snapshots overlapped, producing interleaved duplicate logical keys."
            ),
            "disposition": (
                "Do not select first/last conflicting rows or publish F2; the frozen protocol "
                "does not define conflict resolution. Preserve raw files for audit."
            ),
        },
        "paraphrase_trust": {
            "reviewed": review["n_reviewed"],
            "preserved": review["n_preserved"],
            "changed": review["n_meaning_changed"],
            "human_signoff": review["human_signoff"],
            "trust_gate": review["trust_gate"],
            "failed_canonical_counts": dict(failed_canonicals),
            "root_cause": (
                "The generation prompt requests equivalent wording, but acceptance checks only "
                "that output is non-empty and no more than four times the input length. It has no "
                "entailment or constraint-value preservation check. Multi-clause templates are "
                "therefore accepted when the paraphrase retains a premise but drops an imperative."
            ),
            "disposition": (
                "The current frozen E2 run fails its preregistered meaning-preservation gate. "
                "A validator/retry policy would constitute a new protocol and output root."
            ),
            "review_sha256": sha256(REVIEW),
            "sample_sha256": sha256(SAMPLE),
        },
        "remote_longmemeval_llama": {
            "checked_ref": "origin/artifacts fetched 2026-09-17",
            "remote_rows": 4390,
            "complete_expected_rows": 18000,
            "complete_artifact_available": False,
        },
        "f2_permitted": False,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(OUT)


if __name__ == "__main__":
    main()
