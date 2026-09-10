# ICLR 2027 Plan — 6-week program (Aug 5 → Sep 18/25, 2026)

Single source of truth for the post-NeurIPS-discussion upgrade program. Companion to `E2Eplan.md` (which governed the rebuttal campaign, now closed pending decision).

---

## ⚠ STATUS UPDATE 2026-08-05 — both gates resolved; plan re-targeted

**Gate 0 FAILED → target venue is now ICML 2027 (abstract ~late Jan 2027) or the NeurIPS camera-ready.** ICLR Author Guidelines (verbatim): submissions "submitted in parallel to this or other conferences or journals, are not allowed"; "enforced during the whole reviewing process period." The abstract deadline (Sep 18) falls while the paper is under NeurIPS review (decision Sep 24) — ICLR is unavailable without a blind pre-decision withdrawal from NeurIPS, which is dominated by waiting 6 days. Consequences: the 6-week crunch relaxes to ~5.5 months; **N1 (domain transfer) is RESTORED to scope** (it was cut for time, and it is the strongest answer to 4jc8); E1 gets a realistic annotation timeline. The 6-week structure below is retained as the internal cadence for the same work, minus deadline panic; Sep 24 remains the fork (accept → camera-ready, reject → ICML).

**Gate 1 DIAGNOSED — this is a live-paper issue TODAY, not a Week-1 framing question.** Root cause of the 87.0-vs-84.3 gap found (2026-08-05, see `live_updates.md`): the current pipeline logs `spr_round_N` stages whenever SPR executes; **zero of the 864 IS rows in the released 16-cell artifacts contain any SPR stage**, and they pool to 84.26% — exactly the paper's *no-SPR ablation* number. The released artifacts are single-round runs; the 87.0% SPR-enabled runs are not in the repo. This does not prove 87.0 wrong — it proves the release cannot support it, while the posted rebuttals both cite "87.0 → 84.3 when SPR is disabled" and state "all data, code, and per-example artifacts are released." Anyone who aggregates the release before Sep 24 obtains the ablation number labeled as the full method.

**Gate-1 diagnostic #0 — RUN 2026-08-05, result: STALE-ARTIFACT problem, not live-pipeline.** Response-period artifacts DO contain `spr_round` stages (Experiment A, Amazon stress test, Recipes IS files) and PersonalWAB's 567 IS rows show `rounds_used {1: 558, 2: 6, 3: 3}` — SPR fires in the current pipeline (the 1.04 mean rounds reported to reviewers is real). So the response-period results (PersonalWAB 98.0, multi-fault, Iter-VRP control) are now *verified* SPR-enabled, not merely asserted. Only the 16-cell `outputs/real/` matrix is the no-SPR configuration.

**Gate-1 actions, in order:**
1. **Rerun the 16-cell matrix with SPR enabled (~$1–2, ≤1 day) — the definitive resolver, in parallel with asking the lab.** 864 rows × ~5k tokens at measured rates; first-pass completions largely cache-hit against `cache/completions.sqlite` (identical prompts), so real marginal cost is likely cents — SPR-round completions are the only new tokens. Blocked solely on the OpenRouter cap being raised. Outcomes: **~87%** → SPR works as claimed, committed artifacts are stale, regenerate the release, done; **~84%** → Table 10's SPR claim doesn't hold at this scale, and we know it in a day rather than after acceptance.
2. **Ask Mahfuza/the lab today where the SPR-enabled run outputs are** (free, parallel). If found: verify they aggregate to 87.0 → complete the release.
3. **Decide on the AC note only after #1's number is in.** Rerun ≈87 → release regeneration is the whole fix, no note needed. Rerun ≈84 → short, factual, author-initiated note to the AC before Sep 24 (corrected pooled numbers; response-period results unaffected — verified SPR-enabled per diagnostic #0). Self-initiated it's an erratum; discovered by someone else after acceptance it isn't.
- **Do nothing** remains the one option with unbounded downside; not recommended in any branch.

---

## 0. The controlling dates (verified 2026-08-05)

| Event | Date |
|---|---|
| ICLR 2027 abstract deadline | **Sep 18, 2026 AoE** |
| NeurIPS 2026 author notification | **Sep 24, 2026 AoE** |
| ICLR 2027 full paper deadline | **Sep 25, 2026 AoE** |

