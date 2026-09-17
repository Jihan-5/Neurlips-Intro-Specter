#!/usr/bin/env python3
"""E1 agreement analysis: Cohen's kappa, Krippendorff's alpha, attention-check
screening, adjudication queue, and consensus labels.

Consumes the answer JSONs downloaded from the annotation pages:
    {"annotator": "person1", "phase": "pilot"|"main"|"tiebreak",
     "answers": [{"item_id": "e1_0042", "category": 1..7,
                  "step": <int|null>, "comment": "..."}]}

and the private keymap written by e1_blind_trajectories.py (never shared with
annotators), which marks attention-check items and their ground truth:
    {"e1_0042": {"source": ..., "attention_check": false, ...},
     "e1_0107": {"attention_check": true, "gt_category": 3, "gt_step": 5, ...}}

Rules implemented here are frozen in orchestration/e1_prereg.md:
  - kappa: pairwise Cohen's kappa on Q1 over doubly-labeled items, mean across
    annotator pairs; category 7 (ambiguous) is its own class.
  - attention checks: >2 wrong of an annotator's checks => ALL their labels
    excluded (mechanical, no discretion).
  - Q2 agreement: fraction of pairs within +/-1 step (None matches only None).
  - consensus (with --tiebreaks): Q1 majority; Q2 earlier-of-two if within 1
    step, else median-of-three if any two within 1 step; else unresolved.

Usage:
  python3 scripts/e1_compute_agreement.py --answers outputs/iclr/e1_dataset/answers/*.json \
      --keymap outputs/iclr/e1_dataset/keymap.json --phase pilot
  python3 scripts/e1_compute_agreement.py --answers ... --phase main \
      --emit-adjudication-queue outputs/iclr/e1_dataset/tiebreak_queue.json
  python3 scripts/e1_compute_agreement.py --answers ... --phase main \
      --tiebreaks outputs/iclr/e1_dataset/answers_tiebreak/*.json \
      --emit-consensus outputs/iclr/e1_dataset/consensus.json
"""

import argparse
import itertools
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path


def load_answers(paths, phase):
    """Return {annotator: {item_id: (category, step, comment)}}."""
    by_annotator = {}
    for p in paths:
        blob = json.loads(Path(p).read_text())
        if blob.get("phase") != phase:
            continue
        ann = blob["annotator"]
        d = by_annotator.setdefault(ann, {})
        for a in blob["answers"]:
            cat = int(a["category"])
            step = a.get("step")
            step = None if step in (None, "", "None") else int(step)
            if a["item_id"] in d:
                sys.exit(f"duplicate label for {a['item_id']} by {ann}")
            d[a["item_id"]] = (cat, step, a.get("comment", ""))
    if not by_annotator:
        sys.exit(f"no answer files matched phase={phase!r}")
    return by_annotator


def screen_attention_checks(by_annotator, keymap):
    """Apply the frozen exclusion rule; return (excluded, report_rows)."""
    excluded, rows = set(), []
    for ann, labels in sorted(by_annotator.items()):
        wrong = seen = 0
        for item_id, (cat, _step, _c) in labels.items():
            key = keymap.get(item_id, {})
            if key.get("attention_check"):
                seen += 1
                if cat != key["gt_category"]:
                    wrong += 1
        if wrong > 2:
            excluded.add(ann)
        rows.append((ann, seen, wrong, "EXCLUDED" if wrong > 2 else "ok"))
    return excluded, rows


def cohens_kappa(pairs):
    """pairs: list of (label_a, label_b). Standard unweighted Cohen's kappa."""
    n = len(pairs)
    if n == 0:
        return None
    po = sum(1 for a, b in pairs if a == b) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    if pe == 1.0:
        return 1.0
    return (po - pe) / (1 - pe)


def krippendorff_alpha_nominal(units):
    """units: list of lists of labels (>=2 labels per unit). Nominal metric."""
    units = [u for u in units if len(u) >= 2]
    if not units:
        return None
    do_num = do_den = 0.0
    all_labels = []
    for u in units:
        m = len(u)
        disagree = sum(1 for a, b in itertools.combinations(u, 2) if a != b)
        do_num += disagree / (m - 1)
        do_den += m / 2  # pairs normalization per Krippendorff
        all_labels.extend(u)
    do = do_num / do_den if do_den else 0.0
    n = len(all_labels)
    counts = Counter(all_labels)
    de = sum(c1 * (n - c1) for c1 in counts.values()) / (n * (n - 1))
    if de == 0:
        return 1.0
    return 1 - do / de


def step_match(sa, sb):
    if sa is None or sb is None:
        return sa is None and sb is None
    return abs(sa - sb) <= 1


