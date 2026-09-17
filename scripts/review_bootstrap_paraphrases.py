#!/usr/bin/env python3
"""Recover a seeded paraphrase audit sample using cache hits only (zero API calls).

Sampling is independent of success labels. Canonical/surface pairs come from the
exact committed redraw code and cached completions, not from a new model call.
"""
from __future__ import annotations
import argparse
import json
import random
import sqlite3
from pathlib import Path
import profile_bootstrap_study as boot
from intro_specter.models.cache import make_key
from intro_specter.models.base import CompletionResult


def collect(root, n):
    rng=random.Random(42); result=[]; misses=[]
    cells=sorted(root.glob('*__*')); rng.shuffle(cells)
    for cell in cells:
        ds,model=cell.name.split('__'); cache=Path('cache')/f'bootstrap_{ds}_{model}.sqlite'
        if not cache.exists(): continue
        # The harness always defaults to Llama 8B for paraphrasing, independently
        # of the evaluated model; using the cell model produces false cache misses.
        provider,model_id=boot.expa.MODEL_TABLE['llama-3.1-8b']
        pairs=sorted({(r['task_id'],r['variant_idx']) for line in (cell/'variants.jsonl').read_text().splitlines()
                      if (r:=json.loads(line))['arm']=='direct'})
        rng.shuffle(pairs)
        examples={e.task_id:e for e in boot.expa._load_examples(ds,60)}
        conn=sqlite3.connect(cache.resolve().as_uri()+'?mode=ro',uri=True)
        def cached(text,task,v,span):
            key=make_key(provider=provider,model=model_id,system=boot.PARAPHRASE_SYSTEM,
                user=f'Sentence: {text}',temperature=.7,seed=boot._paraphrase_seed(task,v,span),max_tokens=256)
            row=conn.execute('SELECT payload FROM completions WHERE key=?',(key,)).fetchone()
            if row is None: raise KeyError(key)
            payload=CompletionResult(**json.loads(row[0])).parse_json()
            surface=str(payload.get('paraphrase') or '').strip()
            if not surface or len(surface)>4*max(len(text),40): surface=text
            return surface,0,0
        taken=0
        for task,v in pairs[:500]:
            if task not in examples: continue
            try: _,info=boot.make_variant(examples[task],ds,v,cached)
            except KeyError:
                misses.append([cell.name,task,v]); continue
            spans=list(info['redrawn']); rng.shuffle(spans)
            for span in spans[:1]:
                result.append(dict(cell=cell.name,task_id=task,variant_idx=v,**span))
                taken+=1
            if taken>=5 or len(result)>=n: break
        conn.close()
        if len(result)>=n: break
    return dict(seed=42,api_calls=0,samples=result,cache_misses=misses,
                status='AWAITING_MEANING_REVIEW',required=n)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,default=Path('outputs/jazz/paraphrase_sample.json'))
    ap.add_argument('--n',type=int,default=30); args=ap.parse_args()
    report=collect(Path('outputs/rebuttal/profile_bootstrap'),args.n)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print('samples',len(report['samples']),'cache misses',len(report['cache_misses']))
    if len(report['samples'])<args.n: raise SystemExit(1)


if __name__=='__main__': main()
