# Camera-ready extra-page plan (post-acceptance only — do not use pre-acceptance)

## Policy (verified against NeurIPS 2026 Main Track Handbook, 2026-07-25)
> "If your submission is accepted, you will be allowed an additional content page for the camera-ready version." (9→10 pages total)
> "It is expected that you update the main paper in response to the reviewer comments and discussion."

This is the correct, sanctioned place for expanded content that doesn't fit in the 10,000-character rebuttal response — **but only after acceptance**. Nothing here gets used during the response period; the rebuttal period rule (no paper/supplementary revisions) still applies until a decision is made.

## What goes in the extra page
1. **Non-synthetic-profile results** (in progress, see `orchestration/non_synthetic_experiment_*`): real, un-injected native constraints (TravelPlanner-real's genuine HF-dataset budget/dietary/date constraints, fault-injection disabled) vs. Reflexion — the honest "how far does this generalize beyond templated profiles" data point Mahh's W1 objection asks for.
2. **Multi-fault reasoning at scale** (in progress, see `orchestration/experiment_d_fault_sweep_real`): the real N=2/3/4 (and 5/6 if feasible — investigating) Reflexion-vs-Intro-Specter comparison, already showing a real, statistically significant, growing advantage for Intro-Specter from N=3 onward (86.7/87.8% tied at N=2; 77.2/91.7% and 70.6/91.1% at N=3/4, both p<0.0001).
3. **Token cost accounting** for all of the above, consolidated (see `orchestration/token_cost_summary.md`, being assembled).

## Framing note for the rebuttal text (now, during response period)
Do NOT include the actual extra-page content in the rebuttal response itself (10k char limit, and results are still landing). DO include a brief, honest forward-reference: something like "we are continuing this line of investigation (non-synthetic-profile settings, higher fault counts) and will incorporate results in the camera-ready version's additional content page, as explicitly provided for by the venue." This is honest (true), appropriately scoped (doesn't claim results we don't have yet), and shows good faith engagement without overclaiming inside the response's character limit.
