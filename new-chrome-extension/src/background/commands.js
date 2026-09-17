// What the backend can ask this browser to do, and the answers it gets.
//
// Every command answers exactly once, including with an error: a run whose
// command is never answered is failed by the backend as an unreachable device,
// which is a much worse story than "the control was not there".
//
// The failure kinds are not decoration. `drivers.py` sorts them into two piles:
// `timeout`, `no_tab_for_system`, `no_tab_for_origin`, `focus_not_permitted`
// and `aborted` mean there was no browser to act in, and a skill is not
// demoted for them; anything else is a fact about the page, and a skill that
// keeps producing one has drifted. Answering "control_not_found" when the
// laptop was simply closed is how a working skill gets demoted for somebody
// going to lunch.

import { pointAt } from "./pointing.js";
import {
  csrfTokenInPage,
  requestedWithInPage,
  performAtInPage,
  performInPage,
  sendInPage,
  viewportInPage,
} from "./in-page.js";
import { hideDriving, showDriving } from "./showing.js";
import { state } from "./state.js";

/** Runs whose abort has arrived. Their later commands are refused rather than
 * performed; work already inside the page cannot be recalled, so this is a
 * floor rather than a stop button.
 *
 * A module variable, like the socket itself: both die with this worker, and a
 * run cannot outlive the channel it was sent down. */
const aborted = new Set();

/** Tabs being driven right now, and until when.
 *
 * A replay's own clicks and the requests they set off must not arrive in the
 * evidence plane as though the operator had done them: the miner would see the
 * task being done over and over, offer it as a candidate, and learn from a
 * robot imitating a person. The window extends past the command because the
 * page's own calls follow the click rather than accompany it. */
const driving = new Map();

const SETTLE_MS = 2000;

/** The run this browser is performing, and when it was last asked to do
 * something for it.
 *
 * The envelope has always carried `run_id` and only `abort` ever read it. A
 * panel docked beside the page has to be able to say "a run is doing this" and
 * offer to stop it, and neither is answerable from the tab alone: one run
 * drives several tabs, and a tab is driven by at most one run at a time. */
let latest = null;

/** How long after the last command a run is still considered to be happening.
 * Longer than a step, shorter than an operator's patience -- a finished run
 * that goes on claiming the panel is worse than one that stops claiming it a
 * little early. Exported: `service-worker.js`'s `checkFinishing()` measures
 * the same quiet window against the storage-backed mirror below, and a second
 * constant there would be a second number to keep in step with this one. */
export const RUN_QUIET_MS = 30_000;

/** What this browser is performing right now, or null. */
export function performing() {
  if (!latest) return null;
  if (Date.now() - latest.at > RUN_QUIET_MS) {
    latest = null;
    return null;
  }
  return { runId: latest.runId, kind: latest.kind, since: latest.since };
}

/** What the backend told us about this step, where it told us anything.
 *
 * Read rather than required: an older backend sends neither, and a band that
 * says only "AI-SRO is working in this tab" is still the whole of the point.
 */
function told(command) {
  const said = command.payload || {};
  const of = {};
  if (said.skill) of.skill = said.skill;
  if (Number.isFinite(said.step)) of.step = said.step;
  if (Number.isFinite(said.of)) of.of = said.of;
  return of;
}

/** Put the band in whichever tab this step acts in, and take it away when the
 * run is over. */
async function announce(command, run) {
  if (command.kind === "abort") {
    for (const tabId of driving.keys()) await hideDriving(tabId);
    return;
  }
  const origin = command.payload?.origin || command.payload?.url;
  const tab = origin ? await tabOnOrigin(origin) : null;
  if (tab?.id === undefined || tab?.id === null) return;
  await showDriving(tab.id, {
    skill: run.skill,
    step: run.step,
    of: run.of,
    runId: run.runId,
    // The same window this worker calls a run quiet, so the page and the panel
    // stop saying it at the same moment rather than one outliving the other.
    quietMs: RUN_QUIET_MS,
  });
}

/** Stop a run from here.
 *
 * The same set the backend's own `abort` command fills, so this is not a second
 * mechanism: every later command for that run answers `aborted`, which
 * `drivers.py` sorts as "there was no browser to act in" rather than as a skill
 * that has drifted. What is already inside the page finishes -- nothing can
 * recall it -- so this stops the next step, which is what the button says.
 */
export function abort(runId) {
  if (!runId) return false;
  aborted.add(runId);
  if (latest?.runId === runId) latest = null;
  for (const tabId of driving.keys()) void hideDriving(tabId);
  return true;
}

let seq = 0;
const CALLS_KEPT = 60;
const driven = new Map();

/** What the page called while this run was driving it.
 *
 * The evidence plane drops these deliberately -- a replay's own traffic mined
 * as though a person had done it is the system learning a task from a robot
 * imitating one -- and that is right and stays. This is a different thing with
 * a different life: a handful of calls, in memory, for the length of a run,
 * so the run can be told whether the write it just made came back 201 or 409.
 *
 * Before it existed, every step of every run was judged by photographing the
 * screen and asking a model what it saw -- `verdict_by = screen` on all 67
 * steps this deployment has ever performed, the weakest and slowest rung of
 * the three the verifier documents. A status code is both cheaper and better
 * evidence: 84.24% against 70.04% over the 643 tasks of the WebVoyager
 * benchmark (arXiv:2410.00689, Table 1). The numbers here read 86.9/78.8
 * until 2026-09-15 and are in no version of that paper -- the backend's copy
 * of the same sentence was corrected a day earlier and this one was missed,
 * which is what a number copied into two languages does.
 *
 * Bounded per tab, and never written anywhere: this map is the whole of it.
 */
