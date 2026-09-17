#!/usr/bin/env python3
"""Prepare, shard, execute, and integrity-merge amended E2 recovery v1."""
from __future__ import annotations

import argparse
import collections
import dataclasses
import fcntl
import hashlib
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import profile_bootstrap_study as boot
from e2_recovery_semantics import validate
from intro_specter.models import SQLiteCache, build_provider
from intro_specter.models.base import CompletionResult
from intro_specter.models.cache import make_key

ROOT = Path(__file__).resolve().parents[1]
FAILED = ROOT / "outputs/rebuttal/profile_bootstrap"
RECOVERY = ROOT / "outputs/rebuttal/profile_bootstrap_recovery_v1"
PROTOCOL = ROOT / "orchestration/e2_recovery_protocol.md"
FREEZE_MANIFEST = ROOT / "outputs/jazz/e2_failed_run_freeze_manifest.json"
ARMS = boot.ARMS
DATASETS = ["truthfulqa_real", "hotpotqa_real", "twowiki_real", "musique_real", "longmemeval_real"]
MODELS = ["llama-3.1-8b", "mistral-nemo-12b"]
CELLS = [f"{dataset}__{model}" for dataset in DATASETS for model in MODELS]
PROOF_LOGS = {
    "truthfulqa_real__llama-3.1-8b": "bootstrap_tqa_llama.log",
    "truthfulqa_real__mistral-nemo-12b": "bootstrap_tqa_mistral.log",
    "hotpotqa_real__llama-3.1-8b": "bootstrap_hotpotqa_real_llama-3.1-8b.log",
    "hotpotqa_real__mistral-nemo-12b": "bootstrap_hotpotqa_real_mistral-nemo-12b.log",
    "twowiki_real__llama-3.1-8b": "bootstrap_twowiki_real_llama-3.1-8b.log",
    "twowiki_real__mistral-nemo-12b": "bootstrap_twowiki_real_mistral-nemo-12b.log",
    "musique_real__llama-3.1-8b": "bootstrap_musique_real_llama-3.1-8b.log",
    "musique_real__mistral-nemo-12b": "bootstrap_musique_real_mistral-nemo-12b.log",
    "longmemeval_real__llama-3.1-8b": "bootstrap_lme_llama.log",
    "longmemeval_real__mistral-nemo-12b": "bootstrap_longmemeval_real_mistral-nemo-12b.log",
}
PARAPHRASE_RETRIES = 3
RECOVERY_SYSTEM = (
    "Rewrite one structured user constraint with different wording and exactly equivalent meaning. "
    "Preserve every number, range, negation, prohibition, required action, response-format/style "
    "requirement, named/categorical value, clause, and meaning-bearing domain term. Do not summarize "
    "or weaken it. Preserve who must act: an instruction about the response must remain an "
    "instruction to the assistant, never an action attributed to the user. One English sentence. "
    "JSON only: {\"paraphrase\": \"...\"}."
)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): h.update(chunk)
    return h.hexdigest()


