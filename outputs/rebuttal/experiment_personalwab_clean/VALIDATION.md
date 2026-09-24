# Track P clean PersonalWAB validation

Validated 2026-09-22 from the completed clean outputs only. The historical
contaminated tree remains preserved separately at
`outputs/rebuttal/experiment_personalwab/`.

- Models included: `llama-3.1-8b`, `mistral-nemo-12b` (Qwen intentionally excluded)
- Arms per model: 5
- Rows per arm: 180 = 60 task IDs × 3 seeds (`0,1,2`)
- Rows per model: 900
- Total rows: 1,800 across 10 cells
- JSONL parsing: PASS for all rows
- Duplicate `(task_id, seed, arm)` rows: 0
- Missing cells: 0
- Task identity: the same 60 task IDs and three seeds are present in every cell
- Clean D7 dataset SHA-256: `017093dcd799d56f7f2c7330b7c7a80cdbaa8be388311f60a56bb26445d00fcc`
- Target-ASIN leakage: PASS; fail-closed check found 0 leaks across all 60 sampled tasks
- Completed-row/provider errors: none; every completed arm log ended with `errors: 0`

Aggregate tables are in [`SUMMARY.md`](SUMMARY.md).
