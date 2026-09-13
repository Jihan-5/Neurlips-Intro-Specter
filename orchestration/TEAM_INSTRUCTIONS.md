# Team instructions — ICLR 2027 push (for Jashkaran + his Claude Code sessions)

Read `orchestration/ICLR_2027_submission_plan.md` first (goal, dates, risk register). This file is your operating manual: what to run, how to verify it, and how to parallelize across multiple Claude Code terminals. Paste the relevant Track section directly into a Claude Code session as the task brief.

## 0. Setup (once)

1. Clone; `python3 -m venv .venv && .venv/bin/pip install -e .` (or use existing venv conventions — check `scripts/run_real_benchmarks.sh` header).
2. **API keys are NOT in the repo.** Get `OPENROUTER_API_KEY` and `TOGETHER_API_KEY` from Jihan privately; put them in `.env.local` at repo root (gitignored). NEVER commit keys.
3. Before any experiment wave, run the provider health probe (Track A step 1). Two providers have already drifted/died this month — do not skip.
4. HuggingFace datasets are cached locally on Jihan's machine; first runs on a fresh machine will download MuSiQue/2Wiki/LongMemEval/HotpotQA from HF.

## Ground rules (non-negotiable)

- **File ownership to avoid collisions:** the automation session (Jihan's Claude) owns `paper_final.tex` NUMBERS/TABLES and everything under `scripts/` that regenerates them, on `main`. You own PROSE, FIGURES, and template work on a branch `jashkaran/prose`. Never edit tables/numbers by hand — every number in the paper must be produced by an aggregation script from artifacts.
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

## Track D — reserved for automation (do not touch)

Table regeneration from `outputs/real/spr/` artifacts, profile-node candidacy mechanism, §2.1 evaluator spec, claim-scoping edits. These run on Jihan's side to keep number-provenance in one pair of hands.

---

## Suggested terminal layout (max parallelism)

- Terminal 1: Track A (launch + verification Monitor) — mostly idle waiting, cheap to keep open.
- Terminal 2: Track B1 (figure) → then B3 (template).
- Terminal 3: Track B2 (examples) → then B4 (related work).
- Terminal 4: Track C (verification sweep) — read-only, zero collision risk.

All four are mutually independent. A and C touch no shared files with anything; B lives on the branch. First message to every session: point it at this file + the plan, then ask for the time estimate before it starts.
