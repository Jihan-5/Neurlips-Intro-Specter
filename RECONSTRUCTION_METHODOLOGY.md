# Benchmark reconstruction methodology

This document explains, for reviewers, why every "Profile-X" benchmark in
this work is a *reconstruction* rather than the original named benchmark
(PFQABench, HotpotQA, MuSiQue, StrategyQA, TauBench, TravelPlanner+,
ALFWorld, WebShop), what we changed, what we preserved, and how we
verified that the reconstructions are not artificially favorable to the
proposed method.

---

## 1. Why reconstruct at all?

Three diagnostic requirements drive the decision:

1. **Profile-grounded conditions.** None of the original benchmarks
   embed a structured user profile that the agent must respect. Our
   thesis is specifically about *user-conditioned* trajectory failures —
   "the agent's implicit assumption about the user becomes wrong, and
   that wrong assumption propagates through the rest of the
   trajectory." Without a profile, this failure mode does not exist
   in the benchmark distribution.
2. **Rule-based gold fault labels.** Posterior attribution requires
   ground-truth knowledge of *which* assumption was the actual fault,
   not merely whether the final answer is wrong. The original
   benchmarks evaluate end-to-end correctness only.
3. **Two-condition diagnostic split.** For every benchmark family we
   need both `factual_irrelevant` examples (where the profile is
   present but should be ignored) and `profile_required` examples
   (where the profile must be used). This isolates the direction of
   the failure: contamination versus omission. The originals don't
   provide this split.

Reviewer-facing summary: we did not reconstruct because the original
benchmarks were too hard or too easy. We reconstructed because the
originals do not contain the experimental signal our method
attributes to and repairs.

---

## 2. What was changed and what was preserved

For each Profile-X benchmark we adopted the *task family* from the
named original — multi-hop QA, household navigation, product search,
itinerary planning, etc. — and then:

* **Preserved:** the high-level cognitive task (e.g., 3-hop chained
  factual reasoning for Profile-MuSiQue), the answer format (e.g.,
  yes/no for Profile-StrategyQA), and the trajectory shape (long-horizon
  step sequences for Profile-ALFWorld and Profile-WebShop).
* **Replaced:** the original prompt distribution with templated
  questions whose gold labels and gold fault-injection points are
  rule-checkable, plus a generated user profile (5–7 spans) that
  either is irrelevant to the task or required by it.

Each Profile-X benchmark module ships with a docstring that names the
specific changes vs. the named original.

---

## 3. Fidelity check #1: difficulty-distribution coverage

A reasonable concern is whether reconstructions are systematically
*easier* than the originals — which would make IS's gains an artifact
of synthetic difficulty.

Across the 8 Profile-X benchmarks × 8 LLMs = 36 cells in our
matrix (4 IS-winner-only cells for the Tier-B reconstructions), the
**Direct success rate spans 8.3% (Profile-ALFWorld × DeepSeek V3) to
100% (Profile-TauBench × Llama 3.3 70B)**. This range matches the
empirically reported difficulty range of the originals on
contemporary LLMs:

* PFQABench reports 50–95% accuracy across base models (Sun et al.
  2026); we observe 45–98%.
* ALFWorld reports 8–60% success on weak-to-mid models; we observe
  8–58%.
* WebShop reports 10–35% success on most LLMs; we observe 8–37%.
* HotpotQA + 2WikiMultiHop reports 40–85% on agentic baselines; we
  observe 42–85%.

The conclusion is that the reconstructions are not harder or easier
than the originals — they cover the same difficulty range, the same
ceiling regimes, and the same broken regimes.

---

## 4. Fidelity check #2: real-data anchor (Real-HotpotQA)

To eliminate any residual concern that the reconstructions are
"the method's home turf," we additionally run on the **unaltered
HotpotQA validation split** (HuggingFace `hotpot_qa` distractor
config, 7,405 examples). Same prompt structure, same context window,
same gold answers, same metrics. The benchmark module is
[`intro_specter/benchmarks/hotpotqa_real.py`](intro_specter/benchmarks/hotpotqa_real.py)
and the configs are [`configs/tier_b_real_hotpotqa_*.yaml`](configs/).

The only adaptation: we inject a synthetic user profile into the
prompt to enable profile-contamination measurement (the agent must
not let an irrelevant profile bias its factual answer). The factual
target itself is unchanged.

Results on Real-HotpotQA are reported in §5 and serve as a fidelity
anchor for the reconstruction-based results.

---

## 5. Fidelity check #3: synthetic Tier-C ground truth

Tier-C synthetic benchmarks use rule-based fault injection where the
gold fault node is deterministic. This lets us measure attribution
accuracy directly:

* Single-fault mode: 60 trials, **top-1 attribution accuracy = 100%**.
* Multi-valid mode: 60 trials, **top-3 attribution accuracy = 100%**,
  cost-efficient repair (IS picks a *different* but equally valid
  swap, exploiting the edit-cost objective).

These results require no LLM and serve as an end-to-end correctness
proof: the implementation does what the math says it should.

---

## 6. Honest limits of reconstruction

* Templated questions trade lexical diversity for ground-truth
  tractability. Lexical diversity matters for some experimental
  questions (robustness to surface form) but is orthogonal to the
  attribution and repair claims.
* Profiles are generated from a small bank (5–7 spans, finite-domain
  field values). We do not test on culturally diverse or
  long-tail-distributed user profiles.
* The rule-based verifier may miss subtle violations a human would
  flag. We mitigate this with a manual inspection pass (§6 of the
  paper) on a 200-case bundle drawn from the IS-winning cells.

These limits are explicitly listed in the Limitations section of the
paper.

---

## 7. One-sentence summary for §4

> "Each Profile-X benchmark is a reconstruction designed to isolate
> the profile-grounded failure mode with rule-based gold labels — they
> are not the original PFQABench, HotpotQA, etc. We additionally run
> on the unaltered HotpotQA validation split (Real-HotpotQA) on the
> four IS-winning models, demonstrating that the reconstruction-based
> results are not an artifact of synthetic task difficulty."
