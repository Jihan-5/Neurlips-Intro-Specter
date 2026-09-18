#!/usr/bin/env python3
"""Detached, resumable supervisor for the amended E2 recovery."""
from __future__ import annotations

import json
import fcntl
import os
import re
import signal
import shutil
import subprocess
import sys
import time
import httpx
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECOVERY = ROOT / "outputs/rebuttal/profile_bootstrap_recovery_v1"
STATUS = ROOT / "outputs/jazz/e2_recovery_status.json"
LEDGER = ROOT / "outputs/jazz/e2_recovery_campaign_state.json"
LOG = ROOT / "outputs/jazz/e2_recovery_campaign.log"
COORDINATOR_LOCK = ROOT / "outputs/jazz/e2_recovery_campaign.lock"
WORKER_LOGS = ROOT / "outputs/jazz/e2_recovery_logs"
PYTHON = ROOT / ".venv/bin/python"
SCRIPT = ROOT / "scripts/e2_recovery.py"
CELLS = [f"{d}__{m}" for d in ("truthfulqa_real", "hotpotqa_real", "twowiki_real", "musique_real", "longmemeval_real")
         for m in ("llama-3.1-8b", "mistral-nemo-12b")]
SHARDS = {cell: (2 if cell.startswith(("truthfulqa", "hotpotqa")) else 8) for cell in CELLS}
MIN_CONCURRENCY = 4
START_CONCURRENCY = 8
MAX_CONCURRENCY = 32
RAMP_INTERVAL_SECONDS = 120
RATE_LIMIT_WINDOW_SECONDS = 300
RATE_LIMIT_BACKOFF_THRESHOLD = 3
MAX_SHARD_ATTEMPTS = 16
MAX_FINALIZE_ATTEMPTS = 3
PROVIDER_RETRY_COOLDOWN_SECONDS = 120
RATE_LIMIT_RE = re.compile(r"(?:\b429\b|rate[ -]?limit)", re.IGNORECASE)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)


def event(kind: str, **fields: object) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as handle:
        handle.write(json.dumps({"utc": utc(), "event": kind, **fields}, sort_keys=True) + "\n")


def jsonl_rows(path: Path) -> int:
    if not path.exists(): return 0
    with path.open("rb") as handle:
        return sum(1 for line in handle if line.strip())


