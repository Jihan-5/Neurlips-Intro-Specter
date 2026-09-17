#!/usr/bin/env python3
"""Finalize Jazz after all amended E2 recovery integrity merges pass."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RECOVERY = ROOT / "outputs/rebuttal/profile_bootstrap_recovery_v1"
OUT = ROOT / "outputs/jazz"
PROSE = ROOT.parent / "Neurlips-Intro-Specter-prose"


def run(command: list[str], *, cwd: Path = ROOT) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True,
                   env={**os.environ, "HF_DATASETS_OFFLINE": "1", "HF_HUB_OFFLINE": "1"})


def require_complete_recovery() -> None:
    reports = []
    for cell in sorted(RECOVERY.glob("*__*")):
        path = cell / "integrity.json"
        if path.exists():
            reports.append(json.loads(path.read_text()))
    if len(reports) != 10 or not all(report.get("complete") for report in reports):
        raise SystemExit("amended E2 recovery does not have ten passing integrity reports")


def receipt(name: str, command: list[str]) -> None:
    run(command)
    target = OUT / "validation" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("PASS: " + " ".join(command) + "\n")


def main() -> None:
    require_complete_recovery()
    run([sys.executable, "scripts/generate_e2_e3_sections.py"])
    run([sys.executable, "scripts/audit_jazz_consistency.py"])
    receipt("jazz_tests_passed", [str(ROOT / ".venv/bin/pytest"), "-q", "tests/test_jazz_workflow.py"])
    receipt("full_tests_passed", [str(ROOT / ".venv/bin/pytest"), "-q"])
    run(["tectonic", "paper_final.tex", "--outdir", str(OUT / "build")])
    if PROSE.exists():
        run(["tectonic", "paper_final.tex", "--outdir", str(OUT / "build/prose")], cwd=PROSE)
    run([sys.executable, "scripts/write_overnight_status.py"])
    run([sys.executable, "scripts/jazz_final_gate.py", "--create-done"])
    run([sys.executable, "scripts/sync_artifacts_safe.py", "push",
         "E2 amended recovery complete; F2 and Jazz validation artifacts",
         "--include", "outputs/rebuttal/profile_bootstrap_recovery_v1",
         "--include", "outputs/jazz"])


if __name__ == "__main__":
    main()
