// What this browser has done lately, over the top of whatever you were doing.
//
// A pane and not an overlay. It was one, and as an overlay it drew its lines
// straight through whatever was behind it -- measured on the deployment
// 2026-09-21, `Create a Customer Type` superimposed on `Log in to Keycloak —
// an arrival trigger fired. Shall I?`, both legible and neither readable.
//
// The argument for an overlay was that this is something you glance at and
// leave, and a pane is somewhere you can be left: come back tomorrow and find
// the panel showing last week. The panel opens on Home every time it opens --
// which pane you are on is not stored -- so that costs one press, and buys a
// surface the width of the panel for a run record that wants it.
//
// **A line each, and the line is what happened.** Not a card: a card is for
// something that wants a decision, and every one of these is over. The title,
// what came of it, and when -- in that order, because the question somebody
// opens this to answer is "did the customer type one get made".
//
// **Newest first**, which is what the backend already answers with.
//
// Pure over what it is given: the runs, and what to do when somebody closes
// it. Nothing here fetches, and nothing here keeps state.

import { dayNamed } from "./pending.js";

/** How many lines. Beyond this it is a log, and the console is where a log is
 * read -- a panel beside a warehouse screen is not where somebody scrolls
 * through two hundred runs. */
export const K_LINES = 12;

/** How many of this browser's own lines are shown under the runs.
 *
 * Fewer than the runs, and last, because they answer a narrower question.
 * A run that ended is a thing a person recognises; a refusal is what they go
 * looking for once the run does not explain itself. Six is the last minute or
 * two of a browser that is going wrong, which is the window somebody is in
 * when they open this. */
export const K_SAID = 6;

/** What each outcome is called where a person reads it.
 *
 * The rig's own words, which are not the backend's: `held` is a run every step
 * of which held, and calling it "succeeded" would be this panel translating a
 * verdict it did not make. Anything unlisted is shown as it came -- a
 * deployment may add an outcome, and a browser that drew nothing for it would
 * hide the run rather than the word.
 */
export const ENDINGS = {
  held: "done",
  stopped: "stopped to ask",
  refused: "refused",
  aborted: "stopped by you",
  failed: "failed",
  running: "running",
};

/**
 * The overlay, or `null` when there is nothing to show yet.
 *
 * `runs` are `WorkflowRunModel` rows as the backend sends them. `onClose` is
 * the way out, which is also the escape key: an overlay a person cannot
 * dismiss without finding the one small button is a trap on a 360-pixel panel.
 */
export function history(runs, { onOpen, said = [], now = Date.now() } = {}) {
  const box = document.createElement("section");
  box.className = "history";
  // A region and not a dialog. `role="dialog"` tells a screen reader it has
  // been interrupted and must get out; this is a place somebody walked to.
  box.setAttribute("role", "region");
  box.setAttribute("aria-label", "Recent tasks");

  const head = document.createElement("div");
  head.className = "history-head";
  const title = document.createElement("h3");
  title.textContent = "Recent tasks";
  // No ✕, and nothing listening for Escape. A pane is left by going somewhere
  // else, which is what the navigation is for.
  head.append(title);
  box.append(head);

  if (!runs.length && !said.length) {
    const none = document.createElement("p");
    none.className = "detail";
    // Not "nothing has run": this browser may simply not have been told yet,
    // and a panel that reports an absence it has not established is a panel
    // that lies quietly.
    none.textContent = "Nothing here yet.";
    box.append(none);
    return box;
  }

  // Grouped by the day it ran, newest first -- the backlog's grouping, and
  // the same function, because "when was this" is one question and a panel
  // that answered it two ways would be two panels.
  //
  // Twelve lines reading `Log in to Keycloak` is what this pane looked like
  // without it: a list where every entry is the same words, so the only thing
  // that tells one from another is when it happened and how it ended.
  // Measured on the deployment 2026-09-21.
  const byDay = new Map();
  for (const run of (runs || []).slice(0, K_LINES)) {
    const day = dayNamed(run.started_at, now);
    if (!byDay.has(day)) byDay.set(day, []);
    byDay.get(day).push(run);
  }

  for (const [day, ofThatDay] of byDay) {
    const heading = document.createElement("h4");
    heading.className = "pending-day";
    const named = document.createElement("span");
    named.textContent = `${day} · ${ofThatDay.length}`;
    heading.append(named);
    box.append(heading);
    box.append(_linesOf(ofThatDay, onOpen, now));
  }
  box.append(...whatThisBrowserSaid(said));
  return box;
}