Consequence: the paper must be **finished by Sep 20**, then Sep 24 is a decision gate, not a work gate:
- NeurIPS **accept** → this program's outputs become the camera-ready + extra content page (see `camera_ready_extra_page_plan.md`); most items below are already promised there.
- NeurIPS **reject** → submit to ICLR Sep 25. A rejected paper is no longer under review, so the full-paper submission is clean.

~~**Gate 0 / Gate 1 (original Week-1 formulations)**~~ **SUPERSEDED 2026-08-05 — both gates are resolved; the STATUS UPDATE at the top of this file is authoritative.** (Gate 0: ICLR unavailable, target is ICML 2027 / camera-ready. Gate 1: root cause diagnosed as stale no-SPR artifacts in `outputs/real/`; action list in the status update.) The still-valid content from the original Gate-1 paragraph — the submission-framing consequence — is: whatever the SPR rerun yields, the next submission reports artifact-regenerable numbers throughout, and its headline is the strong reproducible results (multi-fault p<0.0001, PersonalWAB, the validated envelope), with the E1 dataset as the second headline contribution.

## 1. Scope triage

| Item | Verdict | Rationale |
|---|---|---|
| E1 human-annotated fault dataset | **DO — centerpiece** | Kills the evidence objection AND the novelty objection ("first released X"). Wall-clock critical path (humans). |
| E5 statistical hygiene | **DO — non-negotiable** | Every PAT-flagged arithmetic error fixed at source; CIs throughout; pre-registered analysis doc. $0, pure compute. |
| E3 profile-node ablation under noise | **DO** | Mahh named it; cheap; already promised. |
| E2 oracle localization gap | **DO** | Cheap; settles the "100% repair-stage" claim properly (measure all 16 cells or scope the sentence). |
| E6 extractor P/R on real traces | **DO** | Free rider on E1's annotation pass. |
| N4 envelope → named finding | **DO** | Pure writing + already-run validation (TravelPlanner fell on the predicted side). |
| E4 τ-bench/τ²-bench | **DO, gated** | Native user-conditioning benchmark; kills "you manufactured the failure mode" permanently. Week-1 feasibility gate first (Persona2Web NO-GO precedent: license, offline-runnable, no live web). τ-bench is MIT-licensed with simulated users — expected GO, verify. |
| N3 calibrate A(v) | **DO** | Reliability diagrams largely computable from existing per-example artifacts; cheap technical contribution. |
| E7 one frontier model | **DO, scoped** | One model, subset of conditions (multi-fault N=2–4 + PersonalWAB). Either outcome is a result. |
| N5 modern baselines | **PARTIAL** | RAFFLES-style localization baseline comes free as an E1 floor — promote it to a paper baseline. PRM baseline only if Week-3 capacity allows. |
| N2 anchor-condition theorem | **TIMEBOX** | One week (W4), proposition + proof sketch under (≥1 clean anchor, ε-accurate extraction). If it doesn't close, ship as formal conjecture + empirical validation; full theorem is ICML/journal work. |
| N1 domain transfer (code agents / RAG) | **RESTORED (2026-08-05, ICML timeline)** | Was cut for the 6-week ICLR crunch; with ICML 2027 as target it's back in scope. Strongest answer to 4jc8's novelty objection: same Eq. 1–5 loop on a structurally different substrate (code-agent fault localization or multi-hop RAG). Scheduled after the E-series completes (phases P4+). |

## 2. Phase-by-phase (re-baselined 2026-08-05)

