#!/usr/bin/env python3
"""Rebuild a leak-free PersonalWAB compact recommendation file.

The original compact file lived in a session /tmp scratchpad (default path in
intro_specter/benchmarks/personalwab_real.py) and was LOST when that
scratchpad was cleaned; the prep script that built it was never committed.
This script rebuilds it from the public benchmark repo and — crucially —
stores a separate visible history on every recommendation row.  That history
contains only interactions whose integer Unix-millisecond timestamp is
strictly less than that row's task timestamp, and excludes every occurrence
of that row's target ASIN.  The cutoff is deliberately per task, not per user:
the test split contains users with multiple recommendation tasks.

The clean rebuild is verified with:

  1. task-id check: PersonalWABReal(n=60, seed=42) over the rebuilt file must
     yield exactly the 60 task_ids present in
     outputs/rebuttal/experiment_personalwab/<model>/direct.jsonl
     (task ids embed both the sampled row index-selection and user ids, which
     depend on the row COUNT and ORDER of recommend_test — a strong check).
  2. fail-closed target-ASIN leak check: for every sampled task, require every
     visible history timestamp to be strictly pre-task and require the target
     ASIN to be absent from both the raw visible history and every rendered
     profile/history span.

Usage:
  git clone --depth 1 https://github.com/HongruCai/PersonalWAB.git /tmp/pwab
  python3 scripts/prep_personalwab_compact.py \
      --raw-dir /tmp/pwab/PersonalWAB/envs/pwab/data \
      --out data/personalwab/compact_recommend_clean.json \
      --verify-artifacts outputs/rebuttal/experiment_personalwab/llama-3.1-8b/direct.jsonl \
      --verify-leaks
  export PERSONALWAB_COMPACT=$PWD/data/personalwab/compact_recommend_clean.json

The old completion-cache probe is retained only as an optional forensic aid
for contaminated historical builds.  Clean prompts are expected to miss that
cache and cache equality is not a clean-build verification condition.
"""

import argparse
import json
import random
import sys
from pathlib import Path


def build_compact(raw_dir: Path, feature_join: str, history_order: str) -> dict:
    ui = json.loads((raw_dir / "user_instructions.json").read_text())
    profiles_raw = json.loads((raw_dir / "user_profiles.json").read_text())

    history_raw: dict[str, list] = {}
    for part in sorted(raw_dir.glob("user_history_part_*.json")):
        history_raw.update(json.loads(part.read_text()))

    products: dict[str, dict] = {}
    for part in sorted(raw_dir.glob("all_products_part_*.json")):
        products.update(json.loads(part.read_text()))

    def feat(p):
        f = p.get("features")
        if not f:
            return ""
        if isinstance(f, list):
            if feature_join == "first":
                return str(f[0])
            return feature_join.join(str(x) for x in f)
        return str(f)

    catalog = {}
    for asin, p in products.items():
        catalog[asin] = {
            "asin": asin,
            "title": p.get("title", ""),
            "category": p.get("main_category", ""),
            "price": p.get("price"),
            "rating": p.get("average_rating"),
            "feature": feat(p),
        }

    history = {}
    for uid, entries in history_raw.items():
        rows = []
        for e in entries:
            rev = e.get("review") or {}
            pi = e.get("product_info") or {}
            ts = rev.get("timestamp")
            if not isinstance(ts, int):
                raise ValueError(
                    f"history timestamp must be integer Unix milliseconds: "
                    f"user={uid!r}, value={ts!r}"
                )
            rows.append({
                "ts": ts,
                "asin": rev.get("parent_asin") or pi.get("parent_asin"),
                "title": pi.get("title", ""),
                "category": pi.get("main_category", ""),
                "rating": rev.get("rating"),
            })
        if history_order == "ts":
            rows.sort(key=lambda h: (h["ts"] is None, h["ts"]))
        history[uid] = rows

    recommend_test = []
    for r in ui["test"]:
        if r.get("type") != "recommend":
            continue
        pi = r["target"]["product_info"]
        task_ts = r["timestamp"]
        if not isinstance(task_ts, int):
            raise ValueError(
                f"task timestamp must be integer Unix milliseconds: "
                f"user={r.get('user_id')!r}, value={task_ts!r}"
            )
        target_asin = pi["parent_asin"]
        # Per-task D7 cutoff.  Do not precompute one cutoff per user: 152 of
        # the 504 recommendation users have multiple test tasks (up to nine).
        visible_history = [
            h for h in history.get(r["user_id"], [])
            if h["ts"] < task_ts and h["asin"] != target_asin
        ]
        recommend_test.append({
            "user_id": r["user_id"],
            "task": r["task"],
            "timestamp": task_ts,
            "target_asin": target_asin,
            "target_title": pi.get("title", ""),
            "target_category": pi.get("main_category", ""),
            "visible_history": visible_history,
        })

    profiles = {uid: v.get("user_profile", v) for uid, v in profiles_raw.items()}

    return {
        "schema_version": 2,
        "history_policy": {
            "scope": "per_recommendation_task",
            "timestamp_unit": "unix_milliseconds",
            "predicate": "history.ts < task.timestamp",
            "target_asin_excluded": True,
        },
        "recommend_test": recommend_test,
        "profiles": profiles,
        "catalog": catalog,
    }


