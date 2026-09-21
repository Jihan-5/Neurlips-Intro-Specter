#!/usr/bin/env python3
"""Frozen profile-bootstrap analysis with explicit completeness and error accounting.

Includes every observed draw in the reported analysis; smoke-only tasks outside
production are counted as protocol deviations, never silently discarded. Partial
results are labeled provisional. Pooled effects pair by (cell, task, variant).
"""
from __future__ import annotations
import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

ARMS = ('direct', 'reflexion', 'intro_specter')
DATASETS = ('truthfulqa_real', 'longmemeval_real', 'musique_real', 'twowiki_real', 'hotpotqa_real')
MODELS = ('llama-3.1-8b', 'mistral-nemo-12b')


def _percentile(values, q):
    if not values:
        return None
    pos = q / 100 * (len(values) - 1)
    lo = int(pos); hi = min(lo + 1, len(values) - 1)
    return values[lo] * (hi - pos) + values[hi] * (pos - lo) if hi != lo else values[lo]


def summarize(per_arm):
    report = {'arms': {}}
    for arm, rows in per_arm.items():
        groups = defaultdict(list)
        for (task, variant), success in rows.items():
            groups[task].append(float(success))
        variances = [statistics.pvariance(v) for v in groups.values() if len(v) > 1]
        report['arms'][arm] = dict(n_rows=len(rows), n_examples=len(groups),
            mean_success=statistics.mean(rows.values()) if rows else None,
            mean_per_example_variance=statistics.mean(variances) if variances else None)
    keys = per_arm['intro_specter'].keys() & per_arm['reflexion'].keys()
    draws = defaultdict(list)
    for key in sorted(keys):
        draws[key[1]].append(int(per_arm['intro_specter'][key]) - int(per_arm['reflexion'][key]))
    effects = sorted(statistics.mean(v) for v in draws.values())
    if effects:
        favorable = sum(e >= 0 for e in effects) / len(effects)
        tail = effects[:max(1, len(effects) // 10)]
        report['contrast'] = dict(n_pairs=len(keys), n_draws=len(effects),
            mean=statistics.mean(effects), p2_5=_percentile(effects, 2.5),
            p97_5=_percentile(effects, 97.5), favorable_fraction=favorable,
            worst_decile_mean=statistics.mean(tail), worst_decile_min=min(tail),
            worst_decile_favorable=sum(e >= 0 for e in tail) / len(tail),
            hoeffding_bound=math.exp(-2 * len(effects) * max(0., favorable - .5) ** 2),
            pairs_per_draw={str(k): len(v) for k, v in sorted(draws.items())})
    return report


def production_index(task_id, dataset):
    prefix = {'truthfulqa_real':'truthfulqa_', 'hotpotqa_real':'real_hotpotqa_',
              'musique_real':'real_musique_', 'twowiki_real':'real_2wiki_',
              'longmemeval_real':'real_lme_'}[dataset]
    # Hotpot task IDs use real_hotpot_ in older artifacts.
    if dataset == 'hotpotqa_real' and task_id.startswith('real_hotpot_'):
        prefix = 'real_hotpot_'
    if not task_id.startswith(prefix):
        return None
    try:
        return int(task_id[len(prefix):].split('_')[0])
    except ValueError:
        return None


def read_cell(path):
    dataset = path.parent.name.split('__')[0]
    records = {}; malformed = 0; duplicates = 0; conflicts = 0; pending_tail = 0
    lines = path.read_bytes().splitlines(keepends=True)
    for i, line in enumerate(lines):
        try:
            row = json.loads(line)
            key = (row['task_id'], row['variant_idx'], row['arm'])
            if row['arm'] not in ARMS or type(row['true_success']) is not bool:
                raise ValueError('invalid row schema')
        except (ValueError, KeyError, TypeError):
            if i == len(lines)-1 and not line.endswith(b'\n'):
                pending_tail += 1
            else:
                malformed += 1
            continue
        if key in records:
            duplicates += 1
            conflicts += records[key] != row
        records[key] = row
    arms = {a: {} for a in ARMS}
    hashes = defaultdict(set); by_task = defaultdict(set)
    indices = range(48,60) if dataset in ('truthfulqa_real','hotpotqa_real') else range(60)
    production_keys = set(); extra = 0
    for (task, v, arm), row in records.items():
        arms[arm][(task,v)] = row['true_success']
        hashes[(task,v)].add(row.get('profile_hash'))
        by_task[task].add(row.get('profile_hash'))
        idx = production_index(task, dataset)
        if idx in indices and 0 <= v < 100:
            production_keys.add((idx,v,arm))
        else:
            extra += 1
    expected = len(indices)*100*len(ARMS)
    hash_mismatch = sum(len(h) != 1 or None in h for h in hashes.values())
    report = summarize(arms)
    report.update(cell=path.parent.name, raw_rows=len(lines), unique_rows=len(records),
        production_rows=len(production_keys), expected_rows=expected, smoke_or_extra_rows=extra,
        malformed_rows=malformed, incomplete_tail=pending_tail, duplicate_rows=duplicates,
        conflicting_duplicates=conflicts, paired_hash_mismatches=hash_mismatch,
        distinct_profile_hashes={k:len(v) for k,v in sorted(by_task.items())},
        complete=len(production_keys)==expected and not (malformed or pending_tail or conflicts or hash_mismatch))
    return report, arms


def build_report(root, selected=None):
    cells=[]; pooled={a:{} for a in ARMS}
    for cell in sorted(root.glob('*__*')):
        if selected and cell.name not in selected:
            continue
        path=cell/'variants.jsonl'
        if not path.exists():
            continue
        report, arms=read_cell(path); cells.append(report)
        for arm, rows in arms.items():
            for (task,v), success in rows.items():
                pooled[arm][(cell.name + '/' + task,v)] = success
    expected={d+'__'+m for d in DATASETS for m in MODELS}
    present={c['cell'] for c in cells}
    return dict(cells=cells, pooled=summarize(pooled), missing_cells=sorted(expected-present),
        complete=expected <= present and all(c['complete'] for c in cells),
        interpretation='Numbers only; partial results provisional; smoke/extra draws retained and counted.',
        paraphrase_review='Requires separate >=30-sample meaning-preservation review before trusted reporting.')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=Path('outputs/rebuttal/profile_bootstrap'))
    ap.add_argument('--cell',nargs='*')
    ap.add_argument('--output',type=Path)
    ap.add_argument('--require-complete',action='store_true')
    args=ap.parse_args(); report=build_report(args.root,args.cell)
    text=json.dumps(report,indent=2)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(text)
    print('COMPLETE' if report['complete'] else 'PROVISIONAL — incomplete production grid')
    for c in report['cells']:
        print(c['cell'],f"{c['production_rows']}/{c['expected_rows']}",
              'extra=',c['smoke_or_extra_rows'],'malformed=',c['malformed_rows'],
              json.dumps(c.get('contrast',{})))
    print('POOLED',json.dumps(report['pooled']))
    if args.require_complete and not report['complete']:
        raise SystemExit(1)


if __name__=='__main__':
    main()
