# Cumulative-repair SPR variant -- future-work exploration

Status: FUTURE-CONFERENCE R&D EXPLORATION. NOT evidence about the current
submission. The reviewed method (intro_specter/pipeline.py) is completely
unmodified. Everything here comes from a new, isolated module
(intro_specter/pipeline_experimental_cumulative_repair.py) that no existing
script, config, or rebuttal experiment imports. Do not cite these numbers as
evidence about the submitted method; they answer a forward-looking
"what would it take" question raised by Experiment D.

## What changed

Experiment D found that Intro-Specter's Sequential Posterior Refinement (SPR)
loop rebuilds from the original faulty trajectory every round instead of the
previous round's partially-repaired trajectory -- in pipeline.py, the SPR loop
calls rerun_downstream_subgraph_callable(trajectory=trajectory, ...) using the
outer trajectory argument on every round.

The experimental module changes exactly that: inside the SPR round loop, the
rerun call now passes trajectory=last_traj (the previous round's repaired
trajectory) instead of trajectory=trajectory (the original). This is a 2-line
change relative to pipeline.py; every other line -- attribution, posterior
soft-decay, spr_max_rounds=2, tau_abstain, cost-regularized
choose_repair_node -- is copied verbatim.

## Result 1: multi-fault improvement test (60 graphs, Experiment D's set)

Same 60 two-simultaneous-independent-fault synthetic graphs
(intro_specter/benchmarks/synthetic_dag_multi_fault.py, seed=0), same harness
shape as scripts/rebuttal_experiment_d.py, run through the cumulative-repair
variant:

- n_graphs: 60
- pct_both_resolved_within_budget: 0.0% (baseline pipeline.py: 0.0%)
- pct_both_faults_in_top2_posterior: 100.0% (unchanged from Experiment D)
- mean_rounds_used: 3.0

The cumulative-repair change made no difference: still 0/60. A row-by-row
diff against the existing Experiment D output
(outputs/rebuttal/experiment_d/multi_fault_results.jsonl) shows the
cumulative-repair variant's final_output and final_fault_node are
byte-identical to the original pipeline.py on all 60/60 graphs -- the fix had
zero observable effect on this benchmark.

### Root cause (why the fix is a no-op here)

The pipeline-level fix only changes which Trajectory object is threaded into
rerun_downstream_subgraph_callable. But for this synthetic benchmark, the
actual repaired values don't come from that trajectory at all:

- MealPlanningDomain.make_rerun_fn (intro_specter/benchmarks/synthetic_dag.py,
  reused unmodified per the task's instructions) closes over a static
  prefix_values=faulty_values snapshot captured once, at harness-construction
  time. Every call to ComputeGraph.re_execute inside it recomputes values for
  nodes outside the current fault node's DAG-downstream zone from that static
  snapshot -- never from whatever the previous SPR round actually wrote. So
  when round 2 repairs a5 (branch 1), node a7 (branch 2, not downstream of
  a5) reverts to its original faulty value regardless of what last_traj says,
  because re_execute never looks at last_traj.
- Compounding this, repair.split_valid_prefix (intro_specter/repair.py,
  shared by both the original and experimental pipeline) cuts "valid prefix
  vs. downstream" purely by step_id order (step_id < earliest_affected), not
  DAG structure. Since a7 sits at step 9 and a5's affected zone starts at
  step 5, step 9 is classified "downstream of a5" and dropped from the prefix
  even though a7 is not a graph descendant of a5 -- so the previous round's
  a7 fix is discarded from the prefix on top of being ignored by re_execute.

Net effect: for this benchmark's rerun_callable design, no amount of
trajectory-threading inside pipeline.py's SPR loop can matter, because the
callable ignores the trajectory's values outside the zone it's repairing. A
real fix would require either (a) redesigning the synthetic benchmark's
rerun_fn/re_execute to consume the evolving repaired-value map across rounds
instead of a static per-example closure, or (b) reworking
split_valid_prefix to cut by DAG-descendant membership rather than step
order. Both are out of scope for "reuse synthetic_dag_multi_fault.py
unchanged" and for a "minimal, targeted change" to the SPR loop, so they are
not implemented here.

## Result 2: single-fault regression check (60 graphs, Appendix G protocol)

Same 60 single-fault synthetic graphs (synthetic_dag.py, mode="single_fault",
n_examples=60, split="all"), same cumulative-repair variant:

- n_graphs: 60
- pct_top1_attribution: 100.0% (paper reports 100%)
- pct_repaired: 100.0% (paper reports 100%)

No regression. Single-fault graphs never reach the SPR loop's affected code
path in a way that changes behavior (the first repair already resolves the
one fault, so last_traj vs. trajectory never diverge), which is consistent
with the round-1-only nature of single-fault resolution.

## Honest assessment

The cumulative-repair change to pipeline.py's SPR loop, as specified (make
each round rerun from the previous round's trajectory instead of the
original), is a real, minimal, targeted fix to the bug Experiment D
identified -- but it does not fix multi-fault resolution on the existing
60-graph benchmark: 0/60 both-resolved before and after, byte-identical
outputs. The reason is that the bug Experiment D found in pipeline.py is real
but not the only thing standing in the way of accumulation; the synthetic
benchmark's downstream re-execution primitives (ComputeGraph.re_execute's
static-snapshot closure, and split_valid_prefix's step-order-based cut)
independently discard cross-branch repairs regardless of what pipeline.py
does with the trajectory object. Single-fault behavior is fully preserved
(100%/100%, matching the paper).

This is not a viable fix as currently scoped. It is a legitimate future-work
direction, but pursuing it further would require touching the benchmark's
re-execution primitives (out of scope here, and arguably out of scope for
"reuse unchanged"), or moving to the real-benchmark LLM re-execution path
(rerun_downstream_subgraph_llm), where the "downstream zone" is defined by a
natural-language prompt over the actual trajectory text rather than a static
value closure -- a different setting than what was tested here and not
evaluated in this exploration.

## Reproduction / files

- New isolated module: intro_specter/pipeline_experimental_cumulative_repair.py
  (full standalone copy of pipeline.run_intro_specter, not imported by any
  existing file).
- Driver script: scripts/experimental_cumulative_repair_eval.py.
- Raw per-graph results: cumulative_repair_multi_fault.jsonl,
  cumulative_repair_single_fault_regression_check.jsonl.
- Combined summary: cumulative_repair_summary.json.

## Scope verification

intro_specter/pipeline.py and all other existing tracked files were not
edited by this exploration. git status/git diff show only two new untracked
files added (intro_specter/pipeline_experimental_cumulative_repair.py,
scripts/experimental_cumulative_repair_eval.py) plus this output directory;
no existing tracked file's diff changed as a result of this work. (Any
pre-existing modifications to intro_specter/pipeline.py visible in git status
predate this exploration and belong to the concurrent rebuttal experiment
work referenced in the task instructions, not to anything done here.)
