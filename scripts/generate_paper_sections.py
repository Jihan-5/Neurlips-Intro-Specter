"""Auto-generate §3 Problem Formulation, §4 Method, §6 Limitations, and the
prose for §5 Experiments. All data-stable: §3/§4 don't depend on the runs
finishing, §5 prose is templated against the locked aggregate.

Output: outputs/tier_a/paper_sections.tex — drop-in fragments.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


SECTION_3 = r"""\section{Problem Formulation}
\label{sec:problem}

We formalise self-correction in profile-conditioned LLM agents as
abductive Bayesian inference over an explicit assumption graph.

\paragraph{Setup.} A user profile $P = \{p_1, \dots, p_m\}$ is an
ordered set of structured spans, each annotated with kind
(constraint / preference / fact), an ``is-hard'' flag, and an optional
list of contradicting substrings. A task $x$ is a request issued
against $P$. An agent rolling forward on $(P, x)$ produces a
trajectory $\tau = (s_1, \dots, s_T)$ where each $s_t$ is a structured
step with kind $\in \{\textsc{observation}, \textsc{assumption},
\textsc{action}, \textsc{tool\_call}, \textsc{output}\}$ and a public
\textsc{reason\_summary}. We deliberately exclude hidden chain-of-thought
from the schema so the same data can be annotated, audited, and
reproduced.

\paragraph{Assumption-DAG.}
$G = (A, E)$ is a directed acyclic graph over assumption nodes
$a_k = (\text{step\_id}_k, \text{text}_k, \pi_k, \rho_k, c_k, \text{deps}_k)$
where $\pi_k \in \{\textsc{profile}, \textsc{tool},
\textsc{external\_evidence}, \textsc{model\_inferred},
\textsc{world\_knowledge}\}$ is provenance, $\rho_k \subseteq P$ is the
set of profile spans the assumption claims, $c_k \in [0,1]$ is the
agent's confidence, and $\text{deps}_k \subseteq A$ is the set of
predecessor assumptions on which $a_k$ depends. Edges encode
\textsc{supports}, \textsc{depends-on}, \textsc{contradicts}, and
\textsc{downstream-of}.

\paragraph{Profile-grounded violation.}
A violation event $e$ is a tuple
$(\text{step\_id}, p_e, \text{constraint}, \sigma, c_e)$ where
$p_e \in P$ is the violated profile span, $\sigma \in
\{\textsc{low}, \textsc{medium}, \textsc{high}\}$ is severity, and
$c_e \in [0,1]$ is the verifier's confidence. A trajectory exhibits
a \emph{user-specific hallucination} when $\tau$'s output or any step
text contradicts an explicit profile fact, depends on an unsupported
inferred user property, or allows irrelevant profile context to
distort an answer.

\paragraph{Objective.}
Given $(\tau, P, x)$ and a detected $e$, infer the posterior
$p(a_k \mid e)$ over candidate faulty assumptions and choose a repair
$\hat{a}_k$ that maximises expected task success under an explicit
edit-cost constraint:
\begin{equation}
\hat{a}_k = \arg\max_{a_k \in \text{Anc}(e)}
  \; p(a_k \mid e)\,U_{\text{success}}
  \;-\;\lambda\,\frac{C(a_k)}{C_{\max}}
\label{eq:objective}
\end{equation}
where $\text{Anc}(e)$ is the set of ancestors of $e$'s step in $G$,
$C(a_k)$ is the edit cost of repairing at $a_k$ (defined in
Section~\ref{sec:method}), and $\lambda > 0$ trades off posterior
fault probability against repair cost. We refer to this as a
\emph{Bayes-risk-inspired} objective: it is risk-aware and
posterior-conditional, but does not claim Bayes-optimality without
an explicit loss function (we report this honestly in
Section~\ref{sec:limitations}).
"""


SECTION_4 = r"""\section{Method}
\label{sec:method}

Intro-Specter has three layers, each implemented as a single LLM call
plus structured post-processing.

\paragraph{Layer 1: Assumption-DAG construction.}
Given $(P, x, \tau)$, the agent's trajectory is passed to the
extraction prompt (Appendix~A.1), which returns a JSON object with
nodes, edges, and a final-decision node. We parse with
provenance-aware coercion: unknown enum values default to
\textsc{model\_inferred}; cycles are removed by dropping the
lowest-confidence edge; orphan edges are silently elided. We never
store hidden chain-of-thought; only \textsc{reason\_summary} fields.

\paragraph{Layer 2a: Profile-grounded verification.}
A two-layer verifier checks the trajectory against $P$. The first
layer is a deterministic rule-based scan (e.g.,~hard-constraint
banned-substring matching) for benchmark-specific rules. The second
layer is an LLM-based verifier prompt (Appendix~A.2). The two layers'
outputs are unioned and de-duplicated by \texttt{(step\_id,
violated\_span\_id, constraint)}.

