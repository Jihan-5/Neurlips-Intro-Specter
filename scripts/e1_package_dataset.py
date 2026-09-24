#!/usr/bin/env python3
"""Package E1 per-trace blinded data, human labels and consensus. Default is a private draft.
--release fails closed unless screening passes, consensus is complete and all scoring exists.
Never packages private keymaps, attention answers, malformed originals, or the AI baseline.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


def package(root, analysis, output, release=False, metrics=None):
    consensus = json.loads((analysis/'consensus_pending.json').read_text())
    ids = json.loads((analysis/'effective_natural_ids.json').read_text())
    if set(ids) != set(consensus['items']) or len(ids) != len(set(ids)):
        raise ValueError('Consensus coverage differs from effective data')
    if release:
        if not consensus.get('eligible') or any(c.get('status') not in ('agreed','adjudicated') for c in consensus['items'].values()):
            raise ValueError('Release blocked: ineligible or unresolved labels')
        if not metrics or json.loads(metrics.read_text()).get('status') != 'FINAL':
            raise ValueError('Release blocked: incomplete attribution/floor metrics')
        scored = json.loads(metrics.read_text())
        digest = hashlib.sha256((analysis/'consensus_pending.json').read_bytes()).hexdigest()
        if digest not in scored.get('source_sha256', {}).values():
            raise ValueError('Release blocked: metrics use a different consensus')
    if output.exists():
        raise ValueError('Output exists; use a new destination to avoid mixing stale files')
    labels = {}
    for ann in ('jazz','jazz2'):
        b = json.loads((analysis/f'{ann}_effective_main.json').read_text())
        labels[ann] = {a['item_id']:a for a in b['answers']}
    # Validate everything before creating output.
    records = []
    for i in ids:
        records.append({'item': json.loads((root/f'items/{i}.json').read_text()),
            'human_labels': {ann: rows[i] for ann, rows in labels.items()},
            'consensus': consensus['items'][i], 'eligible': consensus['eligible']})
    output.mkdir(parents=True)
    for record in records:
        (output/f"{record['item']['item_id']}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False)+'\n')
    for source, name in [(Path('orchestration/e1_codebook.md'),'codebook.md'),
                         (Path('orchestration/e1_prereg.md'),'prereg.md'), (root/'DATASHEET.md','DATASHEET.md')]:
        shutil.copyfile(source, output/name)
    (output/'README.md').write_text('# E1 '+('release' if release else 'PRIVATE DRAFT — NOT A RELEASE')+'\n\n'
        + f'{len(ids)} effective natural items. Raw human answers are preserved; author adjudication is separate.\n'
        + 'Jazz1/Jazz2 are distinct blinded human annotators. See DATASHEET.md for pending disclosures.\n'
        + ('CC BY 4.0: https://creativecommons.org/licenses/by/4.0/\n' if release else
           'Frozen attention exclusions remain in force; provisional consensus is not eligible gold. Planned release license: CC BY 4.0.\n'))
    (output/'LICENSE.txt').write_text(('Released under' if release else 'Planned release license (draft, not a public release):') + '\nCreative Commons Attribution 4.0 International (CC BY 4.0).\nhttps://creativecommons.org/licenses/by/4.0/legalcode\nRetain attribution to the dataset contributors and upstream source notices.\n')
    manifest = {str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())}
    (output/'manifest.json').write_text(json.dumps({'release':release,'n':len(ids),'sha256':manifest},indent=2)+'\n')
    print(f'Packaged {len(ids)} items -> {output}; release={release}')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dataset-dir',type=Path,default=Path('outputs/iclr/e1_dataset'))
    ap.add_argument('--analysis-dir',type=Path)
    ap.add_argument('--output-dir',type=Path,required=True)
    ap.add_argument('--release',action='store_true')
    ap.add_argument('--metrics',type=Path)
    a=ap.parse_args()
    package(a.dataset_dir,a.analysis_dir or a.dataset_dir/'private/finalization',a.output_dir,a.release,a.metrics)

if __name__=='__main__':
    main()