def _reload_benchmark(compact_path: Path):
    import os

    os.environ["PERSONALWAB_COMPACT"] = str(compact_path)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    # fresh import so the module-level _DATA cache reloads this file
    for m in list(sys.modules):
        if m.startswith("intro_specter"):
            del sys.modules[m]
    from intro_specter.benchmarks.personalwab_real import PersonalWABReal

    return PersonalWABReal


def verify_task_ids(compact_path: Path, artifact_jsonl: Path) -> bool:
    PersonalWABReal = _reload_benchmark(compact_path)

    want = set()
    for line in artifact_jsonl.open():
        line = line.strip()
        if line:
            want.add(json.loads(line)["task_id"])
    examples = list(PersonalWABReal(n_examples=60, seed=42, split="all"))
    got = {ex.task_id for ex in examples}
    missing, extra = want - got, got - want
    ok = len(examples) == len(got) == len(want) == 60 and not missing and not extra
    print(f"task-id check: {len(got & want)}/60 matched; "
          f"artifacts={len(want)} rebuilt={len(got)} "
          f"missing={len(missing)} extra={len(extra)}")
    if missing:
        print("  e.g. missing:", sorted(missing)[:5])
    if extra:
        print("  e.g. extra:", sorted(extra)[:5])
    return ok


def verify_no_target_leaks(compact_path: Path, n_examples: int = 60) -> bool:
    """Fail closed if sampled tasks expose their target ASIN or non-prior history."""
    PersonalWABReal = _reload_benchmark(compact_path)
    compact = json.loads(compact_path.read_text())
    rows = compact["recommend_test"]
    failures: list[str] = []
    examples = list(PersonalWABReal(n_examples=n_examples, seed=42, split="all"))

    for idx, ex in enumerate(examples):
        rng = random.Random(42 * 1_000_037 + idx)
        row = rows[rng.randint(0, len(rows) - 1)]
        target = row["target_asin"].upper()
        visible = row.get("visible_history")
        if not isinstance(visible, list):
            failures.append(f"{ex.task_id}: missing row-local visible_history")
            continue
        bad_ts = [h.get("ts") for h in visible
                  if not isinstance(h.get("ts"), int) or h["ts"] >= row["timestamp"]]
        raw_text = json.dumps(visible, sort_keys=True).upper()
        profile_text = "\n".join(span.text for span in ex.profile.spans).upper()
        if bad_ts:
            failures.append(f"{ex.task_id}: non-prior timestamps {bad_ts[:3]}")
        if target in raw_text:
            failures.append(f"{ex.task_id}: target ASIN in raw visible history")
        if target in profile_text:
            failures.append(f"{ex.task_id}: target ASIN in rendered profile/history")

    passed = len(examples) - len({f.split(":", 1)[0] for f in failures})
    print(f"target-ASIN leak check: {passed}/{len(examples)} tasks leak-free")
    for failure in failures[:10]:
        print("  ", failure)
    return len(examples) == n_examples and not failures


