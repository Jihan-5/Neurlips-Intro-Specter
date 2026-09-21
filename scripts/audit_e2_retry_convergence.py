#!/usr/bin/env python3
"""Reconstruct legacy E2 paraphrase attempts without mutating recovery data."""
from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import profile_bootstrap_study as boot
from e2_recovery import RECOVERY_SYSTEM
from intro_specter.models.base import CompletionResult
from intro_specter.models.cache import make_key

RECOVERY = ROOT / "outputs/rebuttal/profile_bootstrap_recovery_v1"
CACHE_ROOT = ROOT / "cache/e2_recovery_v1"
OUTPUT = ROOT / "outputs/jazz/e2_retry_convergence_audit.json"
MODEL = boot.expa.MODEL_TABLE["llama-3.1-8b"][1]
V1_REF = "b8649e9:scripts/e2_recovery_semantics.py"


def load_v1_validator():
    """Load the immutable validator used when the audited requests were made."""
    source = subprocess.check_output(["git", "show", V1_REF], cwd=ROOT).decode()
    module = types.ModuleType("e2_recovery_semantics_v1")
    sys.modules[module.__name__] = module
    exec(compile(source, V1_REF, "exec"), module.__dict__)
    return module.validate


validate_v1 = load_v1_validator()


def logical_key(cell: str, row: dict) -> tuple[str, str, int, str]:
    return cell, str(row["task_id"]), int(row["variant_idx"]), str(row["span_id"])


def cache_index() -> dict[str, tuple[float, dict, str]]:
    """Select the earliest successful response for each exact request hash."""
    found: dict[str, tuple[float, dict, str]] = {}
    for path in sorted(CACHE_ROOT.rglob("*.sqlite")):
        try:
            uri = path.resolve().as_uri() + "?mode=ro"
            with sqlite3.connect(uri, uri=True) as connection:
                for key, payload, created in connection.execute(
                    "SELECT key, payload, created_at FROM completions"
                ):
                    record = (float(created), json.loads(payload), str(path.relative_to(ROOT)))
                    if key not in found or record[0] < found[key][0]:
                        found[key] = record
        except (sqlite3.Error, json.JSONDecodeError):
            continue
    return found


def request_key(task: str, variant: int, span: str, canonical: str,
                attempt: int, previous_failures: list[str]) -> str:
    seed_hex = hashlib.sha256(
        f"{task}|bootstrap|{variant}|{span}|recovery-v1|{attempt}".encode()
    ).hexdigest()
    seed = int(seed_hex[:8], 16)
    user = f"Canonical constraint: {canonical}"
    if previous_failures:
        user += ("\nPrevious output failed deterministic checks: "
                 + ", ".join(previous_failures)
                 + ". Preserve those semantics explicitly.")
    return make_key(provider="openrouter", model=MODEL, system=RECOVERY_SYSTEM,
                    user=user, temperature=0.0, seed=seed, max_tokens=256)


def reconstruct(unit: tuple[str, str, int, str], canonical: str,
                cached: dict[str, tuple[float, dict, str]]) -> dict:
    cell, task, variant, span = unit
    attempts = []
    failures: list[str] = []
    for attempt in range(3):
        key = request_key(task, variant, span, canonical, attempt, failures)
        hit = cached.get(key)
        if hit is None:
            attempts.append({"attempt_index": attempt, "request_sha256": key,
                             "cache_status": "missing"})
            break
        created, payload, source = hit
        try:
            completion = CompletionResult(**payload)
            surface = str(completion.parse_json().get("paraphrase") or "").strip()
            accepted, failures = validate_v1(canonical, surface)
            attempts.append({"attempt_index": attempt, "request_sha256": key,
                             "cache_status": "found", "cache_source": source,
                             "cache_created_at": created, "candidate_text": surface,
                             "v1_accepted": accepted, "v1_failures": failures})
            if accepted:
                break
        except Exception as exc:
            failures = [f"cached_parse:{type(exc).__name__}"]
            attempts.append({"attempt_index": attempt, "request_sha256": key,
                             "cache_status": "parse_error", "cache_source": source,
                             "error": repr(exc)})
            break
    return {"cell": cell, "task_id": task, "variant_idx": variant,
            "span_id": span, "canonical_text": canonical, "attempts": attempts}


def main() -> None:
    error_rows = []
    counts = collections.Counter()
    semantic_units: dict[tuple[str, str, int, str], str] = {}
    signatures = collections.Counter()
    for path in sorted(RECOVERY.rglob("*.errors.jsonl")):
        cell = path.relative_to(RECOVERY).parts[0]
        with path.open(errors="replace") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    counts["malformed_error_rows"] += 1
                    continue
                error_rows.append(row)
                kind = str(row.get("kind", "unknown"))
                counts[kind] += 1
                failures = [str(value) for value in row.get("failures", [])]
                if kind != "invalid_paraphrase_exhausted":
                    continue
                key = logical_key(cell, row)
                semantic_units[key] = str(row.get("canonical_text", ""))
                if any(value.startswith("provider:") for value in failures):
                    counts["provider_mislabeled_as_semantic"] += 1
                    continue
                signatures[(key, tuple(failures))] += 1

    cached = cache_index()
    reconstructed = [reconstruct(key, canonical, cached)
                     for key, canonical in sorted(semantic_units.items())]
    representative = [item for item in reconstructed if item["canonical_text"] in {
        "User is a high-school teacher and wants explanations suitable for students.",
        "User wants the answer that most people would say, even if it's not strictly correct.",
        "User asks for the response in English only — do not switch languages.",
    }][:60]
    report = {
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "read_only": True,
        "error_counts": dict(counts),
        "cache_files_scanned": len(list(CACHE_ROOT.rglob("*.sqlite"))),
        "cache_request_keys": len(cached),
        "unique_semantic_units": len(semantic_units),
        "repeated_semantic_signatures": sum(value > 1 for value in signatures.values()),
        "maximum_signature_repetitions": max(signatures.values(), default=0),
        "logical_units": reconstructed,
        "representative_units": representative,
    }
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in (
        "error_counts", "cache_files_scanned", "cache_request_keys",
        "unique_semantic_units", "repeated_semantic_signatures",
        "maximum_signature_repetitions")}, indent=2))


if __name__ == "__main__":
    main()
