// The surface docked beside the system the operator is working in.
//
// Everything above the console frame is native, because everything on it needs
// `chrome.*` or needs to know which tab this is: teaching is a control you want
// beside the page being taught, a run driving this browser has to be stoppable
// while it happens, and "tasks you keep doing *here*" is a question a page that
// does not know the host cannot ask.
//
// What is drawn is one card per thing that is true, in the order somebody
// should deal with it. Not connected outranks not observing, which outranks a
// closed channel; a demonstration in progress outranks all of them, because
// while one is running the panel is about that and nothing else.

import { hostMatches } from "../background/scripts.js";
import { transcript } from "./transcript.js";

const $ = (id) => document.getElementById(id);

/** Whether the tenant excludes this host by default.
 *
 * The rule is imported rather than restated: `hostMatches` is the one
 * definition of it, and this file having its own copy is how the panel would
 * come to disagree with the worker about whether a page is being recorded.
 */
function excludedByDefault(status) {
  if (!tabHere.host) return false;
  return (status.policy?.exclude_hosts || []).some((pattern) =>
    hostMatches(tabHere.host, pattern),
  );
}

async function ask(message) {
  const answer = await chrome.runtime.sendMessage(message);
  if (answer?.error) {
    // This panel reloads with its own page; the worker behind it does not.
    // After an update, a new panel talks to the old worker and every new
    // message comes back "no such message" -- which reads as a broken button
    // rather than as a browser that has not picked the update up yet.
    if (String(answer.error).startsWith("no such message")) {
      throw new Error(
        "this browser is still running an older copy of the extension — " +
          "reload it at chrome://extensions, then try again",
      );
    }
    throw new Error(answer.error);
  }
  return answer;
}

/** The tab this panel is docked beside.
 *
 * The active one, which is the whole point of a panel. Where that is not an
 * ordinary page -- a settings tab in front, or this page opened as a tab rather
 * than docked -- the last ordinary page in the same window, which is the same
 * rule the worker falls back to and the same answer an operator would give.
 */
async function beside() {
  const ordinary = (tab) => /^https?:/.test(tab?.url || "");
  const [active] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (ordinary(active)) return active;
  const inThisWindow = await chrome.tabs.query({ currentWindow: true });
  return (
    inThisWindow
      .filter(ordinary)
      .sort((a, b) => (b.lastAccessed || 0) - (a.lastAccessed || 0))[0] || null
  );
}

function hostOf(url) {
  try {
    return new URL(url).hostname.toLowerCase();
  } catch {
    return "";
  }
}

