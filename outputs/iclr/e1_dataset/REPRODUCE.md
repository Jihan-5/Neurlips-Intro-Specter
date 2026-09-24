# Reproduce the coordinator deliverables

Run from the repository root with the existing `.venv`. Frozen inputs are read only. All preparation outputs are private diagnostics until Jihan resolves attention eligibility.

```sh
.venv/bin/python -B scripts/e1_finalize_human.py
.venv/bin/python -B scripts/e1_prediction_inventory.py
.venv/bin/python -B scripts/e1_attribution_vs_human.py --consensus outputs/iclr/e1_dataset/private/finalization/consensus_pending.json --predictions outputs/iclr/e1_dataset/private/finalization/prediction_inputs.json --output outputs/iclr/e1_dataset/private/finalization/attribution_readiness.json
.venv/bin/python -B scripts/aggregate_personalwab.py --root outputs/rebuttal/experiment_personalwab_clean --models llama-3.1-8b,mistral-nemo-12b --require-complete --output outputs/rebuttal/experiment_personalwab_clean/SUMMARY.md
.venv/bin/python -B scripts/aggregate_personalwab.py --root outputs/rebuttal/experiment_personalwab_clean --models llama-3.1-8b,mistral-nemo-12b --require-complete --pooled-only --output outputs/rebuttal/experiment_personalwab_clean/POOLED_SUMMARY.md
.venv/bin/python -B scripts/verify_jazz_finalization.py
.venv/bin/pytest -q tests/test_e1_finalization.py tests/test_e1_annotation_pipeline.py
```

After Jihan's actual adjudication download exists, pass `--adjudications PATH` to `e1_finalize_human.py`. It accepts partial downloads but retains unresolved statuses. It rejects duplicate/unexpected IDs, invalid labels and non-Jihan adjudicators, preserves agreed components, and never changes raw labels. Both exclusions still apply: a future recorded eligibility resolution must be implemented according to Jihan's actual disposition, not inferred from the existence of adjudication labels.

`e1_attribution_vs_human.py --help` defines the artifact schema. `prediction_inputs.json` contains only the 85 exact blinded-item hashes, **no method or judge predictions**. Populate from actual outputs tied to those displayed final traces. Supply top-1 steps, ranked steps, optional category, failed-step location, and one step mapping per ancestor node; include the recorded fixed judge-model/prompt reference. The 15 historical source-arm fault nodes and their DAGs are not a full same-trace comparison; none of the frozen trace exports contains rankings. Do not substitute another arm's prediction or rank the selected node first by assumption. The prereg's judge model/prompt freeze record is absent: Jihan must supply or resolve that omission before any judge run. No new protocol is selected here.

The scorer reports all three floors, coverage/missing IDs, unresolved/category exclusions, exact and ±1 binomial 95% CIs, category agreement where emitted, MRR, and `e1_attribution_accuracy.csv`. Random-ancestor values are analytic expectations, not binomial counts. Incomplete coverage cannot yield a FINAL result. CIs are Clopper–Pearson; Track P uses exact paired McNemar plus percentile paired bootstrap (10,000 resamples, seed 0, 95%, pairs include model/task/seed).

Package to a new destination (existing directories are rejected to prevent stale mixtures):

```sh
.venv/bin/python -B scripts/e1_package_dataset.py --output-dir outputs/iclr/e1_dataset/private/draft_package
```

`--release --metrics PATH` additionally requires eligible resolved consensus and FINAL attribution results; currently this correctly fails. No public release or adjudication answer is synthesized. To repeat draft packaging, choose a new output directory.

Completed earlier E/F experiments are not rerun. Their receipts and source digests are in `private/finalization/validation.json`. All output artifacts move only through the safe artifact transport; the normal branch/worktree is not reset, committed or pushed.
