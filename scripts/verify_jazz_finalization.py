#!/usr/bin/env python3
"""Read-only independent numerical checks; write a validation receipt, not experiment data."""
import hashlib
import json
import math
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.aggregate_personalwab import ARMS, BASELINE_ARMS, load_rows
from scripts.prep_personalwab_compact import verify_task_ids, verify_no_target_leaks
from intro_specter.metrics.stats import mcnemar, paired_bootstrap_ci


def main():
    root=Path('outputs/rebuttal/experiment_personalwab_clean')
    models=['llama-3.1-8b','mistral-nemo-12b']
    cells={m:{a:load_rows(m,a,root,strict=True) for a in ARMS} for m in models}
    keys=set(cells[models[0]]['direct'])
    assert len(keys)==180 and len({t for t,s in keys})==60
    assert keys=={(t,s) for t,_ in keys for s in (0,1,2)}
    assert all(set(v)==keys for c in cells.values() for v in c.values())
    cells['pooled']={a:{(m,*k):v for m in models for k,v in cells[m][a].items()} for a in ARMS}
    checks={}
    for m,c in cells.items():
        checks[m]={}
        for arm in BASELINE_ARMS:
            ks=sorted(c['intro_specter'])
            a=[c[arm][k]['success'] for k in ks]
            b=[c['intro_specter'][k]['success'] for k in ks]
            wins=sum(y and not x for x,y in zip(a,b)); losses=sum(x and not y for x,y in zip(a,b))
            n=wins+losses
            exact=min(1.,2*sum(math.comb(n,k) for k in range(min(wins,losses)+1))/2**n) if n else 1.
            assert abs(mcnemar(a,b).pvalue-exact)<1e-12
            # Independent per-replicate paired resampling, same fixed seed/draw count.
            rng=np.random.default_rng(0)
            differences=np.array(b,dtype=float)-np.array(a,dtype=float)
            samples=[float(np.mean(differences[rng.integers(len(ks),size=len(ks))])) for _ in range(10000)]
            low,high=np.quantile(samples,[.025,.975])
            ci=paired_bootstrap_ci(list(map(float,a)),list(map(float,b)))
            assert np.allclose([ci.point,ci.low,ci.high],[differences.mean(),low,high])
            expected=f'{ci.point*100:+.6f} [{ci.low*100:+.6f}, {ci.high*100:+.6f}] | {exact:.8g}'
            summary=root/('POOLED_SUMMARY.md' if m=='pooled' else 'SUMMARY.md')
            assert expected in summary.read_text()
            checks[m][arm]={'pairs':len(ks),'is_wins':wins,'baseline_wins':losses,
                           'delta':ci.point,'ci95':[ci.low,ci.high],'exact_p':exact}
    compact=Path('data/personalwab/compact_recommend_clean.json')
    assert hashlib.sha256(compact.read_bytes()).hexdigest()=='017093dcd799d56f7f2c7330b7c7a80cdbaa8be388311f60a56bb26445d00fcc'
    assert verify_task_ids(compact,root/models[0]/'direct.jsonl')
    assert verify_no_target_leaks(compact)
    d=Path('outputs/iclr/e1_dataset'); out=d/'private/finalization'
    read=lambda p: json.loads(p.read_text())
    a=read(out/'agreement.json')
    effective={ann:{x['item_id']:x for x in read(out/f'{ann}_effective_main.json')['answers']}
               for ann in ['jazz','jazz2']}
    ids=read(out/'effective_natural_ids.json')
    ca=[effective['jazz'][i]['category'] for i in ids]
    cb=[effective['jazz2'][i]['category'] for i in ids]
    observed=sum(x==y for x,y in zip(ca,cb))/len(ids)
    expected=sum(ca.count(k)*cb.count(k) for k in range(1,8))/len(ids)**2
    assert abs(a['kappa']-(observed-expected)/(1-expected))<1e-12
    combined=ca+cb
    expected_dis=sum(x!=y for i,x in enumerate(combined) for j,y in enumerate(combined) if i!=j)/(len(combined)*(len(combined)-1))
    assert abs(a['alpha_nominal']-(1-(1-observed)/expected_dis))<1e-12
    repilot={ann:read(d/f'answers/{ann}_repilot_answers.json') for ann in ['jazz','jazz2']}
    from scripts.e1_compute_agreement import cohens_kappa
    r={ann:{x['item_id']:x['category'] for x in b['answers']} for ann,b in repilot.items()}
    assert set(r['jazz'])==set(r['jazz2']) and len(r['jazz'])==15
    rk=cohens_kappa([(r['jazz'][i],r['jazz2'][i]) for i in r['jazz']])
    assert rk>=.6
    # Earlier work: inspect completed receipts; do not rerun experiments or write paper.
    gate=read(Path('outputs/jazz/final_gate.json'))
    assert gate['complete'] and all(gate['gates'].values())
    integrities=list(Path('outputs/rebuttal/profile_bootstrap_a1_a2_complete').glob('*/integrity.json'))
    assert len(integrities)==10
    evidence=[Path('outputs/jazz/final_gate.json'),Path('outputs/jazz/JAZZ_DONE'),
      Path('outputs/jazz/bootstrap_a1_a2_final.json'),Path('outputs/jazz/candidacy_final.json'),
      Path('outputs/jazz/personalwab_contradictions.json'),Path('outputs/jazz/consistency_audit.json'),
      Path('paper_sections/generated/jazz_f2.tex'),Path('paper_sections/generated/jazz_f3.tex')]+integrities
    receipt={'track_p_complete':True,'models':models,'qwen':'omitted by Jihan: Leave out bro',
      'rows':1800,'cells':10,'duplicates':0,'task_seed_coverage':'60 x 3; all cells identical',
      'leak_and_task_id_checks':True,'comparisons':checks,'repilot_kappa':rk,
      'independent_kappa_alpha_verified':True,'earlier_ef_completed_receipts_verified':True,
      'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in evidence+[compact]+list(root.glob('*/*.jsonl'))}}
    (out/'validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k not in ['source_sha256','comparisons']},indent=2))

if __name__=='__main__': main()
