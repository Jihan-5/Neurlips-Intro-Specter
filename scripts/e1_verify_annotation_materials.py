#!/usr/bin/env python3
"""Fail-closed integrity check for the D6 E1 annotation materials."""

import argparse
import hashlib
import json
import re
from pathlib import Path


BANNED_KEYS = {
    "dataset", "model", "method", "seed", "success", "repair_status",
    "fault_node_predicted", "extracted_dag", "attention_check", "gt_category",
    "gt_step", "_source_path", "_role", "_gt",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def keys_in(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from keys_in(child)
    elif isinstance(value, list):
        for child in value:
            yield from keys_in(child)


def page_ids(path: Path):
    match = re.search(r"const ITEMS = (\[.*?\]);\nconst KEY", path.read_text(), re.S)
    if not match:
        raise AssertionError(f"cannot parse embedded items from {path}")
    return [row["item_id"] for row in json.loads(match.group(1))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset-dir", default="outputs/iclr/e1_dataset")
    ap.add_argument("--write-report")
    args = ap.parse_args()
    root = Path(args.dataset_dir)
    manifest = json.loads((root / "raw_pool.manifest.json").read_text())
    keymap_path = root / "private" / "keymap.json"
    keymap = json.loads(keymap_path.read_text())
    assignments = json.loads((root / "assignments.json").read_text())

    assert manifest["seed"] == 42
    assert manifest["n_main"] == 100
    assert manifest["n_reserve"] == 30
    assert manifest["n_attention"] == 10
    assert set(assignments) == {"jazz", "mahfuza"}

    roles = {role: {i for i, meta in keymap.items() if meta["role"] == role}
             for role in ("main", "reserve", "attention")}
    assert len(roles["main"]) == 100
    assert len(roles["reserve"]) == 30
    assert len(roles["attention"]) == 10
    assert not (roles["main"] & roles["reserve"])
    assert not (roles["main"] & roles["attention"])

    pilot = assignments["jazz"]["pilot"]
    assert pilot == assignments["mahfuza"]["pilot"]
    assert len(pilot) == len(set(pilot)) == 15
    assert set(pilot) <= roles["main"]
    expected_batch = roles["main"] - set(pilot)

    for annotator in ("jazz", "mahfuza"):
        assigned = assignments[annotator]["main"]
        assert len(assigned) == len(set(assigned)) == 90
        natural = set(assigned) & roles["main"]
        checks = set(assigned) & roles["attention"]
        assert natural == expected_batch
        assert len(checks) == 5
        assert not (set(pilot) & set(assigned))
        for phase in ("pilot", "main"):
            page = root / "annotation_pages" / f"{annotator}_{phase}.html"
            assert page_ids(page) == assignments[annotator][phase]
            page_text = page.read_text()
            for token in (
                '"dataset":', '"model":', '"method":', '"seed":',
                'fault_node_predicted', 'attention_check', 'gt_category', 'gt_step',
            ):
                assert token not in page_text, f"hidden metadata leaked in {page}: {token}"

    item_files = sorted((root / "items").glob("e1_*.json"))
    assert len(item_files) == 140
    for path in item_files:
        item = json.loads(path.read_text())
        assert path.stem == item["item_id"]
        leaked = set(keys_in(item)) & BANNED_KEYS
        assert not leaked, f"blinding leak in {path}: {sorted(leaked)}"
    assert not list((root / "annotation_pages").glob("*keymap*"))

    report = {
        "status": "PASS",
        "seed": 42,
        "natural_n": 100,
        "pilot_n": 15,
        "post_gate_natural_n": 85,
        "attention_checks_per_annotator": 5,
        "page_items": {"pilot": 15, "main_including_checks": 90},
        "annotators": ["jazz", "mahfuza"],
        "raw_pool_sha256": digest(root / "raw_pool.jsonl"),
        "private_keymap_sha256": digest(keymap_path),
        "assignments_sha256": digest(root / "assignments.json"),
        "page_sha256": {
            p.name: digest(p) for p in sorted((root / "annotation_pages").glob("*.html"))
        },
    }
    if args.write_report:
        Path(args.write_report).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
