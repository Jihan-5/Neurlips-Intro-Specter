# Coverage matrix — every reviewer concern → where it is answered

Built from the concern decomposition in `orchestration/E2Eplan.md` (verbatim review texts are
not stored in-repo; **at sign-off, the user should eyeball this matrix against the actual
OpenReview texts** to catch any sub-point the decomposition compressed away).

## Reviewer Mahh (rating 3, conf 4)

| # | Concern | Where answered | Evidence artifact |
|---|---|---|---|
| W1 | Synthetic construct; no naturally occurring failures or human fault labels | Mahh ¶1 (two-claim decomposition), ¶"Requirement (2)" (PersonalWAB completed results), ¶"Two further items" (honest negative: un-injected tasks show no assumption-driven failures — construct requires user-conditioning), Claim-2 concession (human fault labels = camera-ready, κ) | `experiment_personalwab/` (540 paired units), `experiment_c/natural_failures_sample_v2.jsonl` |
| W2 | Incrementality / is the gain just retry budget | 4jc8 reply Iter-VRP table (cross-referenced from Mahh via PersonalWAB's Iter-VRP arm: 98.0 vs 95.2, p=0.0015) | `experiment_b/` 4 cells + rounds-used; `experiment_personalwab/` |
| W3 | Profile immutability under noisy/stale profiles | Mahh ¶"Two further items": ρ=0.10/0.30 profile-corruption cells, IS ahead at both | `experiment_a/` (279 rows) |
| Q1 | Small margin vs Reflexion | Mahh evidence blocks A+B: margin grows with fault count (17.3pp at HotpotQA n=4); PersonalWAB significant vs Reflexion (12/3, p=0.035); TravelPlanner-real gap shrinks 23.2→4.0 under multi-fault | freeze tables |
| — | (implicit) cherry-picking / tailored evaluation | Mahh: disclosed losses (Amazon 42.0 vs 67.1 clean; TravelPlanner-real 37.8 vs 41.8), hop-tier nulls, clean-anchor boundary as tested prediction | `experiment_amazon/`, `experiment_c/nonsynthetic_multifault/`, hop tiers |

## Reviewer 4jc8 (rating 3, conf 4)

| # | Concern | Where answered | Evidence artifact |
|---|---|---|---|
| 1 | SE / fault-tolerance / network-reliability prior art uncredited | 4jc8 ¶1: dedicated related-work subsection with 12 verified citations (Reiter 87; de Kleer & Williams 87; Jones & Harrold 05; Abreu 06; Wong 16; Zeller & Hildebrandt 02; Weiser 81; Korel & Laski 88; Halpern & Pearl 05; Pearl 09; Kliger 95; Steinder & Sethi 04) | citation audit in draft editor notes |
| 2 | What is actually new vs that literature | 4jc8 ¶2–4: three structural differences (candidate set inferred not given; no spectrum — counterfactual trials synthesize one; diagnosis=repair on an edit-cost frontier) | prose, grounded in §2.2/Eq.1/Eq.3–4 |
| 3 | Claims exceed evidence | 4jc8 closing ¶: point to response-period record (nulls+losses reported, artifact-traceable) rather than re-asserting submitted per-cell numbers; Iter-VRP run *because* the paper named it missing | all campaign outputs |
| — | Profile-immutability double-edge (also Mahh) | 4jc8 ¶5: same property both reviewers read differently; treated as scoped modeling assumption | — |

## Reviewer LDZz (rating 5, conf 3)

| # | Concern | Where answered | Evidence artifact |
|---|---|---|---|
| 1 | Figure 1 apparent cycles | LDZz ¶1: cycles are backward attribution arrows, not graph edges; DAG acyclic by construction (§2.1 cycle-resolution); camera-ready redraw with distinct arrow styles | paper text line 68 |
| 2 | Multiple simultaneous violations | LDZz ¶2: sequential single-node pass w/ re-verification (Appendix A; Figure 1 resolves a₄ then a₇); promoted to §2 for camera-ready | paper Appendix A |

## AC meta-review (4 fix paths)

| # | Fix path | Where answered |
|---|---|---|
| 1 | Naturally occurring failures | AC ¶1 + Mahh: PersonalWAB completed (98.0 pooled, sig vs all); honest negative on un-injected failure modes; human-fault-label concession |
| 2 | Validation beyond synthetic injection | AC ¶1 + Mahh: multi-fault matrix (5 datasets), real-field corruption (3 domains incl. losses), Iter-VRP control, profile-noise cells |
| 3 | Related-work treatment | AC ¶2 + 4jc8: dedicated subsection + three structural differences |
| 4 | Exposition | AC ¶3 + LDZz: both items with camera-ready commitments |

## Known gaps deliberately NOT covered by any experiment (disclosed, not hidden)
- Human-annotated fault labels on real trajectories (Claim 2) — camera-ready with inter-annotator κ; explicitly conceded in Mahh ¶Requirement-(2) and AC ¶1.
- Attribution accuracy on natural trajectories — same concession (synthetic diagnostics only, Appendix E).
- Recipes Llama-8B partial (n=1 tier only) and Amazon Llama-8B n=4 partial — disclosed per-model n's in freeze tables.
- Reflexion empty-output bug on Llama-70B cells (TravelPlanner-real 45.7%, Amazon 38.5%, Recipes 16.5% of rows) — those cells excluded from clean comparisons; bug disclosed in Mahh evidence block B.
