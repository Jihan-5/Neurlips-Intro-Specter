import json
from pathlib import Path

from scripts.prep_personalwab_compact import build_compact


def _write_raw(raw: Path) -> None:
    raw.mkdir()
    user = "USER_12345678"
    products = {
        asin: {
            "parent_asin": asin,
            "title": f"Product {asin}",
            "main_category": "Test",
            "features": ["feature"],
            "price": "1.00",
            "average_rating": 4.0,
        }
        for asin in ("BEFORE0001", "TARGET0001", "BETWEEN001", "TARGET0002", "AFTER00001")
    }
    history = {
        user: [
            {
                "product_info": products[asin],
                "review": {"parent_asin": asin, "timestamp": ts, "rating": 5.0},
            }
            for asin, ts in (
                ("BEFORE0001", 100),
                ("TARGET0001", 200),
                ("BETWEEN001", 300),
                ("TARGET0002", 400),
                ("AFTER00001", 500),
            )
        ]
    }
    tasks = {
        "train": [],
        "test": [
            {
                "user_id": user,
                "task": f"task {n}",
                "timestamp": ts,
                "type": "recommend",
                "target": {"product_info": products[target]},
            }
            for n, ts, target in (
                (1, 200, "TARGET0001"),
                (2, 400, "TARGET0002"),
            )
        ],
    }
    (raw / "user_instructions.json").write_text(json.dumps(tasks))
    (raw / "user_profiles.json").write_text(json.dumps({user: {"user_profile": {"Taste": "plain"}}}))
    (raw / "user_history_part_1.json").write_text(json.dumps(history))
    (raw / "all_products_part_1.json").write_text(json.dumps(products))


def test_compact_uses_a_distinct_strict_cutoff_for_each_task(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    _write_raw(raw)

    compact = build_compact(raw, "; ", "raw")

    assert "history" not in compact
    first, second = compact["recommend_test"]
    assert [h["asin"] for h in first["visible_history"]] == ["BEFORE0001"]
    assert [h["asin"] for h in second["visible_history"]] == [
        "BEFORE0001", "TARGET0001", "BETWEEN001"
    ]
    assert all(h["ts"] < first["timestamp"] for h in first["visible_history"])
    assert all(h["ts"] < second["timestamp"] for h in second["visible_history"])


def test_clean_loader_rejects_row_local_target_leak(tmp_path: Path, monkeypatch) -> None:
    raw = tmp_path / "raw"
    _write_raw(raw)
    compact = build_compact(raw, "; ", "raw")
    compact["recommend_test"] = [compact["recommend_test"][0]]
    compact["recommend_test"][0]["visible_history"].append({
        "ts": 150,
        "asin": "TARGET0001",
        "title": "leak",
        "category": "Test",
        "rating": 5.0,
    })
    path = tmp_path / "compact.json"
    path.write_text(json.dumps(compact))

    monkeypatch.setenv("PERSONALWAB_COMPACT", str(path))
    from intro_specter.benchmarks import personalwab_real

    personalwab_real._DATA = None
    bench = personalwab_real.PersonalWABReal(n_examples=1, seed=42)
    try:
        list(bench)
    except ValueError as exc:
        assert "non-prior or target history entries" in str(exc)
    else:
        raise AssertionError("target-ASIN history leak was not rejected")
