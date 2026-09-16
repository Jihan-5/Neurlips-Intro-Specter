# Fault sweep (synthetic) -- Build-plan section 1

n=60 graphs per cell, seed=0. $0 / rule-based, no LLM calls.

**Rebuttal-usable evidence**: `unmodified` rows only (unmodified `pipeline.py` + unmodified `synthetic_dag_multi_fault.py` graphs/rerun_fn).

**Future-work exploration, NOT current-submission evidence**: `fixed` rows (`pipeline_experimental_cumulative_repair.py` + `synthetic_dag_fixed_harness.py`).

| num_faults | variant | pct_resolved | pct_all_faults_in_topN | mean_rounds_used |
|---|---|---|---|---|
| 2 | unmodified | 0.0% | 100.0% | 3.00 |
| 2 | fixed | 78.3% | 100.0% | 3.00 |
| 3 | unmodified | 0.0% | 100.0% | 3.00 |
| 3 | fixed | 0.0% | 100.0% | 3.00 |
| 4 | unmodified | 0.0% | 100.0% | 3.00 |
| 4 | fixed | 0.0% | 100.0% | 3.00 |
| 5 | unmodified | 0.0% | 100.0% | 3.00 |
| 5 | fixed | 0.0% | 100.0% | 3.00 |

## Honest read

**Attribution is unaffected by fault count**: 100% of graphs, at every N and
in both variants, have all N gold fault nodes inside the initial posterior's
top-N -- consistent with the original N=2 Experiment D finding (100% top-2)
and now confirmed to hold at N=3,4,5 as well.

**`unmodified` (rebuttal-relevant) arm: 0% full resolution at every N**,
confirming/extending the original N=2 finding (0/60) out to N=3,4,5. Root
cause (from the earlier N=2 investigation): SPR rounds re-derive from the
*original* faulty trajectory every round rather than the previous round's
partial repair, so at most one fault is ever actually cleared regardless of
round count.

**`fixed` arm (harness fix + cumulative-repair pipeline, future-work only):
the harness fix DID have a real, measurable effect this time -- but only at
N=2.** N=2 resolution jumped from 0% to 78.3% once repairs stopped reverting
across rounds and the prefix/downstream split stopped dropping sibling-branch
steps. That is a genuine improvement, not a repeat of the earlier no-op
finding. However, at N=3, 4, 5 the fixed arm is **still 0%**, i.e. the
harness fix alone does not scale past two simultaneous faults. This is a
real, reproducible result, not a residual bug in the new files -- the cause
was isolated and confirmed directly:

- The pipeline gets exactly 3 repair attempts total (1 initial decision + 2
  SPR rounds, `spr_max_rounds=2`, matching the paper's configs).
- `intro_specter.repair.choose_repair_node` (existing, unmodified,
  untouched by this sweep) selects the repair target by
  `posterior * utility_success - cost / max_cost`, i.e. it is NOT a pure
  posterior argmax -- it trades off against a cost model that heavily favors
  cheap, low-descendant-count nodes such as the terminal recommendation node
  (cost 1, no descendants), even when that node's posterior is far from the
  top.
- We directly instrumented the initial-round decision (before any SPR
  reweighting) across all 480 graphs in this sweep: **the initial round's
  chosen repair target is a true gold fault node in 0/60 graphs, at every
  N.** It reliably picks a cheap, non-fault node first (typically the
  terminal node) -- something that changes the *final output text* but
  leaves the actual faulty step text untouched, so the verifier still fails.
- That means only the 2 remaining SPR rounds ever land on real fault nodes.
  With N=2 faults, 2 real attempts are exactly enough (matches the 78.3%
  success rate, with the shortfall from the remaining ~22% coming from
  within-round tie-breaking/ordering effects on which two candidates get
  tried). With N=3 or more, 2 real attempts can never clear 3+ independent
  faults inside the fixed round budget, so resolution is mathematically
  capped at 0% for this specific budget/cost-model combination regardless of
  how correct the attribution or how "cumulative" the repair mechanism is.

**Net honest conclusion**: the harness-level fix (evolving repaired-value
map + descendant-based prefix split) is real and does what it was built to
do -- it is not a no-op this time, and it recovers substantial resolution at
N=2. But it uncovered a *second*, deeper bottleneck that is neither the
pipeline-level SPR-accumulation bug nor the harness bug: the existing
cost-regularized repair-node selection in `repair.py` structurally wastes
the first of a small, fixed round budget on a cheap-but-wrong node in 100%
of graphs tested, which caps any repair mechanism (however correct) at
"round budget minus one" real fixes. Scaling past N=2 faults within this
budget would require either a larger round budget or a change to the
cost-vs-posterior tradeoff in `choose_repair_node` -- both out of scope for
this sweep (`repair.py` is an existing tracked file and was not touched).
This is reported plainly, same as the original no-op finding, per the
non-negotiable honesty rule: no tuning was applied to either variant to
force a particular outcome.