function clock(since) {
  const seconds = Math.max(0, Math.round((Date.now() - since) / 1000));
  return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

// -- building a card ---------------------------------------------------------

/** One thing that is true, and what can be done about it.
 *
 * A panel that reports a problem without a way out is a panel people stop
 * reading, so a card that has an action carries it; one that does not says why
 * in a sentence somebody can act on elsewhere.
 */
function card({ title, says, metrics, notes, stage, progress, tone, actions = [], toggle }) {
  const holder = document.createElement("section");
  holder.className = "card";
  if (tone) holder.dataset.tone = tone;

  if (title) {
    const heading = document.createElement("h3");
    // `toggle` is only ever passed by `watchCard()` below -- every other
    // caller here gets the plain heading it always had.
    if (toggle) {
      const text = document.createElement("span");
      text.textContent = title;
      heading.append(text, chevronButton(toggle));
    } else {
      heading.textContent = title;
    }
    holder.append(heading);
  }
  if (says) {
    const line = document.createElement("p");
    line.textContent = says;
    holder.append(line);
  }
  if (metrics) {
    const line = document.createElement("p");
    line.className = "metrics";
    line.textContent = metrics;
    holder.append(line);
  }
  // A line each, for a card that has several small facts rather than one --
  // the values a mail gave up, where each of them came from.
  for (const note of notes || []) {
    const line = document.createElement("p");
    line.className = "metrics";
    line.textContent = note;
    holder.append(line);
  }
  if (progress) {
    const bar = document.createElement("div");
    bar.className = "progress";
    for (let step = 0; step < progress.of; step += 1) {
      const segment = document.createElement("span");
      segment.dataset.done = String(step < progress.done);
      bar.append(segment);
    }
    holder.append(bar);
  }
  if (stage) {
    const line = document.createElement("p");
    line.className = "stage";
    line.textContent = stage;
    holder.append(line);
  }

  const row = document.createElement("div");
  row.className = "row";
  for (const action of actions) {
    if (!action) continue;
    const button = document.createElement("button");
    button.type = "button";
    if (!action.primary) button.className = "quiet";
    button.textContent = action.label;
    button.disabled = Boolean(action.disabled);
    button.addEventListener("click", () => action.act(button));
    row.append(button);
  }
  if (row.childElementCount) holder.append(row);
  return holder;
}

// -- the states --------------------------------------------------------------

function render(status) {
  const cards = [];

  if (!status.deviceId) {
    cards.push(
      card({
        title: "Not connected",
        says:
          "This browser has no credential. Nothing is recorded and no task can be "
          + "taught until it is connected to your deployment.",
        tone: "attention",
        actions: [{ label: "Connect", primary: true, act: () => chrome.runtime.openOptionsPage() }],
      }),
    );
  } else if (status.teaching) {
    cards.push(recording(status));
  } else {
    cards.push(watching(status));
  }

  // Before the run and after the state card: it is the only thing here waiting
  // on the person. Not while teaching, because then the panel is about the
  // demonstration and nothing else -- the offer keeps.
  if (!status.teaching) for (const offer of status.offers || []) cards.push(offering(offer));

  if (status.performing) cards.push(performing(status));
  // Not while teaching, same rule as the offers above: a demonstration in
  // progress is the only thing the panel is about. Placed after the run that
  // is happening now and before what is wrong, because it outranks neither --
  // it is a look back at the last thing this browser did, not a fault.
  if (!status.teaching && status.finished) cards.push(finished(status));
  for (const trouble of troubles(status)) cards.push(trouble);

  $("cards").replaceChildren(...cards);
  // Green means this tab -- the one the panel is docked beside -- is being
  // recorded. A dot that went green for "capture is enabled somewhere" told an
  // operator their work was being kept when nothing in front of them was.
  const watchedHere = (status.watched || []).some((entry) => entry.tabId === tabHere.tabId);
  $("where").dataset.state = status.teaching
    ? "recording"
    : status.capturing && watchedHere
      ? "observing"
      : status.deviceId
        ? "unknown"
        : "unknown";

  // While a demonstration is being recorded the panel is about that and
  // nothing else, and none of it applies to a browser that is not connected.
  $("here").hidden = Boolean(status.teaching) || !status.deviceId;
  $("thread").hidden = Boolean(status.teaching) || !status.deviceId;
  $("ask").disabled = !status.deviceId;
  $("purge").disabled = !status.deviceId;
  return status;
}

/** A demonstration, while it is being recorded.
 *
 * It counts out loud. A recording that is capturing nothing looks exactly like
 * one that is capturing everything until it is stopped, and finding out then
 * means doing the task again.
 */
function recording(status) {
  const since = Date.parse(status.teaching.startedAt || "") || Date.now();
  const seen = status.queued ?? 0;
  return card({
    title: "Recording your demonstration",
    says: "Do the task normally. Gestures, network calls and the page structure are being captured.",
    metrics: `${clock(since)} · ${seen} thing${seen === 1 ? "" : "s"} seen`,
    tone: "live",
    actions: [
      { label: "Stop and save", primary: true, act: (button) => stopTeaching(button) },
      { label: "Discard", act: (button) => stopTeaching(button, { discard: true }) },
    ],
  });
}

/** Whether the operator has opened the watching card past what its own state
 * calls for. Remembered here, across redraws, rather than reset by the
 * panel's own two-second poll -- a poll that closed a card the moment
 * somebody opened it to press "Start teaching" would make the press
 * impossible. It decides nothing on its own: a state that needs an answer
 * (see `watchCard` below) opens regardless of it, and can only ever be
 * opened further by it, never closed.
 */
let watchOpen = false;

function watching(status) {
  const paused = status.paused || status.serverPaused;
  if (paused) {
    return watchCard(status, true, null, {
      title: "Paused",
      says: status.serverPaused
        ? "Observation is paused for everyone on this deployment."
        : "Nothing is being recorded until you resume.",
      actions: [pauseAction(status)],
    });
  }

  const watched = status.watched || [];
  const mine = watched.find((entry) => entry.tabId === tabHere.tabId) || null;
  const others = watched.length - (mine ? 1 : 0);
  const elsewhere = others
    ? ` ${others} other tab${others === 1 ? " is" : "s are"} being watched.`
    : "";

  // Nothing is watched unless somebody said so. The alternative -- recording
  // every tab and sorting it out later -- is what put a console's own polling
  // into the evidence and a mail client one policy edit away from it.
  if (!mine) {
    // A host the tenant excludes by default -- webmail, a sign-in page -- can
    // still be watched, because a task that involves the operator's mail
    // cannot be demonstrated otherwise. What it must never be is quiet: this
    // is the one place somebody agrees to their own mailbox being recorded,
    // and a button that said the same thing here as on the WMS would be
    // consent nobody gave.
    const excluded = excludedByDefault(status);
    return watchCard(status, true, null, {
      title: excluded ? `${tabHere.host} is not normally recorded` : "Not watching this tab",
      says: excluded
        ? `${tabHere.host} is excluded for everyone in this tenant by default.` +
          " You can watch it anyway, for this tab: everything in it becomes evidence" +
          " -- its calls, its screens, wherever it navigates -- until you close the tab" +
          " or stop watching. Nobody else can turn this on for you." +
          elsewhere
        : (tabHere.host
            ? `Nothing in ${tabHere.host} is being recorded.`
            : "Open the system you work in.") +
          " Watch a tab and everything in it is evidence -- its calls, its screens," +
          " wherever it navigates." +
          elsewhere,
      // No tone. Not watching is the resting state of this panel, not a fault,
      // and it wore the same amber as "not observing", "this browser cannot be
      // reached" and "last error" -- so when something is actually wrong it
      // looked identical to the ordinary Tuesday. The orange button below is
      // what makes this the card to deal with.
      actions: [
        {
          label: excluded ? `Watch ${tabHere.host} anyway` : "Watch this tab",
          primary: true,
          disabled: !status.capturing || !tabHere.tabId,
          act: (button) => setWatch(button, true),
        },
        pauseAction(status),
      ],
    });
  }

  // A tab whose page-realm patch outlived the extension that installed it.
  //
  // It records gestures and not one call. That is invisible from both sides --
  // the panel says watching, uploads keep arriving -- and it only shows up days
  // later as a skill that checks nothing, by which time the demonstrations are
  // gone. It cannot be repaired from here: the patch lives in the page's own
  // realm, and the handshake that makes it trustworthy can only happen before
  // any page script exists. Reloading the page is the whole fix, so the panel
  // asks for that and says why.
  if ((status.deaf || []).includes(mine.tabId)) {
    return watchCard(status, true, mine, {
      tone: "attention",
      title: "This tab is only recording half of what you do",
      says:
        "The extension was reloaded while this page was open, so what it does" +
        " is being recorded and what it asks the system for is not. A task" +
        " recorded that way becomes a skill that cannot check its own work," +
        " and teaching is refused here until it is fixed. Reloading the page" +
        " fixes it.",
      actions: [
        { label: "Reload this page", primary: true, act: (button) => reloadWatched(button) },
        { label: "Stop watching", act: (button) => setWatch(button, false) },
      ],
    });
  }

  // Watching a host the tenant excludes by default is not the resting state
  // this row collapses to -- it is the one place somebody agreed to their own
  // mailbox, or whatever else is excluded, being recorded, and that agreement
  // is worth reading again every time this card is drawn, not once and then
  // folded away with the ordinary case.
  const granted = excludedByDefault(status);
  if (granted) {
    return watchCard(status, true, mine, {
      title: `Watching ${mine.host}, which is normally excluded`,
      says:
        `You turned this on for ${mine.host}. Everything you do here is evidence,` +
        " until you close the tab or stop watching." +
        elsewhere,
      // Said out loud, because it is a change to the screen they are working
      // on. Chrome puts a debugging banner up for it on any browser that did
      // not install this by policy, and an operator meeting that with no
      // explanation has been given a reason to distrust everything else the
      // panel says.
      metrics:
        `since ${clock(mine.since)}` +
        (status.policy?.capture_snapshots ? " · reading this page's structure too" : ""),
      actions: [
        {
          label: "Start teaching",
          primary: true,
          disabled: !status.capturing,
          act: (button) => startTeaching(button),
        },
        { label: "Stop watching", act: (button) => setWatch(button, false) },
        pauseAction(status),
      ],
    });
  }

  // Nothing here is asking to be answered: this tab has been evidence for a
  // while and stays that way until something changes. A card the size of
  // "not watching" or "paused" for a fact nobody needs to act on is a card
  // people stop reading -- so this collapses to the one line that fact
  // earns, with a chevron back to everything below (`watchCard` decides).
  return watchCard(status, false, mine, {
    title: "Watching this tab",
    says:
      `Everything you do in ${mine.host || "this tab"} is evidence. What you repeat` +
      " becomes a task worth offering; teach one deliberately at any time." +
      elsewhere,
    metrics:
      `since ${clock(mine.since)}` +
      (status.policy?.capture_snapshots ? " · reading this page's structure too" : ""),
    actions: [
      {
        label: "Start teaching",
        primary: true,
        disabled: !status.capturing,
        act: (button) => startTeaching(button),
      },
      { label: "Stop watching", act: (button) => setWatch(button, false) },
      pauseAction(status),
    ],
  });
}

/** The chevron that flips `watchOpen` and redraws from the same status.
 *
 * Only on a card that can actually close. A state that needs an answer is
 * open whatever `watchOpen` says (`watchCard` ORs `needsAnswer` back in), so
 * a chevron there is a control an operator can press and watch do nothing.
 */
function chevronButton({ open, onToggle }) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "chevron";
  button.setAttribute("aria-expanded", String(open));
  button.textContent = open ? "▾" : "▸";
  button.addEventListener("click", onToggle);
  return button;
}

/** The watching card, collapsed or not.
 *
 * `needsAnswer` decides the floor, never the ceiling: a state that needs a
 * press is always open, no matter what the operator last chose, and a
 * steady one opens only when they choose it -- so `open` is the one OR of
 * the two, and closing the card can only ever move `watchOpen`, never force
 * `needsAnswer` shut.
 *
 * The collapsed line still has to answer the one question this whole panel
 * exists to guarantee an answer to -- whether this tab is evidence -- so it
 * reuses `built.title`, which already says exactly that in every branch
 * `watching()` has ("Watching this tab", "Paused", "Not watching this
 * tab", ...), rather than a second, shorter sentence written here that
 * could drift from it.
 */
function watchCard(status, needsAnswer, mine, built) {
  const open = needsAnswer || watchOpen;
  const toggle = {
    open,
    onToggle: () => {
      watchOpen = !watchOpen;
      render(status);
    },
  };

  if (!open) {
    const holder = document.createElement("div");
    holder.className = "card line";
    const dot = document.createElement("span");
    dot.className = "dot";
    const said = document.createElement("p");
    // `mine` is null on every state that has no watch to describe. Those all
    // pass `needsAnswer`, so none of them reaches here today -- and a card
    // that stopped needing an answer should collapse, not throw.
    said.textContent = mine
      ? `${built.title} — ${mine.host || "this tab"}, ${clock(mine.since)}`
      : built.title;
    holder.append(dot, said, chevronButton(toggle));
    return holder;
  }

  // No chevron where pressing it cannot close anything.
  return card({ ...built, toggle: needsAnswer ? undefined : toggle });
}

function pauseAction(status) {
  return {
    label: status.paused ? "Resume" : "Pause",
    disabled: Boolean(status.serverPaused),
    act: async () => {
      const now = await ask({ kind: "status" });
      render(await ask({ kind: "set-paused", paused: !now.paused }));
    },
  };
}

/** Reload the watched tab, which is the whole fix for a half-deaf one.
 *
 * From here rather than by telling somebody to press F5, because the sentence
 * that explains why is on this card and the button should be beside it. */
async function reloadWatched(button) {
  button.disabled = true;
  try {
    await chrome.tabs.reload(tabHere.tabId);
  } catch (error) {
    said(String(error));
  }
  await refresh();
}

async function setWatch(button, on) {
  button.disabled = true;
  try {
    await ask({ kind: on ? "watch-tab" : "unwatch-tab", tabId: tabHere.tabId, url: tabHere.url });
  } catch (error) {
    said(error.message);
  }
  await refresh();
}

