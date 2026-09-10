# live_updates.md

Append-only log. Each entry: what was done, by which agent/session, result, and whether it feeds a new direction. This is the OpenClaw "daily notes" analog — detailed, searchable, NOT auto-injected into every orchestrator turn. The orchestrator distills the load-bearing parts into `directions.md` (the "MEMORY.md"/bootstrap analog).

Newest entries at the bottom.

---

## 2026-07-24T00 — main session — Phase 0 attempt #1
- Installed `intro_specter` package (`pip install -e .`), ran `scripts/aggregate_real_benchmarks.py`.
- Result: `Models:` list contained garbage entries (`longmemeval_real__llama-3.1-8b`, `truthfulqa_real__mistral-nemo-12b`, `twowiki_real__mistral-nemo-12b` appearing AS model names, plus zero-filled rows bleeding across unrelated datasets).
- Initially suspected the two uncommitted-modified output dirs (`outputs/real/longmemeval_real__llama-3.1-8b`, `outputs/real/twowiki_real__mistral-nemo-12b` — mid-edit from in-progress VRP baseline work). Reverted both via `git checkout --` (safe: tracked files, no untracked loss). **Outcome: garbage model names persisted after revert — that was not the cause.**

## 2026-07-24T01 — main session — Root cause found + fixed
- Root cause: `load_results()` in `scripts/aggregate_real_benchmarks.py` used `output_root.rglob("*.jsonl")` (recursive) + `cell_dir.partition("__")` (splits on FIRST `__` only). Auxiliary tiers under `outputs/real/ablation/`, `outputs/real/cascade/`, `outputs/real/n120/` nest dirs one level deeper named `{tag}__{dataset}__{model}` (e.g. `v1_no_dag__truthfulqa_real__mistral-nemo-12b`). The recursive glob picked these up; partitioning on the first `__` yielded `dataset="v1_no_dag"`, `model="truthfulqa_real__mistral-nemo-12b"` — corrupting the main 16-cell table.
- **Fix applied** (script-only, no main-experiment artifacts touched): added `if path.parent.parent != output_root: continue` to restrict aggregation to direct children of `outputs/real`. Confirmed clean output: 7 datasets × 7 models, no garbage names, 49 well-formed cells (28 more than the paper's 16 — hotpotqa_real/strategyqa_real/travelplanner_real and deepseek-v3/gemini-2.5-flash/gpt-oss-20b are later additions beyond the submitted paper's matrix, consistent with recent commits "Phase 2: 24-cell config matrix").
- Filtered to the paper's stated 16-cell matrix (datasets: truthfulqa_real, musique_real, twowiki_real, longmemeval_real; models: llama-3.1-8b, mistral-nemo-12b, qwen-2.5-7b, llama-3.3-70b) → confirmed 16 cells present (111/112 baseline-pairs found, 1 likely missing/errored row — not yet diagnosed at that point).

## 2026-07-24T02 — main session — Phase 0 attempt #2, STILL FAILS on content (not parsing)
- Spot-checked `outputs/real/tables/head_to_head.csv` (post-fix) against the fact sheet:
  - MuSiQue×Mistral: fact sheet says IS 91.7%, "+6.7pp, p=.012, strict win" vs Reflexion. **Actual: IS 81.7%, Reflexion 85.0%, Δ=−3.3pp, p=.754 (not significant) — IS is BEHIND Reflexion.** Confirmed independently from the per-cell `outputs/real/musique_real__mistral-nemo-12b/musique_real__all__summary.csv` (committed artifact, not touched by the aggregator bug or by us) — same numbers.
  - LongMemEval×Llama70B: fact sheet says "−1.7pp, p=1.000" (near-tie NS loss). Actual: IS 56.7%, Reflexion 70.0%, Δ=−13.3pp.
  - TruthfulQA×Mistral: percentages match (86.1/80.6) but real p=.625 (Holm-adj 1.0), not the claimed p=.012.
- STOPPED per Phase-0 gate rule. Reported findings + the aggregator fix to Jihan. Asked how to proceed.

