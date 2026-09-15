# Reference audit for ICLR resubmission (2026-09-12)

Verified by parallel agents against arXiv + web. Verdicts: OK / MINOR (metadata fix) / HALLUCINATED (wrong paper or authors — replaced with the real one) / NOT_FOUND.

## Batch 2 (18 entries) — 1 HALLUCINATED, 3 MINOR, 14 OK

huang2024selfcorrect | OK
zhou2023webarena | OK
wu2024longmemeval | MINOR — published ICLR 2025 (arXiv:2410.10813): \bibitem{wu2024longmemeval} D. Wu et~al. LongMemEval: Benchmarking chat assistants on long-term interactive memory. \emph{ICLR}, 2025.
ho2020twowiki | OK
tyen2024selfcorrect | HALLUCINATED — fake author "I. Tyen", wrong arXiv ID. Real paper arXiv:2410.04055, Jiayi He et al. NEW KEY he2025selfcorrect (update \cite{} in body): \bibitem{he2025selfcorrect} J. He et~al. Self-correction is more than refinement: A learning framework for visual and language reasoning tasks. \emph{Findings of ACL}, 2025.
tyen2024llmerrors | MINOR — first author G. Tyen; venue Findings of ACL 2024: \bibitem{tyen2024llmerrors} G. Tyen et~al. LLMs cannot find reasoning errors, but can correct them given the error location. \emph{Findings of ACL}, 2024.
zhou2024lats | MINOR — full title ends "...in language models": \bibitem{zhou2024lats} A. Zhou et~al. Language Agent Tree Search unifies reasoning, acting, and planning in language models. \emph{ICML}, 2024.
zhao2024expel | OK
sun2023adaplanner | OK
gou2024critic | OK
dhuliawala2024cove | OK (venue is Findings of ACL 2024)
asai2024selfrag | OK
ma2024agentboard | OK
choi2025atlas | OK (arXiv:2509.25586; optionally ICLR 2026)
yuan2026behaviorforest | OK (arXiv:2604.21354)
chen2026triflow | OK (arXiv:2512.11271, WWW 2026 Companion)
weng2023selfverif | OK
wang2023planandsolve | OK

## Batch 1 (18 entries) — 1 HALLUCINATED, 4 MINOR, 13 OK

madaan2023selfrefine | OK
shinn2023reflexion | OK
yao2022react | OK
yao2023tot | OK
besta2024got | OK
manakul2023selfcheckgpt | MINOR — full title: \bibitem{manakul2023selfcheckgpt} P. Manakul et~al. SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection for Generative Large Language Models. \emph{EMNLP}, 2023.
du2024haloscope | OK
lin2021truthfulqa | OK
trivedi2022musique | MINOR — "Multihop" unhyphenated: \bibitem{trivedi2022musique} H. Trivedi et~al. MuSiQue: Multihop Questions via Single-hop Question Composition. \emph{TACL}, 2022.
xie2024travelplanner | OK
sun2024pfqabench | HALLUCINATED — no standalone PFQABench paper; real: \bibitem{sun2024pfqabench} Z. Sun et~al. When Personalization Misleads: Understanding and Mitigating Hallucinations in Personalized LLMs. \emph{arXiv:2601.11000}, 2026. (body-text mentions of "PFQABench [cite]" should say the benchmark is introduced in this paper)
shridhar2021alfworld | OK
yao2022webshop | MINOR — full title: \bibitem{yao2022webshop} S. Yao et~al. WebShop: Towards Scalable Real-World Web Interaction with Grounded Language Agents. \emph{NeurIPS}, 2022.
yao2024taubench | MINOR — full title + ID: \bibitem{yao2024taubench} S. Yao et~al. $\tau$-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains. \emph{arXiv:2406.12045}, 2024.
lightman2023verify | OK
wang2023mathshepherd | OK
liu2023agentbench | OK
hao2023rap | OK

## Batch 4 (19 entries) — 0 HALLUCINATED, 3 MINOR, 16 OK

gui2024htp | OK
liu2023llmp | OK
lu2024dppm | MINOR — actual title: \bibitem{lu2024dppm} Z. Lu et~al. Decompose, plan in parallel, and merge: A novel paradigm for large language models based planning with multiple constraints. \emph{arXiv:2506.02683}, 2025.
yuan2025evoagent | OK
schick2023toolformer | OK
patil2023gorilla | OK
shen2023hugginggpt | MINOR — "Hugging Face" two words: \bibitem{shen2023hugginggpt} Y. Shen et~al. HuggingGPT: Solving AI tasks with ChatGPT and its friends in Hugging Face. \emph{NeurIPS}, 2023.
wang2023voyager | OK
park2023genagents | OK
wu2023autogen | MINOR — venue COLM 2024, not ICLR: \bibitem{wu2023autogen} Q. Wu et~al. AutoGen: Enabling next-gen LLM applications via multi-agent conversation. \emph{COLM}, 2024.
hong2023metagpt | OK
li2023camel | OK
du2023multiagentdebate | OK
chan2023chateval | OK
dubey2024llama3 | OK
jiang2023mistral | OK
yang2024qwen2.5 | OK
ouyang2022instructgpt | OK
openai2023gpt4 | OK