/** A run driving this browser, possibly started somewhere else.
 *
 * Stoppable from here because this is where somebody sees it happening: a run
 * started by a schedule is otherwise a cursor moving on its own.
 */
function performing(status) {
  const run = status.performing;
  const done = Number.isFinite(run.step) ? run.step : null;
  const total = run.of && done !== null && done <= run.of ? run.of : null;
  return card({
    title: run.skill ? `“${run.skill}” is running` : "A run is performing here",
    says:
      (run.because || "Started elsewhere") +
      (done === null ? "." : total ? `. Step ${done} of ${total}.` : `. Step ${done}.`),
    metrics: `${run.kind} · ${clock(run.since)}`,
    stage: run.stage || null,
    progress: total ? { done, of: total } : null,
    tone: "live",
    actions: [
      {
        label: "Stop this run",
        primary: true,
        act: async (button) => {
          button.disabled = true;
          const stopped = await ask({ kind: "abort-run", runId: run.runId });
          // What is already inside the page finishes; this stops the next step,
          // which is what the button says. Where the backend could not be
          // told, this browser has still stopped taking part -- but the run
          // itself is still being driven, and saying "stopping" for that would
          // be the one thing a stop control must never do.
          button.textContent = stopped?.error
            ? `this browser has stopped — but the run could not be told: ${stopped.error}`
            : "stopping — the step already sent will finish";
          await refresh();
        },
      },
      { label: "Details in console", act: () => openConsole(`/runs/${run.runId}`) },
    ],
  });
}

/** What the last run made, and how to take it back.
 *
 * It asks nothing. "Did that come out right?" is a survey and surveys go
 * unanswered; an undo is a thing they wanted, so pressing it costs them
 * nothing to be honest about -- which is exactly what makes it the better
 * signal.
 *
 * Silence means it was fine. A run nobody touched is judged as it is today.
 *
 * Never claims more than the run's own record does. `derived` is read only
 * for a run that actually succeeded -- a run that failed partway through may
 * still have read something back before it did, and showing that as "Created
 * ..." would be the panel saying the write happened when the run's own status
 * says it did not. `run.reversal` is already null for anything but a
 * succeeded run (the backend never computes an undo for one -- see
 * `GET /runs/{id}` in `runs.py`), so nothing extra is needed to keep "Undo
 * that" off a failed run; this only has to get the *title* right.
 */
function finished(status) {
  const run = status.finished;
  const ok = run.status === "succeeded";
  const made = ok ? Object.entries(run.derived || {}) : [];
  const actions = [];
  const notes = [];
  if (ok && run.reversal) {
    actions.push({ label: "Undo that", primary: true, act: (button) => undoRun(button, run) });
    // What the press is about to delete, named before it is pressed.
    //
    // One press is the design and stays one press. But the reversal is a
    // DELETE skill whose steps and values are rendered nowhere -- this button
    // is the only place it ever appears -- and ADR 014's argument for a press
    // promoting a version is that the operator read what it would do. Nobody
    // could read this. `removes` is the delete step's own intent and
    // `parameters` are the identifiers the run read back, which together are
    // the whole of what the reversal will address; said on the card so it is
    // in front of the operator before the click rather than explained after
    // it. `||` because a finished-run row stored by an older worker has
    // neither field, and a card with no undo line is better than one saying
    // "undefined".
    const removes = run.reversal.removes || "Take back what this run made";
    const which = describeItem(run.reversal.parameters || {});
    notes.push(`“Undo that” will: ${removes}${which ? ` — ${which}` : ""}`);
  }
  // Once a run has been called wrong -- through this button or "Undo that"
  // above -- the backend refuses a second one outright (a run may be called
  // wrong only once), so a card that has already recorded one must not go on
  // offering a press guaranteed to fail.
  if (ok && !run.wrongBecause) {
    actions.push({ label: "It's wrong — I'll fix it", act: (button) => wasWrong(button, run) });
  }
  return card({
    title: ok
      ? made.length
        ? `Created ${made.map(([, value]) => value).join(" — ")}.`
        : "Finished. I can't show you what it made — nothing was read back."
      : "The last run failed.",
    says: ok ? null : run.failure || null,
    notes,
    actions,
  });
}

/** The two things "Undo that" means: the record that the operator asked for a
 * reversal, and the reversal itself. `run-wrong` first and awaited before the
 * reversal starts -- what counts against a skill is whether the operator
 * asked to take it back, and that has to land even where starting the
 * reversal in this browser goes on to fail (a tab that has since closed, say).
 *
 * Skipped when `run.wrongBecause` is already set -- this run has already been
 * called wrong once, whether by this button on an earlier press that failed
 * partway through, or by "It's wrong" below, and the backend refuses a second
 * one. What is retried here is only what could still be outstanding: starting
 * the reversal itself.
 *
 * `run.reversal.skill_id` and `.parameters` came back from the backend
 * already computed (`RunModel.reversal`, see the interfaces this task was
 * handed) -- nothing here decides what would undo a run, only that this is
 * the moment to run it.
 */
async function undoRun(button, run) {
  button.disabled = true;
  try {
    if (!run.wrongBecause) {
      // `keepForRetry` is what tells the worker this press, unlike "It's
      // wrong" below, still has a second step after the record lands --
      // starting the reversal, on this same line -- so the row must survive
      // to be retried if that fails. See `afterRunWrong` in `state.js`.
      await ask({
        kind: "run-wrong",
        runId: run.id,
        because: "undone by the operator",
        keepForRetry: true,
      });
    }
    // Pinned to the version `reversal_for` validated -- `skill.runnable`, the
    // one place "may this skill actually be asked to run" is answered. Without
    // it the press ran whatever version happened to be newest by the time it
    // landed, which is neither the version that was checked nor one anybody
    // was shown; the backend refuses that outright now rather than running it.
    await runIt(
      run.reversal.skill_id,
      run.reversal.parameters,
      "Undo that",
      run.reversal.version,
    );
    said("undoing it — a new run is reversing this one");
  } catch (error) {
    said(error.message);
  }
  await refresh();
}

/** No note is asked for here -- see this file's header and `finished()`'s own
 * comment above: this panel asks nothing, and a text box for "why" is the
 * same survey question in a different shape. Pressing this button already
 * says the one thing that matters: the run they got was not the one they
 * wanted.
 */
async function wasWrong(button, run) {
  button.disabled = true;
  try {
    await ask({ kind: "run-wrong", runId: run.id, because: "the operator said this was wrong" });
    said("Fix it the way you meant. I'm watching, and I'll learn from that.");
  } catch (error) {
    said(error.message);
  }
  await refresh();
}

/** A mail this browser recognised, and the one press that acts on it.
 *
 * Nothing runs unasked, so this card is the whole of what a watch does by
 * itself: it says what it found and waits. What a person needs in order to
 * decide is which task, what was read out of the mail as against what was
 * already on the task, and what recognised it.
 *
 * The rule, not the mail. The sender and the subject that decided this were
 * read in the frame and forgotten there -- and the operator can see the mail,
 * because this panel is docked beside it. What they cannot see is which of
 * their own terms caught it, so that is what is written here.
 *
 * Everything on this card was read in this browser and has been nowhere else.
 * The values went up once, to be told what the task would run with; nothing
 * was stored there and nothing is stored by pressing beyond the run's own
 * parameters, which is where a run's values have always lived.
 */
function offering(offer) {
  const named = offer.skill || offer.skillId;
  const read = offer.read || {};
  const missing = offer.missing || [];
  const because = (offer.terms || [])
    .map((term) => `${term.field} contains “${term.contains}”`)
    .join(" and ");
  return card({
    title: `A mail matched “${named}”`,
    says: because
      ? `Recognised in ${offer.host}: ${because}.`
      : `Recognised in ${offer.host}.`,
    // Which value came from the mail and which was already on the task. The
    // difference is the decision: one of them is what somebody just wrote to
    // this operator, and the other is what they set up themselves.
    notes: Object.entries(offer.values || {}).map(
      ([name, value]) =>
        `${name}: ${value} — ${name in read ? "read from the mail" : "already on the task"}`,
    ),
    metrics: `${clock(offer.at)} ago`,
    // Said before the press rather than after it. The same names the fire
    // itself would skip on, so a card that cannot run says so instead of
    // starting a run that stops a moment later where nobody is looking.
    stage: missing.length
      ? `Nothing said ${missing.join(", ")}, so this one cannot run.`
      : offer.skipped || null,
    tone: missing.length ? "attention" : null,
    actions: [
      {
        label: "Run it",
        primary: true,
        disabled: Boolean(missing.length),
        act: async (button) => {
          button.disabled = true;
          try {
            const fired = await ask({ kind: "watch-fire", offerId: offer.id });
            said(
              fired.run_id
                ? `started — “${named}” is running`
                : `nothing started: ${fired.skipped}`,
            );
          } catch (error) {
            said(error.message);
          }
          await refresh();
        },
      },
      {
        label: "Not now",
        act: async (button) => {
          button.disabled = true;
          await ask({ kind: "drop-offer", offerId: offer.id });
          said("dismissed — the mail is untouched and nothing ran");
          await refresh();
        },
      },
    ],
  });
}

