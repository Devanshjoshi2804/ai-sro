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
import { alreadyAnswered, composer, ledger, nudging } from "./ledger.js";
import { runCard } from "./run-card.js";
import { needsAPress, strip } from "./strip.js";
import { panes } from "./panes.js";
import { today } from "./today.js";
import { waiting } from "./waiting.js";

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

  // The strip first: who this is, which tab it is beside, and what is happening
  // to it -- as one line. What used to be a card headed "Not watching this tab"
  // on every tab an operator switched to.
  $("strip").replaceChildren(
    strip(status, tabHere, { onMenu: menu, onToggle: toggleExpanded }),
  );
  const why = needsAPress(status, tabHere);
  // Open when there is something only the operator can fix, or when they asked
  // for it. Everything else is a fact a line states and a card would nag about.
  $("expanded").hidden = !(why || expanded);

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

  // The jobs this browser is offering to do, HERE rather than in the
  // conversation.
  //
  // They were drawn in the thread, interleaved with what was said, which was
  // right when the panel was one column and wrong the moment it became two:
  // Home is what is true right now and an offer is the truest thing on it, so
  // splitting the panel left Home empty and put the card a person was waiting
  // to press behind the other tab. Seen on the deployment 2026-09-16 --
  // "Create a Customer Type — GDY, so far" sitting in Chat with nothing at all
  // on Home.
  //
  // Not the ones that are waiting: those are in the banner above, and a card
  // drawn twice is a card somebody answers twice. Not another tab's, either --
  // an offer about a page nobody is looking at is words without buttons.
  if (!status.teaching) {
    for (const nudge of lastStatus?.nudges || status.nudges || []) {
      if (nudge.state !== "open" || nudge.missed) continue;
      if (nudge.tabId != null && nudge.tabId !== tabHere.tabId) continue;
      cards.push(nudging(nudge, answered));
    }
  }

  if (status.performing) cards.push(performing(status));
  // Not while teaching, same rule as the offers above: a demonstration in
  // progress is the only thing the panel is about. Placed after the run that
  // is happening now and before what is wrong, because it outranks neither --
  // it is a look back at the last thing this browser did, not a fault.
  if (!status.teaching && status.finished) cards.push(finished(status));
  for (const trouble of troubles(status)) cards.push(trouble);

  // The first card is the state of this tab, which is what the strip's chevron
  // opens onto. The rest -- a run, what it made, what is wrong -- stay where
  // they are, above the day.
  const [state, ...rest] = cards;
  // Never while somebody is typing a password into one of these cards.
  //
  // This redraw runs on the two-second poll and replaces every card with a
  // freshly built one, which takes the box with it: an operator typing their
  // password into the card that asked for it watched it empty itself every
  // two seconds. The thread has held this rule since the composer was built
  // -- a redraw that lands on somebody mid-sentence throws away what they
  // typed -- and the cards column had no equivalent because nothing in it was
  // ever typed into.
  //
  // Narrow on purpose: only a password box, because that is the one control
  // here whose value cannot be recovered from anywhere (a parameter field is
  // redrawn from `run.parameters`, which the worker holds). Everything else
  // keeps updating, and the moment they press Save or click away the next
  // poll draws normally.
  if (document.activeElement?.type !== "password") {
    $("expanded").replaceChildren(state);
    $("cards").replaceChildren(...rest);
  }

  // While a demonstration is being recorded the panel is about that and
  // nothing else, and none of it applies to a browser that is not connected.
  $("here").hidden = Boolean(status.teaching) || !status.deviceId;
  $("thread").hidden = Boolean(status.teaching) || !status.deviceId;
  lastStatus = status;
  paintPanes();
  // What arrived while nobody was looking, above everything. Painted from the
  // worker's status rather than from the thread, because that is what it is
  // about -- a request waiting is a fact about this browser, not a line in a
  // conversation -- and after `lastStatus` is set, which is what it reads.
  paintWaiting();
  return status;
}

/** What the profile menu's items mean here.
 *
 * The strip decides nothing itself: it hands back a word about the deployment,
 * and this is where each becomes a call. Every one of them existed already --
 * what changed is that they are no longer in the eye line of the composer.
 */
async function menu(action) {
  switch (action) {
    case "console":
      return openConsole();
    case "frame-console": {
      // The console inside the panel, which is where a supervisor's screens are
      // reachable without leaving the tab the work is in. Toggled, because the
      // way back is the same press.
      const framed = $("console");
      framed.hidden = !framed.hidden;
      if (!framed.hidden && !$("frame").src) void frameTheConsole();
      return undefined;
    }
    case "pause":
    case "resume":
      await ask({ kind: "set-paused", paused: action === "pause" });
      return refresh();
    case "purge":
      return purge();
    case "never":
      await ask({ kind: "unwatch-tab", tabId: tabHere.tabId, url: tabHere.url });
      return refresh();
    case "settings":
      return chrome.runtime.openOptionsPage();
    case "disconnect":
      await ask({ kind: "sign-out" });
      return refresh();
    default:
      return undefined;
  }
}

