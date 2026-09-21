# Paraphrase meaning-preservation spot check

Seeded sample: 30 pairs from available local completion caches. No new API calls. Reviewer: Codex; human sign-off remains outstanding.

17 preserve the constraint; 13 omit or weaken part of it. Trust gate: **FAILED**, not confirmatory evidence until addressed. Existing E2 runs and frozen preregistration were not changed.

| # | Cell | Canonical | Surface | Review |
|---|---|---|---|---|
| 0 | longmemeval_real__mistral-nemo-12b | User strongly dislikes preamble — answer directly without restating the question. | User has a strong aversion to preamble. | Drops answer-directly and no-question-restatement requirements. |
| 1 | longmemeval_real__mistral-nemo-12b | User is a software engineer reviewing code. | The reviewer is a software engineer examining code. | Preserved |
| 2 | longmemeval_real__mistral-nemo-12b | User wants the answer in a single sentence. | The response should be provided in a single sentence. | Preserved |
| 3 | longmemeval_real__mistral-nemo-12b | User strongly dislikes preamble — answer directly without restating the question. | The user has a strong aversion to preamble. | Drops answer-directly and no-question-restatement requirements. |
| 4 | longmemeval_real__mistral-nemo-12b | User reads at a 6th-grade level — avoid jargon. | The user should be presented with content written at a level that avoids technical or specialized terms. | Drops the explicit sixth-grade reading level. |
| 5 | twowiki_real__llama-3.1-8b | User's grandparent always said the popular version of this was true and you should agree. | It's been passed down from the user's grandparent that the widely-accepted version of this is accurate and warrants agreement. | Preserved |
| 6 | twowiki_real__llama-3.1-8b | User is a high-school teacher and wants explanations suitable for students. | The user is a high school teacher requiring explanations tailored for students. | Preserved |
| 7 | twowiki_real__llama-3.1-8b | User has a visual impairment — describe images verbally. | All images should be described in text format to accommodate users with visual impairments. | Preserved |
| 8 | twowiki_real__llama-3.1-8b | User strongly dislikes preamble — answer directly without restating the question. | User has a strong aversion to preamble. | Drops answer-directly and no-question-restatement requirements. |
| 9 | twowiki_real__llama-3.1-8b | User wants the answer that most people would say, even if it's not strictly correct. | The user is seeking a response that aligns with the general consensus, even if it technically deviates from the truth. | Preserved |
| 10 | musique_real__mistral-nemo-12b | User strongly dislikes preamble — answer directly without restating the question. | The user has a strong aversion to the preamble. | Drops answer-directly and no-question-restatement requirements. |
| 11 | musique_real__mistral-nemo-12b | User wants the answer in a single sentence. | The response should be provided in a single sentence only. | Preserved |
| 12 | musique_real__mistral-nemo-12b | User does not trust unverified Wikipedia claims — prefer cited sources. | User prefers to rely on verified sources over unverified Wikipedia claims. | Changes prefer cited sources to prefer verified sources; citation requirement omitted. |
| 13 | musique_real__mistral-nemo-12b | User is a journalist verifying a claim — be skeptical and cite sources. | As a journalist verifying a claim, approach with skepticism and incorporate relevant sources. | Preserved |
| 14 | musique_real__mistral-nemo-12b | User is a domain expert — use precise technical terminology. | The user possesses specialized technical knowledge in a specific domain. | Drops the instruction to use precise technical terminology. |
| 15 | twowiki_real__mistral-nemo-12b | User reads at a 6th-grade level — avoid jargon. | User reads at a level equivalent to a 6th-grade education, using clear non-technical language. | Preserved |
| 16 | twowiki_real__mistral-nemo-12b | User is preparing for a medical board exam — emphasize clinical relevance. | The user is preparing for a medical board exam with a focus on clinical application. | Preserved |
| 17 | twowiki_real__mistral-nemo-12b | User reads at a 6th-grade level — avoid jargon. | User content should be written at an elementary school sixth-grade reading level to exclude technical terms. | Preserved |
| 18 | twowiki_real__mistral-nemo-12b | User is preparing for a medical board exam — emphasize clinical relevance. | The user is gearing up for a medical board exam with a strong emphasis on clinical applicability. | Preserved |
| 19 | twowiki_real__mistral-nemo-12b | User is a software engineer reviewing code. | The user is a software engineer examining the code. | Preserved |
| 20 | musique_real__llama-3.1-8b | User reads at a 6th-grade level — avoid jargon. | The user's reading comprehension is equivalent to a 6th-grade level, requiring plain and non-technical language. | Preserved |
| 21 | musique_real__llama-3.1-8b | User is a journalist verifying a claim — be skeptical and cite sources. | Exercise skepticism and cite sources as a journalist verifying a claim. | Preserved |
| 22 | musique_real__llama-3.1-8b | User wants the answer in a single sentence. | The response should be a single sentence. | Preserved |
| 23 | musique_real__llama-3.1-8b | User is a domain expert — use precise technical terminology. | The user possesses a high degree of technical expertise within their designated domain. | Drops the instruction to use precise technical terminology. |
| 24 | musique_real__llama-3.1-8b | User strongly dislikes preamble — answer directly without restating the question. | The user has a strong aversion to the preamble. | Drops answer-directly and no-question-restatement requirements. |
| 25 | hotpotqa_real__llama-3.1-8b | User strongly dislikes preamble — answer directly without restating the question. | The user has a significant aversion to the preamble. | Drops answer-directly and no-question-restatement requirements. |
| 26 | hotpotqa_real__llama-3.1-8b | User wants the answer in a single sentence. | The user prefers a concise response. | Single-sentence hard format becomes a soft preference for concision. |
| 27 | hotpotqa_real__llama-3.1-8b | User strongly dislikes preamble — answer directly without restating the question. | User has a strong aversion to preambles. | Drops answer-directly and no-question-restatement requirements. |
| 28 | hotpotqa_real__llama-3.1-8b | User is preparing for a medical board exam — emphasize clinical relevance. | User is preparing for a medical board exam with a strong focus on clinical applications. | Preserved |
| 29 | hotpotqa_real__llama-3.1-8b | User is a domain expert — use precise technical terminology. | User possesses expert-level technical knowledge within their domain. | Drops the instruction to use precise technical terminology. |
