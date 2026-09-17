#!/usr/bin/env python3
"""Count recovery only for paired clean-solved, corrupted-default-failed tasks."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def aggregate_cell(cell):
    protocol = json.loads((cell / 'protocol.json').read_text())
    records = {}
    duplicates = 0
    for line in (cell / 'paired.jsonl').read_text().splitlines():
        row = json.loads(line)
        key = (row['task_id'], row['seed'], row['rho'], row['allow_profile_candidates'])
        if key in records:
            if records[key] != row:
                raise ValueError(f'Conflicting duplicate {cell.name}: {key}')
            duplicates += 1
        records[key] = row
    counts = dict(cell=cell.name, rows=len(records), expected=len(protocol['expected_tasks']) * 5,
                  paired=0, eligible=0, recovered=0, regressions=0, missing_pairs=0,
                  added_candidates=0, duplicate_rows=duplicates)
    for task in protocol['expected_tasks']:
        clean = records.get((task, 0, 0.0, False))
        for rho in (0.1, 0.3):
            baseline = records.get((task, 0, rho, False))
            mechanism = records.get((task, 0, rho, True))
            if clean is None or baseline is None or mechanism is None:
                counts['missing_pairs'] += 1
                continue
            if baseline['prime_hash'] != mechanism['prime_hash']:
                raise ValueError(f'Unpaired initial trajectories: {cell.name}/{task}/{rho}')
            if baseline['corrupted_constraint_ids'] != mechanism['corrupted_constraint_ids']:
                raise ValueError('Unpaired corruption')
            counts['paired'] += 1
            counts['added_candidates'] += bool(set(mechanism['candidate_ids']) - set(baseline['candidate_ids']))
            counts['regressions'] += baseline['true_success'] and not mechanism['true_success']
            if clean['true_success'] and not baseline['true_success'] and baseline['corrupted_constraint_ids']:
                counts['eligible'] += 1
                counts['recovered'] += mechanism['true_success']
    counts['complete'] = counts['rows'] == counts['expected'] and counts['missing_pairs'] == 0
    counts['recovery_rate'] = counts['recovered'] / counts['eligible'] if counts['eligible'] else None
    counts['error_attempts'] = sum(1 for _ in (cell / 'errors.jsonl').open()) if (cell / 'errors.jsonl').exists() else 0
    return counts


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=Path('outputs/rebuttal/profile_candidacy'))
    ap.add_argument('--output', type=Path)
    ap.add_argument('--require-complete', action='store_true')
    args = ap.parse_args()
    cells = [aggregate_cell(c) for c in sorted(args.root.glob('*__*')) if (c / 'paired.jsonl').exists()]
    pooled = {k: sum(c[k] for c in cells) for k in ['rows', 'expected', 'paired', 'eligible', 'recovered', 'regressions', 'missing_pairs', 'added_candidates', 'error_attempts']}
    pooled['recovery_rate'] = pooled['recovered'] / pooled['eligible'] if pooled['eligible'] else None
    report = dict(cells=cells, pooled=pooled, complete=len(cells) == 10 and all(c['complete'] for c in cells),
                  caveat='Clean-solved corruption-associated failures; the original diagnostic does not establish 100% causal node traceability. Default code already includes profile ancestors.')
    text = json.dumps(report, indent=2) + '\n'
    print(text, end='')
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(text)
    if args.require_complete and not report['complete']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
