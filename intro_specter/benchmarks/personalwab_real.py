"""PersonalWAB (WWW'25) real-data loader -- single-turn personalized
recommendation track.

Loads the PersonalWAB benchmark data (HongruCai/PersonalWAB; 1,000 real
Amazon users, behavior-grounded profiles, CC BY-NC 4.0) and exposes the
SINGLE-TURN personalized-recommendation task as a `BenchmarkExample`
stream, structurally mirroring `travelplanner_real.py` /
`amazon_products_real.py`.

Data source (verified counts from the shipped files, not README claims)
-----------------------------------------------------------------------
The PersonalWAB repo ships its data in-tree at
`PersonalWAB/envs/pwab/data/`:

* `user_profiles.json`      -- 1,000 users, each an 11-field behavioral
  profile (Gender, Age, Occupation, Price Sensitivity, Shopping
  Interest, Brand Preference, Diversity Preference, Interaction
  Complexity, Tone and Style, Item Reference, Focus Aspect) distilled
  from real Amazon review histories.
* `user_history_part_*.json` -- 1,000 users, 40,648 real product
  interactions (product_info + the user's actual review incl. rating,
  text, parent_asin, timestamp).
* `user_instructions.json`  -- train 6,896 / test 2,174 instructions;
  test split: 757 recommend, 723 review, 694 search. Each row: user_id,
  natural-language task, timestamp, and a ground-truth `target` product
  the user GENUINELY interacted with (the interaction at that same
  timestamp in their history).
* `all_products_part_*.json` -- 35,772 real Amazon products.

This module reads a slimmed one-file snapshot (`compact_recommend.json`,
built deterministically from the raw files by the campaign prep script;
same counts as above) to keep per-process memory small -- 3 model
processes run in parallel on a swap-tight machine. Set
`PERSONALWAB_COMPACT` to override the path.

Task construction (single-turn recommend, hit@1)
------------------------------------------------
PersonalWAB's own single-turn recommendation eval works like this
(replicated from `PersonalWAB/envs/base.py::calculate_reward` and
`envs/pwab/functions/get_recommendations_by_history.py`): the agent
makes one tool call; a SASRec recommender returns a top-10 product
list; result accuracy is a mechanical substring containment check of
the ground-truth `parent_asin` in the returned list, rank-weighted
(`1 - i/len`). Function accuracy separately checks tool choice.

Our arms (direct / reflexion / VRP / IterVRP / Intro-Specter) are
text-trajectory pipelines, not tool-calling loops, and the machine
running this campaign has no torch (SASRec checkpoint ships but cannot
be loaded here) -- so we adapt the task to single-turn candidate
selection while KEEPING their mechanical scoring criterion:

* The agent sees the user's real behavioral profile (11 profile spans)
  plus their real purchase history STRICTLY BEFORE the task timestamp
  (the target interaction itself is excluded -- verified: the target
  appears in `user_history` at the same timestamp for the test rows, so
  filtering by `ts < task_ts` and `asin != target` is required to avoid
  leaking the label), plus the user's natural-language request, plus a
  candidate list of 10 real products = the ground-truth target + 9
  deterministic distractors drawn from the real catalog (same
  main_category where possible).
* Distractors are the catalog items most lexically similar to the
  union of the user's request and the target title (token-overlap score
  over titles, deterministic tie-break, seeded sample from the top-100
  pool; 20-item slate) -- plausible request matches plus near-clones of
  the target, so the slate cannot be solved by request-reading alone
  and the discriminating signal is the user's personal profile/history,
  which is the point of the benchmark. (Calibration history, reported
  honestly: a first pilot with 10 random same-category distractors was
  saturated -- every arm 100% on its first 23 units -- and a second
  pilot with 10 request-similar distractors was still 8/8 on a
  direct-arm probe, largely because the dataset's own Brand Preference
  profile field is a strong genuine signal; slate difficulty was
  hardened to the current design before the production runs, and no
  pilot rows were kept in the production outputs. Calibration used the
  direct arm only, so it does not tune any arm-vs-arm comparison.)
* The agent must recommend exactly ONE candidate, naming its ASIN.
* Scoring is PersonalWAB's own containment criterion at hit@1: success
  iff the ground-truth parent_asin (and no other candidate ASIN)
  appears in the final output. This is their `target_asin in
  observation[i]` check specialised to a single recommended item; the
  rank-weighting term degenerates to 1 at hit@1. DEVIATION, stated
  plainly: their eval scores the output of a SASRec tool the agent
  triggers; ours scores the agent's own single pick from a 10-candidate
  slate. Candidate-slate hit@1 is a strictly mechanical replication of
  their containment scoring, not of their tool loop.

Unlike the other *_real loaders, no synthetic profile constraints are
injected (`inject_profile`/`inject_fault` unused): PersonalWAB's whole
point is that the profiles are real, so the profile spans ARE the
dataset's own behavioral profile + history entries.

Deterministic example selection follows the campaign convention:
`random.Random(seed * 1_000_037 + idx)` picks a row from the 757
test-split recommend instructions.
"""

from __future__ import annotations

import json
import os
import random
import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Literal

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