function toggleExpanded() {
  expanded = !expanded;
  if (lastStatus) render(lastStatus);
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
  // Always the whole card. Collapsing is the strip's job now and only the
  // strip's: this used to keep a second copy of "is it open" beside the one in
  // `render`, which meant two chevrons could disagree about the same tab and
  // the line one of them drew said something the other did not.
  void status;
  void needsAnswer;
  void mine;
  return card(built);
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

/** How long a nudge that ended stays on screen.
 *
 * Four seconds: long enough that an offer disappearing reads as the offer
 * ending rather than the panel dropping it, short enough that a day of them
 * never becomes the wall of unpressable history an operator found themselves
 * scrolling past on a page none of it was about. */
const JUST_ENDED_MS = 4_000;

/** A run driving this browser, possibly started somewhere else.
 *
 * Stoppable from here because this is where somebody sees it happening: a run
 * started by a schedule is otherwise a cursor moving on its own.
 */
function performing(status) {
  const run = status.performing;
  const done = Number.isFinite(run.step) ? run.step : null;
  const total = run.of && done !== null && done <= run.of ? run.of : null;
  const holder = card({
    title: run.skill ? `“${run.skill}” is running` : "A run is performing here",
    // What it is doing beats which step it is on, when it says anything.
    //
    // A run reading a mailbox for the values nobody typed has not reached its
    // first step yet, so "Step 0" is true and useless -- and on the deployment
    // 2026-09-16 it sat there for three and a half minutes while the model
    // retried a 5xx, which reads exactly like a run that has hung. Everything
    // a run does is a step except this one thing, so this one thing says so.
    says: run.doing
      ? `${run.doing}…`
      : (run.because || "Started elsewhere") +
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
      // Where the run actually is. Two routes because there are two id
      // spaces: `/jobs/runs/{id}` reads a workflow-run id (`source: "rig"`,
      // the name the channel gave it) and `/runs/{id}` a skill-run id. The
      // backend keeps them apart on purpose, so a workflow-run id sent to
      // `/runs/` is not a type error -- it is looked up in the skill-run
      // repository, found missing, and drawn as a run that does not exist.
      {
        label: "Details in console",
        act: () =>
          openConsole(run.source === "rig" ? `/jobs/runs/${run.runId}` : `/runs/${run.runId}`),
      },
    ],
  });

  // The run itself, while it is happening: a row per step as the rig judges
  // it, and on the step it has stopped to ask about, the two answers. Only the
  // rig's runs carry this -- a backend run is stepped from the server and this
  // card has only ever said which step it is on. `run.id` rather than
  // `run.runId`: this is the rig's own record, in the same shape `finished`
  // draws a rig run that has ended.
  if (run.run) {
    holder.append(
      runCard(
        { run: run.run },
        {
          // The performing card above already carries "Stop this run".
          stop: false,
          onPress: async (answer, drawn, row, button) => {
            button.disabled = true;
            if (answer === "approve") {
              // The panel never holds the rig's bearer. The press goes to the
              // worker, which is where it lives -- the same path the offer's
              // "yes" takes.
              const got = await ask({ kind: "approve-rig-run", runId: drawn.id });
              if (got?.error) said(got.error);
              // Said, because the row cannot say it yet. The backend stops
              // marking the step `awaiting` as soon as the tap lands, but the
              // write goes out in the same breath and this poll can beat the
              // save -- so without a word here the panel redraws the same
              // paused row with the same button and the tap looks lost. It
              // was: "I clicked approve but nothing happened", on a run whose
              // approval had landed every time.
              else said("approved — sending the write");
            } else if (answer === "stop") {
              await ask({ kind: "abort-run", runId: drawn.id });
            }
            await refresh();
          },
          onSecret: keepSecret,
        },
      ),
    );
  }
  return holder;
}

/** One password, on its way to the vault and gone.
 *
 * The panel is the only screen the person who knows it is looking at, and it
 * is the one place that must not keep it: this reads the field, hands it to
 * the worker, and returns what the worker said. Nothing is stored on this
 * side -- not in `chrome.storage`, not in a variable that outlives the call.
 */
async function keepSecret({ system, field, value }) {
  // Caught rather than thrown on: `ask` turns a worker's `error` into an
  // exception, and an exception inside the Save listener would leave the
  // person who just typed their password looking at a row that said nothing.
  try {
    const kept = await ask({ kind: "keep-secret", system, field, value });
    // Said under the cards as well as on the row. The row's own line is drawn
    // inside a card the next poll rebuilds -- the guard above only holds it
    // while the box has the cursor -- so an operator who presses Save and
    // looks away would otherwise have nothing left saying it worked.
    if (kept?.ok) said("password kept — press Yes again and it will sign in");
    return kept;
  } catch (error) {
    return { ok: false, error: error.message };
  }
}

