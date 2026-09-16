# Experiment D (real): multi-fault sweep, N=2/3/4, twowiki_real x mistral-nemo-12b

Real LLM calls throughout (real `run_reflexion`, real `run_intro_specter`, real `run_intro_specter_cumulative_repair`). Every injected fault is genuinely baked into the prompt/context the agent is shown (no clean-render escape hatch, unlike the earlier synthetic multi-fault benchmark). See `scripts/rebuttal_experiment_d_real.py` module docstring for the full injection/scoring methodology, and `intro_specter/profiles/double_fault_injection.py` for the underlying N-fault injector.

**N=5 was not run *via the profile-constraint approach*.** Constructing a 5th independent, mechanically-clean profile fault type (or requiring 4-way co-occurrence of the 4 available types: english / concise / bullets / preamble) was found impractical -- a direct simulation over 6000 profile draws found 0 examples where all 4 available types co-occur simultaneously (`inject_profile` only samples 3-5 constraints per example total). Forcing N=5 would have required either (a) an LLM-judge-based checker for a 5th subjective constraint type, which an earlier version of this experiment already found unreliable in smoke testing (see script docstring), or (b) inflating the profile size beyond what the unmodified `inject_profile` generator produces, which would no longer be testing the real benchmark. Scoped down to N=2/3/4 rather than force a compromised N=5 that way.

