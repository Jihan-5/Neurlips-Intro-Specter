# Jazz — Human Fault-Annotation Study (E1): the complete how-to

Self-contained brief, written 2026-09-17. This is **camera-ready commitment #2** (NeurIPS 30371
rebuttal, on the record): *"Human fault annotation on natural trajectories: two annotators,
5-category labels, adjudication, Cohen's κ, on real PersonalWAB + TravelPlanner-native failures;
dataset to be constructed and released."* It is also the E1 centerpiece of
`orchestration/ICLR_2027_plan.md` (§6, redesigned 2026-08-05 for annotator independence).

Point every Claude Code session at THIS file first. Background docs if needed:
`orchestration/ICLR_2027_plan.md` (E1 full design + risk register), `JAZZ_INSTRUCTIONS.md`
(repo setup, artifact sync, ground rules — all of §1–§3 there applies here too).

---

## 0. Why this study exists (read once, then it's obvious)

Reviewer **Mahh** (score 3, maintained) had one surviving objection: Intro-Specter's central
claim — *correct fault localization* — has only ever been validated on **synthetic** diagnostics
where we injected the fault ourselves, so ground truth was known by construction. The rebuttal
conceded this is real: no existing dataset supplies human fault labels on naturally-failed
agent trajectories.

This study answers it: **when a real trajectory fails naturally, do independent humans point at
the same faulty step/assumption the method does?** Two products come out:

1. A headline number for the paper: *"the method matched human consensus on X% of
   naturally-failed trajectories (N=…, 95% CI …), vs Y% for the best floor baseline."*
2. A releasable dataset: **the first fault-attribution benchmark for user-conditioned agent
   trajectories** (datasheet, CC BY 4.0, annotator instructions, per-trace JSON). This
   promotion from "validation appendix" to "contribution" makes the co-designed-harness
   objection structurally impossible to write.

**Where it lands:** NeurIPS camera-ready if the Sep 24 decision is an accept; otherwise the
ICML 2027 submission (abstract Jan 16) and/or an ICLR rebuttal. The ~2-week annotation window
deliberately finishes ~Oct 1 — after the Sep 25 crunch, in time for either branch.

---

## 1. Design decisions (frozen 2026-09-17 — do not re-litigate)

| Decision | Value | Why |
|---|---|---|
| Annotators | **8 unpaid volunteers, NONE of them paper authors** | Independence is the entire point; "the authors labeled their own system" kills the study in one review sentence. Free is fine — the design, not the payment, buys independence. |
| N (trajectories) | **120–150** | ±8pp CI at N≈130 vs ±13pp at N=50. Slices (per-benchmark, vs floors) and exclusions eat sample; start at 50 and you report N=38. |
| Labels per item | **2 independent + 3rd only on disagreement** | Cheapest design that yields Cohen's κ and a consensus label. |
| Per-annotator load | **~30–45 items ≈ 8–10 hours over 2 weeks** | 240 base labels + ~60 tiebreaks ÷ 8 people; ~15 min/item. |
| Blinding | **Annotators NEVER see the method's output** | Non-negotiable. They see the trajectory only — no arm names, no repair artifacts, no diagnosis. |
| Adjudication rule | **Written BEFORE the main batch** (§4 below) | Post-hoc rules are unfalsifiable; a reviewer will ask. |
| Pilot gate | **10–20 items, all annotators; proceed only if κ (or α) ≥ 0.6** | If humans can't agree with each other, method-vs-human accuracy is meaningless. Fix the codebook, not the data. |
| Attention checks | **~5 injected-fault items with known ground truth per annotator; exclusion rule pre-written** | Objective quality filter for volunteers. |
| Reporting | **The number goes in the paper whatever it is** | Pre-registered spirit; selective reporting is worse than a mediocre number. |
| Label taxonomy | **5 fault categories + "no identifiable fault" + "ambiguous"** (taxonomy v2, §3) | Matches the rebuttal commitment ("5-category labels"); the escape hatches prevent forced-choice noise. |

Statistical honesty line (from the ICLR plan, still binding): **N≈130 supports "beats the
floors" and nothing finer.** Per-benchmark and per-condition slices are reported as
exploratory, never as claims.