/** Everything wrong at once, in the order somebody should deal with it.
 *
 * These were four grey sentences in four places, each of which said what was
 * true and none of which said what to do.
 */
function troubles(status) {
  const cards = [];
  if (status.deviceId && !status.capturing && !status.paused && !status.serverPaused) {
    cards.push(card({ title: "Not observing", says: `${status.because}.`, tone: "attention" }));
  }
  if (status.deviceId && status.channel !== "open") {
    cards.push(
      card({
        title: "This browser cannot be reached",
        says:
          `The command channel is ${status.channel}. A run started from the console or a `
          + "schedule cannot act here until it opens; nothing already captured is lost.",
        tone: "attention",
      }),
    );
  }
  if (status.lastError) {
    cards.push(card({ title: "Last error", says: status.lastError, tone: "attention" }));
  }
  return cards;
}

async function startTeaching(button) {
  button.disabled = true;
  try {
    const tab = await beside();
    if (!tab) throw new Error("open the system you want to teach in this tab first");
    // Named, not guessed: this panel is docked beside the tab being taught,
    // which is the one thing the options page could never say.
    await ask({ kind: "teach-start", tabId: tab.id, label: tab.title });
  } catch (error) {
    said(error.message);
  }
  await refresh();
}

async function stopTeaching(button, { discard = false } = {}) {
  button.disabled = true;
  try {
    const stopped = await ask({ kind: "teach-stop", discard });
    if (discard) {
      said("discarded — nothing was kept");
    } else {
      const steps = stopped.summary?.frame_count ?? 0;
      said(`saved — ${steps} step${steps === 1 ? "" : "s"}. Teach it once more to prove what varies.`);
    }
  } catch (error) {
    said(error.message);
  }
  await refresh();
  await here();
}

/** A sentence under the cards, for what just happened. */
function said(words) {
  $("candidates-note").textContent = words;
}

async function refresh() {
  const status = await ask({ kind: "status" });
  // What a run driving this browser actually is: the worker knows its id and
  // that it is happening, and the run's own record knows what it is called, how
  // far through it is and which rung it is allowed to be on.
  if (status.performing) {
    try {
      const run = await ask({ kind: "run", runId: status.performing.runId });
      const skill = await ask({ kind: "skill", skillId: run.skill_id });
      const version = (skill.versions || []).find((each) => each.version === run.skill_version);
      status.performing = {
        ...status.performing,
        skill: skill.name || null,
        stage: run.stage || null,
        step: Array.isArray(run.steps) ? run.steps.length : null,
        // How many steps the version has, which is what makes "step 3 of 6"
        // answerable. A looping skill performs more positions than it has
        // steps, so this is a floor rather than a promise -- and the card says
        // "step 3" without the total when they disagree.
        of: version?.steps?.length ?? null,
        because: run.requested_by ? `Started by ${run.requested_by}` : null,
      };
    } catch {
      // A run the panel cannot read is still a run the panel can stop.
    }
  }
  return render(status);
}

/** The system this panel is docked beside. */
/** The host the task list below was built for, so switching tabs rebuilds it.
 * Without this the list is whatever was in front when the panel opened, which
 * reads as "nothing noticed on this system" while the line above it names a
 * different system entirely. */
let showing = null;

/** The tab this panel is docked beside -- the one every card is about. */
let tabHere = { tabId: null, host: "", url: "" };

async function whereWeAre() {
  const tab = await beside();
  const host = hostOf(tab?.url || "");
  tabHere = { tabId: tab?.id ?? null, host, url: tab?.url || "" };
  $("where").textContent = host || "no system open in this window";
  if (host !== showing) {
    showing = host;
    await here();
    await refresh();
  }
}

function openConsole(path = "/console") {
  ask({ kind: "panel-console" }).then(({ consoleUrl }) => {
    if (consoleUrl) void chrome.tabs.create({ url: `${consoleUrl}${path}` });
  });
}

$("open-console").addEventListener("click", () => openConsole());

$("ask").addEventListener("click", () => {
  // The console's chat, framed here rather than in a tab: asking for a task is
  // the one console screen that belongs beside the work.
  const console_ = $("console");
  console_.hidden = !console_.hidden;
  $("ask").textContent = console_.hidden ? "Ask for a task" : "Hide the console";
  if (!console_.hidden && !$("frame").src) void frameTheConsole();
});

$("purge").addEventListener("click", async () => {
  // Two clicks, in the page rather than a modal: a dialog raised here blocks
  // the very worker being asked to do the deleting.
  if ($("purge").dataset.armed !== "1") {
    $("purge").dataset.armed = "1";
    $("purge").textContent = "Really delete the last hour?";
    setTimeout(() => {
      $("purge").dataset.armed = "";
      $("purge").textContent = "Delete the last hour";
    }, 5000);
    return;
  }
  $("purge").dataset.armed = "";
  $("purge").textContent = "Delete the last hour";
  try {
    const gone = await ask({ kind: "purge", hours: 1 });
    $("purged").textContent =
      `deleted ${gone.events} events in ${gone.batches} batches, ` +
      `and ${gone.artifacts ?? 0} screenshots`;
    await here();
  } catch (error) {
    $("purged").textContent = `nothing was deleted: ${error.message}`;
  }
});

$("options").addEventListener("click", (event) => {
  event.preventDefault();
  chrome.runtime.openOptionsPage();
});

// -- the conversation --------------------------------------------------------

/** The thread this panel is a client of, and what was last drawn in it.
 *
 * One continuous thread per operator, resolved by the server rather than
 * guessed at here: `GET /v1/threads/current` answers with the running one and
 * starts one when there is none, so there is exactly one place a thread is
 * made and the panel cannot invent a second conversation by racing itself.
 */
let threadId = null;
let drawn = null;

/** Fetch the thread and draw it. */
async function conversation() {
  let thread;
  try {
    thread = await ask({ kind: "thread" });
  } catch (error) {
    $("thread-note").textContent = error.message;
    return;
  }
  $("thread-note").textContent = "";
  threadId = thread.id;
  show(thread);
}

/** Draw a thread, if it says anything the one on screen does not.
 *
 * A redraw replaces the composer, which takes what somebody was half way
 * through typing with it -- so it happens only when the thread actually
 * changed, and never while a box on this panel has the cursor in it. Anything
 * said in the meantime appears the moment they stop typing.
 *
 * `asked` is that guard's one exception: the redraw the operator's own send
 * triggered. Sending with Enter leaves the cursor exactly where the guard
 * looks for it, so without this the box empties and nothing is painted in its
 * place -- the panel's main interaction, appearing not to work. A poll landing
 * on somebody mid-sentence is what the guard is for; their own press is not
 * that.
 */
function show(thread, { asked = false } = {}) {
  const now = `${thread.id}:${(thread.messages || []).map((message) => message.id).join(",")}`;
  if (now === drawn) return;
  if (!asked && drawn !== null && document.activeElement?.tagName === "INPUT") return;
  drawn = now;
  $("said").replaceChildren(transcript(thread, { onSay: say, onPress: answered }));
}

/** What the operator typed, said into the thread.
 *
 * The post answers with the whole thread, so this re-renders from the answer
 * rather than appending locally: what is on screen is what the server recorded,
 * not a guess at it that would show the message twice when the guess was right.
 */
async function say(text) {
  if (!threadId) return conversation();
  try {
    show(await ask({ kind: "thread-say", threadId, text }), { asked: true });
  } catch (error) {
    $("thread-note").textContent = error.message;
  }
}