export function noteDriven(tabId, request) {
  if (tabId === null || tabId === undefined || !request) return;
  const kept = driven.get(tabId) || [];
  kept.push({
    method: request.method || "",
    url: request.url || "",
    status: request.status ?? null,
    started_at: request.started_at ?? Date.now() / 1000,
    // Which side of the command this call is on, and the only thing
    // `callsSince` compares. See `marks`.
    seq: ++seq,
    // What the warehouse answered a CREATE with, and only a create.
    //
    // A run that made three records has to be able to say which three, or
    // nobody can go and look at them -- and an undo, the day one exists, has
    // to address them by whatever the system called them. The identifier is
    // in the 201's own body and nowhere else this browser can see.
    //
    // Only 201, only the first `CREATED_BODY` characters, and already
    // redacted by the recorder that produced it. A page's ordinary 200s are
    // not kept: their bodies are lists, screens and customer data, and
    // nothing here needs them.
    body:
      request.status === 201
        ? asText(request.response_body).slice(0, CREATED_BODY)
        : null,
  });
  driven.set(tabId, kept.slice(-CALLS_KEPT));
}

const CREATED_BODY = 400;

/** A captured body as the text it was, or "" for one this browser never saw.
 *
 * The recorder wraps a body with what it did to it -- truncated, uninspectable,
 * redacted -- so the text is a field rather than the value itself, and a
 * caller reading it as a string gets `[object Object]` into a run record. */
function asText(body) {
  if (typeof body === "string") return body;
  const text = body?.text ?? body?.value ?? "";
  return typeof text === "string" ? text : "";
}

/** Where each run's counter stood when its last acting command went out.
 *
 * Not a clock. The backend sends `since` as the server's own epoch seconds
 * (`run_workflow.py`'s `sent_at`) and this browser's calls carry the
 * recorder's ISO strings, so the comparison that used to be here --
 * `"2026-09-14T19:41:09.469Z" >= 1789414869.469` -- is `false` for every call
 * ever made. `calls.since` therefore always answered `{calls: []}`, the
 * status rung never once fired in this deployment's 91 recorded steps, and
 * every step paid for a screenshot and a vision call on the rung the verifier
 * calls the weakest. `RunStep.made` is filled from the same answer, so a run
 * could not say which records it created either.
 *
 * Parsing the ISO string would fix the types and leave the worse half: two
 * clocks. A browser a few minutes fast would pass calls from before the
 * command was sent, and the verifier takes the first method-and-shape match
 * walking backwards -- on a repeating job, item 2 would be held by item 1's
 * 201 and would report item 1's identifier as what it made. A counter this
 * worker increments has one owner and no clock at all.
 */
const marks = new Map();

/** Commands that make the page do something, so the calls after one are the
 * calls it made because of it. `calls.since` and `screenshot` are the run
 * looking, and must not move the mark they are about to read. */
const ACTS = new Set([
  "ui.perform",
  "ui.perform_at",
  "http.send",
  "navigate",
  "tab.open",
]);

/** The calls this run's tab made since its last acting command, newest last. */
function callsSince(runId) {
  const tabId = runId && latest?.runId === runId ? latest.tabId : undefined;
  if (tabId === undefined) return { ok: true, result: { calls: [] } };
  const after = marks.get(runId) ?? 0;
  const calls = (driven.get(tabId) || []).filter(
    (call) => call.seq > after && call.status !== null,
  );
  return { ok: true, result: { calls } };
}

export function isDriving(tabId) {
  const until = driving.get(tabId);
  if (until === undefined) return false;
  if (until >= Date.now()) return true;
  driving.delete(tabId);
  return false;
}

function hold(tabId, ms = SETTLE_MS) {
  if (tabId === null || tabId === undefined) return;
  driving.set(tabId, Date.now() + ms);
}

const failure = (kind, detail) => ({ ok: false, error: { kind, detail } });

/** Which of the two is missing, because they are different problems: a browser
 * with nothing open at all, and one where the system this run is for is not
 * among what is open. */
const noPage = (origin) =>
  origin
    ? `no tab is open on ${origin}, which is the system this run is for`
    : "this browser has no ordinary page open";

/**
 * The tab a command acts in.
 *
 * Named by the run where the run knows: `origin` is the system the skill was
 * taught on, and an operator's Chrome has a dozen tabs of which exactly one is
 * that system. Guessing there is not a smaller version of choosing -- the
 * frontmost page is as likely to be somebody's email, and a warehouse gesture
 * performed on it is a real thing that happened to a real person.
 *
 * Only where the run has no origin to give -- a skill taught entirely through
 * the interface, with no call recorded to name the host -- does this fall back
 * to the page in front of the operator, which is the best a guess can do.
 *
 * `no_tab_for_system` when there is none. A browser showing only its own
 * settings pages, or none on the system this run is for, is a device problem
 * rather than a page that changed, and the two are counted differently.
 */
async function drivenTab(origin) {
  const usable = (tab) => tab?.url && /^https?:/.test(tab.url);

  if (origin) {
    const onIt = (await chrome.tabs.query({ url: `${origin}/*` })).filter(
      usable,
    );
    if (!onIt.length) return null;
    // The visible one first: a run drives what the operator can see going on,
    // and a background tab cannot be photographed for the rung that looks.
    return onIt.find((tab) => tab.active) || onIt[0];
  }

  const inFront = await chrome.tabs.query({
    active: true,
    lastFocusedWindow: true,
  });
  if (usable(inFront[0])) return inFront[0];

  // Any ordinary tab rather than none at all: the operator may be looking at a
  // settings page while the system sits in the next tab.
  const all = await chrome.tabs.query({ windowType: "normal" });
  return (
    all
      .filter(usable)
      .sort((a, b) => (b.lastAccessed || 0) - (a.lastAccessed || 0))[0] || null
  );
}

/** A tab already on this origin, because the point of sending from the browser
 * is the session that origin's cookies carry. */
async function tabOnOrigin(url) {
  let origin;
  try {
    origin = new URL(url).origin;
  } catch {
    return null;
  }
  const tabs = await chrome.tabs.query({ url: `${origin}/*` });
  return tabs.find((tab) => /^https?:/.test(tab.url || "")) || null;
}

