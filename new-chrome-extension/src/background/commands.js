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

import { performAtInPage, performInPage, sendInPage, viewportInPage } from "./in-page.js";

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

/**
 * The tab a command without an origin of its own acts in: the one in front of
 * the operator.
 *
 * `no_tab_for_system` when there is none -- a browser showing only its own
 * settings pages is a browser with nothing to drive, and that is a device
 * problem rather than a page that changed.
 */
async function drivenTab() {
  const inFront = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  const usable = (tab) => tab?.url && /^https?:/.test(tab.url);
  if (usable(inFront[0])) return inFront[0];

  // Any ordinary tab will do rather than none at all: the operator may be
  // looking at a settings page while the run's system sits in the next tab.
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

async function uiPerform(payload) {
  const tab = await drivenTab();
  if (!tab) return failure("no_tab_for_system", "this browser has no ordinary page open");
  hold(tab.id);
  const answer = await inPage(tab.id, performInPage, [payload]);
  hold(tab.id);
  return answer || failure("not_actionable", "the page did not answer");
}

async function uiPerformAt(payload) {
  const tab = await drivenTab();
  if (!tab) return failure("no_tab_for_system", "this browser has no ordinary page open");
  hold(tab.id);
  const answer = await inPage(tab.id, performAtInPage, [payload]);
  hold(tab.id);
  return answer || failure("not_actionable", "the page did not answer");
}

async function uiUrl() {
  const tab = await drivenTab();
  if (!tab) return failure("no_tab_for_system", "this browser has no ordinary page open");
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
async function screenshot() {
  const tab = await drivenTab();
  if (!tab) return failure("no_tab_for_system", "this browser has no ordinary page open");

  // The names come from the DOM rather than from the picture: a control's own
  // name beats one inferred from pixels, and the redaction the backend runs
  // before anything reaches a model can only reason about text.
  const seen = (await inPage(tab.id, viewportInPage, [], "ISOLATED")) || {};

  let dataUrl;
  try {
    dataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, { format: "png" });
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
async function navigate(payload) {
  if (!payload?.url) return failure("not_actionable", "navigate with no url");
  const tab = await drivenTab();
  if (!tab) return failure("no_tab_for_system", "this browser has no ordinary page open");

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

async function httpSend(payload) {
  const tab = await tabOnOrigin(payload?.url || "");
  if (!tab) {
    return failure("no_tab_for_origin", `no tab is open on ${payload?.url || "that origin"}`);
  }
  // The isolated world: same origin and the same cookies, but not the page's
  // patched fetch, so a replayed call is not captured as the operator's own.
  const answer = await inPage(tab.id, sendInPage, [payload], "ISOLATED");
  return answer || failure("unreachable", "the page did not answer");
}

/**
 * Perform one command. Never throws: an exception here is a command with no
 * answer, and the backend can only read that as a device that went away.
 */
export async function perform(command) {
  if (command.run_id && aborted.has(command.run_id)) {
    return failure("aborted", "this run was aborted");
  }

  try {
    switch (command.kind) {
      case "ui.perform":
        return await uiPerform(command.payload || {});
      case "ui.perform_at":
        return await uiPerformAt(command.payload || {});
      case "ui.url":
        return await uiUrl();
      case "screenshot":
        return await screenshot();
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