/** An offer in the thread, answered.
 *
 * The message is a thing that was said; this press is the authorisation, and
 * it goes through the same call the candidate rows have always made -- so an
 * assisted run started from the conversation records the operator's press
 * exactly as one started from a row does. Nothing here runs because a message
 * asked for it.
 *
 * The decision is spread into the candidate rather than picked apart, because
 * the fields `beginOffer` reads beyond the id -- a model's title, a signature
 * -- are the backend's to add to an offer later, and a panel that copied three
 * named fields across would silently drop them.
 */
async function answered(answer, message, where, button) {
  const decision = message.decision || {};
  const candidate = { ...decision, id: decision.candidate_id };
  if (!candidate.id) return;
  button.disabled = true;
  if (answer === "do") return beginOffer(candidate, where, button);
  try {
    await ask({ kind: "dismiss-candidate", id: candidate.id, reason: "not worth automating" });
  } catch (error) {
    $("thread-note").textContent = error.message;
    button.disabled = false;
    return;
  }
  await conversation();
}

// -- tasks you keep doing here ----------------------------------------------

async function here() {
  const tab = await beside();
  const host = hostOf(tab?.url || "");
  if (!host) {
    $("candidates").replaceChildren();
    $("candidates-note").textContent = "open the system you work in to see its tasks";
    return;
  }

  let candidates;
  try {
    candidates = await ask({ kind: "candidates", host });
  } catch (error) {
    $("candidates-note").textContent = error.message;
    return;
  }

  // Only what is still a question. The endpoint answers with every status --
  // dismissed and taught included, because the miner reads them all so it does
  // not re-offer what somebody said no to -- and a panel that offered "Teach"
  // on a dismissed one would be offering a button the backend refuses.
  //
  // And not what the conversation is already carrying. A task worth offering
  // is said out loud in the thread, with the same two buttons; drawing it here
  // as well is the panel asking twice and then disagreeing with itself about
  // whether it was answered -- dismissing one left the other live. So this
  // list is what is building up and has not been offered yet, and the thread
  // owns every real offer.
  const offerable = candidates.filter(
    (candidate) => candidate.status === "new" && !candidate.offered_at,
  );

  $("candidates-note").textContent = offerable.length
    ? ""
    : `nothing new noticed on ${host} — it takes a few doings of the same task`;
  $("candidates").replaceChildren(...offerable.map(row));
}

/** The noun for this task, off the signature's own path.
 *
 * Used only where no model has named the task, so this never depends on one
 * being configured and a raw signature never reaches an operator. A numeric
 * or otherwise substituted segment (`workOperations/*`, an update-by-id call)
 * carries no word, so this walks back past it and any other empty segment
 * looking for one that actually is one; `null` says none was found, which is
 * true of some signatures and is a case the caller has to word around rather
 * than one this can paper over with a placeholder.
 */
function noun(candidate) {
  const path = (candidate.signature || "").split(" ")[1] || "";
  const word = path
    .split("/")
    .filter(Boolean)
    .reverse()
    .find((segment) => segment !== "*");
  if (!word) return null;
  // `workOperations` is two words to everybody except a URL. Left exactly as
  // the path spelled it -- plural or not -- so `counted` below is the one
  // place that decides which of those an operator actually reads.
  return word.replace(/([a-z0-9])([A-Z])/g, "$1 $2").toLowerCase();
}

/** `word` at `count`: singular at one, plural otherwise -- "operation" once,
 * "operations" any other time. Naive (`s`-only) on purpose: everything `noun`
 * hands this came off a REST path (`workOperations`, `receipts`, a
 * `shortShip`), and that is English's regular case throughout.
 */
function counted(word, count) {
  const plural = word.endsWith("s");
  if (count === 1) return plural ? word.slice(0, -1) : word;
  return plural ? word : `${word}s`;
}

/** The offer, in one sentence a warehouse operator would recognise as
 * ordinary English -- and a second thanking them for the offer's own
 * meaning: what they repeat, and that we will do the next one.
 *
 * A model writes a title -- a full sentence, conjugated as one -- where the
 * deployment has one and the propose pass has run; that can only be said back
 * as itself, never spliced into a noun's slot the way it was before ("You've
 * created 3 Adjust an LPN after a short ship here"). Where there is no title,
 * the noun taken from the signature's path *is* built to go in that slot, so
 * the two are two different sentences, not one template serving both.
 */
export function plainly(candidate) {
  const said = Math.round(candidate.median_duration_ms / 1000);
  // "1 times" is not a sentence, and a candidate sitting at `times_seen: 1`
  // is not theoretical -- the panel offers everything `status === "new"`
  // regardless of how many times it's been seen, and this is what a fresh
  // one looks like.
  const times = candidate.times_seen === 1 ? "once" : `${candidate.times_seen} times`;
  if (candidate.named_by_model && candidate.title) {
    return `${candidate.title} — you've done this ${times}, about ${said}s each. Want me to do the next one?`;
  }
  const what = noun(candidate);
  // No word survived the signature's path (every segment was `*` or blank).
  // Vaguer is better than visibly broken: "this" reads as ordinary English no
  // matter what the endpoint looked like, where a placeholder noun would not.
  if (!what) return `You've done this ${times} here — about ${said}s each.`;
  const count = candidate.times_seen === 1 ? "one" : candidate.times_seen;
  return `You've created ${count} ${counted(what, candidate.times_seen)} here — about ${said}s each.`;
}

function row(candidate) {
  const item = document.createElement("li");

  const said = document.createElement("p");
  said.className = "title";
  said.textContent = plainly(candidate);
  if (candidate.named_by_model && candidate.title) {
    // Said out loud: a sentence a model wrote is not a fact about the task.
    // Dropped by the round-1 rewrite of this row and caught by the browser
    // suite, not either unit-test gate -- `plainly()` says the title
    // verbatim under the same condition, and only the DOM this builds around
    // it can mark whose words they are.
    const mark = document.createElement("span");
    mark.className = "by-model";
    mark.textContent = " — named by a model";
    said.append(mark);
  }

  item.append(said);

  for (const join of candidate.joins || []) item.append(suggestion(candidate, join));

  const actions = document.createElement("div");
  actions.className = "row";

  const offer = document.createElement("button");
  offer.type = "button";
  offer.textContent = "Do the next one";
  offer.addEventListener("click", () => {
    offer.disabled = true;
    return beginOffer(candidate, item, offer);
  });

  const no = document.createElement("button");
  no.type = "button";
  no.className = "quiet";
  no.textContent = "No thanks";
  no.addEventListener("click", async () => {
    try {
      await ask({ kind: "dismiss-candidate", id: candidate.id, reason: "not worth automating" });
      await here();
    } catch (error) {
      // Said on the row rather than thrown into nothing: a click that does
      // nothing and explains nothing is how somebody decides the panel is
      // broken.
      said.textContent = error.message;
    }
  });

  actions.append(offer, no);
  item.append(actions);
  return item;
}

/** How much to show before running, and what still needs asking.
 *
 * Tied to the rung, not to the press. A preview on every press forever is the
 * thing that makes people stop reading previews -- and the ladder already says
 * when a version has earned the benefit of the doubt, on evidence rather than
 * on somebody's patience. This is not a preference: an operator cannot switch it
 * off, because it is the version that earned it and not them.
 *
 * `version` here is the flat shape this file builds in `preview()` below
 * (`{stage, clean_streak, starts_on}`), not the wire's `SkillVersionModel` --
 * the streak lives two levels down there, under `track_record`, and a function
 * that reached through that nesting itself would be a second place to keep in
 * step with the shape the API happens to use today.
 *
 * `startsOn` is handed back beside the steps because it is one of the three
 * things ADR 014's closed list says an operator reads before pressing: the
 * step intents, the resolved value of each parameter, and the tab the run will
 * act in. The run genuinely navigates there before it does anything, so a
 * preview that named the steps and not the screen was describing a different
 * run from the one about to happen -- and the residual-risk argument that
 * decision rests on depends on that list being exhaustive.
 */
export function previewOf(version, steps) {
  const missing = steps.filter((step) => step.missing).map((step) => step.label || step.missing);
  const show =
    version.stage === "autonomous"
      ? "nothing"
      : version.stage === "recorded" || !version.clean_streak
        ? "every-step"
        : "one-line";
  return { show, steps, missing, startsOn: version.starts_on || null };
}

