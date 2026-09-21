#!/usr/bin/env python3
"""E1 blinding + assignment: turn the sampled pool into opaque annotation items
and per-annotator assignments.

Reads raw_pool.jsonl (from e1_sample_annotation_set.py) and writes:
  items/e1_XXXX.json   blinded items — task, profile spans, numbered steps,
                       final output. NO method/arm/model/dataset names, no
                       fault_node_predicted, no DAG, no success flag wording.
  private/keymap.json  PRIVATE item_id -> provenance + attention-check ground
                       truth. Never share with annotators; stays out of the
                       annotation-pages directory and release until adjudication.
  assignments.json     per-annotator item lists: pilot items go to both named
                       annotators; both label every natural item; each gets
                       n-attention checks interleaved at random positions.

Annotators see the FINAL trajectory of the failed run (the run that actually
failed); blinding is by omission of identity fields, not by editing step text.

Usage:
  python3 scripts/e1_blind_trajectories.py \
      --pool outputs/iclr/e1_dataset/raw_pool.jsonl \
      --out-dir outputs/iclr/e1_dataset \
      --annotator-ids jazz mahfuza --pilot 15 --checks-per-annotator 5
"""

import argparse
import json
import random
from pathlib import Path

SEED = 42  # frozen — orchestration/e1_prereg.md §1


def blind(trace, item_id):
    traj = trace.get("final_trajectory") or trace.get("primed_trajectory")
    task = trace.get("task", {})
    profile = trace.get("profile", {})
    spans = profile.get("spans", [])
    return {
        "item_id": item_id,
        "task_prompt": task.get("prompt", ""),
        "profile_spans": [
            {"text": s.get("text", ""), "kind": s.get("kind", "")}
            if isinstance(s, dict) else {"text": str(s), "kind": ""}
            for s in spans
        ],
        "steps": [
            {
                "step_id": s.get("step_id"),
                "kind": s.get("kind"),
                "text": s.get("text", ""),
                "tool_name": s.get("tool_name"),
                "tool_input": s.get("tool_input"),
                "tool_output": s.get("tool_output"),
            }
            for s in (traj.get("steps") or [])
        ],
        "final_output": traj.get("final_output"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument(
        "--annotator-ids", nargs="+", default=["jazz", "mahfuza"],
        help="D6 named annotator IDs; exactly two are required",
    )
    ap.add_argument("--pilot", type=int, default=15,
                    help="first K main items (after shuffle) form the pilot, "
                         "labeled by ALL annotators")
    ap.add_argument("--checks-per-annotator", type=int, default=5)
    args = ap.parse_args()

    rng = random.Random(SEED)
    rows = [json.loads(line) for line in Path(args.pool).open()]
    mains = [r for r in rows if r["_role"] == "main"]
    reserves = [r for r in rows if r["_role"] == "reserve"]
    checks = [r for r in rows if r["_role"] == "attention"]

    # Opaque ids over a shuffled union so id order leaks nothing.
    everything = mains + reserves + checks
    rng.shuffle(everything)
    out = Path(args.out_dir)
    (out / "items").mkdir(parents=True, exist_ok=True)
    keymap = {}
    for i, trace in enumerate(everything):
        item_id = f"e1_{i:04d}"
        trace["_item_id"] = item_id
        keymap[item_id] = {
            "source_path": trace.get("_source_path"),
            "task_id": trace.get("task_id"),
            "dataset": trace.get("dataset"),
            "model": trace.get("model"),
            "method": trace.get("method"),
            "seed": trace.get("seed"),
            "role": trace["_role"],
            "attention_check": trace["_role"] == "attention",
        }
        if trace["_role"] == "attention":
            gt = trace.get("_gt", {})
            keymap[item_id]["gt_category"] = gt.get("category")
            keymap[item_id]["gt_step"] = gt.get("step")
        (out / "items" / f"{item_id}.json").write_text(
            json.dumps(blind(trace, item_id), default=str)
        )

    # ---- assignments ----
    annotators = list(args.annotator_ids)
    if len(annotators) != 2 or len(set(annotators)) != 2:
        raise SystemExit("Amendment D6 requires exactly two distinct annotator IDs")
    main_ids = [t["_item_id"] for t in mains]
    rng.shuffle(main_ids)
    pilot_ids = main_ids[: args.pilot]
    batch_ids = main_ids[args.pilot :]
    check_ids = [t["_item_id"] for t in checks]

    # D6: the same two named annotators label every natural item.
    per = {a: list(batch_ids) for a in annotators}

    assignments = {}
    for a in annotators:
        my_checks = rng.sample(check_ids, min(args.checks_per_annotator, len(check_ids)))
        batch = per[a] + my_checks
        rng.shuffle(batch)  # checks land at random positions
        assignments[a] = {"pilot": list(pilot_ids), "main": batch}

    (out / "private").mkdir(exist_ok=True)
    (out / "private" / "keymap.json").write_text(json.dumps(keymap, indent=1))
    (out / "assignments.json").write_text(json.dumps(assignments, indent=1))
    loads = {a: len(v["main"]) for a, v in assignments.items()}
    print(f"items: {len(everything)} ({len(pilot_ids)} pilot, {len(batch_ids)} batch, "
          f"{len(reserves)} reserve, {len(check_ids)} attention)")
    print(f"per-annotator main load (incl. checks): {loads}")
    print(f"wrote {out}/items, private/keymap.json, assignments.json")


if __name__ == "__main__":
    main()
