"""Real HotpotQA dataset adapter — fidelity anchor for the reconstruction
benchmarks.

Loads the actual HotpotQA validation split from HuggingFace
(`hotpot_qa`, `distractor` config) and exposes it as a
`BenchmarkExample` stream with the same shape as Profile-HotpotQA.

Why this exists.
The Profile-* benchmarks in this repo are programmatic reconstructions
designed to isolate profile-grounded failures with rule-based gold
labels. A reasonable reviewer concern is whether those reconstructions
faithfully represent task difficulty and the failure-mode distribution
of the original benchmarks they're inspired by. We address this
directly by also running on the unaltered HotpotQA dataset.

Adaptation choices.
* We use the `distractor` setting, which provides the gold supporting
  documents along with 8 distractors — i.e., the agent gets the
  same 10-paragraph context as in the published HotpotQA evaluation.
* We inject a synthetic user profile (5–7 spans) into the prompt
  exactly the same way Profile-HotpotQA does. The profile is
  informational/irrelevant to the factual question — the diagnostic is
  whether the agent's answer is contaminated by the profile (which it
  must not, since the question is factual).
* The verifier is a substring-match rule against `ex["answer"]` plus
  a profile-contamination check (any of the user's
  dietary/language/occupation/city tokens leaking into the answer).
* For attribution evaluation, real HotpotQA has no gold fault-node
  labels, so attribution metrics are not computed here — only success
  rate, profile-violation rate, and token cost.

This module is read-only: we never modify the HuggingFace cache.
"""

from __future__ import annotations

import random
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Literal

from ..schemas import (
    AssumptionDAG,
    GoldLabels,
    Severity,
    Trajectory,
    ViolationEvent,
)
from .base import BenchmarkExample
from .pfqa_recon import _build_profile

# ---------------------------------------------------------------------------
# Lazy-loaded HuggingFace dataset
# ---------------------------------------------------------------------------

_HF_DATASET = None  # cached after first access


def _load_hotpot(split: str) -> Any:
    global _HF_DATASET
    if _HF_DATASET is None or _HF_DATASET[0] != split:
        from datasets import load_dataset
        ds = load_dataset("hotpot_qa", "distractor", split=split, trust_remote_code=False)
        _HF_DATASET = (split, ds)
    return _HF_DATASET[1]


def _flatten_context(context: dict[str, Any], max_chars: int = 3500) -> str:
    """Render the HotpotQA context (titles + sentences) into a single string.

    Truncated to keep prompts within reasonable token budgets — full
    context can run 8k+ chars. We preserve title-keyed structure so the
    agent can still attribute facts to documents.
    """
    titles = context.get("title", [])
    sentence_lists = context.get("sentences", [])
    parts: list[str] = []
    used = 0
    for title, sents in zip(titles, sentence_lists):
        body = "".join(sents).strip()
        block = f"[{title}] {body}"
        if used + len(block) > max_chars:
            block = block[: max(0, max_chars - used)]
            parts.append(block)
            break
        parts.append(block)
        used += len(block) + 1
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Verifier rule
# ---------------------------------------------------------------------------


def _make_rule(meta: dict[str, Any]):
    """Substring-match for gold + profile-contamination check."""
    answer = (meta["answer"] or "").lower()
    profile_keywords = [k.lower() for k in meta.get("profile_keywords", [])]

    def rule(profile, task, trajectory, final_output):
        text = (final_output or "").lower()
        out: list[ViolationEvent] = []
        # Substring match — same convention as Profile-HotpotQA.
        if answer and answer not in text:
            # Also accept short-form yes/no for HotpotQA's binary 'comparison' type.
            if not (answer in {"yes", "no"} and (text.strip().startswith(answer))):
                out.append(ViolationEvent(
                    violation_id="v_real_hotpotqa_factual_miss",
                    step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                    violated_constraint=f"answer must contain factual gold ({meta['answer']!r})",
                    trajectory_text=(final_output or "")[:200],
                    severity=Severity.HIGH,
                    explanation="HotpotQA factual answer absent",
                ))
        contamination = [k for k in profile_keywords if k in text and len(k) > 2]
        if contamination:
            out.append(ViolationEvent(
                violation_id="v_real_hotpotqa_profile_contamination",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint="irrelevant profile context must not bias factual answer",
                trajectory_text=(final_output or "")[:200],
                severity=Severity.HIGH,
                explanation=f"answer leaked irrelevant profile term(s): {contamination}",
            ))
        return out

    rule.__name__ = "real_hotpotqa_factual_irrelevant_rule"
    return rule


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------


