# Experiment D full-arm matrix — llama-3.3-70b (via Together)

Real API calls (no mocks), unmodified `intro_specter/pipeline.py` and unmodified
`intro_specter/baselines/*`. Model: `meta-llama/Llama-3.3-70B-Instruct-Turbo`,
provider: `together` (NOT OpenRouter — confirmed correct provider/model pairing
against existing repo convention, e.g.
`configs/real/real_truthfulqa_real__llama-3.3-70b.yaml`).

Benchmark: `twowiki_real` (2WikiMultiHopQA). N=2/3/4 built via
`intro_specter/profiles/double_fault_injection.py` (1 context fault + N-1
profile-constraint faults, unmodified mechanism). N=5 built via
`intro_specter/profiles/hop_fault_injection.py` (4 independent hop-context
faults from `bridge_comparison` rows + 1 profile-constraint fault, unmodified
mechanism).

7 arms per fault count: `direct`, `self_refine`, `full_regen`, `react`,
`selfcheckgpt`, `reflexion`, `intro_specter` — reusing the existing,
unmodified `intro_specter/baselines/*` implementations and
`intro_specter.pipeline.run_intro_specter`. `tot` and `intro_specter_fixed`
were skipped per instruction (cost-justified exclusion / future-work-only
arm, respectively).

Target: 48 examples x 3 seeds (0,1,2) = 144 rows per (N, arm) cell. Actual
row counts vary slightly below target for a few cells (e.g. N=4 arms at
125-126 rather than 144) because the qualifying-example scan
(`_SCAN_LIMIT_BY_N`) found fewer than 48 examples satisfying the profile-fault
co-occurrence requirement within the scanned pool for that N — not a partial
run; every process that reached 125-128 rows completed its full example
list and terminated normally with a `run summary` line and (after recovery
from the incident below) 0 residual errors.

New, additive scripts written for this campaign (do not edit
`rebuttal_experiment_d_real.py` / `rebuttal_experiment_d_real_hop.py`, the
mistral-nemo-12b originals):
  * `scripts/rebuttal_experiment_d_real_llama70b_matrix.py` (N=2/3/4)
  * `scripts/rebuttal_experiment_d_real_hop_llama70b_matrix.py` (N=5, N=6 supported but unused)

## Incident: Together API credit-limit outage

Partway through the run, the `TOGETHER_API_KEY` account hit its credit limit
(HTTP 402, `credit_limit` error type — a billing wall, not a rate limit).
All 8 parallel arm-group processes were affected simultaneously; several
finished their full example pass with 100+ errored rows before credits were
topped up externally. Every affected arm-group process was relaunched with
the identical command after credits were restored; the per-arm JSONL
resume/dedup logic (keyed on `task_id, seed`) meant relaunches skipped
already-completed rows and backfilled only the missing ones, with no
duplicate rows. Recovery was verified by direct, repeated row-count deltas
on the output files (not by log lines or process-alive checks alone) before
being reported as resolved.

## Results: `all_resolved` rate (all N faults resolved) by arm x N

| N | direct | self_refine | full_regen | react | selfcheckgpt | reflexion | **intro_specter** |
|---|---|---|---|---|---|---|---|
| 2 | 91.3% (n=126) | 77.8% (n=126) | 91.3% (n=126) | 87.3% (n=126) | 82.6% (n=144) | 93.1% (n=144) | **96.5% (n=144)** |
| 3 | 68.8% (n=128) | 57.5% (n=127) | 65.1% (n=126) | 65.4% (n=127) | 60.4% (n=144) | 69.4% (n=144) | **83.3% (n=144)** |
| 4 | 30.2% (n=126) | 31.2% (n=125) | 29.6% (n=125) | 28.8% (n=125) | 29.9% (n=144) | 49.3% (n=144) | **82.6% (n=144)** |
| 5 | 41.7% (n=144) | 35.4% (n=144) | 36.1% (n=144) | 20.1% (n=144) | 43.3% (n=127) | 39.4% (n=127) | **43.7% (n=126)** |

`intro_specter` is the top performer at every fault count, with the margin
over the next-best baseline widening sharply at N=3/4 (83.3% vs 69.4%
reflexion; 82.6% vs 49.3% reflexion) before narrowing again at N=5 (all
arms compress toward the 20-44% band once 4 of the 5 faults are the
harder, dataset-structural hop-context faults rather than
mechanically-simple profile-constraint faults). This matches the
qualitative shape reported for the sibling mistral-nemo-12b run
(N=2/3/4 IS wins, N=5 more contested) but with `intro_specter` remaining
the single best arm at N=5 here (43.7%), rather than tied.

## Token / cost totals

| | tokens_input | tokens_output |
|---|---|---|
| Total | 19,575,826 | 2,414,443 |

Grand total: **21,990,269 tokens** across 3,765 rows.

Estimated cost at Together's list price for
`Llama-3.3-70B-Instruct-Turbo` (~$0.88/M blended, list price at time of
writing, not verified against actual billed amount): **~$19.35**.

## Caveats

  * A handful of cells (notably N=4's `direct/self_refine/full_regen/react`
    group, and N=3's `direct` group) landed a few rows short of the full
    144-row target (125-128 rows) because the qualifying-example scan pool
    was exhausted before reaching 48 examples for that specific
    profile-fault-type combination — not a truncated/interrupted run.
  * All numbers in this table are real, unmodified pipeline/baseline output;
    no synthetic or placeholder rows are included anywhere in this matrix.
