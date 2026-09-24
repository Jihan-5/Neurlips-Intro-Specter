#!/usr/bin/env python3
"""Inventory E1 trace attribution coverage without substituting predictions across traces.
Exports exact blinded-item hashes and source evidence for the downstream prediction loader.
The frozen trace schema has no ranked candidates, failure-step marker, or RAFFLES outputs.
"""
import json
import hashlib
from pathlib import Path


def main():
    root=Path('outputs/iclr/e1_dataset'); out=root/'private/finalization'
    ids=json.loads((out/'effective_natural_ids.json').read_text())
    keys=json.loads((root/'private/keymap.json').read_text())
    try:
        from .e1_blind_trajectories import blind
    except ImportError:
        from e1_blind_trajectories import blind
    evidence={}; inputs={}
    for i in ids:
        source=Path(keys[i]['source_path'])
        trace=json.loads(source.read_text())
        item=root/f'items/{i}.json'
        if trace['success'] is not False or blind(trace,i) != json.loads(item.read_text()):
            raise ValueError(f'{i}: item does not match natural failed source')
        inputs[i]={'item_sha256':hashlib.sha256(item.read_bytes()).hexdigest()}
        evidence[i]={'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'source_arm':trace['method'], 'has_dag':bool(trace.get('extracted_dag')),
            'has_fault_node':trace.get('fault_node_predicted') is not None,
            'has_ranked_candidates':bool(trace.get('posterior')),
            'primed_equals_displayed_final':trace.get('primed_trajectory')==trace.get('final_trajectory')}
    result={'status':'Predictions incomplete; no new inference protocol chosen',
        'items':evidence,'n':len(ids),
        'with_historical_fault_node':sum(v['has_fault_node'] for v in evidence.values()),
        'with_ranked_candidates_in_trace':sum(v['has_ranked_candidates'] for v in evidence.values()),
        'blockers':['Eligible adjudicated consensus',
            'Jihan must supply/resolve the absent frozen RAFFLES judge model/prompt record',
            'Predictions/rankings and failure-node/ancestor mapping on the exact displayed final traces; source-arm repair attribution cannot be substituted across items']}
    (out/'prediction_inventory.json').write_text(json.dumps(result,indent=2)+'\n')
    (out/'prediction_inputs.json').write_text(json.dumps({'status':'INPUT HASHES ONLY — no predictions',
        'judge_protocol':None,'items':inputs},indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='items'},indent=2))

if __name__=='__main__': main()
