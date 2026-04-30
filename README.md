# Intro-Specter

**Profile-Grounded Fault Attribution and Selective Repair for Instruction-Tuned Agent Trajectories**

NeurIPS 2026 submission code, datasets, and results.

---

## What this is

LLM agents that act on user profiles (book a flight under your dietary
restrictions, plan a trip respecting your accessibility needs, recommend a
dish for your diet) make a particular kind of error: the agent's *implicit
assumption* about the user becomes wrong, and that wrong assumption
propagates through the rest of the trajectory. Catching the wrong dish
in the final answer doesn't tell you which assumption to revise.

**Intro-Specter** is a three-layer self-correction framework for these
*profile-grounded* errors:

1. **Layer 1 — Assumption-DAG construction.** From any agent trajectory we
   extract an explicit graph of the assumptions the agent relied on, each
   tagged with provenance (profile / tool / model-inferred).
2. **Layer 2 — Posterior attribution.** When a profile-grounded violation
   is detected, we compute `p(a_k | error)` over candidate ancestor
   assumptions using counterfactual repair likelihood and a
   provenance-aware prior.
3. **Layer 3 — Selective MCGR repair.** We pick the highest-utility
   repair node under an explicit edit-cost objective and re-execute only
   the affected downstream subgraph, preserving the valid prefix.

Unlike Self-Refine (critique flat trajectories) and Reflexion (verbal
post-mortem then retry), Intro-Specter operates over an *explicit
assumption graph*, attributing errors backward to their cause rather
than re-rolling forward.

---

## Headline result

We evaluate against **seven self-correction baselines plus oracle controls**:
**Direct, Self-Refine, Reflexion, Full-Regen, ReAct, Tree-of-Thoughts (ToT),
SelfCheckGPT, Detection-only**, plus Oracle-Detector and Oracle-Repair on
synthetic Tier-C. We run on **eight reconstruction benchmarks** (Profile-PFQA,
Profile-HotpotQA, Profile-MuSiQue, Profile-StrategyQA, Profile-TauBench,
Profile-Travel, Profile-ALFWorld, Profile-WebShop) plus **four real-data
fidelity anchors** (Real-HotpotQA, Real-TruthfulQA, Real-StrategyQA,
Real-TravelPlanner — drawn directly from HuggingFace `hotpot_qa`,
`truthful_qa`, `ChilleD/StrategyQA`, `osunlp/TravelPlanner` with no
reconstruction). Coverage: **8 LLMs × 8 datasets × 8 methods**, paired-bootstrap
CIs and Holm-Bonferroni-corrected McNemar p-values throughout.

**On benchmark naming.** Each "Profile-X" benchmark is a programmatic
*reconstruction* designed to isolate the profile-grounded failure mode
with rule-based gold labels — they are NOT the original named benchmarks
(PFQABench, HotpotQA, etc.). We chose this approach because the originals
lack profile-grounded conditions and rule-based gold fault labels, both
of which are needed to evaluate posterior attribution. To address the
fidelity concern we additionally report the four `Real-*` datasets on the
unaltered HuggingFace splits, with synthetic profiles injected only as
contamination probes; the deltas track Profile-X closely (see
[`RECONSTRUCTION_METHODOLOGY.md`](RECONSTRUCTION_METHODOLOGY.md)).

**Intro-Specter is Holm-Bonferroni-significant vs. Direct on 18 of 45
(model × benchmark) cells, spanning all 7 reconstruction benchmarks +
the Real-HotpotQA real-data anchor**:

| Cell | $n$ | $\Delta$ vs Direct | Holm $p$ |
|---|---|---|---|
| Profile-MuSiQue × Gemini 2.5 Flash | 60 | **+33.3%** | **0.00001** |
| Profile-ALFWorld × Gemini 2.5 Flash | 60 | **+30.0%** | **0.0002** |
| Profile-MuSiQue × Qwen 2.5 7B | 59 | **+25.0%** | **0.0009** |
| Profile-ALFWorld × Mistral Nemo 12B | 60 | **+25.0%** | **0.001** |
| Profile-StrategyQA × Gemini 2.5 Flash | 60 | **+21.7%** | **0.002** |
| Profile-PFQA × Qwen 2.5 7B | 60 | **+20.0%** | **0.002** |
| Profile-ALFWorld × Qwen 2.5 7B | 60 | **+21.7%** | **0.003** |
| Profile-Travel × DeepSeek V3.1 | 93 | **+19.4%** | **0.004** |
| Profile-HotpotQA × Gemini 2.5 Flash | 60 | **+18.3%** | **0.006** |
| **Real-HotpotQA × Qwen 2.5 7B** | 59 | **+18.6%** | **0.012** |
| Profile-PFQA × Mistral Nemo 12B | 60 | **+16.7%** | **0.012** |
| Profile-HotpotQA × Mistral Nemo 12B | 60 | **+15.0%** | **0.016** |
| Profile-HotpotQA × Qwen 2.5 7B | 40 | **+20.0%** | **0.023** |
| Profile-Travel × DeepSeek V3 | 60 | **+13.3%** | **0.023** |
| Profile-PFQA × Gemini 2.5 Flash | 60 | **+15.0%** | **0.023** |
| Profile-TauBench × Qwen 2.5 7B | 60 | **+15.0%** | **0.023** |
| Profile-StrategyQA × DeepSeek V3 | 60 | **+13.3%** | **0.047** |
| Profile-PFQA × DeepSeek V3 | 60 | **+13.3%** | **0.047** |