---

## 2. Pipeline overview — who does what

```
 [Claude/Jazz: automated]                    [Humans]
 1. sample_annotation_set.py      →  trajectory pool (deterministic seed)
 2. blind_trajectories.py         →  stripped, shuffled, ID-keyed items
 3. codebook (draft → frozen)     →  Jihan distributes to 8 annotators
 4. annotation pages (HTML/forms) →  PILOT (10–20 items, everyone)
 5. compute_agreement.py on pilot →  κ ≥ 0.6? — else revise codebook, re-pilot
                                  →  MAIN BATCH (2 labels/item, ~2 weeks)
 6. assignment tracker            →  3rd labels on disagreements
 7. adjudication per frozen rule  →  consensus label per item
 8. compute_agreement.py (final)  →  Cohen's κ, exclusions applied
 9. attribution_vs_human.py       →  method accuracy vs consensus + floors + MRR
10. package_e1_dataset.py         →  outputs/iclr/e1_dataset/ + datasheet
```

Humans touch steps 4–6 only. Everything else is scripted. **Jihan's only manual jobs:**
recruit the 8 people (done), send each their item batch + codebook, chase stragglers.

---

## 3. The annotation task (what goes in the codebook)

Each item shown to an annotator is a **blinded, naturally-failed trajectory**: the user
profile/context, the task, and the step-by-step agent trace (thoughts/actions/observations as
available), with method identity, arm names, and any repair/diagnosis artifacts stripped.

The annotator answers two questions:

**Q1 — fault category** (pick exactly one):
1. **Profile/memory misuse** — the agent ignored, misread, or contradicted the user's
   profile/history (used the wrong preference, stale fact, wrong user attribute).
2. **Faulty assumption / hallucinated fact** — the agent asserted or acted on information not
   grounded in the context or observations.
3. **Wrong action / tool misuse** — right idea, wrong execution: incorrect tool, malformed
   arguments, wrong item selected, misordered steps.
4. **Reasoning/planning error** — a logic step that doesn't follow: invalid inference, skipped
   constraint, goal drift, premature termination.
5. **Environment/task fault** — the failure is not the agent's: broken observation, impossible
   task, ambiguous spec, benchmark artifact.
6. **No identifiable fault** — the trajectory looks correct; the failure label may be a grader
   artifact.
7. **Ambiguous** — genuinely torn between two categories (must name both in the comment box).

**Q2 — fault location**: the index of the FIRST step at which the trajectory went wrong
(the earliest step that, if corrected, the annotator believes the task would have succeeded).
"None" allowed only with categories 5–6.

Codebook requirements (2–3 pages max): one paragraph per category, **10 worked examples**
covering every category including one ambiguous and one no-fault case, a "first faulty step,
not last" rule with an example, and the instruction *"label the trajectory, not the outcome —
a failed task can contain a locally-correct trace."*

**E6 rider (free, do it):** one extra yes/no per item — *"does the extracted graph shown in
part B faithfully reflect the trace?"* — gives extractor node/edge P/R on real traces next to
the synthetic Appendix E numbers. Only if it doesn't push per-item time past ~18 min; drop it
first if piloting shows fatigue.

---

## 4. Frozen rules (write into the repo BEFORE the main batch, verbatim)

Put these in `orchestration/e1_prereg.md`, commit, and never edit after the main batch starts:

1. **Adjudication:** two labels agree on category → consensus = that category; location
   consensus = the earlier of the two if within 1 step, else send to a 3rd annotator.
   Category disagreement → 3rd annotator; majority wins. No majority (3-way split) → item is
   "unresolved," excluded from accuracy, counted and reported.
2. **Attention checks:** each annotator gets ~5 items with injected faults of known ground
   truth, indistinguishable in presentation. Fail >2 of 5 on category → all of that
   annotator's labels excluded; their items re-assigned. Rule applies mechanically.
3. **Exclusions:** malformed/truncated trajectories found during annotation are replaced from
   a pre-sampled reserve pool (sample N+30 up front); every exclusion logged with a reason.
