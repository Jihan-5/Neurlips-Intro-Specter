#!/usr/bin/env python3
"""E1 annotation pages: one self-contained offline HTML file per
(annotator, phase). No server, no accounts, no external assets.

Reads items/ + assignments.json (from e1_blind_trajectories.py) and writes
annotation_pages/personN_pilot.html and personN_main.html. With --phase
tiebreak and --queue (from e1_compute_agreement.py --emit-adjudication-queue)
it builds tiebreak pages instead.

The page autosaves to localStorage and downloads answers as JSON in exactly
the schema scripts/e1_compute_agreement.py consumes:
  {"annotator": "person1", "phase": "pilot", "answers": [
      {"item_id": "e1_0042", "category": 3, "step": 5, "comment": ""}]}

Usage:
  python3 scripts/e1_make_annotation_pages.py \
      --dataset-dir outputs/iclr/e1_dataset --phase pilot main
  python3 scripts/e1_make_annotation_pages.py \
      --dataset-dir outputs/iclr/e1_dataset --phase tiebreak \
      --queue outputs/iclr/e1_dataset/tiebreak_queue.json --annotators person3
"""

import argparse
import html
import json
from pathlib import Path

CATEGORIES = [
    (1, "Profile/memory misuse",
     "info WAS in the profile/context; agent ignored, misread, or contradicted it"),
    (2, "Faulty assumption / hallucinated fact",
     "agent asserted or acted on info that appears NOWHERE in task, profile, or observations"),
    (3, "Wrong action / tool misuse",
     "right plan, wrong execution: wrong tool/arguments/item, dependency-breaking order"),
    (4, "Reasoning/planning error",
     "invalid inference from correct info, skipped a stated constraint, stopped too early"),
    (5, "Environment/task fault",
     "not the agent's fault: broken observation, impossible or contradictory task"),
    (6, "No identifiable fault",
     "the trace looks correct; the failure may be a grading artifact (step = None)"),
    (7, "Ambiguous",
     "genuinely torn between two categories — you MUST name both in the comment"),
]

