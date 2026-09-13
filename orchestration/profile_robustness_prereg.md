# Pre-registration: profile-robustness bootstrap study

**Committed BEFORE any full-run results exist** (only the 2-example smoke test has run; git hash of this commit is the timestamp). Purpose: make profile-selection manipulation impossible-by-design and analysis choices tamper-evident.

## Hypothesis (frozen)
H1: Intro-Specter's advantage over Reflexion on profile-injected benchmarks is invariant to the profile draw: pooled over 100 seeded re-draws (with LLM paraphrase) per example, the paired IS−Reflexion effect is positive in the large majority of draws, and remains ≥ 0 in the bottom decile of draws (worst-case selection against IS).

## Design commitments (frozen)
1. Profile draws are seeded: sha256(task_id | variant_idx) — committed in `scripts/profile_bootstrap_study.py` before evaluation. The draw process never conditions on method identity; all arms receive the identical variant profile (paired design).
2. Verifier rules regenerate from the CANONICAL (pre-paraphrase) template text; paraphrase affects surface form only.
3. N=100 variants per example; arms = direct, reflexion, intro_specter; generation seed 0; tau_abstain=0.0.
4. Every (dataset, model) cell launched is reported — no cell, draw, or arm may be dropped post hoc. Malformed/provider-error rows are reported as counts, never silently excluded.

## Analysis plan (frozen)
Per cell and pooled:
- Mean success per arm across all draws; per-example variance across draws.
- Distribution of paired per-draw IS−Reflexion effect: mean, 2.5/97.5 percentiles, P(IS ≥ Reflexion).
- Worst-case tail: effect within the bottom decile of draws ranked by IS−Reflexion (adversarial selection AGAINST Intro-Specter; conservative by construction).
- Concentration statement: Hoeffding bound on P(observed favorable-draw fraction | true favorable fraction ≤ 0.5).
- Paraphrase spot-check: ≥30 random paraphrases hand-checked for meaning preservation before results are trusted.

## Reporting commitment
Results are reported as observed, including any cell where the effect is negative, its bottom decile flips sign, or variance across draws is large. This document may be appended to but not edited after commit.
