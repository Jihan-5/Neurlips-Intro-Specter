# Experiment D follow-up: Reflexion-equivalent baseline vs. Intro-Specter on the multi-fault synthetic set

Script: `scripts/rebuttal_experiment_d_reflexion.py`
Data: `outputs/rebuttal/experiment_d/multi_fault_vs_reflexion.jsonl`
Same 60 graphs as `scripts/rebuttal_experiment_d.py` (`build_multi_fault_example(idx, seed=0)` for `idx in [0, 60)`), same round budget (3 = 1 initial + T_spr=2), paired at the graph level.

## Investigation finding (answers item 1 of the brief)

There is **no** existing rule-based "verbal critique + blind full regeneration, retry N times" mechanism registered under the name `reflexion` for the synthetic environment. Reading `intro_specter/baselines/reflexion.py::run_reflexion`: when `provider is None` (exactly how every synthetic Tier-C config invokes it — `configs/synthetic_single_fault_test.yaml` etc. list `reflexion` with no `provider_name`), the function does **no retry whatsoever**: it checks the original trajectory once and returns it unchanged. That is the literal mechanism behind the paper's existing claim ("Reflexion ... achieve[s] 0% ... forward-only correction has no environment feedback to verbalise over", `paper_sections/main.tex:133`) — the 0% is a consequence of never attempting a fix, not of a cognitive failure to fix things.

The mechanism that actually *matches* the brief's description ("regenerate the full downstream trajectory without targeted diagnosis, retry N times") already exists under a different name: `full_regen` (`intro_specter/baselines/full_regen.py::run_full_regen`) driven by `MealPlanningDomain.make_regenerate_fn` (`intro_specter/benchmarks/synthetic_dag.py`). Both are unmodified, pre-existing, $0-cost, provider-free.

We ran **both**, unmodified, against the multi-fault set for full transparency:

- **`reflexion_noop`** — exact existing `run_reflexion(..., provider=None)` call, no round-budget parameter (never retries).
- **`full_regen_blind`** — exact existing `run_full_regen` + `make_regenerate_fn`, `max_attempts=3` (matched to Intro-Specter's budget; no other parameters invented).

## Head-to-head numbers (n=60)

| Method | % both faults resolved within budget | mean attempts/rounds used |
|---|---|---|
| Intro-Specter (Experiment D, existing) | **0.0%** | 3.0 |
| Reflexion (`reflexion_noop`, literal synthetic-protocol mechanism) | **0.0%** | 0 (never retries) |
| Full-regen-blind (`full_regen_blind`, matched 3-attempt budget) | **71.7%** (43/60) | 1.57 |

`full_regen_blind` resolved 43/60 graphs, 41 of them on attempt 1. All 43 successes are **structural, not cognitive**: both `synthetic_dag.py` and `synthetic_dag_multi_fault.py` inject faults as a MANUAL-node value **override** on top of a clean render; `make_regenerate_fn` re-renders from `profile_facts` with no overrides, so it deterministically reconstructs the gold value at every MANUAL node on the first try. This is a pre-existing property of the synthetic fault-injection design (present already for single-fault mode; not introduced or tuned here).

The 17/60 failures are explained by a genuine, pre-existing verifier artifact shared by both arms: the hard-constraint checker does plain substring matching, and the allergy-observation text "...shellfish free..." contains the banned substring "fish" (from the vegetarian/vegan `DIETARY_BANNED` list), producing false-positive violations unrelated to either injected fault whenever `allergy == shellfish_free` co-occurs with a fish-banning diet. This affects both baselines' evaluators identically (same `hard_constraint_keyword_rule`), so it does not bias the comparison, but it does mean "71.7%" is a mix of genuine regeneration success and one shared benchmark quirk.

## Honest assessment

This comparison does **not** support a "Intro-Specter handles multi-fault better than Reflexion" claim on this synthetic benchmark — if anything the reverse: a mechanism that regenerates blindly from the user profile resolves 71.7% of paired multi-fault graphs within the same round budget where Intro-Specter resolves 0%, because the synthetic fault-injection methodology (override-on-clean-render) makes blind regeneration structurally easy to win on this particular benchmark; this is a property of the benchmark, not evidence about Reflexion's real-world behavior with an actual LLM (which has no oracle access to `profile_facts` and would not regenerate this cleanly). The literal `reflexion` mechanism as wired into the synthetic protocol is degenerate in the opposite direction (0% because it never retries at all), so it is not a meaningful comparison point either. The one claim this synthetic harness *does* support, independent of resolution rate, is Intro-Specter's exclusive diagnostic value: it is the only one of the three mechanisms tested that produces a localized, auditable posterior over which node is at fault (100% top-2 attribution per the existing Experiment D run) — neither `reflexion_noop` nor `full_regen_blind` produces any localization signal at all, so that gap is real and not an artifact of this benchmark's fault-injection design. We recommend the rebuttal state the attribution/diagnosis gap, not a resolution-rate superiority claim, for the multi-fault synthetic setting.