/** What the rig's own outcomes are, said in a sentence. Its vocabulary is not
 * the backend's -- there is no "succeeded", because the rig judges each step's
 * reading and a run is what those add up to. See `OUTCOMES` in `rig/runs.py`.
 */
const RIG_ENDINGS = {
  held: "The run finished — every step held.",
  stopped: "The run stopped to ask.",
  refused: "The run was refused.",
  aborted: "The run was stopped.",
  failed: "The run failed.",
};

/** One item's values, in a sentence: `name: value, name: value`.
 *
 * All that survives of the sentence-to-skill box, which went with the mining
 * offers that opened it. The undo line still needs it: what a reversal is
 * about to delete has to be readable before the press, and this is the only
 * place those identifiers appear.
 */
function describeItem(item) {
  return Object.entries(item)
    .map(([name, value]) => `${name}: ${value}`)
    .join(", ");
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
  // A run the rig drove: its steps are its own record, and it has neither a
  // reversal nor anywhere to send "It's wrong" -- so the card offers neither,
  // rather than offering both and failing on the press. `runCard` is the same
  // card a backend run is drawn in; what changes is which list it draws and
  // which buttons it puts under it.
  if (run.source === "rig") {
    return runCard(
      { run, skill: null, message: { text: RIG_ENDINGS[run.status] || "The run ended." } },
      { onSecret: keepSecret },
    );
  }
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
    stage: !missing.length
      ? offer.skipped || null
      : offer.canFind
        ? `Nothing said ${missing.join(", ")} — I read those out of the mail when it runs.`
        : `Nothing said ${missing.join(", ")}, so this one cannot run.`,
    tone: missing.length && !offer.canFind ? "attention" : null,
    actions: [
      {
        label: "Run it",
        primary: true,
        disabled: Boolean(missing.length) && !offer.canFind,
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
          (status.channelWhy
            ? `Not dialling: ${status.channelWhy}. `
            : `The command channel is ${status.channel}. `)
          + "A run started from the console or a schedule cannot act here until it "
          + "opens; nothing already captured is lost.",
        tone: "attention",
        // It redials on the minute alarm by itself. This is for the operator
        // watching the card right now, who otherwise has nothing to press and
        // goes looking for a switch to flip in the options page.
        actions: [{ label: "Try again", act: reconnect }],
      }),
    );
  }
  if (status.lastError) {
    cards.push(
      card({
        title: "Last error",
        says: status.lastError,
        tone: "attention",
        // Dismissable, because this is the LAST error and not a current one:
        // it survives whatever fixed it, and an operator with no way to clear
        // it learns to read past the amber.
        actions: [{ label: "Dismiss", act: dismissError }],
      }),
    );
  }
  return cards;
}

async function reconnect(button) {
  button.disabled = true;
  try {
    await ask({ kind: "reconnect" });
    said("dialling — this can take a few seconds");
  } catch (error) {
    said(error.message);
  }
  await refresh();
}

async function dismissError(button) {
  button.disabled = true;
  try {
    await ask({ kind: "clear-error" });
  } catch (error) {
    said(error.message);
  }
  await refresh();
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
}

/** A sentence under the cards, for what just happened.
 *
 * `#candidates-note` by name still, which is a leftover: it was the foot of
 * the candidate list, and when that list went with the rest of the older
 * pipeline's offers this line stayed, because a line saying what just
 * happened is worth having wherever it sits.
 */
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
      // The door that holds this kind of run. A mined job's run lives at
      // `/v1/workflow-runs` and a skill's at `/v1/runs`, and asking the second
      // about the first is a 404 every time -- which is what the card showing
      // "A run is performing here" and no job name was, all evening, on every
      // run this browser drove.
      const rig = status.performing.source === "rig";
      const run = await ask({
        kind: "run",
        runId: status.performing.runId,
        source: status.performing.source,
      });
      status.performing = rig
        ? {
            ...status.performing,
            // The rig plans one step at a time, so there is no total to count
            // towards and the card says "step 3" rather than "step 3 of 7".
            // `rigRun` maps the row; `steps` is what it has done so far.
            skill: null,
            step: Array.isArray(run.steps) ? run.steps.length : null,
            of: null,
            because: null,
          }
        : await _aboutTheSkill(status.performing, run);
    } catch {
      // A run the panel cannot read is still a run the panel can stop.
    }
  }
  void sayTheDay(status);
  return render(status);
}

/** What a SKILL run is, as the performing card draws it: the skill's name, the
 * rung it is allowed to be on, and how many steps its version has.
 *
 * Only for a skill run. A mined job's run has no version to count towards --
 * the rig plans one step at a time -- so asking these questions about one is
 * asking a door that does not hold it.
 */
