#!/usr/bin/env python3
"""Monitor the detached A1/A2 E2 workers and finalize on exact completion.

This process never launches or restarts a worker.  It stops the six named
screen sessions only for a confirmed payment failure or a $30 post-launch
spend breach.  Quiet calls are healthy while their screen remains alive.
"""

from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = ROOT / "outputs/rebuttal/profile_bootstrap_a1_a2_final"
JAZZ = ROOT / "outputs/jazz"
STATUS = JAZZ / "e2_a1_a2_status.json"
HISTORY = JAZZ / "e2_a1_a2_history.jsonl"
LOCK = JAZZ / "e2_a1_a2_monitor.lock"
EXPECTED = 115_200
BASELINE_ROWS = 58_594
BASELINE_USAGE = 8.127270758
SPEND_CAP = 30.0
CELLS = {
    "longmemeval_real__llama-3.1-8b": (18_000, "jazz_e2_a1a2_lme_llama"),
    "longmemeval_real__mistral-nemo-12b": (18_000, "jazz_e2_a1a2_lme_mistral"),
    "musique_real__llama-3.1-8b": (18_000, "jazz_e2_a1a2_musique_llama"),
    "musique_real__mistral-nemo-12b": (18_000, "jazz_e2_a1a2_musique_mistral"),
    "twowiki_real__llama-3.1-8b": (18_000, "jazz_e2_a1a2_twowiki_llama"),
    "twowiki_real__mistral-nemo-12b": (18_000, "jazz_e2_a1a2_twowiki_mistral"),
    "hotpotqa_real__llama-3.1-8b": (3_600, ""),
    "hotpotqa_real__mistral-nemo-12b": (3_600, ""),
}


def utc(ts: float | None = None) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts or time.time()))


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)


def rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("rb") as handle:
        return sum(1 for line in handle if line.strip())


def screens() -> set[str]:
    result = subprocess.run(["screen", "-ls"], text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    found = set()
    for line in result.stdout.splitlines():
        if ".jazz_e2_a1a2_" in line:
            found.add(line.strip().split(".", 1)[1].split()[0])
    return found


def balance() -> dict[str, float]:
    key = os.environ["OPENROUTER_API_KEY"]
    response = httpx.get("https://openrouter.ai/api/v1/key",
                         headers={"Authorization": "Bearer " + key}, timeout=30)
    response.raise_for_status()
    data = response.json()["data"]
    return {name: float(data[name]) for name in ("limit", "usage", "limit_remaining")}


def log_payment_failure() -> str | None:
    needles = ("insufficient credits", "payment required", "http 402", "status_code=402")
    for path in sorted((RUN_ROOT / "_logs").glob("*.log")):
        tail = path.read_text(errors="replace")[-200_000:].lower()
        for needle in needles:
            if needle in tail:
                return f"{path.name}: {needle}"
    return None


def stop_screens(names: set[str]) -> None:
    for name in sorted(names):
        subprocess.run(["screen", "-S", name, "-X", "quit"], check=False)


def main() -> None:
    JAZZ.mkdir(parents=True, exist_ok=True)
    lock_handle = LOCK.open("a")
    try:
        fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise SystemExit("A1/A2 monitor already active") from exc
    launched = time.time()
    samples: list[tuple[float, int]] = [(launched, BASELINE_ROWS)]
    if STATUS.exists():
        try:
            previous_samples = json.loads(STATUS.read_text()).get("samples", [])
            if previous_samples:
                samples = [(float(ts), int(count)) for ts, count in previous_samples]
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
    last_balance: dict[str, float] | None = None
    last_balance_at = 0.0

    while True:
        now = time.time()
        live = screens()
        per_cell = {}
        total = 0
        for cell, (expected, screen_name) in CELLS.items():
            count = rows(RUN_ROOT / cell / "variants.jsonl")
            total += count
            per_cell[cell] = {
                "rows": count, "expected": expected, "remaining": max(0, expected - count),
                "screen": screen_name or None,
                "active": bool(screen_name and screen_name in live),
            }
        if total != samples[-1][1] or now - samples[-1][0] >= 900:
            samples.append((now, total))
            samples = samples[-48:]
        rate = None
        for old_time, old_rows in samples:
            if now - old_time >= 120 and total > old_rows:
                rate = (total - old_rows) / (now - old_time) * 3600
                break
        remaining = max(0, EXPECTED - total)
        eta_seconds = remaining / rate * 3600 if rate else None

        balance_error = None
        if last_balance is None or now - last_balance_at >= 600:
            try:
                last_balance = balance()
                last_balance_at = now
            except Exception as exc:
                balance_error = f"{type(exc).__name__}: {exc}"
        spend = (last_balance["usage"] - BASELINE_USAGE) if last_balance else None
        payment_failure = log_payment_failure()
        premature = [cell for cell, state in per_cell.items()
                      if state["remaining"] and state["screen"] and not state["active"]]
        blocker = None
        if payment_failure:
            blocker = "provider_payment_failure: " + payment_failure
        elif spend is not None and spend >= SPEND_CAP:
            blocker = f"spend_cap_reached: ${spend:.4f} >= ${SPEND_CAP:.2f}"
        elif premature:
            blocker = "worker_exited_incomplete: " + ", ".join(premature)

        status = {
            "updated_utc": utc(now), "protocol": "Amendments A1/A2",
            "run_root": str(RUN_ROOT.relative_to(ROOT)), "rows": total,
            "expected": EXPECTED, "remaining": remaining,
            "rows_per_hour": rate,
            "eta_seconds": eta_seconds,
            "eta_utc": utc(now + eta_seconds) if eta_seconds else None,
            "active_workers": sum(state["active"] for state in per_cell.values()),
            "cells": per_cell, "balance": last_balance, "post_launch_spend": spend,
            "spend_cap": SPEND_CAP, "balance_error": balance_error,
            "blocker": blocker, "samples": samples,
        }
        atomic_json(STATUS, status)
        with HISTORY.open("a") as handle:
            handle.write(json.dumps({k: status[k] for k in (
                "updated_utc", "rows", "remaining", "rows_per_hour", "eta_utc",
                "active_workers", "post_launch_spend", "blocker")}) + "\n")

        if blocker:
            if payment_failure or (spend is not None and spend >= SPEND_CAP):
                stop_screens(live)
            raise SystemExit(blocker)
        if total == EXPECTED:
            try:
                subprocess.run([sys.executable, "scripts/e2_a1_a2_finalize.py"],
                               cwd=ROOT, check=True,
                               env={**os.environ, "HF_DATASETS_OFFLINE": "1", "HF_HUB_OFFLINE": "1"})
            except Exception as exc:
                status["blocker"] = f"finalization_or_integrity_failure: {type(exc).__name__}: {exc}"
                status["updated_utc"] = utc()
                atomic_json(STATUS, status)
                with HISTORY.open("a") as handle:
                    handle.write(json.dumps({"updated_utc": status["updated_utc"],
                                             "rows": total, "remaining": 0,
                                             "active_workers": 0,
                                             "blocker": status["blocker"]}) + "\n")
                raise
            return
        time.sleep(300)


if __name__ == "__main__":
    main()