Originally calendar weeks W1–W6 targeting ICLR. With the ICML pivot, "W*n*" labels below mean **phases in sequence (P1–P6), not calendar weeks** — the ordering, dependencies, and per-phase content are unchanged; the calendar re-anchors at the Sep 24 fork (accept → phases compress into the camera-ready window; reject → phases spread comfortably toward ICML's ~late-Jan abstract deadline, with N1 slotted after P4). P1 remains "immediately," and Gate-1 action #1 (the SPR rerun) precedes everything.

**W1 = P1 (start now) — cost-engineering: Gate-1 rerun + free-data harvest + annotation setup**
W1's job under the $50 cap is to convert every possible cost into $0 before anything is launched:
- **Free-data harvest (new, $0, high yield):** aggregate the 18 existing DeepSeek-V3 / Gemini-2.5-Flash / gpt-oss-20b cells + DeepSeek-V3.1 profile cells into the E7 scale analysis — this may close E7 outright before a single new token is bought.
- **Cache-mining audit ($0):** for E2 and E3, dry-run against `cache/completions.sqlite` and report projected cache-hit rate + real $ cost per experiment before launch; no run starts without a printed projection under budget.
- **Free-tier validation ($0):** test Gemini AI Studio free quota and OpenRouter `:free` variants for stability/rate limits; decide where they're usable (pilots/smoke) vs banned (paper cells) — separate, labeled cells only.
- Gate 0 (ICLR policy), Gate 1 (numbers provenance — Jihan decision), set OpenRouter cap to +$50 exactly (guardrail).
- E5a: rebuild every table from artifacts; discrepancy register; CI machinery (extend `regen_pvalue_tables.py`); freeze the pre-registered analysis plan before any new run.
- E3: implement candidate-generation change (admit profile nodes); launch only after cache audit; 2 cells, IS arm only (~$3).
- E1a: annotation guide + taxonomy v2; blinding pipeline; pilot 20 traces × 2 authors; **recruit volunteer third annotator today** (colleague/labmate outside the author list — longest lead item, now $0).
- E4 gate: τ-bench feasibility (license, offline harness, adapter scope) + hard cost projection at 2 models × 4 arms × 60 tasks; GO only if ≤$15.

**W2 (Aug 12–18) — main batches start**
- E1b: pilot agreement (Krippendorff's α), refine guide, start main batch — target ~200 failing trajectories pooled across methods from PersonalWAB + TravelPlanner-native (both un-injected/real-field).
- E2: oracle-localization harness (feed ground-truth fault to repair stage), run across all 16 cells' failure sets (~$10–20).
- E4 build: adapter following `travelplanner_real.py` pattern; smoke test.
- E7: select frontier model, pilot one cell, project cost before scaling.

**W3 (Aug 19–25) — compute peak**
- E1c: annotation continues (annotators), authors hands-off except adjudication queue.
- E4: full runs — 5 arms (Direct / Reflexion / VRP / Iter-VRP / IS) × 3–4 models (~$40–80).
- E7: full scoped condition set (~$50–150 depending on model pricing).
- N3: calibration analysis + reliability diagrams from per-example artifacts.
- N5: RAFFLES-style baseline implementation (doubles as E1 floor). PRM go/no-go by capacity.

**W4 (Aug 26–Sep 1) — analysis + theory timebox**
- E1d: adjudication, final α, attribution accuracy vs floors (random-ancestor, most-recent-step, RAFFLES) + MRR; annotate IS's own failures → empirical §4.5 taxonomy. E6: extractor node/edge P/R on the same traces.
- E2 analysis → rewrite the repair-stage claim with measured scope.
- N2 timebox: proposition + proof sketch. Hard stop Sep 1.
- Dataset release packaging: datasheet, license (CC BY 4.0), annotator instructions, per-trace JSON.

**W5 (Sep 2–8) — the rewrite**
- Full paper rewrite per §4 below. All numbers frozen from the audit trail (tag → artifact → command), zero exceptions.
- Figure 1 redrawn (solid dependency edges / dashed attribution arrows / legend).

**W6 (Sep 9–15) — audit + red-team**
- Number-by-number audit against artifacts; `wc`-level checklist; anonymization; reproducibility package.
- Adversarial review pass (agents prompted as Mahh-type and 4jc8-type reviewers); fix what they find.
- ~~Sep 16–18: submit ICLR abstract~~ **SUPERSEDED — Gate 0 failed; no ICLR submission.** **Sep 24:** NeurIPS decision → accept: camera-ready branch (§6) · reject: continue phases toward ICML 2027 abstract (~late Jan), N1 enters scope.

## 3. Cost & preparation — REVISED 2026-08-05: hard cap $50 total new spend (user directive)

Structural moves that make $50 feasible:
1. **E7 is already ~free.** `outputs/real/` contains 18 un-aggregated cells on DeepSeek-V3 (671B), Gemini 2.5 Flash, and gpt-oss-20b across 7 datasets, plus DeepSeek-V3.1 profile cells in ACHIEVEMENTS.md. Aggregating these answers "does it hold beyond 70B?" at $0. Only the multi-fault-at-frontier-scale gap needs new tokens.
2. **External annotator, PRIMARY (design updated 2026-08-05 — see E1 in §6).** One annotator outside the author list — unpaid colleague if the $50 cap is strictly all-in, paid if the cap covers API only — serves as the *primary* labeler; authors are secondary; author-vs-external agreement reported separately as the independence evidence. Fallback: 2-author + disclosed limitation. n=120–200 as recruitment allows (±9pp at n=120 supports "beats the floors" only; no per-condition claims lean on it).
3. **Cache mining before any run.** `cache/completions.sqlite` (+ PersonalWAB caches) make identical-prompt reruns free; E2's oracle-repair calls partially overlap trials already executed. Every experiment scripts a cache-hit dry-run first and reports projected $ before launching.
4. **Free tiers as overflow**: Gemini AI Studio free quota (gemini-2.5-flash already a campaign model), OpenRouter `:free` variants, Groq free tier; local Ollama for 7–8B smoke tests. Free-tier cells kept separate and labeled (different serving ≠ same cell), used for pilots/smoke only unless quota proves stable.

**REVISED AGAIN 2026-08-05 (grounded in measured token economics):** `orchestration/token_cost_summary.md` records the ENTIRE rebuttal campaign — 10.69M tokens including the full 1,620-row multi-fault real sweep — at **~$1.60 actual spend** (measured, confirmed exact from raw JSONL). At the campaign's measured blended rate (~$0.15/M for mistral-nemo/qwen-7b/llama-8b tier), $50 ≈ 330M tokens. Measured per-row volumes (`outputs/real/tables/token_cost.csv`): Direct ~2.1–2.2k, IS ~4.9–5.1k, Reflexion ~3.5–7.4k tokens/row. The full original program needs <10k new rows ≈ well under 100M tokens. Conclusion: **$50 covers the FULL program (E4 at full scope, PRM restored) with ≥3× margin.** The earlier "slimmed" table was based on unverified guesses; this one is arithmetic on measured data.

| Line | Volume math (rows × tokens/row, from measured data) | Projected $ |
|---|---|---|
| E3 profile-node ablation (4 A-cells, ρ=0.1/0.3, IS arm) | ~290 rows × 3k (Expt A measured 841k tokens for 279 rows) | $0.15 |
| E2 oracle-gap (all 16 cells' IS failures, cache-first) | ~500 failing rows × 3k repair+verify | $0.50 |
| E4 τ-bench FULL (3 models × 5 arms × 100 tasks) | 1,500 runs × ~30k (multi-turn; verify in W1 pilot) | $7.00 |
| E7 frontier top-up (DeepSeek-V3, multi-fault N=2–4, 2 datasets × 3 arms) | ~1,100 rows × 6k at ~$0.50/M (DeepSeek pricing, verify live) | $3.30 |
| N5 RAFFLES floor + **PRM baseline (restored)** | ~120 traces × 2 calls + PRM scoring pass on 4 cells | $2.50 |
| E1 blinding-pipeline sanity + misc | small | $0.50 |
| E5 / E6 / N2 / N3 / N4 / free-data harvest | local compute + existing artifacts | $0.00 |
| **Projected subtotal** | | **~$14** |
| Reserve (unspent unless a projection is approved against it) | | ~$36 |
| **Hard cap (OpenRouter key limit)** | | **$50.00** |

Only remaining real-money tradeoff vs the original $700 plan: E1 uses a volunteer third annotator instead of paid (n=120–200 as recruitment allows). Everything else is at full original scope.

Prep checklist (Week 1): set OpenRouter cap to exactly +$50 (the physical guardrail) · verify live per-token prices for every model used (projections above assume $0.15/M cheap tier, $0.50/M DeepSeek — trust only after checking the provider pages) · verify ICLR dual-submission text (Gate 0) · Gate 1 decision · recruit volunteer annotator · τ-bench W1 pilot to measure real tokens/task before the full launch · freeze pre-registration doc.

## 4. Exact paper delta (submitted NeurIPS version → ICLR version)

1. **Title/abstract:** reframed around three contributions — (i) the construction transferring classical abductive diagnosis to LLM trajectories by synthesizing the execution spectrum (the 4jc8-rebuttal wording, now the actual §1 text); (ii) the first released human-annotated root-cause dataset for agent-trajectory failures + measured attribution accuracy against it; (iii) the validated operating envelope (anchor condition) as a finding.
2. **§1 contributions** rewritten to those three + comprehensive evaluation bullet (multi-fault, real-user profiles, native-conditioning benchmark).
3. **§2:** multi-violation procedure promoted from Appendix A; formal definition of the task-success evaluator S (and the inference-time proxy — resolves PAT's data-leak question); edge-confidence definition; explicit candidate set C in Eq. 4's denominator; defined normalizers in Eq. 5; Algorithm 1 caching note (resolves re-execution redundancy); Figure 2 relabeled to match single-node semantics or the joint-repair mechanism specified.
4. **§4 restructure:** headline = multi-fault sweep (§4.x, full N=2–5 tables) + PersonalWAB (§4.x) + **E1 attribution-vs-human-labels (new centerpiece section, with floors and MRR)** + E2 oracle gap + E4 τ-bench + N3 calibration. Single-fault 16-cell matrix reported honestly from artifacts as parity-at-matched-cost context (Gate 1). Iter-VRP in the main baseline table; RAFFLES added (N5).
5. **§4.5 taxonomy:** rebuilt from E1's annotated IS failures (empirical, all-cells or explicitly scoped) — replaces the asserted four-cell 100% claim, cross-checked by E2.
6. **§5 related work:** the SE/fault-tolerance subsection from the 4jc8 rebuttal (Reiter, de Kleer & Williams, Tarantula/Ochiai/Wong, delta debugging, slicing, Halpern–Pearl, network fault localization) + the assumes/lacks/replacement table + PAT's LLM-side citations (Graph-of-Thoughts, Self-Contrast, RAFFLES-adjacent failure-attribution work).
7. **§6:** operating envelope moves OUT of limitations into a named finding section (N4), stated as a falsifiable scope claim with the TravelPlanner-native confirmation; E3 result lands here; N2 proposition (or conjecture) alongside; hyperparameter-ablation sentence corrected (PAT).
8. **Appendices:** corrected p-value tables with CIs and the pre-registered Direct comparison family (fixes impossible p-values); MuSiQue added to token-cost + p-value tables; oracle-ensemble arithmetic recomputed; seed-protocol contradiction resolved; TravelPlanner win/loss sentence fixed; dataset datasheet; all PAT typos.
9. **Statement of changes** (internal): every delta traceable to a reviewer sentence or PAT finding — the NeurIPS discussion record becomes the ICLR paper's silent audit trail.

## 5. Risks

- **Annotator recruitment slips** → E1 shrinks to 2 authors + adjudication with disclosed limitation; the dataset release still stands. Mitigate: recruit in W1.
- **τ-bench NO-GO** → fall back to τ²-bench or WorkBench-class native-policy benchmark; if none pass the gate, E4 is dropped and PersonalWAB carries the native-conditioning argument (it already did in rebuttal).
- **Gate 1 fallout** — artifact-derived single-fault numbers weaken the old headline → absorbed by the restructure in §4; the new headline results are the reproducible ones.
- **E7 shows the effect shrinking at frontier scale** → reported as a regime statement; consistent with the paper's existing mid-tier framing, not fatal.
- **NeurIPS accepts on Sep 24** → best-case "risk": the same program ships as camera-ready; only Gate-1 handling differs (camera-ready corrections coordinated with the lab).

## 6. Per-item execution detail (with anti-error protocol)

Every item below states: procedure → volume math → output artifact → verification step → stop rule. No run launches without its projection printed and under the remaining ledger.

**E1 — human-annotated fault dataset ($0 API + external annotator) — REDESIGNED 2026-08-05 for independence.**
The point of E1 is *independent* evaluation (Mahh's exact objection). Authors labeling their own system's failures — even blinded — invites "the authors labeled their own system" verbatim in a review. Design changes:
- **The external annotator is PRIMARY, not third.** Their labels are the reference; authors are secondary annotators.
- **Report author-vs-external agreement separately** from pooled α. High agreement = the independence evidence itself; low agreement = we find out before it's a headline contribution, not after.
- With the ICML timeline, the annotator can be **paid** (still within reach: annotation is human-cost, and the ICML window allows spreading it; if the $50 cap is strictly all-in including humans, recruit an unpaid colleague but keep the primary/secondary design — the design, not the payment, is what buys independence).
- n=120 at ±9pp supports "beats the floors" and nothing finer — **no per-condition claim may lean on E1's n**; per-condition slices are exploratory-labeled.
Procedure: (1) sample failing trajectories from `outputs/rebuttal/experiment_personalwab/` + TravelPlanner-native, pooled across arms, deterministic seed; (2) blinding script strips method identity/arm names/repair artifacts; (3) taxonomy v2 = 5 categories + "no identifiable fault", guide with 10 worked examples; (4) pilot 20 traces, all annotators → α; (5) main batch; (6) adjudication (external annotator's label prevails on unresolved ties); (7) attribution accuracy vs floors (random-ancestor, most-recent-step, RAFFLES) + MRR; (8) IS's own failures → empirical §4.5 taxonomy.
Verify: α ≥ 0.6 on pilot before main batch; accuracy CIs exact binomial. **Stop rule moved up: no external annotator committed by end of W1 → escalate to Jihan immediately** (recruitment is the schedule's most optimistic assumption; don't discover it failed in W3).
Output: `outputs/iclr/e1_dataset/` + datasheet + `e1_attribution_accuracy.csv` + author-vs-external agreement table.

**E2 — oracle localization gap (~$0.50).**
Procedure: for every IS failure in the 16-cell matrix, re-run ONLY the repair stage with the injected ground-truth fault node supplied as the selected candidate (injection metadata already in per-example JSONL). Gap = oracle success − actual success, per cell. Settles the "100% repair-stage" scope question with a measurement across all cells.
Volume: ~500 failures × ~3k tokens (repair + verify only; attribution skipped). Cache dry-run first — many repair completions for correct candidates already exist from the original counterfactual trials.
Verify: oracle arm must weakly dominate actual arm per cell (sanity bound — if any cell violates it, there's a harness bug; stop and diagnose before using any E2 number).
Output: `outputs/iclr/e2_oracle_gap/` + one table.

**E3 — profile-node candidate set under noise (~$0.15).**
Procedure: one flagged code path in candidate generation (`--admit-profile-nodes`) — additive flag, default off, main method untouched. Rerun Experiment A cells (TruthQA×Mistral/Qwen, ρ=0.1/0.3) IS arm; measure how often a profile node is selected and effect on success/misattribution.
Volume: ~290 rows × 3k ≈ 0.9M tokens (Experiment A measured 841k for 279 rows — same order).
Verify: paired vs existing Experiment A IS arm (same example IDs, seeds); McNemar per pre-registered plan.
Output: `outputs/iclr/e3_profile_candidates/`.

**E4 — τ-bench at full scope (~$7.00, the one item with real uncertainty).**
Procedure: W1 gate (license = MIT, offline user-simulator, no live web) → adapter following `travelplanner_real.py` pattern, native policy-violation criterion as the failure signal (the benchmark's own, not ours) → W2 pilot: 10 tasks × 1 arm × 1 model to MEASURE tokens/task → recompute projection → full launch only if ≤ $10: 100 tasks × 5 arms × 3 models.
Volume assumption to verify in pilot: ~30k tokens/task (multi-turn + user sim). If measured >60k/task, scope to 60 tasks × 5 arms × 3 models (~$8) — scope shrinks to fit budget, budget never grows to fit scope.
Verify: reproduce the benchmark's published Direct/baseline number for one model within noise before trusting the adapter.
Output: `outputs/iclr/e4_taubench/`.

**E5 — statistical hygiene ($0, W1, blocks everything downstream).**
Procedure: rebuild every table from raw JSONL via extended `aggregate_real_benchmarks.py` + `regen_pvalue_tables.py`; add 95% paired-bootstrap CIs everywhere; fix each PAT item at source (oracle-ensemble arithmetic, impossible p-values, MuSiQue omissions, TravelPlanner win/loss sentence, seed-protocol contradiction, ablation-cell characterization); write `analysis_preregistration.md` (families, corrections, one-sided/two-sided) BEFORE any new run; sanity-bounds checker runs in CI over every emitted table (|Δ|≥25pp with p=1.0 → hard fail).
Output: `outputs/iclr/tables/` + discrepancy register.

**E6 — extractor validation on real traces ($0).** Rider on E1: annotators mark whether extracted nodes/edges are faithful to the trace → node/edge P/R on real data next to the synthetic Appendix E numbers.

**E7 — frontier scale ($0 harvest + ~$3.30 top-up).**
Procedure: (1) aggregate the 18 existing DeepSeek-V3 / Gemini-2.5-Flash / gpt-oss-20b cells + DeepSeek-V3.1 profile cells — never in the paper, zero cost; (2) top-up: multi-fault N=2–4 on 2 datasets × 3 arms (Direct/Reflexion/IS) × 60 examples on DeepSeek-V3.
Volume: ~1,080 rows × 6k ≈ 6.5M tokens at ~$0.50/M (verify DeepSeek price live).
Verify: harvest cells pass the same n≥5 and error-rate guards as the main aggregation.
Output: scale-regime table + either "holds at 671B" or a stated regime boundary — both are results.

**N2 — anchor proposition ($0, timeboxed W4).** Formalize: ≥1 uncorrupted anchor + ε-faithful extraction ⇒ attribution identifies a true fault with probability bounded by f(prior mass, trial count M, anchor coverage). One week hard stop; ships as proposition + proof sketch or as formal conjecture + the E-series empirical validation.

**N3 — calibration of A(v) ($0).** Reliability diagrams + ECE from existing per-example artifacts (A(v) scores logged); if uncalibrated, apply temperature scaling on a dev split — that itself is the contribution ("calibrating repair-trial posteriors").

**N4 — envelope as finding ($0).** Writing: named §6 subsection, falsifiable statement, TravelPlanner-native as the confirmed out-of-envelope prediction, E3/E7 results slotted in.

**N5 — RAFFLES floor + PRM baseline (~$2.50 tokens; real cost is implementation TIME).** RAFFLES-style judge on E1's traces (doubles as floor and paper baseline). PRM: score IS's candidate rankings vs a process-reward model's step-blame on the 4 ablation cells; report agreement + head-to-head localization. Honest scheduling note: PRM's binding cost is engineering days, not tokens, and it was slotted into W3 (the compute peak) — under the ICML timeline it moves to a quiet week; if the NeurIPS-accept branch compresses the schedule, PRM is the first deferral.

**Camera-ready branch, written out (NeurIPS accepts on Sep 24):**
- Gate-1 branch A (SPR artifacts exist and verify): complete the release, camera-ready keeps submitted headline numbers, this program's results fill the extra content page per `camera_ready_extra_page_plan.md`.
- Gate-1 branch B (they don't exist): the camera-ready **must** report artifact-derived numbers — pooled single-fault becomes parity-with-Reflexion, the SPR ablation claim is corrected or re-run fresh (a fresh SPR-enabled 16-cell rerun is ~864 rows × ~5k tokens ≈ $1–2 at campaign rates — cheap; run it and report whatever it produces), and the paper's center of gravity moves to the response-period results (multi-fault, PersonalWAB, envelope), which are unaffected because they were run fresh from the released code. Coordinated with Mahfuza/the lab, but the constraint is non-negotiable: no number ships that the released artifacts contradict.

## 7. Anti-error protocol ("not glitching")

1. **Physical guardrail:** OpenRouter key cap set to exactly $50. Overrun is impossible, not just monitored.
2. **Ledger:** `orchestration/budget_ledger.csv` — every runner appends (run_id, rows, tokens_in, tokens_out, price_used, $, cumulative). No estimates in the ledger, only measured post-run numbers.
3. **Projection gate:** every launch prints projected cost = rows × measured-tokens/row × live price, and aborts if projection > (remaining cap − $10 reserve). Single runs projecting > $8 need explicit user approval.
4. **Weekly reconciliation:** ledger total vs `GET https://openrouter.ai/api/v1/key` usage delta. Any divergence > 20% → freeze all launches, diagnose.
5. **Price verification W1:** the $0.15/M and $0.50/M assumptions are checked against live provider pages before any projection is trusted.
6. **Sanity-bounds checker on every table** (the PAT class of error): impossible p-value/Δ combinations hard-fail the aggregation.
7. **Number provenance:** every number destined for the paper gets a tag → artifact path → command entry (same discipline as the rebuttal's audit rule). No number enters the text without it.
8. **Milestone check:** if cumulative spend > $25 before end of W3 with E4/E7 incomplete → scope review before anything else launches.
