# E1 pre-registration — frozen analysis rules

Status: **DRAFT until the pilot completes; FROZEN at main-batch launch.** After the freeze
commit, this file must never be edited — any deviation is reported in the paper as a
protocol deviation. (Freeze = the commit that changes this line to "FROZEN as of <date>,
commit <sha>".)

Companion docs: `JAZZ_HUMAN_ANNOTATOR_INSTRUCTIONS.md` (study design),
`orchestration/e1_codebook.md` (annotator-facing definitions),
`PERSON1_ANNOTATOR_INSTRUCTIONS.md` (annotator workflow).

## 1. Sample

- Target N = 120–150 naturally-failed trajectories; reserve pool of +30 sampled at the
  same time with the same procedure. Sampling is deterministic (seed 42), stratified
  roughly proportional across (benchmark × model × arm) cells; exact counts logged by
  `scripts/e1_sample_annotation_set.py` into the dataset manifest.
- Sources: PersonalWAB rebuttal cells (`outputs/rebuttal/experiment_personalwab/`) and
  TravelPlanner-native (`outputs/dev_travel/`). Injected-fault runs are used ONLY for
  attention-check items (~5 per annotator, drawn from `outputs/synthetic_single_fault/`).
- A "naturally-failed trajectory" = a run row with `success == false` in an arm with no
  injected corruption.

## 2. Annotation design

- 8 annotators, none an author. 2 independent labels per item; 3rd label only on
  disagreement (rule 4.1). Annotators are blind to method identity, arm, and the
  method's attribution output.
- Labels: Q1 fault category ∈ {1 profile/memory misuse, 2 faulty assumption/hallucinated
  fact, 3 wrong action/tool misuse, 4 reasoning/planning error, 5 environment/task fault,
  6 no identifiable fault, 7 ambiguous}; Q2 first-faulty-step index (integer; "None"
  permitted only with Q1 ∈ {5, 6}).
- Pilot: 10–20 common items labeled by all annotators. **Gate: proceed to main batch only
  if pilot Cohen's κ (pairwise mean over annotator pairs, categories 1–6 with 7 treated
  as its own class) ≥ 0.6.** One codebook revision + re-pilot is budgeted; a second
  failure stops the study for redesign (reported either way).

## 3. Quality control

- Attention checks: ~5 injected-fault items per annotator, presentation-identical to
  natural items, ground-truth category and step known by construction.
  **Exclusion rule (mechanical, no discretion): an annotator whose category label is
  wrong on >2 of their 5 attention checks has ALL labels excluded**; their items return
  to the assignment queue for re-annotation by others.
- Malformed items (truncated/unrenderable, flagged by annotators): replaced from the
  reserve pool; every replacement logged with item id + reason. Replaced items are
  excluded from all analyses.

## 4. Adjudication (consensus construction)

1. Q1: two labels agree → consensus is that category. Disagree → 3rd annotator;
   majority of the three wins. Three-way split → item is **unresolved**: excluded from
   accuracy computation, count reported.
2. Q2: if the two step indices are within 1 step, consensus = the earlier index.
   Otherwise the item goes to the 3rd annotator; consensus = the median of the three if
   any two are within 1 step, else unresolved (as above).
3. "Ambiguous" (7) counts as a disagreement with any specific category for adjudication
   purposes. Items whose consensus is 5, 6, or unresolved are excluded from
   method-accuracy scoring (the method's task is defined only where a fault exists);
   their frequencies are reported.

## 5. Metrics (all computed by `scripts/e1_compute_agreement.py` /
`scripts/e1_attribution_vs_human.py`; no hand computation)

- **Human agreement:** Cohen's κ on Q1 over doubly-labeled items (before any tiebreaks),
  pairwise mean across annotator pairs; Krippendorff's α (nominal) as robustness check.
  Q2 agreement: fraction of pairs within ±1 step.
- **Method accuracy:** the method's top-1 attributed node/step vs consensus Q2 — reported
  BOTH as exact match and as ±1-step match; plus Q1 category match where the method
  emits a category. Exact (Clopper–Pearson) binomial 95% CIs.
- **Ranking quality:** MRR of the consensus step in the method's ranked candidate list.
- **Floors (all three, none dropped):** (a) random-ancestor: uniform over the failed
  step's ancestors, analytic expectation; (b) most-recent-step: always the last step
  before failure; (c) RAFFLES-style LLM-judge on the same blinded items (judge model and
  prompt fixed before the freeze; recorded here at freeze time).
- **Primary claim the paper may make: method accuracy vs each floor, N pooled.**
  Per-benchmark / per-model / per-arm slices are exploratory (N≈130 supports "beats the
  floors" and nothing finer). No per-condition claim may lean on E1's n.
- All numbers are reported regardless of outcome, including κ, exclusion counts, and
  unresolved counts.

## 6. Release

`outputs/iclr/e1_dataset/release/`: per-trace JSON (blinded item + all raw labels +
consensus), codebook, datasheet, CC BY 4.0. Annotators identified as "annotator 1..8";
acknowledgment naming per individual preference.
