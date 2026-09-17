#!/usr/bin/env python3
"""Rebuild the PersonalWAB compact data file (compact_recommend.json).

The original compact file lived in a session /tmp scratchpad (default path in
intro_specter/benchmarks/personalwab_real.py) and was LOST when that
scratchpad was cleaned; the prep script that built it was never committed.
This script rebuilds it from the public benchmark repo and — crucially —
VERIFIES the rebuild against artifacts the original file produced:

  1. task-id check: PersonalWABReal(n=60, seed=42) over the rebuilt file must
     yield exactly the 60 task_ids present in
     outputs/rebuttal/experiment_personalwab/<model>/direct.jsonl
     (task ids embed both the sampled row index-selection and user ids, which
     depend on the row COUNT and ORDER of recommend_test — a strong check).
  2. cache-key probe: recompute the prime-call cache key (sha256 over
     provider/model/system/user/temperature/seed/max_tokens) for sampled
     examples and require hits in cache/completions_personalwab_<model>.sqlite.
     A hit proves the rebuilt profiles/prompts are BYTE-IDENTICAL to the
     originals.

Usage:
  git clone --depth 1 https://github.com/HongruCai/PersonalWAB.git /tmp/pwab
  python3 scripts/prep_personalwab_compact.py \
      --raw-dir /tmp/pwab/PersonalWAB/envs/pwab/data \
      --out data/personalwab/compact_recommend.json \
      --verify-artifacts outputs/rebuttal/experiment_personalwab/llama-1.1... \
      --verify-cache cache/completions_personalwab_llama-3.1-8b.sqlite \
      --verify-model llama-3.1-8b
  export PERSONALWAB_COMPACT=$PWD/data/personalwab/compact_recommend.json

If verification fails with one --feature-join / --history-order combination,
try the others (the original prep's exact formatting choices are unknown);
the cache probe is the arbiter.
"""

import argparse
import json
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

    recommend_test = []
    for r in ui["test"]:
        if r.get("type") != "recommend":
            continue
        pi = r["target"]["product_info"]
        recommend_test.append({
            "user_id": r["user_id"],
            "task": r["task"],
            "timestamp": r["timestamp"],
            "target_asin": pi["parent_asin"],
            "target_title": pi.get("title", ""),
            "target_category": pi.get("main_category", ""),
        })

    history = {}
    for uid, entries in history_raw.items():
        rows = []
        for e in entries:
            rev = e.get("review") or {}
            pi = e.get("product_info") or {}
            rows.append({
                "ts": rev.get("timestamp"),
                "asin": rev.get("parent_asin") or pi.get("parent_asin"),
                "title": pi.get("title", ""),
                "category": pi.get("main_category", ""),
                "rating": rev.get("rating"),
            })
        if history_order == "ts":
            rows.sort(key=lambda h: (h["ts"] is None, h["ts"]))
        history[uid] = rows

    profiles = {uid: v.get("user_profile", v) for uid, v in profiles_raw.items()}

    return {
        "recommend_test": recommend_test,
        "history": history,
        "profiles": profiles,
        "catalog": catalog,
    }


def verify_task_ids(compact_path: Path, artifact_jsonl: Path) -> bool:
    import os

    os.environ["PERSONALWAB_COMPACT"] = str(compact_path)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    # fresh import so the module-level _DATA cache reloads this file
    for m in list(sys.modules):
        if m.startswith("intro_specter"):
            del sys.modules[m]
    from intro_specter.benchmarks.personalwab_real import PersonalWABReal

    want = set()
    for line in artifact_jsonl.open():
        line = line.strip()
        if line:
            want.add(json.loads(line)["task_id"])
    got = {ex.task_id for ex in PersonalWABReal(n_examples=60, seed=42, split="all")}
    missing, extra = want - got, got - want
    print(f"task-id check: artifacts={len(want)} rebuilt={len(got)} "
          f"missing={len(missing)} extra={len(extra)}")
    if missing:
        print("  e.g. missing:", sorted(missing)[:5])
    return not missing


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
                    help="e.g. cache/completions_personalwab_llama-3.1-8b.sqlite")
    ap.add_argument("--verify-model", default="llama-3.1-8b")
    args = ap.parse_args()

    compact = build_compact(Path(args.raw_dir), args.feature_join, args.history_order)
    print(f"built: {len(compact['recommend_test'])} recommend_test rows, "
          f"{len(compact['history'])} users w/ history, "
          f"{len(compact['profiles'])} profiles, {len(compact['catalog'])} products")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(compact))
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")

    ok = True
    if args.verify_artifacts:
        ok &= verify_task_ids(out, Path(args.verify_artifacts))
    if args.verify_cache:
        ok &= verify_cache(out, Path(args.verify_cache), args.verify_model)
    if args.verify_artifacts or args.verify_cache:
        print("VERIFICATION:", "PASS" if ok else "FAIL")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