PAGE = r"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root { --fg:#1a1a2e; --bg:#fafafa; --card:#fff; --line:#d8d8e0; --accent:#3452c4;
          --ok:#1a7f4b; --warn:#b0730c; }
  * { box-sizing: border-box; }
  body { margin:0; font:16px/1.55 -apple-system, "Segoe UI", Roboto, sans-serif;
         color:var(--fg); background:var(--bg); }
  header { position:sticky; top:0; z-index:5; background:var(--card);
           border-bottom:1px solid var(--line); padding:.6rem 1rem;
           display:flex; gap:1rem; align-items:center; flex-wrap:wrap; }
  header b { font-size:1.05rem; }
  #progress { color:var(--accent); font-variant-numeric:tabular-nums; }
  main { max-width:1200px; margin:0 auto; padding:1rem;
         display:grid; grid-template-columns: minmax(0,3fr) minmax(300px,2fr); gap:1rem; }
  @media (max-width: 900px){ main { grid-template-columns:1fr; } }
  .card { background:var(--card); border:1px solid var(--line); border-radius:10px;
          padding:1rem; overflow-wrap:break-word; }
  h3 { margin:.2rem 0 .5rem; font-size:.95rem; text-transform:uppercase;
       letter-spacing:.04em; color:#666; }
  .step { border-left:3px solid var(--line); padding:.35rem .6rem; margin:.35rem 0; }
  .step .k { display:inline-block; font-size:.72rem; padding:.05rem .45rem;
             border-radius:99px; background:#eef; color:#336; margin-right:.4rem;
             text-transform:uppercase; letter-spacing:.03em; }
  .step .num { font-weight:700; color:var(--accent); margin-right:.35rem; }
  .tool { font-family:ui-monospace, monospace; font-size:.85rem; background:#f4f4f8;
          padding:.3rem .5rem; border-radius:6px; margin-top:.25rem; white-space:pre-wrap; }
  .span { padding:.2rem .5rem; margin:.2rem 0; background:#f6f8ff; border-radius:6px; }
  label.cat { display:block; padding:.45rem .6rem; border:1px solid var(--line);
              border-radius:8px; margin:.3rem 0; cursor:pointer; }
  label.cat:has(input:checked) { border-color:var(--accent); background:#f0f4ff; }
  label.cat .d { display:block; font-size:.83rem; color:#555; margin-left:1.55rem; }
  input[type=number], textarea { width:100%; padding:.45rem; border:1px solid var(--line);
              border-radius:8px; font:inherit; }
  textarea { min-height:3.2rem; }
  .nav { display:flex; gap:.6rem; margin-top:.8rem; flex-wrap:wrap; }
  button { padding:.5rem 1rem; border:1px solid var(--line); border-radius:8px;
           background:var(--card); font:inherit; cursor:pointer; }
  button.primary { background:var(--accent); border-color:var(--accent); color:#fff; }
  button.good { background:var(--ok); border-color:var(--ok); color:#fff; }
  #jump { display:flex; flex-wrap:wrap; gap:.25rem; margin-top:.6rem; }
  #jump button { padding:.15rem .5rem; font-size:.78rem; }
  #jump button.done { background:#e2f4ea; border-color:var(--ok); }
  #jump button.cur { outline:2px solid var(--accent); }
  .note { font-size:.85rem; color:#555; }
  .warn { color:var(--warn); font-weight:600; }
  #final { background:#fffbe8; border:1px solid #e8d9a0; border-radius:8px;
           padding:.5rem .7rem; margin-top:.6rem; white-space:pre-wrap; }
</style></head><body>
<header>
  <b>__TITLE__</b>
  <span id="progress"></span>
  <span style="flex:1"></span>
  <button class="good" onclick="download()">Download answers</button>
</header>
<main>
  <section class="card" id="left">
    <h3>Task given to the agent</h3>
    <div id="task" style="white-space:pre-wrap"></div>
    <h3 style="margin-top:1rem">User profile / context</h3>
    <div id="spans"></div>
    <h3 style="margin-top:1rem">Agent transcript (numbered steps)</h3>
    <div id="steps"></div>
    <h3 style="margin-top:1rem">Final output</h3>
    <div id="final"></div>
  </section>
  <section class="card">
    <div class="note">Read the task and profile first, then the whole transcript.
      <b>First faulty step, not the loudest.</b> Judge only from what the agent
      could see. No AI help, no discussing items with other annotators.</div>
    <h3 style="margin-top:.8rem">Q1 — what KIND of mistake caused the failure?</h3>
    <div id="cats"></div>
    <h3 style="margin-top:.8rem">Q2 — FIRST faulty step number</h3>
    <input type="number" id="step" min="0" placeholder="step number">
    <label class="note" style="display:block;margin-top:.25rem">
      <input type="checkbox" id="stepnone"> No step ("None") — allowed only for
      categories 5 and 6</label>
    <h3 style="margin-top:.8rem">Comment <span class="note">(one sentence;
      REQUIRED for category 7)</span></h3>
    <textarea id="comment"></textarea>
    <div class="nav">
      <button onclick="go(-1)">&#8592; Previous</button>
      <button class="primary" onclick="saveNext()">Save &amp; next &#8594;</button>
    </div>
    <div id="msg" class="note" style="margin-top:.5rem"></div>
    <div id="jump"></div>
  </section>
</main>
<script>
const ANNOTATOR = "__ANNOTATOR__";
const PHASE = "__PHASE__";
const ITEMS = __ITEMS__;
const KEY = "e1_" + ANNOTATOR + "_" + PHASE;
let idx = 0;
let answers = {};
try { answers = JSON.parse(localStorage.getItem(KEY)) || {}; } catch(e) {}

const esc = s => { const d = document.createElement("span"); d.textContent = s == null ? "" : String(s); return d.innerHTML; };

function render() {
  const it = ITEMS[idx];
  document.getElementById("task").innerHTML = esc(it.task_prompt);
  document.getElementById("spans").innerHTML = (it.profile_spans || [])
    .map(s => `<div class="span">${s.kind ? `<b>${esc(s.kind)}:</b> ` : ""}${esc(s.text)}</div>`)
    .join("") || "<i>(none)</i>";
  document.getElementById("steps").innerHTML = (it.steps || []).map(s => {
    let tool = "";
    if (s.tool_name) tool += `<div class="tool">tool: ${esc(s.tool_name)}(${esc(JSON.stringify(s.tool_input))})</div>`;
    if (s.tool_output != null && s.tool_output !== "") tool += `<div class="tool">&#8594; ${esc(typeof s.tool_output === "string" ? s.tool_output : JSON.stringify(s.tool_output))}</div>`;
    return `<div class="step"><span class="num">${esc(s.step_id)}</span><span class="k">${esc(s.kind)}</span>${esc(s.text)}${tool}</div>`;
  }).join("") || "<i>(empty transcript)</i>";
  document.getElementById("final").textContent = it.final_output == null ? "(none)" : String(it.final_output);

  const a = answers[it.item_id] || {};
  document.querySelectorAll("input[name=cat]").forEach(r => r.checked = String(a.category) === r.value);
  document.getElementById("step").value = a.step == null ? "" : a.step;
  document.getElementById("stepnone").checked = "step" in a && a.step === null;
  document.getElementById("comment").value = a.comment || "";
  document.getElementById("msg").textContent = "";
  updateHeader();
}

function updateHeader() {
  const done = ITEMS.filter(it => answers[it.item_id]).length;
  document.getElementById("progress").textContent =
    `item ${idx + 1} / ${ITEMS.length} — ${done} answered`;
  const jump = document.getElementById("jump");
  jump.innerHTML = "";
  ITEMS.forEach((it, i) => {
    const b = document.createElement("button");
    b.textContent = i + 1;
    b.className = (answers[it.item_id] ? "done " : "") + (i === idx ? "cur" : "");
    b.onclick = () => { idx = i; render(); };
    jump.appendChild(b);
  });
}

function collect() {
  const it = ITEMS[idx];
  const cat = document.querySelector("input[name=cat]:checked");
  if (!cat) return { err: "Pick a category (Q1) first." };
  const c = parseInt(cat.value, 10);
  const none = document.getElementById("stepnone").checked;
  const stepRaw = document.getElementById("step").value;
  const comment = document.getElementById("comment").value.trim();
  if (none && c !== 5 && c !== 6) return { err: '"None" is only allowed with categories 5 or 6.' };
  if (!none && stepRaw === "") {
    if (c === 6) return { err: 'Category 6 requires ticking "None".' };
    return { err: "Enter the first faulty step number (Q2), or tick None (cats 5/6)." };
  }
  if (c === 7 && !comment) return { err: "Category 7 requires a comment naming BOTH candidate categories." };
  return { ans: { item_id: it.item_id, category: c,
                  step: none ? null : parseInt(stepRaw, 10), comment: comment } };
}

function saveNext() {
  const r = collect();
  const msg = document.getElementById("msg");
  if (r.err) { msg.innerHTML = '<span class="warn">' + r.err + "</span>"; return; }
  answers[ITEMS[idx].item_id] = r.ans;
  localStorage.setItem(KEY, JSON.stringify(answers));
  msg.textContent = "Saved.";
  if (idx < ITEMS.length - 1) { idx++; render(); } else { updateHeader(); msg.textContent = "Saved — that was the last item. Use Download answers when every item is answered."; }
}

function go(d) { idx = Math.max(0, Math.min(ITEMS.length - 1, idx + d)); render(); }

function download() {
  const missing = ITEMS.filter(it => !answers[it.item_id]).length;
  if (missing > 0 && !confirm(missing + " item(s) not answered yet. Download anyway?")) return;
  const blob = new Blob([JSON.stringify({
    annotator: ANNOTATOR, phase: PHASE,
    answers: ITEMS.map(it => answers[it.item_id]).filter(Boolean),
  }, null, 1)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = ANNOTATOR + "_" + PHASE + "_answers.json";
  a.click();
}

document.getElementById("cats").innerHTML = __CATS__.map(c =>
  `<label class="cat"><input type="radio" name="cat" value="${c[0]}"> <b>${c[0]} &middot; ${c[1]}</b><span class="d">${c[2]}</span></label>`
).join("");
render();
</script></body></html>
"""


def build_page(annotator, phase, items, out_path):
    page = (
        PAGE
        .replace("__TITLE__", html.escape(f"Fault annotation — {annotator} — {phase}"))
        .replace("__ANNOTATOR__", annotator)
        .replace("__PHASE__", phase)
        .replace("__ITEMS__", json.dumps(items))
        .replace("__CATS__", json.dumps([[c, n, d] for c, n, d in CATEGORIES]))
    )
    out_path.write_text(page)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset-dir", required=True)
    ap.add_argument("--phase", nargs="+", default=["pilot", "main"],
                    choices=["pilot", "main", "tiebreak"])
    ap.add_argument("--queue", help="tiebreak item-id list (JSON) for --phase tiebreak")
    ap.add_argument("--annotators", nargs="*",
                    help="subset of annotators (default: all in assignments.json)")
    args = ap.parse_args()

    root = Path(args.dataset_dir)
    assignments = json.loads((root / "assignments.json").read_text())
    items_dir = root / "items"
    pages = root / "annotation_pages"
    pages.mkdir(exist_ok=True)

    def load_item(item_id):
        return json.loads((items_dir / f"{item_id}.json").read_text())

    who = args.annotators or sorted(assignments)
    for phase in args.phase:
        for a in who:
            if phase == "tiebreak":
                if not args.queue:
                    raise SystemExit("--phase tiebreak requires --queue")
                ids = json.loads(Path(args.queue).read_text())
                # a tiebreaker must not have labeled the item already:
                # caller passes --annotators explicitly per queue slice
            else:
                ids = assignments[a][phase]
            items = [load_item(i) for i in ids]
            out = pages / f"{a}_{phase}.html"
            build_page(a, phase, items, out)
            print(f"wrote {out} ({len(items)} items)")


if __name__ == "__main__":
    main()
