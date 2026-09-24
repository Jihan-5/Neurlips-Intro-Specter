import hashlib
import json
from pathlib import Path

import pytest
from scripts.e1_attribution_vs_human import binomial, score
from scripts.e1_package_dataset import package
from scripts.e1_finalize_human import indexed, validate_label
from scripts.aggregate_personalwab import load_rows
from scripts.e1_compute_agreement import build_consensus


def test_d6_merge_keeps_agreed_components():
    rows = {'category_only': [('jazz',1,3),('jazz2',2,4)],
            'step_only': [('jazz',2,3),('jazz2',2,8)]}
    got = build_consensus(rows, {'category_only':('jihan',4,9),'step_only':('jihan',1,5)})
    assert got['category_only']['category'] == 4
    assert got['category_only']['step'] == 3
    assert got['step_only']['category'] == 2
    assert got['step_only']['step'] == 5


def test_reject_duplicate_answers_and_bad_steps():
    with pytest.raises(ValueError):
        indexed({'answers':[{'item_id':'x'},{'item_id':'x'}]})
    with pytest.raises(ValueError):
        validate_label({'category':2,'step':None},{'item_id':'x','steps':[]})


def test_metrics_abstentions_missing_rankings_and_analytic_floor(tmp_path):
    item = {'steps':[{'step_id':s} for s in range(1,5)]}
    path = tmp_path/'x.json'
    path.write_text(json.dumps(item))
    consensus = {'x':{'status':'agreed','category':2,'step':2}}
    pred = {'judge_protocol':'recorded_model_prompt.md', 'items':{'x':{
        'item_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'failure_step':4,'ancestor_steps':[1,2,2],
        'intro_specter':{'step':None},'raffles':{'step':3,'ranked_steps':[3,2,1],'category':2}}}}
    result = score(tmp_path,consensus,pred)
    assert result['methods']['intro_specter']['exact']['hits'] == 0
    assert result['methods']['intro_specter']['mrr'] is None
    assert result['methods']['raffles']['mrr'] == .5
    assert result['methods']['raffles']['within1']['hits'] == 1
    assert result['methods']['random_ancestor']['exact'] == 2/3
    assert result['methods']['most_recent_step']['within1']['hits'] == 1
    assert not result['complete_prediction_coverage']
    pred['items']['x']['item_sha256']='wrong'
    with pytest.raises(ValueError,match='hash'):
        score(tmp_path,consensus,pred)


def test_exact_binomial_boundaries():
    assert binomial([])['ci95'] is None
    assert binomial([False]*10)['ci95'][0] == 0
    assert binomial([True]*10)['ci95'][1] == 1
    assert binomial([True]*10)['ci95'][0] == pytest.approx(.691502892)


def test_no_release_of_excluded_consensus(tmp_path):
    (tmp_path/'consensus_pending.json').write_text(json.dumps({'eligible':False,'items':{'x':{'status':'agreed'}}}))
    (tmp_path/'effective_natural_ids.json').write_text('["x"]')
    with pytest.raises(ValueError,match='ineligible'):
        package(tmp_path,tmp_path,tmp_path/'release',True)
    assert not (tmp_path/'release').exists()


def test_track_p_strict_duplicates(tmp_path):
    (tmp_path/'model').mkdir()
    row = {'task_id':'x','seed':0,'arm':'direct','success':True}
    (tmp_path/'model/direct.jsonl').write_text((json.dumps(row)+'\n')*2)
    with pytest.raises(ValueError,match='Duplicate'):
        load_rows('model','direct',tmp_path,strict=True)


def test_safe_transport_scopes_pull_and_never_restores_invalid_e1(tmp_path, monkeypatch):
    import scripts.sync_artifacts_safe as sync
    monkeypatch.setattr(sync,'ROOT',tmp_path)
    entries = b'\0'.join(b'100644 blob deadbeef\t'+p.encode() for p in [
        'outputs/iclr/e1_dataset/README.md',
        'outputs/iclr/e1_dataset/recovery_v2/bad.json',
        'outputs/unrelated/old.json'])
    def fake_git(*args,**kwargs):
        if args[0]=='ls-tree': return entries
        if args[0]=='cat-file': return b'preserved remote artifact'
        raise AssertionError(args)
    monkeypatch.setattr(sync,'git',fake_git)
    sync.pull('tip',[Path('outputs/iclr/e1_dataset')])
    assert (tmp_path/'outputs/iclr/e1_dataset/README.md').exists()
    assert not (tmp_path/'outputs/iclr/e1_dataset/recovery_v2').exists()
    assert not (tmp_path/'outputs/unrelated').exists()