/** The steps `previewOf` needs, from a skill version's own steps, what
 * `resolve-intent` said is still missing, and what it already read out of the
 * sentence for the rest.
 *
 * A step is a place data was typed only where a declared *input* parameter's
 * `source_step_index` names it -- `kind === "input"` is checked deliberately,
 * because a derived or iterated parameter also carries a `source_step_index`
 * and is never prompted for (see `ParameterKind` in the domain); matching on
 * the index alone once asked a step nobody types into for a value and sent
 * `""` under its name. "Press Save." matches no input parameter and carries
 * `value: null` forever, which is correct: it is a gesture, not a question.
 * A step that does match one keeps its parameter's name on it either way,
 * missing or not -- `renderReady` below decides what to *send* for it, but
 * losing the name here is how a value the sentence supplied stopped being
 * sendable at all.
 */
function preview(skillVersion, missingParameters, known = {}) {
  const steps = (skillVersion.steps || []).flatMap((step) => {
    // Every input parameter this step is the source of, not the first one.
    // `.find()` here meant a step that takes two typed values -- a code and a
    // quantity in the same dialog, say -- showed one of them and sent one of
    // them, and the other was never on the screen the operator read and never
    // in `parameters` at the press. A line each: the step's intent is repeated
    // beside each value, which reads a little redundantly and is the honest
    // shape, because what the operator has to check is the values.
    const found = (skillVersion.parameters || []).filter(
      (candidate) => candidate.kind === "input" && candidate.source_step_index === step.index,
    );
    if (!found.length) return [{ intent: step.intent, value: null }];
    return found.map((parameter) => {
    if (missingParameters.includes(parameter.name)) {
      return {
        intent: step.intent,
        value: null,
        name: parameter.name,
        missing: parameter.name,
        label: parameter.description || parameter.name,
      };
    }
    // Read out of the sentence, not invented: `known` is `resolution.items`,
    // the parser's own extraction, and a name absent from it (no parser
    // configured, or this one just was not said) is shown blank rather than
    // guessed at. Trimmed, and an empty result treated the same as absent --
    // a value the parser read as whitespace is not a value it read, and the
    // rule against sending a key with no value is the same rule whether the
    // gap is a missing name or one that resolved to "".
    return {
      intent: step.intent,
      value: (known[parameter.name] ?? "").trim() || null,
      name: parameter.name,
    };
    });
  });
  return previewOf(
    {
      stage: skillVersion.stage,
      clean_streak: skillVersion.track_record?.clean_streak ?? 0,
      starts_on: skillVersion.starts_on,
    },
    steps,
  );
}

/** The press. Promotes the version the preview just showed and starts it in
 * this browser -- `POST /skills/{id}/runs/from-preview`, never the ordinary
 * run endpoint, because that call does both at once and only this browser is
 * the one the operator watched the preview name. A looped skill is refused
 * here with a sentence written for an operator to read; it is returned to the
 * caller to show, not swallowed into a generic failure.
 *
 * `version` is not optional in practice, even though nothing here enforces it:
 * it is the version number the preview was actually drawn from, and the
 * backend runs exactly that one. If the skill has been taught again between
 * the preview and this press -- re-teaching, a drift repair, or either of the
 * console screens that reset a version for review -- the press is refused
 * with a sentence saying so rather than quietly running steps and values
 * nobody read. That refusal is ADR 014's central claim made true: what was on
 * the screen is what runs.
 */
async function runIt(skillId, parameters, intent, version) {
  // The device this browser is, read fresh rather than cached: it is the one
  // thing every run in this panel already asks for at the moment it presses,
  // not before, because a device id fixed earlier in the flow is one more
  // thing that could go stale while the operator was still typing.
  const { deviceId } = await ask({ kind: "status" });
  return ask({ kind: "run-skill", skillId, parameters, deviceId, intent, version });
}

/** One item's values, said plainly rather than dumped as a raw object --
 * "sku: A1, qty: 4" reads as English; `{"sku":"A1","qty":"4"}` reads as a
 * bug report. */
function describeItem(item) {
  return Object.entries(item)
    .map(([name, value]) => `${name}: ${value}`)
    .join(", ");
}

/** A note appended into `box`, ahead of whatever is about to draw there.
 * A helper only because `box` is cleared at the top of every render step
 * between here and the press (`renderPreview`, then `renderReady`), so
 * anything said before the preview has to be re-said by each of them rather
 * than appended once and lost the moment the next one clears its own box. */
function noteLine(box, text) {
  if (!text) return;
  const line = document.createElement("p");
  line.className = "note";
  line.textContent = text;
  box.append(line);
}

/** Fetches the version, builds its preview, and hands it to `renderPreview`
 * -- the one path both a straight match and a confirmed hedge take, so they
 * cannot drift into asking the press for different things.
 *
 * `items` is `resolution.items`: one parameter set per thing the sentence
 * named -- "these six SKUs" is six. Only the first is ever acted on here,
 * because nothing in this panel runs more than one thing per press; where
 * there was more than one, that is said before the preview rather than
 * silently discarded -- five things a person asked for going unmentioned is
 * worse than the panel admitting it can only start the first.
 */
async function startPreview(candidate, missingParameters, items, box, utterance) {
  const note =
    items && items.length > 1
      ? `This named ${items.length} things; only the first will run now` +
        ` (${describeItem(items[0])}). Ask again, one at a time, for the rest.`
      : null;
  await renderPreview(
    preview(await fetchVersion(candidate), missingParameters, (items && items[0]) || {}),
    candidate,
    box,
    utterance,
    note,
  );
}

/** What a sentence resolved to, drawn into `box`: one skill and its preview,
 * a hedge about the one it found, a question between a few, or nothing
 * taught at all.
 *
 * `resolve-intent` is never asked about one skill in particular -- see
 * `askBox` below for why -- so every one of these is a real outcome, not an
 * edge case. Two candidates too close to separate, and one candidate that
 * does not account for the whole sentence, are the same failure with
 * different shapes: a naive reading runs the best-scoring guess either way,
 * and that is a warehouse write on a coin toss. `ResolveIntent` already
 * refuses to guess and hands back a question in the operator's own words --
 * discarding that here, at the last surface before a live write, would spend
 * the one thing this whole branch is built on. So both ask, with a name on
 * the screen, and wait.
 */
async function renderResolution(resolution, box, utterance) {
  box.replaceChildren();

  if (resolution.matched && resolution.confident) {
    await startPreview(
      resolution.matched,
      resolution.missing_parameters || [],
      resolution.items,
      box,
      utterance,
    );
    return;
  }

  const said_ = document.createElement("p");
  said_.className = "note";

  if (resolution.matched) {
    // Exactly one skill scored best, but it does not account for the whole
    // sentence -- `resolve-intent` says so itself, in `question`, which is
    // rendered rather than recomposed: a second version of "did you mean X?"
    // written here is a second sentence to keep in step with resolve.py's.
    said_.textContent = resolution.question || `Did you mean “${resolution.matched.name}”?`;
    box.append(said_);
    const yes = document.createElement("button");
    yes.type = "button";
    yes.textContent = `Yes, ${resolution.matched.name}`;
    yes.addEventListener("click", async () => {
      yes.disabled = true;
      await startPreview(
        resolution.matched,
        resolution.missing_parameters || [],
        resolution.items,
        box,
        utterance,
      );
    });
    box.append(yes);
    return;
  }

  if (resolution.choices?.length) {
    said_.textContent =
      resolution.question ||
      `Which one did you mean: ${resolution.choices.map((choice) => choice.name).join(" or ")}?`;
    box.append(said_);
    for (const choice of resolution.choices) {
      const pick = document.createElement("button");
      pick.type = "button";
      pick.className = "quiet";
      pick.textContent = choice.name;
      pick.addEventListener("click", async () => {
        pick.disabled = true;
        // `resolve-intent` gives no missing-parameter list, and no extracted
        // values, for a choice that was not the match -- only for the one it
        // settled on. So a picked choice is previewed with nothing marked
        // missing and nothing known either, which is not the same thing as
        // previewing it with nothing required: every input parameter this
        // version declares is simply absent from `parameters` at the press
        // (see `renderReady` -- a value nobody supplied and the parser never
        // read is not sent as `""`), and `ensure_runnable` refuses it by name
        // if any of them was required. A second `resolve-intent` pinned to
        // this choice, asking what it still needs, is the fix if that
        // refusal is ever felt; nothing taught needs it yet.
        await startPreview(choice, [], null, box, utterance);
      });
      box.append(pick);
    }
    return;
  }

  said_.textContent = resolution.question || "Nothing taught matches that.";
  box.append(said_);
}

