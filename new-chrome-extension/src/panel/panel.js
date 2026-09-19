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
import { history } from "./history.js";
import { panes } from "./panes.js";
import { dayNamed, pending, when } from "./pending.js";
import { needsAPress, strip } from "./strip.js";
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
  const [active] = await chrome.tabs.query({
    active: true,
    currentWindow: true,
  });
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
  return seconds < 60
    ? `${seconds}s`
    : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

// -- building a card ---------------------------------------------------------

/** One thing that is true, and what can be done about it.
 *
 * A panel that reports a problem without a way out is a panel people stop
 * reading, so a card that has an action carries it; one that does not says why
 * in a sentence somebody can act on elsewhere.
 */
function card({
  title,
  says,
  metrics,
  notes,
  stage,
  progress,
  tone,
  actions = [],
  toggle,
}) {
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
    // A run in flight says so the way every other surface says it: something
    // turning, beside the words. A card that reads "looking in your mail for
    // Customer Type…" and never moves is indistinguishable from one that hung
    // -- and on 2026-09-16 that is exactly what an operator was looking at for
    // three and a half minutes while the gather retried a 5xx. The ellipsis
    // was doing this job and an ellipsis does not move.
    //
    // CSS only, and off under `prefers-reduced-motion`. A timer per card is a
    // panel that keeps a phone's radio awake to draw a dot.
    if (tone === "live") {
      const turning = document.createElement("span");
      turning.className = "spinner";
      // It says nothing a screen reader needs: the line beside it already
      // says what is happening, and the elapsed time says it is still going.
      turning.setAttribute("aria-hidden", "true");
      const words = document.createElement("span");
      words.textContent = says;
      line.append(turning, words);
    } else {
      line.textContent = says;
    }
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
    strip(status, tabHere, {
      onMenu: menu,
      onToggle: toggleExpanded,
      // The panel's own element, handed over rather than rebuilt: this redraw
      // runs every couple of seconds and the buttons in it must not be
      // replaced under the cursor that is about to press one.
      nav: theNav(),
    }),
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
          "This browser has no credential. Nothing is recorded and no task can be " +
          "taught until it is connected to your deployment.",
        tone: "attention",
        actions: [
          {
            label: "Connect",
            primary: true,
            act: () => chrome.runtime.openOptionsPage(),
          },
        ],
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
  if (!status.teaching)
    for (const offer of status.offers || []) cards.push(offering(offer));

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
  //
  // ONE of them, and the rest behind the tray.
  //
  // Home had eleven cards on it: two of them the same request twice, four from
  // earlier in the day, and the one that had just arrived at the bottom. A
  // panel that exists to say "here is the thing that needs you" was saying it
  // eleven times, which is the same as not saying it. Measured on the
  // deployment 2026-09-18.
  //
  // The newest, because that is the one anybody acts on -- nobody works
  // Tuesday's request on Thursday, and the older ones are a list to go
  // through rather than a thing in the way of the run happening now.
  if (!status.teaching) {
    const here = (lastStatus?.nudges || status.nudges || []).filter(
      (nudge) =>
        nudge.state === "open" &&
        !nudge.missed &&
        !(nudge.tabId != null && nudge.tabId !== tabHere.tabId),
    );
    const [newest, ...rest] = [...here].sort((a, b) => when(b.at) - when(a.at));
    if (newest) {
      const one = nudging(newest, answered);
      if (justArrived(newest)) one.dataset.fresh = "1";
      cards.push(one);
    }
    // And a way to the rest, which is a line rather than ten more cards.
    if (rest.length) cards.push(theRest(rest));
  }

  // A mail that has gone out and not been answered.
  //
  // On Home as well as in the conversation, because the two panes answer two
  // different questions and this is an answer to both: the conversation says
  // what was said, and Home says what is true right now. What was true for as
  // long as a reply took was a panel doing visibly nothing.
  const waitingOnMail = mailCard(status);
  if (waitingOnMail) cards.push(waitingOnMail);

  // A question nobody has answered, before anything about what is happening
  // now. It is the one thing on this panel that is waiting on THEM.
  if (status.question) cards.push(theQuestion(status.question));
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
  drawnCardsOnce = true;
  toTheQuestion(status.finished);
  paintPanes();
  // What arrived while nobody was looking, above everything. Painted from the
  // worker's status rather than from the thread, because that is what it is
  // about -- a request waiting is a fact about this browser, not a line in a
  // conversation -- and after `lastStatus` is set, which is what it reads.
  paintWaiting();
  return status;
}

const K_FRESH_MS = 20000;
/** How long a card that has just arrived keeps its moving border. Long enough
 * to be on screen when somebody is sent here to look at it, short enough that
 * a panel left open does not have four cards asking for attention at once. */

const seenCards = new Set();
const freshUntil = new Map();
let drawnCardsOnce = false;

/** Whether this card is new since the last draw -- and, if it is, send the
 * operator to it.
 *
 * An answer that arrives by mail lands on Home while the person who asked for
 * it is reading the conversation, so the card they have been waiting for
 * appears behind the other tab with nothing to say it did. The same reasoning
 * as `goToTheConversation` when a run asks a question: the panel moves to
 * where the thing that needs a person is, rather than leaving them to find it.
 *
 * Only after a first draw. Every card is new to a panel that has just opened,
 * and a panel that jumped to Home and lit up four borders on open would be
 * shouting about nothing that happened.
 */
function justArrived(nudge) {
  const id = nudge.id;
  if (!id) return false;
  if (!seenCards.has(id)) {
    seenCards.add(id);
    if (drawnCardsOnce) {
      freshUntil.set(id, Date.now() + K_FRESH_MS);
      // The pane, not a redraw: this is called from inside the draw, and
      // `paintPanes` runs at the end of it.
      pane = "home";
    }
  }
  return (freshUntil.get(id) || 0) > Date.now();
}

