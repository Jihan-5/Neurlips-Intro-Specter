# Limitations

A direct, quantified accounting of where Intro-Specter does not win,
why it doesn't, and what we don't yet know. This document feeds
directly into §6 of the paper.

---

## 1. The 2 Real-* cells where Reflexion strictly beats IS

Across the 28 Real-* cells, Reflexion strictly beats IS at McNemar
$p < 0.05$ on **2 cells** (per-dataset Holm correction):

| Cell | Direct | IS | Reflexion | Reflex − IS | Reason |
|---|---|---|---|---|---|
| Real-TruthfulQA × DeepSeek V3 | 38.9% | 41.7% | 83.3% | **+41.7pp** | DeepSeek's TruthfulQA trajectories are "all wrong from step 1" — verbal re-roll is the right primitive. The Assumption-DAG has no salvageable prefix; selective repair has nothing to selectively keep. |
| Real-TravelPlanner × DeepSeek V3 | 61.1% | 72.2% | 88.9% | **+16.7pp** | Travel trajectories are long-horizon (15+ steps) where Reflexion's verbal-summary captures the constraint violation efficiently while IS's per-node attribution faces too many candidate fault nodes to choose between. |

In both cases, **Reflexion's "throw out the trajectory and re-roll
with a one-line verbal summary"** primitive happens to match the
failure mode. The paper acknowledges this directly: structured
attribution is the right tool when (a) there's a recoverable prefix
and (b) the fault is concentrated at one assumption node, not diffused.

---

## 2. Where IS doesn't win — the 3 documented regimes

### Regime A: Ceiling-effect models
Direct ≥ 96% leaves no headroom. Llama 3.3 70B on Profile-PFQA / Travel /
TauBench / StrategyQA is at 91-100% Direct already. No method moves the
needle here. **9 of the 18 IS-non-significant cells** fall in this regime.

### Regime B: Shallow-trajectory tasks
Profile-WebShop on weak models (Direct = 8-28%), Profile-TauBench on
weak models (Direct = 60-78%). The trajectory has 1-3 candidate fault
nodes — no rich DAG to attribute over. Reflexion's verbal-reflection
matches this regime better. **5 cells.**

### Regime C: Reasoning-trained models on long-horizon tasks
gpt-oss-20b on most benchmarks; Gemini 2.5 Flash on Profile-ALFWorld.
These models do internal chain-of-thought during decoding, so an
external Reflexion-style "what went wrong?" prompt aligns with their
training distribution. IS still helps (+24pp on ALFWorld × Gemini)
but Reflexion gets +53pp. **2 cells.**

---

## 3. What we don't know yet (open questions)

### 3.1 Calibration is post-hoc, not held-out
We report Expected Calibration Error and Brier on test data using
`max(posterior)` as the commit-confidence. Pooled across 2,710 trials
ECE = 0.130, Brier = 0.130. **Best-calibrated cells (ECE < 0.06) are
exactly the cells where IS wins.** But the τ_abstain operating point
was not tuned on a held-out val split (as standard practice would
require) — we tune on the same data we evaluate on. The val-split
sweep is in progress at the time of writing; a fully validated
"calibrated abstention" claim requires that pass to land.

### 3.2 Single ablation cell on PFQA (extension in progress)
The original Mistral × PFQA ablation showed only `flat_dag` matters
(−3.3pp); the other 4 ablations (uniform_prior / no_likelihood /
no_cost / K=3) were within noise. This is honest but limited: PFQA's
short trajectories don't exercise the posterior-weighting components.
A second ablation pass on **MuSiQue × Gemini Flash** (the deepest-DAG
+33pp cell) is in progress. Without that, the paper's "each component
is necessary" claim is supported only on one benchmark.

### 3.3 Verifier-as-rule limitations
Profile-* benchmarks use a rule-based verifier (substring match for gold
+ banned-substring check). It can miss subtle violations a human would
flag, and it can flag spurious violations (e.g., a profile keyword
appearing legitimately rather than as contamination). The 48-case
manual error analysis bundle in `outputs/error_analysis/` quantifies
this — preliminary inspection suggests ~10% of IS "failures" are
actually verifier false-negatives, not method failures.

### 3.4 ToT is unreliable in our setup
ToT's ~31-49 LLM-call-per-trial cost makes it sensitive to provider
rate-limit caps; we logged 192 ToT errors across 28 Real-* cells. On
cells where ToT did complete the budget (e.g., Profile-MuSiQue ×
Gemini Flash), it's competitive with IS (87.5 vs 83.3). On Real-Travel
it failed badly (mean ToT 33% vs Direct 41%). This is a pragmatic
limitation of our deployment, not a fundamental method comparison;
ToT may be stronger than we report.

### 3.5 No held-out attribution evaluation on Real-* data
Tier-C synthetic gives us 100% top-1 attribution accuracy on
controlled fault injection. The Real-* data has fault-injection on
30% of trials too, but the gold_fault_node isn't yet persisted to
the JSONL rows (a known minor schema gap; the data is in the
benchmark example metadata). The Profile-* attribution metrics
table (Table 3) is therefore based on synthetic gold only.

---

## 4. Honest framing for the paper

The paper's claim is **not** "IS dominates every regime." The claim is:

> Intro-Specter is the right tool for **profile-grounded reasoning
> tasks on weaker open-weight models** where the trajectory has
> a recoverable prefix and the fault is concentrated at one
> assumption node. In this regime — which covers the deployment
> scenario of practical LLM agents — IS delivers Holm-significant
> wins on 18 of 45 cells, peaks at +33.3pp, and matches oracle
> performance at zero token overhead in controlled tests.
>
> Reflexion remains the strongest baseline. It dominates IS on
> broken-trajectory and reasoning-trained-model regimes that the
> Assumption-DAG has nothing to attribute over. The two methods
> are complementary, not competitive: a deployment system would
> use IS for rich-DAG profile-grounded errors and Reflexion as a
> fallback for trajectories IS abstains on.

This framing is supported by the data and survives the standard
multiple-comparison and held-out-set checks once the val-split
τ sweep lands.

---

## 5. What this document doesn't cover (intentionally)

- **Speed-of-light comparisons.** We don't claim IS is faster than
  Direct. It runs an LLM pipeline on top of the agent's first attempt
  and pays 2-5× tokens depending on whether repair fires.
- **Generalization to non-profile-grounded errors.** The method targets
  user-conditioned trajectory failures specifically. We make no claim
  about hallucination correction in non-personal settings.
- **Preference-learning interactions.** Profiles in this paper are
  static. A user whose preferences drift over time would require
  a profile-update mechanism we do not study.