/** The skill version a candidate names, fetched fresh. Held nowhere between
 * asks: the panel already reads it this way to say what a run in progress is
 * doing (`refresh()`, above), and a second cache here is a second place it
 * could disagree with the skill's own record. */
async function fetchVersion(candidate) {
  const skill = await ask({ kind: "skill", skillId: candidate.skill_id });
  const found = (skill.versions || []).find((each) => each.version === candidate.version);
  return found || { stage: candidate.stage, steps: [], parameters: [], track_record: null };
}

/** What is still missing, asked for by the screen's own name -- never the
 * signature's -- and then the preview `built.show` actually calls for.
 *
 * An empty box is not an answer. A field left blank and continued through
 * would send `""` as the value, and `""` is a value: the run is not refused
 * for missing it, it is sent, and it writes an empty field into a warehouse
 * record. So a blank here is treated exactly like one never typed at all --
 * it stays asked for -- rather than accepted as a deliberate empty string.
 * Trimmed before that check, not after: three spaces is not a value either,
 * and typing them is not meaningfully different from typing nothing.
 */
async function renderPreview(built, candidate, box, utterance, note) {
  box.replaceChildren();
  noteLine(box, note);
  const need = built.steps.filter((step) => step.missing);
  if (need.length) {
    const fields = new Map();
    for (const step of need) {
      const line = document.createElement("label");
      line.textContent = `${step.label}: `;
      const field = document.createElement("input");
      field.type = "text";
      line.append(field);
      box.append(line);
      fields.set(step, field);
    }
    const warn = document.createElement("p");
    warn.className = "note";
    const go = document.createElement("button");
    go.type = "button";
    go.textContent = "Continue";
    go.addEventListener("click", async () => {
      const blank = [...fields].filter(([, field]) => !field.value.trim());
      if (blank.length) {
        warn.textContent = `${blank.map(([step]) => step.label).join(", ")} cannot be left blank.`;
        return;
      }
      for (const [step, field] of fields) step.value = field.value.trim();
      await renderReady(built, candidate, box, utterance, note);
    });
    box.append(warn, go);
    return;
  }
  await renderReady(built, candidate, box, utterance, note);
}

/** Every value is in hand. Now it is only `built.show` deciding what an
 * operator sees before the press -- every step and its value, one line, or
 * nothing at all -- never how many times they have pressed it before.
 *
 * "Nothing at all" means no step-by-step account, earned by a track record
 * good enough that reading one is not worth an operator's time -- it has
 * never meant the operator should not know which task just ran. A sentence
 * could once only mean the one task a row offered; now it is ranked across
 * everything taught, so which task a press just started is no longer implied
 * by which button was on the screen, and it is said here instead.
 *
 * A step with no known value is left out of `parameters` -- never sent as
 * `""`. `ensure_runnable` on the backend refuses a required parameter that
 * is genuinely absent ("no value supplied for X"); it does not, and must
 * not have to, refuse one that arrived as an empty string, because an empty
 * string is a value and this panel does not get to invent one just to fill
 * a slot. Every step still on `built.steps` with `.missing` set was already
 * required to be filled before this function is reached (`renderPreview`
 * refuses to advance on a blank field) -- so the only steps skipped here are
 * ones nothing ever supplied a value for, which is exactly the case the
 * backend's own refusal exists to catch honestly, on its own terms, rather
 * than never seeing the gap at all.
 */
async function renderReady(built, candidate, box, utterance, note) {
  box.replaceChildren();
  noteLine(box, note);
  const parameters = {};
  for (const step of built.steps) {
    const name = step.missing || step.name;
    if (name && step.value !== null && step.value !== undefined) parameters[name] = step.value;
  }

  // Two presses must not be two runs. There is no second guard once this
  // fires -- `box` is not cleared here the way it once was, because the line
  // naming which task is running has to survive whatever the press goes on
  // to say -- so the button disabling itself, and staying disabled, is the
  // only thing standing between one click and two warehouse writes.
  let pressed = false;
  const press = async () => {
    if (pressed) return;
    pressed = true;
    const said_ = document.createElement("p");
    said_.className = "note";
    box.append(said_);
    try {
      await runIt(candidate.skill_id, parameters, utterance, candidate.version);
      said_.textContent = "started";
    } catch (error) {
      // The button stays disabled after this and must: it is the only guard
      // against a second click turning one refused write into two attempts.
      // But a dead control with no explanation reads as a broken panel, not
      // a safe one, so the way back is said here -- type the sentence again,
      // which opens a fresh press with its own guard rather than reusing
      // this one.
      said_.textContent = `${error.message} — type the sentence again to try once more.`;
    }
  };

  if (built.show === "nothing") {
    // Named on its own line, kept rather than overwritten by whatever the
    // press turns out to say: a refusal is still a refusal of the task named
    // here, and an operator reading it needs both, not one replacing the
    // other.
    const named = document.createElement("p");
    named.className = "note";
    named.textContent = `Running “${candidate.name}”…`;
    box.append(named);
    await press();
    return;
  }

  if (built.show === "one-line") {
    const said_ = document.createElement("p");
    said_.textContent = `${candidate.name} — do it?`;
    box.append(said_);
    // The steps behind a disclosure, per the design's own table: a version
    // with a streak has earned the one-line ask, but "earned a shorter
    // question" is not "may no longer be asked what it is about to do".
    // Closed by default and one click from open, which is the difference
    // between not making somebody read it and not letting them.
    const more = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = "What it will do";
    more.append(summary);
    detail(more, built);
    box.append(more);
  } else {
    const said_ = document.createElement("p");
    said_.textContent = candidate.name;
    box.append(said_);
    detail(box, built);
  }

  const go = document.createElement("button");
  go.type = "button";
  go.textContent = "Do it";
  go.addEventListener("click", () => {
    go.disabled = true;
    return press();
  });
  box.append(go);
}

/** Every step and its value, and the tab the run opens before any of them.
 *
 * The whole of what ADR 014 says an operator reads before pressing, in one
 * place, so the full preview and the disclosure behind the one-line ask cannot
 * drift into showing different things. The screen goes first because it is
 * what the run does first -- `starts_on` is navigated to before step one, so a
 * preview that listed the steps and left it out described the same clicks
 * happening somewhere else entirely.
 */
function detail(box, built) {
  if (built.startsOn) {
    const where = document.createElement("p");
    where.className = "metrics";
    where.textContent = `In ${built.startsOn}`;
    box.append(where);
  }
  for (const step of built.steps) {
    const line = document.createElement("p");
    line.className = "metrics";
    line.textContent = step.value === null ? step.intent : `${step.intent} — ${step.value}`;
    box.append(line);
  }
}

/** The one input that turns a sentence into a run: opened here pre-filled
 * with a sentence naming the candidate that offered it, but never restricted
 * to that candidate once opened.
 *
 * `resolve-intent` carries no field to pin it to one skill -- there is
 * nothing to send -- and that absence is deliberate rather than a gap this
 * file works around: a sentence typed in here that names some other taught
 * task is answered about that task, exactly as if it had been typed into a
 * blank box, because the offer that opened this one was a suggestion for
 * what to type, not a restriction on what can be asked.
 */
function askBox(holder, prefill) {
  const row_ = document.createElement("div");
  row_.className = "row";
  const input = document.createElement("input");
  input.type = "text";
  input.value = prefill;
  const go = document.createElement("button");
  go.type = "button";
  go.textContent = "Ask";
  row_.append(input, go);

  const said_ = document.createElement("p");
  said_.className = "note";
  const box = document.createElement("div");

  go.addEventListener("click", async () => {
    go.disabled = true;
    said_.textContent = "";
    try {
      const resolution = await ask({ kind: "resolve-intent", utterance: input.value });
      await renderResolution(resolution, box, input.value);
    } catch (error) {
      said_.textContent = error.message;
    }
    go.disabled = false;
  });

  holder.append(row_, said_, box);
}

/** The sentence the box in `beginOffer` opens with -- a suggestion for what
 * to type, never a restriction on it (see `askBox`).
 *
 * A model's own title is a full sentence and is used as one; failing that,
 * the noun `plainly()` already reads off the candidate's signature makes an
 * ordinary instruction ("Do the next work operation"). Where neither exists
 * this is left blank rather than filled with words about the button that
 * opened it -- "Do the next one" names no task, and typing nothing into the
 * box is a truer starting point than typing a sentence that ranks nothing
 * because it asks for nothing.
 */