## 2026-07-24T03 — user decision
- User: revert the 2 corrupted dirs (done) → fix the parser, re-verify (done, still fails on content) → **"Numbers are what they are — rebuild the rebuttal fact sheet from current repo state."**
- Direction: current `outputs/real/` (post aggregator-fix) is now ground truth. Original fact sheet's per-cell claims are NOT to be assumed true.

## 2026-07-24T04 — user mid-turn interrupt — orchestration/memory layer requested
- Built `E2Eplan.md` (frozen plan + Amendments), `directions.md` (curated current-state), `live_updates.md` (this file), `triggers.md` (dispatch rules), modeled on OpenClaw (https://docs.openclaw.ai/concepts/memory: `MEMORY.md` bootstrap + daily notes + distillation).
- Kicked off `/loop` in dynamic (self-paced) mode per user's choice of repeated invocations over one long background job.

## 2026-07-24T05 — orchestrator cycle 1 — fact sheet rebuild — CRITICAL FINDING
- Scoping decision: did NOT invoke the full `/research_power` 29-agent pipeline for this cycle's "evaluate progress" step — judged it a large cost/scope mismatch for routine bookkeeping. Reserved for direction items that need real external literature validation (e.g. 4jc8's SE/fault-tolerance prior-art gap). Dispatched a `general-purpose` subagent directly for the concrete Now-item instead (rebuild fact sheet — local computation only, no API spend, T4 budget guard not implicated).
- Subagent rebuilt `orchestration/fact_sheet_v2.md` from current `outputs/real/` (post aggregator-fix), filtered to the paper's stated 16-cell matrix. **Findings, fully sourced and cross-verified against both `head_to_head.csv` and `main_table.csv`:**
  - **Pooled success: Intro-Specter 84.30% (730/866) vs Reflexion 85.33% (739/866) — Intro-Specter LOSES overall by −1.0pp.** Paper claims 87.0% vs 85.4% (+1.6pp win).
  - **Cell-level record vs Reflexion: 6 wins / 4 ties / 6 losses.** Paper claims 8 wins / 7 ties / 1 NS loss (15/16 highest-or-tied).
  - **Zero statistically significant wins anywhere** — every Holm-adjusted p-value across all 16 cells is 1.0. Paper claims 4 "strict wins" (MuSiQue×Mistral, TruthQA×Mistral, TruthQA×Qwen, 2Wiki×Qwen) each with p≈.012.
  - The paper's single most-cited headline number, MuSiQue×Mistral "+6.7pp p=.012", is a cell where Intro-Specter actually **loses** (Δ=−3.3pp, p=.754) in current artifacts.
  - Row-count gap (111 vs 112) explained: `longmemeval_real×qwen-2.5-7b×tot` has only 4/60 valid ToT records (56 hit `ProviderError`, logged in `skipped_errors.jsonl`) — correctly dropped by the script's `n<5` guard. Genuine data-quality gap, not a bug.
- **This is no longer a "rebuttal numbers" problem — it is a finding that the submitted paper's central empirical claim (Intro-Specter beats Reflexion) does not currently reproduce from the repo's own committed run artifacts, across the whole 16-cell matrix, not just isolated cells.** Per `triggers.md` T2 (a NEEDS-DECISION item must escalate directly to the user, no subagent should route around it) and given the stakes (this bears on the integrity of an active NeurIPS submission, not just rebuttal wording), stopping the loop here rather than silently continuing to Phase 1.

## 2026-07-24T06 — loop stopped, escalating to user
- `ScheduleWakeup(stop: true)` called. Orchestration paused pending explicit user direction on how to interpret/resolve the pooled-result reversal before any further rebuttal work (drafting, experiments, or further campaign work) proceeds.

