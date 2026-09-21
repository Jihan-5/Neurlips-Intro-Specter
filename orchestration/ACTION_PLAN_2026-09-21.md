# Action plan — 2026-09-21 → Sep 25 (authoritative; supersedes prior track lists)

Owners: **Jihan** (decisions, adjudication, submission), **Jazz** (annotation, reruns, tex),
**Mahfuza** (annotator 2). Context: all Jazz gates PASS (`outputs/jazz/final_gate.json`,
`JAZZ_DONE` present); NeurIPS decision Sep 24; ICLR submit target Sep 25.

Five open issues, ranked by risk to the submission:

---

## Issue 1 — PersonalWAB contamination (HIGHEST RISK: a headline number may be inflated)

**Problem:** Jul-27 PersonalWAB runs used unfiltered histories — post-task purchases were in
the profile, so the ground-truth item was likely visible to all arms
(`JAZZ_HUMAN_ANNOTATOR_INSTRUCTIONS.md` §11). The 98.1% vs 96.1% (p=0.013) result in the
rebuttal record and draft abstract rests on it.

**Decision (Jihan, D7 — decide TODAY):** re-run clean. Contaminated numbers do not go into a
new submission, disclosed or not; the paired delta may survive but the absolute numbers won't
withstand a reviewer diffing profiles against targets.