**UPDATE: N=5 and N=6 WERE subsequently run via a different, dataset-structural fault-injection strategy** (independent hop-level context faults on 2WikiMultiHopQA's `bridge_comparison` question type, instead of more profile-constraint faults) -- see **Section 3** below. The result reverses the story told by Section 1: at N=5/6, the Intro-Specter advantage that grew from N=3 to N=4 **does not persist** -- reflexion and intro_specter are statistically indistinguishable at N=5 and N=6 (McNemar p=1.00 and p=0.22 respectively), with reflexion nominally *ahead* at N=6.


## Section 1 -- Rebuttal-usable evidence (real Reflexion vs. real, UNMODIFIED Intro-Specter)

This is the only section usable as evidence about the current submission. Both arms run the exact, unmodified `intro_specter/baselines/reflexion.py` and `intro_specter/pipeline.py` respectively.

| N | arm | n | %all_resolved | mean frac. faults resolved | per-fault-type %resolved |
|---|---|---|---|---|---|
| 2 | reflexion | 180 | 86.7% | 0.933 | ctx=93.9%, bullets=100.0%, concise=83.3%, english=100.0%, preamble=100.0% |
| 2 | intro_specter | 180 | 87.8% | 0.933 | ctx=93.3%, bullets=100.0%, concise=84.6%, english=100.0%, preamble=100.0% |
| 3 | reflexion | 180 | 77.2% | 0.924 | ctx=82.8%, bullets=100.0%, english=100.0%, preamble=100.0%, concise=92.1% |
| 3 | intro_specter | 180 | 91.7% | 0.972 | ctx=97.2%, bullets=100.0%, english=100.0%, preamble=100.0%, concise=92.1% |
| 4 | reflexion | 180 | 70.6% | 0.918 | ctx=73.3%, bullets=98.5%, concise=93.6%, preamble=100.0%, english=100.0% |
| 4 | intro_specter | 180 | 91.1% | 0.978 | ctx=95.0%, bullets=100.0%, concise=95.0%, preamble=100.0%, english=100.0% |

### Paired comparison (McNemar on `all_resolved`, same (task_id, seed))

| N | n_paired | reflexion-only | intro_specter-only | both | neither | discordant | p |
|---|---|---|---|---|---|---|---|
| 2 | 180 | 2 | 4 | 154 | 20 | 2 | 0.6875 |
| 3 | 180 | 0 | 26 | 139 | 15 | 0 | 0.0000 |
| 4 | 180 | 1 | 38 | 126 | 15 | 1 | 0.0000 |

## Section 2 -- Future-work exploration (code-changed `intro_specter_fixed`, NOT for current-submission claims)

`intro_specter_fixed` runs `intro_specter/pipeline_experimental_cumulative_repair.py`'s `run_intro_specter_cumulative_repair` -- a fully separate copy of the pipeline (never imports or modifies `pipeline.py`) with one targeted change: SPR rounds re-execute from the previous round's partially-repaired trajectory instead of the original faulty trajectory every round. **Do not cite results in this section as evidence about the submitted method.**

| N | arm | n | %all_resolved | mean frac. faults resolved |
|---|---|---|---|---|
| 2 | intro_specter | 180 | 87.8% | 0.933 |
| 2 | intro_specter_fixed | 180 | 88.9% | 0.944 |
| 3 | intro_specter | 180 | 91.7% | 0.972 |
| 3 | intro_specter_fixed | 180 | 91.1% | 0.969 |
| 4 | intro_specter | 180 | 91.1% | 0.978 |
| 4 | intro_specter_fixed | 180 | 91.1% | 0.978 |

### Paired comparison (McNemar on `all_resolved`): intro_specter (unmodified) vs. intro_specter_fixed

| N | n_paired | unmodified-only | fixed-only | both | neither | discordant | p |
|---|---|---|---|---|---|---|---|
| 2 | 180 | 0 | 2 | 158 | 20 | 0 | 0.5000 |
| 3 | 180 | 1 | 0 | 164 | 15 | 0 | 1.0000 |
| 4 | 180 | 0 | 0 | 164 | 16 | 0 | 1.0000 |

## Token accounting

| N | arm | total tokens (in+out) |
|---|---|---|
| 2 | reflexion | 658329 |
| 2 | intro_specter | 994118 |
| 2 | intro_specter_fixed | 994118 |
| 3 | reflexion | 967741 |
| 3 | intro_specter | 1088324 |
| 3 | intro_specter_fixed | 1088324 |
| 4 | reflexion | 1292677 |
| 4 | intro_specter | 1175117 |
| 4 | intro_specter_fixed | 1175117 |

## Section 3 -- N=5 / N=6: a genuinely different fault-injection strategy (hop-level context faults)

Everything above (N=2/3/4) builds N faults as 1 context fault + (N-1) profile-constraint
faults, which structurally caps at N=4 (see the note above this table). Reaching N=5/6
required a fault-type strategy that does **not** depend on profile-constraint co-occurrence
at all. That resource exists in 2WikiMultiHopQA's `bridge_comparison` question type
(2751/12576 dev rows; 2671 of those have exactly 4 independent evidence facts, e.g. two
"director" facts + two "date of birth" facts feeding a which-was-born-later comparison,
each tied to its own supporting paragraph). We inject one near-neighbor-distractor
corruption per fact (swapping in the *other* paired fact's true value, e.g. swapping the
two directors' DOBs) -- 4 independent, textually-disjoint, mechanically-checkable context
faults, with zero reliance on profile constraints. See
`intro_specter/profiles/hop_fault_injection.py` for the injector and
`scripts/rebuttal_experiment_d_real_hop.py` for the full experiment script (both new,
additive files; `twowiki_real.py`, `fault_injection.py`, and `double_fault_injection.py`
are imported unmodified).

  * **N=5** = 4 hop-context faults + 1 profile-constraint fault (needs >=1 of the 4
    mechanically-clean profile-fault types present).
  * **N=6** = 4 hop-context faults + 2 profile-constraint faults (needs >=2 present).

Feasibility was measured directly, not assumed: a simulation drawing the real
`inject_profile` profile (seed=42, `dataset="hotpotqa"`, exactly as `twowiki_real.py` does)
for all 2671 eligible `bridge_comparison` rows found:

| required co-occurrence | rows qualifying | % |
|---|---|---|
| >=1 of {english, concise, bullets, preamble} | 1950 / 2671 | 73.0% |
| >=2 present | 532 / 2671 | 19.9% |
| >=3 present | 33 / 2671 | 1.2% |
| >=4 present | 0 / 2671 | 0.0% |

Both N=5 (73.0%) and N=6 (19.9%) had comfortably large scan pools for n=40 examples x 3
seeds x 2 arms = 240 rows each. Both runs completed in full: **0 errors, 240/240 rows
each.** Only 2 arms were run (`reflexion`, `intro_specter`) -- the future-work-only
`intro_specter_fixed` arm was skipped per instruction, since Section 2 already found it
makes no measurable difference vs. unmodified `intro_specter` at N=2/3/4.

Per-hop-fault resolution is scored mechanically (no LLM judge): the TRUE value for each
fact must appear as a substring of the FULL trajectory text (all visible reasoning `steps`
+ `final_output`, not just `final_output` alone -- a compositional comparison question's
one-sentence answer doesn't require restating the DOBs, so checking `final_output` only
would undercount resolution of facts that don't need to survive into the final sentence).
Profile-constraint fault resolution (english/concise/bullets/preamble) is scored exactly
as in Section 1 (final_output only).

| N | arm | n | %all_resolved | mean frac. faults resolved | per-fault-type %resolved |
|---|---|---|---|---|---|
| 5 | reflexion | 120 | 45.0% | 0.833 | hop0=95.0%, hop1=95.0%, hop2=71.7%, hop3=60.0%, concise=87.5%, english=100.0%, bullets=100.0%, preamble=100.0% |
| 5 | intro_specter | 120 | 45.8% | 0.832 | hop0=95.0%, hop1=95.8%, hop2=72.5%, hop3=57.5%, concise=87.5%, english=100.0%, bullets=100.0%, preamble=100.0% |
| 6 | reflexion | 120 | 45.0% | 0.868 | hop0=91.7%, hop1=100.0%, hop2=70.8%, hop3=65.8%, bullets=100.0%, concise=88.0%, preamble=100.0%, english=100.0% |
| 6 | intro_specter | 120 | 41.7% | 0.850 | hop0=90.8%, hop1=97.5%, hop2=67.5%, hop3=59.2%, bullets=100.0%, concise=92.0%, preamble=100.0%, english=100.0% |

### Paired comparison (McNemar on `all_resolved`, same (task_id, seed))

| N | n_paired | reflexion-only | intro_specter-only | both | neither | discordant | p |
|---|---|---|---|---|---|---|---|
| 5 | 120 | 1 | 2 | 53 | 64 | 3 | 1.0000 |
| 6 | 120 | 5 | 1 | 49 | 65 | 6 | 0.2188 |

**Honest reading of this result.** The Intro-Specter advantage that emerged at N=3 and grew
through N=4 (Section 1) **does not carry over** to N=5/6 under this different fault-type
mix. At N=5 the two arms are statistically tied (p=1.00, and intro_specter is nominally
*ahead* by less than one point, 45.8% vs 45.0%). At N=6 reflexion is nominally *ahead*
(45.0% vs 41.7%, p=0.22, not significant either way). The per-fault breakdown shows why:
the bottleneck at N=5/6 is `hop2`/`hop3` (the two swapped date-of-birth facts, resolved only
~58-72% of the time by *either* method) -- both arms plateau at essentially the same rate on
these, unlike the N=3/4 `ctx`/profile-constraint mix where Intro-Specter's structured
re-verification clearly separated from Reflexion's blind retry (e.g. N=4 ctx: 95.0% vs
73.3%). This suggests the N=3/4 advantage is at least partly tied to the specific fault mix
(one corrupted context value + format/language profile constraints) rather than being a
fault-count effect per se -- when the additional faults are same-difficulty independent
factual corruptions (two DOB swaps) instead of easily-separable format constraints, neither
method reliably resolves all of them and the gap closes. This is reported as-is: not spun,
not discarded.

### Token / cost accounting (Section 3)

Mistral Nemo blended rate used for the cost estimate: $0.15 / M tokens (same rate Section 1
used).

| N | arm | tokens_input | tokens_output | total | est. cost |
|---|---|---|---|---|---|
| 5 | reflexion | 317110 | 58742 | 375852 | $0.0564 |
| 5 | intro_specter | 529856 | 103767 | 633623 | $0.0950 |
| 6 | reflexion | 476487 | 82206 | 558693 | $0.0838 |
| 6 | intro_specter | 537228 | 107002 | 644230 | $0.0966 |
| **N=5+N=6 grand total** | both arms | 1860681 | 351717 | **2212398** | **$0.3319** |

Raw per-row results: `outputs/rebuttal/experiment_d/real_multi_fault_n5.jsonl`,
`outputs/rebuttal/experiment_d/real_multi_fault_n6.jsonl`.
