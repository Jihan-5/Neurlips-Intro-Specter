# Team instructions — ICLR 2027 push (for Jashkaran + his Claude Code sessions)

Read `orchestration/ICLR_2027_submission_plan.md` first (goal, dates, risk register). This file is your operating manual: what to run, how to verify it, and how to parallelize across multiple Claude Code terminals. Paste the relevant Track section directly into a Claude Code session as the task brief.

## 0. Setup (once)

1. Clone; `python3 -m venv .venv && .venv/bin/pip install -e .` (or use existing venv conventions — check `scripts/run_real_benchmarks.sh` header).
2. **API keys are NOT in the repo.** Get `OPENROUTER_API_KEY` and `TOGETHER_API_KEY` from Jihan privately; put them in `.env.local` at repo root (gitignored). NEVER commit keys.
3. Before any experiment wave, run the provider health probe (Track A step 1). Two providers have already drifted/died this month — do not skip.
4. HuggingFace datasets are cached locally on Jihan's machine; first runs on a fresh machine will download MuSiQue/2Wiki/LongMemEval/HotpotQA from HF.

## Ground rules (non-negotiable)

- **File ownership (UPDATED 2026-09-15):** experiment execution and results-section rewriting are now handed to Jashkaran — Tracks A, E, and F below are yours. The invariant that survives the handoff: **never type a number into the paper by hand** — every number must be produced by an aggregation script from committed artifacts, and the script invocation goes in the commit message. Prose/figures stay on `jashkaran/prose`; results/table work goes on a new branch `jashkaran/results`; Jihan merges both.
- Experiments write to `outputs/` (gitignored) and are RESUMABLE — rerunning the same command skips completed rows. Never delete a `.jsonl` unless instructed.
- Protocol constants: `--tau-abstain 0.0`, generation seed 0, benchmark seed 42 (matches clean runs). Qwen-2.5-7B is DEAD at every host — never launch it; llama-3.1-8b is the substitute (see plan "Infrastructure notes").
- Long runs: launch detached (`nohup ... & disown`), prefix `caffeinate -i` on macOS so sleep doesn't pause them.
- **Time estimates:** before starting each track, ask your Claude: "estimate wall-clock time and API cost for this track, then append the estimate to `orchestration/team_status.md`". If any single track estimates >6h, post it — we re-split the work.
- Status protocol: every session appends progress lines to `orchestration/team_status.md` (`[date] [track] [what ran] [rows/verification result] [next]`), commits, pushes. Pull before starting work.

---

## Track A — Run the remaining bootstrap cells (needs API keys; mechanical; one terminal)

