#!/usr/bin/env python3
"""Monitor disjoint A1/A2 shards, merge exact keys, then run finalization."""

from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "outputs/rebuttal/profile_bootstrap_a1_a2_final"
OUT = ROOT / "outputs/jazz"
STATUS = OUT / "e2_a1_a2_status.json"
HISTORY = OUT / "e2_a1_a2_history.jsonl"
LOCK = OUT / "e2_a1_a2_shard_monitor.lock"
EXPECTED = 115_200
HOTPOT_COMPLETE = 7_200
BASELINE_USAGE = 8.127270758
SPEND_CAP = 30.0
PROVIDER_429 = re.compile(
    r"(?:\b(?:status(?:_code)?|http(?:\s+status)?)\s*[=:]?\s*429\b|"
    r"\b429\b.*(?:too many requests|rate[ _-]?limit)|"
    r"(?:too many requests|rate[ _-]?limit).*\b429\b)",
    re.IGNORECASE,
)


def utc(ts: float | None = None) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts or time.time()))


def atomic_json(path: Path, value: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)


def screen_names() -> set[str]:
    result = subprocess.run(["screen", "-ls"], text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    found = set()
    for line in result.stdout.splitlines():
        if ".jazz_e2_a1a2_s_" in line:
            found.add(line.strip().split(".", 1)[1].split()[0])
    return found


def read_keys(path: Path) -> tuple[set[tuple[str, int, str]], int]:
    keys = set()
    malformed = 0
    if not path.exists():
        return keys, malformed
    for raw in path.read_bytes().splitlines():
        try:
            row = json.loads(raw)
            key = (str(row["task_id"]), int(row["variant_idx"]), str(row["arm"]))
        except Exception:
            malformed += 1
            continue
        if key in keys:
            malformed += 1
        keys.add(key)
    return keys, malformed


def provider_rate_limit_count(text: str) -> int:
    """Count only provider 429 failures emitted by retry/error log records.

    This deliberately excludes unrelated startup prose (for example HF Hub's
    generic "higher rate limits" warning) and numeric substrings in row logs.
    """
    return sum(
        1 for line in text.splitlines()
        if ("[RETRY]" in line or "[ERROR]" in line) and PROVIDER_429.search(line)
    )


def balance() -> dict[str, float]:
    response = httpx.get("https://openrouter.ai/api/v1/key",
                         headers={"Authorization": "Bearer " + os.environ["OPENROUTER_API_KEY"]},
                         timeout=30)
    response.raise_for_status()
    data = response.json()["data"]
    return {key: float(data[key]) for key in ("limit", "usage", "limit_remaining")}


def stop_shards(names: set[str]) -> None:
    for name in sorted(names):
        subprocess.run(["screen", "-S", name, "-X", "quit"], check=False)
    ps = subprocess.run(["ps", "-axo", "pid=,command="], text=True,
                        stdout=subprocess.PIPE, check=True).stdout
    for line in ps.splitlines():
        if "profile_bootstrap_study.py" in line and "--assignment-file" in line:
            try:
                os.kill(int(line.strip().split(None, 1)[0]), signal.SIGTERM)
            except (ProcessLookupError, ValueError):
                pass


def main() -> None:
    lock_handle = LOCK.open("a")
    try:
        fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise SystemExit("shard monitor already active") from exc
    manifest = json.loads((RUN / "sharding_manifest.json").read_text())
    samples: list[tuple[float, int]] = []
    rate_limit_samples: list[tuple[float, int]] = []
    last_balance = None
    last_balance_at = 0.0
    while True:
        now = time.time()
        live = screen_names()
        total = HOTPOT_COMPLETE
        duplicate_keys = []
        malformed_total = 0
        premature = []
        cell_states = {}
        error_count = retry_count = rate_limit_count = 0
        for cell in manifest["cells"]:
            base_keys, malformed = read_keys(ROOT / cell["base_output"])
            malformed_total += malformed
            combined = set(base_keys)
            shard_states = []
            for shard in cell["shards"]:
                output = ROOT / shard["output"]
                keys, bad = read_keys(output)
                malformed_total += bad
                overlap = combined & keys
                if overlap:
                    duplicate_keys.extend((cell["cell"], *key) for key in sorted(overlap))
                combined.update(keys)
                active = shard["screen"] in live
                complete = len(keys) == shard["assigned_rows"]
                if not active and not complete:
                    premature.append(f"{cell['cell']}/shard-{shard['index']:03d}")
                shard_states.append({"index": shard["index"], "rows": len(keys),
                                     "expected": shard["assigned_rows"],
                                     "active": active, "complete": complete})
                log = RUN / cell["cell"] / "shards_v1/logs" / f"shard-{shard['index']:03d}.log"
                if log.exists():
                    text = log.read_text(errors="replace")
                    error_count += text.count("[ERROR]")
                    retry_count += text.count("[RETRY]")
                    rate_limit_count += provider_rate_limit_count(text)
            total += len(combined)
            cell_states[cell["cell"]] = {
                "rows": len(combined), "expected": cell["expected_rows"],
                "remaining": cell["expected_rows"] - len(combined),
                "base_rows": len(base_keys), "shards": shard_states,
            }
        if not samples or total != samples[-1][1] or now - samples[-1][0] >= 900:
            samples.append((now, total))
            samples = samples[-48:]
        rate = None
        for old_time, old_rows in samples:
            if now - old_time >= 300 and total > old_rows:
                rate = (total - old_rows) / (now - old_time) * 3600
                break
        remaining = EXPECTED - total
        eta_seconds = remaining / rate * 3600 if rate else None
        rate_limit_samples.append((now, rate_limit_count))
        rate_limit_samples = [sample for sample in rate_limit_samples
                              if now - sample[0] <= 900]
        recent_rate_limits = rate_limit_count - rate_limit_samples[0][1]
        balance_error = None
        if last_balance is None or now - last_balance_at >= 600:
            try:
                last_balance = balance()
                last_balance_at = now
            except Exception as exc:
                balance_error = f"{type(exc).__name__}: {exc}"
        spend = last_balance["usage"] - BASELINE_USAGE if last_balance else None
        payment = None
        for log in RUN.glob("*/shards_v1/logs/*.log"):
            tail = log.read_text(errors="replace")[-100_000:].lower()
            if "insufficient credits" in tail or "status_code=402" in tail or "http 402" in tail:
                payment = str(log.relative_to(ROOT))
                break
        blocker = None
        if duplicate_keys or malformed_total:
            blocker = f"integrity_failure duplicates={len(duplicate_keys)} malformed={malformed_total}"
        elif payment:
            blocker = "provider_payment_failure: " + payment
        elif spend is not None and spend >= SPEND_CAP:
            blocker = f"spend_cap_reached: {spend:.4f}"
        elif premature:
            blocker = "shard_exited_incomplete: " + ", ".join(premature)
        status = {
            "updated_utc": utc(now), "protocol": "A1/A2 deterministic disjoint sharding",
            "rows": total, "expected": EXPECTED, "remaining": remaining,
            "rows_per_hour": rate, "eta_seconds": eta_seconds,
            "eta_utc": utc(now + eta_seconds) if eta_seconds else None,
            "active_workers": len(live), "total_shards": manifest["total_shards"],
            "cells": cell_states, "balance": last_balance,
            "post_launch_spend": spend, "spend_cap": SPEND_CAP,
            "errors": error_count, "retries": retry_count,
            "rate_limit_events": rate_limit_count,
            "recent_rate_limit_events_15m": recent_rate_limits,
            "balance_error": balance_error,
            "duplicate_keys": len(duplicate_keys), "malformed_rows": malformed_total,
            "blocker": blocker, "samples": samples,
        }
        atomic_json(STATUS, status)
        with HISTORY.open("a") as handle:
            handle.write(json.dumps({k: status[k] for k in (
                "updated_utc", "rows", "remaining", "rows_per_hour", "eta_utc",
                "active_workers", "post_launch_spend", "errors", "retries",
                "rate_limit_events", "blocker")}) + "\n")
        if blocker:
            stop_shards(live)
            raise SystemExit(blocker)
        if total == EXPECTED:
            subprocess.run([sys.executable, "scripts/merge_e2_a1_a2_shards.py",
                            "--require-complete"], cwd=ROOT, check=True)
            subprocess.run([sys.executable, "scripts/e2_a1_a2_finalize.py"], cwd=ROOT,
                           check=True, env={**os.environ, "HF_DATASETS_OFFLINE": "1",
                                            "HF_HUB_OFFLINE": "1"})
            return
        time.sleep(120)


if __name__ == "__main__":
    main()