async function _aboutTheSkill(performing, run) {
  const skill = await ask({ kind: "skill", skillId: run.skill_id });
  const version = (skill.versions || []).find((each) => each.version === run.skill_version);
  return {
    ...performing,
    skill: skill.name || null,
    stage: run.stage || null,
    step: Array.isArray(run.steps) ? run.steps.length : null,
    // How many steps the version has, which is what makes "step 3 of 6"
    // answerable. A looping skill performs more positions than it has steps,
    // so this is a floor rather than a promise -- and the card says "step 3"
    // without the total when they disagree.
    of: version?.steps?.length ?? null,
    because: run.requested_by ? `Started by ${run.requested_by}` : null,
  };
}

/** The three numbers over the ledger, fetched beside the redraw rather than in
 * it: a slow analytics answer must not hold up the state of the tab, which is
 * the part somebody is waiting on.
 */
async function sayTheDay(status) {
  if (!status.deviceId) return $("today").replaceChildren();
  try {
    const midnight = new Date();
    midnight.setHours(0, 0, 0, 0);
    const summary = await ask({ kind: "summary", since: midnight.toISOString() });
    const line = today(summary, openOffers);
    $("today").replaceChildren(...(line ? [line] : []));
  } catch {
    // Offline, or an older backend. A day nobody can count is a day this line
    // says nothing about, which is better than a wrong number.
    $("today").replaceChildren();
  }
}

/** The system this panel is docked beside. */
/** The host the task list below was built for, so switching tabs rebuilds it.
 * Without this the list is whatever was in front when the panel opened, which
 * reads as "nothing noticed on this system" while the line above it names a
 * different system entirely. */
/** The tab this panel is docked beside -- the one every card is about. */
let tabHere = { tabId: null, host: "", url: "" };

/** Whether the operator opened the state card themselves, and the last status
 * drawn -- so opening it does not have to wait for the next poll. */
let expanded = false;
let lastStatus = null;

/** Offers in the thread nobody has answered, counted where the thread is drawn
 * so the day's line does not fetch it a second time. */
let openOffers = 0;

async function whereWeAre() {
  const tab = await beside();
  const was = tabHere;
  tabHere = { tabId: tab?.id ?? null, host: hostOf(tab?.url || ""), url: tab?.url || "" };
  // The tab's id and not its host alone. Whether this tab is being watched is
  // answered by looking for `tabHere.tabId` in the watch list, so two tabs on
  // one warehouse are two different answers -- and a host comparison left the
  // panel saying "Watching this tab" beside a second tab nothing was
  // recording.
  if (tabHere.host !== was.host || tabHere.tabId !== was.tabId) await refresh();
}

function openConsole(path = "/console") {
  ask({ kind: "panel-console" }).then(({ consoleUrl }) => {
    if (consoleUrl) {
      void chrome.tabs.create({ url: `${consoleUrl}${path}` });
      return;
    }
    // `consoleUrl` is empty until somebody sets it, and this used to be a
    // silent no-op: the operator pressed "Open the console here", nothing
    // happened, nothing said why, and the only way to find out was to read
    // this function. Say it and open the page that fixes it.
    said("no console address is set — put one in Settings");
    chrome.runtime.openOptionsPage();
  });
}


/** Deleting the operator's own last hour.
 *
 * Reached from the profile menu rather than a button under the composer: an
 * escape hatch is what makes always-on observation defensible, and it is not a
 * thing pressed daily.
 *
 * Confirmed by saying what went rather than by asking first. A dialog raised
 * here would block the very worker being asked to do the deleting, and the
 * menu item is already two presses from anything.
 */
async function purge() {
  try {
    const gone = await ask({ kind: "purge", hours: 1 });
    $("purged").textContent =
      `deleted ${gone.events} events in ${gone.batches} batches, ` +
      `and ${gone.artifacts ?? 0} screenshots`;
  } catch (error) {
    $("purged").textContent = `nothing was deleted: ${error.message}`;
  }
}

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
/** Which half of the panel is showing, in THIS window of it.
 *
 * Home, because somebody opening this panel is looking for what the system is
 * doing or wants from them, which is a glance. A conversation is something you
 * go to. Not stored, for the waiting banner's reason: it is a fact about a
 * person looking at a panel right now.
 */
let pane = "home";

/** What the tabs were last drawn from, so an unchanged pair is left alone. */
let panesDrawn = null;

/** Draw the two tabs and hide whichever half is not showing.
 *
 * Its own painter, called from `render` and from the tabs themselves, because
 * switching pane changes nothing `show()`'s signature can see.
 */