4. **Agreement metric:** Cohen's κ on categories over doubly-labeled items (Krippendorff's α
   as robustness check); percentage step-agreement (±1 step) for location.
5. **Accuracy metric:** method's top-1 attributed step vs consensus location (hit = exact or
   ±1 step, both reported) and category match; **exact binomial 95% CIs**; MRR over the
   method's ranked candidates.
6. **Floors (all three, no cherry-picking):** random-ancestor, most-recent-step, and a
   RAFFLES-style LLM-judge baseline run on the same blinded items.

---

## 5. Data: where trajectories come from

Sample **naturally-failed** (NOT injected-fault) trajectories, pooled across arms, with a
deterministic seed (42), from:

- **TravelPlanner-real (PRIMARY pool — 1,043 failures / 2,016 rows):**
  `outputs/real/travelplanner_real__{deepseek-v3,llama-3.1-8b,mistral-nemo-12b,...}/`.
  (Correction 2026-09-17: `outputs/dev_travel/` is a 5-row dev cell with zero failures —
  useless for sampling; the real cells are the pool.)
- **PersonalWAB (131 failures / 2,835 rows):** `outputs/rebuttal/experiment_personalwab/`
  — ⚠️ BLOCKED pending the §11 integrity decision. Plain `qwen-2.5-7b/` cells may also be
  poisoned by the OpenRouter JSON-drift bug — prefer the `-together` runs.
- Reserve pool: +30 extra items from the same sources.
- Attention-check items: ~10 injected-fault trajectories with known ground truth from
  `outputs/synthetic_single_fault/` (or any injected-fault cell), reformatted identically.

**The summary JSONLs do not contain step-level trajectories.** Full traces are produced by
the new `--dump-traces` backfill (§10) — with a warm completions cache the rerun is
near-free and appends nothing to the existing JSONLs.

`outputs/` travels on the `artifacts` branch — `./scripts/sync_artifacts.sh pull` first
(see JAZZ_INSTRUCTIONS §2b).

Stratify the sample: roughly proportional across (benchmark × model × arm) cells, then
shuffle and strip. The sampling script logs the exact per-cell counts.

---

## 6. Build list (all automatable — Claude does these, in order)

1. `scripts/e1_sample_annotation_set.py` — deterministic sampling per §5; writes
   `outputs/iclr/e1_dataset/raw_pool.jsonl` + per-cell count log.
2. `scripts/e1_blind_trajectories.py` — strips method identity/arm/repair artifacts, assigns
   opaque item IDs, interleaves attention checks, shuffles per-annotator;
   writes `items/{item_id}.json` + a **private** `keymap.json` (item ID → source; never
   shared with annotators; gitignored until release).
3. `orchestration/e1_codebook.md` — the 2–3 page guide per §3 (draft → pilot → freeze).
4. `scripts/e1_make_annotation_pages.py` — one self-contained HTML page per annotator batch
   (trajectory rendered readably, radio buttons for Q1, number field for Q2, comment box;
   "download answers as JSON" button — no server, no accounts; works over email/Drive).
5. `orchestration/e1_prereg.md` — the frozen rules of §4.
6. `scripts/e1_compute_agreement.py` — κ, α, location agreement, attention-check screening,
   adjudication queue generator.
7. `scripts/e1_attribution_vs_human.py` — runs/loads the method's attribution on the same
   items + the three floors; accuracy, CIs, MRR; emits the paper table
   (`e1_attribution_accuracy.csv`).
8. `scripts/e1_package_dataset.py` — release bundle: per-trace JSON, consensus labels,
   datasheet, codebook, CC BY 4.0 LICENSE, into `outputs/iclr/e1_dataset/release/`.

Ground rules from JAZZ_INSTRUCTIONS apply: numbers only from aggregation scripts over
committed artifacts; scripts resumable; artifacts pushed via `sync_artifacts.sh` after every
milestone; status appended to `orchestration/team_status.md` each session.

---

## 7. Timeline (2 weeks + 2 days, day 0 = materials ready)