def protocol_hash() -> str:
    digest = hashlib.sha256()
    for path in (PROTOCOL, Path(__file__), Path(__file__).with_name("e2_recovery_semantics.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def shard_for(task_id: str, variant_idx: int, count: int) -> int:
    digest = hashlib.sha256(f"{task_id}|{variant_idx}".encode()).hexdigest()
    return int(digest[:16], 16) % count


def cache_path(cell: str) -> Path:
    dataset, model = cell.split("__", 1)
    dedicated = ROOT / f"cache/bootstrap_{dataset}_{model}.sqlite"
    # The earliest TruthfulQA and remote-owned LongMemEval/Llama cells used
    # the repository's original shared cache before per-cell caches existed.
    return dedicated if dedicated.exists() else ROOT / "cache/completions.sqlite"


class ReadOnlyCache:
    def __init__(self, path: Path):
        self.path = path
        self.conn = (sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
                     if path.exists() else None)
    def get(self, key: str) -> CompletionResult | None:
        if self.conn is None: return None
        row = self.conn.execute("SELECT payload FROM completions WHERE key=?", (key,)).fetchone()
        if row is None: return None
        result = CompletionResult(**json.loads(row[0])); result.cache_hit = True
        return result


class LayeredCache:
    def __init__(self, old: Path, delta: Path):
        self.old = ReadOnlyCache(old); self.delta = SQLiteCache(delta)
    def get(self, key: str) -> CompletionResult | None:
        return self.delta.get(key) or self.old.get(key)
    def put(self, key: str, result: CompletionResult) -> None: self.delta.put(key, result)


def old_paraphrase(cache: ReadOnlyCache):
    provider, model = boot.expa.MODEL_TABLE["llama-3.1-8b"]
    def call(text: str, task: str, variant: int, span: str):
        key = make_key(provider=provider, model=model, system=boot.PARAPHRASE_SYSTEM,
                       user=f"Sentence: {text}", temperature=.7,
                       seed=boot._paraphrase_seed(task, variant, span), max_tokens=256)
        result = cache.get(key)
        if result is None: raise KeyError(key)
        surface = str(result.parse_json().get("paraphrase") or "").strip()
        if not surface or len(surface) > 4 * max(len(text), 40): raise ValueError("legacy fallback not exact")
        return surface, result.tokens_input, result.tokens_output
    return call


def read_rows(path: Path) -> tuple[dict[tuple[str, int, str], list[tuple[int, dict]]], int]:
    by: dict[tuple[str, int, str], list[tuple[int, dict]]] = collections.defaultdict(list)
    malformed = 0
    if not path.exists(): return by, malformed
    with path.open() as handle:
        for line_no, line in enumerate(handle, 1):
            try: row = json.loads(line)
            except json.JSONDecodeError: malformed += 1; continue
            try: key = (str(row["task_id"]), int(row["variant_idx"]), str(row["arm"]))
            except (KeyError, TypeError, ValueError): malformed += 1; continue
            by[key].append((line_no, row))
    return by, malformed


def dump_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w") as handle:
        for row in rows: handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
    tmp.replace(path)


def prepare(limit_variants: int | None = None, limit_tasks: int | None = None,
            output_root: Path = RECOVERY) -> dict:
    output_root.mkdir(parents=True, exist_ok=True)
    if boot.GEN_SEED != 0 or tuple(ARMS) != ("direct", "reflexion", "intro_specter"):
        raise RuntimeError("frozen E2 constants changed")
    frozen = {item["cell"]: item for item in json.loads(FREEZE_MANIFEST.read_text())["files"]}
    overall = {"protocol_sha256": protocol_hash(), "cells": [], "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    for cell in CELLS:
        dataset, model = cell.split("__", 1)
        examples = boot.expa._load_examples(dataset, 60)
        if limit_tasks: examples = examples[:limit_tasks]
        variants = range(min(100, limit_variants)) if limit_variants else range(100)
        expected_variants = {(example.task_id, v) for example in examples for v in variants}
        expected_keys = {(task, v, arm) for task, v in expected_variants for arm in ARMS}
        source = FAILED / cell / "variants.jsonl"
        source_rows, malformed = read_rows(source)
        source_digest = sha(source) if source.exists() else None
        if source_digest != frozen[cell]["sha256"]:
            raise RuntimeError(f"failed-run artifact changed after freeze: {cell}")
        proof_log = ROOT / "outputs/rebuttal/relaunch_logs" / PROOF_LOGS[cell]
        proof_text = proof_log.read_text(errors="replace")
        if f"for {dataset}, n_variants=100, paraphrase=True" not in proof_text:
            raise RuntimeError(f"historical launch proof missing frozen inputs: {cell}")
        ro = ReadOnlyCache(cache_path(cell)); replay = old_paraphrase(ro)
        example_by_id = {example.task_id: example for example in examples}
        profiles: list[dict] = []; salvage: list[dict] = []
        reasons = collections.Counter()
        for task, variant in sorted(expected_variants):
            candidate_keys = [(task, variant, arm) for arm in ARMS]
            if not any(key in source_rows for key in candidate_keys):
                reasons["no_historical_rows"] += 3; continue
            try:
                variant_example, info = boot.make_variant(example_by_id[task], dataset, variant, replay)
            except Exception as exc:
                reasons[f"profile_replay:{type(exc).__name__}"] += 3; continue
            failures = []
            for redraw in info["redrawn"]:
                ok, why = validate(redraw["canonical_text"], redraw["surface_text"])
                if not ok: failures.append({"span_id": redraw["span_id"], "failures": why})
            if failures:
                reasons["invalid_paraphrase"] += 3; continue
            profiles.append({"task_id": task, "variant_idx": variant, "profile_hash": info["profile_hash"],
                             "redrawn": info["redrawn"], "validation": "passed",
                             "effective_profile": variant_example.profile.model_dump(mode="json")})
            for key in candidate_keys:
                copies = source_rows.get(key, [])
                if not copies: reasons["missing_key"] += 1; continue
                first = copies[0][1]
                if any(row != first for _, row in copies[1:]): reasons["conflicting_duplicate"] += 1; continue
                if first.get("profile_hash") != info["profile_hash"]: reasons["profile_hash_mismatch"] += 1; continue
                if key not in expected_keys or first.get("paraphrased") is not True: reasons["protocol_mismatch"] += 1; continue
                row = dict(first)
                row.update(recovery_provenance="salvaged_verified", recovery_protocol_sha256=protocol_hash(),
                           source_artifact=str(source.relative_to(ROOT)), source_sha256=source_digest,
                           source_line_numbers=[line for line, _ in copies], effective_redrawn=info["redrawn"])
                salvage.append(row)
        cell_root = output_root / cell
        dump_jsonl(cell_root / "salvaged.jsonl", salvage)
        dump_jsonl(cell_root / "profiles.jsonl", profiles)
        protocol = {"cell": cell, "dataset": dataset, "model": model, "benchmark_seed": 42,
                    "generation_seed": 0, "tau_abstain": 0.0, "n_variants": len(variants),
                    "arms": list(ARMS), "expected_task_ids": [e.task_id for e in examples],
                    "expected_logical_units": len(expected_keys), "shard_formula": "sha256(task_id|variant_idx) mod num_shards",
                    "protocol_sha256": protocol_hash(), "source_artifact": str(source.relative_to(ROOT)),
                    "source_sha256": source_digest,
                    "historical_launch_log": str(proof_log.relative_to(ROOT)),
                    "historical_launch_log_sha256": sha(proof_log),
                    "historical_inputs_verified": {"dataset": dataset, "model": model,
                        "generation_seed": 0, "benchmark_seed": 42, "n_variants": 100,
                        "paraphrase": True, "tau_abstain": 0.0, "arms": list(ARMS)}}
        (cell_root / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")
        report = {"cell": cell, "expected": len(expected_keys), "salvaged": len(salvage),
                  "profiles_recovered": len(profiles), "source_malformed": malformed,
                  "not_salvaged": dict(reasons)}
        (cell_root / "prepare_report.json").write_text(json.dumps(report, indent=2) + "\n")
        overall["cells"].append(report); print(json.dumps(report), flush=True)
    (output_root / "prepare_manifest.json").write_text(json.dumps(overall, indent=2) + "\n")
    return overall


class InvalidParaphrase(RuntimeError): pass


def generated_paraphraser(provider, errors: list[dict]):
    def call(text: str, task: str, variant: int, span: str):
        last = []
        for attempt in range(PARAPHRASE_RETRIES):
            seed_hex = hashlib.sha256(f"{task}|bootstrap|{variant}|{span}|recovery-v1|{attempt}".encode()).hexdigest()
            seed = int(seed_hex[:8], 16)
            user = f"Canonical constraint: {text}"
            if last: user += "\nPrevious output failed deterministic checks: " + ", ".join(last) + ". Preserve those semantics explicitly."
            try:
                payload, completion = provider.complete_json(system=RECOVERY_SYSTEM, user=user,
                    model=boot.expa.MODEL_TABLE["llama-3.1-8b"][1], temperature=0.0,
                    seed=seed, max_tokens=256, retries=0)
                surface = str(payload.get("paraphrase") or "").strip()
                ok, last = validate(text, surface)
                if ok: return surface, completion.tokens_input, completion.tokens_output
            except Exception as exc: last = [f"provider:{type(exc).__name__}"]
        error = {"task_id": task, "variant_idx": variant, "span_id": span,
                 "canonical_text": text, "failures": last, "kind": "invalid_paraphrase_exhausted"}
        errors.append(error)
        raise InvalidParaphrase(json.dumps(error))
    return call


def fixed_paraphraser(redrawn: list[dict]):
    surfaces = {(item["span_id"], item["canonical_text"]): item["surface_text"] for item in redrawn}
    def call(text: str, task: str, variant: int, span: str):
        return surfaces[(span, text)], 0, 0
    return call


def worker(cell: str, shard_index: int, num_shards: int, output_root: Path = RECOVERY) -> None:
    dataset, model = cell.split("__", 1); cell_root = output_root / cell
    protocol = json.loads((cell_root / "protocol.json").read_text())
    if protocol["protocol_sha256"] != protocol_hash(): raise SystemExit("protocol hash changed")
    shard_root = cell_root / "shards"; shard_root.mkdir(parents=True, exist_ok=True)
    out = shard_root / f"shard-{shard_index:03d}-of-{num_shards:03d}.jsonl"
    err_path = shard_root / f"shard-{shard_index:03d}-of-{num_shards:03d}.errors.jsonl"
    lock = (shard_root / f"shard-{shard_index:03d}-of-{num_shards:03d}.lock").open("a")
    try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc: raise SystemExit("shard writer already active") from exc
    existing, malformed = read_rows(out)
    if malformed: raise SystemExit("malformed existing shard")
    salvage, _ = read_rows(cell_root / "salvaged.jsonl"); done = set(existing) | set(salvage)
    profiles = {(r["task_id"], r["variant_idx"]): r for r in map(json.loads, (cell_root / "profiles.jsonl").read_text().splitlines())}
    delta = ROOT / f"cache/e2_recovery_v1/{cell}/shard-{shard_index:03d}-of-{num_shards:03d}.sqlite"
    cache = LayeredCache(cache_path(cell), delta)
    eval_provider, model_id = boot.expa.MODEL_TABLE[model]
    provider = build_provider(boot.expa.MODEL_TABLE["llama-3.1-8b"][0], cache=cache)
    allowed_tasks = set(protocol["expected_task_ids"])
    examples = [example for example in boot.expa._load_examples(dataset, 60)
                if example.task_id in allowed_tasks]
    errors: list[dict] = []
    with out.open("a") as handle, err_path.open("a") as err_handle:
        for example in examples:
            for variant in range(protocol["n_variants"]):
                if shard_for(example.task_id, variant, num_shards) != shard_index: continue
                pending = [arm for arm in ARMS if (example.task_id, variant, arm) not in done]
                if not pending: continue
                profile_record = profiles.get((example.task_id, variant))
                paraphraser = fixed_paraphraser(profile_record["redrawn"]) if profile_record else generated_paraphraser(provider, errors)
                try: variant_example, info = boot.make_variant(example, dataset, variant, paraphraser)
                except InvalidParaphrase:
                    for error in errors: err_handle.write(json.dumps(error, sort_keys=True) + "\n")
                    err_handle.flush(); errors.clear(); continue
                if profile_record and info["profile_hash"] != profile_record["profile_hash"]: raise RuntimeError("replayed profile hash changed")
                try:
                    primed, prime_in, prime_out = boot.expa._with_retry(lambda: boot.expa._prime_trajectory(
                        variant_example, provider_name=eval_provider, model=model_id, seed=boot.GEN_SEED, cache=cache),
                        label=f"recovery prime {cell} {example.task_id} v{variant}")
                except Exception as exc:
                    err_handle.write(json.dumps({"kind":"prime_error","task_id":example.task_id,"variant_idx":variant,"error":repr(exc)})+"\n");err_handle.flush();continue
                runners = {
                    "direct": lambda: {"final_trajectory":primed,"method_believed_success":None,"tokens_input":0,"tokens_output":0,"abstained":None,"meta_summary":{}},
                    "reflexion": lambda: boot.expa._run_reflexion_arm(variant_example, primed, provider_name=eval_provider, model=model_id, seed=boot.GEN_SEED, cache=cache),
                    "intro_specter": lambda: boot.expa._run_intro_specter_arm(variant_example, primed, provider_name=eval_provider, model=model_id, seed=boot.GEN_SEED, cache=cache, tau_abstain=0.0),
                }
                for arm in pending:
                    try: arm_out = boot.expa._with_retry(runners[arm], label=f"recovery {arm} {cell} {example.task_id} v{variant}")
                    except Exception as exc:
                        err_handle.write(json.dumps({"kind":"arm_error","task_id":example.task_id,"variant_idx":variant,"arm":arm,"error":repr(exc)})+"\n");err_handle.flush();continue
                    row = {"task_id":example.task_id,"variant_idx":variant,"arm":arm,
                           "true_success":boot.expa._true_success(variant_example,arm_out["final_trajectory"]),
                           "method_believed_success":arm_out["method_believed_success"],
                           "tokens_input":arm_out["tokens_input"]+prime_in,"tokens_output":arm_out["tokens_output"]+prime_out,
                           "abstained":arm_out["abstained"],"profile_hash":info["profile_hash"],
                           "redrawn_span_ids":[r["span_id"] for r in info["redrawn"]],"banned_substrings":info["banned_substrings"],
                           "paraphrased":True,"meta_summary":arm_out["meta_summary"],"effective_redrawn":info["redrawn"],
                           "recovery_provenance":"rerun_recovery","recovery_protocol_sha256":protocol_hash(),
                           "source_artifact":None,"source_sha256":None,"shard_index":shard_index,"num_shards":num_shards}
                    handle.write(json.dumps(row, sort_keys=True, default=str)+"\n");handle.flush();done.add((example.task_id,variant,arm))
                    print(f"{cell} shard={shard_index}/{num_shards} {example.task_id} v={variant} {arm}",flush=True)
    state = {
        "cell": cell, "shard_index": shard_index, "num_shards": num_shards,
        "state": "blocked" if err_path.exists() and err_path.stat().st_size else "complete",
        "rows": sum(len(copies) for copies in read_rows(out)[0].values()),
        "error_rows": sum(1 for line in err_path.read_text().splitlines() if line.strip()),
        "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (shard_root / f"shard-{shard_index:03d}-of-{num_shards:03d}.state.json").write_text(
        json.dumps(state, indent=2) + "\n")
    if state["state"] == "blocked":
        raise SystemExit(2)


def merge(cell: str, num_shards: int, output_root: Path = RECOVERY) -> dict:
    root = output_root / cell; protocol = json.loads((root / "protocol.json").read_text())
    expected = {(task, v, arm) for task in protocol["expected_task_ids"] for v in range(protocol["n_variants"]) for arm in ARMS}
    sources = [root / "salvaged.jsonl"] + [root / "shards" / f"shard-{i:03d}-of-{num_shards:03d}.jsonl" for i in range(num_shards)]
    rows: dict[tuple, tuple[dict, str]] = {}; malformed=[]; overlaps=[]; invalid=[]
    for path in sources:
        parsed, bad = read_rows(path); malformed += [str(path)] * bad
        for key, copies in parsed.items():
            if len(copies)!=1: overlaps.append({"key":key,"source":str(path),"copies":len(copies)});continue
            row=copies[0][1]
            if key in rows: overlaps.append({"key":key,"sources":[rows[key][1],str(path)]});continue
            if row.get("recovery_protocol_sha256")!=protocol_hash(): invalid.append({"key":key,"reason":"protocol_hash"})
            if row.get("recovery_provenance") not in {"salvaged_verified", "rerun_recovery"}:
                invalid.append({"key":key,"reason":"provenance"})
            redraws = row.get("effective_redrawn")
            if not isinstance(redraws, list) or not redraws or not row.get("profile_hash"):
                invalid.append({"key":key,"reason":"required_fields"})
                redraws = []
            if path.name.startswith("shard-"):
                owner = int(path.name.split("-")[1])
                if shard_for(key[0], key[1], num_shards) != owner:
                    invalid.append({"key":key,"reason":"wrong_shard_owner"})
            for redraw in redraws:
                if not validate(redraw["canonical_text"],redraw["surface_text"])[0]: invalid.append({"key":key,"reason":"semantic_validation"})
            rows[key]=(row,str(path))
    missing=sorted(expected-set(rows)); unexpected=sorted(set(rows)-expected)
    hash_conflicts=[]
    by_variant=collections.defaultdict(set)
    for (task,v,_),(row,_) in rows.items(): by_variant[(task,v)].add(row.get("profile_hash"))
    for key,hashes in by_variant.items():
        if len(hashes)!=1: hash_conflicts.append({"variant":key,"hashes":sorted(hashes)})
    error_files=[]
    for path in (root/"shards").glob("*.errors.jsonl") if (root/"shards").exists() else []:
        if path.stat().st_size: error_files.append(str(path))
    complete=not(missing or unexpected or overlaps or malformed or invalid or hash_conflicts or error_files) and len(rows)==len(expected)
    report={"cell":cell,"complete":complete,"expected":len(expected),"completed":len(rows),
            "salvaged":sum(row[0].get("recovery_provenance")=="salvaged_verified" for row in rows.values()),
            "rerun":sum(row[0].get("recovery_provenance")=="rerun_recovery" for row in rows.values()),
            "missing":len(missing),"unexpected":len(unexpected),"overlaps":overlaps[:20],"malformed":malformed,
            "invalid":invalid[:20],"profile_hash_conflicts":hash_conflicts[:20],"error_files":error_files}
    (root/"integrity.json").write_text(json.dumps(report,indent=2,default=str)+"\n")
    if complete: dump_jsonl(root/"variants.jsonl",[rows[key][0] for key in sorted(expected)])
    print(json.dumps(report,indent=2,default=str)); return report


def main() -> None:
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    prep=sub.add_parser("prepare");prep.add_argument("--limit-variants",type=int);prep.add_argument("--limit-tasks",type=int);prep.add_argument("--output-root",type=Path,default=RECOVERY)
    work=sub.add_parser("worker");work.add_argument("--cell",required=True,choices=CELLS);work.add_argument("--shard-index",type=int,required=True);work.add_argument("--num-shards",type=int,required=True);work.add_argument("--output-root",type=Path,default=RECOVERY)
    mer=sub.add_parser("merge");mer.add_argument("--cell",required=True,choices=CELLS);mer.add_argument("--num-shards",type=int,required=True);mer.add_argument("--output-root",type=Path,default=RECOVERY)
    args=ap.parse_args()
    if args.cmd=="prepare": prepare(args.limit_variants,args.limit_tasks,args.output_root)
    elif args.cmd=="worker": worker(args.cell,args.shard_index,args.num_shards,args.output_root)
    else: merge(args.cell,args.num_shards,args.output_root)


if __name__=="__main__": main()
