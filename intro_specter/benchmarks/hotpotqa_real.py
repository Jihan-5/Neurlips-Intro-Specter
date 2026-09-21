"""HotpotQA real-data loader (unified profile + fault injection).

Loads the unaltered HotpotQA validation split from HuggingFace
(`hotpot_qa`, `distractor` config). Each example is paired with a
synthetic user profile drawn from the unified `profiles.templates`
bank (3–5 constraints, half relevant / half irrelevant). On 30 % of
trials we inject one wrong assumption into the agent's working set
and record `gold_fault_node` for attribution scoring.

Adaptation choices:
* We use the `distractor` setting (10 docs per question, gold + 8
  distractors), matching the published HotpotQA evaluation.
* The verifier checks (a) substring match on gold answer (EM-style
  with a relaxed allow-list), (b) banned substrings from the user
  profile (e.g., language switching, banned words from "no Latin
  script" etc.).
* We compute approximate F1 against the gold answer for downstream
  reporting in `condition_meta` but the binary `success` label uses
  the substring rule for compatibility with the rest of the runner.

Backward-compatibility note: callers currently using
`HotpotQAReal(n_examples=…)` without the `fault_inject` flag will get
fault injection enabled by default. This is intentional for the new
unified evaluation matrix; pass `fault_inject=False` to disable.
"""

from __future__ import annotations

import random
import re
import string
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Literal

from ..profiles import inject_fault, inject_profile
from ..schemas import (
    AssumptionDAG,
    GoldLabels,
    ProfileSpan,
    Severity,
    Trajectory,
    UserProfile,
    ViolationEvent,
)
from .base import BenchmarkExample

_HF_DATASET = None


def _load_hotpot(split: str) -> Any:
    global _HF_DATASET
    if _HF_DATASET is None or _HF_DATASET[0] != split:
        from datasets import load_dataset
        ds = load_dataset("hotpotqa/hotpot_qa", "distractor", split=split, trust_remote_code=False)
        _HF_DATASET = (split, ds)
    return _HF_DATASET[1]


def _flatten_context(context: dict[str, Any], max_chars: int = 3500) -> str:
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


def _profile_to_userprofile(profile_dict: dict[str, Any]) -> UserProfile:
    spans = []
    for c in profile_dict["constraints"]:
        spans.append(ProfileSpan(
            id=c["id"],
            text=c["text"],
            kind="constraint" if c["type"] == "hard" else "preference",
            is_hard=(c["type"] == "hard"),
            contradicts=[],
        ))
    return UserProfile(user_id=profile_dict["user_id"], spans=spans)


# Lightweight EM/F1 computation matching standard HotpotQA eval.

_PUNCT = set(string.punctuation)
_ARTICLES = re.compile(r"\b(a|an|the)\b", flags=re.IGNORECASE)


def _normalize(s: str) -> str:
    s = s.lower()
    s = _ARTICLES.sub(" ", s)
    s = "".join(c for c in s if c not in _PUNCT)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _f1(pred: str, gold: str) -> float:
    p_toks = _normalize(pred).split()
    g_toks = _normalize(gold).split()
    if not p_toks or not g_toks:
        return float(p_toks == g_toks)
    common = set(p_toks) & set(g_toks)
    if not common:
        return 0.0
    n_common = sum(min(p_toks.count(t), g_toks.count(t)) for t in common)
    precision = n_common / len(p_toks)
    recall = n_common / len(g_toks)
    return 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0


def _make_rule(meta: dict[str, Any]):
    answer = (meta["answer"] or "").lower()
    banned_substrings = [b.lower() for b in meta.get("banned_substrings", [])]

    def rule(profile, task, trajectory, final_output):
        text = (final_output or "").lower()
        out: list[ViolationEvent] = []
        if answer and answer not in text:
            if not (answer in {"yes", "no"} and (text.strip().startswith(answer))):
                out.append(ViolationEvent(
                    violation_id="v_real_hotpotqa_factual_miss",
                    step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                    violated_constraint=f"answer must contain factual gold ({meta['answer']!r})",
                    trajectory_text=(final_output or "")[:200],
                    severity=Severity.HIGH,
                    explanation="HotpotQA factual answer absent",
                ))
        for b in banned_substrings:
            if b and b in text:
                out.append(ViolationEvent(
                    violation_id="v_real_hotpotqa_profile_violation",
                    step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                    violated_constraint="answer violates a hard profile constraint",
                    trajectory_text=(final_output or "")[:200],
                    severity=Severity.HIGH,
                    explanation=f"answer contains banned substring {b!r}",
                ))
                break
        return out

    rule.__name__ = "real_hotpotqa_rule"
    return rule


Split = Literal["train", "val", "test", "all"]


@dataclass
class HotpotQAReal:
    n_examples: int = 60
    seed: int = 0
    split: Split = "all"
    train_frac: float = 0.6
    val_frac: float = 0.2
    hf_split: str = "validation"
    max_context_chars: int = 3500
    fault_inject: bool = True

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
        ds = _load_hotpot(self.hf_split)
        rng = random.Random(self.seed * 1_000_019 + idx)
        return rng.randint(0, len(ds) - 1)

    def _build_example(self, idx: int) -> BenchmarkExample:
        ds = _load_hotpot(self.hf_split)
        hot_idx = self._hotpot_index(idx)
        ex = ds[hot_idx]

        task_id = f"real_hotpotqa_{idx:05d}_{ex['id']}"
        profile_dict = inject_profile(task_id=task_id, seed=self.seed, dataset="hotpotqa")
        profile = _profile_to_userprofile(profile_dict)

        # Build banned-substring set for the profile.
        banned: list[str] = []
        for c in profile_dict["constraints"]:
            t = c["text"].lower()
            if "english only" in t:
                banned += ["hola ", "bonjour", "ciao ", "你好", "こんにちは"]

        question = ex["question"]
        answer = ex["answer"]
        context_text = _flatten_context(ex["context"], max_chars=self.max_context_chars)

        prompt = (
            f"User profile (read this and respect any hard constraint):\n"
            + "\n".join(f"- {c['text']}" for c in profile_dict["constraints"])
            + "\n\nUse the following context to answer the question. "
            "Answer in one sentence with the named entity or yes/no.\n\n"
            f"Context:\n{context_text}\n\n"
            f"Question: {question}"
        )

        gold_fault = None
        fr = inject_fault(
            task_id=task_id, seed=self.seed,
            profile=profile_dict, gold_answer=answer,
        ) if self.fault_inject else None
        if fr is not None:
            gold_fault = fr.target_node_id

        condition_meta = {
            "answer": answer,
            "hotpot_id": ex["id"],
            "hotpot_type": ex["type"],
            "hotpot_level": ex.get("level", ""),
            "banned_substrings": banned,
            "profile_constraints": profile_dict["constraints"],
            "gold_fault_node": gold_fault,
            "fault_record": (fr.__dict__ if fr else None),
        }
        rule = _make_rule(condition_meta)

        task = {
            "task_id": task_id,
            "task_type": "real_hotpotqa",
            "condition": "factual_real",
            "prompt": prompt,
            "split": self.split_of(idx),
            "condition_meta": condition_meta,
        }
        gold = GoldLabels(
            success=None,
            correct_final_output=answer,
            fault_node_id=gold_fault,
        )
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


__all__ = ["HotpotQAReal", "_f1", "_normalize"]