function paintPanes() {
  const missed = (lastStatus?.nudges || []).filter(
    (one) => one.state === "open" && one.missed,
  ).length;
  // Only when it would say something different. This runs on every push from
  // the worker -- a status lands every couple of seconds -- and rebuilding two
  // buttons that often is how a control comes to flicker under the cursor
  // that is about to press it.
  const now = `${pane}:${missed}`;
  if (now === panesDrawn) {
    // The tabs are what is unchanged. Which half is on screen is asserted
    // every time: it is one property write per element, and an early return
    // that skipped it would leave a pane hidden after anything else touched it.
    showPane();
    return;
  }
  panesDrawn = now;
  $("panes").replaceChildren(
    panes(pane, {
      waiting: missed,
      onPick: (picked) => {
        if (picked === pane) return;
        pane = picked;
        paintPanes();
        // Read it now rather than up to five seconds from now: the poll below
        // runs only while Chat is showing, so arriving on it is exactly when
        // the thread is most likely to be stale.
        if (pane === "chat") {
          void conversation();
          // Their own press, so the view is theirs to move: arriving on the
          // conversation means arriving at the end of it.
          toTheNewest(true);
        }
      },
    }),
  );
  showPane();
}

/** How close to the bottom still counts as reading the newest.
 *
 * A few pixels of slack rather than zero: a thread that has just grown by a
 * line is a thread somebody is still at the bottom of, and an exact comparison
 * makes every redraw a coin toss between sticking and not. */
const K_AT_THE_BOTTOM = 48;

/** Keep the newest thing in sight, the way a conversation is read.
 *
 * Nothing in this panel has ever scrolled, so arriving on Chat showed the
 * OLDEST message with the newest below the fold, and every redraw left it
 * there. That is most of what "it is not smooth" means: the thing you came to
 * read is the one place the panel does not put you.
 *
 * It sticks rather than jumps. Somebody who has scrolled up is reading
 * something, and a view that yanks itself down while they read is worse than
 * one that never moved -- so this only acts when they were already at the
 * bottom, or when `force` says the moment is theirs: they switched to this
 * pane, or they just sent something.
 */
function toTheNewest(force = false) {
  if (pane !== "chat") return;
  const scroll = $("scroll");
  const height = Number(scroll.scrollHeight) || 0;
  const seen = Number(scroll.clientHeight) || 0;
  const at = Number(scroll.scrollTop) || 0;
  if (force || height - at - seen < K_AT_THE_BOTTOM) scroll.scrollTop = height;
}

/** Which half is on screen. Separate from drawing the tabs, because the tabs
 * change when the count does and the panes change when the pane does. */
function showPane() {
  // The composer belongs to the conversation, which is the half of this split
  // worth arguing with: a box you type into, pinned under a column of cards
  // about what is happening now, is what made the old panel one long thing.
  for (const id of ["today", "waiting", "cards"]) {
    if (id !== "waiting") $(id).hidden = pane !== "home";
  }
  $("waiting").hidden = pane !== "home" || !$("waiting").childElementCount;
  for (const id of ["thread", "here", "ask-bar"]) $(id).hidden = pane !== "chat";
}

/** Whether the waiting banner is open, in THIS window of the panel.
 *
 * Not stored: it is a fact about a person looking at a panel right now, not
 * about the browser. A second window of the panel is a second pair of eyes and
 * gets its own answer, and both are folded again next time it opens -- which is
 * the state somebody coming back to the panel should find.
 */
let waitingOpen = false;

/** What the banner was last drawn from, so an unchanged one is left alone --
 * with whatever somebody has typed into it, and without a live region
 * repeating itself every two seconds. */
let waitingDrawn = null;

/** Redraw the banner, and nothing else.
 *
 * Its own painter rather than part of `show()` because opening it changes
 * nothing `show()`'s signature can see: the thread is the same, the cards are
 * the same, and the guard there would return before drawing a thing. The
 * toggle calls this directly.
 */
function paintWaiting() {
  const missed = (lastStatus?.nudges || []).filter(
    (nudge) => nudge.state === "open" && nudge.missed,
  );
  // Only when it would say something different. The panel repaints on every
  // push from the worker, and rebuilding these cards each time would take the
  // half-typed value in one of them with it -- the defect the ledger's own
  // redraw guard exists for, in a place that has boxes to type into.
  //
  // It is also what keeps the live region quiet: `#waiting` announces what
  // changes inside it, and replacing identical children every two seconds is a
  // screen reader saying "3 requests arrived" all afternoon.
  const now = `${waitingOpen}|${missed.map((one) => `${one.id}:${one.state}`).join(",")}`;
  if (now === waitingDrawn) return;
  waitingDrawn = now;
  const banner = waiting(missed, {
    open: waitingOpen,
    onToggle: (open) => {
      waitingOpen = open;
      paintWaiting();
    },
    card: (one) => nudging(one, answered),
  });
  $("waiting").replaceChildren(...(banner ? [banner] : []));
  $("waiting").hidden = !banner || pane !== "home";
}

