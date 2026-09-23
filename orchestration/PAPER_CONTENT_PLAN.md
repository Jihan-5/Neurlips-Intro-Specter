# Paper content plan — ICLR 2027 (2026-09-23; owner: Jihan + Claude for mechanical inserts)

Organizing principle: one story in order of increasing difficulty — localize the faulty
assumption, repair only its dependents; the advantage appears as the fault burden grows.
All numbers from generated artifacts only (jazz_12, jazz_f2/f3.tex, frozen rebuttal tables,
experiment_personalwab_clean/SUMMARY.md). Consistency audit must stay at zero findings.

## Main body (~9 pp)

1. **Abstract** — final draft from 2026-09-21 session; PersonalWAB sentence in clean form
   (pending the Mahfuza contamination resolution; both variants drafted).
2. **§1 Intro** — stands; swap the stale "15 of 16 / 87.0%" evidence sentence for the
   incremental narrative (parity at single fault → separation under multi-fault →
   robustness under profile re-draws); + annotation-dataset sentence ONLY if κ exists.
3. **§2 Method** — untouched.
4. **§3 Experiments** — add ~½ page: bootstrap protocol (100 re-draws, prereg+A1/A2) and
   clean PersonalWAB protocol (before-task truncation, leak check, July correction note).
5. **§4 Results — INCREMENTAL ORDER (single → multi → robustness → real data):**
   - 4.1 Single-fault matrix (jazz_12: 89.4% pooled, 648 obs) — parity-at-matched-cost
     framing; 16-cell mixed package → archival appendix.
   - 4.2 Mechanism diagnostics + ablations + cost + VRP (existing, compressed).
   - 4.3 Multi-fault sweep (~81k trajectories, margins widen with fault count) — the
     escalation where the method separates; biggest table.
   - 4.4 Profile-draw robustness — jazz_f2.tex near-verbatim (two tiers; +2.07 pp;
     95/100 draws; bottom decile −0.34 pp reported as observed).
   - 4.5 Real user histories — CLEAN PersonalWAB (tie w/ Reflexion −0.8 pp p=0.61; wins
     vs direct +8.1, VRP +4.4, iter-VRP +3.3); July tree → appendix w/ contamination note.
   - 4.6 Candidacy + recovered failures — jazz_f3.tex (16/37, zero regressions, caveat).
   - 4.7 Human annotation — state (a) full numbers / (b) construction+pilot κ only /
     (c) omitted; decided by what is TRUE at freeze. No half-claims.
6. **§5 Related** — receives the new citation sweep (4 domains, ~30+ verified refs, full
   \cite integration; see citation protocol below).
7. **§6 Limitations** — + bottom-decile sentence, + TravelPlanner-native loss.
8. **§7 Conclusion** — rewritten last from the final abstract.

## Appendix moves
In: 16-cell archival package · July PersonalWAB + contamination/continuity note · full E2
per-cell tables · 30-row paraphrase review verbatim · codebook+prereg (if 4.7 ships) ·
expanded classical-comparison table (new systems/FL citations land here too).

## Citation sweep protocol (running now, 4 parallel deep-research agents)
Domains: systems/network fault localization · software FL + model-based diagnosis ·
LLM-agent failure attribution (2024–26) · self-correction + personalization.
Every paper verified against fetched metadata (arXiv/DBLP/publisher) — unverifiable is
dropped, never guessed. Integration: bibitem + \cite with a connecting clause each, into
§1/§5/app:classical-comparison; then audit (no undefined/uncited keys) + Tectonic build.

## Process guardrails
- Freeze order: results tables → experiments → intro/abstract → conclusion.
- Gate before every push: consistency audit zero findings + Tectonic build + language grep
  ("worst-case", "never hurts", "every discordant", "15 of 16", "87.0").
- Decision points (Jihan, before Sep 24 midnight): PersonalWAB stance (evidence pack w/
  Mahfuza) · §4.7 state (a/b/c) · Sep 24 accept→camera-ready / reject→ICLR Sep 25.
