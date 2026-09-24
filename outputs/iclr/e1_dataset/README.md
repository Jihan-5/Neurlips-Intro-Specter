# E1 human-data coordinator handoff

Both independent, blinded humans (Jazz1=`jazz`, Jazz2=`jazz2`) have completed the main and replacement pages. Human answers, original pages, preregistration, codebook, private keymap and the separate AI baseline are preserved. The stale exporter metadata in `jazz_main.html` is deliberately untouched and does not determine provenance.

The effective main contains **85 shared natural items**: remove the six malformed originals and include their six logged reserve replacements. Re-pilot κ passes. `private/finalization/AGREEMENT.md` reports freshly computed **descriptive, unscreened** agreement; it is not an eligible study result. Frozen attention screening excludes both humans (5/5 wrong each). The key says Cat1/Step5, while the earliest unsupported restaurant assertion supports Cat2/Step4 under the clarified codebook. The original conflict record remains unchanged at `private/attention_check_conflict_2026-09-23.md`.

Coordinator disposition: preserve the mechanical screen and escalate eligibility to Jihan under the existing exclusion/escalation mechanism. No coordinator exception, new check, changed key, fabricated label, or recovery workflow is used. Jihan must resolve the conflict before study adjudication/release; preparation is complete in the meantime.

## Prepared deliverables

- `private/finalization/`: effective human exports (raw answer objects unchanged), input hashes, agreement, full 14-item disagreement list, 12-item frozen-rule adjudication queue, private offline Jihan page, provisional consensus, prediction inventory and validation receipt.
- `private/draft_package/`: 85 per-trace records with both raw human labels and provisional consensus, copied codebook/prereg, datasheet, planned license and SHA-256 manifest. This is **not a public release**.
- `answers/`: original human exports and separate `ai_codex_main_baseline.json`; never select annotation inputs with a wildcard.
- `DATASHEET.md`: factual stub; final author prose/disclosures belong to Jihan.
- `REPRODUCE.md`: exact commands, prediction schema and remaining prerequisites.

The Jihan page is prepared through the existing `e1_make_annotation_pages.py` workflow. It contains no prefilled adjudication. `e1_finalize_human.py --adjudications PATH` merges an authentic Jihan download by frozen §4: category agreements stand; steps within one resolve to the earlier index. Adjudication does not waive attention exclusions. No final eligible consensus or accuracy is claimed.

Track P is complete for Llama + Mistral. Jihan said “Leave out bro” for Qwen; no Qwen task remains. Earlier E/F completion artifacts were verified without rerunning experiments or changing the paper. See `orchestration/jazz_sprint_handoff_2026-09-23.md` for transport and remaining actions.
