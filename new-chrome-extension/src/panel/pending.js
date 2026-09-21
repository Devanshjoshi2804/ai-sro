// Everything somebody has been asked for and not answered, in one place.
//
// Home had eleven cards on it. Two of them were the same request twice, four
// were from earlier in the day, and the one that had just arrived was at the
// bottom -- so the panel that exists to say "here is the thing that needs you"
// was saying it eleven times at once, which is the same as not saying it.
// Measured on the deployment 2026-09-18.
//
// So Home keeps ONE: the newest request, beside the run that is happening and
// what just finished. Everything else lives here, and here is behind a count
// -- a person glances at the number, and opens it when the number is wrong.
//
// **A pane, not an overlay.** It was one: a dialog over whatever was behind
// it, with a ✕ to find and a height the stylesheet chose, so a queue of one
// drew a card and two thirds of empty black. The argument for an overlay was
// that this is somewhere you glance and leave, and a pane is somewhere you can
// be left -- but the panel opens on Home every time it opens, so being left
// here lasts until the next time somebody opens it, and costs one press.
// Against that: the full width of the panel, reached by the same control as
// Home and Chat, with nothing to dismiss.
//
// **Grouped by the day they arrived**, newest first. A request is a thing
// somebody asked for on a day, and "Tuesday" is how anybody talks about it --
// a list of clock times with no days in it cannot tell an hour ago from a week
// ago, and those are different decisions.
//
// Pure over what it is given. The cards, and what to do when one is pressed.

/** When something happened, in milliseconds, from either shape it is held in.
 *
 * A nudge's `at` is an ISO STRING -- `nudge.js` stamps it with
 * `new Date(now).toISOString()` -- and everything that reached for it here
 * read `Number(at)`, which is `NaN`. So every request in the list dated to the
 * first of January 1970 and "newest first" sorted nothing at all, because
 * `NaN - NaN` is not an order. The unit tests passed: they were written with
 * numbers, which is the one shape the real thing never uses.
 */
export function when(at) {
  if (typeof at === "number") return Number.isFinite(at) ? at : 0;
  const parsed = Date.parse(String(at ?? ""));
  return Number.isFinite(parsed) ? parsed : 0;
}

/** What a day is called at the top of its group. */
export function dayNamed(at, now = Date.now()) {
  const was = new Date(when(at));
  const today = new Date(now);
  const midnight = (d) =>
    new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const days = Math.round((midnight(today) - midnight(was)) / 86400000);
  if (days <= 0) return "Today";
  if (days === 1) return "Yesterday";
  // Past a week the weekday stops being a date anybody can place: "Tuesday"
  // is this week's Tuesday to everybody who reads it.
  if (days < 7) return was.toLocaleDateString(undefined, { weekday: "long" });
  return was.toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

/** The line under a request's title: what it carries, or that it carries
 * nothing yet.
 *
 * The values are why one request differs from another -- eleven cards all
 * reading `Create a Customer Type` is a list nobody can act on.
 */
function carries(nudge) {
  const said = Object.entries(nudge.values || {})
    .filter(([, value]) => String(value ?? "").trim())
    .map(([name, value]) => `${name}: ${value}`);
  if (!said.length) return "nothing read out of it yet";
  return said.join(" · ");
}

/** Somewhere to put a backlog down.
 *
 * A queue is a month deep because nobody cleared it, and nobody cleared it
 * because clearing it was thirty-four presses of "No thanks" -- so the pane
 * that exists to be acted on becomes a pane that is scrolled past, and the one
 * request that arrived this morning is underneath a fortnight of dead ones.
 *
 * Two presses, because it is not undoable: an offer dismissed reports its
 * fate, and a fate is counted -- "this job is always refused" is how the
 * mining side learns to stop offering it, and thirty of those written by a
 * misplaced thumb is a lie told to the thing that decides what to offer. The
 * second press is the whole confirmation: a browser `confirm()` blocks the
 * extension's own message pump, and a dialog to dismiss a dialog-shaped pile
 * is the thing this pane was just rewritten out of.
 */
function clearer(label, ids, onClear) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "quiet";
  button.dataset.clear = String(ids.length);
  button.textContent = label;
  let asked = false;
  button.addEventListener("click", () => {
    if (!asked) {
      asked = true;
      // And it looks like what it now is. `danger` is already what this panel
      // marks a control that destroys something with, at rest rather than
      // only under a pointer -- a touchscreen never has a pointer.
      button.className = "quiet danger";
      button.textContent = `sure? ${label.toLowerCase()}`;
      return;
    }
    button.disabled = true;
    onClear(ids);
  });
  return button;
}

/**
 * The pane, or `null` when nothing is waiting.
 *
 * `cards` are the open nudges, in any order. `onPress` is the same handler the
 * cards on Home are built with, so a press here is the press there -- one path
 * into the backend for an answer, whichever screen it was given on. `onClear`
 * takes a list of ids: a day of them, or all of them.
 */