**Steps (Jazz, ~half a day wall-clock, ~$5–10, fits the $46.68 on Jihan's key):**
1. `scripts/prep_personalwab_compact.py` — rebuild with histories truncated strictly before
   task time; verify no target ASIN appears in any profile (script has the 60/60 check).
2. Re-run `scripts/rebuttal_experiment_personalwab.py` for all model×arm cells on the clean
   build (cache-miss expected — new prompts). Same seeds 0,1,2, bench_seed 42.
3. Recompute pooled paired McNemar (IS vs each baseline) over all completed cells; regenerate
   the §4.7 table from artifacts only.
4. Swap numbers in: paper_final.tex §4.7, the abstract (Jihan holds the draft), F1 package if
   it cites PersonalWAB. Add one methods sentence: "histories are truncated before task time;
   an earlier uncontrolled variant is reported in Appendix X for continuity with the rebuttal."
5. If the clean delta is no longer significant: it still goes in as observed (campaign rule),
   and the abstract's PersonalWAB sentence is replaced with the E2 robustness result.

**Gate:** no abstract/paper submission with the old PersonalWAB numbers.

---

## Issue 2 — E1 human annotation: zero labels, deadline today

**Problem:** prep is complete and verified (pool frozen, pages built, byte-identical rebuilds)
but no human has labeled anything. Sep 21 was the completion target.

**Revised schedule (slip acknowledged; new hard end Sep 24):**
- **Sep 21 (today):** Jazz + Mahfuza label the 15-item pilot independently.
  `scripts/e1_compute_agreement.py` on the pilot; proceed iff κ ≥ 0.6. If κ < 0.6: revise
  codebook tonight (Jazz drafts, Jihan sanity-reads), re-pilot Sep 22 morning from the
  30-item reserve. Two pilot failures → escalate to Jihan (fallback: report α with the
  taxonomy collapsed to 3 categories, disclosed).
- **Sep 22–23:** main batch, 90 items each (85 natural + 5 hidden attention checks),
  ~12 h/day each. Disagreements auto-flagged; nobody resolves their own.
- **Sep 24:** Jihan adjudicates flagged items per frozen §4 rule; final κ; attention-check
  exclusion rule applied as pre-written; `attribution_vs_human` comparison + floors + MRR;
  package `outputs/iclr/e1_dataset/` + datasheet.
- **Contingency — Mahfuza unavailable today:** Jihan becomes annotator 2 (author status
  disclosed, agreement reported separately per the Aug-5 redesign). Decide by tonight; the
  study cannot slip past Sep 24 and still make an ICLR submission with the number in it.

**Gate:** submission may go out WITHOUT this number (it was never promised for ICLR) — but the
paper text must then say "annotation in progress" nowhere; the section simply reports the
dataset construction and pilot κ, or is held for camera-ready. No half-claims.

---

## Issue 3 — Apply D1 to the manuscript (stale headline numbers still in the tex)

**Problem:** `paper_final.tex` still carries the old abstract, the 87.0%/85.4% pooled claims,
and "15 of 16 cells" — all from the artifact set the Gate-1 audit invalidated. The generated
jazz_12 package (89.35%, 648 obs) is built but not inserted; final gate still lists
HEADLINE_SCOPE / HEADLINE_CELL_RECORD as reserved.

**Steps (Jazz, ~2–4 h, $0):**
1. Insert the jazz_12 tables as the primary single-fault results; move the 16-cell mixed
   package to the labeled archival appendix, exactly per D1.
2. Sweep every instance of 87.0 / 85.4 / 84.3 / "15 of 16" / "864 paired observations" in
   body, abstract, intro, and conclusion; replace from the generated package only
   (`scripts/audit_jazz_consistency.py` must come back with zero stale-number findings —
   that clears the two reserved gate items).
3. Drop in the new abstract (Jihan's final draft from 2026-09-21 session) once Issue-1
   numbers are settled — the PersonalWAB sentence is the only line waiting on Issue 1.
4. Rebuild with Tectonic; rerun full suite; push tex + regenerated PDFs.

---

## Issue 4 — E2 worst-decile: honest-language pass (small, mandatory)

**Problem:** prereg H1 clause "≥ 0 in the bottom decile" failed (pooled −0.34 pp; confirmatory
tier −7.21 pp). F2 reports it correctly; the risk is stronger language leaking in elsewhere.

**Steps (Jazz 1 h, Jihan reviews):**
1. Grep manuscript + abstract + any AC-facing draft for "worst-case", "every draw",
   "robust to any profile", "never hurts" — allowed claims are: "positive mean effect
   (+2.07 pp), favorable in 95/100 draws, bottom-decile mean −0.34 pp, reported as observed."
2. The prereg-partial-confirmation is stated once, plainly, in §F2 — not buried in a footnote.

---

## Issue 5 — Submission logistics + loose ends (Jihan)

1. **Sep 24, NeurIPS decision:**
   - **Accept →** camera-ready track: the 10 recorded commitments (memory:
     camera-ready-commitments) become the checklist; E1 annotation lands inside it; ICLR
     submission is dropped.
   - **Reject →** ICLR Sep 25: submit with Issues 1–4 closed; E1 number included only if
     Sep-24 adjudication finished clean.
2. **Abstract registration:** title + final abstract (with clean PersonalWAB numbers or the
   E2 substitute sentence) — do not wait on the full paper.
3. **`rebuttal/final/AC_confidential.md`** is still untracked — decide: commit (it's in-repo
   history visible to collaborators), move outside the repo, or delete.
4. **Paraphrase review sign-off:** `f2_generation_status.json` has `human_signoff: false`;
   Jihan replies "ratified" on the review table (D3 already says so — Jazz flips the flag and
   regenerates the status file so the record is internally consistent).
5. **Budget:** $46.68 remaining on Jihan's key covers Issue 1 with wide margin; no top-up.

---

## Order of operations (dependency-aware)

```
TODAY  : D7 decision (Jihan) ──► PersonalWAB clean rerun starts (Jazz)
TODAY  : Pilot labels (Jazz + Mahfuza) ──► κ gate tonight
Sep 22 : Main batch day 1 ─ rerun finishes ─ D1 tex sweep (parallel, Jazz)
Sep 23 : Main batch day 2 ─ number swap + language pass ─ full rebuild
Sep 24 : Adjudication + final κ (Jihan) ─ NeurIPS decision ─ branch chosen
Sep 25 : Submit (ICLR branch) or camera-ready plan kickoff (accept branch)
```

Escalation to Jihan, immediately: pilot κ < 0.6 twice · Mahfuza not labeling by tonight ·
clean PersonalWAB delta flips sign · any stale number the consistency audit can't trace.