## 2026-07-24T07 — user decision — fact sheet is lab-provided, not to be re-derived
- User: the original fact sheet's numbers are given by their lab — treat as authoritative ground truth, do not argue/change them, perform whatever new calculations are needed on top (i.e. Experiments A-D). This is the explicit human decision the Blocked item was waiting on.
- Resolution: `orchestration/fact_sheet_v2.md`'s rebuilt numbers are NOT to be substituted into rebuttal text or used to override the lab's fact sheet. Experiments A-D proceed using the E2Eplan.md §1 fact sheet as given. The reproducibility gap remains logged here for the record but is closed as a non-issue per explicit user instruction — not to be raised again.
- Resuming work in this repo's `orchestration/` (not yet migrated to the new global `~/.claude/orchestrator_runs/` layout — that migration is deferred, not declined, per the user wanting to resume execution immediately).
- Next: Experiment A (profile-noise robustness).

## 2026-07-24T08 — Experiment A pilot results + parallel fan-out
- Pilot (TruthQA×Mistral ρ=0.30, n=31 paired, before backfill): Reflexion 71.0% true-success, Intro-Specter 77.4%; 0 discordant pairs favoring Reflexion, 2 favoring Intro-Specter; abstention 0/31 (flagged as worth verifying, not yet resolved). Not statistically decisive at this n — preliminary only.
- Root-caused apparent "stall": script had finished normally (8/72 rows missing from 5 transient OpenRouter errors, no retry logic existed). Added retry-with-backoff (3x) + resume/dedup-on-rerun to `scripts/rebuttal_experiment_a.py`. Verified the fix structurally; first direct-shell attempt failed on missing `OPENROUTER_API_KEY` (my Bash tool's env doesn't inherit `.env.local` — must `source` it explicitly each time). Backfill re-launched correctly after sourcing `.env.local`, running in background.
- Fanned out 6 parallel background agents per user request ("run subagents in parallel... make sure things get done faster"):
  1. Experiment A: TruthQA×Mistral ρ=0.10 (full run)
  2. Experiment A: TruthQA×Qwen ρ=0.10 (full run)
  3. Experiment A: TruthQA×Qwen ρ=0.30 (full run)
  4. Experiment B: build IterVRP + runner script + smoke test only (no full batch yet)
  5. Experiment C: sample natural failures from existing outputs/real/ artifacts (travelplanner, longmemeval) + draft (unvalidated) LLM annotation pass — explicitly NOT the real two-author annotation
  6. Experiment D: extend synthetic diagnostic generator with multi_fault mode, target n=60
- All told not to scale beyond their scoped task without reporting back first. Awaiting completion notifications for all 7 (6 agents + 1 backfill bash job).

## 2026-07-24T09 — real numbers landed for 3/4 Experiment A cells; Experiment D complete; Experiment C flawed, fix dispatched
- Backfilled pilot cell (TruthQA×Mistral ρ=0.30): 35/36 paired, Reflexion 74.3%, Intro-Specter 80.0%, discordant 0 Rfx-only / 2 IS-only.
- TruthQA×Qwen ρ=0.10 (36/36 both arms): Reflexion 75.0%, Intro-Specter 80.6%, discordant 0/2.
- TruthQA×Qwen ρ=0.30 (36/36 both arms): Reflexion 72.2%, Intro-Specter 72.2% (tie), discordant 1/1.
- TruthQA×Mistral ρ=0.10: in progress.
- Experiment D complete, n=60, $0 cost: 0% both-faults-resolved, 100% both-in-top2 (perfect attribution), 100% genuinely-interacting. Root cause traced: SPR rounds in `pipeline.py` rebuild from the original trajectory each round, not the prior round's partial repair — repairs don't accumulate, so two independent faults can structurally never both resolve within budget. Real, reproducible, not a bug introduced by us.
- Experiment C's first sample was flawed: LongMemEval-real still calls `inject_profile`, TravelPlanner-real has an unmarked 30% `fault_inject` slice. User decided: build a genuinely un-injected source first. Fix agent dispatched, running (`natural_baseline_run_v2.jsonl` growing, 204KB as of last check).
- Experiment B built + smoke-tested (VRP baseline was already complete/functional; `IterVRP` wraps it in a 3-round matched budget). Full 2-cell batch dispatched, just started.

