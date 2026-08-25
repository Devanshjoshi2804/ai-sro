// The teaching tier: a demonstration, in the operator's own browser.
//
// Passive observation is deliberately cheap and invisible. This is the
// opposite: the operator has been asked to show the system a task, so the
// extension attaches `chrome.debugger` to the tab and takes an accessibility
// tree at every gesture -- the one view that says what a control *is* rather
// than where it happens to sit today, and the thing induction reads to build a
// locator that survives a re-render.
//
// It is not free and it is not quiet. Chrome shows "AI-SRO is debugging this
// browser" across the top of the tab for as long as this is attached, which is
// exactly right: this is the operator deliberately teaching, for a few minutes,
// and they should be able to see that it is on and that it stopped. ADR 008
// keeps passive capture clear of it for the same reason.

import { state } from "./state.js";

const PROTOCOL = "1.3";

/** A tree of any size is worth having, but a page can produce a very large one
 * and it rides in the same queue as everything else. */
const MAX_NODES = 4000;

/** Attach to a tab and start a demonstration in it. */
export async function start(recordingId, tabId) {
  await stop();
  await chrome.debugger.attach({ tabId }, PROTOCOL);
  try {
    await chrome.debugger.sendCommand({ tabId }, "Accessibility.enable");
  } catch (error) {
    // Attached but useless: detach rather than leave the banner up over a
    // session that will produce no snapshots.
    await chrome.debugger.detach({ tabId }).catch(() => {});
    throw error;
  }
  await state.setTeaching({ recordingId, tabId, startedAt: new Date().toISOString() });
}

/** Stop, whether or not anything was attached. Safe to call twice. */
export async function stop() {
  const teaching = await state.teaching();
  await state.setTeaching(null);
  if (!teaching) return null;
  try {
    await chrome.debugger.detach({ tabId: teaching.tabId });
  } catch {
    // The tab closed, or Chrome detached us when it did. Either way there is
    // no banner left to take down.
  }
  return teaching;
}

/** The demonstration this browser is in the middle of, or null. */
export async function current() {
  return state.teaching();
}

/**
 * The accessibility tree of the tab being demonstrated in, as a `snapshot`
 * event -- or null when this tab is not the one, or the tree cannot be had.
 *
 * Taken per gesture rather than per page: it is the state the operator was
 * looking at when they decided to act, which is what the assembler attaches to
 * the frame that gesture opens.
 */
export async function snapshot(tabId, url) {
  const teaching = await state.teaching();
  if (!teaching || teaching.tabId !== tabId) return null;

  let tree;
  try {
    tree = await chrome.debugger.sendCommand({ tabId }, "Accessibility.getFullAXTree");
  } catch {
    // Detached underneath us -- the operator dismissed the banner, or the tab
    // navigated mid-command. The gesture is still evidence; the tree is not
    // worth failing it for.
    return null;
  }
  const nodes = tree?.nodes;
  if (!Array.isArray(nodes) || !nodes.length) return null;

  return {
    kind: "snapshot",
    // CDP's own shape, unreshaped: `capture.decode.to_ax_graph` parses exactly
    // this on the other side, and it is the same parser the server-side
    // recorder's trees go through.
    snapshot: { nodes: nodes.slice(0, MAX_NODES) },
    url,
    taken_at: new Date().toISOString(),
    tab_id: tabId,
  };
}