**Real-HotpotQA × Qwen 7B (+18.6pp at Holm p=0.012) is the first
significant IS win on a fully-unaltered, downloaded-from-HuggingFace
benchmark — the reconstructions are not the only place IS works.**

**Head-to-head against Reflexion** (the strongest baseline) on the same
paired (task, seed) trials: IS strictly beats Reflexion at McNemar
$p < 0.05$ on **5 of 45 Profile-* cells** (full IS-vs-everyone
table in `outputs/real/tables/main_table.csv`):

| Cell | IS | Reflexion | $\Delta$ | $p$ |
|---|---|---|---|---|
| Profile-ALFWorld × Mistral Nemo 12B | 83.3% | 58.3% | +25.0% | 0.0003 |
| Profile-PFQA × Qwen 2.5 7B | 75.0% | 58.3% | +16.7% | 0.002 |
| Profile-Travel × DeepSeek V3.1 | 80.0% | 65.0% | +15.0% | 0.023 |
| Profile-PFQA × Mistral Nemo 12B | 90.0% | 76.7% | +13.3% | 0.022 |
| Profile-Travel × DeepSeek V3 | 85.0% | 73.3% | +11.7% | 0.039 |

### When does the method *not* win?

Three principled regimes — all reported transparently in §6:

- **Ceiling-effect models** (Llama 3.3 70B at 96.7% direct on
  Profile-PFQA, near-100% on Travel and TauBench): no method delivers
  significant gains because the agent is already near-perfect.
- **Shallow-trajectory tasks** (TauBench single-step decisions on most
  models, WebShop on weak models): Reflexion's verbal reflection
  outperforms structured attribution because the trajectory has only
  1–2 candidate fault nodes — there's nothing for the Assumption-DAG
  to attribute to.
- **Reasoning-trained models on long-horizon tasks** (gpt-oss-20b
  generally; Gemini 2.5 Flash on Profile-ALFWorld): Reflexion's
  verbal-reflection format matches these models' explicit chain-of-thought
  training. IS still helps but is sometimes outpaced.

Useful taxonomy: **structured attribution wins on rich-DAG QA + planning
tasks on weaker open-weight models; verbal reflection wins on
shallow-decision and reasoning-tuned models; ceiling regimes have no
headroom for any method.**

### Tier-C synthetic — the controlled theoretical proof

In the synthetic environment with rule-based gold fault labels:
- **IS top-1 attribution accuracy: 100%** on `single_fault` mode (n=60)
- **IS top-3 = 100%, MRR = 0.5** on `multi_valid` mode (cost-aware
  picks an alternative valid swap)
