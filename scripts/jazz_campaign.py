#!/usr/bin/env python3
"""Crash-resumable Jazz E2/E3 supervisor with single-writer ownership.

The coordinator never deletes or truncates experiment output. It owns only
children it launched, persists launch counts across coordinator restarts, and
permits at most one resume after an inherited/failed launch. E2's remote-owned
LongMemEval/Llama cell is monitored but never launched here.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

import httpx

from aggregate_profile_bootstrap import build_report
from aggregate_profile_candidacy import aggregate_cell

ROOT = Path(__file__).resolve().parents[1]
JAZZ = ROOT / "outputs/jazz"
BOOT_ROOT = ROOT / "outputs/rebuttal/profile_bootstrap"
CAND_ROOT = ROOT / "outputs/rebuttal/profile_candidacy"
DATASETS = ["truthfulqa_real", "hotpotqa_real", "twowiki_real", "musique_real", "longmemeval_real"]
MODELS = ["llama-3.1-8b", "mistral-nemo-12b"]
CELLS = [f"{d}__{m}" for d in DATASETS for m in MODELS]
REMOTE_E2 = {"longmemeval_real__llama-3.1-8b"}


def utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def atomic_json(path: Path, value: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)


def append(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(text.rstrip() + "\n")
        handle.flush()


def credit() -> float:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY missing")
    response = httpx.get(
        "https://openrouter.ai/api/v1/key",
        headers={"Authorization": "Bearer " + key}, timeout=30,
    )
    response.raise_for_status()
    remaining = response.json()["data"].get("limit_remaining")
    if remaining is None:
        raise RuntimeError("provider did not return limit_remaining")
    return float(remaining)


def load_ledger(path: Path) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text())
    launches: dict[str, dict[str, int]] = {"e2": {}, "e3": {}}
    for name in CELLS:
        if (BOOT_ROOT / name / "variants.jsonl").exists():
            launches["e2"][name] = 1
        if (CAND_ROOT / name / "paired.jsonl").exists():
            launches["e3"][name] = 1
    value = {"created_utc": utc(), "launches": launches, "progress": {}, "events": []}
    atomic_json(path, value)
    return value


def record_launch(ledger: dict[str, Any], path: Path, kind: str, name: str, pid: int) -> None:
    count = ledger["launches"][kind].get(name, 0) + 1
    ledger["launches"][kind][name] = count
    ledger["events"].append({"utc": utc(), "event": "launch", "kind": kind,
                             "cell": name, "launch_number": count, "pid": pid})
    atomic_json(path, ledger)


def candidacy_reports() -> dict[str, dict[str, Any]]:
    reports: dict[str, dict[str, Any]] = {}
    for name in CELLS:
        cell = CAND_ROOT / name
        if (cell / "paired.jsonl").exists() and (cell / "protocol.json").exists():
            try:
                reports[name] = aggregate_cell(cell)
            except Exception as exc:
                reports[name] = {"cell": name, "complete": False,
                                 "integrity_error": f"{type(exc).__name__}: {exc}"}
    return reports


def job_alive(job: dict[str, Any]) -> bool:
    """Match PID and its expected log, preventing PID-reuse false positives."""
    check = subprocess.run(["lsof", "-a", "-p", str(job["pid"]), "-d", "cwd,1,2"],
                           text=True, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL)
    if check.returncode != 0:
        return False
    expected = str(job.get("log", ""))
    return not expected or expected in check.stdout


def update_progress(ledger: dict[str, Any], kind: str, name: str,
                    rows: int, expected: int) -> dict[str, Any]:
    key = f"{kind}:{name}"
    samples = ledger["progress"].setdefault(key, [])
    now = time.time()
    if not samples or rows != samples[-1][1] or now - samples[-1][0] >= 900:
        samples.append([now, rows])
        del samples[:-24]
    rate = None
    for old_t, old_rows in samples:
        if now - old_t >= 120 and rows > old_rows:
            rate = (rows - old_rows) / (now - old_t)
            break
    remaining = max(0, expected - rows)
    eta_seconds = remaining / rate if rate and rate > 0 else None
    return {
        "rows": rows, "expected": expected, "remaining": remaining,
        "rows_per_hour": rate * 3600 if rate else None,
        "eta_seconds": eta_seconds,
        "eta_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + eta_seconds)) if eta_seconds else None,
        "over_six_hours": eta_seconds is not None and eta_seconds > 21600,
        "sharding": "not used: harness has no validated deterministic disjoint-shard merge"
                    if eta_seconds and eta_seconds > 21600 else None,
    }


def spawn(kind: str, name: str, launch_number: int) -> tuple[subprocess.Popen, Any, list[str], Path]:
    dataset, model = name.split("__", 1)
    log_path = JAZZ / "logs" / f"{kind}_{name}_launch{launch_number}.log"
    log = log_path.open("a")
    if kind == "e2":
        command = [sys.executable, "-u", "scripts/profile_bootstrap_study.py",
                   "--dataset", dataset, "--model", model, "--n-variants", "100",
                   "--cache-path", f"cache/bootstrap_{dataset}_{model}.sqlite"]
    else:
        command = [sys.executable, "-u", "scripts/run_profile_candidacy.py",
                   "--dataset", dataset, "--model", model, "--allow-profile-candidates",
                   "--cache-path", f"cache/jazz_candidacy_{name}.sqlite"]
    process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                               start_new_session=True)
    return process, log, command, log_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--e2-workers", type=int, default=5)
    parser.add_argument("--e3-workers", type=int, default=3)
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--monitor-only", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--wait-for-lock", action="store_true",
                        help="wait for an inherited coordinator, then take over")
    args = parser.parse_args()
    os.chdir(ROOT)
    (JAZZ / "logs").mkdir(parents=True, exist_ok=True)
    lock = (JAZZ / "campaign.lock").open("a")
    waiting_logged = False
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError as exc:
            if not args.wait_for_lock:
                raise SystemExit("another Jazz coordinator owns outputs/jazz/campaign.lock") from exc
            if not waiting_logged:
                append(JAZZ / "logs/campaign.log",
                       f"{utc()} hardened_coordinator_waiting_for_inherited_lock pid={os.getpid()}")
                waiting_logged = True
            time.sleep(30)

    ledger_path = JAZZ / "campaign_ledger.json"
    ledger = load_ledger(ledger_path)
    active: dict[str, tuple[subprocess.Popen, Any, list[str], float, Path]] = {}
    last_credit: float | None = None
    last_credit_check = 0.0
    last_snapshot = ""
    append(JAZZ / "logs/campaign.log",
           f"{utc()} coordinator_start pid={os.getpid()} monitor_only={args.monitor_only}")

    while True:
        events = []
        for key, (process, log, command, started, log_path) in list(active.items()):
            if process.poll() is None:
                continue
            log.close()
            del active[key]
            event = {"event": "exit", "worker": key, "pid": process.pid,
                     "exit_code": process.returncode, "utc": utc()}
            events.append(event)
            ledger["events"].append(event)

        boot = build_report(BOOT_ROOT)
        boot_by_name = {cell["cell"]: cell for cell in boot["cells"]}
        cand = candidacy_reports()
        inherited_path = JAZZ / "inherited_jobs.json"
        inherited = json.loads(inherited_path.read_text()) if inherited_path.exists() else {}
        external_alive = {key: value for key, value in inherited.items()
                          if job_alive(value)}
        progress: dict[str, Any] = {"e2": {}, "e3": {}}
        for name in CELLS:
            bcell = boot_by_name.get(name, {})
            short = name.startswith(("truthfulqa_real", "hotpotqa_real"))
            progress["e2"][name] = update_progress(
                ledger, "e2", name, int(bcell.get("production_rows", 0)),
                int(bcell.get("expected_rows", 3600 if short else 18000)))
            ccell = cand.get(name, {})
            progress["e3"][name] = update_progress(
                ledger, "e3", name, int(ccell.get("rows", 0)),
                int(ccell.get("expected", 60 if short else 300)))

        now = time.time()
        need_launch = not args.monitor_only and any(
            ((not boot_by_name.get(name, {}).get("complete") and name not in REMOTE_E2
              and "e2:" + name not in external_alive
              and ledger["launches"]["e2"].get(name, 0) < 2)
             or (not cand.get(name, {}).get("complete")
                 and ledger["launches"]["e3"].get(name, 0) < 2))
            for name in CELLS
        )
        health_error = None
        if need_launch and (last_credit is None or now - last_credit_check > 600):
            try:
                last_credit = credit()
                last_credit_check = now
            except Exception as exc:
                health_error = f"{type(exc).__name__}: {exc}"

        def running(kind: str) -> int:
            return sum(key.startswith(kind + ":") for key in active)

        if not args.monitor_only and last_credit is not None:
            for name in CELLS:
                key = "e3:" + name
                if running("e3") >= args.e3_workers:
                    break
                if key in active or cand.get(name, {}).get("complete"):
                    continue
                launches = ledger["launches"]["e3"].get(name, 0)
                if launches >= 2 or last_credit < 5:
                    continue
                process, log, command, log_path = spawn("e3", name, launches + 1)
                active[key] = (process, log, command, now, log_path)
                record_launch(ledger, ledger_path, "e3", name, process.pid)
                events.append({"event": "launch", "worker": key, "pid": process.pid})
            for name in CELLS:
                key = "e2:" + name
                if running("e2") >= args.e2_workers:
                    break
                if (name in REMOTE_E2 or key in active or key in external_alive
                        or boot_by_name.get(name, {}).get("complete")):
                    continue
                launches = ledger["launches"]["e2"].get(name, 0)
                if launches >= 2 or last_credit < 35:
                    continue
                process, log, command, log_path = spawn("e2", name, launches + 1)
                active[key] = (process, log, command, now, log_path)
                record_launch(ledger, ledger_path, "e2", name, process.pid)
                events.append({"event": "launch", "worker": key, "pid": process.pid})

        blocked = []
        for name in CELLS:
            if name in REMOTE_E2 and not boot_by_name.get(name, {}).get("complete"):
                blocked.append({"kind": "e2", "cell": name,
                                "reason": "remote-owned; never launch locally"})
            elif (not boot_by_name.get(name, {}).get("complete")
                  and ledger["launches"]["e2"].get(name, 0) >= 2
                  and "e2:" + name not in active):
                blocked.append({"kind": "e2", "cell": name,
                                "reason": "single resume exhausted"})
            if (not cand.get(name, {}).get("complete")
                    and ledger["launches"]["e3"].get(name, 0) >= 2
                    and "e3:" + name not in active):
                blocked.append({"kind": "e3", "cell": name,
                                "reason": "single resume exhausted"})

        workers = {}
        for key, (process, _log, command, started, log_path) in active.items():
            workers[key] = {
                "pid": process.pid,
                "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
                "command": command, "log": str(log_path),
            }
        state = {
            "schema_version": 2, "updated_utc": utc(),
            "coordinator_pid": os.getpid(), "workers": workers,
            "inherited_active_jobs": external_alive,
            "launches": ledger["launches"], "progress": progress,
            "e2": {"complete": boot["complete"], "cells": boot["cells"],
                   "missing_cells": boot["missing_cells"],
                   "trust_gate": "FAILED_MEANING_PRESERVATION",
                   "remote_owned": sorted(REMOTE_E2)},
            "e3": {"complete": len(cand) == 10 and all(cell.get("complete") for cell in cand.values()),
                   "cells": [cand[name] for name in CELLS if name in cand]},
            "provider_limit_remaining": last_credit,
            "provider_health_error": health_error,
            "blocked": blocked, "events_this_poll": events,
            "resumability": "maximum two launches per cell: inherited/initial launch plus one resume; never deletes output",
        }
        atomic_json(JAZZ / "campaign_status.json", state)
        atomic_json(JAZZ / "bootstrap_report.json", boot)
        atomic_json(ledger_path, ledger)
        compact = json.dumps({
            "utc": state["updated_utc"],
            "workers": {key: value["pid"] for key, value in workers.items()},
            "e2_complete": state["e2"]["complete"],
            "e3_complete": state["e3"]["complete"], "blocked": blocked,
        }, sort_keys=True)
        if compact != last_snapshot or events:
            append(JAZZ / "logs/campaign.log", compact)
            append(JAZZ / "campaign_history.jsonl", json.dumps(state, sort_keys=True))
            last_snapshot = compact

        if args.once:
            break
        e2_terminal = state["e2"]["complete"] or all(
            name in REMOTE_E2 or boot_by_name.get(name, {}).get("complete")
            or ledger["launches"]["e2"].get(name, 0) >= 2 for name in CELLS)
        if not active and e2_terminal and state["e3"]["complete"]:
            break
        time.sleep(max(10, args.poll_seconds))


if __name__ == "__main__":
    main()