function show(thread, { asked = false } = {}) {
  // The local half belongs in the signature, not only in the draw below it.
  // It was built from the thread alone, and a rig offer writes nothing to the
  // thread -- `considerOffer` stores a nudge and prompts on the page. So an
  // offer made while the thread was quiet was never drawn here: every poll
  // computed the same signature and returned, and the card appeared only when
  // something unrelated changed the thread. Found on 2026-09-14 by a browser
  // that made an offer the panel never showed.
  const mine = (lastStatus?.nudges || [])
    .map((nudge) => `${nudge.id}:${nudge.state}:${nudge.missed ? "m" : ""}:${nudge.k ?? ""}`)
    .join(",");
  // An answer to a question is drawn from the same local half, and changes
  // without the thread changing -- the same defect the nudges above were found
  // to have: every poll computed the same signature and returned.
  // NOT `answered`: that is the press handler this function hands to the
  // ledger twenty lines down, and a local of the same name shadowed it -- so
  // `onPress` was a string, and every press in the thread threw
  // "onPress is not a function" into a click listener nobody was watching.
  // The panel drew the cards and answered none of them. Found by an operator
  // pressing "Yes, do it" on a rule that had fired and getting nothing.
  // `said` is taken too -- it is how this panel writes a line back to the
  // operator -- so this name belongs to neither.
  const answerSeen = `${lastStatus?.answer?.askedAt || ""}:${(lastStatus?.answer?.answers || []).length}`;
  const missed = (lastStatus?.nearMisses || []).map((one) => `${one.triggerId}:${one.at}`).join(",");
  const asking = (lastStatus?.waiting || []).map((one) => one.id).join(",");
  const now = `${thread.id}:${(thread.messages || []).map((message) => message.id).join(",")}|${mine}|${answerSeen}|${missed}|${asking}|${hostOf(tabHere.url || "")}`;
  if (now === drawn) return;
  if (!asked && drawn !== null && document.activeElement?.tagName === "INPUT") return;
  drawn = now;
  // What only this browser knows, beside what the server holds: the mails it
  // recognised and the prompts it made on the page in front of somebody.
  // Neither is written down, and both belong in the order things happened.
  const local = {
    offers: lastStatus?.offers || [],
    // Open ones for THIS tab, and ones that ended in the last few seconds --
    // nothing else.
    //
    // An operator on their login page was shown eleven rows saying "you were
    // on Create a Work Area" and "you were on Create Customer Type DSS", none
    // of them about the page in front of them, none of them pressable, from
    // yesterday. A nudge is a thing offered and then gone; the ledger is for
    // what was SAID and DECIDED, and an offer nobody answered decided nothing.
    //
    // The brief tail is deliberate rather than zero: an offer that vanishes
    // the instant it expires looks, to somebody who just watched it appear,
    // like the panel losing it. Four seconds is long enough to see it go.
    // A card with no tab behind it is not about a tab. A mail arrived while
    // the operator was somewhere else entirely -- filtered to the tab in front
    // of them it would never be drawn at all, which is how the first version
    // of this lost every request it recognised.
    // Only the ones that have just ENDED. An open offer is a thing to press
    // and belongs on Home with everything else that is true right now; what
    // the conversation keeps is the brief tail of one that closed, so somebody
    // who just watched it go can see that it went rather than wonder where the
    // panel put it.
    nudges: (lastStatus?.nudges || []).filter(
      (nudge) => nudge.state !== "open" && Date.now() - (nudge.endedAt || 0) < JUST_ENDED_MS,
    ),
    answer: lastStatus?.answer || null,
    nearMisses: lastStatus?.nearMisses || [],
    waiting: lastStatus?.waiting || [],
    // Which system the operator is actually looking at, so an offer about
    // another one keeps its words and loses its buttons.
    here: hostOf(tabHere.url || ""),
  };
  openOffers = (thread.messages || []).filter(
    (message) => ["offer", "mail_match"].includes(message.decision?.kind || "")
      && !alreadyAnswered(thread.messages).has(message.decision.candidate_id),
  ).length;
  $("said").replaceChildren(ledger(thread, local, { onPress: answered }));
  // After the words are in, because the height it scrolls to is the height
  // they made. `asked` is the operator's own send, which is always theirs to
  // move the view for.
  toTheNewest(asked);
  // Drawn once and left alone: rebuilding it on every poll would take the
  // cursor out of a half-typed sentence.
  if (!$("ask-bar").childElementCount) $("ask-bar").append(composer(say));
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
    // `tabId` so an offer the sentence turns into is drawn beside the tab the
    // operator is working in -- `show` only draws an OPEN nudge for this tab.
    show(await ask({ kind: "thread-say", threadId, text, tabId: tabHere.tabId }), {
      asked: true,
    });
  } catch (error) {
    $("thread-note").textContent = error.message;
  }
}

