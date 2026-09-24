#!/usr/bin/env python3
"""Score artifact-backed predictions against E1 consensus; never generate judgments.

Prediction JSON: {"items": {item_id: {"item_sha256": ..., "failure_step": int,
 "ancestor_steps": [int, ...], "intro_specter": {"step": int|null,
 "ranked_steps": [int,...], "category": optional int},
 "raffles": {"step": int|null, "ranked_steps": [int,...], "category": optional int}}},
 "judge_protocol": "path to recorded fixed judge model/prompt"}.
Ancestors are one entry per graph node (repeated step mappings retain node weights).
Rankings are ordered unique step IDs. A null top-1 is an explicit abstention/miss;
missing predictions/rankings are coverage gaps, never invented misses or ranks.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from collections import Counter
from scipy.stats import beta


def binomial(hits):
    n, k = len(hits), sum(hits)
    return {'n': n, 'hits': k, 'rate': k/n if n else None,
        'ci95': [0.0 if not k else float(beta.ppf(.025, k, n-k+1)),
                 1.0 if k == n else float(beta.ppf(.975, k+1, n-k))] if n else None}


def score(items, consensus, predictions):
    usable = {i: c for i,c in consensus.items() if c.get('status') in ('agreed','adjudicated')
              and c.get('category') in (1,2,3,4) and c.get('step') is not None}
    methods = {m: {'exact': [], 'within1': [], 'category': [], 'rr': [], 'missing': [], 'ranking_missing': []}
               for m in ('intro_specter', 'most_recent_step', 'raffles')}
    random = {'exact': [], 'within1': [], 'rr': [], 'missing': []}
    for i,c in usable.items():
        raw = items / f'{i}.json'
        item = json.loads(raw.read_text())
        displayed = [s['step_id'] for s in item['steps']]
        p = predictions.get('items', {}).get(i, {})
        if p and p.get('item_sha256') != hashlib.sha256(raw.read_bytes()).hexdigest():
            raise ValueError(f'{i}: prediction is not tied to the displayed trace hash')
        if 'failure_step' in p:
            f = p['failure_step']
            if type(f) is not int or f not in displayed:
                raise ValueError(f'{i}: invalid failure step')
            before = [s for s in displayed if s < f]
            recent = {'step': max(before) if before else None}
            recent['ranked_steps'] = [recent['step']] if before else []
        else:
            recent = None
        for method, accum in methods.items():
            pred = recent if method == 'most_recent_step' else p.get(method)
            if pred is None:
                accum['missing'].append(i)
                continue
            if method == 'raffles' and not predictions.get('judge_protocol'):
                raise ValueError('RAFFLES outputs need the recorded judge protocol reference')
            if 'step' not in pred:
                raise ValueError(f'{i}/{method}: step is required; null means abstention')
            step = pred['step']
            if step is not None and (type(step) is not int or step not in displayed):
                raise ValueError(f'{i}/{method}: invalid displayed step')
            accum['exact'].append(step == c['step'])
            accum['within1'].append(step is not None and abs(step-c['step']) <= 1)
            if 'category' in pred:
                if type(pred['category']) is not int or pred['category'] not in range(1,8):
                    raise ValueError('Invalid predicted category')
                accum['category'].append(pred['category'] == c['category'])
            if 'ranked_steps' in pred:
                ranks = pred['ranked_steps']
                if len(ranks) != len(set(ranks)) or any(type(s) is not int or s not in displayed for s in ranks):
                    raise ValueError(f'{i}/{method}: invalid ranking')
                accum['rr'].append(1/(ranks.index(c['step'])+1) if c['step'] in ranks else 0.)
            else:
                accum['ranking_missing'].append(i)
        ancestors = p.get('ancestor_steps')
        if ancestors is None or not ancestors:
            random['missing'].append(i)
        else:
            if any(type(s) is not int or s not in displayed for s in ancestors):
                raise ValueError(f'{i}: invalid ancestor mapping')
            random['exact'].append(sum(s == c['step'] for s in ancestors)/len(ancestors))
            random['within1'].append(sum(abs(s-c['step']) <= 1 for s in ancestors)/len(ancestors))
            # This floor predicts one uniformly sampled ancestor, so RR equals hit@1.
            random['rr'].append(random['exact'][-1])
    out = {'scorable_n': len(usable), 'consensus_category_counts': dict(Counter(str(c.get('category')) for c in consensus.values())),
           'excluded_or_unresolved_n': len(consensus)-len(usable), 'methods': {}}
    for m, a in methods.items():
        out['methods'][m] = {k: binomial(a[k]) for k in ('exact','within1','category')}
        out['methods'][m].update({'mrr': sum(a['rr'])/len(a['rr']) if a['rr'] else None,
            'mrr_n': len(a['rr']), 'missing': a['missing'], 'ranking_missing': a['ranking_missing']})
    out['methods']['random_ancestor'] = {k: sum(random[k])/len(random[k]) if random[k] else None for k in ('exact','within1','rr')}
    out['methods']['random_ancestor'].update({'n': len(random['exact']), 'missing': random['missing'],
        'ci95': None, 'ci_note': 'Analytic expectations, not observed binomial outcomes; Clopper–Pearson is inapplicable.',
        'rr_note': 'Single sampled ancestor; no invented random-ranking protocol.'})
    out['complete_prediction_coverage'] = bool(usable) and not any(a['missing'] or a['ranking_missing'] for a in methods.values()) and not random['missing']
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dataset-dir', type=Path, default=Path('outputs/iclr/e1_dataset'))
    ap.add_argument('--consensus', type=Path, required=True)
    ap.add_argument('--predictions', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    c, p = json.loads(a.consensus.read_text()), json.loads(a.predictions.read_text())
    result = score(a.dataset_dir/'items', c['items'], p)
    resolved = all(v.get('status') in ('agreed','adjudicated') for v in c['items'].values())
    result['status'] = 'FINAL' if c.get('eligible') and resolved and result['complete_prediction_coverage'] else 'INCOMPLETE / DIAGNOSTIC ONLY'
    result['eligible'] = c.get('eligible', False)
    result['all_consensus_resolved'] = resolved
    result['source_sha256'] = {str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in (a.consensus,a.predictions)}
    a.output.write_text(json.dumps(result, indent=2)+'\n')
    csvpath = a.output.with_name('e1_attribution_accuracy.csv')
    with csvpath.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['status','method','metric','n','estimate','ci95_low','ci95_high'])
        for method, values in result['methods'].items():
            if method == 'random_ancestor':
                for metric in ('exact','within1','rr'):
                    writer.writerow([result['status'],method,metric,values['n'],values[metric],'',''])
            else:
                for metric in ('exact','within1','category'):
                    v=values[metric]
                    writer.writerow([result['status'],method,metric,v['n'],v['rate'],*(v['ci95'] or ['', ''])])
                writer.writerow([result['status'],method,'mrr',values['mrr_n'],values['mrr'],'',''])
    print(json.dumps({k:v for k,v in result.items() if k != 'methods'},indent=2))

if __name__ == '__main__':
    main()
