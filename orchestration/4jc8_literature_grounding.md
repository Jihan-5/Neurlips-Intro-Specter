# Literature grounding for reviewer 4jc8 (rebuttal input)

**Purpose.** Reviewer 4jc8 (borderline reject, confidence 4) argues Intro-Specter's core
mechanism — abductive inference, hierarchical DAG representations, counterfactual
mechanisms — has "a substantial multi-year history" in software engineering,
fault-tolerant systems, and network reliability, and that the paper's related work is
missing the relevant older literature. This document assembles the real, verified prior
work in the four areas 4jc8 named, states the specific structural difference between
each and Intro-Specter's actual mechanism, and gives an honest assessment of the closest
prior art — including work close enough to be a genuine novelty risk, not just a
citation gap.

**What Intro-Specter's mechanism actually is** (grounded in `intro_specter/dag.py`,
`intro_specter/attribution.py`, `README.md`): (1) an **Assumption-DAG** is extracted by
prompting an LLM to expose the implicit assumptions in its own agent trajectory,
each node tagged with a provenance label (`PROFILE`, `TOOL`, `WORLD_KNOWLEDGE`,
`MODEL_INFERRED`, `EXTERNAL_EVIDENCE`) and a confidence score — there is no
hand-authored structural/logical model of "the system"; the DAG *is* a post-hoc encoding
of one LLM trajectory. (2) When a profile-grounded violation is detected, candidate
faulty nodes = ancestors of the violated step in this DAG. (3) A posterior
`p(a_k | e) ∝ p(e | a_k) p(a_k)` is computed per candidate: the prior is
provenance-weighted (model-inferred assumptions score higher prior fault probability
than tool outputs or profile facts) and scaled by `(1 − confidence)`; the likelihood
comes from **counterfactual repair trials** — an LLM proposes an alternative value for
the candidate assumption and an evaluator checks whether the trajectory violation would
be removed. (4) Layer 3 selects the repair node under an edit-cost objective and
re-executes only the downstream subgraph (selective, minimum-cost graph repair — MCGR),
preserving the valid trajectory prefix.

---

## Area 1 — Abductive inference / model-based diagnosis (classical AI diagnosis)

| Title | Authors | Year | Venue | URL | Mechanism (one line) |
|---|---|---|---|---|---|
| A Theory of Diagnosis from First Principles | Raymond Reiter | 1987 | *Artificial Intelligence*, 32(1), 57–95 | https://www.sciencedirect.com/science/article/pii/0004370287900622 (also PDF mirror: http://www.cs.ru.nl/P.Lucas/teaching/KeR/Theorist/reiteraij87.pdf) | Consistency-based diagnosis: given a hand-built logical system description SD and observed behavior, a diagnosis is a minimal set of components whose abnormality assumption restores consistency; diagnoses computed via minimal hitting sets over conflict sets. |
| Diagnosing Multiple Faults | Johan de Kleer, Brian C. Williams | 1987 | *Artificial Intelligence*, 32(1), 97–130 | https://www.sciencedirect.com/science/article/pii/0004370287900634 | GDE (General Diagnostic Engine): model-based diagnosis of a physical device from its hand-specified structure/behavior model; candidates are minimal sets of violated "assumptions" (component-OK literals), refined via further measurements. |
| Sequential Model-Based Diagnosis by Systematic Search | Patrick Rodler | 2023/2024 | *Artificial Intelligence* (2023) / AAAI 2024 (abstract reprint) | https://dl.acm.org/doi/10.1016/j.artint.2023.103988 ; https://ojs.aaai.org/index.php/AAAI/article/view/30609 | Iteratively poses discriminating queries/measurements to shrink the diagnosis candidate set, using entropy/information-theoretic query selection over a fixed logical model — the classical ancestor of "sequential" diagnosis. |

