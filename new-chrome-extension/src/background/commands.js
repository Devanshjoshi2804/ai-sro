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

import {
  csrfTokenInPage,
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
    const onIt = (await chrome.tabs.query({ url: `${origin}/*` })).filter(usable);
    if (!onIt.length) return null;
    // The visible one first: a run drives what the operator can see going on,
    // and a background tab cannot be photographed for the rung that looks.
    return onIt.find((tab) => tab.active) || onIt[0];
  }

  const inFront = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  if (usable(inFront[0])) return inFront[0];

  // Any ordinary tab rather than none at all: the operator may be looking at a
  // settings page while the system sits in the next tab.
  const all = await chrome.tabs.query({ windowType: "normal" });
  return all.filter(usable).sort((a, b) => (b.lastAccessed || 0) - (a.lastAccessed || 0))[0] || null;
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

/** Run one of the page-realm functions and hand back what it answered. */
async function inPage(tabId, func, args, world = "MAIN") {
  const [answer] = await chrome.scripting.executeScript({
    target: { tabId },
    world,
    func,
    args,
  });
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
  const tab = await tabForRun(payload, runId);
  if (!tab) return failure("no_tab_for_system", noPage(payload.origin));
  hold(tab.id);
  const frameId = await frameHolding(tab.id, payload);
  const answer =
    frameId === undefined
      ? await inPage(tab.id, performInPage, [payload])
      : await inFrame(tab.id, frameId, performInPage, [payload]);
  hold(tab.id);
  return answer || failure("not_actionable", "the page did not answer");
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
    if (known && (!payload.origin || originOf(known.url) === payload.origin)) return known;
  }

  let tab = await drivenTab(payload.origin);
  const wanted = payload.starts_on;
  if (wanted && (!tab || !samePage(tab.url, wanted))) {
    const opened = await openAt(wanted);
    if (opened) tab = opened;
  }

  if (tab && runId && latest?.runId === runId) latest = { ...latest, tabId: tab.id };
  return tab;
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
    const done = (tab) => {
      chrome.tabs.onUpdated.removeListener(watch);
      clearTimeout(timer);
      resolve(tab);
    };
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
  return answer?.result;
}

async function uiPerformAt(payload) {
  const tab = await drivenTab(payload.origin);
  if (!tab) return failure("no_tab_for_system", noPage(payload.origin));
  hold(tab.id);
  const answer = await inPage(tab.id, performAtInPage, [payload]);
  hold(tab.id);
  return answer || failure("not_actionable", "the page did not answer");
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
  const visible = tab.active ? tab : await bringForward(tab, payload.allow_focus);
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
    dataUrl = await chrome.tabs.captureVisibleTab(visible.windowId, { format: "png" });
  } catch (error) {
    // A tab that is not the visible one cannot be photographed, and Chrome
    // refuses on its own pages. Both mean there is no screen to look at.
    return failure("no_tab_for_system", `this browser would not be photographed: ${error}`);
  }

  const bytes = bytesOf(dataUrl);
  if (!isPng(bytes)) return failure("no_tab_for_system", "the capture was not an image");

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

async function navigate(payload) {
  if (!payload?.url) return failure("not_actionable", "navigate with no url");
  const tab = await drivenTab(payload.origin);
  if (!tab) return failure("no_tab_for_system", noPage(payload.origin));

  const [inFront] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
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
const LIVE_HEADER_SOURCES = { "csrf-encrypt-token": csrfTokenInPage };

async function httpSend(payload) {
  const tab = await tabOnOrigin(payload?.url || "");
  if (!tab) {
    return failure("no_tab_for_origin", `no tab is open on ${payload?.url || "that origin"}`);
  }
  const headers = { ...(payload.headers || {}) };
  for (const name of payload.live_headers || []) {
    const source = LIVE_HEADER_SOURCES[name.toLowerCase()];
    if (!source) {
      return failure("unreachable", `no live source for header ${name}`);
    }
    const value = await inPage(tab.id, source, [], "MAIN");
    if (!value) {
      return failure("unreachable", `${name} is not on this page`);
    }
    headers[name] = value;
  }
  // The isolated world: same origin and the same cookies, but not the page's
  // patched fetch, so a replayed call is not captured as the operator's own.
  const answer = await inPage(tab.id, sendInPage, [{ ...payload, headers }], "ISOLATED");
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
      ? { runId: command.run_id, kind: command.kind, source, since: now, at: now, ...told(command) }
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
    if (isNewRun) void state.setFinishedRun(null);
  }

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
      case "http.send":
        return await httpSend(command.payload || {});
      case "abort":
        if (command.payload?.run_id) aborted.add(command.payload.run_id);
        return { ok: true, result: { aborted: true } };
      default:
        return failure("not_actionable", `this extension has no ${command.kind}`);
    }
  } catch (error) {
    // Including a page that closed mid-command, which `executeScript` reports
    // by rejecting. An answer saying so is worth more than none.
    return failure("not_actionable", `the command failed in the browser: ${error}`);
  }
}
