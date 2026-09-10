# directions.md

Curated, current-state bootstrap file (OpenClaw `MEMORY.md` analog). Read in full by the orchestrator and every subagent at the start of each cycle. Kept small — detail lives in `live_updates.md`; this file only holds what's true *right now* and what to do about it. The orchestrator rewrites this file each wake-up; it does not accumulate history (that's `live_updates.md`'s job).

---

## Standing authorization update (2026-07-25T13:xx) — open-ended, supersedes the 8h expiry below
- User: "u have full access to monitor and assume yes from my side for everything." Interpretation: same as the overnight authorization but no longer time-boxed — proceed through routine/execution decisions without check-ins, indefinitely, until user says otherwise.
- Restated explicitly (this does NOT change, "assume yes" cannot waive it): rebuttal-usable evidence must come from the unmodified submitted method only; no fabricated/tuned results; no edits to paper_final.tex/paper_sections/ or any other tracked file the campaign depends on being unmodified; nothing posted/pushed externally without separate explicit approval. These are integrity/rule constraints, not permission questions.

## Standing overnight authorization (expires ~8h from 2026-07-25T00:20 EDT, i.e. ~08:20 EDT) — superseded by the open-ended version above
- User: "no like u dont ask me anything for the next 8 hours u have all access granted." Interpretation: proceed through routine decisions using this file's pre-committed decision rules and judgment WITHOUT AskUserQuestion check-ins, for the remainder of the currently-scoped campaign (Experiments A-D, drafting, coverage audit) within the existing $80 budget cap and existing constraints (no paper edits, no external posting, no destructive git ops).
- This does NOT relax triggers.md's T2 escalation conditions (contradiction with used data, evidence undercutting the plan's premise, budget/deadline breach) — those still stop and get written here, just not necessarily as a blocking question if the decision is already covered by a pre-committed rule (e.g. F-A1/F-B2/etc framings).
- This does NOT mean tool-permission prompts are disabled — that's a harness-level setting outside the assistant's control; if one appears, it will still block until the user (or their permission config) resolves it.
- If nothing has resumed this thread by ~08:20 EDT, treat the standing authorization as expired and resume normal check-in behavior.

## Budget
- Cap: ~$80 total new spend (OpenRouter + Together) for the rebuttal campaign, per E2Eplan.md rule 0.
- Spent so far: negligible (~4.2k tokens on the Experiment A smoke test; pilot run in progress).

## Deadline confirmed by user (2026-07-26): July 27 AoE, ~48h from now
- User's explicit target: have everything postable-ready by July 27 AoE (Anywhere-on-Earth, latest possible interpretation — effectively ~48h runway from now). This is tighter than the Aug 3 hard Phase-2 deadline but is the user's chosen target, not to be second-guessed.
- Implication: need to plan backward from this — experiments (currently running: TwoWiki near-done, HotpotQA/MuSiQue/LongMemEval + TravelPlanner-multi-fault all in progress) should have a soft internal cutoff leaving enough runway for strength-assessment synthesis + drafting + coverage matrix + numbers audit + user review, not just run until "done" with no time left for the rest.
- Original Phase 1 (Jul23-27)/Phase 2 (Jul27-Aug3)/Phase 3 (Aug3-10) structure below still applies for context on what Jul 27 actually gates (visibility, not a hard cutoff on the underlying NeurIPS process) — but the user's 48h target is now the operative constraint for this session's pacing.