**Structural difference from Intro-Specter.** Classical model-based diagnosis (Reiter;
de Kleer & Williams) requires a **hand-authored, logic-level structural/behavioral model
of the system** (SD in Reiter's formalism; the component connectivity + behavior modes
in GDE) that exists independently of any single run and is reused across many
observation sets. Fault candidates are derived by consistency-checking observations
against this fixed model, and root candidates are minimal conflict sets. Intro-Specter
has **no hand-built structural model at all** — the "model" (the Assumption-DAG) is
extracted post hoc, per-trajectory, from the LLM's own natural-language reasoning trace,
and is disposable: a new DAG is built for every trajectory rather than reused. The
verified hypothesis holds: classical diagnosis reasons over a designer-specified
consistency theory; Intro-Specter reasons over an LLM-authored, single-instance,
natural-language assumption graph with no logical consistency semantics — its "prior"
is a provenance/confidence heuristic, not a symbolic conflict-set computation. Rodler's
sequential diagnosis is the closest classical analogue to Intro-Specter's *iterative*
posterior refinement (both narrow a candidate set via new evidence), but Rodler's queries
are measurements against the fixed logical SD, whereas Intro-Specter's "queries" are
LLM-generated counterfactual repair trials against a DAG that has no logical model
underneath it — this is a genuine and citable extension-of-idea (sequential candidate
narrowing) applied to a fundamentally different (model-free, LLM-native) substrate, and
should be cited as such rather than omitted.

---

## Area 2 — Fault localization in software engineering

| Title | Authors | Year | Venue | URL | Mechanism (one line) |
|---|---|---|---|---|---|
| Visualization of Test Information to Assist Fault Localization | James A. Jones, Mary Jean Harrold, John Stasko | 2002 | ICSE '02 | https://faculty.cc.gatech.edu/~stasko/papers/icse02.pdf | Introduces Tarantula: colors statements by pass/fail test coverage ratio to visually rank suspicious lines. |
| Empirical Evaluation of the Tarantula Automatic Fault-Localization Technique | James A. Jones, Mary Jean Harrold | 2005 | ASE '05 | https://dl.acm.org/doi/10.1145/1101908.1101949 | Formalizes Tarantula's suspiciousness score from a fixed test suite's coverage spectra and evaluates it against manual fault-finding. |
| An Evaluation of Similarity Coefficients for Software Fault Localization | Rui Abreu, Peter Zoeteweij, Arjan J. C. van Gemund | 2006 | PRDC '06, pp. 39–46, DOI 10.1109/PRDC.2006.18 | https://doi.org/10.1109/PRDC.2006.18 | Introduces/evaluates the Ochiai similarity coefficient over pass/fail coverage spectra as a statement-suspiciousness ranking (spectrum-based fault localization, SBFL). |
| Yesterday, My Program Worked. Today, It Does Not. Why? | Andreas Zeller | 1999 | ESEC/FSE '99 | https://www.cs.columbia.edu/~junfeng/18sp-e6121/papers/delta-debug.pdf | Delta debugging: binary-search-style minimization over a set of *changes* between a working and failing configuration to isolate the minimal failure-inducing diff. |

**Structural difference from Intro-Specter.** SBFL (Tarantula, Ochiai) requires a **fixed
test suite run many times** — suspiciousness is a statistic over coverage counted across
dozens/hundreds of passing and failing executions of the *same* program; it localizes to
a *line of code*, not to a semantic belief, and has no notion of "assumption provenance"
or intervention. Delta debugging requires an explicit **before/after pair of
configurations** (a working version and a failing version, e.g. two commits or two
input sets) and searches over syntactic deltas between them. Intro-Specter has **neither
a test suite nor a before/after pair**: it operates on a *single* trajectory, generated
once by an LLM agent, and localizes fault to a semantic *assumption node* rather than a
code line or configuration delta; its "spectrum" analogue (ancestor-of-violation
candidate set) is a graph-structural notion derived from one run, not a statistical
signal aggregated over many runs. The verified hypothesis holds and should be stated
plainly in the rebuttal: SBFL substitutes population statistics over repeated runs for
what Intro-Specter does with graph structure over a single run, because repeated,
cheaply re-runnable executions with ground-truth pass/fail oracles (SBFL's core
assumption) do not exist for one-shot LLM agent trajectories against a user profile.

