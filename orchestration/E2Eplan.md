# MASTER EXECUTION SPEC — Intro-Specter NeurIPS 2026 Rebuttal Campaign
### Submission 30371 · Discussion deadline: ~4 days from 2026-07-24 · This file is the single source of truth for WHAT we are trying to achieve.

> Status note (added by orchestrator, do not delete): this file is frozen as the original plan.
> Live progress against it is tracked in `directions.md` (what to do next) and `live_updates.md`
> (what has actually happened, including deviations from this plan and why). If reality and this
> plan diverge, `live_updates.md` wins — update this file's "Amendments" section at the bottom
> rather than editing the body.

You are Claude Code, operating inside the Intro-Specter experiment repository. Your mission: execute four experiments, fill every placeholder in four pre-written rebuttal drafts with verified numbers, produce a sentence-level coverage audit proving every reviewer sentence is answered, and prepare final paste-ready rebuttal texts. The quality bar is: **every single sentence in every review receives a mapped, evidenced answer.** The strategic reality is: the decision hinges on converting two "3 (borderline reject)" reviews to 4 and raising the champion's confidence from 3 to 4.

---

## 0. NON-NEGOTIABLE RULES (read before anything else)

1. **No number enters a rebuttal unless you computed it from a run artifact in this repo.** Every filled ⟨TODO⟩ must be traceable: JSONL path → aggregation command → value. Keep a `rebuttal_numbers_audit.md` logging each: tag, value, source file, command, timestamp.
2. **If a result is unflattering, use the designated fallback framing (§4 decision rules) — never soften, omit, or shade it.** The two hostile reviewers are confidence-4. One inflated claim destroys all three threads. Honesty is the strategy, not a constraint on it.
3. **If a run fails or time runs out, the TODO is replaced with the designated no-result fallback text, and you report the gap to Jihan.** Never estimate, never extrapolate, never reuse a "similar" number.
4. **Do not modify the paper, the method, or any main-experiment artifact.** Rebuttal-period work is additive: new configs, new modules, new output dirs.
5. **Anonymity:** no author names, no institution hints, no external links in rebuttal text (exception: anonymized code link if the AC explicitly requests code). No acknowledgments sections.
6. **Character limit: 10,000 per rebuttal (OpenReview, markdown allowed, no file uploads).** Verify final counts with `wc -m` on the paste-ready text (strip the draft files' header/footer notes, which are not posted).
7. **Human sign-off:** final paste-ready texts go to Jihan for approval before posting. You prepare; authors post.
8. Reproducibility discipline for NEW runs = same as paper: deterministic example sampling `Random(42*1,000,037+idx)`, method seeds {0,1,2} for stochastic methods, temperature 0.0 (deterministic prompts) / 0.7 (stochastic-by-design), identical example IDs across paired methods, SQLite cache keyed by SHA-256 of (provider, model, temperature, system_prompt, user_prompt, max_tokens, seed).

---

## 1. CONTEXT PACK

**Paper:** Intro-Specter (submission 30371). Method: extract Assumption-DAG from agent trajectory → on profile violation, counterfactual repair trials score candidate faulty ancestors (Eq. 1–2) → min-cost selective repair of downstream subgraph (Eq. 3–4) → SPR posterior refinement on repair rejection (Eq. 5). Key hyperparams (Table 11): M=1, priors π=(0.45, 0.33, 0.22), λ=0.3, edit-cost w=(0.4,0.3,0.2,0.1), δ=0.25 (abstention threshold), T_spr=2, α=0.1.

**Review state:** LDZz **5** (conf 3, the champion — asks about Figure 1 cycles + multi-violation handling) · Mahh **3** (conf 4 — synthetic-construct objection, incrementality, profile-immutability, small-margin-vs-Reflexion question) · 4jc8 **3** (conf 4 — SE/fault-tolerance prior art uncredited, claims overclaimed) · AC metareview lists 4 fix paths: natural failures, validation beyond injection, related-work treatment, exposition. Full verbatim texts: Appendix R (see original conversation / OpenReview thread — not reproduced here to keep this file bounded; orchestrator/subagents should fetch from OpenReview submission 30371 discussion thread if the exact text is needed again).

**Paper fact sheet AS ORIGINALLY GIVEN ("verified against the submitted PDF" — TREAT AS UNVERIFIED, see Amendments):**
- 16 cells (4 benchmarks × 4 LLMs), 864 paired observations. n=60/cell (n=36 TruthfulQA). Per-cell MDE ≈ 13pp (§6 Limitations); per-cell claims descriptive.
- Pooled: Intro-Specter **87.0%** vs Reflexion **85.4%** (+1.6pp); single-round (no SPR) 84.3%.
- 15/16 cells highest/tied-highest; 8 wins, 7 ties, 1 NS loss (Table 6). NS loss: LongMemEval×Llama70B −1.7pp, p=1.000, CI [−11.7,+8.3].
- Strict wins vs Reflexion: MuSiQue×Mistral 91.7% (+6.7, p=.012); TruthQA×Mistral 86.1% (+5.5, p=.012); TruthQA×Qwen 77.8% (+8.4); 2Wiki×Qwen 94.9% (+3.2). Mid-tier (7–12B): top/tied 12/12.
- SPR: fires on 6 cells, +3.3…+11.7pp, avg +7.2pp (Table 10, Appendix A).
- Tokens/task (Table 7): IS 3.1–6.5k; Reflexion 2.6–5.9k; SelfCheckGPT 5.9–12.1k; ToT 11.2–13.3× IS.
- Ablations (Table 8, 4 cells): no-DAG −2.8 mean (−8.3 worst); uniform prior −3.1 (−8.3); no counterfactual −1.5 (−8.3 worst); no edit-cost −0.6; M=3 −5.0.
- VRP (Table 9): TruthQA×Mist 61.1 vs IS 86.1 (+25.0, p=.012); TruthQA×Qwen 44.4 vs 77.8 (+33.3, p<.001); 2Wiki×Mist tie 96.7; LongMem×Llama8B 76.7 vs 78.3 (+1.7, p=1.0). VRP < Direct on both TruthQA cells. Paper §4.4 "Scope": iterative-VRP not run — "highest-priority follow-up."
- Mechanism diagnostics (§4.1, n=60 synthetic graphs): 100% top-1 attribution (MRR 1.0), 100% repair in single_fault; forward-only baselines 0%; multi_valid → min-cost valid repair every trial.
- DAG extraction (Table 12/Appendix E): node P/R .94/.91; edge P/R .88/.82; cycle rate 5% (resolved by removing edge with min endpoint confidence).
- TravelPlanner (Appendix I, native/un-injected, n=36/cell): 1 numerical win (Llama70B 33.3 vs Rfx 25.0), 3 NS losses (p≥.180); absolute numbers disclaimed vs official evaluator.
- Failure taxonomy (§4.5): on 4 ablation cells, 100% of IS failures are repair-stage (buckets iv–v); explicitly scoped to those cells.
- Profiles: bank of 28 constraint templates; 50% relevant / 50% irrelevant distractors; deterministic per (task_id, seed).
- Infra (Appendix C): all inference via OpenRouter (Llama-3.1-8B, Mistral-Nemo-12B, Qwen2.5-7B) + Together (Llama-3.3-70B); `run_real_benchmark.py` + `configs/real/*.yaml` → `outputs/real/<dataset>__<model>/*.jsonl`; `scripts/aggregate_real_benchmarks.py`; `scripts/regen_pvalue_tables.py`; prompts in `intro_specter/prompts.py`; SQLite cache shipped; total prior spend ≈ $70.

**Rebuttal drafts (in `rebuttal/`):** `01_reviewer_Mahh_rebuttal.md`, `02_reviewer_4jc8_rebuttal.md`, `03_reviewer_LDZz_rebuttal.md`, `04_optional_AC_comment.md`, plus `00_STRATEGY_AND_SCHEDULE.md`. NOTE: as of orchestration setup, this directory did NOT exist in the repo — these must be authored from scratch, not "filled in." See Amendments.

---

## 2. PHASE 0 — REPRODUCTION GATE

Purpose: prove the harness works before building on it, and prove the paper's numbers regenerate from artifacts.

1. Locate repo root, SQLite cache, `outputs/real/` (16+ `<dataset>__<model>` dirs expected).
2. Run `scripts/aggregate_real_benchmarks.py` → confirm it reproduces Tables 2–5 headline numbers EXACTLY.
3. Run `scripts/regen_pvalue_tables.py` → confirm Appendix F values regenerate.
4. **GATE: if any number mismatches the fact sheet above, STOP. Do not run experiments. Report the discrepancy to Jihan immediately.**
5. Record cache-hit behavior on a 5-example dry run of one cell.

---

## 3. PHASE 1 — THE FOUR EXPERIMENTS

Global notes: create `configs/rebuttal/` and `outputs/rebuttal/` (never write into `outputs/real/`). Reuse existing method implementations untouched. Paired design everywhere. Budget guardrail: ~$80 total, report before proceeding if projected to exceed it. Priority if time collapses: **A > B > C > D-synthetic > D-real.**

### EXPERIMENT A — Profile-noise robustness (Mahh W3, AC bullet 2)
`intro_specter/profile_corruption.py`: `stale_swap`, `contradict`, `omit` operators. Original profile = scoring ground truth; corrupted profile = what the agent/pipeline sees. ρ ∈ {10%,30%}. Arms: IS + Reflexion. Cells: TruthQA×Mistral, TruthQA×Qwen first; extend if budget allows. Metrics: success, abstention_rate, misattribution_rate, paired Δ+McNemar+CI. Decision rules F-A1/F-A2/F-A3 per honesty framing (see full text preserved in conversation history / git blame of this file's first version if needed verbatim).

### EXPERIMENT B — Iterative-VRP at matched retry budget (Mahh W2+Q1, AC bullet 2)
`IterVRP` = VRP baseline wrapped in ≤3-round retry loop (=1+T_spr). Cells: TruthQA×Mistral, TruthQA×Qwen, 2Wiki×Mistral. Metrics: success, Δ vs IS, tokens. Decision rules F-B1/F-B2/F-B3.

### EXPERIMENT C — Natural-fault annotation (Mahh W1, AC bullet 1)
Sample N=50 failing un-injected trajectories (TravelPlanner + LongMemEval oracle-mode). Two-annotator (authors) protocol, 5-category cause label, adjudication, Cohen's κ. Run IS attribution on assumption-driven subset, top-1 agreement. Mandatory disclosure: annotators are authors, not blind.

### EXPERIMENT D — Multi-fault stress test (LDZz question)
Extend synthetic diagnostic generator to `multi_fault` mode (2 independent faults), n=60 graphs. Metrics: % resolved within T_spr=2, % both faults in top-2, % genuinely interacting. Optional real tier (2Wiki×Mistral double-injection) only after A/B/C done.

---

## 4. PHASE 2 — STATISTICS PROTOCOL

Paired exact McNemar + 95% paired-bootstrap CI (10,000 resamples), reusing/extending `scripts/regen_pvalue_tables.py` machinery. Report p-values uncorrected, say so explicitly. Cohen's κ for Experiment C. **Sanity bounds check before any number goes in text**: a Δ≥25pp at n=60 cannot have p=1.0; a Δ of 0 cannot have p<.05 — this exact class of error is what PAT's automated feedback caught in the original submission (see Amendments — this turned out to be a *real*, still-unresolved data-pipeline issue, not just a writing slip).

---

## 5. PHASE 3 — TODO REGISTRY

(See original spec text for the full per-file TODO tag table: TODO-A1/A2, TODO-B1-B5, TODO-C1-C6, TODO-D/D2, plus AC-comment equivalents. Preserved in `orchestration/live_updates.md` history and in the first conversation turn if needed verbatim — not duplicated here to keep this file bounded.)

---

## 6. PHASE 4 — SENTENCE-LEVEL COVERAGE AUDIT

Build `rebuttal/coverage_matrix.md`: one row per substantive reviewer sentence, columns: sentence ID, quote, response file+section, status (ANSWERED-WITH-DATA / ANSWERED-WITH-ARGUMENT / CONCEDED-WITH-COMMITMENT / NOT-ADDRESSED). Pre-mapped rows for Mahh (M1-M6), 4jc8 (J1-J8), LDZz (L1-L3), AC (AC1-AC4) — full mapping preserved from original spec; fetch verbatim reviewer text from the OpenReview submission-30371 thread when authoring this file.

---

## 7. PHASE 5 — FINALIZE & POST PROTOCOL

Post order: 4jc8 + LDZz first (Day 1 if possible), Mahh by Day 3, AC comment last. Pre-post checklist: no ⟨TODO⟩ remaining, numbers consistent across files, `wc -m` < 10,000, no identity leaks, coverage matrix has zero NOT-ADDRESSED, stats sanity bounds pass, **Jihan has read and approved.**

## 8. PHASE 6 — DISCUSSION-PERIOD PLAYBOOK

Check OpenReview ~every 6 waking hours (human does this — no OpenReview posting/reading tool is available to the agent). Reviewer replies get drafted responses within 12h. 48h before deadline, one polite nudge max per unengaged hostile reviewer. Log interactions in `rebuttal/discussion_log.md`.

## 9. WHAT DONE LOOKS LIKE

Four paste-ready texts under 10k chars each, every number audited, coverage matrix complete with zero gaps, experiments A–D reported honestly, all posted with author approval.

---

## AMENDMENTS (orchestrator-maintained — append only, do not rewrite history above)

- **2026-07-24, orchestration setup:** `rebuttal/` directory did not exist at plan intake — drafts must be authored from scratch, not filled in. Fact sheet above is UNVERIFIED — Phase 0 gate FAILED twice:
  1. Found and fixed a real bug in `scripts/aggregate_real_benchmarks.py` (naive `partition("__")` on cell-dir names caused `outputs/real/ablation/*`, `cascade/*`, `n120/*` auxiliary-tier directories — which use a 3-part `{tag}__{dataset}__{model}` naming scheme — to be recursively picked up and mis-parsed into the main 16-cell aggregation, corrupting dataset/model columns). Fix: restrict `load_results()` to direct children of `outputs/real` only. This part is resolved and safe (script-only change, no main-experiment artifacts touched).
  2. Even after the fix, per-cell `outputs/real/musique_real__mistral-nemo-12b/musique_real__all__summary.csv` (committed artifact, untouched by us) shows Intro-Specter **losing** to Reflexion (81.7% vs 85.0%, p=.754) on MuSiQue×Mistral — directly contradicting the fact sheet's claim of a 91.7% "+6.7pp, p=.012 strict win." LongMemEval×Llama70B similarly shows a −13.3pp gap vs the claimed −1.7pp near-tie. Root cause NOT YET DIAGNOSED — decision made to treat current `outputs/real/` as ground truth and rebuild the fact sheet from it rather than chase the discrepancy further, given deadline pressure. **This means several headline claims in the fact sheet above (91.7% MuSiQue win in particular) may not survive and must be re-derived, not assumed, before use in any rebuttal text.**
  - This directly overlaps with PAT's own pre-submission feedback flagging impossible p-values, an oracle-disagreement-rate arithmetic contradiction, a TravelPlanner win/loss mischaracterization, and missing MuSiQue data from several tables — i.e., PAT was very likely reacting to a real, still-partially-unresolved data pipeline problem, not hallucinating.
- **2026-07-24, official timeline received**: NeurIPS PC email confirms Phase 1 (author-response-only, invisible to reviewers) runs Jul 23–27; Phase 2 (visible discussion) Jul 27–Aug 3; Phase 3 (reviewer/AC only, authors locked out) Aug 3–10. Target: all rebuttal texts postable by end of Jul 27 so they're visible at the start of Phase 2. This supersedes the earlier rough "~4 days" deadline estimate — see `directions.md`'s Deadlines section for the authoritative dates.
- Work paused here at user's request to first build a persistent orchestration/memory layer (`directions.md`, `live_updates.md`, `triggers.md` + a `/loop`-driven orchestrator using `/research_power` for progress evaluation) modeled on OpenClaw's `MEMORY.md` + daily-notes + distillation pattern (see https://docs.openclaw.ai/concepts/memory). Rebuttal execution resumes once that layer exists.