function _linesOf(runs, onOpen, now) {
  const list = document.createElement("ul");
  list.className = "history-list";
  for (const run of runs) {
    const line = document.createElement("li");
    // A line you can open.
    //
    // These were three spans and nothing to press. The question somebody
    // opens this to answer is "did the customer type one get made", and the
    // answer is in the run -- which the browser is already holding whole,
    // because the list door answers whole rows. A list of titles over records
    // nobody can reach is a list that stops one question short of its own
    // purpose.
    //
    // A button, not a click on the row: a row that does something is a
    // control, and a control that is not a button is one a keyboard cannot
    // reach and a screen reader does not announce.
    const open = document.createElement("button");
    open.type = "button";
    open.className = "history-line";
    const what = document.createElement("span");
    what.className = "what";
    what.textContent = run.title || run.workflow_id || "a job";
    // `status` is what a run carries in this panel -- `asPanelRun` maps the
    // backend's `outcome` onto it, and the run card has drawn it by that name
    // since there were two kinds of run. `outcome` as well, because a row
    // that never went through that map is still a row somebody is reading.
    const ended = run.status || run.outcome || "";
    const how = document.createElement("span");
    how.className = "detail";
    how.textContent = ENDINGS[ended] || ended || "";
    // And what KIND of ending, for the one thing colour is good for: finding
    // the run that went wrong in a list where every line says the same words.
    line.dataset.ended = TONES[ended] || "";
    const when = document.createElement("span");
    when.className = "when";
    when.textContent = ago(run.started_at, now);
    open.append(what, how, when);
    open.addEventListener("click", () => onOpen?.(run, line));
    line.append(open);
    list.append(line);
  }
  return list;
}

/** Which endings are worth a colour, and which way.
 *
 * Three, not six: a palette with a shade per outcome is a legend to learn.
 * The question this pane is opened with is "did it work", so it answers in
 * the two ways that are not "it worked" -- and `running` is neither, it is
 * the one still going.
 */
export const TONES = {
  failed: "bad",
  refused: "bad",
  stopped: "asking",
  aborted: "asking",
  running: "live",
};

/** This browser's own last few refusals, under the runs.
 *
 * The lines are already kept and already shipped -- the heartbeat carries them
 * and the deployment writes them beside its own. What was missing is the
 * operator's own copy: they are standing in front of the browser that refused,
 * being told nothing, while the only account of it travels to a server they
 * cannot read.
 *
 * Shown as they were written, which is deliberate. These are not sentences
 * composed for this surface -- they are what went up the wire, ids and all, so
 * that an operator reading one to somebody on a call is reading the same
 * string that is in the deployment's log.
 *
 * Empty draws nothing at all. A heading over an empty list is a panel telling
 * somebody where a thing would be if it existed.
 */
function whatThisBrowserSaid(said) {
  const lines = (said || []).slice(-K_SAID).reverse();
  if (!lines.length) return [];
  const title = document.createElement("h4");
  title.className = "history-said-head";
  title.textContent = "This browser said";
  const list = document.createElement("ul");
  list.className = "history-said";
  for (const line of lines) {
    const row = document.createElement("li");
    row.className = "detail";
    row.textContent = String(line);
    list.append(row);
  }
  return [title, list];
}

/** How long ago, in the words somebody would use.
 *
 * Minutes up to an hour, then hours, then days. A timestamp is what the
 * console shows; on this surface the question is "was that the one I just
 * pressed" and a clock time makes somebody do the subtraction.
 */
export function ago(when, now = Date.now()) {
  const at = Date.parse(when || "");
  if (!Number.isFinite(at)) return "";
  const seconds = Math.max(0, Math.round((now - at) / 1000));
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}
