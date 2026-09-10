# triggers.md

Rules the orchestrator applies each time it wakes up (via `/loop`/`ScheduleWakeup`). A trigger fires subagents; it does not itself do the work. The orchestrator is the only thing that reads this file and decides what fires — subagents never read it directly.

Each rule: **Watch** (what changed) → **Fire** (what gets dispatched, how many, in parallel or sequential) → **Guard** (conditions that must hold before firing).

---

### T1 — New/changed item in `directions.md` under `## Now` with no matching `IN PROGRESS` line in `live_updates.md`
- **Fire:** one subagent per item (parallel if items are independent, i.e. don't write the same files / don't both spend budget against the same $80 cap).
- **Guard:** item must specify: goal, files it may touch, and a done-condition. If any is missing, the orchestrator's `/research_power` evaluation pass must fill it in before firing — never dispatch an underspecified item.
- **Agent choice:** research/investigation → `Explore` or `general-purpose`; drafting rebuttal text → `general-purpose` with the relevant TODO tags + numbers audit in the prompt; anything touching money (new OpenRouter/Together calls) → requires an explicit budget line in `directions.md` (see T4).

### T2 — A `live_updates.md` entry is tagged `BLOCKED` or `NEEDS-DECISION`
- **Fire:** no subagent. Escalate: orchestrator surfaces it to the user directly (via a message, not silently) and adds a `## Blocked` item in `directions.md`. Do not let subagents route around a human-decision block by re-trying or reframing the question.

### T3 — `/research_power` evaluation pass completes (runs every orchestrator wake-up, see below)
- **Fire:** the orchestrator updates `directions.md`'s `## Now` / `## Next` / `## Done` sections based on the evaluation's verdict, and appends one distilled entry to `live_updates.md` summarizing the verdict. This is the OpenClaw "distillation" step — detailed reasoning stays wherever the eval agent wrote it; only the decision + why lands in `directions.md`.
- **Guard:** the eval must explicitly check the Phase-0 gate condition (numbers traceable to run artifacts, sanity bounds per E2Eplan.md §4) before recommending any drafting work proceed.

### T4 — A direction item requires real API spend (OpenRouter/Together)
- **Fire:** subagent only after the orchestrator states the projected cost in `directions.md` AND cumulative projected spend (tracked in `directions.md`'s `## Budget` line) stays ≤ $80. If it would exceed $80, do not fire — add a `Blocked` item (see T2) asking the user to approve overage or reprioritize.

### T5 — All items in `directions.md`'s `## Now` are done and `## Next` is empty
- **Fire:** no subagent. Orchestrator runs `/research_power` against `E2Eplan.md` end-to-end ("what's left before this campaign is postable") and either populates `## Next` from the remaining plan phases, or — if the plan itself is complete — appends a final summary to `live_updates.md` and stops scheduling further wakeups (`ScheduleWakeup stop:true`).

### T6 — A subagent's result contradicts a number already used elsewhere in `rebuttal/*.md` or in `directions.md`
- **Fire:** one verification subagent (adversarial: told to try to explain the contradiction, not just re-report it) before either number is used further. This mirrors E2Eplan.md's own sanity-bounds rule and exists because that's exactly the failure class already hit once (MuSiQue×Mistral).

### T7 — Deadline guard
- **Fire:** on every wake-up, orchestrator checks days remaining vs. discussion deadline (~4 days from 2026-07-24, i.e. target ~2026-07-28). If <36h remain and any rebuttal thread has unresolved TODOs, escalate to user immediately (T2-style) rather than continuing to iterate — a late but honest partial draft beats a missed deadline.

---

## Non-triggers (explicitly do NOT auto-fire)
- Never auto-post to OpenReview — no tool exists for it, and E2Eplan.md §7 requires human sign-off regardless.
- Never auto-fire an experiment run without a budget line under T4, even if `directions.md` implies urgency.
- Never let a subagent edit `E2Eplan.md`'s body — only the orchestrator appends to its "Amendments" section, and only between wake-ups (not mid-subagent-run).
