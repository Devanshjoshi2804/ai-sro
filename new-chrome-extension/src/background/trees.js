// Accessibility trees, taken passively, while a tab is being watched.
//
// The tree is the one view that says what a control *is* rather than where it
// happens to sit today. The backend builds a locator from it, so a step learned
// without one has only what the DOM offers -- a css path full of ExtJS ids that
// are assigned in render order and differ on the next page load.
//
// ## The banner
//
// Trees come from `chrome.debugger`, and Chrome shows "AI-SRO is debugging this
// browser" for as long as anything is attached -- which, here, is as long as
// the tab is watched. That cost is real, so it is off unless the tenant's
// policy turns it on, below.
//
// An extension force-installed by enterprise policy
// (`ExtensionInstallForcelist`) does not raise the bar at all, which is the
// deployment this is for: managed Chrome, operators who did not install
// anything themselves. An unpacked development copy does raise it, and there is
// no way to suppress that from inside an extension -- `--silent-debugger-extension-api`
// is a launch flag, not something code can ask for. So this is off unless the
// tenant's policy turns it on, and what it costs is written where an
// administrator turns it on rather than discovered by an operator.
//
// ## DevTools
//
// Chrome allows one debugger per tab. An operator who opens DevTools takes it,
// and this cannot have it back until they close them. That is the right way
// round -- their tab, their tools -- so a refused attach is recorded and
// forgotten, not retried in a loop, and capture carries on without trees.

import { state } from "./state.js";
import { allowsHost } from "./scripts.js";

const PROTOCOL = "1.3";

/** A tree of any size is worth having, but a page can produce a very large one
 * and it rides in the same queue as everything else. */
const MAX_NODES = 4000;

/** Tabs this module holds the debugger on. */
const attached = new Map();

/** Tabs that refused, and are not asked again for this worker's lifetime.
 *
 * A tab with DevTools open refuses every time. Asking on every gesture would
 * spend a round trip per click to be told the same thing, and on some Chrome
 * versions would log an error to the operator's own console for each one. */
const refused = new Set();

/** The tree taken before the *next* gesture, per tab.
 *
 * The assembler attaches a snapshot to the frame of the gesture before it, and
 * that frame's locator is built from the tree -- so the tree has to be the
 * screen the operator was looking at when they decided to act. Taken after the
 * click, a step that navigates would carry the destination page, and the backend
 * would build that step's locator from a page where the control it clicked does
 * not exist. */
const waiting = new Map();

export function takeTree(tabId) {
  const taken = waiting.get(tabId) ?? null;
  waiting.delete(tabId);
  return taken;
}

/** Photograph the tree now, for whatever the operator does next.
 *
 * `null` is the ordinary answer, not a failure: the policy has it off, the cap
 * is reached, the tab refused, the page is excluded. A gesture is evidence with
 * or without a tree and is never failed for the want of one.
 */
export async function takeTreeSoon(tabId, url, policy) {
  if (!policy?.capture_snapshots) return null;
  if (tabId === null || tabId === undefined) return null;
  if (refused.has(tabId)) return null;
  // The host of the whole document, which is what a tree actually describes --
  // the same rule a screenshot goes by, for the same reason.
  if (!allowsHost(url, policy)) return null;
  if (!(await within(policy))) return null;
  if (!(await hold(tabId))) return null;

  let tree;
  try {
    tree = await chrome.debugger.sendCommand({ tabId }, "Accessibility.getFullAXTree");
  } catch {
    // Detached underneath us: the tab navigated mid-command, or the operator
    // dismissed the banner. Let go rather than hold a handle to nothing.
    await release(tabId);
    return null;
  }
  const nodes = tree?.nodes;
  if (!Array.isArray(nodes) || !nodes.length) return null;

  await noteTree();
  const taken = {
    kind: "snapshot",
    // CDP's own shape, unreshaped: the server parses exactly this, through the
    // same parser a deliberate demonstration's trees go through.
    snapshot: { nodes: nodes.slice(0, MAX_NODES) },
    url,
    taken_at: new Date().toISOString(),
    tab_id: tabId,
  };
  waiting.set(tabId, taken);
  return taken;
}

/** Let a tab go: it closed, or it stopped being watched. */
export async function release(tabId) {
  waiting.delete(tabId);
  refused.delete(tabId);
  if (!attached.has(tabId)) return;
  attached.delete(tabId);
  await chrome.debugger.detach({ tabId }).catch(() => {});
}

/** Everything, for a policy that has just turned this off. */
export async function releaseAll() {
  await Promise.all([...attached.keys()].map((tabId) => release(tabId)));
}

async function hold(tabId) {
  if (attached.has(tabId)) return true;
  try {
    await chrome.debugger.attach({ tabId }, PROTOCOL);
  } catch (error) {
    // DevTools has it, or another extension does. Their tab, their tools.
    refused.add(tabId);
    return false;
  }
  try {
    await chrome.debugger.sendCommand({ tabId }, "Accessibility.enable");
  } catch {
    // Attached but useless. Detach rather than leave the banner up over a tab
    // that will produce no trees.
    await chrome.debugger.detach({ tabId }).catch(() => {});
    refused.add(tabId);
    return false;
  }
  attached.set(tabId, Date.now());
  return true;
}

const DEFAULT_PER_MINUTE = 20;

/** The same shape of cap as screenshots, and its own budget.
 *
 * Its own, because a tree and a picture cost different things: a tree is a
 * round trip and some JSON, a picture is a PNG. Sharing one counter would have
 * whichever happened first spend the other's allowance. */
async function within(policy) {
  const perMinute = policy.snapshot_max_per_minute ?? DEFAULT_PER_MINUTE;
  if (!(perMinute > 0)) return false;
  const recent = await recentTrees();
  return recent.length < perMinute;
}

async function recentTrees() {
  const since = Date.now() - 60_000;
  const times = (await state.treeTimes()) || [];
  return times.filter((at) => at > since);
}

async function noteTree() {
  await state.setTreeTimes([...(await recentTrees()), Date.now()]);
}