/** Run one of the page-realm functions in EVERY frame, and take the first
 * frame that answered with something.
 *
 * For the live headers, and measured on the real system 2026-09-16. Blue
 * Yonder's portal is a shell that hosts the application in an iframe
 * (`/portal/page?libraryContext=…`), and BOTH have an `Ext`. The shell's
 * `Ext.Ajax.defaultHeaders` carries only `Accept`; the iframe's carries
 * `CSRF-ENCRYPT-TOKEN`, 88 characters of it. Reading the top frame alone
 * therefore finds an Ext, finds no token, and answers `unreachable:
 * CSRF-ENCRYPT-TOKEN is not on this page` -- which failed every replay of
 * every Blue Yonder write, with the token sitting one frame down.
 *
 * First non-null and not a merge: a header has one value, and two frames that
 * disagree are two sessions, not one to pick a winner from by rule. Frames
 * come back in the order Chrome enumerates them, top first, so a page that
 * does put it on the shell keeps behaving exactly as it did.
 */
async function inEveryFrame(tabId, func, args, world = "MAIN") {
  const answers = await chrome.scripting.executeScript({
    target: { tabId, allFrames: true },
    world,
    func,
    args,
  });
  // A frame that threw is worth saying out loud even when another frame
  // answers: a page where the injected code is broken is a page every later
  // step will fail on, and the first sign of it was three hours of silence.
  for (const answer of answers) {
    if (answer?.error) {
      console.warn("[sro] the injected command threw in a frame", answer.error);
    }
  }
  for (const answer of answers) {
    if (answer?.result !== null && answer?.result !== undefined)
      return answer.result;
  }
  return null;
}

/** Run one of the page-realm functions and hand back what it answered. */
async function inPage(tabId, func, args, world = "MAIN") {
  const [answer] = await chrome.scripting.executeScript({
    target: { tabId },
    world,
    func,
    args,
  });
  return whatItSaid(answer);
}

/** One injection's answer, with a throw treated as a throw.
 *
 * Since Chrome 117 an injected function that throws does not reject the
 * promise: it resolves with `{result: undefined, error}`. Reading only
 * `.result` turns every error inside the page into no answer at all, and "the
 * page did not answer" is what the run then says -- a sentence that reads like
 * a page problem for what is a bug in the injected code.
 *
 * Measured on the deployment across 2026-09-16 and 17: every UI step ever
 * attempted on the warehouse host failed that way, for three hours of looking
 * at pages, tabs and content-security policies. The page was fine. The
 * injected function was calling a helper that does not exist inside it.
 */
function whatItSaid(answer) {
  const blew = answer?.error;
  if (blew) {
    throw new Error(
      `the injected command threw in the page: ${blew.message || blew}`,
    );
  }
  return answer?.result;
}

/** PNG dimensions, read out of the file rather than guessed.
 *
 * Unused for the vision rung -- it is told the CSS viewport, which is the space
 * it answers coordinates in -- but the picture's own size is what proves the
 * capture is not empty. */
function isPng(bytes) {
  return bytes.length > 24 && bytes[0] === 0x89 && bytes[1] === 0x50;
}