def pid_matches(pid: int, cell: str, shard: int, count: int) -> bool:
    try:
        command = subprocess.check_output(["ps", "-p", str(pid), "-o", "command="], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return False
    return ("e2_recovery.py worker" in command and f"--cell {cell}" in command
            and f"--shard-index {shard}" in command and f"--num-shards {count}" in command
            and str(RECOVERY) in command)


def discover_worker_pid(cell: str, shard: int, count: int) -> int | None:
    """Find an exact live shard owner even if a coordinator died before ledger flush."""
    try:
        listing = subprocess.check_output(["ps", "-axo", "pid=,command="], text=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    matches = []
    for line in listing.splitlines():
        fields = line.strip().split(None, 1)
        if len(fields) != 2:
            continue
        pid_text, command = fields
        if ("e2_recovery.py worker" in command and f"--cell {cell}" in command
                and f"--shard-index {shard}" in command and f"--num-shards {count}" in command
                and str(RECOVERY) in command):
            matches.append(int(pid_text))
    if len(matches) > 1:
        event("duplicate_live_workers_detected", key=job_key(cell, shard, count), pids=matches)
        raise RuntimeError(f"multiple live writers for {job_key(cell, shard, count)}: {matches}")
    return matches[0] if matches else None


def provider_health() -> dict:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key: return {"ok": False, "reason": "OPENROUTER_API_KEY unavailable"}
    try:
        headers = {"Authorization": f"Bearer {key}"}
        response = httpx.get("https://openrouter.ai/api/v1/key", headers=headers, timeout=30)
        response.raise_for_status(); data = response.json().get("data", {})
        probe = httpx.post("https://openrouter.ai/api/v1/chat/completions", headers=headers,
                           json={"model": "meta-llama/llama-3.1-8b-instruct",
                                 "messages": [{"role": "user", "content": "Reply OK"}],
                                 "temperature": 0, "max_tokens": 1}, timeout=30)
        probe_body = probe.json()
        if probe.status_code >= 400:
            error = probe_body.get("error", {}) if isinstance(probe_body, dict) else {}
            return {"ok": False, "remaining": data.get("limit_remaining"),
                    "usage": data.get("usage"), "probe_http_status": probe.status_code,
                    "probe_error": str(error.get("message", error))[:1000],
                    "checked_utc": utc()}
        return {"ok": True, "remaining": data.get("limit_remaining"),
                "usage": data.get("usage"), "probe_http_status": probe.status_code,
                "checked_utc": utc()}
    except Exception as exc:
        return {"ok": False, "reason": type(exc).__name__, "checked_utc": utc()}


def load_ledger() -> dict:
    if LEDGER.exists():
        return json.loads(LEDGER.read_text())
    return {"created_utc": utc(), "jobs": {}, "samples": [], "provider_health": {}}


def job_key(cell: str, shard: int, count: int) -> str:
    return f"{cell}:{shard:03d}-of-{count:03d}"


def shard_state(cell: str, shard: int, count: int) -> dict | None:
    path = RECOVERY / cell / "shards" / f"shard-{shard:03d}-of-{count:03d}.state.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        # A worker status snapshot can be interrupted independently of its
        # append-only JSONL. Treat it as absent; the worker/merge reconstructs
        # truth from logical keys rather than trusting a partial status file.
        return None


def initialize_log_offsets() -> dict[str, int]:
    """Start at EOF so historical log tails can never influence concurrency."""
    return {str(path): path.stat().st_size for path in rate_limit_sources()}


def rate_limit_sources() -> list[Path]:
    """Return append-only streams that can record provider throttling."""
    logs = list(WORKER_LOGS.glob("production_*.log"))
    errors = list(RECOVERY.glob("*__*/shards/*.errors.jsonl"))
    return logs + errors


def newly_observed_rate_limits(offsets: dict[str, int]) -> int:
    """Count rate-limit messages written since the preceding supervisor sample."""
    observed = 0
    for path in rate_limit_sources():
        key = str(path)
        try:
            size = path.stat().st_size
            offset = offsets.get(key, size)
            if size < offset:
                offset = 0
            with path.open("rb") as handle:
                handle.seek(offset)
                appended = handle.read().decode("utf-8", errors="replace")
            offsets[key] = size
            observed += len(RATE_LIMIT_RE.findall(appended))
        except OSError:
            continue
    return observed


def archive_blocked_attempt(cell: str, shard: int, count: int, attempt: int) -> None:
    """Preserve failed evidence, then expose only missing units to a clean retry."""
    stem = f"shard-{shard:03d}-of-{count:03d}"
    shard_root = RECOVERY / cell / "shards"
    audit_root = shard_root / "failed_attempts"
    audit_root.mkdir(parents=True, exist_ok=True)
    for suffix in ("errors.jsonl", "state.json"):
        source = shard_root / f"{stem}.{suffix}"
        if source.exists():
            source.replace(audit_root / f"{stem}.attempt-{attempt:03d}.{suffix}")

    cache_root = ROOT / "cache/e2_recovery_v1" / cell
    cache_audit = cache_root / "failed_attempts"
    cache_audit.mkdir(parents=True, exist_ok=True)
    for suffix in (".sqlite", ".sqlite-wal", ".sqlite-shm"):
        source = cache_root / f"{stem}{suffix}"
        if source.exists():
            shutil.move(str(source), cache_audit / f"{stem}.attempt-{attempt:03d}{suffix}")
    event("blocked_attempt_archived", key=job_key(cell, shard, count), attempt=attempt)


def throttle_excess(active: dict[str, subprocess.Popen], ledger: dict, target: int) -> None:
    """Gracefully drain newest workers after a genuine recent rate-limit burst."""
    excess = max(0, len(active) - target)
    if not excess:
        return
    newest = sorted(active, key=lambda key: ledger["jobs"][key].get("launched_utc", ""), reverse=True)
    for key in newest[:excess]:
        pid = ledger["jobs"][key].get("pid")
        if not pid:
            continue
        try:
            os.kill(pid, signal.SIGTERM)
            ledger["jobs"][key]["throttled_utc"] = utc()
            event("worker_throttled", key=key, pid=pid, target=target)
        except ProcessLookupError:
            pass


def status_snapshot(ledger: dict, active: dict[str, subprocess.Popen]) -> dict:
    cells = {}
    total_expected = total_salvaged = total_rerun = total_errors = 0
    blockers = []
    if not ledger.get("provider_health", {}).get("ok"):
        health = ledger.get("provider_health", {})
        blockers.append(f"provider unavailable HTTP {health.get('probe_http_status')}: {health.get('probe_error', health.get('reason'))}")
    for cell in CELLS:
        root = RECOVERY / cell
        protocol = json.loads((root / "protocol.json").read_text())
        expected = protocol["expected_logical_units"]
        salvaged = jsonl_rows(root / "salvaged.jsonl")
        shards = []
        rerun = errors = 0
        for index in range(SHARDS[cell]):
            count = SHARDS[cell]
            key = job_key(cell, index, count)
            base = root / "shards" / f"shard-{index:03d}-of-{count:03d}"
            rows = jsonl_rows(base.with_suffix(".jsonl")); rerun += rows
            error_rows = jsonl_rows(root / "shards" / f"shard-{index:03d}-of-{count:03d}.errors.jsonl")
            errors += error_rows
            state = shard_state(cell, index, count)
            record = ledger["jobs"].get(key, {})
            shards.append({"index": index, "rows": rows, "errors": error_rows,
                           "state": state["state"] if state else ("running" if key in active else "pending"),
                           "pid": ((active[key].pid if active[key] is not None else record.get("pid"))
                                   if key in active else record.get("pid")),
                           "attempts": record.get("attempts", 0), "log": record.get("log")})
            if state and state["state"] == "blocked": blockers.append(f"{key}: worker recorded errors")
            if state and state["state"] == "blocked_terminal_semantic":
                blockers.append(f"{key}: terminal semantic failures exhausted per-unit budget")
            if state and state["state"] == "provider_blocked":
                detail = (state.get("provider_failure") or {}).get("provider_error", {})
                blockers.append(f"{key}: provider blocked HTTP {detail.get('http_status')}")
            if not state and record.get("attempts", 0) >= 2 and key not in active:
                blockers.append(f"{key}: crashed after one resumable restart")
        integrity_path = root / "integrity.json"
        integrity = json.loads(integrity_path.read_text()) if integrity_path.exists() else None
        cells[cell] = {"expected": expected, "salvaged": salvaged, "rerun": rerun,
                       "completed": salvaged + rerun, "invalid_or_error_rows": errors,
                       "shards": shards, "integrity": integrity}
        total_expected += expected; total_salvaged += salvaged; total_rerun += rerun; total_errors += errors
    now = time.time(); completed = total_salvaged + total_rerun
    samples = ledger.setdefault("samples", [])
    samples.append({"time": now, "completed": completed})
    ledger["samples"] = [s for s in samples if now - s["time"] <= 3600][-30:]
    rate = 0.0
    if len(ledger["samples"]) >= 2:
        first = ledger["samples"][0]
        if now > first["time"]: rate = (completed - first["completed"]) * 3600 / (now - first["time"])
    remaining = max(0, total_expected - completed)
    return {"updated_utc": utc(), "protocol": "amended E2 recovery v2",
            "output_root": str(RECOVERY.relative_to(ROOT)), "coordinator_pid": os.getpid(),
            "total_expected_logical_units": total_expected, "salvaged_units": total_salvaged,
            "rerun_units": total_rerun, "completed_units": completed, "invalid_units": total_errors,
            "observed_rows_per_hour": rate, "eta_hours": remaining / rate if rate > 0 else None,
            "provider_credit_health": ledger.get("provider_health", {}), "active_jobs": len(active),
            "blockers": sorted(set(blockers)), "completion_conditions": [
                "all shard states complete", "all ten integrity merges complete",
                "zero missing/overlap/conflict/malformed/invalid/error rows",
                "preregistered analysis and F2 generated", "tests and both manuscript builds pass",
                "final Jazz completion audit passes"], "cells": cells}


def launch(cell: str, shard: int, count: int, ledger: dict) -> subprocess.Popen:
    key = job_key(cell, shard, count); WORKER_LOGS.mkdir(parents=True, exist_ok=True)
    log = WORKER_LOGS / f"production_{cell}_shard-{shard:03d}-of-{count:03d}.log"
    handle = log.open("a")
    command = [str(PYTHON), str(SCRIPT), "worker", "--cell", cell, "--shard-index", str(shard),
               "--num-shards", str(count), "--output-root", str(RECOVERY)]
    process = subprocess.Popen(command, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT,
                               start_new_session=True, env={**os.environ, "HF_DATASETS_OFFLINE": "1", "HF_HUB_OFFLINE": "1"})
    record = ledger["jobs"].setdefault(key, {"attempts": 0})
    record.update(pid=process.pid, attempts=record["attempts"] + 1, launched_utc=utc(), log=str(log.relative_to(ROOT)))
    event("worker_launched", key=key, pid=process.pid, attempt=record["attempts"], log=record["log"])
    return process


def main() -> None:
    COORDINATOR_LOCK.parent.mkdir(parents=True, exist_ok=True)
    coordinator_lock = COORDINATOR_LOCK.open("a")
    try:
        fcntl.flock(coordinator_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise SystemExit("E2 recovery coordinator already active") from exc
    if not (RECOVERY / "prepare_manifest.json").exists(): raise SystemExit("prepare manifest absent")
    ledger = load_ledger(); active: dict[str, subprocess.Popen] = {}
    # Adopt exact live workers, including a launch whose coordinator died before
    # its next atomic ledger flush. Never rely on a stale recorded PID alone.
    for cell in CELLS:
        for index in range(SHARDS[cell]):
            key = job_key(cell, index, SHARDS[cell]); record = ledger["jobs"].get(key, {})
            pid = record.get("pid")
            if not (pid and pid_matches(pid, cell, index, SHARDS[cell])):
                pid = discover_worker_pid(cell, index, SHARDS[cell])
                if pid:
                    record = ledger["jobs"].setdefault(key, {"attempts": 0})
                    record["pid"] = pid
                    record["discovered_utc"] = utc()
            if pid:
                active[key] = None  # type: ignore[assignment]
                event("worker_adopted", key=key, pid=pid)
    last_health = 0.0
    log_offsets = initialize_log_offsets()
    adaptive = ledger.setdefault("adaptive_concurrency", {})
    target = int(adaptive.get("target", START_CONCURRENCY))
    target = max(MIN_CONCURRENCY, min(MAX_CONCURRENCY, target))
    last_adjustment = float(adaptive.get("last_adjustment", time.time()))
    rate_limit_events = [float(value) for value in adaptive.get("rate_limit_events", [])]
    finalize_attempts = 0
    while True:
        # Adopted processes have no Popen handle; poll them by exact command identity.
        for key, proc in list(active.items()):
            cell, suffix = key.rsplit(":", 1); index, count = map(int, suffix.split("-of-"))
            alive = pid_matches(ledger["jobs"][key]["pid"], cell, index, count) if proc is None else proc.poll() is None
            if not alive:
                code = None if proc is None else proc.returncode
                event("worker_exited", key=key, exit_code=code)
                active.pop(key)
        now = time.time()
        if now - last_health > 600 or not ledger.get("provider_health"):
            ledger["provider_health"] = provider_health(); last_health = now
            event("provider_health", **ledger["provider_health"])
        new_limits = newly_observed_rate_limits(log_offsets)
        rate_limit_events.extend([now] * new_limits)
        rate_limit_events = [value for value in rate_limit_events if now - value <= RATE_LIMIT_WINDOW_SECONDS]
        if len(rate_limit_events) >= RATE_LIMIT_BACKOFF_THRESHOLD and now - last_adjustment >= RAMP_INTERVAL_SECONDS:
            old_target = target
            target = max(MIN_CONCURRENCY, target // 2)
            last_adjustment = now
            rate_limit_events.clear()
            event("concurrency_backoff", old_target=old_target, target=target,
                  recent_rate_limit_events=new_limits)
            throttle_excess(active, ledger, target)
        elif not rate_limit_events and now - last_adjustment >= RAMP_INTERVAL_SECONDS and target < MAX_CONCURRENCY:
            old_target = target
            target = min(MAX_CONCURRENCY, target + 4)
            last_adjustment = now
            event("concurrency_ramp", old_target=old_target, target=target)
        adaptive.update(target=target, last_adjustment=last_adjustment,
                        rate_limit_events=rate_limit_events,
                        recent_rate_limit_events=new_limits, updated_utc=utc())
        for cell in CELLS:
            for index in range(SHARDS[cell]):
                if len(active) >= target: break
                if not ledger.get("provider_health", {}).get("ok"): break
                count = SHARDS[cell]; key = job_key(cell, index, count)
                state = shard_state(cell, index, count); record = ledger["jobs"].setdefault(key, {"attempts": 0})
                if key in active or (state and state["state"] == "complete"): continue
                if state and state["state"] == "blocked_terminal_semantic":
                    continue
                if state and state["state"] == "provider_blocked" and not ledger.get("provider_health", {}).get("ok"):
                    continue
                if state and state["state"] == "provider_retryable":
                    retry_after = float(record.setdefault("provider_retry_after", now + PROVIDER_RETRY_COOLDOWN_SECONDS))
                    if now < retry_after:
                        continue
                    record.pop("provider_retry_after", None)
                    archive_blocked_attempt(cell, index, count, record["attempts"])
                elif state and state["state"] == "provider_blocked":
                    archive_blocked_attempt(cell, index, count, record["attempts"])
                elif state and state["state"] == "blocked":
                    if record["attempts"] >= MAX_SHARD_ATTEMPTS:
                        continue
                    archive_blocked_attempt(cell, index, count, record["attempts"])
                elif state is None and record["attempts"]:
                    # A process can exit before writing state (for example,
                    # ENOSPC) after recording errors. Preserve that attempt and
                    # retry missing keys with a fresh shard-owned delta cache.
                    errors = (RECOVERY / cell / "shards"
                              / f"shard-{index:03d}-of-{count:03d}.errors.jsonl")
                    if errors.exists() and errors.stat().st_size:
                        archive_blocked_attempt(cell, index, count, record["attempts"])
                if record["attempts"] >= MAX_SHARD_ATTEMPTS: continue
                active[key] = launch(cell, index, count, ledger)
        # Merge only after every shard in a cell completed successfully.
        for cell in CELLS:
            count = SHARDS[cell]
            states = [shard_state(cell, i, count) for i in range(count)]
            if all(state and state["state"] == "complete" for state in states):
                integrity = RECOVERY / cell / "integrity.json"
                if not integrity.exists() or not json.loads(integrity.read_text()).get("complete"):
                    result = subprocess.run([str(PYTHON), str(SCRIPT), "merge", "--cell", cell,
                                             "--num-shards", str(count), "--output-root", str(RECOVERY)], cwd=ROOT)
                    event("cell_merge", cell=cell, exit_code=result.returncode)
        snapshot = status_snapshot(ledger, active); atomic_json(STATUS, snapshot); atomic_json(LEDGER, ledger)
        all_merged = all((RECOVERY / cell / "integrity.json").exists() and
                         json.loads((RECOVERY / cell / "integrity.json").read_text()).get("complete") for cell in CELLS)
        if all_merged:
            event("recovery_grid_complete")
            finalize = ROOT / "scripts/e2_recovery_finalize.py"
            if finalize.exists():
                finalize_attempts += 1
                result = subprocess.run([str(PYTHON), str(finalize)], cwd=ROOT, env=os.environ)
                event("finalize_exited", exit_code=result.returncode, attempt=finalize_attempts)
                if result.returncode == 0:
                    return
                if finalize_attempts < MAX_FINALIZE_ATTEMPTS:
                    time.sleep(60)
                    continue
                event("campaign_blocked", blockers=[
                    f"finalizer failed {MAX_FINALIZE_ATTEMPTS} idempotent attempts"
                ])
                return
            event("campaign_blocked", blockers=["finalizer script absent"])
            return
        if snapshot["blockers"] and not active and ledger.get("provider_health", {}).get("ok"):
            event("campaign_blocked", blockers=snapshot["blockers"])
            return
        time.sleep(30)


if __name__ == "__main__": main()
