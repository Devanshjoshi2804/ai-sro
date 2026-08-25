// A picture of the page the operator just acted on, bounded four ways.
//
// The tenant's policy decides whether these are taken at all and how many a
// minute; a screenshot is the largest and least reversible thing this
// extension collects, so nothing here is taken on a default.
//
// Taken in the worker rather than the page: `captureVisibleTab` is the only
// way to photograph a page without asking the page to help, and a content
// script cannot reach it.

import { allowsHost } from "./scripts.js";
import { state } from "./state.js";

/** One viewport of PNG. Anything larger is a page this cannot afford to
 * carry -- the gesture it would have illustrated goes without it. */
const MAX_SHOT_BYTES = 1024 * 1024;

/** Only when the policy omits its own. A tenant that switched screenshots on
 * without saying how many still gets a bounded number. */
const DEFAULT_PER_MINUTE = 20;

const WINDOW_MS = 60_000;

/** One capture at a time, for as long as this worker lives.
 *
 * Two reasons, and they are the same reason. Chrome refuses
 * `captureVisibleTab` outright while another capture is in flight, so a burst
 * of gestures loses most of its pictures to an error. And the per-minute
 * count is read from storage and written back, so a burst that overlaps reads
 * a count none of the others has written yet and every one of them passes a
 * cap that only one should have.
 *
 * ponytail: a module variable, so it holds within one wake-up of this worker
 * and not across an eviction. Gestures that far apart are not a burst.
 */
let queued = Promise.resolve();

function oneAtATime(task) {
  const next = queued.then(task, task);
  queued = next.then(
    () => {},
    () => {},
  );
  return next;
}

/** The minute's screenshots, forgetting the ones that have aged out of it. */
async function recentShots() {
  const now = Date.now();
  return (await state.shotTimes()).filter((at) => now - at < WINDOW_MS);
}

/** Spend one, once there is something to show for it.
 *
 * Counted after the capture rather than before: Chrome refuses
 * `captureVisibleTab` on its own pages and while another capture is in
 * flight, and a refusal that spent a slot meant a page that could be
 * photographed went without one for the rest of the minute.
 *
 * The read and this write are inside `oneAtATime`, so within one worker
 * lifetime nothing else is between them.
 */
async function noteShot(recent) {
  await state.setShotTimes([...recent, Date.now()]);
}

function bytesOf(dataUrl) {
  const base64 = dataUrl.slice(dataUrl.indexOf(",") + 1);
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

/**
 * A screenshot for the gesture that just happened in `tabId`, or `null` --
 * which is the ordinary answer, not a failure.
 *
 * The tab is re-read here rather than trusted from the message: the gesture
 * came from one frame, and what a photograph shows is the whole top document
 * that frame sits in. An allowed widget embedded in an excluded page would
 * otherwise be answered with a picture of the excluded page.
 */
export async function capture(tabId, policy) {
  if (!policy?.capture_screenshots) return null;
  const perMinute = policy.screenshot_max_per_minute ?? DEFAULT_PER_MINUTE;
  if (!(perMinute > 0)) return null;
  if (tabId === null || tabId === undefined) return null;

  let tab;
  try {
    tab = await chrome.tabs.get(tabId);
  } catch {
    // Closed between the gesture and here. There is nothing left to photograph.
    return null;
  }
  // `captureVisibleTab` photographs whatever is visible in the window, not the
  // tab it is handed. A gesture in a background tab -- a script clicking, a
  // second window -- would be answered with a picture of a different page.
  if (!tab.active) return null;
  if (!allowsHost(tab.url, policy)) return null;

  return oneAtATime(async () => {
    const recent = await recentShots();
    if (recent.length >= perMinute) return null;

    let dataUrl;
    try {
      dataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, { format: "png" });
    } catch {
      // Chrome refuses on its own pages, on a detached window, and past its
      // own limit of two captures a second -- which a policy allowing more
      // than 120 a minute would meet before this cap ever did. None of those
      // is worth an error banner, and none of them costs a slot.
      return null;
    }
    if (typeof dataUrl !== "string" || !dataUrl.startsWith("data:image/png")) return null;

    const bytes = bytesOf(dataUrl);
    if (!bytes.length || bytes.length > MAX_SHOT_BYTES) return null;

    await noteShot(recent);
    return { mime: "image/png", size: bytes.length, bytes };
  });
}