def verify_cache(compact_path: Path, cache_path: Path, model_key: str,
                 n_probe: int = 5) -> bool:
    import os
    import sqlite3

    os.environ["PERSONALWAB_COMPACT"] = str(compact_path)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    for m in list(sys.modules):
        if m.startswith("intro_specter"):
            del sys.modules[m]
    from intro_specter.benchmarks.personalwab_real import PersonalWABReal
    from intro_specter.models.cache import make_key
    from intro_specter.prompts import DIRECT_AGENT_SYSTEM, direct_agent_user
    from rebuttal_experiment_personalwab import MODEL_TABLE

    provider_name, model_id = MODEL_TABLE[model_key]
    conn = sqlite3.connect(cache_path)
    hits = probes = 0
    for ex in PersonalWABReal(n_examples=60, seed=42, split="all"):
        if probes >= n_probe:
            break
        probes += 1
        key = make_key(
            provider=provider_name,
            model=model_id,
            system=DIRECT_AGENT_SYSTEM,
            user=direct_agent_user(
                profile=ex.profile.model_dump(mode="json"), task=ex.task
            ),
            temperature=0.0,
            seed=0,
            max_tokens=8192,
        )
        row = conn.execute(
            "SELECT 1 FROM completions WHERE key = ?", (key,)
        ).fetchone()
        hits += bool(row)
        print(f"  probe {ex.task_id}: {'HIT' if row else 'miss'}")
    print(f"cache probe: {hits}/{probes} prime-call keys found")
    return hits == probes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", required=True,
                    help=".../PersonalWAB/envs/pwab/data of the cloned repo")
    ap.add_argument("--out", required=True)
    ap.add_argument("--feature-join", default="; ",
                    help="'; ' | ' ' | 'first' — how the original prep "
                         "flattened the features list (unknown; cache probe "
                         "arbitrates)")
    ap.add_argument("--history-order", default="raw", choices=["raw", "ts"])
    ap.add_argument("--verify-artifacts",
                    help="existing arm JSONL, e.g. outputs/rebuttal/"
                         "experiment_personalwab/llama-3.1-8b/direct.jsonl")
    ap.add_argument("--verify-cache",
                    help="FORENSIC ONLY: probe an old cache; clean builds are "
                         "expected to miss and should not use this as a gate")
    ap.add_argument("--verify-model", default="llama-3.1-8b")
    ap.add_argument("--verify-leaks", action="store_true",
                    help="fail unless all 60 sampled tasks have strictly prior "
                         "history and no target ASIN in visible profile/history")
    args = ap.parse_args()

    compact = build_compact(Path(args.raw_dir), args.feature_join, args.history_order)
    n_visible = sum(len(r["visible_history"]) for r in compact["recommend_test"])
    print(f"built: {len(compact['recommend_test'])} recommend_test rows, "
          f"{n_visible} task-local visible history entries, "
          f"{len(compact['profiles'])} profiles, {len(compact['catalog'])} products")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(compact))
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")

    ok = True
    if args.verify_artifacts:
        ok &= verify_task_ids(out, Path(args.verify_artifacts))
    if args.verify_leaks:
        ok &= verify_no_target_leaks(out)
    if args.verify_cache:
        ok &= verify_cache(out, Path(args.verify_cache), args.verify_model)
    if args.verify_artifacts or args.verify_leaks or args.verify_cache:
        print("VERIFICATION:", "PASS" if ok else "FAIL")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