def build_consensus(item_labels, tiebreak_labels):
    """item_labels: {item_id: [(ann, cat, step)]} with exactly the base labels.
    tiebreak_labels: {item_id: (ann, cat, step)} third labels.
    Returns {item_id: {"category":..,"step":..,"status": "agreed"|"tiebroken"|"unresolved"}}."""
    out = {}
    for item_id, labels in sorted(item_labels.items()):
        if len(labels) < 2:
            out[item_id] = {"status": "unlabeled"}
            continue
        (a1, c1, s1), (a2, c2, s2) = labels[:2]
        cats = [c1, c2]
        steps = [s1, s2]
        tb = tiebreak_labels.get(item_id)
        cat_agree = c1 == c2
        step_agree = step_match(s1, s2)
        if cat_agree and step_agree:
            step = None if s1 is None else min(x for x in steps if x is not None)
            out[item_id] = {"category": c1, "step": step, "status": "agreed"}
            continue
        if tb is None:
            out[item_id] = {"status": "needs_tiebreak"}
            continue
        _, c3, s3 = tb
        cats.append(c3)
        steps.append(s3)
        # Q1: majority of three
        top, top_n = Counter(cats).most_common(1)[0]
        if top_n < 2:
            out[item_id] = {"status": "unresolved"}
            continue
        # Q2: median of three if any two within 1 step
        concrete = [s for s in steps if s is not None]
        if all(s is None for s in steps):
            step = None
        elif len(concrete) >= 2 and any(
            abs(a - b) <= 1 for a, b in itertools.combinations(concrete, 2)
        ):
            step = int(statistics.median(concrete))
        else:
            out[item_id] = {"status": "unresolved"}
            continue
        out[item_id] = {"category": top, "step": step, "status": "tiebroken"}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--answers", nargs="+", required=True)
    ap.add_argument("--keymap", required=True)
    ap.add_argument("--phase", choices=["pilot", "main"], required=True)
    ap.add_argument("--tiebreaks", nargs="*", default=[])
    ap.add_argument("--emit-adjudication-queue")
    ap.add_argument("--emit-consensus")
    args = ap.parse_args()

    keymap = json.loads(Path(args.keymap).read_text())
    by_annotator = load_answers(args.answers, args.phase)

    excluded, screen_rows = screen_attention_checks(by_annotator, keymap)
    print("== attention-check screening ==")
    for ann, seen, wrong, verdict in screen_rows:
        print(f"  {ann}: {wrong} wrong of {seen} checks -> {verdict}")
    by_annotator = {a: d for a, d in by_annotator.items() if a not in excluded}

    is_natural = lambda i: not keymap.get(i, {}).get("attention_check")

    # pairwise kappa over doubly-labeled natural items
    kappas = []
    print("== pairwise Cohen's kappa (Q1, natural items) ==")
    for a, b in itertools.combinations(sorted(by_annotator), 2):
        shared = [
            i for i in by_annotator[a]
            if i in by_annotator[b] and is_natural(i)
        ]
        pairs = [(by_annotator[a][i][0], by_annotator[b][i][0]) for i in shared]
        k = cohens_kappa(pairs)
        if k is not None:
            kappas.append(k)
            print(f"  {a} x {b}: kappa={k:.3f} (n={len(pairs)})")
    if kappas:
        print(f"  MEAN pairwise kappa = {statistics.mean(kappas):.3f}")

    # per-item label table for alpha / step agreement / consensus
    item_labels = defaultdict(list)
    for ann, d in by_annotator.items():
        for item_id, (cat, step, _c) in d.items():
            if is_natural(item_id):
                item_labels[item_id].append((ann, cat, step))

    alpha = krippendorff_alpha_nominal(
        [[cat for _, cat, _ in v] for v in item_labels.values()]
    )
    if alpha is not None:
        print(f"== Krippendorff's alpha (nominal, Q1) = {alpha:.3f} ==")

    step_pairs = [
        step_match(v[0][2], v[1][2]) for v in item_labels.values() if len(v) >= 2
    ]
    if step_pairs:
        frac = sum(step_pairs) / len(step_pairs)
        print(f"== Q2 within-1-step agreement = {frac:.3f} (n={len(step_pairs)}) ==")

    tiebreaks = {}
    for blob_path in args.tiebreaks:
        blob = json.loads(Path(blob_path).read_text())
        if blob.get("phase") != "tiebreak":
            continue
        for a in blob["answers"]:
            step = a.get("step")
            step = None if step in (None, "", "None") else int(step)
            tiebreaks[a["item_id"]] = (blob["annotator"], int(a["category"]), step)

    consensus = build_consensus(item_labels, tiebreaks)
    status_counts = Counter(v["status"] for v in consensus.values())
    print(f"== consensus status == {dict(status_counts)}")

    if args.emit_adjudication_queue:
        queue = [i for i, v in consensus.items() if v["status"] == "needs_tiebreak"]
        Path(args.emit_adjudication_queue).write_text(json.dumps(queue, indent=1))
        print(f"wrote {len(queue)} items -> {args.emit_adjudication_queue}")

    if args.emit_consensus:
        Path(args.emit_consensus).write_text(json.dumps(consensus, indent=1))
        print(f"wrote consensus -> {args.emit_consensus}")


if __name__ == "__main__":
    main()