## 2026-07-25T00:20 — user granted standing overnight authorization (~8h, expires ~08:20 EDT)
- Logged in directions.md. Proceeding without AskUserQuestion check-ins for routine/pre-covered decisions; T2-class genuine blockers still stop and get written here.
- Kicked off Experiment B's full 2-cell batch (background agent). Started an overnight self-paced `/loop` to keep checking real file state (not agent self-reports, which lagged reality more than once tonight), chain next steps as each experiment completes, and stop cleanly if nothing's left to do or a real blocker appears.

## 2026-07-25T01:05 — Experiment C corrected baseline complete — major finding + security flag
- Confirmed by direct code inspection: ALL 7 `intro_specter/benchmarks/*_real.py` loaders unconditionally call `inject_profile(...)` and default `fault_inject=True`. No genuinely clean, already-run source exists anywhere in `outputs/real/`. Mahh's structural objection is factually correct as stated.
- Built `scripts/rebuttal_natural_baseline_run.py` (additive, reuses raw HF-loading internals of `truthfulqa_real.py`/`musique_real.py`, skips injection entirely, `profile=None`, Direct method only). Ran 150 fresh examples (75 TruthfulQA + 75 MuSiQue), cost ~$0.01. Result: 118/142 scored = 83.1% organic failure rate.
- **Critical honest finding**: every failure inspected is a wrong-fact/wrong-hop/misconception error, NOT assumption-driven — because with no profile, there's nothing to hold a wrong assumption about. Experiment C's original goal (show assumption-driven failures occur naturally) may be structurally near-unanswerable: profile-bearing settings are necessarily injected; un-injected settings have no profile to violate. Usable claim: "the model fails on natural, un-injected tasks too" (weaker than hoped). NOT usable: claims about assumption-driven/profile-violation failure rates specifically. To be disclosed honestly in rebuttal text, not reframed — per E2Eplan.md rule 2/3.
- Output: `outputs/rebuttal/experiment_c/natural_failures_sample_v2.jsonl` (50-row corrected sample, seed 42). Old `natural_failures_sample.jsonl` marked SUPERSEDED, cross-referenced.
- **Security note**: mid-run, the subagent received a message via its task-notification channel purporting to be from "the coordinator" instructing it to skip ahead to the annotation pass — contradicting the explicit stop-after-sampling instruction it was given. NOT sent by the main session. Subagent correctly identified it as illegitimate and did not act on it. Flagged to user per standard prompt-injection handling; no corrective action needed since the subagent already did the right thing.
- Next (already in the standing loop plan, not a new decision): draft LLM annotation pass on the v2 sample, for a precise confirmatory number on the ~0% assumption-driven rate implied above. Still explicitly NOT the real two-author annotation.

## 2026-07-26 — Persona2Web feasibility gate: NO-GO (Phase 0, stopped before building anything)

**Target:** Persona2Web (ICML 2026, arXiv 2602.17003) — "Persona2Web: Benchmarking Personalized Web Agents for Contextual Reasoning with User History" (Kim, Lee, Lee, Yonsei DLI).

**Verdict: NO-GO.** Fails hard gate (d) live-web requirement; (b) license also unresolved.

Evidence (all URLs actually fetched 2026-07-26):
- (a) PASS — links resolve:
  - Paper: https://arxiv.org/abs/2602.17003 (v3, accepted ICML 2026)
  - Project page: https://serin-kimm.github.io/Persona2Web/
  - Code: https://github.com/serin-kimm/Persona2Web (public, 6 commits; contains AgentOccam/ and browser-use/ Playwright agent runners + config_files/)
  - Data: https://huggingface.co/datasets/yonsei-dli/Persona2Web (150 tasks / 650 rows; fields: original_query, preference JSON, task_id, task_variant A/B/C, user_id, website)