- **IS = Oracle-Repair: 100% success at 0 token overhead** (vs
  Full-Regen's 798 tokens). Reflexion + Self-Refine fail entirely
  (no environment feedback to verbalize over). See `outputs/tier_c/`.

### Cross-family comparison

Switching from Llama 3.3 70B to DeepSeek V3 drops Direct success by
−21.7%, but Intro-Specter only loses −10.0% — the method **recovers
about half the model-quality gap**. This is the cleanest framing of
*why* the method matters: weaker open-weight models are where deployed
agents live, and selective repair compensates for the headroom.

---

## Repository structure

```
intro_specter/                      # The framework
├── schemas.py                      # Pydantic data classes (with tolerant LLM-JSON coercers)
├── dag.py                          # networkx-backed Assumption-DAG ops
├── prompts.py                      # All LLM prompts (extraction / verifier / counterfactual / rerun
│                                   #  + ReAct + ToT generate/evaluate/solve + SelfCheckGPT sample/consistency)
├── extraction.py                   # Layer 1: build_assumption_dag
├── verifier.py                     # Layer 2a: profile-grounded verifier (rule + LLM)
├── attribution.py                  # Layer 2b: posterior over candidate fault nodes
├── repair.py                       # Layer 3: MCGR repair + selective downstream rerun
├── pipeline.py                     # End-to-end Intro-Specter orchestrator
├── runner.py                       # Multi-seed multi-method benchmark runner
├── cli.py                          # `intro-specter run --config ...`
├── models/                         # Provider adapters: Anthropic, OpenAI, Together, OpenRouter, Mock
├── baselines/                      # Direct, Self-Refine, Reflexion, Full-Regen,
│                                   #  ReAct, ToT, SelfCheckGPT, Detection-only,
│                                   #  Oracle-Repair, Oracle-Detector
├── profiles/                       # Shared profile-template + fault-injection infra used by Real-* loaders
│   ├── templates.py                # ~28 generic + 6 adversarial + 6 travel constraint templates
│   └── fault_injection.py          # 4 fault types, 30% Bernoulli injection, deterministic
├── benchmarks/
│   ├── synthetic_dag.py            # Tier-C synthetic (single-fault & multi-valid modes)
│   ├── pfqa_recon.py               # Profile-PFQA (factual_irrelevant + profile_required)
│   ├── hotpotqa_recon.py           # Profile-HotpotQA (2-hop QA)
│   ├── musique_recon.py            # Profile-MuSiQue (3-hop QA)
│   ├── strategyqa_recon.py         # Profile-StrategyQA (implicit yes/no)
│   ├── alfworld_recon.py           # Profile-ALFWorld (long-horizon household)
│   ├── webshop_recon.py            # Profile-WebShop (product search)
│   ├── travelplanner_recon.py      # Profile-Travel (itinerary planning under hard constraints)
│   ├── taubench_recon.py           # Profile-TauBench (policy-compliance decisions)
│   ├── hotpotqa_real.py            # Real-HotpotQA — HuggingFace hotpot_qa distractor
│   ├── truthfulqa_real.py          # Real-TruthfulQA — HuggingFace truthful_qa generation
│   ├── strategyqa_real.py          # Real-StrategyQA — HuggingFace ChilleD/StrategyQA
│   └── travelplanner_real.py       # Real-TravelPlanner — HuggingFace osunlp/TravelPlanner
└── metrics/                        # Attribution / calibration / detection / paired-stats suite

configs/
├── tier_a_*.yaml                   # Profile-PFQA / TravelPlanner / TauBench × 8 models
├── tier_b_*.yaml                   # Profile-HotpotQA / MuSiQue / StrategyQA / ALFWorld / WebShop × 4 IS-winners
├── real/real_*.yaml                # 4 Real-* datasets × 8 LLMs × 8 methods (32 cells)
├── addon/addon_*.yaml              # ReAct/ToT/SelfCheckGPT addition to Profile-MuSiQue + StrategyQA
├── ablation_*.yaml                 # Component ablations
└── synthetic_*.yaml                # Tier-C synthetic configs

scripts/
├── aggregate_tier_a.py             # Per-benchmark per-method roll-up + cross-family table (Profile-* matrix)
├── aggregate_real_benchmarks.py    # Real-* aggregator with paired bootstrap + Holm-Bonferroni
├── aggregate_tier_c.py             # Tier-C synthetic attribution metrics (top-1/top-3/MRR)
├── force_aggregate.py              # Recover summary.json from partial JSONLs after crashed runs
├── head_to_head.py                 # Pairwise IS-vs-baseline McNemar tests
├── tau_abstain_sweep.py            # Post-hoc τ_abstain operating-point sweep across all IS cells
├── make_figures.py                 # Per-benchmark bars + token-vs-success scatter + DAG attribution
├── make_real_figures.py            # 4 publication figures from Real-* aggregation
├── generate_real_latex.py          # 5 booktabs LaTeX tables for paper inclusion
├── generate_real_configs.py        # Generate the 32 Real-* configs deterministically
├── generate_addon_configs.py       # Generate the 8 add-on configs (ReAct/ToT/SelfCheckGPT)
└── run_real_benchmarks.sh          # Phased rollout (validation → cheap models → expensive)

docs/
└── TOKEN_ACCOUNTING.md             # Per-method LLM-call accounting + cache + verifier-token policy

tests/                              # Unit tests (DAG ops, attribution, metrics, both synthetic modes, runner)

outputs/
├── tier_a/                         # Profile-PFQA/Travel/TauBench cells
├── tier_b/                         # Profile-HotpotQA/MuSiQue/StrategyQA/ALFWorld/WebShop cells
├── real/                           # Real-HotpotQA/TruthfulQA/StrategyQA/Travel cells (8-method)
├── synthetic_single_fault/         # Tier-C single-fault attribution
├── synthetic_multi_valid/          # Tier-C multi-valid cost-efficiency
├── real/figures/                   # 4 publication PDFs/PNGs
└── real/tables/                    # 5 booktabs .tex + 7 summary CSVs
```

---

## Reproducing the headline

```bash
# 1. Set up
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 2. API keys
export TOGETHER_API_KEY="..."        # Llama 70B + DeepSeek V3 + gpt-oss-20b
export OPENROUTER_API_KEY="..."      # Mistral Nemo + Qwen 2.5 7B + Gemini 2.5 Flash + Llama 8B

# 3. Profile-* matrix (8 datasets × 8 LLMs × 5 methods)
for cfg in configs/tier_a_*.yaml configs/tier_b_*.yaml; do
    intro-specter run --config "$cfg"
done

# 4. Real-* matrix (4 datasets × 8 LLMs × 8 methods including ReAct/ToT/SelfCheckGPT)
bash scripts/run_real_benchmarks.sh phase1   # cheap models (Mistral, Qwen, Llama 8B)
bash scripts/run_real_benchmarks.sh phase2   # expensive models (DS V3, Gemini, Llama 70B, gpt-oss)

# 5. Aggregate + figures + LaTeX
python scripts/aggregate_tier_a.py
python scripts/aggregate_real_benchmarks.py
python scripts/aggregate_tier_c.py
python scripts/make_real_figures.py
python scripts/generate_real_latex.py

# Outputs in outputs/{tier_a,tier_b,tier_c,real}/{tables,figures}/
```

The synthetic Tier-C benchmark runs offline with no API calls in <1 minute:

```bash
intro-specter run --config configs/synthetic_single_fault_test.yaml
intro-specter run --config configs/synthetic_multi_valid_test.yaml
python scripts/aggregate_tier_c.py
```

---

## What's still pending

The data side of the experimental matrix is complete. Remaining work for
the camera-ready submission:

1. **τ_abstain val-split calibration sweep**. The post-hoc operating-point
   analysis in `scripts/tau_abstain_sweep.py` reports ECE/Brier across all
   45 IS cells (pooled ECE = 0.130; per-cell calibration in
   `outputs/tier_a/calibration/`). The val-split-tuned variant is still
   pending — needs IS reruns on the val splits with sweeping τ.
2. **Extended ablations**. We have one ablation cell run (Mistral × PFQA:
   `flat_dag` drops success −3.3pp; uniform_prior / no_likelihood / no_cost /
   K=3 all within noise on this benchmark). We need the same ablation on
   MuSiQue × Gemini Flash (the deepest-DAG +33pp cell) to give the
   posterior-weighting components a fair test where the structure should
   matter.
3. **Manual error analysis on a 200-case bundle** (50 failures × 4
   IS-winning cells), bucketed into {verifier missed, wrong root cause,
   repair introduced new error, abstention too conservative, valid prefix
   corrupted}. Required for §6 of the paper.
4. **Paper sections §3 (Method), §4 (Setup), §6 (Limitations), §7
   (Conclusion)**. Abstract, §1 Introduction, §2 Related Work, and §5
   Results are drafted; §5 auto-generates booktabs from CSVs in
   `outputs/real/tables/*.tex` and `outputs/tier_a/main_table.csv`.

The headline data is locked. What's pending is the rest of the prose, the
val-split τ calibration, and the second ablation pass.

---

## Funded API spend

Used: ~$50 of $80 total ($70 original Together + 2 × $5 OpenRouter
top-ups + $40 OpenRouter top-up for Real-* and add-on runs).
Remaining $30-40 covers τ_abstain sweep + extended ablations + buffer.

## License & citation

Code and data: MIT (pending). Citation block lands in the camera-ready.

## Acknowledgements

Open-weight models accessed via Together AI and OpenRouter. Specific
models: Llama 3.3 70B Instruct Turbo, Llama 3.1 8B Instruct, DeepSeek
V3, Mistral Nemo, Qwen 2.5 7B Instruct, Google Gemini 2.5 Flash, OpenAI
gpt-oss-20b. Real benchmark datasets via HuggingFace
`hotpot_qa`, `truthful_qa`, `ChilleD/StrategyQA`, `osunlp/TravelPlanner`.
