# Response to Reviewer LDZz (draft — grounded directly in paper_final.tex)

We thank the reviewer for these two points and address both directly.

**On Figure 1's apparent cycles:** the Assumption-DAG is constructed to be acyclic by design — cycles are actively detected during extraction and resolved by removing the edge with the lowest endpoint-node confidence (§2.1), so the graph itself never contains one. What Figure 1 additionally draws are the counterfactual repair trial arrows from step (4) — these trace *backward* from a candidate assumption to the evidence used to score it, and are visually distinct in intent from the forward dependency edges from step (3), but we agree they can read as cycles at a glance if the two arrow types aren't clearly differentiated. We will redraw Figure 1 for the camera-ready version with distinct arrow styles (e.g., solid for dependency edges, dashed for attribution/scoring arrows) to remove the ambiguity.

**On handling multiple violations:** this is already specified in Appendix A (Implementation notes) and depicted directly in Figure 1 itself, though we agree it deserved more visibility in the main text. The current implementation handles multiple simultaneous violations via a sequential single-node pass: after repairing the top-scoring candidate $a^\star$, re-verification checks for any residual violation, and if one remains, a second single-node repair is triggered against the next candidate. Figure 1's worked example shows this directly — step (4) resolves $a_4$ first, and a residual violation triggers a second pass resolving $a_7$. We will move this sentence from the appendix into the main method section (§2) for camera-ready, since it answers a question the current organization leaves implicit.

---
## Editor's notes (not for submission — delete before posting)
- Grounded directly against `paper_final.tex`: the DAG's cycle-resolution mechanism (line 68, "$G=(A,E)$... Cycles, when detected, are resolved by removing the edge with the lowest endpoint-node confidence"), Figure 1's actual caption text (line 113, "the algorithm proceeds via sequential single-node repair, with re-verification detecting residual violations between passes (here resolving $a_4$ then $a_7$)"), and Appendix A's implementation note (line 398, same sequential single-node-pass description). No fact in this draft is asserted from memory.
- Character count: ~1,650 chars. Well under the 10,000 limit.
- No placeholders — this response has zero dependency on P0/P1/P2, exactly as scoped in the plan.
