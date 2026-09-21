# PAT Verification Sweep — 2026-09-13

Source checked: `paper_final.tex` on current main (`efb8faa`).

| # | Previously flagged issue | Status | Evidence |
|---|---|---|---|
| 1 | Oracle-ensemble disagreement arithmetic | FIXED | The previously flagged oracle-ensemble arithmetic claim is no longer present in the current paper. |
| 2 | McNemar p-values incompatible with success gaps | STILL PRESENT | Main-text line 202 reports MuSiQue×Mistral vs Reflexion as +6.7pp, p=0.012 and TruthfulQA×Mistral vs Reflexion as +5.5pp, p=0.012. Appendix gives the corresponding Reflexion p-values as 0.219 for MuSiQue×Mistral (line 728) and 0.625 for TruthfulQA×Mistral (line 695). Main-text p-values appear stale/inconsistent with regenerated tables. |
| 3 | MuSiQue missing from token-cost table and Appendix D | FIXED | MuSiQue is present in the current token-cost table and has a full statistical table in Appendix D; Appendix statistical-table range explicitly runs through `tab:pvalues-musique` (line 686). |
| 4 | Promised 95% CIs and Direct-baseline comparisons missing | FIXED | Experimental protocol specifies paired-bootstrap 95% CIs (line 124); Appendix statistical tables report CIs and include Direct comparisons (line 686 onward). |
| 5 | TravelPlanner “zero wins” vs appendix contradiction | FIXED | Main text states one numerical win and three NS losses (line 202); TravelPlanner appendix states the same (line 749). |
| 6 | “Four strongest-gain cells” / ablation-cell characterization | STILL PRESENT | Line 229 now says the four ablation cells are “one per benchmark,” but the cells are TruthQA×Mistral, TruthQA×Qwen, 2Wiki×Mistral, and LongMem×Llama8B: two TruthfulQA cells and no MuSiQue cell. |
| 7 | Hyperparameter-ablation prose inconsistent with ablation table | FIXED | Current wording scopes claims to means and affected cells instead of claiming every component hurts uniformly; see line 246 and surrounding ablation discussion. |
| 8 | Seed-protocol contradiction: three seeds vs captions saying one seed | FIXED | The old explicit “1 seed” caption contradiction is gone. Current protocol consistently states three method-internal seeds at line 124 and again at line 523. See additional note below regarding how seed-averaged outcomes enter McNemar. |
| 9 | Cost “21% cheaper” denominator error | FIXED | The old “21% cheaper” claim is absent. Current cost section reports direct token counts and ratios rather than that percentage claim. |
| 10 | SelfCheckGPT missing from comparison figure | STILL PRESENT | Comparison-figure caption at line 60 names ToT, GoT, ToTH, and Intro-Specter only; SelfCheckGPT is still absent. |
| 11 | Result-table tie bolding | FIXED | Current headline tables bold tied best-performing methods together (e.g. tied Reflexion/Intro-Specter cells). |
| 12 | “Tables 3–5” citation omitted Table 6 | FIXED | Current Appendix text references the full table range from TruthfulQA through MuSiQue (line 686). |
| 13 | Missing spaces `failure.We` / `reasoning.In` | FIXED | Neither malformed string is present in the current source. |
| 14 | Edge confidence undefined for cycle removal | FIXED | Line 68 defines cycle removal using the minimum endpoint-node confidence, `min(l_source, l_target)`; line 683 repeats the rule. |
| 15 | Eq. 4 candidate-set denominator vs profile-node exclusion | FIXED | Candidate set explicitly excludes profile-derived assumptions at line 72; full algorithm repeats the exclusion at line 465. |

## Additional findings

### Holm-correction reporting ambiguity
Line 124 states that p-values are Holm-Bonferroni corrected within the pre-registered Direct and Reflexion comparison families. Line 686 describes Appendix significance checkmarks as based on `p < 0.05 (uncorrected)`. The paper should explicitly distinguish raw p-values from Holm-adjusted significance decisions, or report adjusted p-values consistently.

### Seed aggregation vs exact McNemar needs clarification
Lines 124 and 523 state that stochastic methods use three method-internal seeds and that reported success rates average across seeds. The headline tables still describe `n=60` paired observations per cell, and exact McNemar requires paired binary outcomes. The current text does not explain how the three seed outcomes are collapsed into the binary paired observations used for McNemar. This is separate from the old “1 seed” contradiction, which is fixed.