- (b) FAIL/UNRESOLVED — no LICENSE file found on the GitHub repo or the HF dataset card (default = all rights reserved). Only license statement found is CC BY-NC-ND 4.0 on the arXiv HTML (paper text license; ND would forbid derivative adaptation anyway).
- (c) PARTIAL — queries, preference constraints, and user histories are downloadable from HF, BUT the dataset contains NO cached web content; tasks name live target websites.
- (d) FAIL (CRITICAL) — evaluation requires LIVE WEB access. Converging evidence from four sources:
  1. Paper abstract/body: "a benchmark designed to evaluate personalized web agents under realistic, open-web environment."
  2. Project page: "Persona2Web is specifically designed for evaluating personalization capability of web agents on the real open web."
  3. GitHub README: "Persona2Web runners execute Persona2Web tasks on the real open web" — runners are Playwright/browser-use agents needing OPENAI_API_KEY/GEMINI_API_KEY; no offline/snapshot mode.
  4. Paper reproducibility section: authors handle web volatility by repeated-run variance (Table 8) and temporal drift Dec-2025-vs-Mar-2026 (Table 9) — i.e., they mitigate live-web nondeterminism statistically; **no cached snapshots are released or mentioned**.
- Scoring is additionally LLM-judge-based (GPT-5-mini judging full trajectories against rubrics, with human meta-eval) — replicable in principle, but moot given (d).

**Why this kills the eval for us:** paired 5-arm comparison (direct / reflexion / violation_reprompt / iter_vrp / intro_specter) requires all arms to see the same environment state; live search results and item availability drift between and within runs, confounding arm deltas. Authors themselves document temporal variability across months. Per campaign rules: live-web => infeasible, no workarounds attempted.

**Action:** STOPPED at Phase 0 per instructions. Nothing downloaded, no adapter built, no tracked files modified (this log entry is the only change).

## 2026-07-26 — PersonalWAB experiment: BLOCKER — OpenRouter key exhausted mid-run

