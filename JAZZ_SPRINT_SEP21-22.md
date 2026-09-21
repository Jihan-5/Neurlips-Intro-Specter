# Jazz — experiments-only sprint, DONE by end of Sep 22 (supersedes the Sep-24 schedule in ACTION_PLAN_2026-09-21.md)

Scope: **experiments and generated artifacts only.** All tex/paper writing is Jihan's —
do NOT touch `paper_final.tex`, the abstract, or prose sections. Your deliverables are
JSONLs, generated tables/JSON summaries, and artifact-branch pushes.

Three tracks. **P and A start NOW and run in parallel** — P is API-bound (background),
A is your hands. G chains off A.

---

## Track P — PersonalWAB clean rerun (D7: GO — approved by Jihan)

The Jul-27 runs are contaminated (post-task purchases in profiles; target likely visible).
Re-run clean. This is background work — launch it, then go label.

1. **Rebuild clean compact** (~30 min):
   `scripts/prep_personalwab_compact.py` with histories truncated strictly BEFORE task time.
   Verify with the built-in 60/60 task-id check **plus** an explicit leak check: assert no
   ground-truth ASIN appears anywhere in any profile/history string. If the script lacks a
   before-task-time mode, add the filter there (that's experiment infra, not paper writing).
2. **Launch all cells** (background, nohup + caffeinate, per-cell logs):
   `scripts/rebuttal_experiment_personalwab.py` for every model×arm on the clean build.
   Same protocol as July: 60 examples × seeds 0,1,2, bench_seed 42. Models: mistral-nemo-12b,
   llama-3.1-8b (OpenRouter — Jihan's key has $46.68), qwen-2.5-7b via Together
   (`Qwen/Qwen2.5-7B-Instruct-Turbo`, own cell label, as before). Expect cache misses
   (new prompts); budget ~$5–10. Probe the key first; ping Jihan if headroom < $15.
3. **Aggregate when complete**: pooled + per-model success, paired exact McNemar IS vs each
   baseline on (task_id, seed), 95% paired-bootstrap CIs — regenerate
   `outputs/rebuttal/experiment_personalwab_clean/SUMMARY.md` **from the JSONLs only**.
   Keep the old contaminated tree untouched for the continuity appendix.
4. **Push to artifacts branch** with the safe sync script.
5. **Report the pooled clean IS-vs-Reflexion delta + p to Jihan the moment it exists** —
   the abstract has one sentence waiting on it. If the delta flips sign or loses
   significance: report it exactly as observed, immediately — no interpretation.

## Track A — E1 annotation labels (your hands; Mahfuza in parallel)

Everything is staged (`outputs/iclr/e1_trace_pool` frozen, pages verified). What's missing
is labels. Compressed to 2 days:

- **TODAY Sep 21, morning:** you and Mahfuza independently label the 15-item pilot
  (~4 h each). Jihan is telling Mahfuza her start is NOW; if she hasn't started by
  mid-afternoon, escalate to Jihan immediately (fallback: Jihan labels as annotator 2,
  disclosed).
- **TODAY, evening:** `scripts/e1_compute_agreement.py` on the pilot. κ ≥ 0.6 → start the
  main batch TONIGHT. κ < 0.6 → send Jihan the confusion table, tighten the codebook
  tonight (category boundary notes only — no taxonomy changes), re-pilot from the 30-item
  reserve first thing Sep 22. Two failures → escalate; Jihan decides the collapsed-taxonomy
  fallback.
- **Sep 21 night → Sep 22:** main batch, 90 items each (85 natural + 5 hidden attention
  checks). At ~10–12 min/item that is ~16–18 h — split it: ~5 h tonight, the rest through
  Sep 22. Do NOT discuss items with Mahfuza mid-batch; disagreements get flagged, never
  self-resolved.
- **Sep 22, by ~20:00:** both label sets complete. Run agreement → κ, apply the pre-written
  attention-check exclusion rule mechanically, emit the flagged-disagreement list, and send
  it to Jihan the moment it exists (he adjudicates same evening — that's his lane).

## Track G — final numbers + packaging (Sep 22 night, after Jihan's adjudication lands)

1. `scripts/e1_compute_agreement.py` final pass with consensus labels → final κ (+ α).
2. Attribution-vs-human comparison: method top-1 vs consensus, MRR, and the pre-registered
   floor baselines, on the natural-failure items. Numbers from artifacts only.
3. Package `outputs/iclr/e1_dataset/` + datasheet stub (data files + README; Jihan writes
   the datasheet prose).
4. Push everything (Track P outputs, labels, agreement JSONs, packaged dataset) to the
   artifacts branch; append a team_status entry with verbatim script outputs.

---

## Hour-by-hour (target)

```
Sep 21 09:00  P1-P2: clean rebuild + leak check + launch all cells (background)
Sep 21 10:00  A: pilot labeling (you ∥ Mahfuza)
Sep 21 15:00  A: pilot κ gate → main batch starts (or codebook fix path)
Sep 21 night  A: main batch part 1 (~5h)   ∥  P: cells running
Sep 22 day    A: main batch to completion  ∥  P3-P4: aggregate + push when cells finish
Sep 22 20:00  A: final labels + flags → Jihan (adjudication, his lane)
Sep 22 night  G: final κ, attribution-vs-human, packaging, artifact push — DONE
```

## Escalate to Jihan immediately (don't sit on these)

- Pilot κ < 0.6 twice · Mahfuza not labeling by Sep 21 afternoon
- OpenRouter headroom < $15 mid-run · any provider dying (probe before relaunching)
- Clean PersonalWAB delta flips sign or loses significance (report, don't wait for the grid)
- Anything that makes the Sep 22 finish impossible — say so the moment you know, with ETA.

Everything else in ACTION_PLAN_2026-09-21.md (tex sweep, language pass, abstract, gates,
AC file) is Jihan's side — ignore it.
