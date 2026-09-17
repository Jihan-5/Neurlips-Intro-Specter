#!/usr/bin/env python3
"""Write the concise, credential-free Jazz overnight recovery record."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aggregate_profile_bootstrap import build_report
from aggregate_profile_candidacy import aggregate_cell

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/jazz"


def utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def alive(job: dict) -> bool:
    check = subprocess.run(["lsof", "-a", "-p", str(job["pid"]), "-d", "cwd,1,2"],
                           text=True, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL)
    expected = job.get("log", "")
    return check.returncode == 0 and (not expected or expected in check.stdout)


def caffeinate_assertions() -> list[str]:
    check = subprocess.run(["pmset", "-g", "assertions"], text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return [line.strip() for line in check.stdout.splitlines()
            if "caffeinate" in line or "PreventUserIdleSystemSleep" in line]


def write() -> dict:
    previous_path = OUT / "overnight_status.json"
    previous = json.loads(previous_path.read_text()) if previous_path.exists() else {}
    now_epoch = time.time()
    previous_epoch = previous.get("sample_epoch")
    previous_e2 = {cell["cell"]: cell for cell in previous.get("progress", {}).get("e2", [])}
    previous_e3 = {cell["cell"]: cell for cell in previous.get("progress", {}).get("e3", [])}
    inherited = json.loads((OUT / "inherited_jobs.json").read_text())
    active = {name: {**job, "alive": alive(job), "ownership": "inherited/read-only"}
              for name, job in inherited.items()}
    campaign_path = OUT / "campaign_status.json"
    campaign = json.loads(campaign_path.read_text()) if campaign_path.exists() else {}
    coordinator_workers = campaign.get("workers", campaign.get("active", {}))
    for name, value in coordinator_workers.items():
        job = value if isinstance(value, dict) else {"pid": value}
        active["e3:" + name if ":" not in name else name] = {
            **job, "alive": alive(job), "ownership": "inherited coordinator"}

    bootstrap = build_report(ROOT / "outputs/rebuttal/profile_bootstrap")
    candidacy = []
    for cell in sorted((ROOT / "outputs/rebuttal/profile_candidacy").glob("*__*")):
        if (cell / "protocol.json").exists() and (cell / "paired.jsonl").exists():
            try:
                candidacy.append(aggregate_cell(cell))
            except Exception as exc:
                candidacy.append({"cell": cell.name, "complete": False,
                                  "integrity_error": f"{type(exc).__name__}: {exc}"})
    e2 = [{key: cell.get(key) for key in ("cell", "production_rows", "expected_rows",
           "smoke_or_extra_rows", "malformed_rows", "incomplete_tail", "duplicate_rows",
           "conflicting_duplicates", "paired_hash_mismatches", "complete")}
          for cell in bootstrap["cells"]]
    def add_eta(cells: list[dict], old: dict[str, dict], row_key: str,
                expected_key: str) -> None:
        for cell in cells:
            prior = old.get(cell["cell"], {})
            delta = (cell.get(row_key) or 0) - (prior.get(row_key) or 0)
            elapsed = now_epoch - previous_epoch if previous_epoch else 0
            rate = delta / elapsed if elapsed > 0 and delta > 0 else None
            remaining = max(0, (cell.get(expected_key) or 0) - (cell.get(row_key) or 0))
            eta = remaining / rate if rate else None
            cell.update(rows_per_hour=rate * 3600 if rate else prior.get("rows_per_hour"),
                        eta_seconds=eta,
                        eta_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_epoch + eta)) if eta else None,
                        over_six_hours=eta is not None and eta > 21600)
    add_eta(e2, previous_e2, "production_rows", "expected_rows")
    add_eta(candidacy, previous_e3, "rows", "expected")
    assertions = caffeinate_assertions()
    blockers = [
        {"scope": "E1/F1", "blocker": "headline scope is reserved for Jihan; both 12-cell pure-SPR and 16-cell mixed packages remain separate"},
        {"scope": "E2/F2", "blocker": "30-item paraphrase review failed meaning preservation (17/30 preserved); confirmatory reporting is not permitted"},
        {"scope": "E2", "blocker": "longmemeval_real__llama-3.1-8b remains remote-owned and incomplete locally"},
    ]
    if not bootstrap["complete"]:
        blockers.append({"scope": "E2", "blocker": "production grid incomplete"})
    conflict_cells = [cell["cell"] for cell in e2
                      if cell.get("conflicting_duplicates") or cell.get("paired_hash_mismatches")]
    if conflict_cells:
        blockers.append({
            "scope": "E2 integrity",
            "blocker": (f"{len(conflict_cells)} cells contain conflicting duplicate keys and/or "
                        "paired profile-hash mismatches from overlapping historical writers; "
                        "the frozen protocol defines no row-selection rule"),
            "cells": conflict_cells,
        })
    if len(candidacy) != 10 or not all(cell.get("complete") for cell in candidacy):
        blockers.append({"scope": "E3", "blocker": "paired candidacy grid incomplete"})
    state = {
        "schema_version": 1, "updated_utc": utc(), "sample_epoch": now_epoch,
        "sleep_prevention": {"required": "caffeinate -i for campaign duration",
                             "asserted": any("caffeinate" in line for line in assertions),
                             "evidence": assertions},
        "active_jobs": active,
        "coordinator_heartbeat": campaign.get("updated_utc"),
        "handoff": "hardened coordinator owns the campaign flock; inherited E2 workers are monitored read-only and each has one current output owner",
        "progress": {"e2": e2, "e2_complete": bootstrap["complete"],
                     "e3": candidacy,
                     "e3_complete": len(candidacy) == 10 and all(cell.get("complete") for cell in candidacy)},
        "blockers": blockers,
        "expected_completion_conditions": {
            "E1_F1": "generated 12-cell and 16-cell packages remain validated; Jihan alone chooses headline scope",
            "E2_F2": "all 10 production cells complete with no malformed/conflicting/hash-mismatch rows; prereg aggregation passes; paraphrase trust gate resolved",
            "E3_F3": "all 10 paired cells complete; paired hashes/corruptions valid; recovery aggregation and generated subsection pass tests",
            "E4": "exploratory proxy artifact validates and remains explicitly non-general",
            "F4": "numeric provenance audit, relevant regression suite, and full LaTeX build pass",
            "done_sentinel": "outputs/jazz/JAZZ_DONE is created only by the final gate after the completion report verifies every non-reserved item"
        },
        "done_exists": (OUT / "JAZZ_DONE").exists(),
        "recovery_files": ["outputs/jazz/campaign_status.json", "outputs/jazz/campaign_ledger.json",
                           "outputs/jazz/campaign_history.jsonl", "outputs/jazz/logs/campaign.log",
                           "outputs/jazz/inherited_jobs.json"],
    }
    tmp = OUT / "overnight_status.json.tmp"
    tmp.write_text(json.dumps(state, indent=2) + "\n")
    tmp.replace(OUT / "overnight_status.json")
    # The final gate is deliberately conservative and idempotent. It may
    # create JAZZ_DONE only after every required non-reserved gate passes.
    subprocess.run([sys.executable, "scripts/jazz_final_gate.py", "--create-done"],
                   cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return state


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=int, default=300)
    args = parser.parse_args()
    while True:
        state = write()
        print(state["updated_utc"], "overnight status updated", flush=True)
        if not args.watch or (OUT / "JAZZ_DONE").exists():
            return
        time.sleep(max(30, args.interval))


if __name__ == "__main__":
    main()
