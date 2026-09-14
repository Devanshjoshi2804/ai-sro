// A run, while it is happening.
//
// The panel used to say "step 4 of 7" over a progress bar. A run drives the
// operator's own browser, in front of them, and a bar tells them none of the
// three things they want: which step it is on, whether the last one actually
// landed, and whether they can still change what the next one will send.
//
// So it is a row per step of the plan -- including the ones still to come,
// because what is about to happen is the part somebody might want to stop.
//
// Two rules this file exists to hold:
//
// 1. A step already sent cannot be changed. What has gone to the warehouse has
//    gone, and a control offering to take it back would be offering something
//    the system cannot do.
// 2. Done and confirmed are different. A step that went out and came back 200
//    was performed; a step whose effect something read back was confirmed.
//    Drawing both as a plain tick would be the panel claiming the stronger of
//    the two, which is the whole failure the read-back exists to catch.
//
// Pure: state in, DOM out. What a press means is the caller's.

/** Which values a step will render, read off whatever plan it carries. */
const NAMES = /\{\{\s*([a-zA-Z0-9_]+)\s*\}\}/g;

function namesIn(step) {
  const plan = step?.network_plan || step?.ui_plan || step?.tool_plan;
  if (!plan) return [];
  const text = JSON.stringify(plan);
  return [...new Set([...text.matchAll(NAMES)].map((match) => match[1]))];
}

/**
 * What happened to one step, as one character.
 *
 * `✓!` is the honest one: performed, but nothing read the effect back, or
 * something did and disagreed. Until the read-back rung exists, most steps are
 * this, and saying so is the point -- a panel that ticked them all would be
 * telling an operator their warehouse is fine on the strength of a status code.
 */
export function glyphFor(outcome) {
  if (!outcome) return "○";
  // The rig words this differently, because it judges a step rather than
  // records a disposition: `held` is its reading of "the thing I said would
  // happen did", `unclear` is the same honesty `✓!` carries here -- it went
  // out and nothing could say whether it landed.
  //
  // `awaiting` is `withheld`'s glyph because it is the same fact to the person
  // reading it: the write has not gone. `done_by_operator` is a plain tick --
  // they went and did it themselves while the rig waited, and that step is as
  // over as one the rig performed.
  if (typeof outcome === "string") {
    return {
      held: "✓",
      done_by_operator: "✓",
      withheld: "⏸",
      awaiting: "⏸",
      failed: "✗",
      refused: "✗",
      skipped: "○",
    }[outcome] || "✓!";
  }
  if (outcome.disposition === "failed") return "✗";
  if (outcome.disposition === "withheld") return "⏸";
  if (outcome.disposition === "performed") {
    const checked = outcome.confirmed && !(outcome.assertion_failures || []).length;
    return checked ? "✓" : "✓!";
  }
  return "●";
}

/**
 * The card.
 *
 * `onChange(runId, name, value)` when the operator edits a value for a step
 * still to come. `onPress(answer, run, card, button)` for `pause` and `stop`.
 * `notes` are what they have said to this run, each carrying the step index it
 * arrived during.
 */