function bytesOf(dataUrl) {
  const binary = atob(dataUrl.slice(dataUrl.indexOf(",") + 1));
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

async function uiPerform(payload, runId) {
  const tab = await awake(await tabForRun(payload, runId));
  if (!tab) return failure("no_tab_for_system", noPage(payload.origin));
  hold(tab.id);
  const frameId = await frameHolding(tab.id, payload);
  const answer =
    frameId === undefined
      ? await inPage(tab.id, performInPage, [payload])
      : await inFrame(tab.id, frameId, performInPage, [payload]);
  hold(tab.id);
  if (answer?.ok) await reacted(tab.id, payload.action);
  // What "the page did not answer" actually means, said where it is known.
  //
  // It means the injection produced no result: the frame is gone, the tab was
  // asleep, the page went somewhere else mid-command. It does NOT mean the
  // control was missing -- `performInPage` answers that itself, by name. The
  // two read identically on a run card, and on 2026-09-16 three runs failed
  // this way while an operator and I read it as "the locator did not match"
  // and went looking at the wrong thing. So the tab says who it was.
  return answer || failure("not_actionable", await didNotAnswer(tab, frameId));
}

/** The page the command was performed against, for a failure that has to be
 * read by somebody who cannot see it -- and whether anything can be run in it
 * at all.
 *
 * "The page did not answer" has two causes that want two different people to
 * do two different things, and they are indistinguishable from the run's side:
 * the command ran and produced nothing, or nothing ran. A page whose own
 * content-security policy refuses injected script gives the second, silently
 * and with no error, and on this deployment every UI step ever attempted on
 * the warehouse host has failed while the ones on the mailbox held.
 *
 * So the failure asks. One trivial function in each world -- the page's own
 * (`MAIN`, where the application's `Ext` lives and where a locator by
 * component has to run) and the extension's (`ISOLATED`, which a page's policy
 * cannot touch) -- and the answer says which of them will run anything.
 *
 * Only on the failure path, so an ordinary step pays nothing for it.
 */
async function didNotAnswer(tab, frameId) {
  const where = String(tab.url || "").slice(0, 120);
  const frame = frameId === undefined ? "the page" : `frame ${frameId}`;
  const [main, isolated] = await Promise.all([
    canRun(tab.id, "MAIN"),
    canRun(tab.id, "ISOLATED"),
  ]);
  const worlds =
    main && isolated
      ? "script runs in it"
      : isolated
        ? "nothing runs in the page's own world -- its content-security policy refuses injected script"
        : main
          ? "only the page's own world runs script"
          : "no script runs in it at all";
  return `${frame} at ${where} did not answer (status ${tab.status || "unknown"}; ${worlds})`;
}

/** Whether a trivial function runs in this tab, in that world. */
async function canRun(tabId, world) {
  try {
    const [answer] = await chrome.scripting.executeScript({
      target: { tabId },
      world,
      func: () => true,
    });
    return answer?.result === true;
  } catch {
    return false;
  }
}

/** A tab that can be injected into, waking it first if Chrome has put it away.
 *
 * Chrome discards background tabs under memory pressure -- Memory Saver does
 * it on a timer -- and a discarded tab is still in `chrome.tabs.query` with
 * its url and title. Injecting into one returns NOTHING: no error, no result,
 * which arrives at the run as "the page did not answer" and reads like a
 * missing control. An operator whose warehouse tab has been sitting behind
 * their mail for an hour has exactly this tab.
 *
 * Reloaded and waited for rather than skipped, because it is the right tab:
 * the alternative is opening a second one at the same origin, which leaves the
 * operator with two and loses whatever was on the screen in the first.
 */
async function awake(tab) {
  if (!tab || !tab.discarded) return tab;
  // Listening BEFORE the reload, not after it. A tab that comes back quickly
  // reports itself complete while the reload call is still being awaited, and
  // a watcher registered afterwards waits out its whole timeout for an event
  // that has already happened -- twenty seconds added to a step for a tab that
  // was ready in one.
  const ready = settled(tab.id);
  try {
    await chrome.tabs.reload(tab.id);
  } catch {
    return tab;
  }
  return (await ready) || (await chrome.tabs.get(tab.id).catch(() => tab));
}

/** The tab this run acts in, opening the screen it was taught on if need be.
 *
 * A skill taught by clicking names no URL on any step, so until the version
 * recorded where the demonstration began, a run could only be performed by an
 * operator who had already navigated to the right screen themselves -- and one
 * who had not read thirteen `control_not_found` lines that said nothing about
 * being on the wrong page.
 *
 * A new tab rather than navigating the one in front. The operator is looking at
 * that tab; taking it out from under them to do something they did not ask to
 * watch is the kind of thing that gets an extension uninstalled. A new tab is
 * also the honest picture of what is happening: a second window on the system,
 * doing the task, next to the one they are working in.
 *
 * Decided once per run and remembered, because a task changes the page it is on
 * -- a modal opens, a fragment changes -- and asking again at every step would
 * open a fresh tab in the middle of the form it had just filled in.
 */
async function tabForRun(payload, runId) {
  if (runId && latest?.runId === runId && latest.tabId !== undefined) {
    const known = await chrome.tabs.get(latest.tabId).catch(() => null);
    // The pinned tab serves the run only while it is on the origin this step
    // names. A job that crosses from one system to another names the second
    // origin on its later steps, and performing those in the first system's
    // tab is the cross-application hand-off failure the origin exists to stop.
    if (known && (!payload.origin || originOf(known.url) === payload.origin))
      return known;
  }

  let tab = await drivenTab(payload.origin);
  const wanted = opensFor(payload);
  if (wanted && (!tab || !samePage(tab.url, wanted))) {
    const opened = await openAt(wanted);
    if (opened) tab = opened;
  }

  if (tab && runId && latest?.runId === runId)
    latest = { ...latest, tabId: tab.id };
  return tab;
}

/** The page a navigate may open a tab at, or null.
 *
 * `opensFor` says the same thing for a perform, about `starts_on`. This one is
 * about the url the navigate itself carries: http or https, and on the origin
 * the command names. A navigate to a `chrome://` page or to another system is
 * not this run's business.
 */
export function openFor(payload) {
  const wanted = payload?.url;
  if (!wanted || !/^https?:/.test(wanted)) return null;
  if (payload.origin && originOf(wanted) !== payload.origin) return null;
  return wanted;
}

/** The page this step may open a tab at, or null.
 *
 * `starts_on` only ever speaks for the step's OWN system. A job that crosses
 * from one to another used to send every step the page the run BEGAN on, so a
 * step whose origin was the warehouse arrived carrying the operator's mail --
 * and the caller found their warehouse tab, threw it away because it was not
 * on that page, opened the mail, and clicked a warehouse control there. The
 * step failed `not_actionable: the page did not answer`, on the real
 * deployment, 2026-09-15.
 *
 * The backend now sends it for the first step alone. This is the same rule
 * said again where the tab is actually chosen, because a stale build of either
 * side must not be able to drive somebody's browser into the wrong system.
 */
export function opensFor(payload) {
  const wanted = payload?.starts_on;
  if (!wanted) return null;
  if (payload.origin && originOf(wanted) !== payload.origin) return null;
  return wanted;
}

function originOf(url) {
  try {
    return new URL(url).origin;
  } catch {
    return null;
  }
}

/** Two URLs that are the same screen.
 *
 * Compared without the query, because a session id or a site code in it is not
 * what makes this the Work Areas page -- and with the fragment, because in an
 * application that routes on the fragment it is the only thing that says which
 * screen this is at all.
 */
export function samePage(a, b) {
  const parse = (raw) => {
    try {
      const url = new URL(raw);
      return `${url.origin}${url.pathname}${url.hash}`.replace(/\/+$/, "");
    } catch {
      return null;
    }
  };
  const one = parse(a);
  return one !== null && one === parse(b);
}

/** Open a tab on that screen and wait for it to finish loading.
 *
 * In the background: the run is not asking for the operator's attention, and a
 * tab that stole focus mid-sentence would be worse than the problem it solves.
 * The band the page shows is what tells them it is there.
 */
async function openAt(url) {
  let tab;
  try {
    tab = await chrome.tabs.create({ url, active: false });
  } catch {
    return null;
  }
  const ready = await settled(tab.id);
  return ready || tab;
}

const OPENS_WITHIN_MS = 20_000;

function settled(tabId) {
  return new Promise((resolve) => {
    let settledAlready = false;
    const done = (tab) => {
      if (settledAlready) return;
      settledAlready = true;
      chrome.tabs.onUpdated.removeListener(watch);
      clearTimeout(timer);
      resolve(tab);
    };
    const ignore = () => {};
    const watch = (id, change) => {
      if (id === tabId && change.status === "complete") {
        chrome.tabs.get(tabId).then(done, () => done(null));
      }
    };
    // A page that never reports complete is still worth acting on: the locator
    // says whether the control is there, and that is a better answer than a run
    // that failed because a third-party script kept a request open.
    const timer = setTimeout(() => done(null), OPENS_WITHIN_MS);
    chrome.tabs.onUpdated.addListener(watch);
    // And a tab that is ALREADY loaded answers now. Waiting for an `onUpdated`
    // that has already fired is how a page served from cache costs a step its
    // whole twenty seconds -- the listener above can only ever see what
    // happens after it is attached. Last, so `done` and `ignore` both exist.
    chrome.tabs.get(tabId).then((tab) => {
      if (tab?.status === "complete") done(tab);
    }, ignore);
  });
}

const REACTS_WITHIN_MS = 900;
const LOADS_WITHIN_MS = 8_000;
/** How long a single-page application is given to draw what it just routed to.
 * The route change is the decision, not the render. */
const PAINTS_WITHIN_MS = 300;

/** Let the page finish reacting before anybody looks at it.
 *
 * A click on Sign In is a form submit: the command returns the instant the
 * click dispatches, and the run then photographs a page that has not started
 * navigating yet. That is what happened on a real login -- username typed,
 * password typed from the vault, Sign In pressed, and the verifier reported
 * "the browser remains on the Keycloak login page with the sign-in form still
 * visible", because it was looking at the page as it had been a moment before.
 * The run stopped on a step that had in fact worked.
 *
 * Bounded twice. If nothing starts loading within `REACTS_WITHIN_MS` this
 * returns: a click that opens a menu navigates nowhere, and waiting on it
 * would add a second to every step of every run. Once something IS loading it
 * waits for complete, up to `LOADS_WITHIN_MS` -- a page held open by a
 * third-party script is still worth looking at, and the verifier says what it
 * sees either way.
 *
 * Not for typing. A keystroke does not submit anything, and a run that fills
 * six fields would pay the wait six times over for nothing.
 */
function reacted(tabId, action) {
  if (action === "type") return Promise.resolve();
  return new Promise((resolve) => {
    let loading = false;
    const done = () => {
      chrome.tabs.onUpdated.removeListener(watch);
      chrome.webNavigation?.onHistoryStateUpdated?.removeListener(routed);
      clearTimeout(quiet);
      clearTimeout(cap);
      clearTimeout(painting);
      resolve();
    };
    const watch = (id, change) => {
      if (id !== tabId) return;
      if (change.status === "loading") loading = true;
      else if (change.status === "complete" && loading) done();
    };
    // The screen changed without the browser navigating.
    //
    // A single-page application routes with `history.pushState`, and a tab
    // that never leaves its document never reports `loading` -- so on a
    // client-routed screen, which is most of a modern WMS, the wait above
    // sees nothing at all and the run photographs the page mid-render. This
    // is the same event the browser raises for the url in its own address
    // bar, so it costs no injection and no page-realm code.
    //
    // Then a short pause, because a route change is the application deciding
    // what to draw and not the drawing: resolving on the event itself would
    // move the "too early" problem rather than fix it.
    let painting = null;
    const routed = (details) => {
      if (details.tabId !== tabId || details.frameId !== 0) return;
      loading = true;
      clearTimeout(painting);
      painting = setTimeout(done, PAINTS_WITHIN_MS);
    };
    const quiet = setTimeout(() => {
      if (!loading) done();
    }, REACTS_WITHIN_MS);
    const cap = setTimeout(done, LOADS_WITHIN_MS);
    chrome.tabs.onUpdated.addListener(watch);
    chrome.webNavigation?.onHistoryStateUpdated?.addListener(routed);
  });
}

/** Which frame of the page holds this control.
 *
 * The recorder registers with `allFrames: true`, so a demonstration on a screen
 * the application renders inside an iframe -- a portal shell hosting a
 * configuration app, which is most enterprise WMS screens -- was recorded from
 * inside that frame. The driver injected into the top document only, where
 * neither the framework nor any of the recorded css paths exist, so every step
 * of every such skill answered `control_not_found` on a screen whose controls
 * were plainly visible. Looking in one frame and being taught in another is not
 * a locator problem, and no amount of re-teaching would have fixed it.
 *
 * A probe rather than a wider act: acting where it looked would click in every
 * frame that matched. `undefined` means "no frame claimed it" -- the top
 * document is asked anyway, so the answer is the same `control_not_found` it
 * would have given, with the same tried-locator list to read.
 */
async function frameHolding(tabId, payload) {
  let answers;
  try {
    answers = await chrome.scripting.executeScript({
      target: { tabId, allFrames: true },
      world: "MAIN",
      func: performInPage,
      args: [{ ...payload, probe: true }],
    });
  } catch {
    // A page that cannot be scripted at all. The single-frame attempt below
    // fails the same way and says so in the language the run already reads.
    return undefined;
  }
  return frameOf(answers);
}

/** The one frame that claimed the control, or `undefined`.
 *
 * None, or more than one, is `undefined`. A control that resolves in two frames
 * is not one this can pick between, and picking wrong would act on the wrong
 * half of a page carrying the same form twice.
 */
export function frameOf(answers) {
  const holding = (answers || []).filter((each) => each?.result?.ok);
  return holding.length === 1 ? holding[0].frameId : undefined;
}

async function inFrame(tabId, frameId, func, args, world = "MAIN") {
  const [answer] = await chrome.scripting.executeScript({
    target: { tabId, frameIds: [frameId] },
    world,
    func,
    args,
  });
  return whatItSaid(answer);
}

async function uiPerformAt(payload) {
  const tab = await awake(await drivenTab(payload.origin));
  if (!tab) return failure("no_tab_for_system", noPage(payload.origin));
  hold(tab.id);
  // The browser first. A point is a pixel in the top-level viewport, and only
  // the browser knows which renderer owns a pixel -- `executeScript` has to be
  // told which document to run in, which is a question the point does not
  // answer and which the frame lookup below gets wrong the moment an
  // application routes inside its own frame. `pointAt` dispatches the event
  // where a real mouse would arrive and lets Chrome route it.
  const driven = await pointAt(tab.id, payload);
  if (driven.ok || driven.error?.kind !== "cannot_drive_tab") {
    hold(tab.id);
    if (driven.ok) await reacted(tab.id, payload.action);
    return driven;
  }
  // Chrome allows one debugger per tab and somebody else has it -- DevTools,
  // almost always. The synthetic path is worse -- untrusted events, and a
  // frame lookup that is a guess -- and it is not nothing.
  let answer = await inPage(tab.id, performAtInPage, [payload]);
  // The point landed on a frame, so ask the frame.
  //
  // The picture the model was shown is the top document's viewport, and a
  // warehouse application inside an iframe puts every control in another
  // document: the point is right and the document is wrong. Rather than
  // refusing -- which made the rung that looks at a picture useless on the one
  // system it exists for -- the same question goes to that frame with the
  // point moved into its coordinates.
  //
  // Once. A frame inside a frame is answered by the same reply from the inner
  // one, and a loop that followed them would be a loop somebody has to bound
  // anyway; one hop covers an application in a frame, which is what this is.
  const frame = answer?.error?.frame;
  if (frame) {
    const inside = await frameShowing(tab.id, frame.src);
    if (inside === undefined) {
      return failure(
        "control_not_found",
        `that point is inside a frame this browser cannot reach (${frame.src || "no src"})`,
      );
    }
    answer = await inFrame(tab.id, inside, performAtInPage, [
      { ...payload, x: payload.x - frame.left, y: payload.y - frame.top },
    ]);
  }
  hold(tab.id);
  if (answer?.ok) await reacted(tab.id, payload.action);
  return (
    answer || failure("not_actionable", await didNotAnswer(tab, undefined))
  );
}

/** The id of the frame the top document pointed at, or `undefined`.
 *
 * Three ways, weakest last, because a frame's `src` ATTRIBUTE is the url it
 * was created with and not the url it is showing. Measured on the deployment,
 * 2026-09-17: the point landed on the application's frame, whose `src` still
 * named `#wm.config.warehouse.warehouse////` while the app had long since
 * routed to the Customer Types screen inside it. The exact match found
 * nothing, and a run that had reached the right page reported that it could
 * not reach the frame in front of it.
 *
 *  1. The url as it stands, which is right whenever the frame has not routed.
 *  2. The same document ignoring the query and the fragment -- a session
 *     token and an in-app route are exactly what change under a frame that
 *     has stayed where it is.
 *  3. The only child frame there is. A page with one frame and a point inside
 *     it has said which frame that is by arithmetic; a page with several gets
 *     `undefined` rather than a guess.
 */
async function frameShowing(tabId, src) {
  const frames =
    (await chrome.webNavigation.getAllFrames({ tabId }).catch(() => [])) || [];
  const children = frames.filter((one) => one.frameId !== 0);
  if (src) {
    const exact = children.find((one) => one.url === src);
    if (exact) return exact.frameId;
    const document_ = pageOf(src);
    const same = children.filter(
      (one) => document_ && pageOf(one.url) === document_,
    );
    if (same.length === 1) return same[0].frameId;
  }
  return children.length === 1 ? children[0].frameId : undefined;
}

/** A url without what identifies one visit to it: scheme, host and path. The
 * query holds the session token and the fragment holds the in-app route, and
 * both change under a frame that has not moved. */
function pageOf(url) {
  try {
    const { origin, pathname } = new URL(url);
    return `${origin}${pathname}`;
  } catch {
    return "";
  }
}

async function uiUrl(payload) {
  const tab = await drivenTab(payload.origin);
  if (!tab) return failure("no_tab_for_system", noPage(payload.origin));
  return { ok: true, result: { url: tab.url } };
}

/**
 * A picture of what the operator is looking at, and the names of the controls
 * on it.
 *
 * Always inline, which is what the vision rung asks for: it is looking at the
 * picture now, and a round trip through object storage to read back what it
 * just asked for is two more places for it to be delayed or lost. There is no
 * stored form of this command -- a run keeps no screens, so there would be
 * nothing to read a stored one back with.
 */
async function screenshot(payload) {
  const tab = await drivenTab(payload.origin);
  if (!tab) return failure("no_tab_for_system", noPage(payload.origin));
  // `captureVisibleTab` photographs whatever is active in the window, not the
  // tab it is handed. For a tab that is not the active one, the picture and
  // the coordinate space beside it would come from two different pages -- and
  // the model's answer, fed back as `ui.perform_at`, would land on the second.
  //
  // So the page has to be brought forward, and whether it may is the run's
  // decision rather than this browser's: `allow_focus` says the operator asked
  // for this and is watching. Without it the command is refused, because
  // taking somebody's screen while they are working in it is worse than a run
  // that did not finish.
  const visible = tab.active
    ? tab
    : await bringForward(tab, payload.allow_focus);
  if (!visible) {
    return failure(
      "focus_not_permitted",
      "the page to be driven is not the visible one, and this run may not bring it forward",
    );
  }

  // The names come from the DOM rather than from the picture: a control's own
  // name beats one inferred from pixels, and the redaction the backend runs
  // before anything reaches a model can only reason about text. Read from the
  // tab that was photographed, so the picture and the coordinates beside it
  // are the same page.
  const seen = (await inPage(visible.id, viewportInPage, [], "ISOLATED")) || {};

  let dataUrl;
  try {
    dataUrl = await chrome.tabs.captureVisibleTab(visible.windowId, {
      format: "png",
    });
  } catch (error) {
    // A tab that is not the visible one cannot be photographed, and Chrome
    // refuses on its own pages. Both mean there is no screen to look at.
    return failure(
      "no_tab_for_system",
      `this browser would not be photographed: ${error}`,
    );
  }

  const bytes = bytesOf(dataUrl);
  if (!isPng(bytes))
    return failure("no_tab_for_system", "the capture was not an image");

  return {
    ok: true,
    result: {
      image_base64: dataUrl.slice(dataUrl.indexOf(",") + 1),
      mime_type: "image/png",
      // The CSS viewport, not the picture's pixels: the model answers
      // coordinates in this space and `ui.perform_at` acts in it.
      width: seen.width || 0,
      height: seen.height || 0,
      text_digest: seen.digest || "",
    },
  };
}

/**
 * Take this browser somewhere else -- refused when that would take the screen
 * out from under the operator.
 *
 * `allow_focus` is the run's trigger saying it may: a task the operator started
 * and is watching may move their tab, one a cron or a mail relay started may
 * not. Refused rather than done anyway, and refused with the kind that tells
 * the backend no browser was available rather than that the page had changed.
 */
/**
 * Bring a tab to the front, if this run is allowed to.
 *
 * Answers the tab as it now is, or `null` when it may not be moved. Both the
 * tab and its window: a tab activated in a window that is behind another one
 * is still not what the operator is looking at, and `captureVisibleTab` would
 * photograph whatever is in front of it.
 */
async function bringForward(tab, allowFocus) {
  if (!allowFocus) return null;
  try {
    await chrome.windows.update(tab.windowId, { focused: true });
    return await chrome.tabs.update(tab.id, { active: true });
  } catch {
    // The window closed while we were asking. There is no screen to take.
    return null;
  }
}

/**
 * Open a tab on a system nobody has open, so a lookup has somewhere to look.
 *
 * A READ's door, and only a read's. `http.send`, `navigate` and `screenshot`
 * all need a tab already on the origin -- the point of sending from the
 * browser is the session that origin's cookies carry -- so a question asked of
 * four systems is answerable only for the ones the operator happens to have
 * open. That is not a rule anybody chose; it is what "no tab" meant before
 * there was a way to say otherwise.
 *
 * In the background, always. `active: false` means the page loads behind
 * whatever the operator is doing and their focus never moves; a lookup is not
 * worth taking somebody's screen for, and `screenshot` asks for `allow_focus`
 * separately when it needs the page in front.
 *
 * Not a general "open this url": the tab is opened so the next command can
 * find it, and the backend only ever sends an address resolved from a page
 * this deployment has already been to.
 */
async function openTab(payload) {
  if (!payload?.url) return failure("not_actionable", "tab.open with no url");
  let origin;
  try {
    origin = new URL(payload.url).origin;
  } catch {
    return failure(
      "not_actionable",
      `tab.open with an unreadable url: ${payload.url}`,
    );
  }
  if (!/^https?:$/.test(new URL(payload.url).protocol)) {
    // A `chrome://` or `file://` url is not a system with a session, and
    // opening one is the extension reaching outside the job it has.
    return failure(
      "not_actionable",
      "tab.open only opens http and https pages",
    );
  }

  const open = (await chrome.tabs.query({ url: `${origin}/*` })).filter(
    (tab) => tab.url && /^https?:/.test(tab.url),
  );
  if (open.length) {
    // Already there. Opening a second tab on a system the operator has open
    // would leave them tidying up after a question they asked.
    return { ok: true, result: { opened: false, tab_id: open[0].id } };
  }

  const tab = await chrome.tabs.create({ url: payload.url, active: false });
  // The page needs time to answer before the command after this one asks it
  // anything. `hold` is what a driven tab already gets; the wait is the same
  // one a navigate leaves behind.
  hold(tab.id, 8000);
  return { ok: true, result: { opened: true, tab_id: tab.id } };
}

async function navigate(payload) {
  if (!payload?.url) return failure("not_actionable", "navigate with no url");
  let tab = await drivenTab(payload.origin);
  if (!tab) {
    // Nothing open on that system, and this command names the page it wants.
    //
    // Refusing here is refusing to do the one thing a navigate is: `ui.perform`
    // opens a tab through `starts_on` when the operator's browser is elsewhere,
    // and a navigate -- which carries a url by definition -- would not. So a
    // run whose first warehouse step is "go to the Customer Types screen" died
    // `no_tab_for_system` in front of an operator who had that system open in
    // another window. Measured on the deployment, 2026-09-17.
    //
    // Only the page this command is for. `openFor` is the same rule `opensFor`
    // holds for a perform: a url whose origin is not the command's is not this
    // system's page, and opening it would be driving the browser somewhere
    // nobody asked for.
    const wanted = openFor(payload);
    tab = wanted ? await openAt(wanted) : null;
    if (!tab) return failure("no_tab_for_system", noPage(payload.origin));
    // Opened AT the page, which is the whole of what this command asked for.
    hold(tab.id, 8000);
    return { ok: true, result: { navigated: true, opened: true } };
  }

  const [inFront] = await chrome.tabs.query({
    active: true,
    lastFocusedWindow: true,
  });
  if (!payload.allow_focus && inFront?.id === tab.id) {
    return failure(
      "focus_not_permitted",
      "that would navigate the tab the operator is looking at",
    );
  }

  hold(tab.id, 8000);
  await chrome.tabs.update(tab.id, { url: payload.url });
  return { ok: true, result: { navigated: true } };
}

/** The extension's own menu of headers it knows how to read off a live page,
 * matching `LIVE_FETCHABLE_HEADERS` on the backend -- a name the backend asks
 * for that is not here is `unreachable`, never silently dropped, because that
 * gap is a deployment the two sides disagree about, not a normal miss. */
const LIVE_HEADER_SOURCES = {
  "csrf-encrypt-token": csrfTokenInPage,
  "x-requested-with": requestedWithInPage,
};

async function httpSend(payload) {
  let tab = await tabOnOrigin(payload?.url || "");
  // The one case where a call may open its own page, and it is the first
  // command of a run. A job whose write goes out as a call performs none of
  // the steps that used to walk the browser to the form -- there is no form --
  // so nothing before this has put a tab on the origin. `opensFor` still
  // refuses a `starts_on` that names a different system, so this can only ever
  // open the page the call is going to.
  const wanted = tab
    ? null
    : opensFor({ ...payload, origin: originOf(payload?.url || "") });
  if (wanted) tab = await openAt(wanted);
  if (!tab) {
    // No tab, and no page to open one at -- and for a call that needs nothing
    // off a live page, that is still not a reason to give up.
    //
    // The tab was never what carried the session. This extension holds
    // `<all_urls>` host permissions, and Chrome's own rule is that requests
    // from an extension to a third party are treated as SAME-SITE where the
    // extension has host permissions for it -- which is what lets even a
    // `SameSite=Strict` session cookie go -- and a worker request to a
    // permitted host is not bound by the page's CORS either. The worker can
    // send what the page would have sent.
    //
    // Last, not first, and reached only where the answer today is a hard
    // failure. The page path is the one this deployment has watched succeed,
    // and Chrome's rule carries a caveat nothing here can check from the
    // worker: it does not apply where third-party cookies are blocked. A call
    // that went out unauthenticated is answered 401, read as a failed write,
    // and un-earns the job -- so this must never be the cheap path.
    //
    // `live_headers` is the real reason a page is wanted. `CSRF-ENCRYPT-TOKEN`
    // is read out of `Ext.Ajax.defaultHeaders` in the page's MAIN world, and
    // there is no page here to read it from, so a call naming one still fails.
    if ((payload.live_headers || []).length === 0) {
      // The same function the page runs, run here instead: same request, same
      // answer shape, and no page realm at all -- so it is no more visible to
      // the recorder's MAIN-world patch than the isolated-world send is.
      return (
        (await sendInPage(payload)) ||
        failure("unreachable", "the call went nowhere")
      );
    }
    return failure(
      "no_tab_for_origin",
      `no tab is open on ${payload?.url || "that origin"}`,
    );
  }
  const headers = { ...(payload.headers || {}) };
  for (const name of payload.live_headers || []) {
    const key = name.toLowerCase();
    // A plain `[key]` lookup also answers for `constructor`, `__proto__`,
    // and every other name `Object.prototype` carries, each with a truthy
    // value that is not a header source -- `hasOwn` is the only way to ask
    // "is this actually in the menu" instead of "does this exist somewhere
    // on the object", which a name like that would still pass.
    const source = Object.hasOwn(LIVE_HEADER_SOURCES, key)
      ? LIVE_HEADER_SOURCES[key]
      : undefined;
    if (!source) {
      return failure("unreachable", `no live source for header ${name}`);
    }
    // Every frame, not just the top one: on the system this was built for the
    // token lives in the application's iframe and the shell has none.
    const value = await inEveryFrame(tab.id, source, [], "MAIN");
    if (!value) {
      return failure(
        "unreachable",
        `${name} is not on this page or any frame of it`,
      );
    }
    headers[name] = value;
  }
  // The isolated world: same origin and the same cookies, but not the page's
  // patched fetch, so a replayed call is not captured as the operator's own.
  const answer = await inPage(
    tab.id,
    sendInPage,
    [{ ...payload, headers }],
    "ISOLATED",
  );
  return answer || failure("unreachable", "the page did not answer");
}

/**
 * Perform one command. Never throws: an exception here is a command with no
 * answer, and the backend can only read that as a device that went away.
 *
 * `source` is which channel the command arrived on -- "backend" or "rig". It
 * is recorded on the run because a run's finish has to be asked of the process
 * that started it, and a rig run asked of the backend is a 404.
 */
export async function perform(command, source = "backend") {
  if (command.run_id && aborted.has(command.run_id)) {
    return failure("aborted", "this run was aborted");
  }

  if (command.run_id) {
    const now = Date.now();
    const isNewRun = latest?.runId !== command.run_id;
    latest = isNewRun
      ? {
          runId: command.run_id,
          kind: command.kind,
          source,
          since: now,
          at: now,
          ...told(command),
        }
      : { ...latest, kind: command.kind, at: now, ...told(command) };
    // The page says so itself while it is being driven. The panel already
    // does, and the panel is not where somebody is looking: they are watching
    // fields fill and buttons press, with nothing there saying it is not them.
    void announce(command, latest);
    // Mirrored to storage, not just held in `latest`: this worker is evicted
    // between commands as a matter of course, which is the *ordinary* case
    // for a run performed with the panel closed, and `latest` dying with it
    // would mean the only trigger left to notice a run finishing is the panel
    // poll -- which only ever fires for an operator already staring at the
    // screen. `service-worker.js`'s `checkFinishing()` reads this instead,
    // off both the panel poll and the heartbeat alarm that fires whether the
    // panel is open or not. Only `runId`, `at` and `source`: everything else
    // `latest` carries -- `tabId`, the step count the band shows -- is for
    // driving this run within this worker's own lifetime and is worthless to a
    // worker that has since been evicted and restarted. `source` survives
    // because the finish has to be asked of the process that started the run,
    // and a restarted worker no longer has the channel to ask.
    void state.setActiveRun({ runId: command.run_id, at: now, source });
    // A new run starting supersedes whatever the last one made. Left standing,
    // "Undo that" for the run before this one would sit under a card saying
    // this one is performing right now -- confusing even though neither fact
    // is wrong, and cheaper to clear here than to wait out however long this
    // run takes to finish on its own.
    if (isNewRun) {
      void state.setFinishedRun(null);
      // One run drives at a time, so the marks of the runs before it are
      // nobody's to read.
      marks.clear();
    }
  }

  // Before the page is touched, so every call it makes because of this
  // command counts and none of the ones it had already made do.
  if (command.run_id && ACTS.has(command.kind)) marks.set(command.run_id, seq);

  try {
    switch (command.kind) {
      case "ui.perform":
        return await uiPerform(command.payload || {}, command.run_id);
      case "ui.perform_at":
        return await uiPerformAt(command.payload || {});
      case "ui.url":
        return await uiUrl(command.payload || {});
      case "screenshot":
        return await screenshot(command.payload || {});
      case "navigate":
        return await navigate(command.payload || {});
      case "tab.open":
        return await openTab(command.payload || {});
      case "calls.since":
        return callsSince(command.run_id);
      case "http.send":
        return await httpSend(command.payload || {});
      case "abort":
        if (command.payload?.run_id) aborted.add(command.payload.run_id);
        return { ok: true, result: { aborted: true } };
      default:
        return failure(
          "not_actionable",
          `this extension has no ${command.kind}`,
        );
    }
  } catch (error) {
    // Including a page that closed mid-command, which `executeScript` reports
    // by rejecting. An answer saying so is worth more than none.
    return failure(
      "not_actionable",
      `the command failed in the browser: ${error}`,
    );
  }
}
