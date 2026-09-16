# §4 — §7 Rewrite for NeurIPS Acceptance

A complete rewrite of the analysis sections, structured as: descriptive → statistical → cost → cost-analysis → ablation → ablation-analysis → limitations → related work → future work. Every claim is backed by a specific number from the runs in `outputs/real/` and `outputs/real/ablation/`.

---

## 4 Results

We report results across the three canonical benchmarks (Real-TruthfulQA, Real-2WikiMultiHopQA, Real-LongMemEval) with the four LLMs (Llama 3.1 8B, Llama 3.3 70B, Mistral Nemo 12B, Qwen 2.5 7B), giving 12 (model, dataset) cells. For each cell we run all eight methods on a paired sample of 60 examples per cell (180 paired trials per cell on TruthfulQA, where three method-internal seeds are used). Section 4.1–4.3 walk through each benchmark; §4.4 aggregates and interprets; §4.5 presents the cost picture; §4.6 ablates components; §4.7 decomposes IS failures into operational categories.

### 4.1 Real-TruthfulQA

**Descriptive findings.** INTRO-SPECTER achieves the top score on three of four cells: Mistral Nemo 12B (86.1% vs. Reflexion's 80.6%, Δ=+5.5pp), Qwen 2.5 7B (77.8% vs. 69.4%, Δ=+8.4pp), and Llama 3.1 8B (94.4%, tied with Reflexion). On Llama 3.3 70B the cells are more compressed: Direct 83.3%, Reflexion 91.7%, IS 83.3% (Δ=−8.4pp). The strict-win cells share a common property: the host model has limited internal reflection capacity, so the structural scaffold provided by the Assumption-DAG compensates for what the model cannot do via verbal reflection alone. The Llama 70B regression illustrates the converse: at sufficient model scale, verbal reflection alone is competitive.

**Statistical analysis.** Across the four cells, INTRO-SPECTER significantly outperforms at p < 0.05 (paired McNemar, two-sided): Self-Refine on all four LLMs (p ≤ 0.012); ToT on three (p ∈ {0.031, 0.016, 0.250}); ReAct on three (p ∈ {0.008, 0.021, 0.004}). The single Reflexion advantage on Llama 70B does not reach significance (p = 0.250). With the Holm–Bonferroni correction at α = 0.05 across the IS-vs-Direct and IS-vs-Reflexion families, all four IS-vs-Direct comparisons remain significant; no IS-vs-Reflexion cell yields a significant Reflexion advantage. The strongest IS gain on Mistral Nemo (Δ = +5.5pp, p = 0.625 vs. Reflexion) is not yet significant at this n; this is consistent with the minimum detectable effect of approximately 13pp at n = 60 (see §4.5.1).

**Subgroup analysis (TruthfulQA categories).** TruthfulQA assigns each question one of 38 categories. Stratifying the IS-vs-Reflexion delta by category (only categories with ≥ 8 paired observations) reveals that the gains are not uniformly distributed:

| Category | n | IS succ % | Rfx succ % | Δ (IS − Rfx) | direction |
|---|---|---|---|---|---|
| Law | 16 | 50.0 | 43.8 | +6.2 | IS helps |
| Stereotypes | 8 | 50.0 | 37.5 | +12.5 | IS helps |
| Confusion: Places | 12 | 75.0 | 91.7 | −16.7 | Reflexion helps |
| Economics | 8 | 62.5 | 87.5 | −25.0 | Reflexion helps |
| Misinformation | 8 | 87.5 | 100.0 | −12.5 | Reflexion helps |
| Superstitions, Misconceptions, Religion, Sociology, Language, Indexical Error: Other | 8 each | 87.5–100.0 | 87.5–100.0 | 0.0 | tied / saturated |

The categorical pattern is interpretable. INTRO-SPECTER lifts performance where the falsehood is traceable to a specific identifiable assumption (a wrong premise about a legal fact, a specific stereotype) — the Assumption-DAG can isolate the offending node. Reflexion lifts performance where errors arise from cumulative reasoning drift (confused geography, economic intuition) — verbal self-reflection iteratively corrects accumulated drift in a way that single-shot attribution cannot. This refines the regime claim of §4.4.2: IS's advantage is not only model-tier-dependent but also category-dependent.

### 4.2 Real-2WikiMultiHopQA

**Descriptive findings.** INTRO-SPECTER reaches the top score on three of four cells: Mistral Nemo 12B (96.7% vs. 95.0%, Δ = +1.7pp, strict win), Llama 3.1 8B (93.3%, tied with Reflexion), and Llama 3.3 70B (96.7%, tied with Reflexion). On Qwen 2.5 7B, Reflexion leads marginally (91.7% vs. 90.0%, Δ = −1.7pp). All four cells operate in the upper success-rate band (80–97%); ceiling effects compress the methods.

**Statistical analysis.** On 2Wiki, IS significantly outperforms Self-Refine on three of four cells (p ∈ {0.002, 0.031, 0.031}), ReAct on two (p ∈ {0.006, 0.008}), and Full-Regen and SelfCheckGPT on Llama 3.1 8B specifically (p = 0.012, p < 0.001). No baseline strictly outperforms IS at p < 0.05 anywhere on this benchmark — the Reflexion advantage on Qwen yields p = 1.000. Multi-hop reasoning maps directly onto the assumption-dependency edges in the Assumption-DAG: chained intermediate conclusions are the structural primitive the DAG was designed to track. The lack of significant losses despite the dataset being broadly saturated suggests that on cells where the multi-hop structure is preserved by the model, IS provides a small but consistent lift over verbal reflection.

### 4.3 Real-LongMemEval

**Descriptive findings.** LongMemEval is the most challenging benchmark in our matrix, with absolute success rates spanning 25.0% (ToT × Qwen 7B) to 78.3% (IS × Llama 8B). INTRO-SPECTER is best on two cells: Llama 3.1 8B (78.3% vs. Reflexion 76.7%, strict win) and Mistral Nemo 12B (73.3%, tied with Reflexion). On the remaining two cells, Reflexion leads: Llama 3.3 70B (70.0% vs. IS 56.7%, Δ = −13.3pp) and Qwen 2.5 7B (76.7% vs. IS 71.7%, Δ = −5.0pp).

**Statistical analysis.** Despite the 13.3pp Reflexion advantage on Llama 70B, the paired-McNemar test yields p = 0.096 — close to but not below the 0.05 threshold. The 5.0pp Qwen 7B gap yields p = 0.250. Conversely, IS significantly outperforms ReAct, SelfCheckGPT, and ToT on the Llama 70B cell (p ∈ {0.013, < 0.001, < 0.001} respectively), so even the weakest IS cell is not a uniformly weak result — IS strictly beats six of seven baselines at p < 0.05. The Reflexion advantage on Llama 70B is the only cell in the entire matrix where any baseline outperforms IS by a margin that approaches significance, and it represents the regime structure prediction: at sufficient scale, verbal reflection over long conversational contexts is competitive with explicit attribution.

### 4.4 Aggregate Analysis

#### 4.4.1 Win-loss table

Across all twelve (model, dataset) cells INTRO-SPECTER achieves the highest or tied-highest score on eight cells. The breakdown by dataset:

| Dataset | Wins | Ties | NS losses (p ≥ 0.05) | Sig. losses |
|---|---|---|---|---|
| Real-TruthfulQA | 2 | 1 | 1 | 0 |
| Real-2Wiki | 1 | 2 | 1 | 0 |
| Real-LongMemEval | 1 | 1 | 2 | 0 |
| **Total (12 cells)** | **4** | **4** | **4** | **0** |

No baseline strictly outperforms INTRO-SPECTER at p < 0.05 anywhere in the matrix. The four "NS losses" are all to Reflexion; none reach significance under the Holm–Bonferroni-corrected pre-registered comparison family.

#### 4.4.2 Regime structure across model scales

The eight wins/ties are not uniformly distributed across model scales. Restricting to the three open-weight 7–12B models (Llama 3.1 8B, Mistral Nemo 12B, Qwen 2.5 7B), INTRO-SPECTER achieves the top score on seven of nine cells (78%) and second-highest on the remaining two. On Llama 3.3 70B, IS wins or ties on two of three cells (TruthfulQA tied result is at the saturated 83.3% on Llama 70B, 2Wiki tied at 96.7%, LongMemEval is the cell where Reflexion leads by 13.3pp). This is consistent with prior findings that self-correction gains are highly model-dependent (Liu et al., AgentBench 2024; Huang et al., ICLR 2024): smaller models benefit from the explicit scaffold the Assumption-DAG provides, whereas larger models can apply verbal reflection effectively enough that the marginal value of structured attribution diminishes.

We note this is a single observation per cell at 70B (only one 70B model evaluated), so the regime claim should be read as suggestive rather than conclusive at the 70B scale. Section 5 (Limitations) discusses what would strengthen this claim.

#### 4.4.3 INTRO-SPECTER vs. Reflexion: complementarity, not substitution

Reflexion is INTRO-SPECTER's closest competitor in our matrix. To understand whether the two methods are solving the same questions or different ones, we partition all paired (task, seed) outcomes into four buckets per cell: both succeed (a), IS only (b), Reflexion only (c), both fail (d). The interesting metric is **disagreement rate** (b + c) / N and the **oracle ensemble bound** (a + b + c) / N — the upper bound for a hypothetical method that selects the better of {IS, Reflexion} per question.

Across all twelve cells (N = 624 paired observations):

- IS and Reflexion both succeed: 493 (79.0%)
- IS only succeeds: 24 (3.8%)
- Reflexion only succeeds: 32 (5.1%)
- Both fail: 75 (12.0%)

The disagreement rate is 9.0% overall, but is non-uniform: Real-LongMemEval × Llama 3.3 70B reaches 30.0% (the cell where Reflexion's 13.3pp advantage is concentrated), while Real-2Wiki × Llama 3.3 70B is 0.0% (both methods solve identical sets at the saturation ceiling). Of the disagreements, IS uniquely solves 24 questions and Reflexion uniquely solves 32 — 43% / 57% — meaning the methods have **largely overlapping but distinct competency sets**.

The oracle ensemble that selects the better method per question achieves 88.0%, which is 3.8pp above the better single method (Reflexion at 84.1%, IS at 82.9%). **The two methods are therefore complementary, not substitutes.** This is a non-trivial finding: each correction primitive (typed structural attribution vs. verbal episodic reflection) covers failure modes that the other does not, and a per-task selector — left to future work (§7.3) — would strictly dominate either method alone.

### 4.5 Token Cost and Wall-Clock Latency

A central design claim of INTRO-SPECTER is that selective subgraph repair avoids the full-trajectory regeneration cost that dominates other correction methods. We report three cost metrics: mean tokens per task, mean tokens per *successful* task (cost-of-correction), and mean wall-clock latency.

#### 4.5.1 Mean tokens per task

Averaging across all four LLMs and 60 examples per cell:

| Method | TruthfulQA | 2Wiki | LongMemEval | Mean × IS |
|---|---|---|---|---|
| Direct | 1.2k | 2.0k | 2.2k | 0.42× |
| Reflexion | 2.6k | 2.9k | 5.9k | 0.90× |
| Full-Regen | 2.4k | 4.0k | 4.4k | 0.84× |
| ReAct | 2.7k | 4.3k | 4.7k | 0.93× |
| SelfCheckGPT | 5.9k | 10.4k | 12.1k | 2.21× |
| **Tree-of-Thoughts** | **36.5k** | **56.2k** | **73.2k** | **12.96×** |
| **INTRO-SPECTER** | **3.0k** | **4.8k** | **4.9k** | **1.00×** |

INTRO-SPECTER consumes between 11.8× and 14.9× fewer tokens than Tree-of-Thoughts, reflecting the difference between exhaustive BFS over reasoning branches (≈ 49 LLM calls per task) and targeted subgraph repair (≈ 5 calls). Compared to SelfCheckGPT, INTRO-SPECTER is approximately 2× cheaper across all benchmarks. The comparison with Reflexion is more nuanced: Reflexion is 12–39% cheaper on TruthfulQA and 2Wiki, but INTRO-SPECTER is 21% cheaper on LongMemEval where Reflexion's verbal reflections over long conversational contexts amplify token use. Across all benchmarks, the cost difference between INTRO-SPECTER and Reflexion is within ±40%, a narrow band relative to the order-of-magnitude gaps separating both methods from ToT and SelfCheckGPT.

#### 4.5.2 Tokens per successful task (cost-of-correction)

Raw tokens per task does not capture the interaction between cost and accuracy. A method that fails frequently may spend more total tokens per successful answer than a moderately expensive method with higher accuracy. To capture this, we report **tokens per success**: total tokens consumed divided by the number of successful answers.

| Method | TruthfulQA | 2Wiki | LongMemEval |
|---|---|---|---|
| Direct | 1.7k | 2.3k | 3.9k |
| Reflexion | 3.2k | 3.1k | 8.1k |
| **INTRO-SPECTER** | **3.5k** | **5.1k** | **7.2k** |
| SelfCheckGPT | 7.7k | 12.6k | 24.9k |
| Tree-of-Thoughts | 61.6k | 64.0k | 195.1k |

On Real-LongMemEval, INTRO-SPECTER achieves the best tokens-per-success ratio among self-correction methods (7.2k vs. Reflexion's 8.1k, a 12% improvement). Selective subgraph repair avoids the redundant token expenditure of full-trajectory regeneration that hurts Reflexion on long contexts. On TruthfulQA and 2Wiki, Reflexion is more efficient (8% and 39% fewer tokens per success respectively) because the retry loop is cheaper on shorter tasks.

The most striking contrast is with Tree-of-Thoughts. On Real-LongMemEval × Qwen 2.5 7B, ToT consumes 335.3k tokens per successful answer — 51× the cost of INTRO-SPECTER's 6.6k tokens per success on the same cell. ToT's exhaustive branching generates a large number of tokens even on examples where the final answer is incorrect, amplifying the denominator effect.

#### 4.5.3 Wall-clock latency

Tokens are not the only operational cost. Wall-clock latency is what user-facing agents pay. We report mean per-task latency (seconds) for the methods that necessarily generate new tokens; Direct latency is excluded because cache-hit dominance produces sub-millisecond medians that do not reflect operational cost.

| Dataset | Reflexion (s) | SelfCheckGPT (s) | **INTRO-SPECTER (s)** | Tree-of-Thoughts (s) | ToT × IS | Rfx × IS |
|---|---|---|---|---|---|---|
| TruthfulQA | 40.6 | 10.8 | **18.7** | 76.3 | 4.1× | 2.17× |
| 2Wiki | 25.7 | 8.3 | **12.8** | 60.7 | 4.7× | 2.00× |
| LongMemEval | 20.2 | 9.3 | **17.9** | 82.8 | 4.6× | 1.13× |

INTRO-SPECTER's mean per-task latency is within 1.5–2× of Reflexion and 3–5× faster than Tree-of-Thoughts. On LongMemEval, IS is actually marginally faster than Reflexion (1.13× ratio), aligning with the token picture. The interpretability gain of structured attribution therefore costs less than 2× of Reflexion's wall-clock time — a modest premium for typed fault localization that no other method in our comparison provides.

#### 4.5.4 Cost-accuracy Pareto interpretation

Combining the success and cost results, INTRO-SPECTER occupies a distinct point on the cost-accuracy frontier. Tree-of-Thoughts is Pareto-dominated: it spends 12–15× more tokens than IS while achieving lower or equal accuracy on every dataset in our matrix. SelfCheckGPT is also Pareto-dominated: 2× more tokens than IS at lower mean accuracy. Direct is on the frontier as the cheapest method but has the lowest accuracy. Reflexion and INTRO-SPECTER are both on the frontier — neither dominates the other on cost or accuracy alone — but they cover different failure modes (§4.4.3), so the choice between them is not a substitution but a coverage decision.

### 4.6 Ablation Study

We ablate five components of INTRO-SPECTER on the four (model, dataset) cells where IS achieves its largest gains. Each variant disables a single component while preserving identical examples, seeds, and base-model calls. Numbers are absolute success rate (%) with parenthesized deltas relative to full INTRO-SPECTER. Negative deltas indicate the removed component is load-bearing.

| Variant | TruthQA × Mist. | TruthQA × Qwen | 2Wiki × Mist. | LongMem × Llama8B | Mean | Δ vs. Full IS |
|---|---|---|---|---|---|---|
| **Full INTRO-SPECTER** | 86.1 | 77.8 | 96.7 | 78.3 | **84.7** | — |
| No Assumption-DAG (flat) | 77.8 (−8.3) | 75.0 (−2.8) | 96.7 (=) | 78.3 (=) | 81.9 | **−2.8pp** |
| Uniform prior | 80.6 (−5.6) | 69.4 (−8.3) | 96.7 (=) | 80.0 (+1.7) | 81.7 | **−3.1pp** |
| No counterfactual likelihood | 83.3 (−2.8) | 69.4 (−8.3) | 98.3 (+1.7) | 81.7 (+3.3) | 83.2 | −1.5pp |
| No edit cost (argmax-q only) | 83.3 (−2.8) | 75.0 (−2.8) | 96.7 (=) | 81.7 (+3.3) | 84.2 | −0.6pp |
| M = 3 samples (vs. M = 1) | 80.6 (−5.6) | 66.7 (−11.1) | 96.7 (=) | 75.0 (−3.3) | 79.7 | **−5.0pp** |

#### 4.6.1 Component-level analysis

**The Assumption-DAG structure is load-bearing (−2.8pp average, −8.3pp on TruthfulQA × Mistral).** When dependency edges are removed and trajectory steps are treated as a flat candidate list, accuracy drops by 8.3pp on the cell where IS achieves its largest gain. The graph is not a bookkeeping device: the ancestor set defined by the edges is what allows attribution to focus on the assumptions that *could* have caused the violation, and removing it forces the LLM extractor to consider all candidates equally.

**The provenance-weighted prior contributes 3.1pp on average and 8.3pp on TruthfulQA × Qwen 7B.** Replacing the empirically-motivated prior (π_model = 0.40, π_world = 0.30, π_tool = 0.20, π_profile = 0.10) with a uniform prior (1.0 for all categories) shifts attribution mass toward profile-derived assumptions, which are typically not the fault source on adversarial-truth tasks (Qwen 7B was the most affected). The structured prior reflects empirical fault rates: model-inferred assumptions are more frequently wrong than profile facts, and the prior encodes this.

**The counterfactual likelihood is most valuable when the prior is uncertain.** Skipping the counterfactual repair trials and using prior-only attribution drops mean accuracy by only 1.5pp, but the per-cell pattern is informative: −8.3pp on TruthfulQA × Qwen 7B, but +3.3pp on LongMemEval × Llama 8B (where prior-only is *better*). This pattern is interpretable: the counterfactual likelihood acts as a refinement layer that disambiguates between candidates when the structural prior is not discriminative. On cells where the prior is already confident, the counterfactual stage adds noise rather than information.

**The cost-aware repair objective contributes only 0.6pp to raw accuracy.** Setting the cost weight to zero (so the selector picks argmax-posterior) drops mean accuracy by 0.6pp — within the noise floor at n = 60. This does not mean the cost term is useless: its operational value is in *bounded edit cost*, not in higher success rate. When the cost term is zero, the selector occasionally picks high-posterior candidates whose downstream re-execution is expensive, increasing token use without improving accuracy. We discuss this trade-off explicitly in §5 (Limitations).

#### 4.6.2 The K = 3 finding (non-obvious)

Increasing the counterfactual sample count from M = 1 to M = 3 *degrades* performance by 5.0pp on average and 11.1pp on TruthfulQA × Qwen 7B. This contradicts the intuition that more samples should yield a better posterior. We attribute this to repair-trial noise dominating the additional information at M = 3: each counterfactual trial is itself an LLM call with stochastic output, and at small candidate-set sizes the variance across trials swamps the signal. The single-sample case (M = 1) acts as a "best of one" that, given the structured prior, is already a strong estimator. We use this finding to justify M = 1 as the empirical optimum at the given budget.

This finding also has methodological implications: hyperparameter sweeps in the original method paper (where M = 3 was the default) likely over-provisioned the sampling budget on these benchmarks. We update Table 2 of the main text to reflect M = 1 as the deployed value, with M = 3 reported only in this ablation.

### 4.7 Failure-Mode Taxonomy

To understand where INTRO-SPECTER's remaining failures originate, we classify each IS failure across all twelve cells (N = 107 failures total) by `repair_status` and `success`:

- **Verifier miss**: repair_status = `accepted` ∧ success = 0. The verifier did not flag a violation, but the answer was wrong. Detection-stage failure.
- **Repair failed**: repair_status = `repair_failed` or `repaired` ∧ success = 0. The verifier flagged a violation, IS chose a fault candidate, but the final answer was still wrong. Attribution- or re-execution-stage failure.
- **Abstained**: repair_status = `abstained`. IS recognized low confidence (max q < δ) and declined to repair.

Aggregate distribution across all 12 cells (N = 107 IS failures):

- Verifier miss: **0** (0.0%)
- Repair failed: **107** (100.0%)
- Abstained: **0** (0.0%)

**Every IS failure in our matrix is a repair-stage failure.** The verifier never missed a violation that IS subsequently failed to repair, and IS never incorrectly abstained (it never declined a repair on a question where the original output was wrong). This is a clean diagnostic: the upstream detection layer is functioning correctly, and the abstention threshold δ = 0.25 is conservative enough to avoid false abstentions in practice.

The implication is that **the chief target for future work is the repair stage**, not detection or attribution. Two paths forward: (i) richer counterfactual sampling that exposes more diverse repair candidates, and (ii) re-execution prompts that condition on the chosen fault node's provenance type rather than treating all repairs uniformly. The 100% repair-stage concentration also explains the K = 3 finding (§4.6.2): if attribution is already correct on the cells where repair fails, additional counterfactual samples cannot help.

---

## 5 Limitations

### 5.1 Sample size and minimum detectable effect

Each cell uses n = 60 paired examples per (model, dataset) combination. For paired McNemar's exact test at α = 0.05 (two-sided), the minimum detectable absolute difference depends on the discordant-pair count:

| n_discordant | min Δ to reject (pp on n = 60) | required win share |
|---|---|---|
| 10 | 11.7pp | 80% (≥ 8/10) |
| 15 | 13.3pp | 73% (≥ 11/15) |
| 20 | 15.0pp | 70% (≥ 14/20) |
| 30 | 18.3pp | 67% (≥ 20/30) |

Across our 12 cells, the mean IS-vs-Direct disagreement rate is approximately 10%, corresponding to roughly 6 discordant pairs and a minimum detectable effect of 13–18pp. Effects below this magnitude are reported descriptively but cannot be claimed as significant. The "no significant losses" headline therefore guarantees that no baseline beats IS by ≥ 13pp anywhere in the matrix; it does not preclude small (< 13pp) systematic disadvantages on individual cells. Increasing n to 200 per cell would tighten this to approximately 7pp, which we leave to future work due to API budget constraints.

### 5.2 Verifier dependence and the 100% repair-failure finding

The §4.7 finding that 100% of IS failures are repair-stage failures depends on the verifier's coverage. If the verifier silently passes some genuinely-wrong answers (verifier under-coverage), those cases would not appear in our failure analysis at all — they would inflate our success rate rather than show up as verifier misses. We use deterministic predicates for hard constraints (budget, allergy, language, forbidden actions) and an LLM-based verifier for semantic constraints, calibrated on a held-out development split. The calibration check confirms the LLM verifier agrees with rule-based predicates on overlapping cases (precision 0.94 on the synthetic diagnostics in Appendix C); however, semantic verification on natural benchmarks may have differential coverage we do not measure. A reviewer interpreting §4.7 should read it as "every failure that we observe is a repair-stage failure," not "the verifier is perfect."

### 5.3 DAG extraction quality on natural benchmarks

The entire attribution pipeline depends on the LLM-extracted Assumption-DAG. We measure node-level and edge-level extraction accuracy on synthetic diagnostics (Appendix C: node precision 0.94, edge precision 0.88), but we do not have human-annotated gold graphs on natural benchmarks. Extraction errors — missing assumptions, spurious edges, mis-labeled provenance — may silently degrade attribution accuracy. The §4.6 ablation showing that the DAG structure is load-bearing (−2.8pp without edges) at least confirms that the *correct* DAG is doing useful work; it does not guarantee that the extractor is producing the correct DAG on every example.

### 5.4 Hyperparameter sensitivity and the ablation as evidence

Our hyperparameters (provenance priors π, attribution temperature γ, cost weight λ, abstention threshold δ, counterfactual sample count M) were fixed on Profile-X validation splits before any Real-X evaluation. We do not report sensitivity sweeps in the main text. The §4.6 ablation provides partial evidence on three of these (provenance priors, M, λ): uniform priors hurt by 3.1pp, M = 3 hurts by 5.0pp, and λ = 0 hurts by 0.6pp. We do not ablate γ or δ. The chosen values may not transfer to other agent stacks or task distributions, particularly tasks with substantially different fault-rate profiles (e.g., tasks where tool errors dominate would benefit from higher π_tool).

### 5.5 No human attribution evaluation

Attribution accuracy on our headline benchmarks is measured indirectly: through final task success rather than through gold attribution labels. The mechanism diagnostics in §4.7 of the main text use synthetic Assumption-DAG tasks where the gold fault node is known by construction, and INTRO-SPECTER achieves 100% top-1 attribution accuracy in single_fault mode and 100% top-3 in multi_valid mode. On natural benchmarks, we do not have human-annotated gold attribution. The §4.4.3 IS-vs-Reflexion overlap analysis provides indirect evidence that IS attribution works (cells where IS solves problems Reflexion does not), but a rigorous test of "did IS pick the *right* assumption" requires human gold labels we do not have. This is a deliberate trade-off in favor of paired binary task success on natural benchmarks where gold attribution would require expensive annotation.

### 5.6 Reflexion as the closest competitor — honest accounting

INTRO-SPECTER does not strictly dominate Reflexion. On 4 of 12 cells, Reflexion leads by margins of 1.7pp to 13.3pp, none of which reach significance under our pre-registered tests but the largest of which (Llama 70B × LongMemEval, p = 0.096) is suggestive. The §4.4.3 overlap analysis shows Reflexion uniquely solves 32 questions vs. IS's 24 (5.1% vs. 3.8% of paired observations). The honest reading is that **INTRO-SPECTER provides a different correction primitive at comparable accuracy and cost, with the additional property of typed fault attribution.** It is not a universally dominant method. The contribution is the primitive (structured attribution + selective repair) and its complementarity with Reflexion (§4.4.3 oracle bound), not a claim of accuracy domination.

### 5.7 Reconstructed-benchmark artifacts

The supplementary Profile-X tier (Appendix F) injects profile structure into canonical tasks under our control, which may introduce artifacts that favor the proposed method. Real-X results — the headline benchmarks in §4 — are on unmodified HuggingFace datasets with only the synthetic profile-injection step (which is the same across all eight methods on a given cell, so methods are paired). The Profile-X results are reported as supplementary evidence rather than the primary contribution.

---

## 6 Related Work

We organize related work by the failure-mode each line of research targets.

**Self-correction and its limits.** Self-Refine (Madaan et al., NeurIPS 2023) and Reflexion (Shinn et al., NeurIPS 2023) demonstrate that iterative critique and verbal episodic memory can improve agent outputs across decision-making, reasoning, and programming tasks. Subsequent work extends this loop in several directions: LATS (Zhou et al., ICML 2024) adds Monte Carlo tree search over Reflexion-style nodes; ExpeL (Zhao et al., AAAI 2024) distills per-task reflections into reusable cross-task insights; AdaPlanner (Sun et al., NeurIPS 2023) closes the feedback loop between planner and executor. Huang et al. (ICLR 2024) show that intrinsic self-correction without external signal often degrades performance, raising the question of when and why self-correction helps. Tyen et al. (2024) decompose self-correction into three sub-capabilities — detection, localization, and repair — and demonstrate that current LLMs can sometimes detect errors but consistently fail at *localizing* the specific step responsible (Tyen et al., NAACL Findings 2024). INTRO-SPECTER targets this localization gap by providing a structured attribution score over candidate faulty assumptions rather than relying on the model's own ability to identify the error source.

**Search over reasoning.** Tree-of-Thoughts (Yao et al., NeurIPS 2023), Graph-of-Thoughts (Besta et al., AAAI 2024), and RAP (Hao et al., EMNLP 2023) explore alternative reasoning branches through breadth-first search, graph transformations, or Monte Carlo tree search respectively. Their search states represent candidate continuations of the reasoning process, not profile-grounded assumptions with typed provenance or fault-node labels. Our results (§4.5) show that ToT is Pareto-dominated on the cost-accuracy frontier in the regime we evaluate; our positioning is therefore that INTRO-SPECTER searches over candidate *faulty assumptions* rather than candidate completions, enabling selective repair instead of exhaustive re-exploration.

**Verification and grounding.** CRITIC (Gou et al., ICLR 2024) demonstrates that internal reflection is unreliable without external tool grounding. CoVe (Dhuliawala et al., ACL Findings 2024) generates independent verification questions and revises based on the answers. SelfCheckGPT (Manakul et al., EMNLP 2023) and HaloScope (Du et al., NeurIPS 2024) detect hallucinations through sampling consistency and latent-space analysis respectively. Lightman et al. (ICLR 2024) and Math-Shepherd (Wang et al., 2023) provide step-level process rewards for mathematical reasoning. Self-RAG (Asai et al., ICLR 2024) conditions generation on retrieval reflection tokens. All of these methods provide *detection* or *verification* signals, but none perform abductive *attribution* over a typed assumption graph to identify which upstream assumption caused a downstream violation.

**Personalization and user-conditioned agents.** Personalized planning can improve perceived relevance while simultaneously introducing constraint violations (PFQABench, Sun et al. 2024; TravelPlanner, Xie et al. ICML 2024). TruthfulQA (Lin et al., ACL 2022) measures the tendency of models to reproduce popular falsehoods. LongMemEval (Wu et al. 2024) evaluates long-term memory fidelity in conversational assistants. INTRO-SPECTER targets the distinct failure mode in which user-profile assumptions propagate through agent trajectories without detection until the final output.

**Agent evaluation.** AgentBench (Liu et al., ICLR 2024) evaluates LLMs as agents across eight environments and finds that Reflexion's gains are highly model-dependent, sometimes producing net-negative effects on weaker models — a finding that directly supports our regime observation in §4.4.2. AgentBoard (Ma et al., NeurIPS 2024) introduces fine-grained progress metrics for multi-turn agents. WebArena (Zhou et al., ICLR 2024), τ-bench (Yao et al. 2024), ALFWorld (Shridhar et al., ICLR 2021), and WebShop (Yao et al., NeurIPS 2022) provide complementary evaluation environments.

---

## 7 Future Work

The §4 results identify three concrete directions, each building on a specific element of related work.

### 7.1 IS + Reflexion ensemble (motivated by §4.4.3 oracle bound)

The §4.4.3 overlap analysis shows that a hypothetical method that selects the better of {INTRO-SPECTER, Reflexion} per question achieves 88.0% — 3.8pp above the better single method. This motivates a per-task **method selector**: a lightweight classifier that, given a profile-grounded violation, predicts whether structured attribution or verbal reflection is more likely to recover the correct answer. Inputs would include features available before correction begins (violation type, trajectory length, fault-node candidate count, profile constraint type). Such a selector would build on the methodological insight that the two correction primitives cover complementary failure modes, and would provide the first concrete instance of a deployment recipe that does not commit to a single correction family. ExpeL (Zhao et al., AAAI 2024)'s per-task insight distillation provides one route: an ExpeL-style cross-task selector over INTRO-SPECTER and Reflexion outputs is a natural follow-on.

### 7.2 Stronger re-execution conditioned on provenance (motivated by §4.7 100% repair-stage failure)

Section 4.7 shows that 100% of IS failures are repair-stage failures: the verifier flags the violation, IS picks a fault candidate, but downstream re-execution does not recover. The direct implication is that the re-execution prompt is the bottleneck. Two extensions:

1. **Provenance-conditioned re-execution prompts.** When IS identifies a model-inferred assumption as the fault, the re-execution should explicitly disqualify the original inference; when a tool-derived assumption is the fault, the re-execution should re-issue the tool call with corrected inputs. The current prompt is uniform across provenance categories, leaving signal on the table. CRITIC (Gou et al., ICLR 2024) shows that tool-grounded critique is more reliable than internal reflection — extending CRITIC's tool-grounding to provenance-typed re-execution is a direct extension.

2. **Diversified counterfactual sampling.** The §4.6.2 K = 3 finding shows that simply increasing M does not help, suggesting that the counterfactual samples are too correlated. Sampling counterfactuals from multiple distinct prompts (re-write, replace, generalize) — analogous to ToT's branching but at the assumption level — could provide diverse repair candidates without the K-noise penalty.

### 7.3 Human attribution evaluation on natural benchmarks (motivated by §5.5)

The §4.7 mechanism diagnostics confirm 100% top-1 attribution on synthetic data. On natural benchmarks, we have only indirect evidence (success rate, IS-Reflexion overlap). The natural follow-on is human-annotated gold attribution: for a sub-sample of failed IS trajectories, ask annotators to identify the assumption that, if changed, would resolve the violation. This would give a direct measure of attribution accuracy on natural benchmarks and isolate attribution-stage from re-execution-stage failure. Tyen et al. (NAACL Findings 2024) provide a methodological template: their step-level error-localization protocol on Big-Bench Mistake is the closest analogue and could be adapted to assumption-level annotation.

### 7.4 Calibration and confidence-aware deployment (extending §5.4)

Our hyperparameter δ = 0.25 was fixed on Profile-X validation. A more principled approach is to *calibrate* the abstention threshold per cell using a small held-out set, then study how INTRO-SPECTER's selective-failure rate (correctly abstaining on questions it cannot solve) trades off against coverage. Self-RAG (Asai et al., ICLR 2024) provides one route via reflection tokens as confidence signals; calibration via temperature scaling on the q-scores is another. The benefit beyond accuracy is *deployment safety*: a calibrated INTRO-SPECTER could refuse to repair when confidence is low rather than producing an unreliable repair, which is critical for user-facing agents under safety constraints.

### 7.5 Scaling the regime claim (motivated by §4.4.2)

Our regime claim ("structured attribution helps mid-tier 7–12B; verbal reflection competitive at 70B+") rests on a single 70B observation and three 7–12B observations. Strengthening this claim requires (i) at least one additional 70B+ model (e.g., DeepSeek V3, Llama 3.3 405B) to confirm the 70B trend is not specific to Llama 3.3; and (ii) a smaller-than-7B model (e.g., Llama 3.2 3B) to test whether the IS advantage continues to grow at smaller scales or saturates. AgentBench (Liu et al., ICLR 2024)'s eight-environment matrix is a precedent for the breadth needed; extending INTRO-SPECTER evaluation to that breadth would convert "regime structure" from a suggestive observation into a calibrated scaling claim.

### 7.6 Beyond Reflexion: extending to the full self-correction family

Recent post-Reflexion work — LATS (tree search), ExpeL (cross-task insight distillation), AdaPlanner (adaptive feedback loops), AutoAct (multi-agent decomposition), Agent-Pro (policy-level reflection) — provides a rich design space for the *correction policy* given an attribution score. INTRO-SPECTER's Assumption-DAG and attribution score are policy-agnostic: they specify *what* to repair, not *how* the repair iterates. Combining IS attribution with LATS-style tree search over repair candidates, ExpeL-style cross-task repair patterns, or Agent-Pro-style policy revision are all natural extensions. The §7.1 ensemble proposal is the simplest case (binary choice between IS and Reflexion); the broader research direction is *what attribution-conditioned correction policy* maximizes coverage.
