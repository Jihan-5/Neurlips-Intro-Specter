"""Real LongMemEval benchmark.

Loads the unaltered LongMemEval-Oracle JSON from HuggingFace
(`xiaowu0162/longmemeval-cleaned`, longmemeval_oracle.json, 500
examples) and exposes it as a `BenchmarkExample` stream. Mirrors the
pattern of `hotpotqa_real.py`, adapted for the longer multi-session
chat-history context.

LongMemEval is the closest publicly available analog to PFQABench's
intent: long-history user-conditioned reasoning. Each example asks a
question whose answer requires retrieving + composing facts from
multiple prior chat sessions. The "oracle" variant retains only the
evidence sessions, keeping prompts manageable (~5-15k tokens of
conversational context).

Schema (from xiaowu0162/longmemeval-cleaned):
    question_id, question_type (e.g., 'temporal-reasoning',
        'multi-session', 'preference', 'knowledge-update'),
    question, answer, question_date,
    haystack_dates, haystack_session_ids, haystack_sessions
    (list of dialogues; each dialogue is list of {role, content}).

Verifier rule: substring match on `answer` plus the standard
profile-violation banned-substring check.
"""

from __future__ import annotations

import json
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

_HF_DATASET = None  # cached after first access


def _load() -> list[dict]:
    global _HF_DATASET
    if _HF_DATASET is not None:
        return _HF_DATASET
    from huggingface_hub import hf_hub_download
    path = hf_hub_download(
        repo_id="xiaowu0162/longmemeval-cleaned",
        filename="longmemeval_oracle.json",
        repo_type="dataset",
    )
    with open(path) as f:
        data = json.load(f)
    _HF_DATASET = data
    return data


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


_PUNCT = set(string.punctuation)
_ARTICLES = re.compile(r"\b(a|an|the)\b", flags=re.IGNORECASE)


def _normalize(s: str) -> str:
    s = (s or "").lower()
    s = _ARTICLES.sub(" ", s)
    s = "".join(c for c in s if c not in _PUNCT)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _flatten_sessions(sessions: list[list[dict]], dates: list[str],
                      max_chars: int = 4500) -> str:
    """Render LongMemEval haystack sessions into a single conversational
    transcript, dated, truncated to fit prompt budget."""
    parts: list[str] = []
    used = 0
    for date, session in zip(dates, sessions):
        header = f"[Session {date}]"
        block_lines = [header]
        for turn in session:
            role = turn.get("role", "?")
            content = turn.get("content", "")
            line = f"  {role}: {content}"
            block_lines.append(line)
        block = "\n".join(block_lines)
        if used + len(block) > max_chars:
            block = block[: max(0, max_chars - used)]
            parts.append(block)
            break
        parts.append(block)
        used += len(block) + 1
    return "\n\n".join(parts)


def _make_rule(meta: dict[str, Any]):
    answer = str(meta["answer"] or "").lower()
    banned_substrings = [b.lower() for b in meta.get("banned_substrings", [])]

    def rule(profile, task, trajectory, final_output):
        text = (final_output or "").lower()
        out: list[ViolationEvent] = []
        if answer and answer not in text:
            out.append(ViolationEvent(
                violation_id="v_real_lme_factual_miss",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint=f"answer must contain factual gold ({meta['answer']!r})",
                trajectory_text=(final_output or "")[:200],
                severity=Severity.HIGH,
                explanation="LongMemEval factual answer absent",
            ))
        for b in banned_substrings:
            if b and b in text:
                out.append(ViolationEvent(
                    violation_id="v_real_lme_profile_violation",
                    step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                    violated_constraint="answer violates a hard profile constraint",
                    trajectory_text=(final_output or "")[:200],
                    severity=Severity.HIGH,
                    explanation=f"answer contains banned substring {b!r}",
                ))
                break
        return out

    rule.__name__ = "real_longmemeval_rule"
    return rule


Split = Literal["train", "val", "test", "all"]


@dataclass
class LongMemEvalReal:
    """LongMemEval-Oracle via HuggingFace; profile injected as additional
    constraint context on top of the chat-history haystack."""

    n_examples: int = 60
    seed: int = 42
    split: Split = "all"
    train_frac: float = 0.6
    val_frac: float = 0.2
    max_context_chars: int = 4500
    fault_inject: bool = True

    @property
    def name(self) -> str:
        return "longmemeval_real"

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

    def _hf_index(self, idx: int) -> int:
        rows = _load()
        rng = random.Random(self.seed * 1_000_043 + idx)
        return rng.randint(0, len(rows) - 1)

    def _build_example(self, idx: int) -> BenchmarkExample:
        rows = _load()
        hf_idx = self._hf_index(idx)
        ex = rows[hf_idx]

        task_id = f"real_lme_{idx:05d}_{ex['question_id']}"
        # Use hotpotqa profile category since LongMemEval is QA-style.
        profile_dict = inject_profile(task_id=task_id, seed=self.seed, dataset="hotpotqa")
        profile = _profile_to_userprofile(profile_dict)

        banned: list[str] = []
        for c in profile_dict["constraints"]:
            if "english only" in c["text"].lower():
                banned += ["hola ", "bonjour", "ciao ", "你好", "こんにちは"]

        question = str(ex["question"])
        answer = str(ex["answer"]) if ex["answer"] is not None else ""
        sessions_text = _flatten_sessions(
            ex["haystack_sessions"], ex["haystack_dates"],
            max_chars=self.max_context_chars,
        )

        prompt = (
            "User profile (read this and respect any hard constraint):\n"
            + "\n".join(f"- {c['text']}" for c in profile_dict["constraints"])
            + "\n\nThe following are prior chat sessions between the user and "
            "an assistant. Use them to answer the question. Answer in one "
            "concise sentence with the specific entity, date, or fact.\n\n"
            f"Chat history:\n{sessions_text}\n\n"
            f"Current date: {ex.get('question_date', '')}\n"
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
            "lme_question_id": ex["question_id"],
            "lme_question_type": ex.get("question_type", ""),
            "banned_substrings": banned,
            "profile_constraints": profile_dict["constraints"],
            "gold_fault_node": gold_fault,
            "fault_record": (fr.__dict__ if fr else None),
        }
        rule = _make_rule(condition_meta)

        task = {
            "task_id": task_id,
            "task_type": "real_longmemeval",
            "condition": "long_memory_real",
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


__all__ = ["LongMemEvalReal"]