---

## Area 3 — Fault-tolerant distributed systems (RCA in microservices, chaos engineering)

| Title | Authors | Year | Venue | URL | Mechanism (one line) |
|---|---|---|---|---|---|
| Chaos Engineering | Ali Basiri, Niosha Behnam, Ruud de Rooij, Lorin Hochstein, Luke Kosewski, Justin Reynolds, Casey Rosenthal | 2016 | *IEEE Software* 33(3), 35–41 | https://doi.org/10.1109/MS.2016.60 (arXiv companion: https://arxiv.org/pdf/1702.05843) | Proactively injects real faults into a production distributed system to empirically verify resilience, rather than diagnosing a fault after the fact. |
| Intelligent Root Cause Localization in MicroService Systems: A Survey and New Perspectives | (survey) | 2025 | *ACM Computing Surveys* | https://dl.acm.org/doi/10.1145/3736755 | Surveys dependency-graph- and causal-graph-based RCA: constructs a service call/dependency graph from traces, then ranks candidate root-cause services via graph propagation or causal discovery over metrics/logs/traces. |
| Failure Diagnosis in Microservice Systems: A Comprehensive Survey and Analysis | (survey) | 2024 | arXiv preprint | https://www.arxiv.org/pdf/2407.01710 | Surveys anomaly detection + root-cause localization pipelines built on pre-instrumented service topology graphs. |
| The PetShop Dataset — Finding Causes of Performance Issues across Microservices | Michaela Hardt, William R. Orchard, Patrick Blöbaum, Shiva Kasiviswanathan, Elke Kirschbaum | 2023/2024 | CLeaR 2024 (PMLR 236) | https://arxiv.org/pdf/2311.04806 | Benchmark of injected latency/availability faults over a real microservice call graph, used to evaluate causal and non-causal RCA methods. |
| CausalRCA: Causal Inference based Precise Fine-grained Root Cause Localization for Microservice Applications | (authors per arXiv listing) | 2022 | arXiv preprint | https://arxiv.org/pdf/2209.02500 | Learns a causal graph over monitored KPIs/metrics (not a reasoning trace) and ranks root causes by causal-graph traversal from the anomaly. |

**Structural difference from Intro-Specter.** Microservices RCA — whether classic
dependency-graph propagation or newer causal-discovery variants (CausalRCA, RADICE,
CHASE, DynaCausal) — operates over a **pre-instrumented, infrastructure-level topology**:
the graph nodes are *services*, and edges are *actual network/RPC call relationships*
observed via tracing infrastructure (Jaeger/Zipkin-style spans) across many requests over
time; the "fault" being localized is an infra/performance anomaly (latency, error rate,
CPU). Chaos engineering (Basiri et al.) is not diagnostic at all — it is a proactive,
experimental discipline for *injecting* faults into a live system to test resilience,
the inverse direction of Intro-Specter's post hoc attribution. Intro-Specter's DAG nodes
are **semantic assumptions inside one LLM's reasoning**, not services; there is no
call-graph instrumentation, no aggregation across requests, and the "topology" is
authored anew by the LLM for each trajectory rather than observed from infrastructure.
The verified hypothesis holds: swap "service dependency graph built from RPC traces" for
"assumption graph built from one LLM's self-report," and swap "resource/latency
anomaly" for "profile-grounded semantic violation," and the RCA machinery's graph-search
logic (propagate anomaly score along edges, rank ancestors) is structurally the nearest
sibling to Intro-Specter's ancestor-candidate step in `dag.py` — this is a fair,
citable "extends the ancestor-graph localization idea from infra topology to LLM
self-reported reasoning topology" framing for the rebuttal, not a false-novelty claim.

---

