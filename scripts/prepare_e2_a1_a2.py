#!/usr/bin/env python3
"""Prepare an isolated E2 Amendment A1/A2 production root.

The source bootstrap tree is read-only.  Expected logical keys are retained
only when there is one copy, or when every duplicate JSON object is byte
identical.  Every copy of a conflicting key is discarded and the key is
persisted for a fresh single-writer rerun.  Malformed and unexpected rows are
reported but never copied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from profile_bootstrap_study import ARMS, expa


AUTHORIZED_CELLS = (
    ("longmemeval_real", "llama-3.1-8b"),
    ("longmemeval_real", "mistral-nemo-12b"),
    ("musique_real", "llama-3.1-8b"),
    ("musique_real", "mistral-nemo-12b"),
    ("twowiki_real", "llama-3.1-8b"),
    ("twowiki_real", "mistral-nemo-12b"),
    ("hotpotqa_real", "llama-3.1-8b"),
    ("hotpotqa_real", "mistral-nemo-12b"),
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _key(row: dict[str, Any]) -> tuple[str, int, str]:
    return str(row["task_id"]), int(row["variant_idx"]), str(row["arm"])


def _expected(dataset: str, n_variants: int) -> set[tuple[str, int, str]]:
    n_examples = expa.DATASET_REGISTRY[dataset]["n_examples"]
    examples = expa._load_examples(dataset, n_examples)
    return {
        (example.task_id, variant_idx, arm)
        for example in examples
        for variant_idx in range(n_variants)
        for arm in ARMS
    }


def prepare_cell(source_root: Path, target_root: Path, dataset: str, model: str,
                 n_variants: int) -> dict[str, Any]:
    cell = f"{dataset}__{model}"
    source = source_root / cell / "variants.jsonl"
    if not source.exists():
        raise FileNotFoundError(source)
    target_dir = target_root / cell
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "variants.jsonl"
    report_path = target_dir / "a1_prepare_report.json"
    if target.exists() and report_path.exists():
        report = json.loads(report_path.read_text())
        if report.get("source_sha256") == _sha256(source) and report.get("target_sha256") == _sha256(target):
            return report
    if target.exists():
        raise FileExistsError(f"refusing to overwrite prepared target: {target}")

    expected = _expected(dataset, n_variants)
    copies: dict[tuple[str, int, str], list[tuple[bytes, dict[str, Any]]]] = defaultdict(list)
    malformed: list[dict[str, Any]] = []
    with source.open("rb") as handle:
        for line_no, raw in enumerate(handle, 1):
            raw = raw.rstrip(b"\r\n")
            if not raw:
                continue
            try:
                row = json.loads(raw)
                key = _key(row)
            except Exception as exc:
                malformed.append({"line": line_no, "error": str(exc)})
                continue
            copies[key].append((raw, row))

    conflicts: list[tuple[str, int, str]] = []
    identical_duplicate_keys: list[tuple[str, int, str]] = []
    unexpected = sorted(key for key in copies if key not in expected)
    retained: list[bytes] = []
    for key in sorted(expected):
        rows = copies.get(key, [])
        if not rows:
            continue
        # A1 says byte-identical payloads may collapse.  Semantically equal
        # JSON with different bytes is deliberately not broadened into that
        # exception.
        distinct_payloads = {raw for raw, _ in rows}
        if len(distinct_payloads) > 1:
            conflicts.append(key)
            continue
        if len(rows) > 1:
            identical_duplicate_keys.append(key)
        retained.append(rows[0][0])

    with target.open("xb") as handle:
        for raw in retained:
            handle.write(raw + b"\n")

    conflict_records = [
        {"task_id": task_id, "variant_idx": variant_idx, "arm": arm}
        for task_id, variant_idx, arm in conflicts
    ]
    (target_dir / "a1_conflict_keys.json").write_text(
        json.dumps(conflict_records, indent=2) + "\n"
    )
    report = {
        "cell": cell,
        "source": str(source),
        "source_sha256": _sha256(source),
        "expected_rows": len(expected),
        "source_valid_rows": sum(len(v) for v in copies.values()),
        "source_unique_keys": len(copies),
        "retained_rows": len(retained),
        "conflicting_keys_discarded": len(conflicts),
        "identical_duplicate_keys_collapsed": len(identical_duplicate_keys),
        "unexpected_keys_discarded": len(unexpected),
        "malformed_rows_discarded": len(malformed),
        "missing_rows_after_prepare": len(expected) - len(retained),
        "conflicts": conflict_records,
        "identical_duplicate_keys": [list(k) for k in identical_duplicate_keys],
        "unexpected_keys": [list(k) for k in unexpected],
        "malformed": malformed,
        "target": str(target),
        "target_sha256": _sha256(target),
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", default="outputs/rebuttal/profile_bootstrap")
    parser.add_argument("--target-root", default="outputs/rebuttal/profile_bootstrap_a1_a2")
    parser.add_argument("--n-variants", type=int, default=100)
    args = parser.parse_args()

    source_root = Path(args.source_root)
    target_root = Path(args.target_root)
    target_root.mkdir(parents=True, exist_ok=True)
    reports = [
        prepare_cell(source_root, target_root, dataset, model, args.n_variants)
        for dataset, model in AUTHORIZED_CELLS
    ]
    manifest = {
        "protocol": "E2 Amendments A1/A2",
        "prepared_utc": datetime.now(timezone.utc).isoformat(),
        "source_root": str(source_root),
        "target_root": str(target_root),
        "authorized_cells": [f"{d}__{m}" for d, m in AUTHORIZED_CELLS],
        "cells": reports,
        "total_expected_rows": sum(r["expected_rows"] for r in reports),
        "total_retained_rows": sum(r["retained_rows"] for r in reports),
        "total_conflicting_keys_discarded": sum(r["conflicting_keys_discarded"] for r in reports),
        "total_missing_rows_after_prepare": sum(r["missing_rows_after_prepare"] for r in reports),
        "old_recovery_tree_policy": "audit-only; no rows imported",
        "paraphrase_reporting": {
            "confirmatory": "canonical template types judged meaning-preserved in the frozen 30-item review",
            "exploratory": "full 100-draw grid; surface fidelity disclosed as 17/30",
        },
    }
    (target_root / "a1_a2_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({
        "target_root": str(target_root),
        "expected": manifest["total_expected_rows"],
        "retained": manifest["total_retained_rows"],
        "conflicts": manifest["total_conflicting_keys_discarded"],
        "missing": manifest["total_missing_rows_after_prepare"],
    }, indent=2))


if __name__ == "__main__":
    main()
