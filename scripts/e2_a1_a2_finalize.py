#!/usr/bin/env python3
"""Integrity-check E2 A1/A2, aggregate both tiers, validate, build, and publish."""

from __future__ import annotations

import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from aggregate_profile_bootstrap import ARMS, build_report, summarize  # noqa: E402
from prepare_e2_a1_a2 import AUTHORIZED_CELLS, _expected  # noqa: E402
import profile_bootstrap_study as boot  # noqa: E402

MANAGED = ROOT / "outputs/rebuttal/profile_bootstrap_a1_a2_final"
ORIGINAL = ROOT / "outputs/rebuttal/profile_bootstrap"
COMPLETE = ROOT / "outputs/rebuttal/profile_bootstrap_a1_a2_complete"
OUT = ROOT / "outputs/jazz"
GEN = ROOT / "paper_sections/generated"
PROSE = ROOT.parent / "Neurlips-Intro-Specter-prose"
TRUTHFUL = (("truthfulqa_real", "llama-3.1-8b"),
            ("truthfulqa_real", "mistral-nemo-12b"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], *, cwd: Path = ROOT) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True,
                   env={**os.environ, "HF_DATASETS_OFFLINE": "1", "HF_HUB_OFFLINE": "1"})


def validate_cell(cell: str, path: Path, conflict_path: Path | None) -> dict[str, Any]:
    dataset, _ = cell.split("__", 1)
    expected = _expected(dataset, 100)
    records: dict[tuple[str, int, str], dict[str, Any]] = {}
    raw_payloads: dict[tuple[str, int, str], bytes] = {}
    malformed = []
    duplicates = []
    for line_no, raw in enumerate(path.read_bytes().splitlines(), 1):
        try:
            row = json.loads(raw)
            key = (str(row["task_id"]), int(row["variant_idx"]), str(row["arm"]))
            if key in records:
                duplicates.append({"line": line_no, "key": list(key),
                                   "byte_identical": raw_payloads[key] == raw})
            records[key] = row
            raw_payloads[key] = raw
        except Exception as exc:
            malformed.append({"line": line_no, "error": str(exc)})
    missing = sorted(expected - records.keys())
    unexpected = sorted(records.keys() - expected)
    hashes: dict[tuple[str, int], set[Any]] = defaultdict(set)
    arms: dict[tuple[str, int], set[str]] = defaultdict(set)
    for (task, variant, arm), row in records.items():
        hashes[(task, variant)].add(row.get("profile_hash"))
        arms[(task, variant)].add(arm)
    bad_triples = [list(k) for k in hashes
                   if hashes[k] == {None} or len(hashes[k]) != 1 or arms[k] != set(ARMS)]

    conflict_keys = set()
    if conflict_path and conflict_path.exists():
        conflict_keys = {(item["task_id"], int(item["variant_idx"]), item["arm"])
                         for item in json.loads(conflict_path.read_text())}
    recovered_missing = sorted(key for key in conflict_keys
                               if key not in records or records[key].get("recovered") is not True)
    recovered_unexpected = sorted(key for key, row in records.items()
                                  if row.get("recovered") is True and key not in conflict_keys)
    report = {
        "cell": cell, "source": str(path.relative_to(ROOT)), "source_sha256": sha(path),
        "expected_rows": len(expected), "rows": len(records), "missing": len(missing),
        "unexpected": len(unexpected), "duplicates": duplicates, "malformed": malformed,
        "bad_arm_or_hash_triples": bad_triples,
        "a1_conflict_keys": len(conflict_keys),
        "a1_conflicts_rerun_and_labeled": len(conflict_keys) - len(recovered_missing),
        "recovered_missing_or_unlabeled": [list(k) for k in recovered_missing],
        "recovered_true_outside_a1": [list(k) for k in recovered_unexpected],
    }
    report["complete"] = not any((missing, unexpected, duplicates, malformed, bad_triples,
                                  recovered_missing, recovered_unexpected))
    if not report["complete"]:
        raise RuntimeError("integrity failure: " + json.dumps(report)[:4000])
    return report


