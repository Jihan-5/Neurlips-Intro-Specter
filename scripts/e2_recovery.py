#!/usr/bin/env python3
"""Prepare, shard, execute, and integrity-merge amended E2 recovery v2."""
from __future__ import annotations

import argparse
import collections
import dataclasses
import fcntl
import hashlib
import json
import os
import shutil
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
SHARD_COUNTS = {cell: (2 if cell.startswith(("truthfulqa", "hotpotqa")) else 8) for cell in CELLS}
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
class TerminalSemanticFailure(InvalidParaphrase): pass


class ParaphraseProviderFailure(RuntimeError):
    def __init__(self, record: dict):
        self.record = record
        super().__init__(json.dumps(record, sort_keys=True))


def provider_error_record(exc: Exception) -> dict:
    response = getattr(exc, "response", None)
    status = getattr(exc, "status_code", None) or getattr(response, "status_code", None)
    try: status = int(status) if status is not None else None
    except (TypeError, ValueError): status = None
    name = type(exc).__name__
    transient = bool(status in {408, 409, 425, 429} or (status is not None and status >= 500)
                     or any(token in name.lower() for token in ("timeout", "connection", "ratelimit")))
    return {"exception_type": name, "http_status": status,
            "message": str(exc)[:2000], "transient": transient}


def is_provider_exception(exc: Exception) -> bool:
    info = provider_error_record(exc)
    name = info["exception_type"].lower()
    return info["http_status"] is not None or any(
        token in name for token in ("api", "provider", "timeout", "connection", "ratelimit")
    )


