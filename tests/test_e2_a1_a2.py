import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prepare_e2_a1_a2 as prep
from e2_a1_a2_shard_monitor import provider_rate_limit_count


def test_shard_cache_reads_frozen_base_and_writes_only_delta(tmp_path):
    from intro_specter.models import SQLiteCache
    from intro_specter.models.base import CompletionResult
    from profile_bootstrap_study import ReadThroughCache

    base = tmp_path / "base.sqlite"
    delta = tmp_path / "delta.sqlite"
    SQLiteCache(base).put("old", CompletionResult(text="base", model="m", provider="p"))
    cache = ReadThroughCache(base, delta)
    assert cache.get("old").text == "base"
    cache.put("new", CompletionResult(text="delta", model="m", provider="p"))
    assert cache.get("new").text == "delta"
    assert SQLiteCache(base).get("new") is None


def test_shard_monitor_counts_only_real_provider_429_records():
    text = "\n".join([
        "Warning: set HF_TOKEN to enable higher rate limits and faster downloads.",
        "row tokens=(4291,406)",
        "[RETRY] arm attempt 2/5 failed (APIStatusError: Error code: 429 - rate limit)",
        "[ERROR] prime failed: HTTP status 429 Too Many Requests",
    ])
    assert provider_rate_limit_count(text) == 2


def _write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def test_prepare_discards_all_conflicting_copies_and_keeps_identical_duplicate(
    tmp_path, monkeypatch
):
    source_root = tmp_path / "source"
    target_root = tmp_path / "target"
    cell = source_root / "toy__model" / "variants.jsonl"
    base = {"task_id": "t", "variant_idx": 0, "arm": "direct", "value": 1}
    conflict = {"task_id": "t", "variant_idx": 0, "arm": "reflexion", "value": 1}
    rows = [
        base,
        dict(base),
        conflict,
        {**conflict, "value": 2},
        {"task_id": "unexpected", "variant_idx": 0, "arm": "direct"},
    ]
    _write(cell, rows)
    # Same JSON object, different bytes: A1's exception is byte-identical,
    # so this pair is a conflict rather than an identical duplicate.
    with cell.open("a") as handle:
        handle.write('{"task_id": "t", "variant_idx": 0, "arm": "intro_specter", "value": 3}\n')
        handle.write('{"task_id":"t","variant_idx":0,"arm":"intro_specter","value":3}\n')
    expected = {
        ("t", 0, "direct"),
        ("t", 0, "reflexion"),
        ("t", 0, "intro_specter"),
    }
    monkeypatch.setattr(prep, "_expected", lambda dataset, n_variants: expected)

    report = prep.prepare_cell(source_root, target_root, "toy", "model", 1)

    kept = [json.loads(line) for line in (target_root / "toy__model" / "variants.jsonl").read_text().splitlines()]
    assert kept == [base]
    assert report["retained_rows"] == 1
    assert report["conflicting_keys_discarded"] == 2
    assert report["identical_duplicate_keys_collapsed"] == 1
    assert report["unexpected_keys_discarded"] == 1
    assert report["missing_rows_after_prepare"] == 2
    keys = json.loads((target_root / "toy__model" / "a1_conflict_keys.json").read_text())
    assert keys == [
        {"task_id": "t", "variant_idx": 0, "arm": "intro_specter"},
        {"task_id": "t", "variant_idx": 0, "arm": "reflexion"},
    ]


def test_authorized_plan_includes_d4_cell_alongside_seven_cell_block():
    assert prep.AUTHORIZED_CELLS == (
        ("longmemeval_real", "llama-3.1-8b"),
        ("longmemeval_real", "mistral-nemo-12b"),
        ("musique_real", "llama-3.1-8b"),
        ("musique_real", "mistral-nemo-12b"),
        ("twowiki_real", "llama-3.1-8b"),
        ("twowiki_real", "mistral-nemo-12b"),
        ("hotpotqa_real", "llama-3.1-8b"),
        ("hotpotqa_real", "mistral-nemo-12b"),
    )