def materialize_expected_source(cell: str, source: Path, target_dir: Path) -> dict[str, Any]:
    """Copy only frozen-grid keys while preserving out-of-grid source rows as audit evidence."""
    dataset, _ = cell.split("__", 1)
    expected = _expected(dataset, 100)
    kept: list[bytes] = []
    quarantined: list[bytes] = []
    for line_no, raw in enumerate(source.read_bytes().splitlines(), 1):
        try:
            row = json.loads(raw)
            key = (str(row["task_id"]), int(row["variant_idx"]), str(row["arm"]))
        except Exception as exc:
            raise RuntimeError(f"malformed upstream source row {source}:{line_no}: {exc}") from exc
        (kept if key in expected else quarantined).append(raw)
    target = target_dir / "variants.jsonl"
    with target.open("wb") as handle:
        for raw in kept:
            handle.write(raw + b"\n")
    quarantine = target_dir / "out_of_grid_quarantine.jsonl"
    with quarantine.open("wb") as handle:
        for raw in quarantined:
            handle.write(raw + b"\n")
    return {
        "upstream_source": str(source.relative_to(ROOT)),
        "upstream_source_sha256": sha(source),
        "out_of_grid_rows_quarantined": len(quarantined),
        "out_of_grid_quarantine": str(
            (COMPLETE / target_dir.name / quarantine.name).relative_to(ROOT)),
        "out_of_grid_quarantine_sha256": sha(quarantine),
    }


def materialize_complete() -> list[dict[str, Any]]:
    if COMPLETE.exists():
        raise RuntimeError(f"refusing to overwrite existing complete root: {COMPLETE}")
    tmp = Path(tempfile.mkdtemp(prefix="profile_bootstrap_a1_a2_complete-",
                               dir=COMPLETE.parent))
    reports = []
    try:
        for dataset, model in (*AUTHORIZED_CELLS, *TRUTHFUL):
            cell = f"{dataset}__{model}"
            source_root = MANAGED if (dataset, model) in AUTHORIZED_CELLS else ORIGINAL
            merged = source_root / cell / "variants.merged.jsonl"
            source = merged if merged.exists() else source_root / cell / "variants.jsonl"
            conflict = source_root / cell / "a1_conflict_keys.json"
            target_dir = tmp / cell
            target_dir.mkdir()
            source_audit = None
            if source_root == ORIGINAL:
                source_audit = materialize_expected_source(cell, source, target_dir)
                validation_source = target_dir / "variants.jsonl"
            else:
                shutil.copy2(source, target_dir / "variants.jsonl")
                validation_source = source
            report = validate_cell(
                cell, validation_source, conflict if source_root == MANAGED else None)
            if source_audit:
                report["source"] = str(
                    (COMPLETE / cell / "variants.jsonl").relative_to(ROOT))
                report.update(source_audit)
            (target_dir / "integrity.json").write_text(json.dumps(report, indent=2) + "\n")
            reports.append(report)
        tmp.replace(COMPLETE)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return reports


def reviewed_template_types() -> tuple[set[str], dict[str, list[str]]]:
    review = ROOT / "orchestration/jazz_paraphrase_review.md"
    judgments: dict[str, list[str]] = defaultdict(list)
    for line in review.read_text().splitlines():
        parts = [part.strip() for part in line.split("|")]
        if len(parts) >= 7 and parts[1].isdigit():
            judgments[parts[3]].append(parts[5])
    eligible = {canonical for canonical, labels in judgments.items()
                if labels and all(label == "Preserved" for label in labels)}
    return eligible, dict(judgments)


def two_tier(full: dict[str, Any]) -> dict[str, Any]:
    eligible_types, judgments = reviewed_template_types()
    eligible_variants: dict[str, set[tuple[str, int]]] = {}
    cell_counts = {}
    for cell_dir in sorted(COMPLETE.glob("*__*")):
        dataset = cell_dir.name.split("__", 1)[0]
        n_examples = boot.expa.DATASET_REGISTRY[dataset]["n_examples"]
        examples = boot.expa._load_examples(dataset, n_examples)
        eligible = set()
        for example in examples:
            for variant in range(100):
                _, info = boot.make_variant(example, dataset, variant, None)
                canonical_types = [item["canonical_text"] for item in info["redrawn"]]
                if canonical_types and all(item in eligible_types for item in canonical_types):
                    eligible.add((example.task_id, variant))
        eligible_variants[cell_dir.name] = eligible
        cell_counts[cell_dir.name] = len(eligible)

    per_arm = {arm: {} for arm in ARMS}
    for cell_dir in sorted(COMPLETE.glob("*__*")):
        eligible = eligible_variants[cell_dir.name]
        for line in (cell_dir / "variants.jsonl").read_text().splitlines():
            row = json.loads(line)
            key = (row["task_id"], int(row["variant_idx"]))
            if key in eligible:
                per_arm[row["arm"]][(cell_dir.name + "/" + key[0], key[1])] = row["true_success"]
    confirmatory = summarize(per_arm)
    return {
        "protocol": "Amendments A1/A2", "grid_complete": full["complete"],
        "trust_gate": "FAILED_17_OF_30_RATIFIED",
        "confirmatory_rule": ("variant eligible only when every redrawn canonical template type "
                               "was reviewed at least once and every reviewed occurrence was Preserved"),
        "eligible_canonical_template_types": sorted(eligible_types),
        "review_judgments": judgments, "eligible_variants_by_cell": cell_counts,
        "confirmatory": confirmatory,
        "exploratory": full["pooled"],
        "exploratory_label": "profile re-draw + paraphrase (surface fidelity 17/30 on strict review)",
    }


