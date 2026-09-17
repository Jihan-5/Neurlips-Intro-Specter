#!/usr/bin/env python3
"""Generate F2/F3 only from complete, integrity-checked experiment grids."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aggregate_profile_bootstrap import build_report
from aggregate_profile_candidacy import aggregate_cell

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/jazz"
GEN = ROOT / "paper_sections/generated"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    boot_root = ROOT / "outputs/rebuttal/profile_bootstrap"
    e2 = build_report(boot_root)
    trust = json.loads((OUT / "paraphrase_review.json").read_text())
    e2_status = {"grid_complete": e2["complete"], "trust_gate": trust["trust_gate"],
                 "human_signoff": trust["human_signoff"], "generated": False}
    if e2["complete"]:
        (OUT / "bootstrap_final.json").write_text(json.dumps(e2, indent=2) + "\n")
    if e2["complete"] and trust["human_signoff"] and trust["trust_gate"] == "PASSED":
        contrast = e2["pooled"]["contrast"]
        text = ("\\subsection{Profile-draw robustness}\n"
                f"Across {contrast['n_draws']} frozen profile draws, the pooled paired effect "
                f"was {100*contrast['mean']:+.2f}\\,pp (2.5/97.5 percentiles "
                f"{100*contrast['p2_5']:+.2f}/{100*contrast['p97_5']:+.2f}\\,pp). "
                f"The bottom-decile mean was {100*contrast['worst_decile_mean']:+.2f}\\,pp; "
                f"the favorable-draw fraction was {contrast['favorable_fraction']:.3f}, with "
                f"Hoeffding bound {contrast['hoeffding_bound']:.3g}.\n")
        (GEN / "jazz_f2.tex").write_text(text)
        e2_status["generated"] = True
    (OUT / "f2_generation_status.json").write_text(json.dumps(e2_status, indent=2) + "\n")

    cells = []
    cand_root = ROOT / "outputs/rebuttal/profile_candidacy"
    for cell in sorted(cand_root.glob("*__*")):
        if (cell / "protocol.json").exists() and (cell / "paired.jsonl").exists():
            cells.append(aggregate_cell(cell))
    keys = ["rows", "expected", "paired", "eligible", "recovered", "regressions",
            "missing_pairs", "added_candidates", "error_attempts"]
    pooled = {key: sum(cell[key] for cell in cells) for key in keys}
    pooled["recovery_rate"] = pooled["recovered"] / pooled["eligible"] if pooled["eligible"] else None
    complete = len(cells) == 10 and all(cell["complete"] for cell in cells)
    e3 = {"cells": cells, "pooled": pooled, "complete": complete,
          "quantity": "clean-solved, corruption-associated default failures recovered by expanded candidate set",
          "caveat": "The paired denominator does not by itself establish causal node traceability."}
    (OUT / "candidacy_final.json").write_text(json.dumps(e3, indent=2) + "\n")
    if complete:
        rate = 100 * pooled["recovery_rate"] if pooled["recovery_rate"] is not None else 0
        text = ("\\subsection{When the profile itself is at fault}\n"
                "The synthetic diagnostic above tests localization when the gold fault node is "
                "known by construction. Complementing that evidence, the paired candidacy study "
                "tests whether broadening the extracted candidate set can recover failures under "
                "the stored benchmark trajectories. It recovered "
                f"{pooled['recovered']} of {pooled['eligible']} clean-solved, corruption-associated "
                f"default failures ({rate:.1f}\\%). The denominator requires the clean control to "
                "succeed and the matched corrupted default arm to fail; this is a recovered-failure "
                "quantity, not a claim that every failure is causally traceable to one node. This "
                "distinction is consistent with the inferred-component limitation summarized in "
                "Table~\\ref{tab:classical}.\n")
        (GEN / "jazz_f3.tex").write_text(text)
        sources = {str(path): sha(path) for path in cand_root.glob("*__*/paired.jsonl")}
        (GEN / "jazz_f3_provenance.json").write_text(json.dumps({
            "command": ".venv/bin/python scripts/generate_e2_e3_sections.py",
            "sources": sources, "aggregation": "outputs/jazz/candidacy_final.json"}, indent=2) + "\n")


if __name__ == "__main__":
    main()
