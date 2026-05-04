"""Real 2WikiMultiHopQA benchmark.

Loads the unaltered 2WikiMultihopQA dev split from HuggingFace
(`xanhho/2WikiMultihopQA`, dev.parquet, 12,576 examples) and exposes
it as a `BenchmarkExample` stream. Mirrors `hotpotqa_real.py`.

The dataset's `context` field is a JSON-string-encoded list of
[title, sentences] tuples; we parse and flatten the same way as
HotpotQA distractor.
"""

from __future__ import annotations

import ast
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


def _load(split: str = "dev") -> list[dict]:
    global _HF_DATASET
    if _HF_DATASET is not None and _HF_DATASET[0] == split:
        return _HF_DATASET[1]
    from huggingface_hub import hf_hub_download
    import pandas as pd
    fname = "dev.parquet" if split == "dev" else f"{split}.parquet"
    path = hf_hub_download(repo_id="xanhho/2WikiMultihopQA",
                            filename=fname, repo_type="dataset")
    df = pd.read_parquet(path)
    rows = df.to_dict(orient="records")
    _HF_DATASET = (split, rows)
    return rows


def _parse_context(ctx: Any) -> list[tuple[str, list[str]]]:
    """Parse the context field. May be a list, a JSON string, or a Python literal."""
    if isinstance(ctx, list):
        parsed = ctx
    elif isinstance(ctx, str):
        try:
            parsed = json.loads(ctx)
        except (json.JSONDecodeError, ValueError):
            try:
                parsed = ast.literal_eval(ctx)
            except (ValueError, SyntaxError):
                return []
    else:
        return []
    out: list[tuple[str, list[str]]] = []
    for item in parsed:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            title, sents = item
            if isinstance(sents, list):
                out.append((str(title), [str(s) for s in sents]))
    return out


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


def _flatten_context(parsed: list[tuple[str, list[str]]], max_chars: int = 3500) -> str:
    parts: list[str] = []
    used = 0
    for title, sents in parsed:
        body = "".join(sents).strip()
        block = f"[{title}] {body}"
        if used + len(block) > max_chars:
            block = block[: max(0, max_chars - used)]
            parts.append(block)
            break
        parts.append(block)
        used += len(block) + 1
    return "\n".join(parts)


def _make_rule(meta: dict[str, Any]):
    answer = (meta["answer"] or "").lower()
    banned_substrings = [b.lower() for b in meta.get("banned_substrings", [])]

    def rule(profile, task, trajectory, final_output):
        text = (final_output or "").lower()
        out: list[ViolationEvent] = []
        if answer and answer not in text:
            if not (answer in {"yes", "no"} and (text.strip().startswith(answer))):
                out.append(ViolationEvent(
                    violation_id="v_real_2wiki_factual_miss",
                    step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                    violated_constraint=f"answer must contain factual gold ({meta['answer']!r})",
                    trajectory_text=(final_output or "")[:200],
                    severity=Severity.HIGH,
                    explanation="2WikiMultiHopQA factual answer absent",
                ))
        for b in banned_substrings:
            if b and b in text:
                out.append(ViolationEvent(
                    violation_id="v_real_2wiki_profile_violation",
                    step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                    violated_constraint="answer violates a hard profile constraint",
                    trajectory_text=(final_output or "")[:200],
                    severity=Severity.HIGH,
                    explanation=f"answer contains banned substring {b!r}",
                ))
                break
        return out

    rule.__name__ = "real_2wiki_rule"
    return rule


Split = Literal["train", "val", "test", "all"]


@dataclass
class TwoWikiReal:
    n_examples: int = 60
    seed: int = 42
    split: Split = "all"
    train_frac: float = 0.6
    val_frac: float = 0.2
    hf_split: str = "dev"
    max_context_chars: int = 3500
    fault_inject: bool = True

    @property
    def name(self) -> str:
        return "twowiki_real"

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
        rows = _load(self.hf_split)
        rng = random.Random(self.seed * 1_000_039 + idx)
        return rng.randint(0, len(rows) - 1)

    def _build_example(self, idx: int) -> BenchmarkExample:
        rows = _load(self.hf_split)
        hf_idx = self._hf_index(idx)
        ex = rows[hf_idx]

        task_id = f"real_2wiki_{idx:05d}_{ex['_id']}"
        profile_dict = inject_profile(task_id=task_id, seed=self.seed, dataset="hotpotqa")
        profile = _profile_to_userprofile(profile_dict)

        banned: list[str] = []
        for c in profile_dict["constraints"]:
            if "english only" in c["text"].lower():
                banned += ["hola ", "bonjour", "ciao ", "你好", "こんにちは"]

        question = ex["question"]
        answer = ex["answer"]
        parsed_ctx = _parse_context(ex["context"])
        context_text = _flatten_context(parsed_ctx, max_chars=self.max_context_chars)

        prompt = (
            "User profile (read this and respect any hard constraint):\n"
            + "\n".join(f"- {c['text']}" for c in profile_dict["constraints"])
            + "\n\nUse the following paragraphs to answer the multi-hop question. "
            "Answer in one sentence with the named entity or yes/no.\n\n"
            f"Paragraphs:\n{context_text}\n\n"
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
            "twowiki_id": ex["_id"],
            "twowiki_type": ex.get("type", ""),
            "banned_substrings": banned,
            "profile_constraints": profile_dict["constraints"],
            "gold_fault_node": gold_fault,
            "fault_record": (fr.__dict__ if fr else None),
        }
        rule = _make_rule(condition_meta)

        task = {
            "task_id": task_id,
            "task_type": "real_2wiki",
            "condition": "factual_2hop_real",
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


__all__ = ["TwoWikiReal"]
