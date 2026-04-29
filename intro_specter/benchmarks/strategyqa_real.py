"""StrategyQA real-data loader.

Loads the unaltered StrategyQA train split from HuggingFace
(`ChilleD/StrategyQA`, 1,603 yes/no questions) and exposes it as a
`BenchmarkExample` stream with profile injection and 30 % controlled
fault injection.

Why use the train split? StrategyQA's official test split has hidden
labels. The train split has gold yes/no answers, the bridging
`facts`, and `term`/`description` metadata — sufficient for our
evaluation.

Profile-grounded twist: each example is paired with a synthetic user
profile (3–5 constraints, half relevant / half irrelevant). The
verifier checks (a) yes/no polarity match against gold and (b) that
the answer doesn't violate any hard profile constraint (e.g.,
language-switching for an "English only" user).

Fault-injection condition: on ~30 % of trials we inject one wrong
assumption into the agent's working set and record `gold_fault_node`
for attribution scoring.
"""

from __future__ import annotations

import random
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
from .strategyqa_recon import _yes_no_polarity  # reuse the polarity extractor

_HF_DATASET = None


def _load(split: str = "train") -> Any:
    global _HF_DATASET
    if _HF_DATASET is None or _HF_DATASET[0] != split:
        from datasets import load_dataset
        ds = load_dataset("ChilleD/StrategyQA", split=split)
        _HF_DATASET = (split, ds)
    return _HF_DATASET[1]


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


def _make_rule(meta: dict[str, Any]):
    gold = "yes" if meta["gold_answer"] else "no"
    banned_substrings = [b.lower() for b in meta.get("banned_substrings", [])]

    def rule(profile, task, trajectory, final_output):
        text = (final_output or "")
        polarity = _yes_no_polarity(text)
        out: list[ViolationEvent] = []
        if polarity != gold:
            out.append(ViolationEvent(
                violation_id="v_strategyqa_real_polarity_miss",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint=f"answer must be {gold!r}",
                trajectory_text=text[:200],
                severity=Severity.HIGH,
                explanation=f"polarity wrong: got {polarity!r}",
            ))
        for b in banned_substrings:
            if b and b in text.lower():
                out.append(ViolationEvent(
                    violation_id="v_strategyqa_real_profile_violation",
                    step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                    violated_constraint="answer violates a hard profile constraint",
                    trajectory_text=text[:200],
                    severity=Severity.HIGH,
                    explanation=f"answer contains banned substring {b!r}",
                ))
                break
        return out

    rule.__name__ = "strategyqa_real_rule"
    return rule


Split = Literal["train", "val", "test", "all"]


@dataclass
class StrategyQAReal:
    n_examples: int = 60
    seed: int = 0
    split: Split = "all"
    train_frac: float = 0.6
    val_frac: float = 0.2
    hf_split: str = "train"
    fault_inject: bool = True

    @property
    def name(self) -> str:
        return "strategyqa_real"

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
        ds = _load(self.hf_split)
        rng = random.Random(self.seed * 1_000_029 + idx)
        return rng.randint(0, len(ds) - 1)

    def _build_example(self, idx: int) -> BenchmarkExample:
        ds = _load(self.hf_split)
        hot_idx = self._hf_index(idx)
        ex = ds[hot_idx]

        task_id = f"strategyqa_real_{idx:05d}_{ex['qid']}"
        profile_dict = inject_profile(task_id=task_id, seed=self.seed, dataset="strategyqa")
        profile = _profile_to_userprofile(profile_dict)

        banned = []
        for c in profile_dict["constraints"]:
            if "english only" in c["text"].lower():
                banned += ["hola ", "bonjour", "ciao ", "你好", "こんにちは"]
            if "concise" in c["text"].lower() or "under 20 words" in c["text"].lower():
                pass

        prompt = (
            f"Profile note (informational): the user has stated:\n"
            + "\n".join(f"- {c['text']}" for c in profile_dict["constraints"])
            + f"\n\nQuestion: {ex['question']}\n\n"
            f"Answer with 'yes' or 'no' on a single line, then a one-sentence justification."
        )

        gold_fault = None
        fr = inject_fault(
            task_id=task_id, seed=self.seed,
            profile=profile_dict, gold_answer=("yes" if ex["answer"] else "no"),
        ) if self.fault_inject else None
        if fr is not None:
            gold_fault = fr.target_node_id

        condition_meta = {
            "gold_answer": bool(ex["answer"]),
            "facts": ex.get("facts", ""),
            "term": ex.get("term", ""),
            "description": ex.get("description", ""),
            "banned_substrings": banned,
            "profile_constraints": profile_dict["constraints"],
            "gold_fault_node": gold_fault,
            "fault_record": (fr.__dict__ if fr else None),
        }
        rule = _make_rule(condition_meta)

        task = {
            "task_id": task_id,
            "task_type": "strategyqa_real",
            "condition": "implicit_yesno_real",
            "prompt": prompt,
            "split": self.split_of(idx),
            "condition_meta": condition_meta,
        }
        gold = GoldLabels(
            success=None,
            correct_final_output=("yes" if ex["answer"] else "no"),
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


__all__ = ["StrategyQAReal"]
