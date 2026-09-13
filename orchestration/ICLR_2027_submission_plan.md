# ICLR 2027 Submission Plan — Intro-Specter

**Target: ICLR 2027 main track. Abstract Sep 18, 2026 · Full paper Sep 25, 2026.**
NeurIPS 2026 decision lands Sep 24; if accepted there, we withdraw the ICLR abstract. If rejected, we submit Sep 25. Fallback chain: ICML 2027 (abstract Jan 16) with the human-annotation study added → TMLR (rolling, evidence-only criteria) as the floor.

**Strategy in one line:** the NeurIPS verdict was "solid work, insufficient novelty, synthetic evaluation" — so the ICLR submission must be visibly not the same paper: integrity-clean, rebuttal-evidence integrated, and carrying one genuinely new section (the profile-fault class + mechanism) that did not exist at NeurIPS.

---

## Status board (updated 2026-09-12)

### ✅ Done
- **Reference audit** — all 72 bib entries verified against arXiv/ACL Anthology by 4 parallel agents. 6 hallucinated (matches NeurIPS citation checker exactly), 10 minor errors — **all fixed in `paper_final.tex`**, including prose that described the fabricated papers. Audit trail: `rebuttal/reference_audit_results.md`. Zero cited-but-undefined keys.
- **Evaluator-S question resolved** (PAT's "data leak / retraction risk" flag): headline benchmarks use the reference-free self-report evaluator (`runner.py::_self_report_evaluator`); the gold-using evaluator exists only in the synthetic harness where re-execution must be simulated. Needs a §2.1 paragraph, not a retraction.
- **Iter-VRP false claim removed** — §4 "we did not run it" replaced with the executed 4-cell matched-budget results (frozen: `rebuttal/tables/iter_vrp.md`).
- **§4.6 Multi-fault robustness** (N=2–5, ~76k trajectories, saturation boundary) and **§4.7 PersonalWAB** (real user histories, 540 paired units, every discordant count in our favor) — drafted into `paper_final.tex` from artifact-frozen tables.
- **Profile-fault diagnostic** (basis of the new novelty section): corrupted-profile study across 5 datasets × 2 models (`outputs/rebuttal/experiment_a/`, aggregator `scripts/aggregate_experiment_a_diagnostic.py`). Headline: on constraint-bound tasks, Intro-Specter fails 21% of tasks it solves cleanly, 100% of those failures trace to the corrupted profile node its candidate set excludes, and no baseline recovers them either.

### ⏳ In flight
- **SPR-enabled 16-cell rerun** — resolves the 84.3% (released artifacts, no-SPR) vs 87.0% (paper claim) discrepancy. 12/16 cells runnable (Qwen-2.5-7B is dead at every API host — see infra notes). ~640/648 rows done, zero errors. Output: `outputs/real/spr/`.
- **Profile bootstrap harness** (`scripts/profile_bootstrap_study.py`, being built): ~100 re-drawn + LLM-paraphrased profile variants per example, rerun Direct/Reflexion/Intro-Specter, report the *distribution* of the effect across profile draws. Kills the "results overfit one template-bank draw" objection. Scope: maximal (5 datasets × 2 models), run in priority order (TruthfulQA + LongMemEval first).

### ⬜ To do (deadline-ordered)
1. **Sep 12–14 — Tables regenerated from artifacts** (with new SPR numbers): recomputed exact McNemar p-values (kills the impossible ones), paired-bootstrap CIs (promised in §3.4, never delivered), Direct column in Appendix D, missing MuSiQue tables, cost-% arithmetic fix, SelfCheckGPT restored to Fig. 3, tie-bolding fix.
2. **Sep 13–17 — Remaining integration**: §2.1 evaluator-S spec; real-field corruption + honest losses → appendix; operating envelope ("≥1 uncorrupted anchor") → named §6 subsection as falsifiable scope claim; multi-violation procedure App A → §2; contribution + abstract rewrite (classical-diagnosis "construction" framing); related work += Reiter/GDE/SBFL/delta debugging/Halpern–Pearl + verified 2025–26 papers (Who&When ICML'25, AgentDebug, RAFFLES w/ correct authors); Figure 1 redraw (solid dependency vs dashed attribution edges + legend); prune 35 uncited bib entries; NeurIPS checklist → ICLR format; new intro examples (see below).
3. **Sep 13–20 — New experiments** (parallel):
   - Profile bootstrap runs (maximal, priority-ordered). **Blocked on OpenRouter credit top-up (~+$30) — Jihan.**
   - Profile-node candidacy mechanism (camera-ready commitment #1): admit profile nodes to the candidate set, run on the Experiment-A cells, measure recovered failures → new "when the profile itself is at fault" subsection = the paper's novelty lever. Fallback if it slips: ship diagnostic-only.
   - Stretch: organic profile-vs-behavior contradiction rate on PersonalWAB's 1,000 real users (one number that pre-empts "you invented this problem").
4. **Sep 18 — Jihan:** register ICLR abstract + reciprocal-reviewing signup (check dual-submission wording; NeurIPS still pending until Sep 24).
5. **Sep 21–24 — Finalization**: full compile; consistency sweep (every prose number vs its table); PAT-report re-audit end-to-end; Mahfuza prose review.
6. **Sep 24:** NeurIPS decision → branch. **Sep 25:** submit.

### New motivating examples (replacing dietary-restriction/budget-hotel)
Running examples: **enterprise CRM copilot acting on a stale client record** and **healthcare intake agent with an outdated medication/allergy list**. Supporting instances: finance assistant with stale risk tolerance; coding agent conditioned on an outdated repo config. All four to be woven through intro, worked example, and the profile-fault section.

---

## Infrastructure notes (read before running anything)
- **Qwen-2.5-7B is unrunnable industry-wide** (Sep 2026): OpenRouter's only remaining upstream (Phala) emits degenerate JSON (`"/steps"` keys; arrays mangled into strings that still parse); Together dropped serverless access to every Qwen2.5-7B variant. Parser shim in `intro_specter/models/base.py::_strip_pointer_keys` protects against mode 1. Substitute **llama-3.1-8b** (OpenRouter, verified healthy) and disclose.
- Experiment A protocol: `--tau-abstain 0.0` for extension cells (0.25 caused mass abstention artifacts); in-harness `--rho 0.0` clean-control arm for drift-immune pairing.
- Budget: OpenRouter ~$8 remaining of $60 cap (needs +$30 for maximal bootstrap); Together key healthy.

## Ownership
- **Jihan:** OpenRouter top-up, ICLR abstract + reciprocal reviewing (Sep 18), final call on framing, prose review with Mahfuza.
- **Claude (this repo's sessions):** everything automatable above; monitors + detached workers for long runs; all numbers regenerated from artifacts, never hand-copied.

## Honest odds
As-is at NeurIPS-quality: ~10–15%. With everything above landed: **~25–35%**. Same upgraded paper + annotation study at ICML in January: ~30–40%. TMLR: high, but claims must be narrowed to evidence (its only criterion).

---

## Risk register (added 2026-09-12)

**Process (potentially fatal):**
1. **Deanonymization — this repo is PUBLIC** with paper, reviews, strategy, author names. ICLR is double-blind. → Flip private before Sep 25; separate anonymized artifact repo. *(Decision: Jihan)*
2. 1-day window Sep 24→25: submission must be 100% assembled by Sep 22.
3. Dual-submission gray zone (abstract Sep 18 while NeurIPS pending) — read exact CFP wording this week.
4. Reciprocal-reviewing eligibility — verify an author qualifies.
5. Public NeurIPS record: never silently walk back a posted concession; supersede with new evidence or keep it.

**Scientific:**
6. Qwen column: 4/16 cells irreproducible (provider dead). Mixed-provenance table w/ disclosure vs 12-cell paper. *(Decision: Jihan; recommendation: keep 16 + archival footnote.)*
7. Bootstrap may return an unflattering variance → we pre-commit to reporting it as-is.
8. Profile-candidacy mechanism may not recover failures → fallback diagnostic-only; must know by Sep 19 (run it early).
9. SPR delta partially confounded by provider drift → cite the 21 `repaired_via_spr` rescue rows as drift-immune evidence; all tables from new artifacts.
10. TruthfulQA has only 12 distinct tasks — don't let it carry the profile-fault story alone; LongMemEval for breadth.
11. Extend the pre-registered Holm-Bonferroni families to the new comparisons explicitly.
12. Spot-check ~30 bootstrap paraphrases by hand (canonical-rule invariant protects scoring, not display coherence).

**Operational:**
13. Budget: maximal bootstrap blocked on +$30 OpenRouter top-up (Jihan); else ship scoped + disclose.
14. Provider drift (2 incidents already): health-probe before each launch wave; snapshot dates in paper.
15. Laptop sleep pauses detached runs: use `caffeinate -i` for overnight workers.
16. Two-writer collisions on paper_final.tex: teammate owns prose/figures on a branch; automation owns tables/numbers on main; merge daily.
17. Page budget: two new results sections + contribution rewrite must fit — decide cuts by Sep 20.
18. Figure 1 redraw unassigned — good first teammate task.
