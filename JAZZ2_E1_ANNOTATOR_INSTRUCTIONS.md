# Jazz 2 — E1 blinded annotation handoff

You are the second, distinct human annotator. Read
`orchestration/e1_codebook.md` before labeling. Do not open raw traces, source/model
metadata, the private keymap, Jazz 1's answers, or any method output. Do not use AI
assistance or discuss judgments with Jazz 1.

## What to receive

- `orchestration/e1_codebook.md`
- `outputs/iclr/e1_dataset/annotation_pages/jazz2_pilot.html`
- After the pilot gate passes:
  `outputs/iclr/e1_dataset/annotation_pages/jazz2_main.html`

The pages are self-contained and blinded. They contain the same 15-item pilot as Jazz 1,
and a 90-item main batch (85 natural items plus five indistinguishable attention checks).

## First task: pilot

Open `jazz2_pilot.html`, label all 15 items, and for each item choose one fault category
and the earliest faulty step. Use `None` only for categories 5 or 6; category 7 requires a
comment naming both candidate categories. Click **Download answers** and save the download
as:

`outputs/iclr/e1_dataset/answers/jazz2_pilot_answers.json`

The coordinator then runs the pilot κ gate. Jazz 2 may start this pilot as soon as Jazz 1's
pilot exists; Jazz 2 does **not** need to wait for Jazz 1's main batch. Do not open the main
page until the coordinator confirms κ ≥ 0.6.

## After the κ gate

Open `jazz2_main.html`, label all 90 items, and download the result as:

`outputs/iclr/e1_dataset/answers/jazz2_main_answers.json`

Work in sittings of at most ten items. If an item is malformed or unreadable, flag it in
the comment and stop on that item rather than guessing. Download an in-progress JSON at the
end of each sitting; never edit another annotator's file.

## Coordinator-only pilot κ command

After both pilot files exist, the coordinator runs:

```bash
.venv/bin/python scripts/e1_compute_agreement.py \
  --answers outputs/iclr/e1_dataset/answers/jazz_pilot_answers.json \
            outputs/iclr/e1_dataset/answers/jazz2_pilot_answers.json \
  --keymap outputs/iclr/e1_dataset/private/keymap.json --phase pilot
```

The private keymap is for the coordinator's local command only and must not be shared with
Jazz 2. If κ is below 0.6, stop main labeling: the coordinator sends the confusion table to
Jihan, tightens boundary notes without changing the taxonomy, and both annotators re-pilot
from the reserve. A second failure is escalated to Jihan.
