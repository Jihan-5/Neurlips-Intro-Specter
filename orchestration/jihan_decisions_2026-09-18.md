# Jihan's decisions — 2026-09-18 (unblocks all reserved items in jazz_final_completion_report.md)

Authorized by Jihan in-session 2026-09-18. These resolve, on the record, every item the
final gate marked RESERVED or BLOCKED. Jashkaran: treat this file as the authoritative
go-ahead; nothing here is silently resolved — each decision and its rationale is stated.

## D1 — E1/F1 headline scope: 12-cell pure-SPR is the primary package

The **12-cell pure-SPR** package (`paper_sections/generated/jazz_12`) is the headline.
The 16-cell mixed package (`jazz_16`) ships as a clearly labeled archival appendix.

Rationale: the Gate-1 diagnosis (live_updates 2026-08-05) showed the original
`outputs/real/` 16-cell matrix is the no-SPR configuration; leading with the mixed
package would repeat the stale-artifact problem the audit uncovered. The pure-SPR
package is the configuration the paper actually claims.

## D2 — E2 duplicate-key conflicts (3 cells): discard-and-rerun, no selection

Amendment A1 (appended to `orchestration/profile_robustness_prereg.md`): for any
logical key `(task_id, variant_idx, arm)` with conflicting duplicate rows, **all**
conflicting copies are discarded and that key is re-run fresh under a single-writer
coordinator. No rule selects among conflicting values — this forbids cherry-picking
by construction. Re-run rows carry `recovered: true`. Non-conflicting duplicates
(byte-identical payloads) keep one copy.

## D3 — E2 paraphrase trust gate: gate stands; reporting is two-tier

The 30-item review (17/30 preserved, `orchestration/jazz_paraphrase_review.md`) is
**ratified as-is**; the bar is not lowered and the failure is disclosed verbatim.

- **Confirmatory tier (Amendment A2, declared before wave-2 completion and before any
  pooled analysis):** the pre-registered analyses are additionally run on the subgroup
  of variants whose canonical template type was judged meaning-preserved in the review
  (the review failed on specific template types — e.g. "answer directly without
  restating", "use precise technical terminology" — not at random). Subgroup membership
  is fixed by the existing review table, which predates all pooled results.
- **Exploratory tier:** the full grid is reported as observed, labeled "profile re-draw
  + paraphrase (surface fidelity 17/30 on strict review)". The paired design is intact
  (all arms saw identical variant text), so paired comparisons remain valid; only the
  "meaning-preserving" qualifier is weakened, and that is said in the text.
- F2 generation is **unblocked** under this two-tier structure; the review table is
  cited wherever the exploratory tier appears.

## D4 — LongMemEval × Llama-3.1-8B cell: ownership transferred to Jashkaran

The local run on Jihan's machine is dead at **4,919/18,000 rows**; the artifact was
pushed to `origin/artifacts` (commit `306fff9`, 2026-09-18) and supersedes the stale
4,390-row copy. Jashkaran now owns the cell: pull artifacts first, then resume it
under the single-writer coordinator alongside the other wave-2 cells. The "do not
duplicate — still running on Jihan's machine" warning in TEAM_INSTRUCTIONS/JAZZ_INSTRUCTIONS
is void.

## D5 — Credit

Jihan is raising the OpenRouter key limit $70 → $90 (probe showed $16.68 remaining on
2026-09-18; wave 2 needs ≥ $35 headroom per JAZZ_INSTRUCTIONS §2). Re-probe
`limit_remaining` before launching; do not launch E2 until it shows ≥ $35.

## Net effect on the final gate

| Gate item | Was | Now |
|---|---|---|
| E1 headline choice | RESERVED | Decided (D1) |
| E2_complete_grid | BLOCKED | Runnable once D5 credit lands (D2 recovery rule + D4 ownership) |
| E2_paraphrase_trust | BLOCKED | Resolved by two-tier reporting (D3); gate itself unchanged |
| F2_generated | BLOCKED | Unblocked under D3 structure, after E2 grid completes |
