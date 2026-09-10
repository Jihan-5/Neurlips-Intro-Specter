"""Additive multi-fault injector for Amazon product data's NATIVE
(dataset-true, non-templated) constraints -- price/budget, brand, category,
and a feature/spec snippet, each derived directly from real per-row fields
of `davidberenstein1957/Amazon-Reviews-2023-Retail-Products` (a verified
Parquet mirror of the official McAuley-Lab Amazon-Reviews-2023 metadata;
see `intro_specter/benchmarks/amazon_products_real.py`'s module docstring
for why this mirror is used instead of the original script-based dataset,
and for the real per-field extraction rates).

Why this file exists
---------------------
This is the direct Amazon analogue of
`intro_specter/profiles/native_multi_fault_injection.py` (built for
TravelPlanner): TravelPlanner's native constraints are budget/days/local
booking rules; Amazon's native constraints are price/brand/category/feature.
Same "pick N disjoint constraint slots, corrupt each independently, remember
the true value for scoring" pattern, applied to a different real dataset's
native fields, again NOT reusing `fault_injection.py` / `double_fault_injection.py`
(those operate on the templated profile-dict shape and a scalar
`gold_answer`, which don't apply here for the same reason documented in
`native_multi_fault_injection.py`).

Confirmed feasibility (measured directly against the Amazon mirror, 4,000-row
sample, seed=7 -- see `amazon_products_real.py` docstring for the full
numbers): 94.8% of rows support all 4 native slots (price, brand, category,
feature) simultaneously, 5.1% support exactly 3 (price+2 of
brand/category/feature; feature is the one occasionally missing), and only
~0.1% support fewer than 3. This is materially BETTER coverage than
TravelPlanner's own native fields (whose N=4/5 fault counts are restricted
to the ~33% "hard" level) -- so N=1..4 are ALL broadly feasible across
essentially the whole pool, not level-gated the way TravelPlanner is.
Callers should still pre-filter (`max_faultable_slots(ex) >= num_faults`)
for the rare rows missing a slot, mirroring the same discipline.

Selection order (deterministic, not random): price, brand, category,
feature. This mirrors `native_multi_fault_injection.py`'s "slots requested
in caller-given order, first N present" discipline, so N=1 is always
'price only', N=2 is always 'price+brand', etc. across every row that
qualifies -- keeping the corrupted-slot IDENTITY constant as N is the only
thing that varies between conditions.

Corruption + resolution-check discipline
------------------------------------------
Corruption strategies are the Amazon-native analogue of
`native_multi_fault_injection.py`'s `_corrupted_budget` /
`_corrupted_categorical`: `price` is corrupted by inflating the shown
budget ceiling (agent believes it has MORE money than the real ceiling
allows, same "wrong assumption" shape as TravelPlanner's budget fault);
`brand` / `category` / `feature` are corrupted by deterministically
swapping in a different value from a small fixed pool. This module ONLY
builds the corrupted constraint set + records true values; resolution
checking against the agent's final free-text recommendation is done by the
calling script (same separation of concerns as the TravelPlanner module).
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Any

from intro_specter.benchmarks.amazon_products_real import (
    _budget_ceiling,
    _extract_brand,
    _extract_category,
    _extract_feature_snippet,
    native_constraints,
)
from intro_specter.schemas import ProfileSpan

_SLOT_PRIORITY = ["price", "brand", "category", "feature"]

_BRAND_POOL = [
    "Sony", "Samsung", "Anker", "Logitech", "HP", "Canon", "Bose", "JBL",
    "TP-Link", "Belkin", "SanDisk", "Western Digital", "Seagate", "Corsair",
    "Razer", "ASUS", "Dell", "Lenovo", "Philips", "Panasonic", "GoPro",
    "Amazon Basics",
]
_CATEGORY_POOL = [
    "Batteries", "Cables & Interconnects", "Surveillance Cameras",
    "Graphics Tablets", "DVD Recorders", "Headphones", "Laptop Bags",
    "Wireless Routers", "Smart Watches", "Bluetooth Speakers",
    "Memory Cards", "External Hard Drives", "Gaming Mice", "Keyboards",
    "Webcams", "Power Banks", "Phone Cases", "Screen Protectors",
    "Tripods", "Camera Lenses",
]
_FEATURE_POOL = [
    "waterproof design", "built-in Bluetooth 5.0", "rechargeable lithium battery",
    "night vision capability", "fast USB-C charging", "adjustable mounting bracket",
    "active noise cancellation", "4K video recording", "long battery life up to 10 hours",
    "compact and lightweight design", "quick-release mounting mechanism",
    "voice control support",
]

_CATEGORICAL_POOLS = {
    "brand": _BRAND_POOL,
    "category": _CATEGORY_POOL,
    "feature": _FEATURE_POOL,
}


def _hash_int(*parts: Any) -> int:
    h = hashlib.sha256("::".join(str(p) for p in parts).encode()).hexdigest()
    return int(h[:12], 16)


def _corrupted_price(true_budget: float, task_id: str) -> float:
    """Inflate the shown budget ceiling by a factor in [1.4, 2.2] -- direct
    analogue of `native_multi_fault_injection.py::_corrupted_budget`: the
    agent believes it has substantially MORE money than it does."""
    h = _hash_int("amz_native_multifault_price", task_id)
    factor = 1.4 + ((h % 1_000_000) / 1_000_000) * 0.8
    corrupted = true_budget * factor
    step = 1.0 if corrupted < 20 else (5.0 if corrupted < 100 else 10.0)
    corrupted = math.ceil(corrupted / step) * step
    return max(corrupted, true_budget + 5.0)


def _corrupted_categorical(slot: str, true_value: str, task_id: str) -> str:
    pool = _CATEGORICAL_POOLS[slot]
    candidates = [v for v in pool if v.strip().lower() != true_value.strip().lower()]
    if not candidates:
        candidates = pool
    h = _hash_int("amz_native_multifault_cat", slot, task_id)
    return candidates[h % len(candidates)]


@dataclass(frozen=True)
class AmazonNativeMultiFaultRecord:
    task_id: str
    native_constraint_count: int
    num_faults: int
    faulted_slots: list[str]
    true_values: dict[str, Any]
    corrupted_values: dict[str, Any]
    spans: list[ProfileSpan]


def max_faultable_slots(ex: dict[str, Any]) -> int:
    native = native_constraints(ex)
    present_ids = {cid for cid, _, _ in native}
    return sum(1 for slot in _SLOT_PRIORITY if slot in present_ids)


def build_amazon_native_multi_fault(
    *, task_id: str, ex: dict[str, Any], num_faults: int,
) -> AmazonNativeMultiFaultRecord:
    """Builds `num_faults` independent, genuinely-applied faults on the
    native Amazon constraints for one row, selecting slots via the fixed
    `_SLOT_PRIORITY` order (first `num_faults` present slots). Raises
    `RuntimeError` if the row has fewer than `num_faults` eligible slots."""
    native = native_constraints(ex)
    native_by_id = {cid: (text, is_hard) for cid, text, is_hard in native}
    present_slots = [s for s in _SLOT_PRIORITY if s in native_by_id]
    if num_faults > len(present_slots):
        raise RuntimeError(
            f"build_amazon_native_multi_fault: task_id={task_id!r} has only "
            f"{len(present_slots)} faultable slots ({present_slots}), requested num_faults={num_faults}"
        )
    faulted_slots = present_slots[:num_faults]

    true_values: dict[str, Any] = {}
    corrupted_values: dict[str, Any] = {}
    spans: list[ProfileSpan] = []

    true_price = float(ex["price"])
    true_budget = _budget_ceiling(true_price)
    brand = _extract_brand(ex.get("details"))
    category = _extract_category(ex.get("categories"), ex.get("main_category"))
    feature = _extract_feature_snippet(ex.get("features"))
    true_lookup = {"price": true_budget, "brand": brand, "category": category, "feature": feature}

    for cid, text, is_hard in native:
        true_val = true_lookup[cid]
        true_values[cid] = true_val
        if cid in faulted_slots:
            if cid == "price":
                corrupted = _corrupted_price(true_budget, task_id)
                corrupted_values["price"] = corrupted
                text = f"Recommended product price must not exceed ${corrupted:.2f}."
            else:
                corrupted = _corrupted_categorical(cid, str(true_val), task_id)
                corrupted_values[cid] = corrupted
                label = {
                    "brand": "Recommended product must be brand/manufacturer",
                    "category": "Recommended product must belong to this category",
                    "feature": "Recommended product must have this feature/spec",
                }[cid]
                text = f"{label}: {corrupted}."
        spans.append(ProfileSpan(id=cid, text=text, kind="constraint", is_hard=is_hard, contradicts=[]))

    return AmazonNativeMultiFaultRecord(
        task_id=task_id,
        native_constraint_count=len(native),
        num_faults=num_faults,
        faulted_slots=faulted_slots,
        true_values=true_values,
        corrupted_values=corrupted_values,
        spans=spans,
    )


__all__ = [
    "AmazonNativeMultiFaultRecord",
    "build_amazon_native_multi_fault",
    "max_faultable_slots",
]
