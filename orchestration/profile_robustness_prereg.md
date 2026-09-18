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

## Amendments (appended 2026-09-18, authorized by Jihan — see orchestration/jihan_decisions_2026-09-18.md)

**A1 — Duplicate-key conflict rule.** Overlapping top-level writers produced conflicting
duplicate rows for some logical keys `(task_id, variant_idx, arm)` in 3 cells. Rule: all
conflicting copies of a key are discarded and the key is re-run fresh under a single-writer
coordinator; no rule selects among conflicting values. Re-run rows carry `recovered: true`.
Byte-identical duplicates keep one copy. Appended before the pooled analysis has run.

**A2 — Strict-fidelity confirmatory subgroup.** The 30-item paraphrase review
(orchestration/jazz_paraphrase_review.md; 17/30 preserved) failed the trust gate. The gate
stands. The pre-registered analyses will additionally be computed on the subgroup of variants
whose canonical template type was judged meaning-preserved in that review; this subgroup is
the confirmatory tier. The full grid is reported as the exploratory tier with the review
result disclosed verbatim. Subgroup membership is fixed by the already-committed review
table; this amendment is appended before wave-2 completion and before any pooled analysis.
