// What this browser has done lately, over the top of whatever you were doing.
//
// An overlay and not a third pane, which is the whole argument: history is
// something you glance at and leave. A pane is somewhere you can be left --
// come back to the panel tomorrow and find it showing last week, with the run
// happening right now behind it. This slides over, says its piece, and closes
// with the press that opened it.
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
export function history(runs, { onClose, said = [], now = Date.now() } = {}) {
  const box = document.createElement("section");
  box.className = "history";
  box.setAttribute("role", "dialog");
  box.setAttribute("aria-label", "Recent tasks");

  const head = document.createElement("div");
  head.className = "history-head";
  const title = document.createElement("h3");
  title.textContent = "Recent tasks";
  const shut = document.createElement("button");
  shut.type = "button";
  shut.className = "quiet";
  shut.textContent = "✕";
  shut.title = "Close";
  shut.setAttribute("aria-label", "Close");
  shut.addEventListener("click", () => onClose?.());
  head.append(title, shut);
  box.append(head);

  box.addEventListener("keydown", (event) => {
    if (event.key === "Escape") onClose?.();
  });

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

  const list = document.createElement("ul");
  list.className = "history-list";
  for (const run of (runs || []).slice(0, K_LINES)) {
    const line = document.createElement("li");
    const what = document.createElement("span");
    what.className = "what";
    what.textContent = run.title || run.workflow_id || "a job";
    const how = document.createElement("span");
    how.className = "detail";
    how.textContent = ENDINGS[run.outcome] || run.outcome || "";
    const when = document.createElement("span");
    when.className = "when";
    when.textContent = ago(run.started_at, now);
    line.append(what, how, when);
    list.append(line);
  }
  box.append(list);
  box.append(...whatThisBrowserSaid(said));
  return box;
}

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