## Deadlines (from official NeurIPS 2026 PC email, received 2026-07-24 — supersedes earlier "~4 days" estimate)
- **Phase 1 (author response only), Jul 23–27**: draft/post initial responses now; NOT visible to reviewers/AC until this phase ends. Target: have all 3-4 rebuttal texts postable by end of Jul 27.
- **Phase 2 (author/reviewer/AC discussion), Jul 27–Aug 3**: responses become visible; reviewers may ask follow-ups; keep responding.
- **Phase 3 (reviewer/AC only), Aug 3–10**: authors can no longer see or respond to continued discussion — everything postable must be posted before Aug 3.
- Hard rules reconfirmed: no paper/supplementary revisions during response period (matches E2Eplan.md rule 4 already); 10,000-char limit per review (matches rule 6); no links except an anonymized code link to the AC only if a reviewer explicitly asks for code (matches rule 5's exception); use OpenReview's per-review "Rebuttal" buttons.

## Ground truth status
- `outputs/real/` (post aggregator-fix, see live_updates.md 2026-07-24T01) is the authoritative source for all rebuttal numbers. The plan's original "fact sheet" (E2Eplan.md §1) is UNVERIFIED and its per-cell claims must be re-derived, not assumed — confirmed wrong on at least MuSiQue×Mistral and LongMemEval×Llama70B, and the TruthQA×Mistral p-value.
- Root cause of why paper-submitted numbers differ from current repo artifacts is still open. Not blocking — we're proceeding on "current repo state is ground truth" per user decision, but if a subagent finds the actual cause (e.g., a second copy of results elsewhere, a since-reverted commit, a different seed set used for the PDF), report it — it may change what's postable.

## Now
- (none — halted, see Blocked)

## Next: Experiment D extension — Reflexion comparison + fault-count sweep (2026-07-25T11:30, user-requested)
- User wants: (1) a real Reflexion-equivalent baseline comparison on the existing 2-fault graphs (dispatched, agent a887430a104199403 running — building a fair symbolic analog of real Reflexion's blind-full-regen-no-attribution behavior, matched 3-round budget, reusing the existing $0/synthetic execution model), (2) then generalize to 2/3/4/5 simultaneous faults, n=60 each, same IS-vs-Reflexion-equivalent comparison.
- Explicit honesty instruction given to the agent and holding for the follow-up: report the real result whatever it is, do not tune the Reflexion-equivalent to look artificially better or worse. Already-known root cause (SPR rounds don't accumulate repairs, fixed 3-round budget) predicts resolution rate should degrade further as fault count exceeds what 3 rounds can cover — that's a legitimate, precise, honest finding either way, not something to avoid finding.
- Sequencing: 3/4/5-fault sweep dispatches AFTER the 2-fault+Reflexion agent completes, reusing its exact Reflexion-equivalent mechanism (not a second implementation) to keep the comparison consistent across fault counts.

## Next: strength-assessment subagent (dispatch once A+B+C all complete — D already is)
- User request 2026-07-25T00:50: once all experiments are done, run a subagent that reads ALL real results (Experiment A's 4-cell paired stats, B's 2-cell paired stats, C's corrected natural-failure sample + draft annotations, D's completed multi-fault numbers) and produces an honest strength assessment PER REVIEWER — Mahh (3→4), 4jc8 (3→4), LDZz (confidence 3→4) — NOT the rebuttal text itself, a synthesis step before drafting.
- For each reviewer's specific objection (Mahh W1/W2/W3/Q1, LDZz's Fig1/multi-violation question — 4jc8's is mostly literature/framing, note separately whether any new data is even relevant to it), the subagent should: (a) determine which pre-committed decision-rule framing (F-A1/A2/A3, F-B1/B2/B3, C's assumption-driven-% framing, D's ≥80%-or-scoped-limitation framing) actually applies given the REAL numbers, (b) rate the resulting evidence strength honestly (strong/moderate/weak/doesn't-move-the-needle) — do not inflate, (c) flag anywhere the honest framing (per E2Eplan.md rule 2/3, never soften unflattering results) might not be enough to actually earn the score increase, so that's known before drafting starts, not discovered after.
- This becomes the input to the actual rebuttal-drafting phase (§5/§6 of E2Eplan.md) — do not let the loop skip straight from "experiments done" to "drafting text" without this synthesis step landing first and being logged in live_updates.md.

## Next (frozen until Blocked item is resolved)
- Investigate the PAT-flagged items that are cheap/local to check (no API spend): oracle-ensemble disagreement-rate arithmetic, TravelPlanner win/loss mischaracterization, seed-count contradiction, MuSiQue missing from token-cost/p-value tables — likely now secondary to the pooled-reversal finding but may share a root cause.
- Set up `rebuttal/` scaffold and re-plan Experiments A–D — cannot responsibly proceed until Blocked item is resolved, since the entire rebuttal strategy (defending an accuracy advantage over Reflexion) may not hold.

## Blocked
- (none — resolved 2026-07-24T09: user chose "find/build a genuinely un-injected data source first" for Experiment C, see Now)

## Full-matrix real results so far (2026-07-25T23:5x) — Intro-Specter top-or-tied at every N, 2 of 4 models confirmed
- Mistral-Nemo-12B (complete, 7 arms): Intro-Specter wins outright at N=2,3,4 (87.8/91.7/91.1 vs next-best 86.7/77.2/71.9) and is nominal top at N=5 (45.8 vs 45.0).
- Qwen-2.5-7B (complete, 7 arms): Intro-Specter wins outright at N=2,3,4 (83.3/80.0/80.6) and 3-way ties for top at N=5 (33.3%).
- Llama-3.3-70B (complete per subagent report): Intro-Specter top at every N including N=5 (96.5/83.3/82.6/43.7), only model where N=5 is an outright win not a tie.
- Llama-3.1-8B: in progress, ~81%.
- **Real, broad evidence now exists that this isn't a Reflexion-specific artifact** — holds against 6 baselines across (so far) 3 of 4 models.
- Non-synthetic TravelPlanner: found a real scoring bug (Intro-Specter's "no downstream steps to regenerate" case stores a placeholder string as final_output instead of the real answer, causing ~45% spurious extraction failures vs ~16% for Reflexion). Fix + re-score dispatched (agent ab8bd3d2ee04f9688), using already-collected data, minimal new API calls only for the ~57 affected rows if needed.

## Condition-1 finding + two new dataset builds (2026-07-26T00:5x)
- **Condition 1 (single-fault synthetic, from existing outputs/real/ data, zero new experiments): Reflexion (80.17%) actually beats Intro-Specter (77.85%) on grand average across 5 datasets × 4 models.** This is the OPPOSITE of the multi-fault pattern. Refined narrative: Intro-Specter's advantage is not universal, it specifically emerges under multi-fault conditions — a sharper, more defensible claim than "wins everywhere."
- User approved building 2 more genuine non-synthetic multi-fault datasets (beyond TravelPlanner): Food.com recipes (`AkashPS11/recipes_data_food.com`, MIT license, real prep-time/calorie/ingredient fields) and Amazon product data (`McAuley-Lab/Amazon-Reviews-2023`, real price/brand/category fields, sparser field completeness risk flagged). Both dispatched as new `_real.py` loader builds following `travelplanner_real.py`'s pattern.
- Also dispatched: TravelPlanner's missing Condition 2 (synthetic multi-fault on the templated profile layer, distinct from the already-running native-constraint experiment).

## MAJOR SCOPE EXPANSION (2026-07-25T18:xx) — full baseline×model multi-fault matrix, timeline reset
- User explicitly chose full scope after being shown the time cost: N=2 through N=5, all 6 baselines (Direct, Self-Refine, Reflexion, Full-Regen, ReAct, SelfCheckGPT — ToT excluded, justified by the paper's own token-cost/efficiency finding) × all 4 models (Mistral-Nemo-12B, Qwen-2.5-7B, Llama-3.1-8B via OpenRouter, Llama-3.3-70B via Together) = ~96 cells.
- **This abandons the earlier 3-4hr "reach drafting" target — explicitly acknowledged and chosen by the user.** New realistic estimate: several hours to overnight-scale given ~10-20x the volume of everything run tonight combined.
- Dispatched as 4 parallel model-specific agents (partition by model for provider/rate-limit cleanliness). Reusing existing `intro_specter/baselines/*` implementations for the 5 new baseline arms (Direct/SR/FR/ReAct/SChk already used in the main real benchmark, not new code) and existing injection modules (`double_fault_injection.py` for N=2-4, `hop_fault_injection.py` for N=5).
- Rebuttal-usable evidence only from unmodified methods (all of these ARE unmodified — no `intro_specter_fixed` arm in this expansion, per earlier finding that it made no difference on real data anyway).

## Scope decision (2026-07-25T18:xx) — fault-count sweep capped at N=5
- User: N=6 unnecessary, stop extending further. N=2-5 is the primary real-benchmark fault-count table for LDZz. N=6 data already collected/reported honestly is KEPT (not discarded — it's real data, no reason to hide a result already generated) but demoted to supplementary, not part of the primary narrative.
- Full real picture, for reference: N=2 tied (86.7/87.8, p=0.69); N=3 IS wins (77.2/91.7, p<0.0001); N=4 IS wins (70.6/91.1, p<0.0001); N=5 tied (45.0/45.8, p=1.00); [N=6 supplementary: 45.0/41.7, p=0.22, Reflexion nominally ahead].
- No further fault-count expansion work to be dispatched.

## Parallelization catch-up (2026-07-25T13:01) — user correctly flagged Mahh/4jc8 threads were neglected
- Experiment D's multi-fault thread (LDZz-focused) consumed most of tonight's attention following successive user-driven expansions (Reflexion comparison, cumulative-repair exploration, real double-injection, 2/3/4/5-fault sweep). Meanwhile: Experiment B died silently a SECOND time (found stuck at 37/37 for hours, no process running) and Experiment C's chained next-step (draft annotation on the corrected v2 sample) never actually got dispatched despite being in the loop's plan.
- Fixed: B resumed directly again (PID 2509, will need closer watching — this is its second silent death, worth investigating root cause once campaign work settles). C's draft-annotation-on-v2 dispatched. 4jc8's literature-grounding work (never started until now) dispatched via research_power in parallel with everything else.
- Going forward: actively check ALL four reviewer-facing threads (A done, B, C, D) each cycle, not just whichever one had the most recent user message about it.

## Now
- Experiment B full batch: 56/718 rows at ~24min elapsed (~2.3 rows/min) → ETA roughly 4.5-5h remaining for cell 1+2 combined at this pace. Error rate low or expected (isolated transient, retried). No action needed, just tracking pace so the loop knows this is the long pole tonight.
- Experiment A TruthQA×Mistral ρ=0.10: last checked 31/33 rows, nearly done.

## Next (after A)
- Experiment B (IterVRP matched-budget), then C (natural-fault annotation), then D (multi-fault stress test), per E2Eplan.md §3 priority order A>B>C>D.

## Done
- Fixed `scripts/aggregate_real_benchmarks.py` recursive-glob bug (auxiliary ablation/cascade/n120 tiers corrupting main aggregation).
- Reverted 2 uncommitted-modified output dirs to clean git state.
- Built this orchestration layer (`E2Eplan.md`, `directions.md`, `live_updates.md`, `triggers.md`).
- Rebuilt and fully sourced `orchestration/fact_sheet_v2.md` from current repo state — surfaced the pooled-reversal finding above.