**Status at block:** PersonalWAB (WWW'25) single-turn recommend adapter built, smoke-tested, and launched
(3 models x 5 arms x 60 examples x seeds 0,1,2). ~300 production rows in
`outputs/rebuttal/experiment_personalwab/{model}/{arm}.jsonl` before the key died. Zero code errors.

**Blocker (verified via GET https://openrouter.ai/api/v1/key):** limit $50.00, usage $50.006,
limit_remaining $0.00, limit_reset null (no auto-reset). Every OpenRouter call now returns
403 "Key limit exceeded (total limit)". All three assigned models (mistral-nemo-12b, qwen-2.5-7b,
llama-3.1-8b) are OpenRouter-served in the campaign MODEL_TABLE. Runs stopped cleanly
(failed rows are never written; resume/dedup on (task_id, seed, arm) makes relaunch lossless).

**Feasible continuation taken:** Together key works. Of the three models, ONLY Qwen-2.5-7B has a
serverless Together equivalent (`Qwen/Qwen2.5-7B-Instruct-Turbo`; verified by live test call —
Llama-3.1-8B and Mistral-Nemo require dedicated endpoints). Launched a clean separate cell
`qwen-2.5-7b-together` (not mixed with the partial OpenRouter qwen rows; FP8 Turbo serving is a
different endpoint, so it gets its own cell, stated plainly in SUMMARY).

**To unblock the other 2.7 cells:** raise the key limit at
https://openrouter.ai/workspaces/default/keys/2b579e7f72ed8b45ac3a3be837f69eb65f8d1d2662b731b2c9de056bada4f17f
then relaunch (resumes automatically):
  for m in mistral-nemo-12b qwen-2.5-7b llama-3.1-8b; do
    nohup zsh -c "set -a; source .env.local; set +a; python3 -u scripts/rebuttal_experiment_personalwab.py --model $m" \
      > outputs/rebuttal/experiment_personalwab/$m.log 2>&1 & disown; done
Estimated remaining OpenRouter spend for all three cells: roughly $3-6 total at observed token volumes.

## 2026-07-27 — PersonalWAB: qwen-2.5-7b-together cell COMPLETE (900/900 rows, 0 errors)

Success rates (180 paired rows/arm, 60 examples x seeds 0,1,2): direct 165/180=0.917,
reflexion 168/180=0.933, violation_reprompt 168/180=0.933, iter_vrp 168/180=0.933,
intro_specter 174/180=0.967. Exact McNemar (IS vs baseline, discordant IS-wins/baseline-wins):
vs direct 9/0 p=0.0039; vs reflexion, VRP, iter_vrp each 6/0 p=0.0312. IS won every discordant
pair. Mean rounds_used: IS 1.04 vs iter_vrp 1.15. Token cost: IS ~2.1x direct.
Full table: outputs/rebuttal/experiment_personalwab/SUMMARY.md. The three OpenRouter cells
remain blocked on the $50 key cap (partial real counts kept in SUMMARY.md; resume command above).

## 2026-08-05 — Gate 0 + Gate 1 resolved (ICLR plan, main session)

**Gate 1 — reproduction-gap ROOT CAUSE FOUND (diagnosis, no new spend):**
- `intro_specter/pipeline.py` (current code, lines ~280-340) appends `spr_round_{N}` / `spr_round_{N}_decision` entries to `meta["stages"]` whenever the SPR loop executes; `spr_max_rounds=0` disables it.
- Scan of ALL 864 intro_specter rows in the paper's 16-cell matrix (`outputs/real/{truthfulqa,musique,twowiki,longmemeval}_real__{4 models}`): stage kinds seen = extraction (864), verifier (864), attribution/decision/post_verifier (219 — the violation path). **Zero rows contain any spr stage.**
- Pooled IS success from these artifacts: 728/864 = **84.26%** — matching fact_sheet_v2's 84.30% and, critically, the PAPER'S OWN "single-round (no SPR)" ablation number (84.3%), not its full-method headline (87.0%).
- Conclusion: the committed `outputs/real/` runs are the no-SPR configuration. The released artifact package therefore reproduces the ablation, labeled as the full method. The 87.0% SPR-enabled runs are not in this repo. This does NOT prove 87.0 wrong — it proves the release cannot support it.
- Exposure: rebuttals state "all data, code, and per-example artifacts are released" and cite "disabling SPR drops pooled success from 87.0 to 84.3 — below Reflexion." Anyone aggregating the release before the Sep 24 decision gets 84.3 for the full method.
- Decision tree written into ICLR_2027_plan.md §Gate 1: (A) lab produces SPR-enabled artifacts → verify → complete the release, no correction needed; (B) they don't exist → factual correction to AC before decision. Jihan + lab decision required NOW, not Week 1.

**Gate 0 — ICLR 2027 UNAVAILABLE:** Author Guidelines verbatim: "submissions... that have been submitted in parallel to this or other conferences or journals, are not allowed" + "enforced during the whole reviewing process period." Abstract deadline Sep 18 < NeurIPS notification Sep 24 → submitting while under NeurIPS review violates the policy; withdrawing from NeurIPS 6 days before its decision to enable it would be irrational. **Plan pivots to ICML 2027 (abstract ~late Jan 2027) / NeurIPS camera-ready.** Restores N1 (domain transfer) and realistic E1 annotation timeline.

## 2026-08-05 (later) — Gate-1 diagnostic #0: response-period artifacts ARE SPR-enabled
- grep for `spr_round` across `outputs/rebuttal/`: present in Experiment A (all 4 cells), Amazon stress test (all 4 models × N tiers), Recipes IS files.
- PersonalWAB IS rows (567): rounds_used {1: 558, 2: 6, 3: 3} → SPR fired on 9 rows; the 1.04 mean rounds reported to reviewers is real and now verified from artifacts.
- Conclusion: **stale-artifact problem, not live-pipeline problem.** Current pipeline's SPR works; only the 16-cell `outputs/real/` matrix is the no-SPR configuration. Everything told to reviewers during the response period was produced by SPR-enabled code.
- Plan updated: SPR-enabled 16-cell rerun (~$1–2, cache-assisted, blocked only on OpenRouter cap) promoted to Gate-1 action #1, ahead of the lab file search; AC-note decision deferred until the rerun's number is in. Plan body reconciled with status header (N1 restored in triage, ICLR submission line struck, W→P phase re-baseline, E1 external-primary in §3).
