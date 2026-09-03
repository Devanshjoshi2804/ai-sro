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
export function runCard({ run, skill, message, notes = [] }, { onPress, onChange } = {}) {
  const card = document.createElement("div");
  card.className = "run";
  card.dataset.status = run.status;
  card.dataset.runId = run.id;

  const title = document.createElement("p");
  title.className = "what";
  title.textContent = message?.text || `Running ${skill?.name || ""}`.trim();
  card.append(title);

  const done = new Map((run.steps || []).map((step) => [step.index, step]));
  const live = run.status === "running";
  // The next position nothing has recorded. Positions rather than a count: a
  // skill whose body runs once per thing in a list does not know its own length
  // until the system answers, which is why the executor asks per step too.
  const inFlight = Math.max(-1, ...done.keys()) + 1;

  for (const step of skill?.latest?.steps || []) {
    card.append(stepRow({ step, outcome: done.get(step.index), live, inFlight, run, notes, onChange }));
  }

  if (live) {
    const row = document.createElement("div");
    row.className = "row";
    for (const [answer, label] of [
      ["pause", "Stop after this step"],
      ["stop", "Stop"],
    ]) {
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

function stepRow({ step, outcome, live, inFlight, run, notes, onChange }) {
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