def generate_f2(full: dict[str, Any], tiers: dict[str, Any], reports: list[dict[str, Any]]) -> None:
    exp = tiers["exploratory"]["contrast"]
    conf = tiers["confirmatory"]["contrast"]
    text = (
        "\\subsection{Profile-draw robustness (Amendments A1/A2)}\n"
        "We report two pre-declared tiers after the strict paraphrase review preserved 17/30 "
        "sampled constraints. The confirmatory tier contains only variants for which every "
        "redrawn canonical template type was uniformly judged meaning-preserved in the frozen "
        "review; the complete grid is exploratory and labeled profile re-draw plus paraphrase "
        "with surface fidelity 17/30. Conflicting historical logical keys were discarded and "
        "rerun under a single writer; non-conflicting rows were retained. "
        f"In the confirmatory tier ({conf['n_pairs']} paired outcomes), the mean paired "
        f"Intro-Specter--Reflexion effect was {100*conf['mean']:+.2f}\\,pp, the bottom-decile "
        f"mean was {100*conf['worst_decile_mean']:+.2f}\\,pp, and the favorable-draw fraction "
        f"was {conf['favorable_fraction']:.3f} (Hoeffding bound {conf['hoeffding_bound']:.3g}). "
        f"Across the exploratory full grid ({exp['n_pairs']} paired outcomes), the corresponding "
        f"values were {100*exp['mean']:+.2f}\\,pp, "
        f"{100*exp['worst_decile_mean']:+.2f}\\,pp, and {exp['favorable_fraction']:.3f}.\n")
    (GEN / "jazz_f2.tex").write_text(text)
    sources = {str((COMPLETE / r["cell"] / "variants.jsonl").relative_to(ROOT)):
               sha(COMPLETE / r["cell"] / "variants.jsonl") for r in reports}
    for path in (ROOT / "orchestration/profile_robustness_prereg.md",
                 ROOT / "orchestration/jihan_decisions_2026-09-18.md",
                 ROOT / "orchestration/jazz_paraphrase_review.md"):
        sources[str(path.relative_to(ROOT))] = sha(path)
    (GEN / "jazz_f2_provenance.json").write_text(json.dumps({
        "command": ".venv/bin/python scripts/e2_a1_a2_finalize.py",
        "protocol": "Amendments A1/A2", "sources": sources,
        "aggregation": "outputs/jazz/bootstrap_a1_a2_two_tier.json",
        "old_recovery_v1_used": False,
    }, indent=2) + "\n")
    (OUT / "f2_generation_status.json").write_text(json.dumps({
        "grid_complete": True, "integrity_complete": True,
        "trust_gate": "FAILED_17_OF_30_RATIFIED",
        "resolution": "AMENDMENT_A2_TWO_TIER",
        "protocol": "AMENDMENTS_A1_A2", "human_signoff": False,
        "generated": True, "old_recovery_v1_used": False,
    }, indent=2) + "\n")


