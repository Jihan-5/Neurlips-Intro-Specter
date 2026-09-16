# Non-synthetic TravelPlanner (Experiment C follow-up): extraction-bug fix and corrected numbers

## Bug, root cause (traced, not guessed)

Original file: `outputs/rebuttal/experiment_c/nonsynthetic_travelplanner_results.jsonl`
(607 rows, 60 tasks x 3 seeds x 2 arms, minus a couple of errored rows).

Investigation confirmed: 57/303 (18.8%) of `arm=="intro_specter"` rows had
`extracted_total_cost: null` (i.e. the mechanical `_extract_total_cost` regex in
`scripts/rebuttal_experiment_c_nonsynthetic_travelplanner.py` found no parseable
`"Total cost: $<number>"` figure in the stored `final_output`), vs only 4/304 (1.3%)
of `arm=="reflexion"` rows. All 57 null-cost `intro_specter` rows, without
exception, had gone through Layer-3 downstream repair (their `meta_summary.stages`
all contain `decision` + `post_verifier`, i.e. none were `status="accepted"`
early-exit rows) -- 100% overlap between "went through repair" and "lost its
answer", which pinned the bug to the repair path specifically.

**Traced code path:**

1. `intro_specter/pipeline.py::run_intro_specter`, at the initial repair call
   (line ~246-255) and at every SPR round (line ~336-355), calls
   `rerun_downstream_subgraph_llm(..., trajectory=trajectory, ...)` where
   `trajectory` is always the **original, top-level primed trajectory** passed
   into `run_intro_specter` -- never the intermediate/previous repair attempt.
2. `intro_specter/repair.py::rerun_downstream_subgraph_llm` (line ~176-177) does:
   ```python
   new_steps = coerce_trajectory_steps(payload.get("repaired_steps", []))
   final_output = coerce_final_output(payload.get("final_output"), fallback=trajectory.final_output)
   ```
   where `payload` is the LLM's JSON response to the `REEXECUTION_SYSTEM` /
   `reexecution_user` prompt in `intro_specter/prompts.py`, which asks the model to
   "Regenerate the downstream trajectory from the repaired assumption onward"
   given a `DOWNSTREAM_NODE_IDS` list that is sometimes empty or trivial (when the
   chosen fault node has no/few descendants -- i.e. the actual fix lands entirely
   in the preserved prefix and there is nothing substantive left to regenerate).