Wave 1 (running on Jihan's machine): truthfulqa×llama-8b, truthfulqa×mistral, longmemeval×llama-8b.
**Your cells (wave 2, after Jihan tops up OpenRouter credit):**

```bash
set -a; source .env.local; set +a
for spec in "longmemeval_real mistral-nemo-12b" "musique_real llama-3.1-8b" "musique_real mistral-nemo-12b" "twowiki_real llama-3.1-8b" "twowiki_real mistral-nemo-12b" "hotpotqa_real llama-3.1-8b" "hotpotqa_real mistral-nemo-12b"; do
  ds=${spec% *}; m=${spec#* }
  caffeinate -i nohup python3 scripts/profile_bootstrap_study.py \
    --dataset $ds --model $m --n-variants 100 \
    --cache-path cache/bootstrap_${ds}_${m}.sqlite \
    > outputs/rebuttal/relaunch_logs/bootstrap_${ds}_${m}.log 2>&1 & disown
done
```

**Health probe first** (paste to your Claude): "Run a single `--smoke` bootstrap invocation for each (dataset, model) pair above; confirm rows written with non-empty final outputs, zero `[ERROR]` lines, and distinct profile hashes across variants. Only then launch the full wave."

**Verification loop (every ~30 min or via a Monitor):**
```bash
wc -l outputs/rebuttal/profile_bootstrap/*/variants.jsonl          # target: 18,000 rows per 60-task cell (60×100×3), 3,600 for hotpotqa/truthfulqa (12 tasks)
grep -c "\[ERROR\]" outputs/rebuttal/relaunch_logs/bootstrap_*.log  # should stay ~0; investigate any growth
python3 scripts/aggregate_profile_bootstrap.py                      # sanity: numbers move, no crashes
```
**Done =** every launched cell at full row count, error count explained (network blips get a resume pass: rerun the same command), aggregator output pasted into `team_status.md`.
**Do NOT interpret results** — the analysis is pre-registered in `orchestration/profile_robustness_prereg.md`; report numbers as-is.

## Track B — Prose & figures (no API needed; branch `jashkaran/prose`; parallel-safe with Track A)

Independent subtasks — one Claude Code terminal each if you want max parallelism:

**B1. Figure 1 redraw** (highest value): current figure's dependency edges and attribution arrows share one style and read as cycles (an on-record camera-ready promise). Redraw (TikZ preferred): solid = dependency edges, dashed = counterfactual attribution arrows, plus a legend. Panel content unchanged. Verify: compiles standalone; no visual cycles.

**B2. Motivating examples rewrite**: replace dietary-restriction/budget-hotel examples throughout intro + worked example. Running examples: (1) enterprise CRM copilot acting on a stale client record; (2) healthcare intake agent with an outdated medication/allergy list. Supporting one-liners: finance assistant with stale risk tolerance; coding agent conditioned on an outdated repo config. Keep every technical claim identical — only the scenario skin changes. Verify: grep for leftover "restaurant/hotel/dietary" references.

**B3. ICLR template migration**: port `paper_final.tex` to the ICLR 2027 style files on the branch; NeurIPS checklist appendix comes out; anonymization pass (no author names, no acknowledgments, no repo links that deanonymize). Verify: compiles; page count within limit; `grep -i "neurips\|mankani\|farooque\|jihan-5"` returns nothing in the body.

**B4. Related-work additions** (draft text only; cite keys must come from `rebuttal/reference_audit_results.md` — every citation VERIFIED, never from memory): classical diagnosis paragraph (Reiter 1987; de Kleer & Williams 1987; Tarantula/Ochiai SBFL; delta debugging; program slicing; Halpern–Pearl) + 2025–26 agent-fault papers (Who&When arXiv 2505.00212; AgentDebug arXiv 2509.25370; RAFFLES EACL 2026 by C. Zhu et al.). Hand the draft to Jihan for merge — do not merge into main yourself.

## Track C — PAT-report verification sweep (no API; read-only; parallel-safe with everything)

Paste to a Claude session: "Read `paper_final.tex` top to bottom against this checklist of previously-flagged issues; for each, report FIXED / STILL PRESENT / N-A with line numbers, into `orchestration/pat_sweep_results.md`: (1) oracle-ensemble disagreement arithmetic (§4.6-ish); (2) McNemar p-values incompatible with success gaps (App D tables); (3) MuSiQue missing from token-cost table and App D; (4) promised 95% CIs and Direct-baseline comparisons missing; (5) TravelPlanner 'zero wins' vs Appendix G contradiction; (6) 'four strongest-gain cells' mischaracterization; (7) §5 hyperparameter-ablation sentence vs Table 9; (8) seeds protocol contradiction (§3.4 three seeds vs table captions '1 seed'); (9) cost '21% cheaper' denominator error; (10) SelfCheckGPT missing from Fig 3; (11) Table 4 tie-bolding; (12) 'Tables 3–5' citation omitting Table 6; (13) missing spaces 'failure.We' / 'reasoning.In'; (14) undefined edge confidence for cycle removal; (15) Eq. 4 candidate-set denominator vs profile-node exclusion." Report only — fixes to numbers/tables belong to the automation session; typo/notation fixes go on `jashkaran/prose`.

## Track D — dissolved (2026-09-15)

Former automation-side work is reassigned to Jashkaran as Tracks E and F below.

## Track E — Finish ALL remaining experiments (Jashkaran; needs API keys)

Priority order. Same protocol constants and resume/verification discipline as Track A. Status of each goes in `team_status.md` after every session.

**E1. SPR-enabled 16-cell rerun — FINISH + AGGREGATE (highest priority; resolves the 87.0 vs 84.3 discrepancy).** State: ~640/648 rows done in `outputs/real/spr/`, but only truthfulqa/musique/longmemeval × {llama-3.1-8b, llama-3.3-70b, mistral-nemo-12b} exist on disk — **the three twowiki cells are missing or elsewhere**. Check `outputs/real/spr/_logs/` for the exact launch commands used, complete any missing cells/rows (resumable), then aggregate with `scripts/aggregate_real_benchmarks.py` pointed at `outputs/real/spr/`. Deliverable: pooled IS success with SPR on, per-cell table, posted verbatim to `team_status.md`. Do NOT reconcile it with the paper's 87.0 yourself — flag the number to Jihan; what the paper says depends on it (Gate 1 in the plan).

**E2. Track A wave 2 — the 7 remaining bootstrap cells** (command block in Track A above). ⚠️ Blocked on OpenRouter credit top-up (+$30, Jihan's action — ping him before launching). Note: `longmemeval_real × llama-3.1-8b` is STILL RUNNING on Jihan's machine (4,249/18,000 rows as of Sep 15) — do not duplicate that cell. When all cells are at full row count: `scripts/aggregate_profile_bootstrap.py`, then apply the pre-registered analysis in `orchestration/profile_robustness_prereg.md` exactly as frozen (worst-case decile + Hoeffding are already specced) — report, don't interpret.

**E3. Profile-node candidacy mechanism (camera-ready commitment #1; the paper's novelty lever).** Build: admit profile nodes to the SPR candidate set (currently excluded — see the candidate-set construction in `intro_specter/pipeline.py`), gated behind a flag (e.g. `--allow-profile-candidates`) so default behavior is unchanged. Run on the Experiment-A cells (`outputs/rebuttal/experiment_a/`, protocol in plan "Infrastructure notes": `--tau-abstain 0.0`, `--rho 0.0` clean-control arm). Measure: of the failures the diagnostic attributes to corrupted profile nodes, how many does the mechanism recover? Aggregate via a new `scripts/aggregate_profile_candidacy.py` modeled on `aggregate_experiment_a_diagnostic.py`. If this slips past Sep 20, tell Jihan — fallback is shipping diagnostic-only.

**E4. Stretch — organic contradiction rate on PersonalWAB.** One number: across PersonalWAB's 1,000 real users, what fraction have ≥1 profile-vs-behavior contradiction in their history (no LLM calls needed if detectable by rule; otherwise cheapest model). Pre-empts "you invented this problem." Only start after E1–E3 are launched/done.

## Track F — Rewrite results sections from the new artifacts (Jashkaran; branch `jashkaran/results`)

Every number script-generated; commit the aggregator invocation alongside. Order matters — F1 blocks on E1.

**F1. Table regeneration with new SPR numbers:** recomputed exact McNemar p-values (kills the currently-impossible ones), paired-bootstrap 95% CIs (promised in §3.4, never delivered), Direct column added to Appendix D, missing MuSiQue tables, cost-% arithmetic fix, SelfCheckGPT restored to Fig. 3, tie-bolding fix. Track C's sweep results (`orchestration/pat_sweep_results.md`, when done) is the checklist of what must change.

**F2. Bootstrap robustness section:** once E2 aggregates, write the profile-robustness results subsection strictly per the pre-registration — distribution of the effect across profile draws, worst-case decile, Hoeffding bound. No post-hoc analyses beyond the prereg without flagging them as exploratory.

**F3. Profile-fault subsection ("when the profile itself is at fault"):** write up E3's recovered-failure results as the new novelty subsection; wire it to the diagnostic numbers already in the paper (21% clean-task failure, 100% traceability) and to `tab:classical`.

**F4. Consistency sweep:** every prose number vs its generating table, across the whole paper. This is the Sep 21–24 finalization item — start it as soon as F1 lands.

---

## Suggested terminal layout (max parallelism, updated 2026-09-15)

- Terminal 1: E1 (SPR finish + aggregate) → then F1 (tables).
- Terminal 2: E3 (candidacy mechanism — the long pole; start immediately).
- Terminal 3: E2 (bootstrap wave 2, once credit lands) with a verification Monitor.
- Terminal 4: Track C sweep if not done → then F4.

B-track leftovers (uncited-bib prune incl. `steinder2004survey`, B4 related-work draft using audit Batch 5 keys) fit in any idle terminal. First message to every session: point it at this file + the plan, ask for a time estimate before it starts, log to `team_status.md` after.
