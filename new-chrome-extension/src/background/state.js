// What this browser knows between service-worker lifetimes.
//
// MV3 evicts the worker while it is idle, so nothing here may live in a module
// variable: every read goes to chrome.storage. `local` rather than `session`
// because `session` is cleared when Chrome restarts, and an operator who has to
// paste a credential every morning is an operator who turns the extension off.

const KEYS = {
  token: "sro.token",
  deviceId: "sro.deviceId",
  apiUrl: "sro.apiUrl",
  consoleUrl: "sro.consoleUrl",
  policy: "sro.policy",
  watches: "sro.watches",
  watched: "sro.watched",
  paused: "sro.paused",
  serverPaused: "sro.serverPaused",
  lastBeat: "sro.lastBeat",
  lastError: "sro.lastError",
  queueEpoch: "sro.queueEpoch",
  pendingBatch: "sro.pendingBatch",
  shotTimes: "sro.shotTimes",
  teaching: "sro.teaching",
};

export const DEFAULT_API_URL = "http://localhost:8000";

async function read(key, fallback = null) {
  const held = await chrome.storage.local.get(key);
  return key in held ? held[key] : fallback;
}

async function write(key, value) {
  await chrome.storage.local.set({ [key]: value });
}

export const state = {
  token: () => read(KEYS.token, ""),
  setToken: (token) => write(KEYS.token, token),

  deviceId: () => read(KEYS.deviceId, ""),
  setDeviceId: (id) => write(KEYS.deviceId, id),

  apiUrl: () => read(KEYS.apiUrl, DEFAULT_API_URL),
  setApiUrl: (url) => write(KEYS.apiUrl, url.replace(/\/+$/, "")),

  /** Where the console is, for the panel to frame. A different origin from the
   * backend and not derivable from it -- one is an API, the other is a site,
   * and a deployment may put them anywhere. Empty means the panel shows only
   * what it can do itself, which is most of why it exists. */
  consoleUrl: () => read(KEYS.consoleUrl, ""),
  setConsoleUrl: (url) => write(KEYS.consoleUrl, url.replace(/\/+$/, "")),

  /** The tabs the operator asked to be watched, newest first. Each is
   * `{ tabId, host, since }`.
   *
   * Nothing is watched by default and nothing is inferred: what a person is
   * working in is a thing only that person knows, and every rule this system
   * tried to guess it by -- our own origins, the tenant's host list -- was
   * either wrong about a tab or silently right about the wrong one.
   *
   * A tab id, not a host: the operator points at the window in front of them,
   * and it keeps being that window when the application navigates to a
   * different host mid-task, which every SSO flow does. */
  watched: () => read(KEYS.watched, []),
  setWatched: (tabs) => write(KEYS.watched, tabs),

  policy: () => read(KEYS.policy, null),
  setPolicy: (policy) => write(KEYS.policy, policy),

  /** The mail rules this browser holds, each `{ id, host, terms, values,
   * sender_at, subject_at }`.
   *
   * The rule, never a match. A watch is evaluated in the page and what it saw
   * is forgotten there; a list of mails this browser recognised would be the
   * one thing `ValueAt` went structural lengths to keep out of storage.
   *
   * Written here rather than kept in the worker because the watch content
   * script reads the change through `chrome.storage.onChanged` -- a page open
   * all day picks up a watch created this morning, and drops the lot when the
   * operator signs out. */
  watches: () => read(KEYS.watches, []),
  setWatches: (watches) => write(KEYS.watches, watches),

  // Two pauses, deliberately separate. This one is the operator's and lives
  // only here; theirs is theirs to hold. The other arrives on a heartbeat and
  // is an administrator's.
  paused: () => read(KEYS.paused, false),
  setPaused: (paused) => write(KEYS.paused, paused),

  serverPaused: () => read(KEYS.serverPaused, false),
  setServerPaused: (paused) => write(KEYS.serverPaused, paused),

  lastBeat: () => read(KEYS.lastBeat, null),
  setLastBeat: (at) => write(KEYS.lastBeat, at),

  lastError: () => read(KEYS.lastError, ""),
  setLastError: (message) => write(KEYS.lastError, message),

  /** Distinguishes one lifetime of the event queue from the next.
   *
   * Batch ids are minted from IndexedDB row keys, and that counter restarts
   * whenever the store is recreated. Without something that does not restart
   * alongside it, the first batch after an evicted database would collide
   * with one the backend had already stored. */
  async queueEpoch() {
    const held = await read(KEYS.queueEpoch, "");
    if (held) return held;
    return state.newQueueEpoch();
  },
  async newQueueEpoch() {
    const minted = crypto.randomUUID().slice(0, 8);
    await write(KEYS.queueEpoch, minted);
    return minted;
  },

  /** The batch that has been sent at least once and not yet accounted for:
   * its id and the exact rows it named.
   *
   * Both, not just the id. `trim` can delete rows out from under a batch
   * between attempts, and a retry that quietly picked up a different set --
   * or minted a different id over an overlapping one -- is how the same
   * events got stored twice. */
  pendingBatch: () => read(KEYS.pendingBatch, null),
  setPendingBatch: (batch) => write(KEYS.pendingBatch, batch),

  /** When the last minute's screenshots were taken, so the policy's
   * per-minute cap survives this worker being evicted between two clicks --
   * which, at a human's pace, is most pairs of clicks. */
  shotTimes: () => read(KEYS.shotTimes, []),
  setShotTimes: (times) => write(KEYS.shotTimes, times),

  /** The demonstration this browser is in the middle of: which recording, in
   * which tab. In storage rather than a module variable because the worker is
   * evicted between two of the operator's clicks, and a demonstration that
   * forgot itself halfway through would upload the rest as ordinary work. */
  teaching: () => read(KEYS.teaching, null),
  setTeaching: (teaching) => write(KEYS.teaching, teaching),

  async forget() {
    await chrome.storage.local.remove(Object.values(KEYS));
  },
};

/** Whether anything may be captured right now, and why not when it may not. */
export async function capturing() {
  const [token, deviceId, policy, paused, serverPaused] = await Promise.all([
    state.token(),
    state.deviceId(),
    state.policy(),
    state.paused(),
    state.serverPaused(),
  ]);
  if (!token) return { on: false, because: "no credential" };
  if (!deviceId) return { on: false, because: "not registered" };
  if (paused) return { on: false, because: "paused here" };
  if (serverPaused) return { on: false, because: "paused by an administrator" };
  if (!policy?.capture_enabled) return { on: false, because: "not enabled for this tenant" };
  return { on: true, because: "" };
}