export function runCard(
  { run, skill, message, notes = [] },
  { onPress, onChange, onSecret, stop = true } = {},
) {
  const card = document.createElement("div");
  card.className = "run";
  card.dataset.status = run.status;
  card.dataset.runId = run.id;

  const title = document.createElement("p");
  title.className = "what";
  title.textContent = message?.text || `Running ${skill?.name || ""}`.trim();
  card.append(title);

  // Who drove it, and so what there is to draw and to press. A record with no
  // `source` is a backend run -- older rows have none, and reading a missing
  // field as "rig" would send a backend run's Stop somewhere it has never been
  // heard of.
  const rig = run.source === "rig";
  const done = new Map((run.steps || []).map((step) => [step.index, step]));
  const live = run.status === "running";
  // The next position nothing has recorded. Positions rather than a count: a
  // skill whose body runs once per thing in a list does not know its own length
  // until the system answers, which is why the executor asks per step too.
  const inFlight = Math.max(-1, ...done.keys()) + 1;

  // The rig plans one step at a time and there is no skill in this browser to
  // draw the rest from, so its rows are its own record: what it said it was
  // doing, and the verdict on it. Everything below -- the glyphs, a note said
  // during a step -- is the same code for both.
  const plan = rig
    ? (run.steps || []).map((step) => ({ ...step, intent: step.says }))
    : skill?.latest?.steps || [];
  // A job done once per thing on a list, drawn one thing at a time.
  //
  // Nineteen rows of "Click Save." with nothing saying which record each
  // belongs to is a run nobody can read -- and the question somebody watching
  // actually has is not which step it is on, it is how many of the three are
  // done. So a line goes in front of each thing's rows, naming it and counting
  // it, and the rows underneath are the rows they always were.
  const things = run.items || [];
  let drawing = null;
  for (const step of plan) {
    const thing = step.item ?? null;
    if (thing !== null && thing !== drawing) {
      drawing = thing;
      const heading = document.createElement("p");
      heading.className = "thing";
      const said = Object.values(things[thing] || {}).join(" ");
      heading.textContent = `${thing + 1} of ${things.length || thing + 1}${said ? ` — ${said}` : ""}`;
      card.append(heading);
    }
    card.append(
      stepRow({
        step,
        outcome: rig ? done.get(step.index)?.outcome : done.get(step.index),
        live,
        inFlight,
        run,
        notes,
        onPress,
        onSecret,
        onChange: rig ? undefined : onChange,
      }),
    );
  }

  // What a dry run held back. There is no other screen it could be said on --
  // phase 5 left one system, and this card is where the writes were drawn in
  // words -- and the operator watching them be planned is the person who needs
  // to know they did not happen.
  const withheld = rig && !live ? (run.withheld || []).length : 0;
  if (withheld) {
    const line = document.createElement("p");
    line.className = "note";
    line.textContent =
      `dry run — ${withheld} write${withheld === 1 ? "" : "s"} shown here, not sent`;
    card.append(line);
  }

  // `stop: false` when the card is drawn under one that already carries "Stop
  // this run" -- the performing card -- so a live run shows one Stop, not two.
  if (live && stop) {
    const row = document.createElement("div");
    row.className = "row";
    // The rig has no pause: its loop checks one flag between steps, and a
    // control offering to stop after this one would be offering something the
    // process behind it cannot do.
    const buttons = rig
      ? [["stop", "Stop"]]
      : [
          ["pause", "Stop after this step"],
          ["stop", "Stop"],
        ];
    for (const [answer, label] of buttons) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "quiet";
      button.textContent = label;
      button.addEventListener("click", () => onPress?.(answer, run, card, button));
      row.append(button);
    }
    card.append(row);
  }
  return card;
}

/** A planned command in words. `textContent` only; the payload is the model's
 * and the page's. */
function wordsFor(sent) {
  if (!sent) return "";
  const p = sent.payload || {};
  if (sent.kind === "http.send") return `${p.method || "call"} ${p.url || ""}`;
  if (sent.kind === "navigate") return `open ${p.url || ""}`;
  const where = (p.locators || [])[0]?.query || "";
  return `${p.action || "act"}${p.value ? ` "${p.value}"` : ""} ${where}`.trim();
}