export function pending(cards, { onPress, onClear, now = Date.now() } = {}) {
  const waiting = (cards || []).filter((one) => one.state === "open");
  if (!waiting.length) return null;

  const box = document.createElement("section");
  box.className = "history pending";
  // A region and not a dialog. `role="dialog"` tells a screen reader it has
  // been interrupted and must get out; this is a place somebody walked to.
  box.setAttribute("role", "region");
  box.setAttribute("aria-label", "Waiting for you");

  const head = document.createElement("div");
  head.className = "history-head";
  const title = document.createElement("h3");
  const today = waiting.filter(
    (one) => dayNamed(one.at, now) === "Today",
  ).length;
  // The count, and how much of it is today's. A backlog nobody can date reads
  // as one undifferentiated pile; "six, four of them today" is a person
  // deciding what to do this afternoon.
  title.textContent =
    waiting.length === 1
      ? "1 request waiting"
      : `${waiting.length} requests waiting${today && today < waiting.length ? ` · ${today} today` : ""}`;
  // No ✕, and nothing listening for Escape. A pane is left by going somewhere
  // else, which is what the navigation is for -- a second way out, on the
  // surface itself, is a control that has to be found and then explained.
  head.append(title);
  // The whole pile, in one press-and-confirm. Only where there is a pile:
  // "Dismiss all 1" beside a single request is a second way to do what the
  // card under it already does.
  if (onClear && waiting.length > 1) {
    head.append(
      clearer(
        `Dismiss all ${waiting.length}`,
        waiting.map((one) => one.id),
        onClear,
      ),
    );
  }
  box.append(head);

  // Newest first, and the days in the order the newest ones fall in.
  const byDay = new Map();
  for (const one of [...waiting].sort((a, b) => when(b.at) - when(a.at))) {
    const day = dayNamed(one.at, now);
    if (!byDay.has(day)) byDay.set(day, []);
    byDay.get(day).push(one);
  }

  for (const [day, ones] of byDay) {
    const when = document.createElement("h4");
    when.className = "pending-day";
    const named = document.createElement("span");
    named.textContent = `${day} · ${ones.length}`;
    when.append(named);
    // And a day at a time, which is what makes a month-deep queue clearable
    // without also clearing this morning. The grouping was already here for
    // reading; this is the same grouping being acted on.
    if (onClear && byDay.size > 1) {
      when.append(
        clearer(
          `Dismiss ${ones.length}`,
          ones.map((one) => one.id),
          onClear,
        ),
      );
    }
    box.append(when);

    const list = document.createElement("ul");
    list.className = "history-list";
    for (const one of ones) list.append(row(one, onPress));
    box.append(list);
  }
  return box;
}

/** One request: what it is, what it carries, and the two answers.
 *
 * The answers are here rather than only on Home because a list of things
 * needing a decision that cannot be decided from is a list somebody reads and
 * then has to find again somewhere else.
 */
function row(nudge, onPress) {
  const item = document.createElement("li");
  item.dataset.id = nudge.id || "";

  const what = document.createElement("p");
  what.className = "what";
  what.textContent = nudge.title || "A request";
  item.append(what);

  const detail = document.createElement("p");
  detail.className = "detail";
  detail.textContent = carries(nudge);
  item.append(detail);

  // What it is still short of, where it is short: a request that cannot run
  // yet is a different decision from one that can, and pressing yes on it
  // opens a question rather than starting a job.
  if ((nudge.missing || []).length) {
    const short = document.createElement("p");
    short.className = "detail";
    short.dataset.kind = "short";
    short.textContent = `still needs ${nudge.missing.join(", ")}`;
    item.append(short);
  }

  const row_ = document.createElement("div");
  row_.className = "row";
  // The flag and not only `disabled`. A disabled button does not fire in a
  // browser, which is most of the guarantee -- but "one request, one fate" is
  // worth holding in the handler rather than in an attribute anything could
  // set back.
  let ended = false;
  // The buttons themselves, held rather than queried back off the row: a
  // selector is a second description of what was just built, and one that
  // answers `.children` in a browser and something else in a test is a guard
  // that only works in the test.
  const made = [];
  for (const { answer, label, quiet } of [
    { answer: "do", label: "Do it", quiet: false },
    { answer: "not-here", label: "No thanks", quiet: true },
  ]) {
    const button = document.createElement("button");
    button.type = "button";
    if (quiet) button.className = "quiet";
    button.textContent = label;
    button.addEventListener("click", () => {
      // One press ends the row, for the reason the card keeps: the list does
      // not redraw on an answer, so without this both buttons stay live under
      // the cursor and "No thanks" then "Do it" is two fates for one request.
      if (ended) return;
      ended = true;
      for (const each of made) each.disabled = true;
      item.dataset.answered = answer;
      onPress?.(answer, nudge, item, button);
    });
    made.push(button);
    row_.append(button);
  }
  item.append(row_);
  return item;
}