class ParaphraseLedger:
    """Append-only, shard-owned semantic-attempt budget across process restarts."""
    def __init__(self, path: Path):
        self.path = path
        self.records: list[dict] = []
        if path.exists():
            with path.open() as handle:
                for line_no, line in enumerate(handle, 1):
                    try: self.records.append(json.loads(line))
                    except json.JSONDecodeError as exc:
                        raise RuntimeError(f"malformed paraphrase ledger {path}:{line_no}") from exc

    @staticmethod
    def key(task: str, variant: int, span: str) -> tuple[str, int, str]:
        return str(task), int(variant), str(span)

    def for_unit(self, task: str, variant: int, span: str) -> list[dict]:
        key = self.key(task, variant, span)
        return [row for row in self.records
                if self.key(row["task_id"], row["variant_idx"], row["span_id"]) == key]

    def append(self, row: dict) -> None:
        row = {**row, "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as handle:
            handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
            handle.flush(); os.fsync(handle.fileno())
        self.records.append(row)

    def semantic_attempts(self, task: str, variant: int, span: str) -> list[dict]:
        by_index: dict[int, dict] = {}
        for row in self.for_unit(task, variant, span):
            if row.get("event") not in {"semantic_attempt", "semantic_attempt_imported_v1"}: continue
            index = int(row["attempt_index"])
            if index in by_index and by_index[index].get("candidate_text") != row.get("candidate_text"):
                raise RuntimeError(f"conflicting persisted paraphrase attempt for {(task, variant, span, index)}")
            by_index[index] = row
        return [by_index[index] for index in sorted(by_index)]

    def accepted(self, canonical: str, task: str, variant: int, span: str) -> dict | None:
        for row in self.semantic_attempts(task, variant, span):
            surface = str(row.get("candidate_text") or "")
            if validate(canonical, surface)[0]: return row
        return None

    def terminal(self, task: str, variant: int, span: str) -> bool:
        return any(row.get("event") == "terminal_semantic_failure"
                   for row in self.for_unit(task, variant, span))


def generated_paraphraser(provider, ledger: ParaphraseLedger):
    def call(text: str, task: str, variant: int, span: str):
        accepted = ledger.accepted(text, task, variant, span)
        if accepted is not None:
            return (str(accepted["candidate_text"]), int(accepted.get("tokens_input", 0)),
                    int(accepted.get("tokens_output", 0)))
        attempts = ledger.semantic_attempts(task, variant, span)
        if ledger.terminal(task, variant, span) or len(attempts) >= PARAPHRASE_RETRIES:
            raise TerminalSemanticFailure(f"persisted terminal semantic failure: {(task, variant, span)}")
        last = list(attempts[-1].get("failures", [])) if attempts else []
        for attempt in range(len(attempts), PARAPHRASE_RETRIES):
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
            except Exception as exc:
                error = {"event": "provider_failure", "task_id": task,
                         "variant_idx": variant, "span_id": span,
                         "canonical_text": text, "attempt_index": attempt,
                         "provider_error": provider_error_record(exc)}
                ledger.append(error)
                raise ParaphraseProviderFailure(error) from exc
            record = {"event": "semantic_attempt", "task_id": task,
                      "variant_idx": variant, "span_id": span,
                      "canonical_text": text, "attempt_index": attempt,
                      "candidate_text": surface, "failures": last, "accepted": ok,
                      "tokens_input": completion.tokens_input,
                      "tokens_output": completion.tokens_output}
            ledger.append(record)
            if ok: return surface, completion.tokens_input, completion.tokens_output
            attempts.append(record)
        terminal = {"event": "terminal_semantic_failure", "task_id": task,
                    "variant_idx": variant, "span_id": span,
                    "canonical_text": text, "semantic_attempts": len(attempts),
                    "failures": last}
        ledger.append(terminal)
        raise TerminalSemanticFailure(json.dumps(terminal))
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
    paraphrase_path = shard_root / f"shard-{shard_index:03d}-of-{num_shards:03d}.paraphrases.jsonl"
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
    paraphrase_ledger = ParaphraseLedger(paraphrase_path)
    allowed_tasks = set(protocol["expected_task_ids"])
    examples = [example for example in boot.expa._load_examples(dataset, 60)
                if example.task_id in allowed_tasks]
    provider_failure: dict | None = None
    terminal_units: set[tuple[str, int, str]] = set()
    with out.open("a") as handle, err_path.open("a") as err_handle:
        for example in examples:
            if provider_failure: break
            for variant in range(protocol["n_variants"]):
                if shard_for(example.task_id, variant, num_shards) != shard_index: continue
                pending = [arm for arm in ARMS if (example.task_id, variant, arm) not in done]
                if not pending: continue
                profile_record = profiles.get((example.task_id, variant))
                if profile_record:
                    for redraw in profile_record["redrawn"]:
                        if not validate(redraw["canonical_text"], redraw["surface_text"])[0]:
                            raise RuntimeError("stored fixed profile fails current semantic validation")
                paraphraser = (fixed_paraphraser(profile_record["redrawn"])
                               if profile_record else generated_paraphraser(provider, paraphrase_ledger))
                try: variant_example, info = boot.make_variant(example, dataset, variant, paraphraser)
                except TerminalSemanticFailure as exc:
                    unit = (example.task_id, variant, "profile")
                    terminal_units.add(unit)
                    err_handle.write(json.dumps({"kind": "terminal_semantic_failure",
                        "task_id": example.task_id, "variant_idx": variant,
                        "error": str(exc)}, sort_keys=True) + "\n")
                    err_handle.flush(); continue
                except ParaphraseProviderFailure as exc:
                    provider_failure = exc.record
                    err_handle.write(json.dumps({"kind": "paraphrase_provider_error",
                        **exc.record}, sort_keys=True) + "\n")
                    err_handle.flush(); break
                if profile_record and info["profile_hash"] != profile_record["profile_hash"]: raise RuntimeError("replayed profile hash changed")
                try:
                    primed, prime_in, prime_out = boot.expa._with_retry(lambda: boot.expa._prime_trajectory(
                        variant_example, provider_name=eval_provider, model=model_id, seed=boot.GEN_SEED, cache=cache),
                        label=f"recovery prime {cell} {example.task_id} v{variant}")
                except Exception as exc:
                    info = provider_error_record(exc)
                    kind = "prime_provider_error" if is_provider_exception(exc) else "prime_error"
                    err_handle.write(json.dumps({"kind":kind,"task_id":example.task_id,
                        "variant_idx":variant,"error":repr(exc),
                        "provider_error":info if kind.endswith("provider_error") else None})+"\n")
                    err_handle.flush()
                    if kind.endswith("provider_error"):
                        provider_failure = {"event": kind, "provider_error": info}
                        break
                    continue
                runners = {
                    "direct": lambda: {"final_trajectory":primed,"method_believed_success":None,"tokens_input":0,"tokens_output":0,"abstained":None,"meta_summary":{}},
                    "reflexion": lambda: boot.expa._run_reflexion_arm(variant_example, primed, provider_name=eval_provider, model=model_id, seed=boot.GEN_SEED, cache=cache),
                    "intro_specter": lambda: boot.expa._run_intro_specter_arm(variant_example, primed, provider_name=eval_provider, model=model_id, seed=boot.GEN_SEED, cache=cache, tau_abstain=0.0),
                }
                for arm in pending:
                    try: arm_out = boot.expa._with_retry(runners[arm], label=f"recovery {arm} {cell} {example.task_id} v{variant}")
                    except Exception as exc:
                        info = provider_error_record(exc)
                        kind = "arm_provider_error" if is_provider_exception(exc) else "arm_error"
                        err_handle.write(json.dumps({"kind":kind,"task_id":example.task_id,
                            "variant_idx":variant,"arm":arm,"error":repr(exc),
                            "provider_error":info if kind.endswith("provider_error") else None})+"\n")
                        err_handle.flush()
                        if kind.endswith("provider_error"):
                            provider_failure = {"event": kind, "provider_error": info}
                            break
                        continue
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
                if provider_failure: break
    if provider_failure:
        provider_info = provider_failure["provider_error"]
        shard_state = "provider_retryable" if provider_info["transient"] else "provider_blocked"
    elif terminal_units:
        shard_state = "blocked_terminal_semantic"
    else:
        shard_state = "blocked" if err_path.exists() and err_path.stat().st_size else "complete"
    state = {
        "cell": cell, "shard_index": shard_index, "num_shards": num_shards,
        "state": shard_state,
        "rows": sum(len(copies) for copies in read_rows(out)[0].values()),
        "error_rows": sum(1 for line in err_path.read_text().splitlines() if line.strip()),
        "terminal_semantic_units": len(terminal_units),
        "provider_failure": provider_failure,
        "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (shard_root / f"shard-{shard_index:03d}-of-{num_shards:03d}.state.json").write_text(
        json.dumps(state, indent=2) + "\n")
    if state["state"] != "complete":
        raise SystemExit(2)


def migrate_retry_ledgers(audit_path: Path, output_root: Path = RECOVERY,
                          verify_only: bool = False) -> dict:
    """Import v1 candidates, preserve failed attempts, and activate protocol v2."""
    audit = json.loads(audit_path.read_text())
    current_hash = protocol_hash()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    ledger_rows: dict[Path, list[dict]] = collections.defaultdict(list)
    imported = collections.Counter()

    # Existing accepted rows remain immutable, but every effective redraw must
    # pass the complete v2 validator before its legacy protocol hash is allowed.
    legacy_hashes: set[str] = set()
    accepted_rows = 0
    accepted_rows_seen = 0
    invalid_accepted: list[dict] = []
    invalid_accepted_keys: dict[Path, set[tuple[str, int, str]]] = collections.defaultdict(set)
    for cell in CELLS:
        root = output_root / cell
        sources = [root / "salvaged.jsonl", *[
            root / "shards" / f"shard-{index:03d}-of-{SHARD_COUNTS[cell]:03d}.jsonl"
            for index in range(SHARD_COUNTS[cell])
        ]]
        for source in sources:
            parsed, malformed = read_rows(source)
            if malformed: raise RuntimeError(f"cannot migrate malformed accepted rows: {source}")
            for copies in parsed.values():
                for _, row in copies:
                    accepted_rows_seen += 1
                    redraws = row.get("effective_redrawn")
                    if not isinstance(redraws, list) or not redraws:
                        raise RuntimeError(f"accepted row lacks redraw audit evidence: {source}")
                    row_failures = []
                    for redraw in redraws:
                        ok, failures = validate(redraw["canonical_text"], redraw["surface_text"])
                        if not ok:
                            row_failures.append({"span_id": redraw.get("span_id"),
                                                 "canonical_text": redraw["canonical_text"],
                                                 "surface_text": redraw["surface_text"],
                                                 "failures": failures})
                    if row_failures:
                        key = (str(row["task_id"]), int(row["variant_idx"]), str(row["arm"]))
                        invalid_accepted_keys[source].add(key)
                        invalid_accepted.append({"source": str(source.relative_to(ROOT)),
                                                 "task_id": key[0], "variant_idx": key[1],
                                                 "arm": key[2], "failures": row_failures})
                        continue
                    if row.get("recovery_protocol_sha256"):
                        legacy_hashes.add(str(row["recovery_protocol_sha256"]))
                    accepted_rows += 1

    for unit in audit["logical_units"]:
        cell = str(unit["cell"]); task = str(unit["task_id"])
        variant = int(unit["variant_idx"]); span = str(unit["span_id"])
        canonical = str(unit["canonical_text"])
        shard = shard_for(task, variant, SHARD_COUNTS[cell])
        ledger_path = (output_root / cell / "shards"
                       / f"shard-{shard:03d}-of-{SHARD_COUNTS[cell]:03d}.paraphrases.jsonl")
        accepted = False; semantic_count = 0
        for attempt in unit.get("attempts", []):
            if attempt.get("cache_status") != "found": break
            surface = str(attempt.get("candidate_text") or "")
            ok, failures = validate(canonical, surface)
            ledger_rows[ledger_path].append({
                "event": "semantic_attempt_imported_v1", "task_id": task,
                "variant_idx": variant, "span_id": span, "canonical_text": canonical,
                "attempt_index": semantic_count, "candidate_text": surface,
                "failures": failures, "accepted": ok,
                "v1_request_sha256": attempt.get("request_sha256"),
                "v1_cache_source": attempt.get("cache_source"),
                "v1_failures": attempt.get("v1_failures", []),
                "recorded_utc": now,
            })
            semantic_count += 1; imported["semantic_attempts"] += 1
            if ok:
                accepted = True; imported["accepted_cached_units"] += 1
                break
        if not accepted and semantic_count >= PARAPHRASE_RETRIES:
            ledger_rows[ledger_path].append({
                "event": "terminal_semantic_failure", "task_id": task,
                "variant_idx": variant, "span_id": span, "canonical_text": canonical,
                "semantic_attempts": semantic_count, "source": "v1_cache_revalidation",
                "recorded_utc": now,
            })
            imported["terminal_semantic_units"] += 1
        elif not accepted:
            imported["retryable_units"] += 1

    report = {"created_utc": now, "protocol_version": "AMENDED_RECOVERY_V2",
              "protocol_sha256": current_hash, "legacy_protocol_sha256": sorted(legacy_hashes),
              "accepted_rows_seen": accepted_rows_seen,
              "accepted_rows_revalidated": accepted_rows,
              "invalid_accepted_rows_removed": invalid_accepted,
              "imported": dict(imported),
              "ledger_files": len(ledger_rows), "source_audit": str(audit_path.relative_to(ROOT)),
              "source_audit_sha256": sha(audit_path), "verify_only": verify_only}
    if verify_only:
        print(json.dumps(report, indent=2))
        return report

    for path, rows in ledger_rows.items():
        if path.exists() and path.stat().st_size:
            existing = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
            if existing != rows:
                raise RuntimeError(f"non-idempotent ledger migration target: {path}")
            continue
        dump_jsonl(path, rows)

    archived = []
    # Preserve the complete original source byte-for-byte, then remove only
    # rows that demonstrably fail v2. Retained lines are copied verbatim.
    for source, rejected in invalid_accepted_keys.items():
        target = (source.parent / "failed_attempts"
                  / f"{source.name}.pre-v2-invalid-accepted")
        target.parent.mkdir(parents=True, exist_ok=True)
        original = source.read_bytes()
        if target.exists():
            if target.read_bytes() != original:
                raise RuntimeError(f"invalid-accepted archive conflict: {target}")
        else:
            target.write_bytes(original)
        retained = []
        for raw in original.splitlines(keepends=True):
            row = json.loads(raw)
            key = (str(row["task_id"]), int(row["variant_idx"]), str(row["arm"]))
            if key not in rejected:
                retained.append(raw)
        source.write_bytes(b"".join(retained))
        archived.append(str(target.relative_to(ROOT)))

    for cell in CELLS:
        root = output_root / cell; shard_root = root / "shards"
        for suffix in ("errors.jsonl", "state.json"):
            for source in sorted(shard_root.glob(f"shard-*.{suffix}")):
                target = shard_root / "failed_attempts" / f"{source.stem}.pre-v2.{source.suffix.lstrip('.')}"
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    if sha(target) != sha(source):
                        raise RuntimeError(f"migration archive conflict: {target}")
                    source.unlink()
                else:
                    shutil.move(str(source), str(target))
                archived.append(str(target.relative_to(ROOT)))
        cache_root = ROOT / "cache/e2_recovery_v1" / cell
        for database in sorted(cache_root.glob("shard-*-of-*.sqlite")):
            for sidecar in ("", "-wal", "-shm"):
                source = Path(str(database) + sidecar)
                if not source.exists(): continue
                target = (cache_root / "failed_attempts"
                          / f"{database.stem}.pre-v2.sqlite{sidecar}")
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    if sha(target) != sha(source): raise RuntimeError(f"migration cache conflict: {target}")
                    source.unlink()
                else:
                    shutil.move(str(source), str(target))
                archived.append(str(target.relative_to(ROOT)))

        protocol_path = root / "protocol.json"
        protocol = json.loads(protocol_path.read_text())
        old = str(protocol.get("protocol_sha256", ""))
        if old and old != current_hash: legacy_hashes.add(old)
        protocol.update(protocol_version="AMENDED_RECOVERY_V2",
                        protocol_sha256=current_hash,
                        accepted_legacy_protocol_sha256=sorted(legacy_hashes),
                        retry_budget_scope="cell|task_id|variant_idx|span_id",
                        retry_budget_total=PARAPHRASE_RETRIES,
                        retry_migration_audit=str(audit_path.relative_to(ROOT)))
        protocol_path.write_text(json.dumps(protocol, indent=2) + "\n")

    manifest_path = output_root / "prepare_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest.update(protocol_sha256=current_hash, protocol_version="AMENDED_RECOVERY_V2",
                    accepted_legacy_protocol_sha256=sorted(legacy_hashes),
                    retry_migration_audit=str(audit_path.relative_to(ROOT)))
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    campaign_path = ROOT / "outputs/jazz/e2_recovery_campaign_state.json"
    if campaign_path.exists():
        campaign = json.loads(campaign_path.read_text())
        for record in campaign.get("jobs", {}).values():
            record.update(attempts=0, pid=None, migrated_retry_v2_utc=now)
        campaign["retry_protocol_version"] = "AMENDED_RECOVERY_V2"
        campaign["samples"] = []
        campaign["provider_health"] = {}
        campaign_path.write_text(json.dumps(campaign, indent=2) + "\n")

    report["archived_files"] = archived
    target = ROOT / "outputs/jazz/e2_retry_migration_report.json"
    target.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2)); return report


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
            allowed_hashes = {protocol_hash(), *protocol.get("accepted_legacy_protocol_sha256", [])}
            if row.get("recovery_protocol_sha256") not in allowed_hashes:
                invalid.append({"key":key,"reason":"protocol_hash"})
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
    mig=sub.add_parser("migrate-retry-ledgers");mig.add_argument("--audit",type=Path,default=ROOT/"outputs/jazz/e2_retry_convergence_audit.json");mig.add_argument("--output-root",type=Path,default=RECOVERY);mig.add_argument("--verify-only",action="store_true")
    args=ap.parse_args()
    if args.cmd=="prepare": prepare(args.limit_variants,args.limit_tasks,args.output_root)
    elif args.cmd=="migrate-retry-ledgers": migrate_retry_ledgers(args.audit,args.output_root,args.verify_only)
    elif args.cmd=="worker": worker(args.cell,args.shard_index,args.num_shards,args.output_root)
    else: merge(args.cell,args.num_shards,args.output_root)


if __name__=="__main__": main()
