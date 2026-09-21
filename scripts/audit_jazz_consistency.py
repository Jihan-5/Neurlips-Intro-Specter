#!/usr/bin/env python3
"""F4: enumerate every numeric manuscript line and validate the Jazz artifact gates.

An inventory entry is not verification. Unresolved claims remain explicit and
cause --strict to fail; this script never rewrites paper claims or silently
accepts a headline scope.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def audit():
    paper=Path('paper_final.tex'); text=paper.read_text(); lines=text.splitlines()
    inventory=[]; section='preamble'; in_bibliography=False
    for i,line in enumerate(lines,1):
        if r'\begin{thebibliography}' in line: in_bibliography=True
        if r'\end{thebibliography}' in line:
            in_bibliography=False
            continue
        if in_bibliography: continue
        if line.startswith('%'): continue
        match=re.search(r'\\(?:sub)?section\*?\{([^}]+)',line)
        if match: section=match.group(1)
        numeric_text=re.sub(r'\\(?:cite\w*|label|ref)\{[^}]*\}', '', line)
        numbers=re.findall(r'(?<![A-Za-z])[-+]?\d+(?:\.\d+)?',numeric_text)
        if numbers:
            syntax=line.startswith(('\\usepackage','\\newcommand','\\pgfplotsset','\\includegraphics','  \\includegraphics','\\cmidrule','\\label','\\begin{algorithmic}','\\bibliographystyle'))
            inventory.append(dict(line=i,section=section,numbers=numbers,text=line,
                table_refs=re.findall(r'\\ref\{(tab:[^}]+)\}',line),
                status='LAYOUT_OR_SYNTAX' if syntax else 'REVIEW_REQUIRED'))
    findings=[]
    def flag(code,needle,reason,source):
        locations=[i for i,l in enumerate(lines,1) if needle in l]
        if locations: findings.append(dict(code=code,lines=locations,status='BLOCKED' if code.startswith('HEADLINE') else 'UNRESOLVED',reason=reason,source=source))
    flag('HEADLINE_SCOPE','87.0', 'Jihan owns reconciliation; pure SPR and mixed provenance are separate review packages.', 'paper_sections/generated/jazz_12/summary.json; jazz_16/summary.json')
    flag('HEADLINE_CELL_RECORD','15 of 16','Historical cell record disagrees with generated comparison counts; preserve until Jihan chooses scope.','paper_sections/generated/jazz_12/paired.csv; jazz_16/paired.csv')
    flag('CANDIDATE_EXCLUSION','non-profile ancestors','Released code already admits profile ancestors; E3 expands to all profile nodes.','intro_specter/dag.py:candidate_nodes_for_violations')
    flag('CANDIDATE_EXCLUSION','excluding immutable profile-derived','Claim does not describe the released default.','intro_specter/dag.py')
    flag('GENERATION_SEEDS','three method-internal seeds','Historical real runner overrides generation seed with dataset seed; artifacts do not contain three method-internal trials. E3 correctly fixes generation seed 0.','intro_specter/runner.py:run and seed_override')
    flag('TOKEN_ACCOUNTING','totals include the SPR','Released pipeline token counters include extraction/verifier but omit counterfactual and repair-provider tokens; recorded costs are not full costs.','intro_specter/pipeline.py:tokens_input and tokens_output assignments')
    flag('TRUTHFULQA_DENOMINATOR','after partial completion','TruthfulQA test split uses 12 of 60 local indices times three dataset seeds; this is split selection, not a 36-row rate-limit shortfall.','intro_specter/benchmarks/truthfulqa_real.py:_indices')
    flag('ITER_VRP_ALREADY_RUN','ablation we did not run','Contradicts executed matched-budget control paragraph and frozen artifacts.','rebuttal/tables/iter_vrp.md')
    flag('ABLATION_PROVENANCE','100\\% of \\method failures','Failure-stage/causal-attribution claim needs its annotation artifact; the Experiment-A diagnostic only classifies clean-solved failures.','scripts/aggregate_experiment_a_diagnostic.py')
    flag('EXTRACTION_METRICS','0.94 & 0.91 & 0.88 & 0.82','No generating extraction-evaluation artifact identified; do not certify these as verified.','Appendix DAG Extraction Quality')
    flag('CYCLE_CONFIDENCE','lowest endpoint-node confidence','Paper says endpoint minimum, implementation removes the lowest source-node confidence edge.','intro_specter/dag.py:remove_cycles')
    flag('TAU_PROTOCOL','$\\delta$ & Abstention threshold & 0.25','Jazz runs use tau=0.0; historical table states 0.25.','JAZZ_INSTRUCTIONS.md; configs/real/spr__*.yaml')
    cites=set()
    for match in re.finditer(r'\\cite\w*\{([^}]+)\}',text): cites.update(x.strip() for x in match.group(1).split(','))
    bib=set(re.findall(r'\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}',text))
    undefined=sorted(cites-bib)
    packages={}
    for scope in (12,16):
        root=Path(f'paper_sections/generated/jazz_{scope}')
        provenance=json.loads((root/'provenance.json').read_text())
        stale=[p for p,h in provenance['source_sha256'].items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
        packages[str(scope)]=dict(summary=json.loads((root/'summary.json').read_text()),stale_sources=stale)
    report=dict(paper_sha256=hashlib.sha256(paper.read_bytes()).hexdigest(),numeric_inventory=inventory,
        findings=findings,undefined_citations=undefined,generated_packages=packages,
        headline_decision='RESERVED_FOR_JIHAN',complete=False)
    out=Path('outputs/jazz/consistency_audit.json'); out.write_text(json.dumps(report,indent=2)+'\n')
    md=['# Jazz consistency audit','', 'Generated by `.venv/bin/python scripts/audit_jazz_consistency.py`. The paper headline is unchanged pending Jihan. An inventory does not certify a number.','',
        '| Finding | Lines | Status | Evidence |','|---|---|---|---|']
    for f in findings: md.append(f"| {f['code']} | {', '.join(map(str,f['lines']))} | {f['status']} | {f['reason']} Source: {f['source']} |")
    md+=['','## Complete numeric-line inventory','', '| Line | Section | Numeric tokens | Status |','|---|---|---|---|']
    for r in inventory: md.append(f"| {r['line']} | {r['section']} | {', '.join(r['numbers'])} | {r['status']} |")
    Path('orchestration/jazz_consistency_audit.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(dict(numeric_lines=len(inventory),unresolved_findings=len(findings),undefined_citations=undefined,
                         stale_generated_sources={k:v['stale_sources'] for k,v in packages.items()}),indent=2))
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--strict',action='store_true'); args=ap.parse_args()
    r=audit()
    if args.strict and not r['complete']: raise SystemExit(1)


if __name__=='__main__': main()
