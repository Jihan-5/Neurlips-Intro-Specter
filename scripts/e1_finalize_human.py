#!/usr/bin/env python3
"""Reconstruct effective human main labels and stage D6 adjudication, without screening overrides.

Outputs are descriptive/pre-adjudication diagnostics while frozen checks exclude humans.
An optional Jihan answer download merges by frozen rules, but does not waive exclusions.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from collections import Counter
try:
    from .e1_compute_agreement import (build_consensus, cohens_kappa,
        krippendorff_alpha_nominal, screen_attention_checks, step_match)
    from .e1_make_annotation_pages import build_page
except ImportError:
    from e1_compute_agreement import (build_consensus, cohens_kappa,
        krippendorff_alpha_nominal, screen_attention_checks, step_match)
    from e1_make_annotation_pages import build_page


def read(path):
    return json.loads(Path(path).read_text())


def write(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')


def indexed(blob):
    rows = blob['answers']
    result = {a['item_id']: a for a in rows}
    if len(result) != len(rows):
        raise ValueError('Duplicate answer IDs')
    return result


def validate_label(answer, item):
    c, s = answer['category'], answer['step']
    if type(c) is not int or c not in range(1, 8):
        raise ValueError('Invalid category')
    if s is None:
        if c not in (5, 6):
            raise ValueError('Null step outside categories 5/6')
    elif type(s) is not int or s not in [v['step_id'] for v in item['steps']]:
        raise ValueError(f"Invalid step for {item['item_id']}: {s}")
    if c == 6 and s is not None:
        raise ValueError('Category 6 requires null step')
    if c == 7 and not answer.get('comment', '').strip():
        raise ValueError('Category 7 requires comment')


def prepare(root, out, adjudications=None):
    out.mkdir(parents=True, exist_ok=True)
    keymap = read(root / 'private/keymap.json')
    log = (root / 'repilot_malformed_log.md').read_text()
    replacements = dict(re.findall(r'\| `(e1_\d+)` \| [^|]+ \| `(e1_\d+)` \|', log))
    if len(replacements) != 6 or len(set(replacements.values())) != 6:
        raise ValueError('Expected six logged one-to-one replacements')
    if any(keymap[i]['role'] != 'reserve' or keymap[i]['attention_check'] for i in replacements.values()):
        raise ValueError('Replacements must be natural reserve items')
    inputs = [root / 'private/keymap.json', root / 'assignments.json', root / 'repilot_malformed_log.md']
    effective, natural = {}, {}
    for ann in ('jazz', 'jazz2'):
        mainpath = root / f'answers/{ann}_main_answers.json'
        reppath = root / f'answers/{ann}_main_replacements_answers.json'
        inputs.extend([mainpath, reppath])
        main, rep = read(mainpath), read(reppath)
        if main['annotator'] != ann or rep['annotator'] != ann:
            raise ValueError('Annotator identity mismatch')
        if main['phase'] != 'main' or rep['phase'] != 'main_replacements':
            raise ValueError('Wrong human answer phase')
        m, r = indexed(main), indexed(rep)
        pagepath = root / f'annotation_pages/{ann}_main.html'
        inputs.append(pagepath)
        page_items = json.loads(re.search(r'const ITEMS = (.*?);\n', pagepath.read_text(), re.S).group(1))
        if set(m) != {i['item_id'] for i in page_items} or set(r) != set(replacements.values()):
            raise ValueError('Answers differ from assigned main/replacement IDs')
        if not set(replacements) <= set(m) or set(r) & set(m):
            raise ValueError('Invalid replacement coverage')
        rows = [a for a in main['answers'] if a['item_id'] not in replacements] + rep['answers']
        effective[ann] = indexed({'answers': rows})
        natural[ann] = {i: a for i, a in effective[ann].items() if not keymap[i]['attention_check']}
        if len(effective[ann]) != 90 or len(natural[ann]) != 85:
            raise ValueError('Expected 85 natural + five checks per annotator')
        for i, a in effective[ann].items():
            itempath = root / f'items/{i}.json'
            inputs.append(itempath)
            item = read(itempath)
            ids = [v['step_id'] for v in item['steps']]
            if len(ids) != len(set(ids)) or sorted(ids) != list(range(1, len(ids)+1)):
                raise ValueError(f'Malformed effective item {i}')
            validate_label(a, item)
        write(out / f'{ann}_effective_main.json', {'annotator': ann, 'phase': 'main',
              'status': 'derived; frozen screening applies', 'answers': rows})
    if set(natural['jazz']) != set(natural['jazz2']):
        raise ValueError('Human natural item sets differ')
    ids = sorted(natural['jazz'])
    base = {a: {i: (r['category'], r['step'], r.get('comment', '')) for i, r in rows.items()}
            for a, rows in effective.items()}
    excluded, screen = screen_attention_checks(base, keymap)
    item_labels = {i: [(a, natural[a][i]['category'], natural[a][i]['step']) for a in natural] for i in ids}
    pairs = [(natural['jazz'][i]['category'], natural['jazz2'][i]['category']) for i in ids]
    steps = [(natural['jazz'][i]['step'], natural['jazz2'][i]['step']) for i in ids]
    decisions = {}
    preliminary = build_consensus(item_labels, {})
    queue = [i for i, r in preliminary.items() if r['status'] == 'needs_adjudication']
    if adjudications:
        b = read(adjudications)
        if b['annotator'] != 'jihan' or b['phase'] != 'adjudication':
            raise ValueError('Expected Jihan adjudication download')
        for i, a in indexed(b).items():
            if i not in queue:
                raise ValueError(f'Unexpected adjudication ID {i}')
            validate_label(a, read(root / f'items/{i}.json'))
            decisions[i] = ('jihan', a['category'], a['step'])
        inputs.append(Path(adjudications))
    consensus = build_consensus(item_labels, decisions)
    for i, value in consensus.items():
        if 'category' in value:
            validate_label({**value, 'comment': 'consensus'}, read(root / f'items/{i}.json'))
    disagreements = []
    for i, (ca, cb), (sa, sb) in zip(ids, pairs, steps):
        if ca != cb or sa != sb:
            disagreements.append({'item_id': i, 'jazz': natural['jazz'][i], 'jazz2': natural['jazz2'][i],
                'category_disagreement': ca != cb, 'step_exact_disagreement': sa != sb,
                'requires_adjudication': i in queue})
    report = {'status': 'DESCRIPTIVE ONLY; excluded by frozen screen' if excluded else 'eligible',
        'effective_n': len(ids), 'eligible_n': 0 if excluded else len(ids),
        'category_exact': sum(a == b for a, b in pairs)/len(ids),
        'category_exact_count': sum(a == b for a, b in pairs),
        'kappa': cohens_kappa(pairs), 'alpha_nominal': krippendorff_alpha_nominal(pairs),
        'q2_exact': sum(a == b for a, b in steps)/len(ids),
        'q2_exact_count': sum(a == b for a, b in steps),
        'q2_within1': sum(step_match(a,b) for a,b in steps)/len(ids),
        'q2_within1_count': sum(step_match(a,b) for a,b in steps),
        'disagreement_count': len(disagreements), 'adjudication_count': len(queue),
        'screen': screen, 'excluded': sorted(excluded), 'replacements': replacements,
        'consensus_status': dict(Counter(v['status'] for v in consensus.values())),
        'category_confusion': dict(Counter(f'{a},{b}' for a,b in pairs))}
    write(out/'agreement.json', report)
    write(out/'disagreements.json', disagreements)
    write(out/'adjudication_queue.json', queue)
    write(out/'consensus_pending.json', {'eligible': not excluded, 'screen': screen,
        'status': report['status'], 'items': consensus})
    write(out/'effective_natural_ids.json', ids)
    write(out/'input_hashes.json', {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
    # Existing offline annotation workflow; only a new private Jihan page is written.
    build_page('jihan', 'adjudication', [read(root/f'items/{i}.json') for i in queue], out/'jihan_adjudication.html')
    page = out/'jihan_adjudication.html'
    page.write_text(page.read_text().replace('<main>', '<p style="padding:1rem;color:#a00">PREPARATION ONLY — frozen screen excludes both annotators. Jihan must resolve eligibility before study adjudication. Apply prereg §4; category agreements and steps within ±1 remain fixed in merge.</p><main>'))
    rows = ['# Effective human agreement (descriptive, before adjudication)', '', report['status'], '',
            'Frozen attention key and historical exclusions remain unchanged. These are unscreened diagnostics, not eligible study results.', '',
            '```json', json.dumps(report, indent=2), '```', '',
            'Full raw-answer disagreement list: `disagreements.json`; all category or >1-step disagreements: `adjudication_queue.json`.',
            'Jihan page uses the existing offline export schema. Merge with `--adjudications PATH`; agreed components cannot be overwritten.']
    (out/'AGREEMENT.md').write_text('\n'.join(rows)+'\n')
    print(json.dumps(report, indent=2))
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dataset-dir', type=Path, default=Path('outputs/iclr/e1_dataset'))
    ap.add_argument('--output-dir', type=Path)
    ap.add_argument('--adjudications', type=Path)
    a = ap.parse_args()
    prepare(a.dataset_dir, a.output_dir or a.dataset_dir/'private/finalization', a.adjudications)

if __name__ == '__main__':
    main()
