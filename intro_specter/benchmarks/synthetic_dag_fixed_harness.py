"""FUTURE-WORK EXPLORATION -- NOT part of the current NeurIPS submission's
evidence base. Standalone, additive harness-level fix for Experiment D's
cumulative-repair pipeline variant
(`intro_specter/pipeline_experimental_cumulative_repair.py`, built earlier
tonight, not touched by this file). Do not cite results produced with this
module as evidence about the reviewed method; the reviewed method's harness
is `intro_specter/benchmarks/synthetic_dag.py` + `intro_specter/repair.py`,
neither of which this file imports for modification, edits, or monkeypatches
(``ComputeGraph`` is imported READ-ONLY and used unmodified).

Background -- two harness-level bugs found while investigating why the
cumulative-repair pipeline variant had *zero* measurable effect on the
multi-fault synthetic benchmark (Experiment D, N=2 faults, 0/60 -> 0/60):

1. **Static value snapshot.** `MealPlanningDomain.make_rerun_fn` (in
   `synthetic_dag.py`) closes over `prefix_values=faulty_values` -- the
   *original* faulty node-value map, captured once when the benchmark example
   is built -- and passes that SAME static dict to `graph.re_execute(...)` on
   every call, for every SPR round. So even though
   `pipeline_experimental_cumulative_repair.py` correctly threads the
   *previous round's repaired trajectory* into the re-execution call, the
   closure it calls into re-derives every "outside the swap zone" node value
   from the ORIGINAL faulty snapshot every time -- silently reverting
   whatever a prior round already fixed. This is why the cumulative-repair
   pipeline logic change was a no-op: the fix was applied one layer above
   where the actual staleness lived.

2. **Step-id-ordered prefix/downstream split.** `intro_specter.repair.split_
   valid_prefix` (an existing, unmodified, tracked file we do not edit) marks
   a trajectory step "downstream" of a fault node by comparing `step_id`
   against the *earliest* step id among the fault node's true DAG
   descendants -- i.e. "downstream" = "step_id >= earliest_affected_step_id".
   On this benchmark's multi-fault graphs, independent branches interleave
   step ids (e.g. branch 1's fault sits at step 5, branch 2's entire body
   occupies steps 6-9, and they only reconverge at the terminal step 10).
   Branch 2's steps are NOT descendants of branch 1's fault node, but they DO
   have `step_id >= 5`, so the ordered split silently drops them from BOTH
   the "prefix" set (excluded, step_id too high) AND the "downstream" set
   returned by the original `make_rerun_fn` (excluded, not a true descendant
   -> not in `zone_step_ids`) -- they vanish from the reassembled trajectory
   entirely.

This module fixes both, as a fully separate/standalone pair of functions:

* `split_valid_prefix_fixed` -- same (prefix_steps, downstream_steps)
  contract as `intro_specter.repair.split_valid_prefix`, but partitions
  purely by TRUE DAG descendant *membership* (via
  `intro_specter.dag.descendants_of_node`, unmodified), never by step_id
  order/threshold. Provided as the correct, reusable primitive; also used
  below as the source of truth for the fixed closure's own bookkeeping.

* `make_rerun_fn_fixed` -- drop-in replacement for
  `MealPlanningDomain.make_rerun_fn` with the SAME call signature/contract
  (so it can be substituted directly as a `MultiFaultExample.rerun_fn`), but
  closing over a MUTABLE `current_values` map that starts as a copy of the
  faulty snapshot and is updated in place after every call with that round's
  freshly re-derived values (fix 1). Because the caller
  (`intro_specter.repair.rerun_downstream_subgraph_callable`, not modified
  here) still computes its `valid_prefix` argument via the untouched,
  step-id-ordered `split_valid_prefix`, this closure does not trust that
  argument's *zone* semantics -- it returns steps for every trajectory
  position NOT already covered by the given prefix, always rendered from the
  current (correct, evolving) value map, which structurally can never drop a
  step regardless of how the caller sliced its prefix (fix 2's practical
  effect: no more disappearing sibling-branch steps).

Nothing here is imported by, or imports for modification, `synthetic_dag.py`,
`repair.py`, `pipeline.py`, or `pipeline_experimental_cumulative_repair.py`.
"""

