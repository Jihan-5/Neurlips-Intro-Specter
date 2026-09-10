We thank the reviewer for a careful review. We treat the central concern — that the synthetic, single-fault construction may drive the reported gains — as two requirements: **(1)** robustness beyond the original construction and **(2)** evaluation on real user data. New experiments for both (~140k trajectories, eight dataset-conditions × four LLMs; exact McNemar + paired bootstrap; per-example artifacts released); W2 and W3 answered directly below.

**1. The gains survive — and grow — under harder versions of the construct (W1).** We extended injection to N=2–5 *simultaneous* faults per example (one factual context distractor + N−1 independent profile-constraint corruptions; dataset-native multi-hop fact corruptions where structure permits). Pooled over N=2–5, four LLMs, seven methods:

| Success (%) | Direct | Reflexion (best baseline) | Ours |
|---|---|---|---|
| 2WikiMultiHop | 65.5 | 71.5 | **78.6** |
| HotpotQA | 62.9 | 71.6 | **81.4** |
| MuSiQue | 54.5 | 57.2 | **62.4** |
| LongMemEval | 48.8 | 57.7 | **65.3** |
| TravelPlanner (profile-injected) | 34.0 | 32.6 | **36.6** |

Ours leads all six baselines on all five datasets, and the margin *widens* as faults stack:

| Ours vs Reflexion by fault count | N=2 | N=3 | N=4 |
|---|---|---|---|
| HotpotQA | 84.8 / 84.1 | 79.9 / 68.3 | 79.6 / 62.3 |
| LongMemEval | 73.9 / 71.7 | 66.0 / 57.9 | 56.1 / 43.6 |
| 2WikiMultiHop | 91.7 / 89.9 | 86.7 / 79.6 | 87.5 / 74.4 |

Saturation tiers are reported: when *every* fact in one chain is corrupted at once (2Wiki N=5, MuSiQue N=4–5), all seven methods converge to ties — included, not omitted. The paper's +1.6pp pooled figure averages over cells at or near saturation ceiling; the multi-fault tiers above are the same method measured where headroom exists.