_DEFAULT_COMPACT = (
    "/private/tmp/claude-501/-Users-jihanmankani-Neurlips-Intro-Specter/"
    "5636e7ce-8bb7-48a8-b61c-0ddf6e5df234/scratchpad/personalwab/"
    "compact_recommend.json"
)

_DATA = None  # cached after first access


def _load() -> dict[str, Any]:
    global _DATA
    if _DATA is None:
        path = os.environ.get("PERSONALWAB_COMPACT", _DEFAULT_COMPACT)
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"PersonalWAB compact data file not found at {path!r}. "
                "Build it with the campaign prep script "
                "(prep_personalwab_compact.py) from the cloned "
                "HongruCai/PersonalWAB repo, or set PERSONALWAB_COMPACT."
            )
        with open(path) as f:
            _DATA = json.load(f)
    return _DATA


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def _profile_spans(user_id: str, pw_profile: dict[str, Any],
                   hist_rows: list[dict[str, Any]]) -> UserProfile:
    spans: list[ProfileSpan] = []
    for field, value in pw_profile.items():
        spans.append(ProfileSpan(
            id=f"pw_prof_{_slug(field)}",
            text=f"{field}: {value}",
            kind="preference",
            is_hard=False,
            contradicts=[],
        ))
    for i, h in enumerate(hist_rows):
        rating = h.get("rating")
        rating_str = f"rated {rating:g}/5" if rating is not None else "purchased"
        spans.append(ProfileSpan(
            id=f"pw_hist_{i:02d}",
            text=(f"Past purchase ({rating_str}): {h['title']} "
                  f"[ASIN {h['asin']}, {h['category']}]"),
            kind="history",
            is_hard=False,
            contradicts=[],
        ))
    return UserProfile(user_id=user_id, spans=spans)


def _make_rule(meta: dict[str, Any]):
    target_asin = meta["target_asin"].upper()
    candidate_asins = [a.upper() for a in meta["candidate_asins"]]

    def rule(profile, task, trajectory, final_output):
        text = (final_output or "").upper()
        step_id = trajectory.steps[-1].step_id if trajectory.steps else 0
        found = [a for a in candidate_asins if a in text]
        out: list[ViolationEvent] = []
        if not found:
            out.append(ViolationEvent(
                violation_id="v_pwab_no_candidate_asin",
                step_id=step_id,
                violated_constraint=(
                    "recommendation must name exactly one of the candidate "
                    "products by its ASIN"),
                trajectory_text=(final_output or "")[:200],
                severity=Severity.MEDIUM,
                explanation="no candidate ASIN found in the recommendation",
            ))
        elif target_asin not in found:
            # NOTE: deliberately does NOT name the ground-truth ASIN.
            # QA-style loaders (twowiki_real) put the gold answer in the
            # violation because there the constraint IS the answer; for a
            # recommendation task the house analogue is the
            # amazon_products_real / travelplanner_real style -- a
            # constraint description that leaves the fix to the agent.
            # Naming the target here would let every feedback arm copy
            # the answer verbatim and erase all arm differences.
            out.append(ViolationEvent(
                violation_id="v_pwab_wrong_item",
                step_id=step_id,
                violated_constraint=(
                    "recommended product must be the candidate this user "
                    "would genuinely choose next, given their behavioral "
                    "profile and purchase history"),
                trajectory_text=(final_output or "")[:200],
                severity=Severity.HIGH,
                explanation=(
                    "the recommended candidate is not the user's genuine "
                    "next choice; reconsider the candidate list against "
                    "the user's profile and purchase history"),
            ))
        elif len(found) > 1:
            out.append(ViolationEvent(
                violation_id="v_pwab_multiple_items",
                step_id=step_id,
                violated_constraint=(
                    "recommendation must name exactly ONE candidate product "
                    "(hit@1), not several"),
                trajectory_text=(final_output or "")[:200],
                severity=Severity.MEDIUM,
                explanation=f"{len(found)} candidate ASINs named",
            ))
        return out

    rule.__name__ = "personalwab_real_rule"
    return rule


_STOP = {
    "the", "and", "for", "with", "that", "this", "your", "you", "any",
    "some", "have", "has", "are", "can", "could", "would", "like",
    "looking", "need", "want", "please", "hey", "there", "thanks",
    "recommend", "recommendations", "suggest", "suggestions", "find",
    "great", "good", "quality", "high", "best", "new", "get", "buy",
    "product", "products", "item", "items", "about", "them", "help",
}


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9']+", (text or "").lower())
            if len(w) > 2 and w not in _STOP}


def _candidate_pool(data: dict[str, Any], request: str, target_title: str,
                    exclude: set[str], pool_size: int = 100) -> list[str]:
    """ASINs of the catalog items most lexically similar to the request
    AND/OR the target title (union of both token sets) -- i.e. plausible
    request matches plus near-clones of the target, so the slate cannot
    be solved by request-reading alone.
    Deterministic: scores are exact, ties broken by ASIN sort order."""
    tok_cache = data.setdefault("_title_tokens", {})
    if not tok_cache:
        for a, p in data["catalog"].items():
            tok_cache[a] = _tokens(p["title"])
    q = _tokens(request) | _tokens(target_title)
    scored: list[tuple[int, str]] = []
    for a, toks in tok_cache.items():
        if a in exclude:
            continue
        s = len(q & toks)
        if s:
            scored.append((-s, a))
    scored.sort()
    return [a for _, a in scored[:pool_size]]