| Days | What | Owner |
|---|---|---|
| 0–1 | Build list §6 items 1–5; Jihan sanity-reads codebook | Claude + Jihan |
| 2–3 | **Pilot:** all 8 annotators label the same 10–20 items | annotators |
| 3 | Pilot κ; if < 0.6 → revise codebook, re-pilot (budget one redo max) | Claude |
| 4–11 | **Main batch:** ~30–35 items each, 2 labels/item | annotators |
| 8 | Mid-point nudge: progress check, chase stragglers | Jihan |
| 11–13 | Tiebreak round (3rd labels on disagreements, ~expect 20–35% of items) | annotators |
| 13–14 | Adjudication per frozen rule; final κ; attribution vs floors; tables | Claude |
| 14–16 | Dataset packaging + datasheet; results paragraph drafted | Claude |

**Escalation triggers (ping Jihan immediately):** pilot κ < 0.6 twice · >2 annotators
inactive by day 8 · any attention-check exclusion (changes coverage math) · method accuracy
lands below the best floor (paper framing must change — flag, don't spin).

---

## 8. Expected results & how they'll be read

What we expect, and what each outcome means (all get reported regardless):

- **Human-human agreement (κ):** target ≥ 0.6 (substantial). 0.4–0.6 is publishable with
  discussion ("fault attribution is genuinely hard for humans — which itself motivates
  tooling"); < 0.4 after a codebook revision means the taxonomy, not the study, is the
  finding.
- **Method vs human consensus:** the working hypothesis is **~65–80% category+location
  agreement**, clearly above floors (random-ancestor lands ~1/trajectory-length ≈ 10–20%;
  most-recent-step typically 20–35%; RAFFLES-style judge is the serious comparator).
  At N=130, 72% observed → 95% CI ≈ [64%, 79%].
- **The claim the paper makes:** "beats the floors" — nothing finer. Slice tables
  (PersonalWAB vs TravelPlanner, per-model) go in the appendix marked exploratory.
- **Category distribution** of natural failures feeds the rebuilt empirical §4.5 taxonomy
  (replaces the asserted four-cell 100% claim).
- **Deliverable sentences** (targets, numbers TBD from artifacts — never hand-typed):
  *"On N=1xx naturally-failed trajectories from PersonalWAB and TravelPlanner, two independent
  non-author annotators agreed on fault category with κ = 0.xx; the method's top-ranked
  attribution matched adjudicated human consensus on xx% of trajectories (95% CI xx–xx),
  versus xx% for the strongest baseline."* Plus: *"We release the first human-annotated
  fault-attribution benchmark for user-conditioned agent trajectories."*

Failure modes that are still wins: low κ → finding about task difficulty + released dataset
stands; method below RAFFLES → honest comparison table, method keeps the cost/structure
advantages argued elsewhere. The only unpublishable outcome is an unrun study.

---

## 9. When to ping Jihan (don't sit on these)

1. Codebook draft ready for sanity-read (blocks pilot).
2. Pilot κ, the moment it's computed.
3. Any escalation trigger from §7.
4. Final headline number — **send it raw; what the paper claims branches on it. Do not
   reconcile against paper text yourself** (same rule as E1-SPR in JAZZ_INSTRUCTIONS).
5. The §11 PersonalWAB decision (blocks the PersonalWAB half of the pool).

---

## 10. BUILD STATUS + runbook (2026-09-17)

Built and tested this session (branch `worktree-jazz-annotator-instructions`):

| Piece | Status |
|---|---|
| `orchestration/e1_codebook.md` (v1, 11 worked examples) | ✅ written — needs Jihan sanity-read |
| `orchestration/e1_prereg.md` (frozen rules, DRAFT until pilot) | ✅ written |
| `scripts/e1_compute_agreement.py` (κ, α, screening, consensus) | ✅ tested on fixtures |
| `--dump-traces` in `intro_specter/runner.py` + CLI | ✅ smoke-tested end-to-end on dev_travel: full steps/profile/DAG dumped, zero new API spend, no JSONL duplication |
| `--dump-traces` in `scripts/rebuttal_experiment_personalwab.py` | ✅ implemented (same backfill semantics), not yet run |
| `scripts/e1_sample_annotation_set.py` (stratified, seed 42) | ✅ tested |
| `scripts/e1_blind_trajectories.py` (blinding, keymap, assignments) | ✅ tested — no identity leaks in items/pages |
| `scripts/e1_make_annotation_pages.py` (offline HTML, autosave, download) | ✅ tested; answers round-trip into the agreement script |
| `scripts/prep_personalwab_compact.py` (rebuild lost data file) | ✅ task-id verification PASSES 60/60 (see §11) |
| `scripts/e1_attribution_vs_human.py`, `e1_package_dataset.py` | ⬜ not yet written (needed at study end, ~day 13) |

**Runbook to annotation-ready (order):**

```bash
set -a; source .env.local; set +a
# 1. Trace backfill over the TravelPlanner-real cells (warm cache => ~free;
#    verify configs' cache_path matches the cache used originally):
for m in deepseek-v3 llama-3.1-8b mistral-nemo-12b; do
  intro-specter run --config configs/real/real_travelplanner_real__${m}.yaml --dump-traces
done
# also one injected-fault cell for attention checks, e.g.:
intro-specter run --config <synthetic_single_fault config> --dump-traces

# 2. Sample + blind + pages:
python3 scripts/e1_sample_annotation_set.py \
  --traces outputs/real/travelplanner_real__*/traces \
  --n 135 --reserve 30 \
  --attention-traces <injected traces dir> --n-attention 10 \
  --attention-gt <gt json>  \
  --out outputs/iclr/e1_dataset/raw_pool.jsonl
python3 scripts/e1_blind_trajectories.py --pool outputs/iclr/e1_dataset/raw_pool.jsonl \
  --out-dir outputs/iclr/e1_dataset --annotators 8 --pilot 15 --checks-per-annotator 5
python3 scripts/e1_make_annotation_pages.py --dataset-dir outputs/iclr/e1_dataset

# 3. Send each person their personN_pilot.html + codebook + their copy of
#    PERSON1_ANNOTATOR_INSTRUCTIONS.md (name-swapped). keymap.json stays PRIVATE.
```

Attention-check ground truth: injected-fault traces know the true fault node; map it to
(category, step) once per item into the `--attention-gt` JSON by hand-checking ~10 items.

---

## 11. ⚠️ PersonalWAB integrity finding (2026-09-17) — decision needed from Jihan

While rebuilding the lost PersonalWAB compact data file (it lived in a session /tmp
scratchpad and was deleted; the prep script was never committed), verification against the
completion cache surfaced this:

- The Jul 27 runs behind `outputs/rebuttal/experiment_personalwab/` were made with
  **unfiltered user histories**: profile spans included purchases with timestamps AFTER
  the task, proven by a cached completion for `pwab_real_00000_BT2IRYMQ` whose
  purchase-history observation lists the Gootium bag bought post-task. The current
  loader's `ts < task_ts` + target-exclusion filter (with the comment "excluding it
  avoids leaking the label") was added later and was NOT active for those runs.
- Since the target interaction sits in the user's history at the task timestamp, the
  **target item itself was very likely present in the profile shown to the model** —
  i.e., the recommend-task numbers in §4.7 may be inflated by label leakage.
- Byte-exact reconstruction of those runs is not possible: the Jul-27 runtime code was
  never committed (the Sep 9 commit squashed everything after later fixes). A
  `legacy_unfiltered_history` forensic flag was added to the loader to document the
  behavior; cache-key probes still miss on other unknowable formatting details.
- The rebuilt compact file itself is GOOD: `scripts/prep_personalwab_compact.py` passes
  the task-id check 60/60 (row order/count/user selection provably correct). Regenerate
  it any time with the commands in that script's docstring; set `PERSONALWAB_COMPACT`.

**Decision fork (Jihan):**
- (a) **Rerun PersonalWAB with the current fixed loader** + rebuilt compact +
  `--dump-traces` (real API cost, cheap models; produces clean trajectories for E1 AND
  leak-free numbers that would replace §4.7's if they differ), or
- (b) keep E1 on the TravelPlanner-real pool only (1,043 failures is ample) and handle
  the PersonalWAB question separately.
Either way: **flag, don't fix silently** — the current §4.7 numbers and the rebuttal
claims rest on the leaky runs.
