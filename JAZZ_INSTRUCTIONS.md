# Jazz — you own ALL remaining experiments + the results rewrite (Tracks E & F)

Self-contained brief, handed off 2026-09-15. Point every Claude Code session at THIS file first
("read JAZZ_INSTRUCTIONS.md, then estimate wall-clock + API cost for the track I paste next").
Background docs if a session needs them: `orchestration/ICLR_2027_submission_plan.md` (goal,
dates, Gate 1, risk register), `orchestration/TEAM_INSTRUCTIONS.md` (same tracks, shorter form).

**Deadline context:** NeurIPS decision Sep 24 → ICLR submit Sep 25. Everything below must be
runnable-complete by **Sep 20** so Sep 21–24 is pure finalization.

---

## 1. Setup (once)

```bash
git clone https://github.com/Jihan-5/Neurlips-Intro-Specter.git && cd Neurlips-Intro-Specter
python3 -m venv .venv && .venv/bin/pip install -e .
```

- **API keys:** Jihan sends you your own `OPENROUTER_API_KEY` and `TOGETHER_API_KEY` privately
  (Signal/1Password — not Slack plaintext). Put them in `.env.local` at repo root (gitignored).
  **NEVER commit keys.** Load with: `set -a; source .env.local; set +a`
- **Datasets:** first runs download MuSiQue/2Wiki/LongMemEval/HotpotQA from HuggingFace — expect
  a slow first cell on a fresh machine.
- **Key health probe before ANY wave** (two providers died mid-campaign already):
  ```bash
  curl -s https://openrouter.ai/api/v1/key -H "Authorization: Bearer $OPENROUTER_API_KEY"
  # check limit_remaining before launching; wave 2 needs ~$30 headroom (see §2)
  ```

## 2. Budget — what the OpenRouter key must have on it

| Item | Est. cost |
|---|---|
| E2 bootstrap wave 2 (7 cells, maximal scope) | ~$30 |
| E1 SPR rerun completion (cache-assisted) | ~$1–2 |
| E3 candidacy runs on Experiment-A cells | ~$3–5 |
| Buffer for resume passes / retries | ~$5 |
| **Total OpenRouter credit needed** | **~$40** |

Jihan is topping up / issuing your key with this credit — **confirm `limit_remaining ≥ $35`
via the probe above before launching E2**; E1 and E3 can start on less. Together key is healthy,
no top-up needed there.

## 3. Ground rules (non-negotiable)

1. **Never type a number into the paper by hand.** Every number comes from an aggregation
   script over committed artifacts; put the script invocation in the commit message.
2. Experiments write to `outputs/` (gitignored) and are **resumable** — rerunning the same
   command skips completed rows. Never delete a `.jsonl` unless instructed.
3. Protocol constants: `--tau-abstain 0.0`, generation seed 0, benchmark seed 42.
   **Qwen-2.5-7B is DEAD at every host — never launch it**; llama-3.1-8b is the substitute
   (disclose the substitution wherever it appears).
4. Long runs: `caffeinate -i nohup ... & disown` (macOS) so sleep doesn't pause them.
5. Branches: experiments/artifacts + results/tables → `jazz` branches (`jashkaran/results`),
   prose → `jashkaran/prose`. **Do not merge into main yourself** — Jihan merges.
6. After every session: append to `orchestration/team_status.md`
   (`[date] [track] [what ran] [rows/verification] [next]`), commit, push. Pull before starting.
7. Before each track, have your Claude estimate wall-clock + cost and log it. Any single
   track estimating >6h → post it, we re-split.

---

## 4. TRACK E — experiments (priority order)

### E1. Finish + aggregate the SPR-enabled 16-cell rerun — DO THIS FIRST
Resolves the paper's 87.0% (claim) vs 84.3% (released no-SPR artifacts) discrepancy — the
single highest-stakes number in the campaign (Gate 1 in the plan).

- State: ~640/648 rows done, `outputs/real/spr/`. On disk: truthfulqa/musique/longmemeval
  × {llama-3.1-8b, llama-3.3-70b, mistral-nemo-12b}. **The three twowiki cells are missing** —
  check `outputs/real/spr/_logs/` for the exact launch commands used and complete them
  (resumable), plus any short rows in existing cells.
- Aggregate: `scripts/aggregate_real_benchmarks.py` pointed at `outputs/real/spr/`.
- Deliverable: pooled Intro-Specter success with SPR on + per-cell table, pasted verbatim into
  `team_status.md`. **Do NOT reconcile it against the paper yourself — send the number to
  Jihan immediately**; what the paper claims branches on it.

