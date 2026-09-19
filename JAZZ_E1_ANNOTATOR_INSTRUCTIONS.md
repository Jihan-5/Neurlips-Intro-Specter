# E1 labeling — Jazz (Annotator 1)

Read `orchestration/e1_codebook.md` before labeling. Do not inspect
`outputs/iclr/e1_dataset/private/keymap.json`, source traces, model names, method names, or the
other annotator's answers. Do not use AI assistance or discuss judgments with Mahfuza.

1. Open `outputs/iclr/e1_dataset/annotation_pages/jazz_pilot.html` in a browser.
2. Label all 15 pilot items. For each item, choose one category and the earliest faulty
   step. Use `None` only for categories 5 or 6; category 7 requires both candidate
   categories in the comment.
3. Click **Download answers** and save the file as `jazz_pilot_answers.json` under
   `outputs/iclr/e1_dataset/answers/`.
4. Do not open the main page until the two pilot files have been analyzed and the pilot
   Cohen's kappa is at least 0.6.
5. After the gate passes, open `annotation_pages/jazz_main.html`. It contains 85 natural
   items plus five indistinguishable attention checks. Save the download as
   `answers/jazz_main_answers.json`.

Deadline recovery schedule (current date 2026-09-19): finish the 15-item pilot first
today. If the gate passes, also finish main-page items 1–45 today; finish items 46–90 on
Sep 20. Download an in-progress JSON at the end of every sitting and the complete main
JSON on Sep 20. Sep 21 is reserved for Jihan's adjudication and final computation.

Work in sittings of at most ten items. Flag malformed or unreadable items in the comment
and stop on that item rather than guessing.

After both pilot downloads exist, the prepared gate command is:

```bash
.venv/bin/python scripts/e1_compute_agreement.py \
  --answers outputs/iclr/e1_dataset/answers/jazz_pilot_answers.json \
            outputs/iclr/e1_dataset/answers/mahfuza_pilot_answers.json \
  --keymap outputs/iclr/e1_dataset/private/keymap.json --phase pilot
```

After both main downloads exist, use the same tool with `--phase main` and
`--emit-adjudication-queue outputs/iclr/e1_dataset/adjudication_queue.json`; then build
Jihan's page with `scripts/e1_make_annotation_pages.py --phase adjudication --queue ...
--annotators jihan`. No consensus is emitted until Jihan's adjudication file is present.
