"""Real MuSiQue benchmark (3-hop subset).

Loads the unaltered MuSiQue-Ans validation split from HuggingFace
(`dgslibisey/MuSiQue`) and exposes the 3-hop subset as a stream of
`BenchmarkExample`s. Mirrors the structure of `hotpotqa_real.py` —
profile + 30% fault injection from `intro_specter.profiles`, substring
verifier with banned-substring contamination check, and EM/F1 helpers
on the dataset's gold answer.

Why 3-hop only: 2-hop MuSiQue is too close to HotpotQA in difficulty;
the deep-DAG case is where IS's posterior attribution should pay off.
The dev split has 760 3-hop examples, well above our n=60 sample.
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

_HF_DATASET = None  # cached {(split, hop_filter): filtered_list}


def _load_3hop(split: str = "validation") -> list[dict]:
    """Return the 3-hop subset of MuSiQue-Ans dev as a plain list, cached."""
    global _HF_DATASET
    key = (split, "3hop")
    if _HF_DATASET is not None and _HF_DATASET[0] == key:
        return _HF_DATASET[1]
    from datasets import load_dataset
    ds = load_dataset("dgslibisey/MuSiQue", split=split)
    rows = [ex for ex in ds if str(ex.get("id", "")).startswith("3hop")]
    _HF_DATASET = (key, rows)
    return rows


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


# Lightweight EM/F1 (HotpotQA-style normalization).
_PUNCT = set(string.punctuation)
_ARTICLES = re.compile(r"\b(a|an|the)\b", flags=re.IGNORECASE)


def _normalize(s: str) -> str:
    s = (s or "").lower()
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
    p = n_common / len(p_toks)
    r = n_common / len(g_toks)
    return 2 * p * r / (p + r) if (p + r) else 0.0


def _flatten_paragraphs(paragraphs: list[dict[str, Any]], max_chars: int = 3500) -> str:
    """Render MuSiQue's paragraph list (title + text) into a single string,
    truncated to keep prompts under the LLM input budget."""
    parts: list[str] = []
    used = 0
    for p in paragraphs:
        title = p.get("title", "")
        text = p.get("paragraph_text", "").strip()
        block = f"[{title}] {text}"
        if used + len(block) > max_chars:
            block = block[: max(0, max_chars - used)]
            parts.append(block)
            break
        parts.append(block)
        used += len(block) + 1
    return "\n".join(parts)


def _make_rule(meta: dict[str, Any]):
    """Substring verifier on gold answer (with aliases) + profile-contamination check."""
    answers = [a.lower() for a in meta["answers"] if a]
    banned_substrings = [b.lower() for b in meta.get("banned_substrings", [])]

    def rule(profile, task, trajectory, final_output):
        text = (final_output or "").lower()
        out: list[ViolationEvent] = []
        if answers and not any(a in text for a in answers):
            out.append(ViolationEvent(
                violation_id="v_real_musique_factual_miss",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint=f"answer must contain factual gold ({meta['gold_answer']!r}) or an alias",
                trajectory_text=(final_output or "")[:200],
                severity=Severity.HIGH,
                explanation="MuSiQue 3-hop factual answer absent",
            ))
        for b in banned_substrings:
            if b and b in text:
                out.append(ViolationEvent(
                    violation_id="v_real_musique_profile_violation",
                    step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                    violated_constraint="answer violates a hard profile constraint",
                    trajectory_text=(final_output or "")[:200],
                    severity=Severity.HIGH,
                    explanation=f"answer contains banned substring {b!r}",
                ))
                break
        return out

    rule.__name__ = "real_musique_rule"
    return rule


Split = Literal["train", "val", "test", "all"]


@dataclass
class MuSiQueReal:
    """Real MuSiQue 3-hop via HuggingFace; profile injected as irrelevant context.

    `n_examples` requested; if the dev split has fewer 3-hop examples
    than requested we use all of them (and `actual_n` is recorded in
    `condition_meta`).
    """

    n_examples: int = 60
    seed: int = 42
    split: Split = "all"
    train_frac: float = 0.6
    val_frac: float = 0.2
    hf_split: str = "validation"
    max_context_chars: int = 3500
    fault_inject: bool = True

    @property
    def name(self) -> str:
        return "musique_real"

    def __len__(self) -> int:
        return len(self._indices())

    def __iter__(self) -> Iterator[BenchmarkExample]:
        for idx in self._indices():
            yield self._build_example(idx)

    def _indices(self) -> list[int]:
        # Cap n_examples by available 3-hop rows in dev.
        rows = _load_3hop(self.hf_split)
        n = min(self.n_examples, len(rows))
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
        rows = _load_3hop(self.hf_split)
        n = min(self.n_examples, len(rows))
        train_end = int(n * self.train_frac)
        val_end = int(n * (self.train_frac + self.val_frac))
        if idx < train_end:
            return "train"
        if idx < val_end:
            return "val"
        return "test"

    def _hf_index(self, idx: int) -> int:
        """Deterministic mapping from local idx → row index in the 3-hop list."""
        rows = _load_3hop(self.hf_split)
        rng = random.Random(self.seed * 1_000_037 + idx)
        return rng.randint(0, len(rows) - 1)

    def _build_example(self, idx: int) -> BenchmarkExample:
        rows = _load_3hop(self.hf_split)
        hf_idx = self._hf_index(idx)
        ex = rows[hf_idx]

        task_id = f"real_musique_{idx:05d}_{ex['id']}"
        profile_dict = inject_profile(task_id=task_id, seed=self.seed, dataset="hotpotqa")
        # Reusing the "hotpotqa" profile category since both are factual multi-hop QA;
        # adversarial-truthfulqa templates aren't appropriate here.
        profile = _profile_to_userprofile(profile_dict)

        banned: list[str] = []
        for c in profile_dict["constraints"]:
            t = c["text"].lower()
            if "english only" in t:
                banned += ["hola ", "bonjour", "ciao ", "你好", "こんにちは"]

        question = ex["question"]
        gold_answer = ex["answer"]
        answer_aliases = list(ex.get("answer_aliases", []) or [])
        all_answers = [gold_answer] + answer_aliases
        context_text = _flatten_paragraphs(ex["paragraphs"], max_chars=self.max_context_chars)

        prompt = (
            "User profile (read this and respect any hard constraint):\n"
            + "\n".join(f"- {c['text']}" for c in profile_dict["constraints"])
            + "\n\nUse the following paragraphs to answer a 3-hop question. "
            "Answer in one sentence with the named entity.\n\n"
            f"Paragraphs:\n{context_text}\n\n"
            f"Question: {question}"
        )

        gold_fault = None
        fr = inject_fault(
            task_id=task_id, seed=self.seed,
            profile=profile_dict, gold_answer=gold_answer,
        ) if self.fault_inject else None
        if fr is not None:
            gold_fault = fr.target_node_id

        condition_meta = {
            "gold_answer": gold_answer,
            "answers": all_answers,
            "musique_id": ex["id"],
            "musique_hops": 3,
            "actual_n": min(self.n_examples, len(rows)),
            "banned_substrings": banned,
            "profile_constraints": profile_dict["constraints"],
            "gold_fault_node": gold_fault,
            "fault_record": (fr.__dict__ if fr else None),
        }
        rule = _make_rule(condition_meta)

        task = {
            "task_id": task_id,
            "task_type": "real_musique",
            "condition": "factual_3hop_real",
            "prompt": prompt,
            "split": self.split_of(idx),
            "condition_meta": condition_meta,
        }
        gold = GoldLabels(
            success=None,
            correct_final_output=gold_answer,
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


__all__ = ["MuSiQueReal", "_f1", "_normalize"]