**2. Real user profiles — the reviewer's core ask (W1).** On PersonalWAB (WWW'25): 1,000 users with behavior-grounded profiles from real histories — real purchases, ratings, reviews (the benchmark's profiles are simulated over these real behaviors, which we state as such); ground truth is the item the real user genuinely interacted with (hit@1 over a 20-candidate real-product slate). Three LLMs × 180 paired × 5 arms, including a *budget-matched* iterative control:

| Pooled, 540 paired units | Success (%) | Discordant (ours-win/loss) | exact McNemar p |
|---|---|---|---|
| Direct | 93.2 | 26 / 0 | $3.0{\times}10^{-8}$ |
| VRP (single-round) | 94.6 | 18 / 0 | $7.6{\times}10^{-6}$ |
| Iter-VRP (matched budget) | 95.2 | 18 / 3 | 0.0015 |
| Reflexion | 96.3 | 12 / 3 | 0.035 |
| **Ours** | **98.0** | — | — |

Against Reflexion this is a **46% relative error reduction** (3.7%→2.0% error) — significant against every baseline despite ceiling effects, at fewer mean rounds than the matched-budget control (1.04 vs 1.15). Per-model: Qwen-7B 96.7 vs Reflexion 93.3 (6/0 discordant, p=0.031); Mistral-Nemo 97.8 vs 96.7 (significant vs Direct/VRP; NS vs Reflexion); Llama-8B ceiling-compressed (99.4 vs 98.9). Every discordant count across all three models favors ours. Disclosed: rates are near ceiling (real profiles are a strong signal); our scorer replicates the benchmark's ASIN-containment criterion at hit@1 rather than its trained-recommender top-10; the ground-truth interaction is excluded from visible history to prevent leakage.

**3. Real-field corruption (beyond templates).** We corrupted *real fields of real records*, scored against true values. Because our Reflexion implementation has an output-coercion defect on a fraction of Llama-3.3-70B rows in these two conditions (row counts in the appendix), the table below *excludes* that model for both methods — the conservative basis (inclusion favors us):

| Success (%) | Direct | Reflexion | Ours |
|---|---|---|---|
| Food.com Recipes — real prep-time/calories/servings, N=1–5 | 42.5 | 57.0 | **58.2** |
| TravelPlanner native — real budget/days/cuisine/rules, N=2–5 | 24.0 | **40.5** | 32.8 |

Recipes: a statistical tie — ours ahead at N=1 (93.9/93.0) and ~2× more robust at the extremes (N=4: 16.6/12.3; N=5: 19.4/8.6), behind at N=2–3 (88.6/90.3; 48.5/56.5). TravelPlanner-native: Reflexion leads; we report it as a loss, with two details: (a) its 23.2pp single-fault advantage narrows to 7.7pp under multi-fault on this basis (4.0pp with all models included) — the regime the paper was criticized for not testing is where the gap narrows most; (b) per-constraint (full data), ours leads on localizable slots (house-rule 81.0 vs 76.0; budget 69.6 vs 66.2) and trails on globally-cascading ones (day-count 64.1 vs 75.5). *Including* the defect-affected model gives Recipes 59.6 vs 55.4 and TravelPlanner 37.8 vs 41.8 — conclusions (tie; loss) unchanged either way. The defect does not materially manifest in the main 16-cell matrix (zero empty rows in fifteen of sixteen cells; 4/60 in LongMemEval×Llama-70B, a cell already reported as a loss, which correction could only deepen — no reported win is affected); it is documented in the released code.

**4. Scope — when and why it wins (Q1).** One characterization fits every result above: the advantage requires **at least one uncorrupted anchor** — a clean evidence span, untouched constraint, or genuine user history — against which counterfactual attribution validates a repair (Eq. 1–2 score a repair by whether it removes the violation *while remaining consistent with everything else believed*). Single faults, stacked independent faults, real numeric constraints, and rich real histories satisfy this; those are the settings where ours is strongest. Globally-cascading constraints satisfy it partially (gap narrows to parity). An adversarial stress test corrupting *all* identity-defining fields of a product at once — deliberately leaving no anchor — behaves exactly as predicted (full regeneration is the right tool there); complete results are in the released artifacts and will appear in the appendix. The revision states this envelope as a falsifiable scope claim rather than unqualified superiority.

**5. Profile immutability under noise (W3), including the structural question.** We corrupted the *profile itself* (stale swaps, contradictions, omissions) at $\rho=0.10$/$0.30$: ours remains ahead of Reflexion at both (82.1 vs 79.7; 76.1 vs 73.6 true-success, ~70 paired/cell). On the sharper structural reading — a noisy profile means the true fault may *be* a profile node, which our candidate set excludes — the mechanism reaches it indirectly: profile *spans* are immutable, but the *derived belief nodes* extracted from them carry model provenance and are admissible candidates, so the method repairs the downstream belief without editing the span — consistent with the persistence of the advantage under noise above. The direct instrument — admitting profile nodes to $C(v;G)$ under noise and measuring how often one is selected — is cleaner; it requires a change to candidate generation, and we commit to it as a camera-ready ablation alongside richer noise models.

**6. Do assumption-driven failures occur naturally?** Tested directly: 150 genuinely un-injected examples (no profile), every failure inspected. Honest answer: organic failures are wrong-fact/wrong-hop errors — with no stated profile there is no user assumption to violate; the construct exists only where user-conditioning exists, which is why PersonalWAB is the right venue. We concede: attribution accuracy remains validated on synthetic diagnostics only (Appendix E); human fault annotation on real trajectories, with inter-annotator agreement, is camera-ready work no existing dataset supplies.

**7. Cost.** Mean tokens per example, Reflexion÷ours: TravelPlanner-native 1.95×, product stress test 1.63×, Recipes 1.54×, TravelPlanner-injected 1.37×, LongMemEval 1.32×, HotpotQA 1.07× — cheaper on six of eight conditions; Reflexion is cheaper on 2Wiki (0.81×) and MuSiQue (0.84×). No blanket claim.

**8. What is new (W2).** The ingredients are familiar; the contribution is the closed loop between them, which none of the cited systems form. RAFFLES localizes faults but terminates in a judgment — no edit-cost model, no re-execution, no round conditioned on the first repair's outcome. ContextWeaver builds a dependency graph over interaction history, but the graph is memory, not a hypothesis space — no attribution objective is defined on it. Theorem-of-Thought propagates belief over a reasoning graph, but its updates are not interventional — nothing scores a node by executing a counterfactual change and testing whether the violation disappears. Ours is the only formulation in which (i) the likelihood proxy is repair execution itself (Eq. 1), (ii) that score selects the repair point traded against downstream edit cost (Eq. 4), and (iii) verifier rejection re-enters as evidence on the same posterior in closed form (Eq. 5) rather than as a fresh critique. The paper's ablations show the loop is load-bearing: Table 8 reports −2.8pp without the DAG and −3.1pp with uniform priors; Table 10 shows disabling SPR drops pooled success from 87.0 to 84.3 — *below* Reflexion. A pipeline of the cited parts does not produce that; the coupling does. The Iter-VRP control (also an arm on PersonalWAB above, 98.0 vs 95.2, p=0.0015) confirms this experimentally at matched retry budget.

These are not conditional offers. The multi-fault results (§1) become §4.6 with full tables in a dedicated appendix; PersonalWAB (§2) becomes §4.7 with per-model tables in a dedicated appendix; real-field corruption (§3) joins Appendix I alongside the existing TravelPlanner results; the operating envelope (§4) becomes a named subsection of §6, replacing the current construct-shift paragraph; and the Iter-VRP control retires the "we did not run it" caveat in §4.4 and §6. The profile-node candidate-set ablation (§5) is the one item not yet run, and we commit to it explicitly. All data, code, and per-example artifacts are released. We hope these experiments and clarifications answer the reviewer's concerns.
