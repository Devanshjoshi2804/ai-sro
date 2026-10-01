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

import { passwordBox, standingPassword } from "./password-box.js";

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
  //
  // `not_needed` is a DASH, and this is the second time it has been argued.
  // It was `✓!` for a day (the fallback below), which reads as "it went out
  // and nothing could say whether it landed" -- the opposite of the truth. It
  // was then a tick, on the argument that the step was over and the job whole.
  //
  // Measured against a real card, 2026-09-16: five ticks, one cross, above a
  // line reading "Nobody was watching, so it replayed the call it learned --
  // the page never moved". An operator read five things done and one failed;
  // nothing at all had been done on the page. A tick is the mark this panel
  // uses for "that happened", and the whole meaning of `not_needed` is that it
  // did not happen and did not need to. The dash says so and nothing else.
  if (typeof outcome === "string") {
    return (
      {
        held: "✓",
        done_by_operator: "✓",
        withheld: "⏸",
        awaiting: "⏸",
        not_needed: "–",
        failed: "✗",
        refused: "✗",
        skipped: "○",
      }[outcome] || "✓!"
    );
  }
  if (outcome.disposition === "failed") return "✗";
  if (outcome.disposition === "withheld") return "⏸";
  if (outcome.disposition === "performed") {
    const checked =
      outcome.confirmed && !(outcome.assertion_failures || []).length;
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
  { onPress, onChange, onSecret, onPassword, stop = true } = {},
) {
  const card = document.createElement("div");
  card.className = "run";
  card.dataset.status = run.status;
  card.dataset.runId = run.id;

  const title = document.createElement("p");
  title.className = "what";
  title.textContent = message?.text || `Running ${skill?.name || ""}`.trim();
  card.append(title);

  // A Steel run that could not sign in, asking for its password right here.
  const asked = standingPassword(run);
  if (asked && onPassword)
    card.append(passwordBox(asked, { runId: run.id, onPassword }));

  // What nobody typed.
  //
  // A value an operator filled in needs no provenance: they were standing
  // there and they meant it. A value read out of their mailbox is only as good
  // as the message it came from, and the run has recorded which one since the
  // gather existed -- the id and the few words it was quoted from -- while no
  // surface has ever shown it. Recorded and invisible is the same as not
  // recorded to the person deciding whether the run did the right thing.
  //
  // The span, not the whole mail. It is what somebody checks the reading
  // against without opening anything, and the mail itself is in their mailbox
  // where it already was.
  for (const [name, found] of Object.entries(run.gathered || {})) {
    const said = document.createElement("p");
    said.className = "detail";
    const quoting = String(found?.quoting || "").trim();
    said.textContent =
      `${name}: ${found?.value ?? ""} — read from your mail` +
      (quoting ? ` (“${quoting}”)` : "");
    card.append(said);
  }

  // Who drove it, and so what there is to draw and to press. A record with no
  // `source` is a backend run -- older rows have none, and reading a missing
  // field as "rig" would send a backend run's Stop somewhere it has never been
  // heard of.
  const rig = run.source === "rig";

  // Why a run can finish having touched nothing on the page.
  //
  // A run nobody was watching -- a trigger at three in the morning -- replays
  // the call the demonstration made instead of filling the form: the record
  // appears in the warehouse and no screen ever moves. Read afterwards with no
  // explanation that is indistinguishable from a run that did nothing, so the
  // card says which of the two ways it did the job.
  //
  // Only in that direction. A watched run types into the form and presses Save
  // in front of the person, and telling them what they are looking at is
  // noise. `=== false` because a row from before this distinction existed has
  // no field, and those runs replayed.
  if (rig && run.watched === false) {
    const how = document.createElement("p");
    how.className = "detail";
    how.textContent =
      "Nobody was watching, so it replayed the call it learned — the page never moved.";
    card.append(how);
  }
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

  // What this run made, named.
  //
  // Nothing in this system can take a warehouse record back: the guards in
  // front of a run -- a door that says when it is unsure, a list that proves
  // the first thing before doing the rest -- stop wrong records being made and
  // do nothing about one that was. So a run that made records says which, in
  // the words the warehouse used, and a person can go and look at them.
  const made = (run.steps || [])
    .map((step) => step.made || {})
    .filter((one) => Object.keys(one).length);
  if (rig && !live && made.length) {
    const line = document.createElement("p");
    line.className = "note";
    // And whether anything can take them back. Said in words and not drawn as
    // a button: what an undo would have to do is address each record by
    // whatever the warehouse called it, and a wrong mapping deletes the wrong
    // record. Where nothing can, saying so is the honest half -- an operator
    // who has just watched three records be made needs to know that the
    // taking-back is theirs to do.
    line.textContent =
      `Made ${made.length} record${made.length === 1 ? "" : "s"}. ` +
      (run.undo
        ? "A job you have done before takes these back — open it in the console."
        : "Nothing here can take them back.");
    card.append(line);

    // The record itself, in the warehouse's own field names.
    //
    // This was `Object.values(...).join(" ")` -- "made 1 record: GQV leaning
    // new SRO type 006" -- which drops the half that says what each value IS.
    // The backend already picks the fields that name the row out of whatever
    // the system answered (`made_by`), so the names are there and were being
    // thrown away one line before a person read them.
    //
    // Nothing here knows which fields a system will send: a customer type
    // comes back with `customerType`, an order with an id and a status, and
    // this draws whatever arrived rather than a shape it was taught.
    for (const record of made) {
      const said = document.createElement("p");
      said.className = "detail";
      said.textContent = Object.entries(record)
        .map(([name, value]) => `${name}: ${value}`)
        .join(" \u00b7 ");
      card.append(said);
    }
  }

  // What a dry run held back. There is no other screen it could be said on --
  // phase 5 left one system, and this card is where the writes were drawn in
  // words -- and the operator watching them be planned is the person who needs
  // to know they did not happen.
  const withheld = rig && !live ? (run.withheld || []).length : 0;
  if (withheld) {
    const line = document.createElement("p");
    line.className = "note";
    line.textContent = `dry run — ${withheld} write${withheld === 1 ? "" : "s"} shown here, not sent`;
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
      button.addEventListener("click", () =>
        onPress?.(answer, run, card, button),
      );
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
  // The whole mail, because approving it is sending it: a mail cannot be
  // unsent, and its words are a model's.
  if (sent.kind === "mail.send")
    return `send to ${p.to || "?"} — "${p.subject || ""}"\n\n${p.body || ""}`;
  const where = (p.locators || [])[0]?.query || "";
  return `${p.action || "act"}${p.value ? ` "${p.value}"` : ""} ${where}`.trim();
}

function stepRow({
  step,
  outcome,
  live,
  inFlight,
  run,
  notes,
  onPress,
  onSecret,
  onChange,
}) {
  const row = document.createElement("div");
  row.className = "step";
  row.dataset.index = String(step.index);

  const glyph = document.createElement("span");
  glyph.className = "glyph";
  const now = !outcome && live && step.index === inFlight;
  glyph.textContent = outcome ? glyphFor(outcome) : now ? "●" : "○";
  // What the stylesheet colours the circle by. The character is the meaning
  // and stays the text; this only lets the tone follow it.
  glyph.dataset.glyph = glyph.textContent;
  // The one thing on this panel that should move. A run in flight and a run
  // that stopped on a live step draw the identical dot otherwise, and "still
  // going" is the question somebody watching actually has. The stylesheet
  // decides what moving means, and stops it for anybody who asked for less.
  if (now) glyph.dataset.live = "true";
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
    step.unpriced
      ? "unpriced"
      : step.cost_usd > 0
        ? `$${step.cost_usd.toFixed(4)}`
        : null,
  ].filter(Boolean);
  if (meta.length) {
    const said = document.createElement("span");
    said.className = "meta";
    said.textContent = meta.join(" · ");
    row.append(said);
  }

  // The rig has stopped here to ask.
  //
  // The WORDS whether or not the run is still going, the BUTTONS only while it
  // is. Those were one condition, and an operator paid for it all evening:
  // twelve runs in one day, every one of them ending `stopped`, and every one
  // drew this row as a bare ⏸ with no question on it -- because a stopped run
  // is not live, and the sentence saying what it had asked for was rendered
  // inside the same branch as the Approve.
  //
  // The buttons really do belong to a live run: an `awaiting` row on a run
  // that has ended is a record, and pressing Approve on it would approve
  // nothing. But a question nobody can read is worse than a question nobody
  // can answer -- "The run stopped to ask" with nothing saying what it asked
  // is the panel shrugging.
  if (outcome === "awaiting") {
    const words = document.createElement("span");
    words.className = "planned";
    // What would go out, or -- where the run stopped for a reason rather than
    // a write -- what it is asking. A list stops once after the first thing
    // with that thing's result in the sentence.
    words.textContent = wordsFor(step.sent) || step.reason || "";
    row.append(words);
  }
  // What the field dictionary already knows about the values this step writes,
  // and the reason it is drawn BEFORE the buttons: it is the thing the person
  // tapping Approve most needs and would otherwise never learn. A column that
  // keeps four characters of six answers 201 either way, so no rung of the
  // ladder below can say it and no later screen shows it.
  for (const note of step.notes || []) {
    const said = document.createElement("span");
    said.className = "note";
    said.textContent = note;
    row.append(said);
  }
  if (outcome === "awaiting" && live) {
    const approve = document.createElement("button");
    approve.type = "button";
    approve.textContent = "Approve";
    approve.addEventListener("click", () =>
      onPress?.("approve", run, row, approve),
    );
    const stop = document.createElement("button");
    stop.type = "button";
    stop.className = "quiet";
    stop.textContent = "Stop";
    stop.addEventListener("click", () => onPress?.("stop", run, row, stop));
    row.append(approve, stop);
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
    // Two answers, because there are two. A credential the deployment should
    // keep is stored and reused by every run that signs into this system; one
    // the operator is lending for the job in front of them is held for the
    // next step that types it and forgotten. Offering only the first made
    // every password a permanent one, which is a decision nobody was asked
    // about -- and on a system whose credential is not this deployment's to
    // hold, the only way through was to store it anyway.
    const press = (label, quiet, once) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = label;
      if (quiet) button.className = "quiet";
      button.addEventListener("click", async () => {
        const value = field.value;
        field.value = "";
        if (!value) return;
        button.disabled = true;
        const kept = await onSecret(
          { system: wants.system, field: wants.field, value, once, runId: run.id },
          button,
        );
        button.disabled = false;
        asking.textContent = kept?.ok
          ? once
            ? "Held for the next run only. Run this job again and it will sign in."
            : "Kept. Run this job again and it will sign in."
          : `That could not be kept: ${kept?.error || "the vault did not answer"}`;
      });
      return button;
    };
    row.append(
      asking,
      field,
      press("Save for this job", false, false),
      press("Just this once", true, true),
    );
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
        field.addEventListener("change", () =>
          onChange?.(run.id, name, field.value),
        );
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