function stepRow({ step, outcome, live, inFlight, run, notes, onPress, onSecret, onChange }) {
  const row = document.createElement("div");
  row.className = "step";
  row.dataset.index = String(step.index);

  const glyph = document.createElement("span");
  glyph.className = "glyph";
  glyph.textContent = outcome ? glyphFor(outcome) : live && step.index === inFlight ? "●" : "○";
  const intent = document.createElement("span");
  intent.className = "intent";
  intent.textContent = step.intent || "";
  row.append(glyph, intent);

  // What the rig charged this step to, in the two senses. `matched_by` is how
  // the control was found -- a locator rung, or `sight` when none matched and
  // the model pointed at the screen, said in words because the operator
  // watching is the one who should know a workaround just happened; `stale`
  // is the rig saying the page has moved under the step. The money is what
  // the call that planned it cost. `unpriced` is said in the word rather than
  // drawn as $0.0000 -- a call that never returned is not a free one, and a
  // ledger that rounds it to nothing is a ledger nobody can add up.
  const meta = [
    step.matched_by === "sight" ? "found by sight" : step.matched_by || null,
    step.stale ? "page moved" : null,
    step.unpriced ? "unpriced" : step.cost_usd > 0 ? `$${step.cost_usd.toFixed(4)}` : null,
  ].filter(Boolean);
  if (meta.length) {
    const said = document.createElement("span");
    said.className = "meta";
    said.textContent = meta.join(" · ");
    row.append(said);
  }

  // The rig has stopped here to ask. What it would send is drawn in words --
  // this is the one moment somebody can read a write before it happens -- and
  // the two answers go on this row rather than under the card, because "yes"
  // means yes to *this* step and a button anywhere else would not say which.
  // Only while the run is live: an `awaiting` row on a run that has since
  // ended is a record, and pressing Approve on it would approve nothing.
  if (outcome === "awaiting" && live) {
    const words = document.createElement("span");
    words.className = "planned";
    // What would go out, or -- where the run stopped for a reason rather than
    // a write -- what it is asking. A list stops once after the first thing
    // with that thing's result in the sentence, and a row with two buttons and
    // no words is a question nobody can answer.
    words.textContent = wordsFor(step.sent) || step.reason || "";
    const approve = document.createElement("button");
    approve.type = "button";
    approve.textContent = "Approve";
    approve.addEventListener("click", () => onPress?.("approve", run, row, approve));
    const stop = document.createElement("button");
    stop.type = "button";
    stop.className = "quiet";
    stop.textContent = "Stop";
    stop.addEventListener("click", () => onPress?.("stop", run, row, stop));
    row.append(words, approve, stop);
  }

  // The step wanted a password and the vault had none.
  //
  // The refusal used to be a sentence naming a vault key, which is a sentence
  // for whoever deploys this system and not for the person it stopped: they
  // are standing in a warehouse with this panel open, and they have no
  // console, no shell, and no way to look up what a vault key is. A refusal
  // only a developer can act on is a refusal nobody acts on -- so the step
  // that wants a password asks for it here, where the person who knows it is.
  //
  // The field is never read back, never defaulted, and never written to
  // `chrome.storage`: it goes to the worker, which puts it in the vault, and
  // is cleared on the way. Drawn for a finished run as well as a live one --
  // this refusal ENDS the run, so the row somebody sees it on is always a
  // record by the time they read it.
  const wants = step.sent?.payload?.needs_secret;
  if (wants && onSecret) {
    const asking = document.createElement("p");
    asking.className = "note";
    asking.textContent = `This job needs your ${(wants.field || "password").replace("-", " ")} for ${wants.system || "this system"}.`;
    const field = document.createElement("input");
    field.type = "password";
    // Not `current-password`: a manager offering to fill this would be
    // offering the credential for the PANEL's own origin, which is not the
    // system being signed into.
    field.autocomplete = "off";
    field.placeholder = wants.field || "password";
    const save = document.createElement("button");
    save.type = "button";
    save.textContent = "Save for this job";
    save.addEventListener("click", async () => {
      const value = field.value;
      field.value = "";
      if (!value) return;
      save.disabled = true;
      const kept = await onSecret({ system: wants.system, field: wants.field, value }, save);
      save.disabled = false;
      asking.textContent = kept?.ok
        ? "Kept. Run this job again and it will sign in."
        : `That could not be kept: ${kept?.error || "the vault did not answer"}`;
    });
    row.append(asking, field, save);
  }

  // Only a step that is still to come, and only one that has values of its own.
  // The step in flight is excluded with the rest of the past: its request may
  // already be in the air, and a control that sometimes works is worse than
  // none.
  const names = namesIn(step);
  if (live && !outcome && step.index > inFlight && names.length) {
    const change = document.createElement("button");
    change.type = "button";
    change.className = "quiet";
    change.textContent = "change";
    change.addEventListener("click", () => {
      change.remove();
      for (const name of names) {
        const field = document.createElement("input");
        field.type = "text";
        field.placeholder = name;
        field.value = run.parameters?.[name] ?? "";
        field.addEventListener("change", () => onChange?.(run.id, name, field.value));
        row.append(field);
      }
    });
    row.append(change);
  }

  for (const note of notes.filter((each) => each.at_step === step.index)) {
    const said = document.createElement("p");
    said.className = "note";
    said.textContent = note.text || "";
    row.append(said);
  }
  return row;
}