Split = Literal["train", "val", "test", "all"]


@dataclass
class HotpotQAReal:
    """Real HotpotQA via HuggingFace; profile is injected as irrelevant context."""

    n_examples: int = 100
    seed: int = 0
    split: Split = "all"
    train_frac: float = 0.6
    val_frac: float = 0.2
    hf_split: str = "validation"  # source split on HuggingFace
    max_context_chars: int = 3500

    @property
    def name(self) -> str:
        return "hotpotqa_real"

    def __len__(self) -> int:
        return len(self._indices())

    def __iter__(self) -> Iterator[BenchmarkExample]:
        for idx in self._indices():
            yield self._build_example(idx)

    def _indices(self) -> list[int]:
        n = self.n_examples
        train_end = int(n * self.train_frac)
        val_end = int(n * (self.train_frac + self.val_frac))
        if self.split == "train":
            return list(range(0, train_end))
        if self.split == "val":
            return list(range(train_end, val_end))
        if self.split == "test":
            return list(range(val_end, n))
        return list(range(n))

    def split_of(self, idx: int) -> Split:
        n = self.n_examples
        train_end = int(n * self.train_frac)
        val_end = int(n * (self.train_frac + self.val_frac))
        if idx < train_end:
            return "train"
        if idx < val_end:
            return "val"
        return "test"

    def _hotpot_index(self, idx: int) -> int:
        """Deterministic mapping from local idx → row index in the HF split.

        We sample `n_examples` rows by deterministic hash so different seeds
        select different subsets while still being reproducible.
        """
        ds = _load_hotpot(self.hf_split)
        total = len(ds)
        rng = random.Random(self.seed * 1_000_019 + idx)
        return rng.randint(0, total - 1)

    def _build_example(self, idx: int) -> BenchmarkExample:
        ds = _load_hotpot(self.hf_split)
        hot_idx = self._hotpot_index(idx)
        ex = ds[hot_idx]

        rng_profile = random.Random(self.seed * 1_000_021 + idx)
        profile, facts = _build_profile(rng_profile, idx)

        question = ex["question"]
        answer = ex["answer"]
        context_text = _flatten_context(ex["context"], max_chars=self.max_context_chars)
        prompt = (
            f"Use the following context to answer the question. "
            f"Answer in one sentence with the named entity or yes/no.\n\n"
            f"Context:\n{context_text}\n\n"
            f"Question: {question}"
        )

        # Profile keywords for contamination check (irrelevant-profile signal).
        profile_keywords = [
            facts["dietary"], facts["language"].lower(),
            facts["occupation"], facts["city"][0].lower(),
        ]
        condition_meta = {
            "answer": answer,
            "hotpot_id": ex["id"],
            "hotpot_type": ex["type"],
            "hotpot_level": ex.get("level", ""),
            "profile_keywords": profile_keywords,
        }
        rule = _make_rule(condition_meta)

        task_id = f"real_hotpotqa_{idx:05d}_{ex['id']}"
        task = {
            "task_id": task_id,
            "task_type": "real_hotpotqa",
            "condition": "factual_irrelevant_real",
            "prompt": prompt,
            "split": self.split_of(idx),
            "condition_meta": condition_meta,
        }
        gold = GoldLabels(success=None, correct_final_output=answer)
        return BenchmarkExample(
            task_id=task_id,
            dataset=self.name,
            profile=profile,
            task=task,
            trajectory=Trajectory(task_id=task_id, steps=[], final_output=None),
            dag=AssumptionDAG(task_id=task_id, nodes=[], edges=[]),
            gold=gold,
            rules=[rule],
            split=self.split_of(idx),
        )


__all__ = ["HotpotQAReal"]