\paragraph{Layer 2b: Posterior attribution.}
For each candidate $a_k \in \text{Anc}(e)$ we compute
\begin{equation}
p(a_k \mid e) \propto p(e \mid a_k)\,p(a_k)
\end{equation}
where the prior $p(a_k)$ is provenance-weighted (higher for
\textsc{model\_inferred}, lower for \textsc{profile}, scaled by
$1 - c_k$ so high-confidence nodes are less likely faults), and the
likelihood is estimated by counterfactual repair: for each candidate
we sample $K$ alternative assumption values, simulate each via
re-execution, and count the fraction that remove the violation while
preserving task success. Posterior is normalised over the candidate
set.

\paragraph{Layer 3: Min-Cost Graph-Edit Repair (MCGR).}
We compute $\hat{a}_k$ via Equation~\ref{eq:objective}. If
$\max_{a_k} p(a_k \mid e) < \tau_{\text{abstain}}$, we abstain; the
runtime falls back to either full regeneration or returning the
unrepaired trajectory with a warning, depending on the deployment
policy. When $\hat{a}_k$ is selected, the re-execution prompt
(Appendix~A.4) is asked to regenerate only the steps in
$\{\hat{a}_k\} \cup \text{Desc}(\hat{a}_k)$, conditioning on the
preserved valid prefix and any tool observations carried over.
The post-repair trajectory is re-verified to confirm the violation
is resolved.

\begin{algorithm}[t]
\caption{Intro-Specter}
\label{alg:intro-specter}
\begin{algorithmic}[1]
\Require profile $P$, task $x$, trajectory $\tau$, model $M$, verifier $V$, threshold $\tau_{\text{abstain}}$
\State $G \gets$ \textsc{BuildAssumptionDAG}$(M, P, x, \tau)$
\State $E \gets V(P, x, \tau)$
\If{$E = \emptyset$} \Return $(\textsc{accepted}, \tau, G)$ \EndIf
\State $\text{Anc} \gets \bigcup_{e \in E} \text{ancestors-of-step}(G, e)$
\For{each $a_k \in \text{Anc}$}
  \State $R_k \gets$ sample $K$ counterfactual repairs of $a_k$
  \State $\ell_k \gets |\{r \in R_k : V(\text{rerun}(r)) \text{ passes}\}| / K$
  \State $\pi_k \gets$ \textsc{StructuralPrior}$(a_k, G)$
  \State $C_k \gets$ \textsc{EditCost}$(a_k, G)$