## Area 4 — Network reliability / fault diagnosis

| Title | Authors | Year | Venue | URL | Mechanism (one line) |
|---|---|---|---|---|---|
| Network Tomography: Recent Developments | R. Castro, M. Coates, G. Liang, R. Nowak, B. Yu | 2004 | *Statistical Science* 19(3), 499–517 | https://doi.org/10.1214/088342304000000422 (Project Euclid) | Statistical inference of internal network link-level behavior (loss, delay, topology) from end-to-end path measurements, without direct access to internal routers. |
| Alarm Correlation (survey chapter) | (multiple; representative overview) | — | IEEE Network / conference proceedings on alarm correlation | https://www.macs.hw.ac.uk/~dwcorne/RSR/eventcorr.pdf | Groups/correlates the flood of low-level alarms a single network fault produces so operators see the probable root alarm rather than every downstream symptom alarm. |

**Structural difference from Intro-Specter.** Network tomography infers **link-level
physical/statistical properties of a real communication network** from repeated
end-to-end probe measurements — its "graph" is the actual physical/logical network
topology, and its inference target is loss/delay parameters, not a semantic fault.
Alarm correlation groups **discrete alarm events** raised by network elements according
to known or learned propagation rules (a fault at node A causes downstream alarms at B,
C, D) so the root alarm can be surfaced from the flood — this is the network-domain
sibling of "ancestor-of-violation" candidate identification, but operating over
device-generated alarm signals and (typically) a known or rule-mined physical topology,
not over a single LLM's self-reported reasoning chain. Neither area has a notion of an
LLM-native, provenance-tagged, per-trajectory assumption graph, and neither uses
counterfactual repair trials as a likelihood signal; the connection to Intro-Specter is
looser than areas 1–3 (mostly at the level of "propagate a fault signal backward through
a directed graph to find the most likely origin"), and the rebuttal should frame this
area as the most distant, citing it briefly for the ancestor-propagation *idea* lineage
rather than claiming a close structural parallel.

---

## Honest "closest prior art" assessment

Two 2026 arXiv preprints are **uncomfortably close to Intro-Specter's actual mechanism**
and must be engaged with directly rather than folded into generic related work:

1. **CausalFlow: Causal Attribution and Counterfactual Repair for LLM Agent Failures**
   (Bonagiri, Borkar, Anderias, Rafatirad, Homayoun; arXiv 2605.25338, submitted
   2026-05-25). https://arxiv.org/abs/2605.25338v1 — Models a failed LLM agent trace as
   a sequential chain of dependent steps, computes step-level "Causal Responsibility
   Scores" via **counterfactual intervention**, and generates **minimal counterfactual
   repairs** for the failure-inducing step. This overlaps substantially with
   Intro-Specter's Layer 2 (counterfactual repair trials scoring candidate faulty
   ancestors). **Key differences to lean on in the rebuttal:** (a) CausalFlow's trace
   model is a linear chain of steps, not a DAG with provenance-typed nodes and explicit
   ancestor/descendant structure — Intro-Specter's Assumption-DAG supports branching
   dependency structure and a provenance-aware structural prior (profile vs. tool vs.
   model-inferred), which CausalFlow does not model; (b) CausalFlow's repairs are used
   for offline supervision/preference-data generation as a primary use case, whereas
   Intro-Specter performs online selective subgraph re-execution (Layer 3, MCGR) under
   an explicit edit-cost objective, preserving the valid trajectory prefix; (c)
   Intro-Specter's task setting (profile-grounded errors — the agent's wrong belief
   about *user* attributes/preferences) is a distinct failure class from CausalFlow's
   general reasoning/tool-use/code-gen failures. This is real, close prior art — cite it
   and differentiate explicitly; do not omit it.

