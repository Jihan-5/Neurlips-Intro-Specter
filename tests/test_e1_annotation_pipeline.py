import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.e1_compute_agreement import build_consensus
from scripts.e1_freeze_trace_pool import load_unique


ROOT = Path(__file__).resolve().parents[1]


def _trace(i, role):
    row = {
        "task_id": f"task_{i:03d}",
        "dataset": "travelplanner_real",
        "model": "hidden-model",
        "method": "hidden-method",
        "seed": 42,
        "success": False,
        "task": {"prompt": f"Task {i}"},
        "profile": {"spans": [{"text": "prefers quiet", "kind": "preference"}]},
        "final_trajectory": {
            "steps": [{"step_id": 1, "kind": "thought", "text": "plan"}],
            "final_output": "answer",
        },
        "fault_node_predicted": "secret",
        "_source_path": f"source/{i}.json",
        "_role": role,
    }
    if role == "attention":
        row["_gt"] = {"category": 1, "step": 1}
    return row


def _digest_tree(path):
    return {
        str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(path.rglob("*")) if p.is_file()
    }


def _build(tmp_path, name):
    pool = tmp_path / f"{name}.jsonl"
    rows = (
        [_trace(i, "main") for i in range(100)]
        + [_trace(i + 100, "reserve") for i in range(30)]
        + [_trace(i + 130, "attention") for i in range(10)]
    )
    pool.write_text("".join(json.dumps(row) + "\n" for row in rows))
    out = tmp_path / name
    subprocess.run([
        sys.executable, str(ROOT / "scripts/e1_blind_trajectories.py"),
        "--pool", str(pool), "--out-dir", str(out), "--pilot", "15",
        "--checks-per-annotator", "5",
    ], check=True)
    subprocess.run([
        sys.executable, str(ROOT / "scripts/e1_make_annotation_pages.py"),
        "--dataset-dir", str(out),
    ], check=True)
    manifest = {
        "seed": 42, "n_main": 100, "n_reserve": 30, "n_attention": 10,
    }
    (out / "raw_pool.jsonl").write_bytes(pool.read_bytes())
    (out / "raw_pool.manifest.json").write_text(json.dumps(manifest))
    subprocess.run([
        sys.executable, str(ROOT / "scripts/e1_verify_annotation_materials.py"),
        "--dataset-dir", str(out),
    ], check=True)
    return out


def test_two_annotator_materials_are_blind_complete_and_reproducible(tmp_path):
    first = _build(tmp_path, "first")
    second = _build(tmp_path, "second")
    assert _digest_tree(first) == _digest_tree(second)


def test_d6_disagreement_requires_jihan_and_preserves_frozen_agreements():
    labels = {
        "agreed": [("jazz", 1, 4), ("mahfuza", 1, 5)],
        "disputed": [("jazz", 2, 3), ("mahfuza", 4, 8)],
    }
    pending = build_consensus(labels, {})
    assert pending["agreed"] == {"category": 1, "step": 4, "status": "agreed"}
    assert pending["disputed"] == {"status": "needs_adjudication"}
    decided = build_consensus(labels, {"disputed": ("jihan", 4, 6)})
    assert decided["disputed"] == {
        "category": 4, "step": 6, "status": "adjudicated", "adjudicator": "jihan",
    }


def test_trace_freeze_deduplicates_exact_rows_and_rejects_conflicts(tmp_path):
    row = {
        "dataset": "travelplanner_real", "model": "m", "seed": 42,
        "method": "direct", "task_id": "t1", "success": False,
    }
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    raw = json.dumps(row, sort_keys=True).encode()
    first.write_bytes(raw)
    second.write_bytes(raw)
    unique, duplicates = load_unique([first, second])
    assert len(unique) == 1
    assert duplicates == 1

    second.write_text(json.dumps({**row, "success": True}, sort_keys=True))
    with pytest.raises(SystemExit, match="conflicting duplicate trace key"):
        load_unique([first, second])