## Batch 3 (18 entries) — 4 HALLUCINATED, 0 MINOR, 14 OK

zhou2024selfdiscover..hao2024llmrwplanning: OK except:
tyen2024raffles | HALLUCINATED — real authors C. Zhu et al. (arXiv 2509.06822, EACL 2026): \bibitem{zhu2026raffles} C. Zhu et~al. RAFFLES: Reasoning-based attribution of faults for LLM systems. \emph{EACL}, 2026.
rozanov2025stateact | HALLUCINATED — real title: \bibitem{rozanov2025stateact} N. Rozanov and M. Rei. StateAct: Enhancing LLM base agents via self-prompting and state-tracking. \emph{arXiv:2410.02810}, 2024.
liu2024contextweaver | HALLUCINATED — real: Y. Wu et al. arXiv 2604.23069 (2026): \bibitem{wu2026contextweaver} Y. Wu et~al. ContextWeaver: Selective and dependency-structured memory construction for LLM agents. \emph{arXiv:2604.23069}, 2026.
peng2024theoremofthought | HALLUCINATED — real: S. Abdaljalil et al., KnowFM @ ACL 2025 (arXiv 2506.07106): \bibitem{abdaljalil2025theoremofthought} S. Abdaljalil et~al. Theorem-of-Thought: A multi-agent framework for abductive, deductive, and inductive reasoning in language models. \emph{KnowFM Workshop @ ACL}, 2025.

## Batch 5 (2026-09-15) — classical-diagnosis + agent-fault keys for Track B4

The classical keys below were added to `paper_final.tex` in commit efb8faa ("canonical FL citations") and their \bibitem entries already exist in the manuscript bibliography. Use these keys verbatim — do not invent new ones:

reiter1987diagnosis | OK — R. Reiter. A theory of diagnosis from first principles. \emph{Artificial Intelligence}, 32(1):57--95, 1987.
dekleer1987gde | OK — J. de~Kleer and B.~C. Williams. Diagnosing multiple faults. \emph{Artificial Intelligence}, 32(1):97--130, 1987.
jones2005tarantula | OK — J.~A. Jones and M.~J. Harrold. Empirical evaluation of the Tarantula automatic fault-localization technique. \emph{ASE}, 2005.
abreu2006ochiai | OK — R. Abreu et~al. An evaluation of similarity coefficients for software fault localization. \emph{PRDC}, 2006.
wong2016survey | OK — W.~E. Wong et~al. A survey on software fault localization. \emph{IEEE TSE}, 42(8):707--740, 2016.
zeller2002delta | OK — A. Zeller and R. Hildebrandt. Simplifying and isolating failure-inducing input. \emph{IEEE TSE}, 28(2):183--200, 2002.
weiser1981slicing | OK — M. Weiser. Program slicing. \emph{ICSE}, 1981.
halpern2005causes | OK — J.~Y. Halpern and J. Pearl. Causes and explanations: A structural-model approach. Part I: Causes. \emph{BJPS}, 56(4):843--887, 2005.
steinder2004survey | OK — M. Steinder and A.~S. Sethi. A survey of fault localization techniques in computer networks. \emph{Science of Computer Programming}, 53(2):165--194, 2004.
zhu2026raffles | OK — already audited in Batch 3.

NEW keys, verified against arXiv abs pages 2026-09-15 (not yet in paper_final.tex — add these \bibitem entries when the B4 draft is merged):

zhang2025whowhen | VERIFIED — arXiv:2505.00212, submitted 2025-04-30. Full author list confirmed (S. Zhang, M. Yin, J. Zhang, et al.). arXiv comments say "camera-ready" but the venue is not named on the abs page — cite as arXiv unless the venue is separately verified. \bibitem[Zhang et~al.(2025)]{zhang2025whowhen} S. Zhang et~al. Which agent causes task failures and when? On automated failure attribution of LLM multi-agent systems. \emph{arXiv:2505.00212}, 2025.
zhu2025agentdebug | VERIFIED — arXiv:2509.25370, submitted 2025-09-29, no venue on abs page. First author Kunlun Zhu (no relation to zhu2026raffles' C. Zhu — keep keys distinct). \bibitem[Zhu et~al.(2025)]{zhu2025agentdebug} K. Zhu et~al. Where LLM agents fail and how they can learn from failures. \emph{arXiv:2509.25370}, 2025.

## FINAL TALLY: 6 hallucinated (matches NeurIPS checker), 10 minor, 56 OK, 0 unverifiable.
Key renames (update \cite{} in body): tyen2024selfcorrect→he2025selfcorrect, tyen2024raffles→zhu2026raffles, liu2024contextweaver→wu2026contextweaver, peng2024theoremofthought→abdaljalil2025theoremofthought
