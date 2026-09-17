#!/usr/bin/env python3
"""Generate F1 candidate tables and prose from an explicitly selected artifact scope.

No manuscript mutation. Produces both independently reviewable 12-cell SPR and
16-cell mixed-provenance packages. A 16-cell package labels Qwen archival/no-SPR.
Raw source SHA256s and paired counts accompany every generated package.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from aggregate_real_benchmarks import load_results, main_table, head_to_head, token_cost_table

DS=[('truthfulqa_real','TruthfulQA','truthfulqa','tqa'),('twowiki_real','2WikiMultiHopQA','2wiki','2wiki'),
    ('longmemeval_real','LongMemEval','longmemeval','lme'),('musique_real','MuSiQue','musique','musique')]
MODELS=[('llama-3.1-8b','Llama 8B'),('llama-3.3-70b','Llama 70B'),('mistral-nemo-12b','Mistral 12B')]
METHODS=['direct','self_refine','reflexion','full_regen','react','selfcheckgpt','tot','intro_specter_llm']
SHORT=['Direct','SR','Rfx','FR','ReAct','SChk','ToT',r'\method']


def table(caption,label,columns,header,rows,size='small'):
    return '\n'.join([r'\begin{table}[t]\centering'+'\\'+size,
        r'\caption{'+caption+'}',r'\label{'+label+'}',r'\setlength{\tabcolsep}{3pt}',
        r'\resizebox{\linewidth}{!}{%',
        r'\begin{tabular}{'+columns+r'}\toprule',header+r'\\\midrule',
        *[r+r' \\' for r in rows],r'\bottomrule\end{tabular}}\end{table}',''])


def generate(scope, output):
    models=MODELS+([('qwen-2.5-7b','Qwen 7B (archival)')] if scope==16 else [])
    slugs=[x[0] for x in models]; datasets=[d[0] for d in DS]
    base=load_results(Path('outputs/real')); spr=load_results(Path('outputs/real/spr'))
    base=base[base.dataset.isin(datasets)&base.model.isin(slugs)]
    spr=spr[spr.dataset.isin(datasets)&spr.model.isin(slugs)]
    active={tuple(v) for v in spr[['dataset','model']].drop_duplicates().values}
    keep=base.apply(lambda r:r['method']!='intro_specter_llm' or (r['dataset'],r['model']) not in active,axis=1)
    data=pd.concat([base[keep],spr],ignore_index=True)
    data=data[data.method.isin(METHODS)]
    main=main_table(data,datasets,slugs); paired=head_to_head(data,family='baseline')
    output.mkdir(parents=True,exist_ok=True)
    main.to_csv(output/'success.csv',index=False); paired.to_csv(output/'paired.csv',index=False)
    token=token_cost_table(data); token.to_csv(output/'cost.csv',index=False)
    sources={}
    for root in [Path('outputs/real'),Path('outputs/real/spr')]:
        for ds in datasets:
            for model in slugs:
                for p in sorted((root/(ds+'__'+model)).glob('*__seed*__*.jsonl')):
                    sources[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    provenance=('Qwen rows are archival no-SPR runs; Qwen is unavailable for rerun. '
                'Llama 3.1 8B substitutes for Qwen in new E2/E3 experiments. ' if scope==16 else
                'Only the three runnable models have SPR reruns. Qwen archival no-SPR results are excluded from this scope. ')
    provenance+='Baselines are archival; paired task/seed keys do not remove provider drift. Missing observations are not zero scores.'
    (output/'provenance.json').write_text(json.dumps(dict(scope=scope,source_sha256=sources,notes=provenance,
        invocation=f'.venv/bin/python scripts/generate_jazz_results.py --scope {scope}',
        correction_family='one Holm family per baseline across all selected cells',
        paired_unit='(dataset, model, task_id, seed); stored binary outcome, no seed averaging'),indent=2)+'\n')
    tables=[]; stats=[]; summary=[]
    for ds,title,label,plabel in DS:
        rows=[]; statrows=[]
        for slug,display in models:
            cell=main[(main.dataset==ds)&(main.model==slug)].iloc[0]
            values=[cell.get(m+'_success') for m in METHODS]
            best=max(float(v) for v in values if pd.notna(v))
            formatted=[]
            for v in values:
                text='---' if pd.isna(v) else f'{100*v:.1f}'
                if pd.notna(v) and abs(v-best)<1e-12: text=r'\textbf{'+text+'}'
                formatted.append(text)
            rows.append(display+' & '+' & '.join(formatted))
            pieces=[]
            for m in METHODS[:-1]:
                h=paired[(paired.dataset==ds)&(paired.model==slug)&(paired.baseline==m)]
                if h.empty: pieces.append('---'); continue
                h=h.iloc[0]
                p=f'{h.p_raw:.3f}' if h.p_raw>=.001 else '<.001'
                mark='*' if h.holm_reject else ''
                pieces.append(f'${p}${mark} [{100*h.ci_low:+.1f},{100*h.ci_high:+.1f}]'+r'\,('+str(int(h.n))+')')
            statrows.append(display+' & '+' & '.join(pieces))
        tables.append(table(title+r': success (\%). Bold denotes all tied numerical maxima. '+
            ('Qwen is archival/no-SPR. ' if scope==16 else '')+'Counts and provenance accompany the generated CSV.',
            'tab:'+label,'l'+'c'*8,' & '+' & '.join(SHORT),rows))
        stats.append(table(title+r': exact raw $p$, paired-bootstrap 95\% CI (pp), and paired $n$ in parentheses. '
            r'$\ast$: Holm-adjusted $p<.05$ within the baseline family; sign of the CI determines direction.',
            'tab:pvalues-'+plabel,'l'+'c'*7,' & '+' & '.join(SHORT[:-1]),statrows,'small'))
        h=paired[(paired.dataset==ds)&(paired.baseline=='reflexion')]
        summary.append(title+' & '+' & '.join(str(int(x)) for x in [(h.delta>1e-12).sum(),(h.delta.abs()<=1e-12).sum(),
            ((h.delta< -1e-12)&~h.holm_reject).sum(),((h.delta< -1e-12)&h.holm_reject).sum()]))
    tables.append(table('Cell outcomes against Reflexion; wins/ties are numerical, loss significance uses Holm adjustment.',
        'tab:summary','lcccc','Dataset & Wins & Ties & NS losses & Sig. losses',summary))
    (output/'main_tables.tex').write_text('\n'.join(tables))
    (output/'paired_tables.tex').write_text('\n'.join(stats))
    costrows=[]
    cost_methods=['direct','reflexion','selfcheckgpt','tot','intro_specter_llm']
    for ds,title,*_ in DS:
        means=token[token.dataset==ds].set_index('method').mean_tokens
        ref=means['intro_specter_llm']
        costrows.append(title+' & '+' & '.join(f'{means[m]:.0f} & {means[m]/ref:.2f}' for m in cost_methods))
    (output/'cost_table.tex').write_text(table('Recorded mean tokens per observed task; ratios use the recorded IS mean as denominator. '
        'Token accounting is inherited from the released harness; archival baselines and SPR reruns have different provider snapshots.',
        'tab:cost-full','l'+'rr'*5,'Dataset & Direct & ratio & Rfx & ratio & SChk & ratio & ToT & ratio & IS & ratio',costrows))
    isrows=data[data.method=='intro_specter_llm']; h=paired[paired.baseline=='reflexion']
    n=int(isrows.shape[0]); successes=int(isrows.success.sum())
    # Pooled comparison uses exactly the intersection, not separately averaged arms.
    target=isrows.merge(data[data.method=='reflexion'],on=['dataset','model','task_id','seed'],suffixes=('_is','_rf'))
    pooled=dict(scope=scope,n=n,successes=successes,success_rate=successes/n,
        paired_n=len(target),paired_is=float(target.success_is.mean()),paired_reflexion=float(target.success_rf.mean()),
        delta=float(target.success_is.mean()-target.success_rf.mean()),wins=int((h.delta>1e-12).sum()),
        ties=int((h.delta.abs()<=1e-12).sum()),losses=int((h.delta< -1e-12).sum()),
        significant_wins=int(((h.delta>0)&h.holm_reject).sum()), significant_losses=int(((h.delta<0)&h.holm_reject).sum()))
    prose=(f'Across {scope} cells, '+r'\method'+f' records {successes}/{n} successes ({100*successes/n:.2f}'+r'\%). '
        f'On {len(target)} matched observations, the IS--Reflexion difference is {100*pooled["delta"]:+.2f}'+r'\,pp '
        f'({100*pooled["paired_is"]:.2f}'+r'\% versus '+f'{100*pooled["paired_reflexion"]:.2f}'+r'\%). '
        f'The cell record against Reflexion is {pooled["wins"]} numerical wins, {pooled["ties"]} ties, and {pooled["losses"]} losses; '
        f'{pooled["significant_wins"]} wins and {pooled["significant_losses"]} losses survive Holm adjustment. '+provenance+'\n')
    (output/'summary.tex').write_text(prose)
    (output/'summary.json').write_text(json.dumps(pooled,indent=2)+'\n')
    (output/'review.tex').write_text(r'''\documentclass{article}
\usepackage[margin=20mm]{geometry}
\usepackage{booktabs,graphicx,amsmath}
\newcommand{\method}{\textsc{Intro-Specter}}
% Keep the standalone audit build independent of scaled legacy bitmap fonts.
% The manuscript may still use graphicx's real resizebox when a scope is chosen.
\renewcommand{\resizebox}[3]{#3}
\begin{document}
\section*{Jazz results review: scope '''+str(scope)+r'''}
\input{summary.tex}
\input{main_tables.tex}
\clearpage
\input{paired_tables.tex}
\clearpage
\input{cost_table.tex}
\end{document}
''')
    print(json.dumps(pooled))


def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--scope',type=int,choices=[12,16]); args=ap.parse_args()
    for scope in ([args.scope] if args.scope else [12,16]):
        generate(scope,Path(f'paper_sections/generated/jazz_{scope}'))


if __name__=='__main__': main()