2. **Causal Agent Replay (CAR): Counterfactual Attribution for LLM-Agent Failures**
   (Jaineet Shah; arXiv 2606.08275, submitted 2026-06-06).
   https://arxiv.org/abs/2606.08275v1 — Models an agent run as a structural causal
   model, applies a do-operation to a step, and re-executes forward to measure outcome
   shift; uses a budget-bounded Monte-Carlo Shapley estimator to split credit across
   interacting steps. This is the same broad idea (intervene on a step/node, observe
   whether the failure is removed) as Intro-Specter's counterfactual-repair likelihood.
   **Key differences:** CAR's causal model is an SCM over *agent steps* validated
   against synthetic ground-truth SCMs, with no provenance typing, no DAG extracted as
   an explicit artifact the system reasons over structurally (ancestors/descendants,
   selective repair), and no profile-grounded-error framing; it is fundamentally an
   attribution/credit-assignment tool (a "why" explainer), not a repair-and-continue
   system with a min-cost selective re-execution step. Intro-Specter's Layer 3 (pick a
   repair node under an edit-cost objective and re-execute only the affected downstream
   subgraph) has no analogue in CAR.

**Verdict:** These two are genuine novelty risk items, not merely missing citations —
they were pre-printed in May/June 2026, both post-date what a typical review cycle would
have expected authors to have found unprompted, and both target the same idea space
("counterfactual intervention over LLM agent trajectory steps to attribute failure").
The rebuttal should (a) cite both explicitly, (b) concede the shared premise
(counterfactual intervention as a fault-attribution likelihood signal for LLM
trajectories is not solely Intro-Specter's idea), and (c) argue novelty on the specific
combination Intro-Specter contributes that neither preprint has: **explicit
provenance-typed DAG structure (not a linear step chain or opaque SCM) + a
provenance-aware structural prior + selective minimum-cost subgraph repair with
prefix preservation + the profile-grounded-error problem framing.** This is a defensible
combination-novelty argument, but it is not the same as "no related work exists" — 4jc8
would be justified in pressing further on this point, and the paper's current related
work section is a genuine gap here, not just an oversight on classical citations.

No 2023–2026 paper found combines all four of: (i) DAG (not chain) extraction from an
LLM trajectory, (ii) provenance-typed structural priors, (iii) counterfactual-trial
likelihoods, and (iv) selective min-cost subgraph repair with sequential/iterative
posterior refinement across multiple violations in one trajectory. The combination
appears to be the paper's actual point of novelty; the individual pieces are not.

---

## NeurIPS 2026 contemporaneous-work policy applies to both preprints — verified

Confirmed against the official NeurIPS 2026 Main Track Handbook (fetched 2026-07-25):

> "For the purpose of the reviewing process, papers that appeared online after March 1st,
> 2026 will generally be considered 'contemporaneous' in the sense that the submission
> will not be rejected on the basis of the comparison to contemporaneous work."

Both CausalFlow (published 2026-05-25, arXiv metadata verified) and Causal Agent Replay
(published 2026-06-06, arXiv metadata verified) postdate March 1, 2026 by a wide margin —
CausalFlow also postdates Intro-Specter's own submission date (04 May 2026). **Neither can
be grounds for a novelty-based rejection under NeurIPS's own explicit policy.**

The handbook is equally explicit that this is not a free pass to omit them: **"Authors are
still expected to cite and discuss contemporaneous work and perform empirical comparisons
to the degree feasible."** The recommended 4jc8-response framing therefore combines both
halves of the policy rather than leaning on only the favorable half:

1. Cite both papers with their exact publication dates.
2. State plainly, with the quoted policy line, that per NeurIPS 2026's contemporaneous-work
   rule (cutoff March 1, 2026) neither is eligible grounds for an originality-based
   rejection — this is a verifiable, rule-grounded point, not a rhetorical dodge.
3. Still perform the substantive "discuss to the degree feasible" comparison already
   written above (the shared premise conceded, the four-part combination-novelty argument
   made) — citing the rule without engaging the content would read as evasive to a
   confidence-4 reviewer who can check the handbook themselves; doing both reads as
   rule-literate and substantively engaged.