function suggestedSentence(candidate) {
  if (candidate.named_by_model && candidate.title) return candidate.title;
  const what = noun(candidate);
  return what ? `Do the next ${counted(what, 1)}` : "";
}

/** Starts the offer this row just made: doing the operator's next occurrence
 * of the task.
 *
 * Teaches the candidate first -- silently, because the operator asked for a
 * task done, not a lesson on how the system learns tasks -- then opens the
 * same box every sentence goes through. A refusal here is not an error to
 * report and move past: passive capture cannot always induce a task from
 * what it saw, and the honest answer is to say so and ask for one more
 * ordinary doing of it, which is what the sentence below says.
 */
async function beginOffer(candidate, item, offerButton) {
  const note = document.createElement("p");
  note.className = "note";
  note.textContent = "one moment…";
  item.append(note);

  let taught;
  try {
    taught = await ask({ kind: "teach-candidate", id: candidate.id });
  } catch (error) {
    note.textContent = error.message;
    if (offerButton) offerButton.disabled = false;
    return;
  }

  if (taught.needs_demonstration) {
    // `taught.because` is `str(InductionFailed)` -- a recording id, an
    // objective-key slug, a JSON pointer diffing two demonstrations. None of
    // that is written for an operator to read, so the sentence here is fixed
    // rather than passed through; `taught.because` stays in the console's own
    // review screen, where a person who wants the raw reason already is one.
    note.textContent =
      "I've watched this a few times but the doings differ too much for me to be sure" +
      " — do one more and I'll try again.";
    if (offerButton) offerButton.disabled = false;
    return;
  }

  // Cleared rather than removed: `card()` and the rest of this file never
  // reach for a node's own `.remove()`, because nothing here tracks a node's
  // parent to make it meaningful, and reaching for it once here would be a
  // second way to take a node out of the page for no reason worth a second
  // way.
  note.textContent = "";
  askBox(item, suggestedSentence(candidate));
}

/** What a model noticed about this candidate, and the two words a person can
 * answer it with.
 *
 * The answer is the point. A suggestion nobody can answer accumulates on a
 * screen until the screen is ignored, and every sweep re-asks it -- so until
 * somebody says, it is a question, and once they have, it is a fact with their
 * name on it and the miner stops asking.
 */
function suggestion(candidate, join) {
  const holder = document.createElement("div");
  holder.className = "joined";

  const said_ = document.createElement("p");
  said_.className = "note";
  const what =
    join.kind === "workflow"
      ? "looks like half of one job with another task"
      : "looks like the same task as another";
  said_.textContent = join.answered
    ? `${join.answered === "same" ? "one job with another task" : "a different task"} — ` +
      `${join.answered_by} said so`
    : `${what} — ${join.because}`;
  holder.append(said_);

  const actions = document.createElement("div");
  actions.className = "row";

  if (join.answered) {
    // The only answer anything can act on. `same` about a workflow means the
    // two are one job done in two systems -- which no single candidate can
    // represent, so until this button existed the answer changed nothing.
    if (join.kind === "workflow" && join.answered === "same") {
      const merge = document.createElement("button");
      merge.type = "button";
      merge.textContent = "Teach as one";
      merge.addEventListener("click", async () => {
        merge.disabled = true;
        try {
          const answer = await ask({
            kind: "teach-together",
            id: candidate.id,
            otherId: join.other_id,
          });
          said_.textContent = answer.needs_demonstration
            ? answer.because || "the evidence for the two halves was too thin"
            : "learned as one skill";
          await here();
        } catch (error) {
          said_.textContent = error.message;
          merge.disabled = false;
        }
      });
      actions.append(merge);
      holder.append(actions);
    }
    return holder;
  }

  for (const [label, answer] of [
    ["Same task", "same"],
    ["Different", "different"],
  ]) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "quiet";
    button.textContent = label;
    button.addEventListener("click", async () => {
      try {
        await ask({
          kind: "answer-join",
          id: candidate.id,
          otherId: join.other_id,
          // `kind` is taken by the message itself, and a join has one too.
          joinKind: join.kind,
          answer,
        });
        await here();
      } catch (error) {
        said_.textContent = error.message;
      }
    });
    actions.append(button);
  }
  holder.append(actions);
  return holder;
}

// -- the console -------------------------------------------------------------

async function frameTheConsole() {
  const { consoleUrl, token } = await ask({ kind: "panel-console" });
  if (!token || !consoleUrl) {
    // Already said once, at the top, with the button that fixes it. Saying it
    // again down here would be a second complaint about one thing.
    $("console").hidden = true;
    return;
  }

  const origin = new URL(consoleUrl).origin;
  const frame = $("frame");

  // The console announces itself once its listener exists. Posting on `load`
  // instead would race its hydration and lose the credential intermittently,
  // which is the worst way for a handshake to fail.
  window.addEventListener("message", (event) => {
    if (event.origin !== origin) return;
    if (event.data?.kind === "sro.ready") {
      // Addressed to the console's own origin, never "*": a wildcard hands the
      // credential to whatever the frame has navigated to.
      frame.contentWindow?.postMessage({ kind: "sro.credential", token }, origin);
      return;
    }
    if (event.data?.kind === "sro.credential.ok") $("console-note").textContent = "";
  });

  $("console-note").textContent = "opening the console…";
  frame.src = `${consoleUrl}/console?embedded=1`;
  frame.hidden = false;

  // A cross-origin frame does not report its own failures, so the reply is the
  // only health check there is -- and until it arrives the frame is a grey
  // rectangle that looks like a broken page. Show what to do instead of it, and
  // keep showing it: a setup step nobody is told about twice is a setup step
  // nobody does.
  setTimeout(() => {
    if ($("console-note").textContent === "opening the console…") {
      frame.hidden = true;
      refused(consoleUrl);
    }
  }, 5000);
}

/** What to do when the console will not accept this browser.
 *
 * The console decides which extension may frame it and hand it a credential --
 * a deployment that accepted any extension would accept one somebody else
 * installed. So this is a line of configuration, and the panel is where
 * somebody finds out it is missing. It says which line, where, and hands it
 * over ready to paste.
 */
function refused(consoleUrl) {
  const holder = $("console-refused");
  holder.hidden = false;
  holder.replaceChildren();

  const origin = `chrome-extension://${chrome.runtime.id}`;
  const said_ = document.createElement("p");
  said_.className = "note";
  said_.textContent = `${consoleUrl} did not accept this browser. It only frames extensions it has been told about.`;

  const what = document.createElement("code");
  what.className = "fix";
  what.textContent = `NEXT_PUBLIC_EXTENSION_ORIGINS=${origin}`;

  const where = document.createElement("p");
  where.className = "note";
  where.textContent = "Put that in the console's environment (frontend/.env.local) and restart it.";

  const copy = document.createElement("button");
  copy.type = "button";
  copy.textContent = "Copy the line";
  copy.addEventListener("click", async () => {
    await navigator.clipboard.writeText(what.textContent);
    copy.textContent = "copied";
    setTimeout(() => (copy.textContent = "Copy the line"), 2000);
  });

  const again = document.createElement("button");
  again.type = "button";
  again.className = "quiet";
  again.textContent = "Try again";
  again.addEventListener("click", () => {
    holder.hidden = true;
    $("console-note").textContent = "";
    void frameTheConsole();
  });

  const row_ = document.createElement("div");
  row_.className = "row";
  row_.append(copy, again);
  holder.append(said_, what, where, row_);
  $("console-note").textContent = "";
}

// ponytail: polled while the panel is open rather than pushed from the worker.
// A few storage reads a second is cheap and has no lifecycle edge cases; make
// it a broadcast if it is ever felt.
setInterval(() => {
  if (document.visibilityState !== "visible") return;
  void refresh();
  void whereWeAre();
}, 2000);

// ponytail: the thread is polled too, on its own slower tick -- it is a call to
// the API rather than a read of the worker's own state, and nothing in a
// conversation arrives fast enough to be worth the two-second one. Make it a
// push from the worker if an offer ever needs to land sooner than this.
setInterval(() => {
  if (document.visibilityState !== "visible") return;
  void conversation();
}, 5000);

void refresh();
void whereWeAre();
void conversation();