/** Something in the thread, answered.
 *
 * The message is a thing that was said; this press is the authorisation.
 * Nothing here runs because a message asked for it.
 *
 * Every path below is the rig's. The mining pipeline's own offer -- "you've
 * done this 4 times, want me to do the next one?" -- is gone: it offered to
 * teach a SKILL from recordings, which is not the system this browser drives,
 * and the rig already holds that work as a job with steps. The ledger no
 * longer draws those messages at all.
 */
async function answered(answer, message, where, button, values) {
  // An offer the rig made about the job in front of somebody. Its two answers
  // are its own -- `nudge-answer` is the backend nudge's -- because the worker
  // reports one fate per path, and an offer that took both would be counted
  // twice.
  if (answer === "start-rig-run" || answer === "drop-nudge") {
    return answeredOffer(answer, message, button, values);
  }
  // "Always, here." A rule rather than a run: nothing starts now, and the next
  // time this operator lands on the page this offer is about, their own
  // browser starts the job. Kept out of `answeredOffer` because that function
  // reports an offer's FATE, and making a rule is not one of the three -- the
  // offer in front of them is still theirs to answer either way.
  if (answer === "do-this-here") return madeARule(message, button);
  // Which of the two jobs they meant. Said back into the conversation as the
  // job's own name rather than started here: the door then reads a sentence
  // with no ambiguity left in it, and the offer it makes is the ordinary one.
  if (answer === "which-job") {
    button.disabled = true;
    return say(values?.title || button.textContent || "");
  }
  // A rule that fired and stopped to ask, answered from where the operator is
  // rather than only in the console.
  if (answer === "waiting-approve" || answer === "waiting-decline") {
    return answeredWaiting(answer, message, button);
  }
  const decision = message.decision || {};
  // A matched mail: the values are the browser's, and the ones the operator
  // typed into the card are what the run must use -- so they go up on the press
  // rather than the ones the mail happened to fill.
  if (decision.kind === "mail_match") return firedFromMail(decision, answer, button, values);
}

/** The rig's offer, answered.
 *
 * The values are the ones on the card: the prefix read some off the page and
 * the operator typed the rest, and both are in front of them when they press.
 * The run is started in the worker, which holds the credential; this is the
 * press that authorises it.
 *
 * Either way it ends by drawing the thread again from scratch. The card
 * disables itself on the press, so leaving it there after a refusal would leave
 * a dead offer under the cursor -- and the offer is still open in the worker
 * when a start is refused, so what belongs on screen is the card as it now is,
 * not the spent one.
 */
async function answeredOffer(answer, nudge, button, values) {
  button.disabled = true;
  try {
    if (answer === "drop-nudge") {
      await ask({ kind: "drop-nudge", nudgeId: nudge.id });
      said("dismissed \u2014 nothing ran");
    } else {
      const got = await ask({
        kind: "start-rig-run",
        nudgeId: nudge.id,
        values: values?.values || {},
      });
      said(got.ok ? "started \u2014 watching it below" : got.error || "nothing started");
    }
  } catch (error) {
    said(error.message);
  }
  await refresh();
  drawn = null;
  await conversation();
}


/** A fire waiting on somebody, answered from the panel.
 *
 * The run starts with the name on THIS credential, not the name of whoever
 * made the rule: an unattended write happens because somebody said so, and
 * pressing this is the somebody.
 */
async function answeredWaiting(answer, card, button) {
  try {
    const got = await ask({
      kind: "answer-waiting",
      confirmationId: card.id,
      answer: answer === "waiting-approve" ? "approve" : "decline",
    });
    if (!got.ok) {
      button.disabled = false;
      said(got.error || "nothing happened");
      return;
    }
    said(got.run_id ? "started \u2014 watching it below" : "declined \u2014 nothing ran");
  } catch (error) {
    button.disabled = false;
    said(error.message);
  }
  await refresh();
  drawn = null;
  await conversation();
}


/** "Do this here", answered from the ledger.
 *
 * The page is the offer's, chosen in the worker: a rule made about whichever
 * tab the panel happens to be docked beside is a rule about the wrong page
 * that fires forever after.
 */
async function madeARule(nudge, button) {
  try {
    const got = await ask({ kind: "do-this-here", nudgeId: nudge.id });
    if (got.ok) {
      said(`from now on this runs when you land on ${got.page}`);
      return;
    }
    // The card said "every time you land here" on the press. It is not true,
    // so it is taken back rather than left standing.
    button.disabled = false;
    button.textContent = "Always, here";
    said(got.error || "no rule was made");
  } catch (error) {
    button.disabled = false;
    button.textContent = "Always, here";
    said(error.message);
  }
}


/** A matched mail, answered from the ledger.
 *
 * `watch-fire` is the same call the offer card has always made; what is new is
 * that the values come from the fields the operator may have edited. A press is
 * still the authorisation, and the run is still the server's to start.
 */
