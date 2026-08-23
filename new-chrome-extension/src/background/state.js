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
  policy: "sro.policy",
  paused: "sro.paused",
  serverPaused: "sro.serverPaused",
  lastBeat: "sro.lastBeat",
  lastError: "sro.lastError",
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

  policy: () => read(KEYS.policy, null),
  setPolicy: (policy) => write(KEYS.policy, policy),

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