3. `intro_specter/schemas.py::coerce_final_output` only falls back to the
   `fallback` argument (the primed trajectory's real answer) when the LLM's own
   `final_output` field is `None` or `""`. It does **not** detect "non-empty but
   non-substantive" responses.
4. In practice, when asked to regenerate an empty/trivial downstream set, Mistral
   Nemo returns non-empty junk in that field: literal strings like
   `"No downstream steps to regenerate."`, `"Repaired trajectory generated
   successfully."`, `"Unknown"`, `"Total cost: $..."` (literal ellipsis, no
   number), `"Itinerary planning in progress..."`, etc. (10 distinct placeholder-ish
   strings observed across the 57 rows -- there is no single hardcoded string, as
   the original report's hypothesis suspected; it's LLM-generated noise in
   response to a degenerate prompt). `coerce_final_output` passes these straight
   through as if they were real answers, silently discarding the primed
   trajectory's actual (often already-correct) travel plan.

This confirms and refines the original hypothesis: the placeholder text is not
hardcoded anywhere in `intro_specter/` (correctly not found by the original grep)
-- it is the LLM's own response to a degenerate "regenerate downstream steps: []"
prompt, and the bug is that `coerce_final_output`'s fallback only fires on
empty/None, not on "present but useless" text.

## Fix applied (rebuttal-script layer only; `intro_specter/` untouched)

Per instructions, `intro_specter/pipeline.py` and `intro_specter/repair.py` were
**not** modified (this behavior may be fine/intentional for other callers of
`coerce_final_output`). Instead:

1. `scripts/rebuttal_experiment_c_nonsynthetic_travelplanner.py` (the only script
   file this task authorized editing) gained a new
   `_recover_placeholder_final_output(final_traj, primed)` helper, called from
   `_run_intro_specter_arm`: if the pipeline's returned `final_output` has no
   mechanically-parseable `Total cost: $<number>` figure (via the same
   `_extract_total_cost` regex already used for scoring) **but** the original
   primed trajectory's `final_output` does, the primed trajectory's answer is
   substituted back in. If the pipeline's output does parse a cost, it is trusted
   unchanged (it may be a genuine, differently-priced repaired answer). This fixes
   the bug going forward for any future re-run of this script.
2. New script `scripts/rebuttal_experiment_c_nonsynthetic_rescue.py` re-scores the
   **existing, already-collected** JSONL with zero new API calls: for each of the
   57 affected `intro_specter` rows, it deterministically re-derives the original
   primed trajectory (`_prime_trajectory`, temperature=0.0, fixed seed) via the
   existing `cache/completions.sqlite` (~300MB, still present) -- this is a pure
   cache replay (verified: all 57 affected rows resolved via cache hits across 49
   distinct `(task_id, seed)` pairs, with a dummy `OPENROUTER_API_KEY` in place so
   any accidental cache miss would raise loudly rather than silently making a real
   call; none did). It then applies the same recovery logic and recomputes
   `extracted_total_cost` / `budget_fault_resolved` for those rows.

Output: `outputs/rebuttal/experiment_c/nonsynthetic_travelplanner_results_v2.jsonl`
(all 607 rows; the 57 corrected rows are tagged
`"_rescue_note": "recovered_from_primed_trajectory_fallback"`). The original file
is untouched for audit trail.

## Corrected numbers

| Arm | Before (buggy) | After (fixed) |
|---|---|---|
| Reflexion | 279/304 = **91.8%** | 279/304 = **91.8%** (unaffected -- not this bug's path) |
| Intro-Specter | 177/303 = **58.4%** | 208/303 = **68.6%** |

57/303 (18.8%) of Intro-Specter rows were affected; all 57 were recoverable (the
primed trajectory's own `final_output` always had a parseable cost figure -- 0 rows
remained null after the fallback). This closes roughly a quarter of the original
33.4-point gap (58.4% -> 68.6%, a +10.2-point recovery), but a substantial gap to
Reflexion **remains** (68.6% vs 91.8%, a 23.2-point gap).

## Second real reason (gap persists after the fix -- investigated, not assumed away)

The 95 still-unresolved Intro-Specter rows (in `_v2`) are **not** an extraction
artifact:
- All 95 now have a genuine, parseable extracted cost that legitimately exceeds
  the true budget (mean overshoot +65%, median +58% over budget).
- `method_believed_success` is `False` for every one of these 95 rows -- Intro-
  Specter's own verifier correctly and honestly flags every one of these as
  unresolved; there is no false "success" being claimed.
- But Intro-Specter's own verifier believes success far less often overall (33/303
  = 10.9%) than Reflexion's does (85/304 = 27.9%), while Intro-Specter's actual
  unresolved-rate is much higher (95/303 = 31.4% vs Reflexion's 25/304 = 8.2%).
  I.e. Intro-Specter is *more* pessimistic about its own output yet still fails
  the mechanical check far more often -- its targeted, subgraph-only repair
  (regenerate only the fault node + descendants, preserving the rest of the
  trajectory verbatim) is genuinely less effective at reducing a budget overshoot
  on this task than Reflexion's approach (up to 2 full self-refine trials that can
  re-plan the whole itinerary). Regenerating only a partial trajectory subgraph
  gives the model less room to cut costs elsewhere in the plan (e.g. cheaper
  accommodation/activities on days outside the regenerated window) than a full
  re-generation does.
- The effect is level-dependent: Intro-Specter resolves 93.8% of `medium`-level
  rows (comparable to Reflexion's 90.6%) but only 55.8% of `easy` rows (vs
  Reflexion 94.7%) and 67.5% of `hard` rows (vs Reflexion 89.7%). The `easy`-level
  degradation is the largest single driver of the remaining gap and warrants
  further investigation (e.g. whether the attribution/repair-node-selection step
  performs worse when there are only 3 native constraints to disambiguate among),
  but that is a distinct, real finding, not an artifact of this extraction bug.

**Bottom line:** the extraction bug was real and inflated the apparent gap by about
10 points, but even after the honest fix, Intro-Specter genuinely underperforms
Reflexion on this non-synthetic, single-budget-fault TravelPlanner setup (68.6% vs
91.8% resolved). This should be reported as a genuine limitation of the targeted
subgraph-repair mechanism on this task, not attributed further to measurement
error.
