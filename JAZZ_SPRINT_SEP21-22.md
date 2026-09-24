# Jazz — experiments-only sprint, DONE by end of Sep 22 (supersedes the Sep-24 schedule in ACTION_PLAN_2026-09-21.md)

Scope: **experiments and generated artifacts only.** All tex/paper writing is Jihan's —
do NOT touch `paper_final.tex`, the abstract, or prose sections. Your deliverables are
JSONLs, generated tables/JSON summaries, and artifact-branch pushes.

> **Track P scope clarification (recorded 2026-09-23):** Jihan explicitly said “Leave out bro” for Qwen, as confirmed by the coordinator. The authorized clean scope is Llama + Mistral only. The original Qwen launch line below is superseded; do not run or substitute Qwen. Completion evidence: `orchestration/jazz_sprint_handoff_2026-09-23.md`.

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

## Track A — E1 annotation labels (SEQUENTIAL two-annotator plan, revision 2 — 2026-09-21)

Everything is staged (`outputs/iclr/e1_trace_pool` frozen, pages verified). Per Jihan:
annotators are **Jazz 1** (you first) and **Jazz 2** (starts when you finish). Sequential
is fine for κ — independence is about blinding, not timing. Hard rules that make the κ
real: **Jazz 1 and Jazz 2 must be two different humans** (the same person labeling twice
is not two annotators and will not be presented as such); Jazz 2 never sees Jazz 1's
labels, notes, or the method's outputs — only their own pages + the codebook. Regenerate
pages with `scripts/e1_blind_trajectories.py --annotator-ids jazz1 jazz2` +
`e1_make_annotation_pages.py` (deterministic — same items, fresh per-annotator shuffle
and private keymap). Record both names/roles for the datasheet.

**Sequencing (κ pilot gate moves to Jazz 2's entry, since it needs both pilots):**

- **TODAY Sep 21:** Jazz 1 labels the 15-item pilot (~3–4 h), then continues straight
  into the main 90 items (85 natural + 5 hidden attention checks). Target: pilot by
  midday, ~half the main batch tonight (~10–12 min/item).
- **Sep 22, morning:** Jazz 1 finishes the main batch. **Jazz 2 starts the moment Jazz 1's
  pilot exists** if they're available sooner — earlier overlap is better, sequential is
  the latest-allowed schedule, not the goal.
- **Jazz 2 entry gate:** Jazz 2 labels the 15-item pilot first →
  `scripts/e1_compute_agreement.py` on the two pilots. κ ≥ 0.6 → Jazz 2 proceeds to the
  main 90. κ < 0.6 → send Jihan the confusion table; tighten codebook boundary notes
  (no taxonomy changes), both re-pilot from the 30-item reserve. Second failure →
  escalate to Jihan.
- **Sep 22, by ~22:00:** both label sets complete. Run final agreement → κ, apply the
  pre-written attention-check exclusion rule mechanically, emit the flagged-disagreement
  list to Jihan the moment it exists (he adjudicates — his lane).
- **Fallback (pre-authorized, NOTIFY Jihan first):** if Jazz 2 cannot finish by Sep 22
  night, ship Jazz 1's complete set as "single-annotator preliminary" with Jazz 2's
  partial progress recorded; κ completes when Jazz 2 finishes (camera-ready window). No
  fake second set, ever.

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
Sep 21 10:00  A: Jazz 1 pilot → main batch part 1 (Jazz 2 onboarded, waiting or overlapping)
Sep 21 night  A: Jazz 1 main batch continues (~5h more)   ∥  P: cells running
Sep 22 day    A: Jazz 1 finishes main ─ Jazz 2 pilot → κ gate → Jazz 2 main  ∥  P3-P4: aggregate + push when cells finish
Sep 22 22:00  A: both sets done → final κ + flags → Jihan (adjudication, his lane)
Sep 22 night  G: final κ, attribution-vs-human, packaging, artifact push — DONE
```

## Escalate to Jihan immediately (don't sit on these)

- Pilot κ < 0.6 twice · no annotator 2 by Sep 21 evening (switching to the single-annotator fallback is a NOTIFY, not a silent switch)
- OpenRouter headroom < $15 mid-run · any provider dying (probe before relaunching)
- Clean PersonalWAB delta flips sign or loses significance (report, don't wait for the grid)
- Anything that makes the Sep 22 finish impossible — say so the moment you know, with ETA.

Everything else in ACTION_PLAN_2026-09-21.md (tex sweep, language pass, abstract, gates,
AC file) is Jihan's side — ignore it.
