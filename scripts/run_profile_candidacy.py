#!/usr/bin/env python3
"""E3 paired recovery study. Separate artifacts; no writes to Experiment A/E2.

Seed 0, benchmark seed 42, tau=0. In each cell run a contemporaneous rho=0
default control and both default/extended candidate sets at rho=.1 and .3.
The prime and all unchanged prompts are cached identically between arms.
Qwen is replaced by Llama 3.1 8B; archival Qwen is never pooled as that model.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import rebuttal_experiment_a as expa
from intro_specter.models import SQLiteCache


def run_cell(dataset, model, root, cache_path, *, smoke=False):
    cell = root / f"{dataset}__{model}"
    cell.mkdir(parents=True, exist_ok=True)
    lock = (cell / '.writer.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    provider, model_id = expa.MODEL_TABLE[model]
    cache = SQLiteCache(cache_path)
    examples = expa._load_examples(dataset, expa.DATASET_REGISTRY[dataset]['n_examples'])
    if smoke:
        examples = examples[:2]  # Same production task IDs, never n_examples=2.
    protocol = dict(dataset=dataset, model=model, model_id=model_id, seed=0,
                    benchmark_seed=42, tau_abstain=0.0, rhos=[0.0, 0.1, 0.3],
                    expected_tasks=[e.task_id for e in examples],
                    mechanism='all_profile_nodes_v1', smoke=smoke,
                    qwen_substitution='llama-3.1-8b',
                    candidate_note='Default already admits profile ancestors; flag adds remaining profile nodes.')
    manifest = cell / 'protocol.json'
    if manifest.exists() and json.loads(manifest.read_text()) != protocol:
        raise ValueError(f'Protocol changed: use a separate output root: {cell}')
    manifest.write_text(json.dumps(protocol, indent=2) + '\n')
    path = cell / 'paired.jsonl'
    done = {}
    if path.exists():
        for line in path.read_text().splitlines():
            r = json.loads(line)
            done[(r['task_id'], r['rho'], r['allow_profile_candidates'])] = r
    errors = 0
    with path.open('a') as output, (cell / 'errors.jsonl').open('a') as error_file:
        for example in examples:
            for rho in protocol['rhos']:
                flags = [False] if rho == 0 else [False, True]
                pending = [flag for flag in flags if (example.task_id, rho, flag) not in done]
                if not pending:
                    continue
                profile, ids = (example.profile, []) if rho == 0 else expa.corrupt_profile(
                    example.profile, rho, expa._corruption_seed(example.task_id, 0, rho),
                    expa._constraint_meta(example))
                corrupted = replace(example, profile=profile)
                try:
                    primed, prime_in, prime_out = expa._with_retry(lambda: expa._prime_trajectory(
                        corrupted, provider_name=provider, model=model_id, seed=0, cache=cache))
                    if not primed.final_output.strip():
                        raise ValueError('Empty prime output')
                    prime_hash = hashlib.sha256(primed.model_dump_json().encode()).hexdigest()
                    for flag in pending:
                        result = expa._with_retry(lambda: expa._run_intro_specter_arm(
                            corrupted, primed, provider_name=provider, model=model_id, seed=0,
                            cache=cache, tau_abstain=0.0, allow_profile_candidates=flag))
                        final = result.pop('final_trajectory')
                        if not final.final_output.strip():
                            raise ValueError('Empty mechanism output')
                        row = dict(task_id=example.task_id, seed=0, rho=rho,
                                   allow_profile_candidates=flag, prime_hash=prime_hash,
                                   corrupted_constraint_ids=ids, true_success=expa._true_success(example, final),
                                   final_output=final.final_output, **result)
                        row['tokens_input'] += prime_in
                        row['tokens_output'] += prime_out
                        output.write(json.dumps(row) + '\n'); output.flush()
                        done[(example.task_id, rho, flag)] = row
                        print(example.task_id, rho, flag, row['true_success'], flush=True)
                except Exception as exc:
                    errors += 1
                    error_file.write(json.dumps(dict(task_id=example.task_id, rho=rho,
                                                    error=type(exc).__name__, message=str(exc)[:500])) + '\n')
                    error_file.flush()
                    print('[ERROR]', example.task_id, rho, type(exc).__name__, flush=True)
    expected = len(examples) * 5
    print(f'rows={len(done)}/{expected} errors_this_pass={errors}', flush=True)
    return 0 if len(done) == expected else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dataset', required=True, choices=list(expa.DATASET_REGISTRY))
    ap.add_argument('--model', required=True, choices=['llama-3.1-8b', 'mistral-nemo-12b'])
    ap.add_argument('--allow-profile-candidates', action='store_true', required=True,
                    help='Explicitly authorize the paired opt-in mechanism arm')
    ap.add_argument('--output-dir', type=Path, default=Path('outputs/rebuttal/profile_candidacy'))
    ap.add_argument('--cache-path', required=True)
    ap.add_argument('--smoke', action='store_true')
    args = ap.parse_args()
    raise SystemExit(run_cell(args.dataset, args.model, args.output_dir, args.cache_path, smoke=args.smoke))


if __name__ == '__main__':
    main()