### E2. Bootstrap wave 2 — 7 remaining cells (waits on the $30 credit)
- ⚠️ `longmemeval_real × llama-3.1-8b` is STILL RUNNING on Jihan's machine (4,249/18,000 rows
  as of Sep 15) — do not duplicate that cell.
- Smoke first: one `--smoke` invocation per (dataset, model) pair; confirm rows written,
  non-empty outputs, zero `[ERROR]`, distinct profile hashes. Then launch:

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

- Verify every ~30 min (or set a Monitor):
  `wc -l outputs/rebuttal/profile_bootstrap/*/variants.jsonl` (target 18,000/60-task cell,
  3,600 for hotpotqa/truthfulqa), `grep -c "\[ERROR\]"` on the logs (~0),
  `python3 scripts/aggregate_profile_bootstrap.py` (no crashes).
- Done = full row counts everywhere → run the aggregator → apply the **pre-registered**
  analysis in `orchestration/profile_robustness_prereg.md` EXACTLY as frozen (worst-case
  decile + Hoeffding already specced). Report numbers as-is; zero interpretation.

### E3. Profile-node candidacy mechanism — START IN PARALLEL DAY 1 (long pole)
Camera-ready commitment #1 and the paper's novelty lever.

- Build: admit profile nodes into the SPR candidate set (currently excluded — see candidate-set
  construction in `intro_specter/pipeline.py`), behind a flag (`--allow-profile-candidates`)
  so default behavior is byte-identical.
- Run on the Experiment-A cells (`outputs/rebuttal/experiment_a/`; protocol: `--tau-abstain 0.0`,
  in-harness `--rho 0.0` clean-control arm).
- Measure: of failures the diagnostic attributes to corrupted profile nodes (headline: 21% of
  clean-solved tasks fail, 100% traceable), how many does the mechanism RECOVER?
- Aggregate via a new `scripts/aggregate_profile_candidacy.py` modeled on
  `aggregate_experiment_a_diagnostic.py`.
- **If this slips past Sep 20, tell Jihan immediately** — fallback is shipping diagnostic-only.

### E4. Stretch — organic contradiction rate on PersonalWAB
One number: fraction of PersonalWAB's 1,000 real users with ≥1 profile-vs-behavior
contradiction in their history. Rule-based if possible, cheapest model otherwise. Pre-empts
"you invented this problem." Only after E1–E3 are launched/done.

---

## 5. TRACK F — rewrite the results from the new artifacts (branch `jashkaran/results`)

F1 blocks on E1; F2 on E2; F3 on E3. F4 starts as soon as F1 lands.

### F1. Table regeneration with the new SPR numbers
Recomputed exact McNemar p-values (kills the currently-impossible ones) · paired-bootstrap
95% CIs (promised in §3.4, never delivered) · Direct column in Appendix D · missing MuSiQue
tables · cost-% arithmetic fix · SelfCheckGPT restored to Fig. 3 · tie-bolding fix.
Checklist source: `orchestration/pat_sweep_results.md` (Track C output) — run that sweep
first if it doesn't exist yet (checklist is in TEAM_INSTRUCTIONS Track C).

### F2. Profile-robustness results subsection
Strictly per `orchestration/profile_robustness_prereg.md`: effect distribution across profile
draws, worst-case decile, Hoeffding bound. Anything beyond the prereg is labeled exploratory.

### F3. "When the profile itself is at fault" subsection
Write up E3's recovered-failure results as the novelty subsection; wire to the existing
diagnostic numbers and to Table `tab:classical` (now in the appendix).

### F4. Consistency sweep
Every prose number vs its generating table, whole paper. This is the Sep 21–24 gate.

### Citations for any new text
Keys come ONLY from `rebuttal/reference_audit_results.md` (Batch 5 has the classical-diagnosis
keys + newly verified `zhang2025whowhen`, `zhu2025agentdebug`). Never cite from memory — this
project already got burned by 6 hallucinated references at NeurIPS.

---

## 6. Suggested terminal layout

- Terminal 1: E1 → F1
- Terminal 2: E3 (start immediately — long pole)
- Terminal 3: E2 once credit lands (+ verification Monitor)
- Terminal 4: Track C PAT sweep (if `pat_sweep_results.md` absent) → F4

## 7. When to ping Jihan (don't sit on these)

1. E1's pooled SPR number, the moment the aggregator prints it.
2. OpenRouter key missing the ~$35 headroom for E2.
3. E3 at risk of slipping past Sep 20.
4. Anything that makes a released/paper number look wrong — flag, don't fix silently.