/** The requests Home is not showing, as one line that opens them.
 *
 * Not a card per request, which is what this replaces. A person looking at
 * Home is looking for the next thing to do; how much else is queued is a
 * number, and the queue itself is somewhere to go.
 */
function theRest(rest) {
  const oldest = rest.reduce(
    (was, one) => (when(one.at) < when(was.at) ? one : was),
    rest[0],
  );
  return card({
    title: `${rest.length} more waiting`,
    says:
      rest.length === 1
        ? `One more request, from ${dayNamed(oldest.at).toLowerCase()}.`
        : `The oldest is from ${dayNamed(oldest.at).toLowerCase()}.`,
    actions: [{ label: "Go through them", primary: true, act: theBacklog }],
  });
}

/** Waiting on somebody's mailbox, said on Home.
 *
 * `tone: "live"` for the turning indicator the gather card already uses: one
 * animation in this panel for "something is happening and you are not waiting
 * on it", rather than a second one that means the same thing differently.
 *
 * Nothing here is an estimate. Who was asked, when they were asked, when this
 * browser last read the mailbox, and whether it is reading one this second --
 * every number is something this browser did.
 */
function mailCard(status) {
  const mail = status.mail;
  if (!mail?.awaiting) return null;
  const to = mail.awaiting.to || "whoever was asked";
  return card({
    title: "Waiting on a reply",
    says: mail.looking
      ? `Reading the mailbox for ${to}'s answer`
      : `Asked ${to} ${ago(mail.awaiting.at)}. Last read the mailbox ${ago(mail.lookedAt)}`,
    tone: "live",
  });
}

