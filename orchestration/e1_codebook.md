# Annotation codebook — agent-failure fault labeling (v1, pilot)

You are labeling transcripts of an AI agent that tried to complete a task for a simulated
user and **failed**. Each item shows: (A) the task, (B) the user's profile/context, (C) the
agent's numbered steps (thoughts, tool calls, observations), (D) the final output.

Answer two questions per item:

- **Q1 — fault category:** which ONE kind of mistake caused the failure (definitions below).
- **Q2 — first faulty step:** the number of the EARLIEST step that, had it been done
  correctly, you believe the task would have succeeded.

Core principles:

1. **First, not worst.** Blame the step where the bad information *enters or is first acted
   on*, not where the consequences finally appear.
2. **Label the trajectory, not the outcome.** A failed task can contain a correct trace —
   category 6 exists for exactly that. Don't hunt for a fault that isn't there.
3. **Judge from what the agent could see.** A step is faulty only relative to the task,
   the user context, and the observations available *up to that step*.

---

## The categories

**1 · Profile/memory misuse** — the information WAS in the user's profile/history and the
agent ignored, misread, or contradicted it. Wrong preference applied, stale attribute used,
constraint from the profile dropped.
*Boundary:* if the "fact" was never in the profile/context at all, that's category 2.

**2 · Faulty assumption / hallucinated fact** — the agent asserted or acted on information
that appears nowhere in the task, profile, or observations. Invented product details,
imagined constraints, fabricated tool results.
*Boundary:* misremembering something that IS in the context is category 1; a wrong logical
step from correct facts is category 4.

**3 · Wrong action / tool misuse** — the plan/intent was right but execution was wrong:
called the wrong tool, malformed arguments, selected the wrong item from correct search
results, steps in an order that breaks a dependency.
*Boundary:* if the plan itself was wrong, that's category 4.

**4 · Reasoning/planning error** — a logic step that doesn't follow: invalid inference from
correct information, a stated task constraint skipped, goal drift, declaring success/stopping
before the task was done.
*Boundary:* if the bad step traces to an invented fact → 2; to a misread profile → 1.

**5 · Environment/task fault** — the failure is not the agent's: a tool returned broken or
contradictory output, the task is impossible or self-contradictory, the grading target is
wrong. Q2 may be "None", or the step of the broken observation.

**6 · No identifiable fault** — the trace looks correct end-to-end; the "failure" label may
be a grading artifact. Q2 = "None".

**7 · Ambiguous** — after honest effort you are genuinely torn between two categories.
You MUST name both candidates in the comment box. Expect to use this on well under 15% of
items; if you're above that, re-read the boundaries above.

Quick decision path: *Did the agent even err?* (no → 5 or 6) → *Was the bad info from the
user context, invented, or correctly held but misused?* (context → 1, invented → 2,
correctly held → next) → *Was the plan wrong or the execution of a right plan wrong?*
(plan → 4, execution → 3).

---

## Worked examples

Stylized but representative; step numbers refer to the agent's numbered transcript.

**Ex. 1 (→ cat 1).** Profile: "vegetarian; budget meals." Step 3: agent searches
restaurants, results include veg and non-veg. Step 5: agent recommends a steakhouse.
*Label: 1, step 5.* The preference existed and was violated at the recommendation step.

**Ex. 2 (→ cat 1, first-not-worst).** Profile: "prefers window seats." Step 2: agent
summarizes the profile as "prefers aisle seats." Steps 3–7 proceed consistently; step 7
books an aisle seat. *Label: 1, step 2.* The misreading enters at step 2; step 7 is only
the consequence.

**Ex. 3 (→ cat 2).** Task: plan a day in Mumbai. Step 4: agent writes "the Gateway of
India is closed on Mondays" (stated nowhere in any observation) and drops it from an
otherwise-valid plan, breaking the required-attractions constraint. *Label: 2, step 4.*

**Ex. 4 (→ cat 2, not 1).** Profile says nothing about allergies. Step 3: agent asserts
"the user is allergic to nuts" and excludes every dessert option, failing the
three-course-meal requirement. *Label: 2, step 3.* Invented, not misread.

**Ex. 5 (→ cat 3).** Step 4: search returns item IDs `B0091X` (32-oz bottle, matches the
request) and `B0091Y` (4-oz travel size). Step 5: agent's reasoning names the 32-oz bottle,
but the purchase call passes `B0091Y`. *Label: 3, step 5.* Right plan, wrong argument.

**Ex. 6 (→ cat 3, ordering).** Step 2: agent calls `book_hotel` before `check_availability`;
the booking targets a sold-out date and every later repair attempt fails. *Label: 3,
step 2.* Dependency-breaking order is execution, not planning, when the plan itself listed
both calls.

**Ex. 7 (→ cat 4).** Task: "itinerary under $500 total." Steps 3–6 price components
correctly ($180 + $220 + $160 = $560). Step 7: agent states "total $460, within budget"
and finalizes. *Label: 4, step 7.* All facts correct; the inference is wrong.

**Ex. 8 (→ cat 4, premature stop).** Task requires booking flight + hotel. Steps 1–5 book
the flight. Step 6: agent declares the task complete. *Label: 4, step 6.*

**Ex. 9 (→ cat 5).** Step 4: the search tool returns an empty result set for a query that
plainly should match (and the same query succeeds elsewhere in the transcript). The agent
handles the empty result reasonably but cannot finish. *Label: 5, step 4.*

**Ex. 10 (→ cat 6).** Every step is grounded, the user's constraints are respected, and the
final output satisfies the task as written — yet the item is marked failed (e.g., the grader
expected a different but equally valid answer). *Label: 6, step None.* This is a legitimate,
valuable label — do not force a fault.

**Ex. 11 (→ cat 7, used correctly).** Profile: "loves the beach." Step 5: agent plans a
mountain trek. Is the profile entry a preference the agent violated (1), or was the trek a
defensible plan given an explicit user request in the task that overrides the profile (6)?
If the task text is genuinely unclear about which wins, label 7 and write: "torn 1 vs 6 —
task instruction may override profile."

---

## Q2 edge rules

- Count only the agent's numbered steps (the item viewer numbers them for you).
- Several faults? Pick the FIRST; mention others in the comment.
- Fault "between" steps (e.g., something the agent never did)? Blame the earliest step
  where doing it was possible and warranted.
- Categories 5–6: step of the broken observation for 5 if one exists, else "None"; always
  "None" for 6.

## Process reminders

- One sitting = at most 10 items. Comment box: one sentence for any non-obvious call;
  REQUIRED for category 7.
- Broken/unreadable item → flag in the comment, skip, tell Jihan. Don't guess.
- No AI assistance and no discussion with other annotators on judgments (see your
  instructions file). Honest disagreement is fine; that's what the study measures.