def write_status() -> None:
    monitor = json.loads((OUT / "e2_a1_a2_status.json").read_text())
    e3 = json.loads((OUT / "candidacy_final.json").read_text())
    if not e3.get("complete"):
        raise RuntimeError("E3 aggregation is not complete; refusing final gate")
    status = {
        "schema_version": 2, "updated_utc": monitor["updated_utc"],
        "sleep_prevention": {"required": "caffeinate -i", "asserted": True,
                             "evidence": ["A1/A2 production and monitor launched under caffeinate"]},
        "progress": {"e2_complete": True, "e2_a1_a2": monitor, "e3_complete": True},
        "blockers": [], "done_exists": (OUT / "JAZZ_DONE").exists(),
    }
    (OUT / "overnight_status.json").write_text(json.dumps(status, indent=2) + "\n")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    reports = materialize_complete()
    full = build_report(COMPLETE)
    if not full["complete"]:
        raise RuntimeError("frozen aggregator rejected complete A1/A2 grid")
    tiers = two_tier(full)
    (OUT / "bootstrap_a1_a2_final.json").write_text(json.dumps(full, indent=2) + "\n")
    (OUT / "bootstrap_a1_a2_two_tier.json").write_text(json.dumps(tiers, indent=2) + "\n")

    # Generate the already-complete E3/F3 package first; then write the A1/A2
    # F2 package so legacy recovery-v1 state cannot overwrite it.
    run([sys.executable, "scripts/generate_e2_e3_sections.py"])
    generate_f2(full, tiers, reports)
    (PROSE / "paper_sections/generated").mkdir(parents=True, exist_ok=True)
    shutil.copy2(GEN / "jazz_f2.tex", PROSE / "paper_sections/generated/jazz_f2.tex")
    shutil.copy2(GEN / "jazz_f2_provenance.json",
                 PROSE / "paper_sections/generated/jazz_f2_provenance.json")
    write_status()
    run([sys.executable, "scripts/audit_jazz_consistency.py"])
    run([str(ROOT / ".venv/bin/pytest"), "-q", "tests/test_jazz_workflow.py",
         "tests/test_e2_a1_a2.py"])
    (OUT / "validation").mkdir(parents=True, exist_ok=True)
    (OUT / "validation/jazz_tests_passed").write_text("PASS: A1/A2 focused Jazz tests\n")
    run([str(ROOT / ".venv/bin/pytest"), "-q"])
    (OUT / "validation/full_tests_passed").write_text("PASS: full offline suite\n")
    run(["tectonic", "paper_final.tex", "--outdir", str(OUT / "build")])
    run(["tectonic", "paper_final.tex", "--outdir", str(OUT / "build/prose")], cwd=PROSE)

    run([sys.executable, "scripts/sync_artifacts_safe.py", "push",
         "E2 Amendments A1/A2 complete; two-tier F2 and validation artifacts",
         "--include", "outputs/rebuttal/profile_bootstrap_a1_a2_complete",
         "--include", "outputs/jazz"])
    (OUT / "validation/artifact_transport_passed").write_text(
        "PASS: A1/A2 E2, two-tier F2, and validation artifacts pushed\n")
    run([sys.executable, "scripts/jazz_final_gate.py", "--create-done"])
    try:
        run([sys.executable, "scripts/sync_artifacts_safe.py", "push",
             "Jazz A1/A2 final gate, completion sentinel, and transport receipt",
             "--include", "outputs/jazz"])
    except Exception:
        (OUT / "JAZZ_DONE").unlink(missing_ok=True)
        raise

    tracked = [
        "scripts/profile_bootstrap_study.py", "scripts/prepare_e2_a1_a2.py",
        "scripts/e2_a1_a2_monitor.py", "scripts/e2_a1_a2_finalize.py",
        "scripts/merge_e2_a1_a2_shards.py", "scripts/repair_e2_a1_conflict.py",
        "tests/test_e2_a1_a2.py", "scripts/jazz_final_gate.py",
        "paper_sections/generated/jazz_f2.tex",
        "paper_sections/generated/jazz_f2_provenance.json",
        "orchestration/jazz_final_completion_report.md",
    ]
    run(["git", "add", *tracked])
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
    if diff.returncode != 0:
        run(["git", "commit", "-m", "Complete E2 A1/A2 and integrate two-tier F2"])
    run(["git", "push", "origin", "HEAD:jashkaran/results"])
    run(["git", "add", "paper_final.tex", "paper_sections/generated/jazz_f2.tex",
         "paper_sections/generated/jazz_f2_provenance.json"], cwd=PROSE)
    prose_diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=PROSE)
    if prose_diff.returncode != 0:
        run(["git", "commit", "-m", "Integrate E2 A1/A2 two-tier F2"], cwd=PROSE)
    run(["git", "push", "origin", "HEAD:jashkaran/prose"], cwd=PROSE)


if __name__ == "__main__":
    main()