/** How long ago, in the roundest words that are still true. */
function ago(at) {
  const was = Number(at) || 0;
  if (!was) return "not yet";
  const seconds = Math.max(0, Math.round((Date.now() - was) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  return minutes < 60 ? `${minutes}m ago` : `${Math.round(minutes / 60)}h ago`;
}

/** A question this operator has not answered.
 *
 * Drawn from the CONVERSATION by way of the worker, not from the run that
 * asked it. The run is one slot: on 2026-09-17 a question was written at 03:57
 * and a later run took that slot at 03:59, and the question sat unanswered in
 * the thread for the rest of the morning with nothing on screen about it.
 *
 * A card rather than a line in the waiting banner, and it says the whole
 * question rather than a count: "3 requests arrived" is a number somebody
 * opens when they have a minute, and this is a job of theirs that has stopped
 * a foot from the end.
 */
function theQuestion(question) {
  return card({
    title: question.title
      ? `${question.title} — waiting on you`
      : "Waiting on you",
    says: question.text,
    tone: "attention",
    actions: [
      {
        label: "Answer it",
        primary: true,
        act: () => {
          pane = "chat";
          paintPanes();
          void conversation();
          toTheNewest(true);
          // In the box, so the answer is one keystroke away rather than one
          // press and then a hunt for where to type it.
          $("ask-bar").querySelector?.("input")?.focus();
        },
      },
    ],
  });
}

/** The run that has already been taken to its question, so the panel moves
 * somebody once and not on every poll. */
let askedAbout = null;

/** A run that came up short asks, and the asking is in the conversation.
 *
 * The run went looking for values nobody typed and could not find one. It
 * ends -- it has to, a write with a blank in it is a wrong record -- and what
 * it could not find is already a question in this operator's own thread,
 * written by the backend as the run closed.
 *
 * What is left is putting them in front of it. A question waiting behind the
 * other tab, under a card reading "The run stopped", is a question nobody
 * answers: the panel showed the dead end and hid the way out of it.
 *
 * Once per run. The status lands every couple of seconds and a pane that
 * re-asserted itself on each one is a panel somebody cannot leave -- they are
 * allowed to go back to Home and look at something else.
 */
function toTheQuestion(run) {
  if (!run || run.source !== "rig" || !(run.needs || []).length) return;
  if (run.id === askedAbout) return;
  askedAbout = run.id;
  pane = "chat";
  void conversation();
  // At the end of it, which is where the question is.
  toTheNewest(true);
}

/** Watch this system wherever it opens, from now on.
 *
 * The press says it about the HOST. Every tab already open on it is watched
 * too -- saying it about a system and leaving four of its tabs blind is the
 * same defect one layer along.
 */
async function alwaysWatch(button) {
  button.disabled = true;
  try {
    await ask({ kind: "always-watch", tabId: tabHere.tabId, url: tabHere.url });
    said(`watching ${tabHere.host} wherever it opens`);
  } catch (error) {
    said(error.message);
  }
  await refresh();
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
      await ask({
        kind: "unwatch-tab",
        tabId: tabHere.tabId,
        url: tabHere.url,
      });
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
      {
        label: "Stop and save",
        primary: true,
        act: (button) => stopTeaching(button),
      },
      {
        label: "Discard",
        act: (button) => stopTeaching(button, { discard: true }),
      },
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
      title: excluded
        ? `${tabHere.host} is not normally recorded`
        : "Not watching this tab",
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
        // Once, about the system, rather than once per tab.
        //
        // A tab id lives for as long as one tab and the work does not: a link
        // opened in a new tab, a window reopened after lunch, and the tab a
        // RUN opens for itself are all the same system doing the same job.
        // Measured on the deployment, 2026-09-17 -- a run drove a Blue Yonder
        // tab it had opened, with its own banner across the top of it, while
        // this panel said "not watched" beside it. Nothing it did was
        // evidence, so the job performed and the system learnt nothing.
        {
          label: `Always watch ${tabHere.host}`,
          disabled: !status.capturing || !tabHere.host,
          act: (button) => alwaysWatch(button),
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
        {
          label: "Reload this page",
          primary: true,
          act: (button) => reloadWatched(button),
        },
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
        (status.policy?.capture_snapshots
          ? " · reading this page's structure too"
          : ""),
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
      (status.policy?.capture_snapshots
        ? " · reading this page's structure too"
        : ""),
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
    await ask({
      kind: on ? "watch-tab" : "unwatch-tab",
      tabId: tabHere.tabId,
      url: tabHere.url,
    });
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
        (done === null
          ? "."
          : total
            ? `. Step ${done} of ${total}.`
            : `. Step ${done}.`),
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
          openConsole(
            run.source === "rig"
              ? `/jobs/runs/${run.runId}`
              : `/runs/${run.runId}`,
          ),
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
              const got = await ask({
                kind: "approve-rig-run",
                runId: drawn.id,
              });
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
  // "to ask" only when something is actually waiting on somebody; `howItEnded`
  // below decides. A run that stopped because a step failed was announcing a
  // question nobody had been asked, on a card whose own rows said a step had
  // failed -- and the operator went looking for the thing to answer.
  stopped: "The run stopped.",
  refused: "The run was refused.",
  aborted: "The run was stopped.",
  failed: "The run failed.",
};

/** How a rig run ended, in the words of the thing that ended it.
 *
 * `RIG_ENDINGS` names the outcome and nothing else, which is right for four of
 * the five and useless for `stopped`: a run stops because a step is waiting on
 * a person, or because a step failed twice, and those want two different
 * people to do two different things. The step already knows which -- it was
 * simply not being read, so every stop announced a question and half of them
 * had asked nobody anything.
 *
 * The failure's own words, not ours: "unreachable: TypeError: Failed to fetch"
 * says the browser could not reach the system, and "the run stopped" says a
 * person should go and look at something.
 */
/** What a finished job made, as the thing it is.
 *
 * Big, because it is the answer. Bordered and moving, because a run finishing
 * is the one moment on this surface worth catching an eye that was elsewhere
 * -- and the movement stops the moment somebody has read it, which is what the
 * press is for. A card that pulses forever is a card people learn to stop
 * seeing.
 *
 * The steps stay, folded. Nobody reads them when the answer is what they
 * expected, and everybody wants them the one time it is not.
 */
function madeCard(run, wrote, ending) {
  const holder = document.createElement("div");
  holder.className = "made";
  holder.dataset.runId = run.id;

  const what = document.createElement("p");
  what.className = "made-what";
  what.textContent = wrote;
  holder.append(what);

  const how = document.createElement("p");
  how.className = "detail";
  how.textContent = ending || "";
  holder.append(how);


  // The machinery, for the time it is wanted. `<details>` because it is the
  // one disclosure the browser already gets right -- keyboard, screen reader
  // and all -- and this panel has no business reimplementing it.
  const steps = document.createElement("details");
  steps.className = "made-steps";
  const summary = document.createElement("summary");
  summary.textContent = `How it went — ${(run.steps || []).length} steps`;
  steps.append(summary);
  steps.append(
    runCard(
      { run, skill: null, message: { text: "" } },
      { onSecret: keepSecret },
    ),
  );
  holder.append(steps);

  // What takes it back, where this tenant has been seen doing it.
  //
  // The rig's result card has never offered one. The reason was written into
  // this file -- "a run the rig drove has neither a reversal nor anywhere to
  // send It's wrong" -- and it was true: the backend answered an id and could
  // not say which record a press would address, so a button here would have
  // been a button that deletes something nobody named.
  //
  // It can say now. `undoes_by` is the record as the warehouse named it, and
  // `undo` is the mined job whose own evidence shows somebody deleting records
  // of this kind. Both, or neither: a press that cannot name what it removes
  // is not a press anybody consented to.
  const back =
    run.undo && run.undoes_by ? Object.entries(run.undoes_by)[0] : null;
  if (back) {
    const says = document.createElement("p");
    says.className = "detail";
    says.dataset.kind = "undo";
    // Named before the press and not after it, which is ADR 014's rule for the
    // skill reversal beside this one: the operator reads what it will do.
    says.textContent = `“Undo it” runs a job that deletes ${back[0]} ${back[1]}.`;
    holder.append(says);
  }

  const row = document.createElement("div");
  row.className = "row";
  if (back) {
    const undo = document.createElement("button");
    undo.type = "button";
    undo.className = "quiet";
    undo.textContent = "Undo it";
    undo.addEventListener("click", () => {
      undo.disabled = true;
      void undoTheRun(run, back, undo);
    });
    row.append(undo);
  }
  const ok = document.createElement("button");
  ok.type = "button";
  ok.textContent = "OK";
  ok.addEventListener("click", () => {
    // The sweep stops on the press, not when the refresh lands. A border still
    // travelling under a button somebody has just pressed reads as a press
    // that did not register.
    holder.dataset.read = "true";
    void forgetRun(ok);
  });
  row.append(ok);
  holder.append(row);
  return holder;
}

/** What this run took back, where it was an undo of another. */
function tookBack(run) {
  if (!run.undoes_run) return "";
  return run.status === "held"
    ? `This took back what run ${run.undoes_run} made.`
    : `This was taking back what run ${run.undoes_run} made, and did not finish` +
        ` — that record is still there.`;
}

/** One press that runs the same job again, with the values it already had. */
function tryAgainRow(run) {
  const row = document.createElement("div");
  row.className = "row";
  const again = document.createElement("button");
  again.type = "button";
  again.textContent = "Try it again";
  again.addEventListener("click", async () => {
    again.disabled = true;
    try {
      const started = await ask({
        kind: "retry-rig-run",
        workflowId: run.workflow_id,
        values: run.values || {},
        items: run.items || [],
      });
      if (started?.ok === false) {
        again.disabled = false;
        said(started.error || "that job could not be started");
        return;
      }
      said("trying it again");
      goToTheRun();
    } catch (error) {
      again.disabled = false;
      said(`that job could not be started: ${error.message}`);
    }
  });
  row.append(again);
  return row;
}

/** Start the job that takes back what this run made.
 *
 * An ordinary rig run of an ordinary mined job, started with the one value that
 * names the record -- not a special path, and deliberately so: the delete goes
 * through the same ladder, the same write gate and the same belts as any other
 * job, and an undo that skipped them would be the one write in this system
 * nobody checked.
 */
async function undoTheRun(run, [field, names], button) {
  try {
    const started = await ask({
      kind: "undo-rig-run",
      workflowId: run.undo,
      values: { [field]: names },
      // Which run this takes back. Two panels showing one card would otherwise
      // press two deletes at one record; the backend refuses the second.
      undoesRun: run.id,
    });
    if (started?.ok === false) {
      button.disabled = false;
      said(started.error || "that job could not be started");
      return;
    }
    said(`taking back ${field} ${names}`);
    goToTheRun();
  } catch (error) {
    button.disabled = false;
    said(error.message);
  }
}

/** The operator has read it. Clears only the copy this panel draws -- the run
 * itself is on the backend for as long as the tenant keeps it. */
async function forgetRun(button) {
  button.disabled = true;
  try {
    await ask({ kind: "forget-run" });
  } catch (error) {
    said(error.message);
  }
  await refresh();
}

/** What a run that held actually wrote, named.
 *
 * Only for a run that HELD: a run that stopped wrote nothing, or wrote
 * something nobody has confirmed, and a card claiming otherwise is the one
 * lie this surface must never tell.
 *
 * Values and not step records, for the reason `finished` gives. Trimmed,
 * because a description may hold two thousand characters and this is a
 * headline.
 */
function whatItWrote(run) {
  if (run.status !== "held") return "";
  const said = Object.values(run.values || {})
    .map((one) => String(one || "").trim())
    .filter(Boolean)
    .map((one) => (one.length > K_WROTE ? `${one.slice(0, K_WROTE)}…` : one));
  return said.length ? said.join(", ") : "";
}

/** How much of one written value the card repeats back. Enough to recognise
 * the record by, not enough to push the steps off the screen. */
const K_WROTE = 60;

/** A sentence that now follows something else. `The run finished…` reads badly
 * after a dash; `the run finished…` does not. Only the first letter, and only
 * where it is a letter: a value that starts with a digit is left alone. */
function lowerFirst(said) {
  return /^[A-Z][a-z]/.test(said)
    ? said[0].toLowerCase() + said.slice(1)
    : said;
}

function howItEnded(run) {
  const steps = run.steps || [];
  if (steps.some((step) => step.outcome === "awaiting"))
    return "The run stopped to ask.";
  const failed = [...steps].reverse().find((step) => step.outcome === "failed");
  const why = String(failed?.reason || "").trim();
  if (why)
    return `The run stopped — ${why.slice(0, K_WHY)}${why.length > K_WHY ? "…" : ""}`;
  // A run that held having skipped steps did not do what its rows say it did.
  // Measured on the deployment, 2026-09-17 at 14:20: four of six steps came
  // back `not_needed` -- the page would not take the click, so the form was
  // never filled and the write went out as a call -- and the card said "every
  // step held" above four dashes. The record was made and the sentence was
  // still false, which is the worse half: an operator reads the sentence.
  // ...and a run that skipped a step did not necessarily send its write as a
  // call either. That is the sentence this became, and it was wrong the other
  // way round: measured on the deployment, 2026-09-18 at 02:20, a run that
  // pressed every button on the page and made the record by clicking Save --
  // five ticks, every one `component`, $0.0224 -- was announced as "the write
  // went out as a call, 1 step on the page skipped". The skipped step was
  // "Open an email", which is skipped on every single run of this job because
  // the mail was read before the run began.
  //
  // So the two facts are said separately, because they are separate: a step
  // the run did not do, and a write that did not go through the form. A write
  // done on the page carries the locator that found its button, which is what
  // `matched_by` is; a replayed call has none.
  const skipped = steps.filter((step) => step.outcome === "not_needed").length;
  if (run.status !== "held" || !skipped)
    return RIG_ENDINGS[run.status] || "The run ended.";
  const wrote = [...steps].reverse().find((step) => step.outcome === "held");
  const many = `${skipped} ${skipped === 1 ? "step" : "steps"}`;
  return wrote?.matched_by
    ? `The run finished — ${many} skipped, and the rest done on the page.`
    : `The run finished — the write went out as a call, ${many} on the page skipped.`;
}

/** How much of a failure's own words the card carries. Long enough for
 * "unreachable: TypeError: Failed to fetch", short enough that a stack trace
 * cannot become the card. */
const K_WHY = 120;

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
    // A run that stopped for want of a value says what it is waiting on, not
    // that it stopped. "The run stopped" is true and useless: the operator
    // pressed yes, something went looking on their behalf and came back one
    // word short, and the question about that word is in the conversation this
    // panel has just moved them to.
    const short = [
      (run.needs || []).length
        ? `I could not find ${run.needs.join(", ")} — I have asked in the conversation.`
        : howItEnded(run),
      // And where this run is itself an undo, which run it took back.
      //
      // The two are one piece of work and nothing said so. A delete that
      // worked is quietly right either way; a delete that did NOT is what this
      // is for -- an undo that fails writes nothing, so it has no result card
      // of its own to read, and the card that offered the press has been
      // answered and gone. Without this the failure reads as a job that failed
      // on its own rather than as a record still sitting in the warehouse.
      tookBack(run),
    ]
      .filter(Boolean)
      .join(" ");
    // And WHAT it made, first, because that is the thing somebody came to the
    // card to read.
    //
    // The card said "the run finished — 1 step skipped, and the rest done on
    // the page" and stopped: true, and it never named the record. An operator
    // who authorised a write is owed the write, not a report on the mechanism
    // that performed it.
    //
    // From the run's own values rather than from the warehouse's answer. The
    // step that created it records `made` from the response body, and for a
    // write performed on the PAGE there is no body to read -- the browser sees
    // the call and its status, not what came back, and it stays that way
    // deliberately: a create's answer is a row of somebody's data. What this
    // says is therefore what the run WROTE, which the 201 and the screen belt
    // between them confirm landed.
    const wrote = whatItWrote(run);
    // A job that finished is a RESULT, and a result is not a report.
    //
    // The card drew six rows of machinery -- which rung matched, what each
    // step cost -- above the one thing somebody came to read, which is what
    // now exists in the warehouse that did not exist a minute ago. That is the
    // right card while a run is going and the wrong one once it has gone: the
    // steps are how, and how is a thing you go and look for when the answer
    // surprises you.
    //
    // So the values are the card, the steps fold away behind them, and it ends
    // when the operator says they have read it rather than when an hour is up.
    if (wrote) return madeCard(run, wrote, short);
    const card = runCard(
      {
        run,
        skill: null,
        message: {
          text: wrote
            ? `${wrote} — ${lowerFirst(short || "done")}`
            : short || RIG_ENDINGS[run.status] || "The run ended.",
        },
      },
      { onSecret: keepSecret },
    );
    // And one press to try it again, where trying again is safe.
    //
    // A run stops for reasons that have nothing to do with the job -- a
    // session that expired, a tab closed, a browser that could not be reached
    // -- and the offer that started it is spent, so the request sat there
    // until somebody noticed and sent the mail again. Measured on the
    // deployment 2026-09-19: a run stopped on a sign-in page and this card
    // offered a person nothing at all.
    //
    // `try_again` is the backend's answer, not this card's guess: it is true
    // only where nothing the run did may have landed. A second press after a
    // write nobody could confirm is two records.
    if (run.try_again && run.workflow_id) card.append(tryAgainRow(run));
    return card;
  }
  const ok = run.status === "succeeded";
  const made = ok ? Object.entries(run.derived || {}) : [];
  const actions = [];
  const notes = [];
  if (ok && run.reversal) {
    actions.push({
      label: "Undo that",
      primary: true,
      act: (button) => undoRun(button, run),
    });
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
    actions.push({
      label: "It's wrong — I'll fix it",
      act: (button) => wasWrong(button, run),
    });
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
    await ask({
      kind: "run-wrong",
      runId: run.id,
      because: "the operator said this was wrong",
    });
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
  if (
    status.deviceId &&
    !status.capturing &&
    !status.paused &&
    !status.serverPaused
  ) {
    cards.push(
      card({
        title: "Not observing",
        says: `${status.because}.`,
        tone: "attention",
      }),
    );
  }
  if (status.deviceId && status.channel !== "open") {
    cards.push(
      card({
        title: "This browser cannot be reached",
        says:
          (status.channelWhy
            ? `Not dialling: ${status.channelWhy}. `
            : `The command channel is ${status.channel}. `) +
          "A run started from the console or a schedule cannot act here until it " +
          "opens; nothing already captured is lost.",
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
    if (!tab)
      throw new Error("open the system you want to teach in this tab first");
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
      said(
        `saved — ${steps} step${steps === 1 ? "" : "s"}. Teach it once more to prove what varies.`,
      );
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
  const version = (skill.versions || []).find(
    (each) => each.version === run.skill_version,
  );
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
    const summary = await ask({
      kind: "summary",
      since: midnight.toISOString(),
    });
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
  tabHere = {
    tabId: tab?.id ?? null,
    host: hostOf(tab?.url || ""),
    url: tab?.url || "",
  };
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
  lastThread = thread;
  show(thread);
}

/** The last thread the server handed over, so a draw that is not from the
 * server has something true to build on. */
let lastThread = null;

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

/** What the cluster was last drawn from, so an unchanged one is left alone. */
let panesDrawn = null;

/** The element the navigation lives in, made once.
 *
 * The strip is rebuilt from the worker's status every couple of seconds. The
 * navigation is not: it is handed to the strip as this element, so redrawing
 * the line around it cannot replace the button somebody is reaching for.
 */
let navSlot = null;
function theNav() {
  if (!navSlot) navSlot = document.createElement("div");
  return navSlot;
}

/** Draw the two tabs and hide whichever half is not showing.
 *
 * Its own painter, called from `render` and from the tabs themselves, because
 * switching pane changes nothing `show()`'s signature can see.
 */
function paintPanes() {
  // Everything open, not only what was MISSED.
  //
  // The count used to mean "arrived while you were not looking", which was the
  // right number when everything waiting was on Home and the badge only said
  // you had not been there. Home keeps one now, so what the badge is for is
  // the size of the queue behind the tray -- and a queue that counted only the
  // ones you had never seen would say six, then four, then nothing, while six
  // requests sat there unanswered.
  const missed = (lastStatus?.nudges || []).filter(
    (one) => one.state === "open",
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
  theNav().replaceChildren(
    panes(pane, {
      waiting: missed,
      onPick: (picked) => {
        // Two of the four are places and two are things to do. History is an
        // overlay you close and come back from -- a third pane is somewhere a
        // person can be left, and coming back tomorrow to find the panel
        // showing last week is how a surface stops being about now.
        if (picked === "history") return void openHistory();
        if (picked === "pending") return void theBacklog();
        if (picked === "new") return void freshThread();
        if (picked === pane) return;
        if (picked === "chat") return void goToTheConversation();
        pane = picked;
        paintPanes();
      },
    }),
  );
  showPane();
}

/** What this browser has done lately, over the top of what you were doing.
 *
 * Fetched on the press rather than kept fresh in the background: it is a
 * glance, and a panel that polled a list nobody has open would be spending a
 * request every two seconds on a screen that is not on screen.
 *
 * A failure is said in the overlay itself. The alternative -- opening an empty
 * one -- reports "nothing has happened" when what is true is "this browser
 * could not ask", and those are different facts.
 */
async function openHistory() {
  const over = $("history");
  over.hidden = false;
  over.replaceChildren();
  let runs = [];
  try {
    runs = (await ask({ kind: "recent-runs", limit: K_HISTORY })) || [];
  } catch (error) {
    const said = document.createElement("p");
    said.className = "detail";
    said.textContent = error.message;
    over.append(said);
    return;
  }
  over.dataset.kind = "history";
  over.replaceChildren(
    history(runs, {
      onClose: () => {
        over.hidden = true;
        over.replaceChildren();
      },
    }),
  );
}

/** The backlog, over whatever you were doing.
 *
 * Drawn from the status this panel already has rather than fetched: these are
 * this browser's own offers, held in `chrome.storage`, and the panel is the
 * same browser. Nothing to wait for, so it opens instantly -- which is what
 * makes it somewhere to glance rather than somewhere to go.
 */
function theBacklog() {
  // The same slot history uses. One overlay at a time is the whole point of an
  // overlay, and a second container would be a second thing to remember to
  // hide.
  const over = $("history");
  const open = (lastStatus?.nudges || []).filter((one) => one.state === "open");
  const drawn = pending(open, {
    onPress: answered,
    onClose: () => {
      over.hidden = true;
      over.replaceChildren();
    },
  });
  if (!drawn) return;
  // Which overlay this is, so the stylesheet can give a queue the height it
  // needs without giving history the same.
  over.dataset.kind = "pending";
  over.hidden = false;
  over.replaceChildren(drawn);
  // The focus goes with it, or the escape key this listens for lands on
  // whatever was focused behind the overlay.
  drawn.tabIndex = -1;
  drawn.focus?.();
}

/** How many runs the overlay asks for. The console is where a log is read. */
const K_HISTORY = 12;

/** A conversation somebody deliberately started.
 *
 * The thread is otherwise one continuous conversation per operator, which is
 * the right default -- a question about a run this morning belongs with the
 * run. This is for when they have finished with that and are starting
 * something else, and it puts them on it: a new thread drawn behind the pane
 * they are not looking at is a press that appears to do nothing.
 */
async function freshThread() {
  try {
    const made = await ask({ kind: "new-thread" });
    if (made?.id) threadId = made.id;
  } catch (error) {
    $("thread-note").textContent = error.message;
  }
  pane = "chat";
  paintPanes();
  drawn = null;
  await conversation();
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

/** Show the conversation, redrawn, at the end of it.
 *
 * One way to get there, because there are now two ways to be sent: picking the
 * tab, and pressing a card whose answer is a question rather than a run.
 *
 * The second is what this was extracted for. A press on the Home pane wrote
 * `Customer Type takes 4 characters. What should it be?` into the thread and
 * left the operator looking at Home, where no part of it is visible -- the
 * question was asked, correctly, into a pane nobody had been taken to. Seen on
 * the deployment 2026-09-18, twice, and it reads exactly like nothing
 * happened.
 *
 * `drawn = null` because the guard that stops a redraw replacing a composer
 * somebody is typing in also stops the first draw after arriving here.
 *
 * Reading the thread now rather than up to five seconds from now: the poll
 * runs only while Chat is showing, so arriving is exactly when it is most
 * likely to be stale. And the scroll is forced -- arriving at a conversation
 * means arriving at the end of it, which is where the question is.
 */
function goToTheConversation() {
  pane = "chat";
  paintPanes();
  drawn = null;
  // Twice, and both are needed. Now, so the switch lands at the end of what is
  // already drawn rather than at the top of it -- a fetch away is long enough
  // to read as a jump. And again when the thread comes back, because the
  // message somebody is being sent here to read is one that was not on screen
  // when the first scroll ran.
  toTheNewest(true);
  void conversation().then(() => toTheNewest(true));
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
  // The composer is not in this list. One box, always there: an operator who
  // thinks of something while looking at their cards should not have to find
  // the other tab before they can say it -- and a question from a run arrives
  // in the conversation, so the box they answer in belongs under their hand
  // wherever they are standing.
  for (const id of ["thread", "here"]) $(id).hidden = pane !== "chat";
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
    .map(
      (nudge) =>
        `${nudge.id}:${nudge.state}:${nudge.missed ? "m" : ""}:${nudge.k ?? ""}`,
    )
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
  const missed = (lastStatus?.nearMisses || [])
    .map((one) => `${one.triggerId}:${one.at}`)
    .join(",");
  const asking = (lastStatus?.waiting || []).map((one) => one.id).join(",");
  // And the wait on a mailbox, which changes with the CLOCK rather than with
  // anything said. Everything else in this signature is a thing that happened;
  // this one is a thing that is still happening, and a line reading "last read
  // 40s ago" that only redraws when somebody speaks is a line that lies for as
  // long as the conversation is quiet -- which is the whole of the time it is
  // on screen. The look's own timestamp is what moves it: once per look, not
  // once per poll.
  const waitingOn = `${lastStatus?.mail?.awaiting?.at || ""}:${lastStatus?.mail?.lookedAt || ""}:${lastStatus?.mail?.looking ? "r" : ""}`;
  const now = `${thread.id}:${(thread.messages || []).map((message) => message.id).join(",")}|${mine}|${answerSeen}|${missed}|${asking}|${waitingOn}|${hostOf(tabHere.url || "")}`;
  if (now === drawn) return;
  if (!asked && drawn !== null && document.activeElement?.tagName === "INPUT")
    return;
  drawn = now;
  if (thread !== lastThread && (thread.messages || []).length)
    lastThread = thread;
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
      (nudge) =>
        nudge.state !== "open" &&
        Date.now() - (nudge.endedAt || 0) < JUST_ENDED_MS,
    ),
    answer: lastStatus?.answer || null,
    nearMisses: lastStatus?.nearMisses || [],
    waiting: lastStatus?.waiting || [],
    // Which system the operator is actually looking at, so an offer about
    // another one keeps its words and loses its buttons.
    here: hostOf(tabHere.url || ""),
    // The sentence that has been sent and not yet answered, so the panel shows
    // it the instant it leaves rather than when the reply lands. Named apart
    // from `waiting`, which is the list of fires waiting on somebody.
    sending: sendingNow,
    // The mail this browser sent and is waiting on, and whether it is reading
    // a mailbox at this instant. The conversation is where the draft was read
    // and approved, so the conversation is where the waiting belongs.
    mail: lastStatus?.mail || null,
  };
  openOffers = (thread.messages || []).filter(
    (message) =>
      ["offer", "mail_match"].includes(message.decision?.kind || "") &&
      !alreadyAnswered(thread.messages).has(message.decision.candidate_id),
  ).length;
  // The runs the conversation can draw under a message that names one.
  //
  // The ledger has had this branch since the skills path existed and it has
  // never fired, because nothing ever passed a map: `runs.get?.(run_id)` on
  // `undefined` is silently nothing. So a thread that said "Running X…" said
  // only that, and what came of it was on the other pane.
  //
  // Built from the two runs this browser actually holds -- the one performing
  // and the one that just finished -- rather than fetched: those are the two a
  // conversation can be about, and a map of every run this tenant ever did
  // would be a page load to draw one card.
  const runs = new Map();
  for (const one of [lastStatus?.performing, lastStatus?.finished]) {
    const id = one?.run?.id || one?.runId || one?.id;
    if (!id) continue;
    runs.set(
      id,
      one === lastStatus?.finished
        ? finished({ finished: one })
        : performing({ performing: one }),
    );
  }
  $("said").replaceChildren(ledger(thread, local, { onPress: answered, runs }));
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
 * The post answers with the whole thread, so the SETTLED state re-renders from
 * the answer rather than being appended locally: what stays on screen is what
 * the server recorded, not a guess at it. What is drawn in the meantime is
 * marked as not-yet-answered and replaced wholesale when the answer lands, so
 * the two can never disagree.
 */
async function say(text) {
  if (!threadId) return conversation();
  // Said from Home, read in the conversation. The box is under their hand on
  // both panes; the answer to what they said is only in one of them, and a
  // reply nobody is shown is a reply nobody reads.
  if (pane !== "chat") {
    pane = "chat";
    paintPanes();
  }
  // Their words, on screen, now.
  //
  // What a sentence costs varies from nothing to several seconds -- an answer
  // to a standing question is decided without a model call, and a sentence the
  // resolver has to place is two calls and a retrieval. For that whole stretch
  // the box emptied and the panel showed exactly what it showed before, so the
  // one thing the operator knows for certain -- that they pressed send -- was
  // the one thing nothing on screen agreed with.
  //
  // Drawn from what is already held rather than fetched: this is the thread
  // the reply will arrive in, plus the line they just wrote, plus a mark that
  // something is being worked out. The server's answer replaces all of it a
  // moment later, so nothing here is a claim about what was decided.
  thinking(text);
  let answered;
  try {
    // `tabId` so an offer the sentence turns into is drawn beside the tab the
    // operator is working in -- `show` only draws an OPEN nudge for this tab.
    answered = await ask({
      kind: "thread-say",
      threadId,
      text,
      tabId: tabHere.tabId,
    });
  } catch (error) {
    $("thread-note").textContent = error.message;
  }
  // Cleared BEFORE the draw, not after it.
  //
  // With this in a `finally` the server's answer was drawn while the echo was
  // still set, so the sentence appeared twice -- once as the thing that landed
  // and once as the thing still in flight -- until some later poll happened to
  // redraw. And a spinner left turning after a failure is the panel lying
  // about what it is doing, so this runs on that path too.
  sendingNow = null;
  if (answered) show(answered, { asked: true });
  // And if that answer was the last one, go and watch it.
  //
  // The run starts in the worker the moment the reply lands, and the card that
  // says what it is doing is drawn on Home -- so answering the last question
  // left the operator sitting in the conversation while the job they had just
  // finished authorising ran somewhere they were not looking. The outbound
  // half of this walk was built and the return half was not.
  if (startedByTheAnswer(answered)) goToTheRun();
}

/** Whether the reply to that sentence set a job running.
 *
 * `resume` is the door's word, and it is the door's to give -- the same field
 * the worker starts the run on. Read here rather than inferred from the text,
 * for the reason the worker reads it: this browser must not decide that a
 * press was implied.
 */
function startedByTheAnswer(thread) {
  for (const message of [...(thread?.messages || [])].reverse()) {
    if (message.speaker !== "assistant") continue;
    const decision = message.decision || {};
    return Boolean(decision.kind === "job" && decision.resume);
  }
  return false;
}

/** Show the half of the panel a run is drawn in.
 *
 * The mirror of `goToTheConversation`, and it exists for the same reason: a
 * transition with only an outbound half leaves somebody somewhere they cannot
 * see what they just did.
 */
function goToTheRun() {
  pane = "home";
  paintPanes();
  drawn = null;
  void refresh();
}

/** The sentence just sent, and the fact that an answer is being worked out.
 *
 * Held here rather than pushed into the thread: the thread is the server's
 * record of what was decided, and this is neither decided nor the server's.
 * `show` folds it in and the next draw from the server drops it.
 */
let sendingNow = null;

function thinking(text) {
  sendingNow = { text, at: new Date().toISOString() };
  // Past the signature guard, which is computed from what the SERVER holds --
  // and nothing the server holds has changed yet, which is precisely the case
  // this exists for.
  drawn = null;
  show(lastThread || { id: threadId, messages: [] }, { asked: true });
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
  // The same yes, for an offer that cannot simply run. Nothing starts: the
  // question lands in this conversation, the operator answers it in words, and
  // the answer that completes the set starts the job on the press they have
  // just given. The card draws no boxes for exactly this reason.
  if (answer === "ask-about-offer") return askAboutOffer(message, button);
  // The mail to whoever asked, sent or let go. Nothing leaves the mailbox
  // without this press, and this press sends nothing but the words already on
  // screen: the backend re-reads them from the thread.
  if (answer === "send-draft") return sendTheDraft(message, button);
  if (answer === "drop-draft") return dropTheDraft(button);
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
  if (decision.kind === "mail_match")
    return firedFromMail(decision, answer, button, values);
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
      said(
        got.ok
          ? "started \u2014 watching it below"
          : got.error || "nothing started",
      );
    }
  } catch (error) {
    said(error.message);
  }
  await refresh();
  drawn = null;
  await conversation();
}

/** Send the drafted mail, having read it.
 *
 * The id and not the words. What goes out is what the backend put in front of
 * the operator, read back from their own thread -- so the mail that leaves and
 * the mail that was read are the same by construction rather than by this
 * panel being careful.
 */
async function sendTheDraft(message, button) {
  button.disabled = true;
  try {
    const got = await ask({
      kind: "send-draft",
      threadId,
      messageId: message.id,
    });
    said(
      got.ok
        ? got.sent_to
          ? `asked ${got.sent_to}`
          : "nothing was sent"
        : got.error || "nothing was sent",
    );
  } catch (error) {
    said(error.message);
  }
  drawn = null;
  await conversation();
}

/** "No, I'll ask them myself."
 *
 * Nothing is reported and nothing is stored: the draft was an offer to write,
 * and declining to write a mail is not an event worth a row. The words stay in
 * the thread, because they were said.
 */
async function dropTheDraft(button) {
  button.disabled = true;
  said("left it with you");
}

/** An offer that needs something decided, handed to the conversation.
 *
 * The offer stays open in the worker rather than being reported answered: it
 * has not been accepted or dismissed, it has been taken up, and the thing that
 * ends it is the run that starts when the last question is answered. Reporting
 * a fate here would close it under somebody mid-sentence.
 */
async function askAboutOffer(nudge, button) {
  button.disabled = true;
  try {
    const got = await ask({ kind: "ask-about-offer", nudgeId: nudge.id });
    said(got.ok ? got.asked || "asked below" : got.error || "nothing to ask");
  } catch (error) {
    said(error.message);
  }
  await refresh();
  // And take them to it. The question is asked in the conversation, the card
  // they pressed is on Home, and writing the one without going to the other is
  // indistinguishable from nothing happening.
  goToTheConversation();
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
    said(
      got.run_id
        ? "started \u2014 watching it below"
        : "declined \u2014 nothing ran",
    );
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
    button.textContent = "Always on this page";
    said(got.error || "no rule was made");
  } catch (error) {
    button.disabled = false;
    button.textContent = "Always on this page";
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
    const fired = await ask({
      kind: "watch-fire",
      offerId: decision.offer_id,
      values,
    });
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
  return ask({
    kind: "run-skill",
    skillId,
    parameters,
    deviceId,
    intent,
    version,
  });
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
      frame.contentWindow?.postMessage(
        { kind: "sro.credential", token },
        origin,
      );
      return;
    }
    if (event.data?.kind === "sro.credential.ok")
      $("console-note").textContent = "";
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
  where.textContent =
    "Put that in the console's environment (frontend/.env.local) and restart it.";

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
    if (message?.kind !== "status" || document.visibilityState !== "visible")
      return;
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

/** Whether this document still belongs to the extension that is running.
 *
 * An extension that reloads -- a developer pressing the button, or Chrome
 * applying an update -- orphans every page the old one had open. This panel
 * keeps running the old code and `chrome.runtime.id` goes undefined: the port
 * cannot be reopened, no message reaches the new worker, and every call fails
 * with "Extension context invalidated". The panel does not look broken. It
 * looks like a panel where nothing is happening.
 *
 * Measured on 2026-09-17 and 18: four mail offers were made, kept, and
 * badged, and the operator watched a panel showing two questions from eight
 * hours earlier. The offers appeared the instant the panel was reopened by
 * hand. Everything under it worked; the window onto it had been dead since
 * the first reload.
 */
const stillOurs = () => Boolean(chrome.runtime?.id);

/** Say so, and offer the one thing that fixes it.
 *
 * Reloaded outright when nobody is mid-sentence, because a panel that cannot
 * hear the worker has nothing to lose by starting again -- and left to a press
 * when they are, because what they typed is theirs and a reload eats it.
 */
function orphaned() {
  const typed = $("ask-bar")?.querySelector("textarea, input");
  if (!typed || !typed.value.trim()) {
    location.reload();
    return;
  }
  // Its own line, in the place the panel already keeps for "this browser and
  // this deployment cannot talk to each other".
  const holder = $("console-refused");
  if (!holder || !holder.hidden) return;
  holder.hidden = false;
  holder.replaceChildren();
  const note = document.createElement("p");
  note.className = "note";
  note.textContent =
    "AI-SRO was updated and this panel is the old one — nothing here is live any more.";
  const again = document.createElement("button");
  again.type = "button";
  again.textContent = "Reopen it";
  again.addEventListener("click", () => location.reload());
  holder.append(note, again);
}

setInterval(() => {
  if (document.visibilityState !== "visible") return;
  if (!stillOurs()) return orphaned();
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