\EndFor
\State $p \gets \textsc{Normalize}(\{\pi_k \ell_k\})$
\If{$\max_k p_k < \tau_{\text{abstain}}$} \Return $(\textsc{abstain}, \tau, G, p)$ \EndIf
\State $\hat{k} \gets \arg\max_k p_k U_{\text{success}} - C_k / C_{\max}$
\State $\tau' \gets$ \textsc{RerunDownstreamSubgraph}$(\hat{k}, G, \tau, M)$
\State \Return $(\textsc{repaired}, \tau', G, p, \hat{k})$
\end{algorithmic}
\end{algorithm}
"""


SECTION_2_RELATED_WORK = r"""\section{Related Work}
\label{sec:related}

We organise prior work around what each line \emph{cannot} do, leading
to the gap that Intro-Specter targets.

\paragraph{Prompted reasoning and self-consistency.}
Chain-of-Thought~\citep{wei2022cot} and Self-Consistency~\citep{wang2022selfconsistency}
improve reasoning trace quality by sampling and majority vote, but
operate over flat answer traces and do not identify which user-profile
assumption caused a downstream violation.

\paragraph{ReAct-style agents.}
ReAct~\citep{yao2023react} grounds reasoning in tool calls and
environment feedback, performing well on HotpotQA, FEVER, ALFWorld,
and WebShop-style tasks. Tool grounding fixes some action-level
errors, but early wrong assumptions about the user can still
propagate through later actions; ReAct provides no backward-attribution
mechanism.

\paragraph{Reflexion and Self-Refine.}
Reflexion~\citep{shinn2023reflexion} adds verbal post-mortems stored
as episodic memory. Self-Refine~\citep{madaan2023selfrefine} alternates
critique-revise cycles. Both revise globally or heuristically; neither
performs posterior root-cause attribution conditional on a detected
profile-grounded violation. We choose the repair point using posterior
attribution and edit cost, not by re-rolling forward.

\paragraph{Tree- and graph-structured search.}
Tree of Thoughts~\citep{yao2023tot} maintains and prunes branching
reasoning states; Graph of Thoughts~\citep{besta2024got} generalises
to arbitrary graph transformations. Search heuristics here optimise
candidate completions, not fault localisation. We search over candidate
\emph{faulty assumptions} rather than over candidate completions.

\paragraph{Hallucination detection and uncertainty.}
SelfCheckGPT-style sampling consistency~\citep{manakul2023selfcheckgpt},
TruthfulQA~\citep{lin2022truthfulqa}, and HaloScope's latent-space
detection~\citep{du2024haloscope} all detect final-answer
unreliability; UProp~\citep{duan2025uprop} decomposes per-step
uncertainty. Detection is a useful input signal but does not
prescribe \emph{which} assumption to revise. In our pipeline, the
verifier plays the detection role; attribution and selective repair
are the contribution.

\paragraph{Personalisation-induced hallucination.}
TravelPlanner+~\citep{singh2024travel} shows personalisation can degrade
hard-constraint satisfaction. Sun et~al.~\cite{sun2026personalization}
formalise representational entanglement between personalisation and
factuality. The Martingale Score~\citep{he2025martingale} finds that
LLM belief updates systematically violate Bayesian rationality, making
self-correction fragile when it relies on the model's own
self-evaluation. These results motivate three design choices: external
profile-grounded verification, explicit assumption nodes (so the system
can reason about provenance rather than activations), and a Bayes-risk-
inspired repair objective (which does \emph{not} require the model's
internal posterior to be calibrated).

\paragraph{The gap.} Existing methods provide reflection, search, or
uncertainty signals but do not jointly model user-profile assumptions
as explicit trajectory nodes, infer a posterior over candidate faulty
assumptions after a detected profile-grounded violation, and
selectively repair only the downstream subgraph. Intro-Specter does.
"""


SECTION_7_REPRODUCIBILITY = r"""\section{Reproducibility}
\label{sec:reproducibility}

\paragraph{Code and data.} The full pipeline, all benchmark
constructors, all five baselines, the calibration / ablation /
robustness analysis scripts, and the configs that reproduce every
table and figure in this paper are released at
\url{https://github.com/Jihan-5/Neurlips-Intro-Specter} under MIT
license.

\paragraph{Models and providers.} We use Together AI for Llama 3.3
70B Instruct Turbo, DeepSeek V3, DeepSeek V3.1, and OpenAI gpt-oss-20b;
and OpenRouter for Llama 3.1 8B Instruct, Mistral Nemo 12B,
Qwen 2.5 7B Instruct, and Google Gemini 2.5 Flash. All API calls were
made between 2026-04-27 and 2026-04-29; we cache and persist every
prompt-response pair for re-runs.

\paragraph{Hyperparameters.} For all headline runs we use
$\tau_{\text{abstain}}=0$ (commit always; calibration sweep reported
separately in Section~\ref{sec:experiments}), counterfactual sample
count $K=1$ on natural benchmarks (per-task cost), and the cost-aware
selection rule with $\lambda=1$ on $C(a_k)$ normalised by maximum
candidate cost. Verifier is rule-based on the headline runs; LLM
verifier ablation reported in the appendix.

\paragraph{Statistical testing.} All headline numbers report
mean across 60 paired (task, seed) trials (20 test examples $\times$
3 seeds). 95\% paired bootstrap confidence intervals use 10K
resamples. McNemar's test is applied to paired binary success;
Wilcoxon signed-rank to paired tokens. Holm-Bonferroni correction is
applied across the (method $\times$ metric $\times$ benchmark) family.

\paragraph{Prompts.} All four prompts (Assumption-DAG extraction,
profile-grounded verification, counterfactual repair generation,
re-execution) are reproduced verbatim in Appendix~A.

\paragraph{Datasets.} PFQABench-Recon, TravelPlanner+ Recon,
TauBench-Recon, HotpotQA + 2WikiMultiHopQA Recon, ALFWorld-Recon, and
WebShop-Recon are all generated programmatically; the constructors
are deterministic given a seed and are released alongside the
pipeline. We deliberately use reconstructions rather than the
original datasets for two reasons: (i)~to control gold-fault labels
on Tier-C, and (ii)~because access policies for the original
PFQABench, TravelPlanner+, tau-bench, ALFWorld, and WebShop datasets
vary; a programmatic reconstruction is a level playing field for
all baselines and removes data-availability variance. Section~\ref{sec:limitations}
acknowledges this.
"""


def main() -> int:
    out_dir = Path("outputs/tier_a")
    out_dir.mkdir(parents=True, exist_ok=True)
    parts = [
        "% Auto-generated by scripts/generate_paper_sections.py.",
        "% Drop-in §2/§3/§4/§7 fragments (§5 + §6 are in paper_focused.tex).",
        "",
        SECTION_2_RELATED_WORK,
        "",
        SECTION_3,
        "",
        SECTION_4,
        "",
        SECTION_7_REPRODUCIBILITY,
    ]
    (out_dir / "paper_sections.tex").write_text("\n".join(parts))
    print(f"Wrote {out_dir / 'paper_sections.tex'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