async function firedFromMail(decision, answer, button, values) {
  button.disabled = true;
  if (answer !== "run") {
    await ask({ kind: "drop-offer", offerId: decision.offer_id });
    said("dismissed — the mail is untouched and nothing ran");
    return refresh();
  }
  try {
    const fired = await ask({ kind: "watch-fire", offerId: decision.offer_id, values });
    said(fired.run_id ? "started" : `nothing started: ${fired.skipped}`);
  } catch (error) {
    said(error.message);
    button.disabled = false;
  }
  await refresh();
}

// -- tasks you keep doing here ----------------------------------------------

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

// The worker pushes the state; this only asks when it has not heard.
//
// It used to poll every two seconds, which is two redraws a second of work
// nobody did and, worse, a state change waiting up to two seconds to appear:
// a rule fires, a run starts, an offer arrives, and the panel sits on the old
// picture. A named port lets the worker say so the moment it knows.
//
// The port is opened lazily and never retried in a loop -- a service worker
// is evicted whenever Chrome feels like it, taking every port with it, and an
// eager reconnect turns each eviction into a storm. The slow beat below
// reopens it on its own schedule, and doubles as the safety net for a push
// that was never delivered.
let toWorker = null;

function listen() {
  if (toWorker) return;
  try {
    toWorker = chrome.runtime.connect({ name: "panel" });
  } catch {
    // No worker to connect to this instant. The beat tries again.
    toWorker = null;
    return;
  }
  toWorker.onDisconnect.addListener(() => {
    toWorker = null;
  });
  toWorker.onMessage.addListener((message) => {
    if (message?.kind !== "status" || document.visibilityState !== "visible") return;
    void drawPushed(message.status);
  });
}

/** A status the worker sent, drawn the same way a fetched one is.
 *
 * `refresh()` is what knows how to finish a status -- the performing card needs
 * the run and the skill behind it, which are the backend's and not the
 * worker's -- so a push that carries a run takes that path rather than growing
 * a second one that would drift from it.
 */
async function drawPushed(pushed) {
  if (pushed?.performing) return refresh();
  void sayTheDay(pushed);
  render(pushed);
}

// How the panel learns it is beside a different tab.
//
// One side panel serves the whole window, so switching tabs does not reload
// this document and nothing about it changes by itself. When the worker's
// push replaced the two-second poll, the beat below went to twenty seconds --
// and `whereWeAre` went with it, having been a passenger on that poll. It got
// nothing in return: the push carries the WORKER's status, fired by
// `chrome.storage.onChanged`, and which tab an operator is looking at is not
// worker state and never reaches storage. So a tab switch was noticed only by
// the twenty-second net.
//
// Every card here is about "this tab". For that whole stretch the state line,
// the watch button and what is offerable all belonged to the tab the operator
// had just left -- which is the five to seven seconds they reported, and
// twenty if they switched at the wrong moment.
//
// Events rather than a faster beat: a tab switch is a thing Chrome tells us
// about, and the beat stays where it is, as the safety net it already was.
chrome.tabs.onActivated?.addListener(() => void whereWeAre());
// The same tab navigating. A warehouse screen that routes without a page load
// still changes what this panel should say, and `beside()` reads the url.
chrome.tabs.onUpdated?.addListener((_tabId, changeInfo) => {
  if (changeInfo.url) void whereWeAre();
});
// Switching WINDOWS activates no tab -- the one being focused was already
// active in its own window -- so `onActivated` never fires and this is the only
// thing that says the panel is now beside something else.
chrome.windows?.onFocusChanged?.addListener(() => void whereWeAre());

setInterval(() => {
  if (document.visibilityState !== "visible") return;
  listen();
  void whereWeAre();
  // The safety net, at a tenth of the old rate: a push that never arrived, a
  // worker evicted between one and the next, a port that closed quietly.
  void refresh();
}, 20000);

// ponytail: the thread is polled too, on its own slower tick -- it is a call to
// the API rather than a read of the worker's own state, and nothing in a
// conversation arrives fast enough to be worth the two-second one. Make it a
// push from the worker if an offer ever needs to land sooner than this.
// The conversation, polled only while somebody is reading it.
//
// It was polled every five seconds whatever was on screen, which on a panel
// that is now two halves is a call about a pane nobody is looking at. Home
// draws no thread at all, and what Home DOES draw -- the cards, the run, what
// is waiting -- arrives on the worker's own port the moment it changes.
//
// ponytail: a push would make even this one unnecessary, and the plan asks for
// one -- a `thread.changed` command relayed to the panel. It is not built,
// because the thing that needed to land sooner than five seconds was the mail
// offer, and that is a card now rather than a line in the conversation: it
// comes over the port already. Build the push the day a SENTENCE has to land
// faster than a person can read the one above it.
setInterval(() => {
  if (document.visibilityState !== "visible" || pane !== "chat") return;
  void conversation();
}, 5000);

listen();
void refresh();
void whereWeAre();
void conversation();