from __future__ import annotations

from collections.abc import Callable

from ..dag import descendants_of_node
from ..schemas import AssumptionDAG, AssumptionNode, Trajectory, TrajectoryStep
from .synthetic_dag import ComputeGraph

# ---------------------------------------------------------------------------
# Fix 2: descendant-based (not step_id-ordered) prefix/downstream split
# ---------------------------------------------------------------------------


def split_valid_prefix_fixed(
    trajectory: Trajectory, dag: AssumptionDAG, fault_node_id: str
) -> tuple[list[TrajectoryStep], list[TrajectoryStep]]:
    """Same contract as `intro_specter.repair.split_valid_prefix`: returns
    ``(prefix_steps, downstream_steps)``. Unlike that function, the split is
    by TRUE DAG descendant membership -- ``{fault_node_id} | descendants(fault_node_id)``
    -- never by comparing `step_id` against a threshold. Order-preserving
    within each returned list (matches the trajectory's original step order)."""
    affected_node_ids = {fault_node_id} | {n.id for n in descendants_of_node(dag, fault_node_id)}
    step_id_to_node_id = {n.step_id: n.id for n in dag.nodes}
    prefix = [
        s for s in trajectory.steps
        if step_id_to_node_id.get(s.step_id) not in affected_node_ids
    ]
    downstream = [
        s for s in trajectory.steps
        if step_id_to_node_id.get(s.step_id) in affected_node_ids
    ]
    return prefix, downstream


# ---------------------------------------------------------------------------
# Fix 1: evolving repaired-value map instead of a static snapshot
# ---------------------------------------------------------------------------


def make_rerun_fn_fixed(
    *,
    graph: ComputeGraph,
    profile_facts: dict[str, str],
    faulty_values: dict[str, str],
    gold_values: dict[str, str],
) -> Callable[
    [list[TrajectoryStep], AssumptionNode, AssumptionDAG],
    tuple[list[TrajectoryStep], str | None],
]:
    """Drop-in, fixed-harness replacement for
    `MealPlanningDomain.make_rerun_fn` (`synthetic_dag.py`, not modified).
    Same call signature so it can directly replace `MultiFaultExample.rerun_fn`.

    `current_values` starts as a COPY of `faulty_values` and is mutated after
    every call with that round's freshly re-derived values (via
    `ComputeGraph.re_execute`, whose own swap-zone computation is already
    fully DAG-structural through `ComputeGraph.downstream` -- unaffected by
    either bug). Every call therefore builds on whatever the previous call
    already repaired, instead of re-deriving "outside the swap zone" values
    from the original faulty snapshot every round.

    The returned `new_steps` cover every trajectory position NOT already
    present in the `valid_prefix` argument this closure receives (rendered
    from the up-to-date `current_values`), rather than only the swap node's
    true descendants -- this is what prevents unrelated sibling-branch steps
    from being silently dropped when the caller's own prefix computation
    (`intro_specter.repair.split_valid_prefix`, untouched, step_id-ordered)
    misclassifies them.
    """
    current_values: dict[str, str] = dict(faulty_values)

    def rerun(
        valid_prefix: list[TrajectoryStep],
        fault_node: AssumptionNode,
        dag: AssumptionDAG,
    ) -> tuple[list[TrajectoryStep], str | None]:
        new_values = graph.re_execute(
            prefix_values=current_values,
            profile_facts=profile_facts,
            swap_node_id=fault_node.id,
            swap_value=gold_values[fault_node.id],
        )
        current_values.update(new_values)
        prefix_step_ids = {s.step_id for s in valid_prefix}
        new_steps_all, final_output = graph.values_to_steps(current_values)
        new_steps = [s for s in new_steps_all if s.step_id not in prefix_step_ids]
        return new_steps, final_output

    return rerun


__all__ = ["make_rerun_fn_fixed", "split_valid_prefix_fixed"]
