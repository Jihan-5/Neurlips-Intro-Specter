"""Regression tests for candidate gating and evidence/completeness accounting."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from aggregate_profile_bootstrap import read_cell, summarize, ARMS
from aggregate_profile_candidacy import aggregate_cell
from intro_specter.benchmarks.synthetic_dag import SyntheticDAGBenchmark
from intro_specter.pipeline import IntroSpecterConfig, run_intro_specter
from intro_specter.schemas import AssumptionNode, AttributionPosterior, Provenance
from intro_specter.verifier import HybridVerifier


def test_profile_flag_preserves_default_and_expands_candidates(monkeypatch):
    import intro_specter.pipeline as pipeline
    from intro_specter.dag import candidate_nodes_for_violations
    ex=next(iter(SyntheticDAGBenchmark(n_examples=1,seed=42,mode='single_fault')))
    orphan=AssumptionNode(id='profile_orphan',assumption='Detached profile fact',provenance=Provenance.PROFILE,
                          step_id=999,confidence=.5)
    dag=ex.dag.model_copy(update={'nodes':[*ex.dag.nodes,orphan]})
    captured=[]
    def posterior(**kwargs):
        captured.append([n.id for n in kwargs['candidates']])
        return AttributionPosterior(candidates=[],entropy=0,top_k=[]),[]
    monkeypatch.setattr(pipeline,'posterior_update',posterior)
    # Ambient environment must not silently switch a production experiment.
    monkeypatch.setenv('ALLOW_PROFILE_CANDIDATES','1')
    verifier=HybridVerifier(rules=list(ex.rules))
    verdict,_=verifier.check(profile=ex.profile,task=ex.task,trajectory=ex.trajectory,final_output=ex.trajectory.final_output)
    expected=[n.id for n in candidate_nodes_for_violations(dag,verdict.violations)]
    for enabled in (False,True):
        run_intro_specter(profile=ex.profile,task=ex.task,trajectory=ex.trajectory,verifier=verifier,
            sampler=None,config=IntroSpecterConfig(allow_profile_candidates=enabled),gold_dag=dag,
            rerun_callable=ex.rerun_fn)
    assert captured[0]==expected
    assert set(captured[1])==set(expected)|{n.id for n in dag.nodes if n.provenance==Provenance.PROFILE}
    assert len(captured[1])==len(set(captured[1]))


def test_recovery_requires_clean_success_corrupt_failure_and_mechanism_success(tmp_path):
    cell=tmp_path/'cell'; cell.mkdir()
    (cell/'protocol.json').write_text(json.dumps({'expected_tasks':['recover','always_success','base_failure']}))
    rows=[]
    for task in ['recover','always_success','base_failure']:
        for rho,flag in [(0.,False),(.1,False),(.1,True),(.3,False),(.3,True)]:
            success=task=='always_success' or (task=='recover' and (rho==0 or flag))
            rows.append(dict(task_id=task,seed=0,rho=rho,allow_profile_candidates=flag,
                             true_success=success,prime_hash='paired',corrupted_constraint_ids=['c1'] if rho else [],candidate_ids=[]))
    (cell/'paired.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    report=aggregate_cell(cell)
    assert report['eligible']==2 and report['recovered']==2 and report['complete']
    assert report['recovery_rate']==1
    (cell/'paired.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows[:-1]))
    assert not aggregate_cell(cell)['complete']


def test_candidacy_malformed_tail_is_visible(tmp_path):
    cell=tmp_path/'cell'; cell.mkdir()
    (cell/'protocol.json').write_text(json.dumps({'expected_tasks':[]}))
    (cell/'paired.jsonl').write_bytes(b'{"partial":')
    report=aggregate_cell(cell)
    assert report['malformed_rows']==1
    assert not report['complete']


def test_bootstrap_worst_tail_and_pool_pairing():
    arms={a:{} for a in ARMS}
    for v in range(100):
        arms['reflexion'][('x',v)]=v<10
        arms['intro_specter'][('x',v)]=v>=10
    r=summarize(arms)['contrast']
    assert r['worst_decile_mean']==-1 and r['favorable_fraction']==.9
    assert abs(r['mean']-.8)<1e-12
    assert r['hoeffding_bound']<1e-13


def test_bootstrap_extra_smoke_and_partial_write_are_visible(tmp_path):
    cell=tmp_path/'truthfulqa_real__llama-3.1-8b'; cell.mkdir()
    path=cell/'variants.jsonl'
    row=dict(task_id='truthfulqa_00001',variant_idx=0,arm='direct',true_success=True,profile_hash='a')
    path.write_text(json.dumps(row)+'\n'+json.dumps(row)+'\n'+ '{"partial":')
    r,_=read_cell(path)
    assert r['smoke_or_extra_rows']==1 and r['production_rows']==0
    assert r['duplicate_rows']==1 and r['incomplete_tail']==1 and not r['complete']