def _fmt_price(p: Any) -> str:
    try:
        return f"${float(p):.2f}"
    except (TypeError, ValueError):
        return "price n/a"


Split = Literal["train", "val", "test", "all"]


@dataclass
class PersonalWABReal:
    n_examples: int = 60
    seed: int = 42
    split: Split = "all"
    train_frac: float = 0.6
    val_frac: float = 0.2
    n_candidates: int = 20
    max_history_spans: int = 12
    fault_inject: bool = False  # real profiles; no synthetic faults (see module docstring)

    @property
    def name(self) -> str:
        return "personalwab_real"

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

    def _build_example(self, idx: int) -> BenchmarkExample:
        data = _load()
        rows = data["recommend_test"]
        rng = random.Random(self.seed * 1_000_037 + idx)
        row = rows[rng.randint(0, len(rows) - 1)]

        user_id = row["user_id"]
        target_asin = row["target_asin"]
        task_ts = row["timestamp"]

        # History strictly BEFORE the task timestamp, target excluded
        # (the target interaction itself sits in user_history at task_ts;
        # verified during data acquisition -- excluding it avoids leaking
        # the label through the profile).
        full_hist = data["history"].get(user_id, [])
        prior = [h for h in full_hist
                 if h.get("ts") is not None and h["ts"] < task_ts
                 and h["asin"] != target_asin]
        hist_rows = prior[-self.max_history_spans:]
        hist_asins = {h["asin"] for h in full_hist}

        pw_profile = data["profiles"].get(user_id, {})
        profile = _profile_spans(user_id, pw_profile, hist_rows)

        # Candidate slate: target + (n_candidates-1) real distractors --
        # the catalog items most lexically similar to the user's REQUEST
        # (never the target, never an item this user already interacted
        # with), so every candidate plausibly matches the request text
        # and the discriminating signal is the personal profile/history.
        catalog = data["catalog"]
        target_prod = catalog.get(target_asin, {
            "asin": target_asin,
            "title": row["target_title"],
            "category": row["target_category"],
            "price": None, "rating": None, "feature": "",
        })
        all_asins = data.setdefault("_catalog_keys", sorted(catalog.keys()))
        exclude = hist_asins | {target_asin}
        pool = _candidate_pool(data, row["task"], row["target_title"], exclude)
        n_dis = self.n_candidates - 1
        if len(pool) >= n_dis:
            distractors = rng.sample(pool, n_dis)
        else:
            extra_pool = [a for a in all_asins
                          if a not in exclude and a not in pool]
            distractors = pool + rng.sample(extra_pool, n_dis - len(pool))
        candidates = [catalog[a] for a in distractors] + [target_prod]
        rng.shuffle(candidates)
        candidate_asins = [c["asin"] for c in candidates]

        cand_lines = []
        for i, c in enumerate(candidates, 1):
            bits = [f"{i}. {c['title']}",
                    f"ASIN: {c['asin']}",
                    f"category: {c['category']}",
                    _fmt_price(c.get("price"))]
            if c.get("rating") is not None:
                bits.append(f"avg rating {c['rating']}")
            if c.get("feature"):
                bits.append(f"feature: {c['feature']}")
            cand_lines.append(" | ".join(bits))

        prompt = (
            "You are a personalized shopping recommendation agent. Use the "
            "user's behavioral profile and real purchase history (provided "
            "as the user profile) to serve this request:\n\n"
            f"USER REQUEST: {row['task']}\n\n"
            "Recommend exactly ONE product from the following candidate "
            "list -- the one this specific user is most likely to want "
            "next, given their profile, purchase history, and request.\n\n"
            "CANDIDATES:\n" + "\n".join(cand_lines) + "\n\n"
            "Name the chosen product and state its ASIN on its own line as "
            "'ASIN: <asin>'. Recommend exactly one candidate; do not list "
            "alternatives."
        )

        task_id = f"pwab_real_{idx:05d}_{user_id[-8:]}"
        condition_meta = {
            "pw_user_id": user_id,
            "pw_timestamp": task_ts,
            "target_asin": target_asin,
            "target_title": row["target_title"],
            "target_category": row["target_category"],
            "candidate_asins": candidate_asins,
            "n_history_spans": len(hist_rows),
            "n_prior_history": len(prior),
            "instruction": row["task"],
        }
        rule = _make_rule(condition_meta)

        task = {
            "task_id": task_id,
            "task_type": "personalwab_real",
            "condition": "recommend_singleturn_real",
            "prompt": prompt,
            "split": self.split_of(idx),
            "condition_meta": condition_meta,
        }
        gold = GoldLabels(
            success=None,
            correct_final_output=f"{row['target_title']} (ASIN: {target_asin})",
            fault_node_id=None,
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


__all__ = ["PersonalWABReal"]
