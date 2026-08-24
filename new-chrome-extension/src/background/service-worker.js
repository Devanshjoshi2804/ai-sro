// Registration, heartbeat, and the truthful badge.
//
// Nothing here holds state in a module variable: MV3 evicts this worker while
// it is idle and every wake-up starts from storage.

import { api, ApiError } from "./api.js";
import * as queue from "./queue.js";
import { allowsHost, applyPolicy, unregister } from "./scripts.js";
import { capturing, state } from "./state.js";
import { flush } from "./upload.js";

const BEAT = "sro-heartbeat";
const FLUSH = "sro-flush";
const EVERY_MINUTES = 1;

const VERSION = chrome.runtime.getManifest().version;

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create(BEAT, { periodInMinutes: EVERY_MINUTES });
  chrome.alarms.create(FLUSH, { periodInMinutes: EVERY_MINUTES });
  void settle();
});

chrome.runtime.onStartup.addListener(() => {
  chrome.alarms.create(BEAT, { periodInMinutes: EVERY_MINUTES });
  chrome.alarms.create(FLUSH, { periodInMinutes: EVERY_MINUTES });
  void settle();
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === BEAT) void beat();
  if (alarm.name === FLUSH) void flushQueue();
});

// Page lifecycle, straight from the platform -- no content script needed for
// this, and nothing rides on a page having one registered at all.
// ponytail: main frame only; add per-iframe navigation if a miner needs it.
chrome.webNavigation.onCommitted.addListener((d) => {
  if (d.frameId === 0) void pageEvent("navigated", d.tabId, d.url, d.timeStamp);
});
chrome.webNavigation.onCompleted.addListener((d) => {
  if (d.frameId === 0) void pageEvent("loaded", d.tabId, d.url, d.timeStamp);
});
chrome.webNavigation.onCreatedNavigationTarget.addListener((d) => {
  void pageEvent("popup_opened", d.sourceTabId, d.url, d.timeStamp);
});

async function pageEvent(page_kind, tab_id, url, timeStamp) {
  const [policy, allowed] = await Promise.all([state.policy(), capturing()]);
  if (!allowed.on || !allowsHost(url, policy)) return;
  await queue.enqueue({
    kind: "page",
    at: new Date(timeStamp).toISOString(),
    page_kind,
    url,
    detail: null,
    tab_id,
  });
}

chrome.runtime.onMessage.addListener((message, sender, respond) => {
  // Returning true keeps the channel open for the async answer.
  handle(message, sender).then(respond, (error) => respond({ error: String(error) }));
  return true;
});

async function handle(message, sender) {
  switch (message?.kind) {
    case "content-ready":
      return { ok: true };
    case "gesture":
      // tab_id comes from the sender, not the content script -- a frame has
      // no chrome.tabs access of its own to ask for it.
      await queue.enqueue({
        kind: "gesture",
        gesture: message.gesture,
        tab_id: sender?.tab?.id ?? null,
        frame_url: message.frameUrl,
      });
      return { ok: true };
    case "request":
      await queue.enqueue({
        kind: "request",
        request: message.request,
        tab_id: sender?.tab?.id ?? null,
        frame_url: message.frameUrl,
      });
      return { ok: true };
    case "sign-in":
      await state.setApiUrl(message.apiUrl);
      await state.setToken(message.token);
      return register(message.label);
    case "sign-out":
      await unregister();
      await state.forget();
      await badge();
      return { ok: true };
    case "set-paused":
      await state.setPaused(Boolean(message.paused));
      return settle();
    case "status":
      return status();
    default:
      return { error: `no such message: ${message?.kind}` };
  }
}

async function flushQueue() {
  const deviceId = await state.deviceId();
  const allowed = await capturing();
  if (!deviceId || !allowed.on) return;
  try {
    const result = await flush(deviceId);
    if (result.error) await state.setLastError(result.error);
    else if (result.uploaded) await state.setLastError("");
  } catch (error) {
    // A 401 already dropped the token in api.js; settle() reflects that as
    // "no credential" on the next status read rather than repeating it here.
    await state.setLastError(error instanceof ApiError ? error.message : String(error));
  }
}

/** Register this browser profile, then apply whatever policy came back. */
async function register(label) {
  const registered = await api.register(label || defaultLabel(), VERSION);
  await state.setDeviceId(registered.device_id);
  await state.setPolicy(registered.policy);
  await state.setLastError("");
  await settle();
  return status();
}

async function beat() {
  const deviceId = await state.deviceId();
  if (!deviceId) return;

  try {
    const [policy, queuedEvents, queuedBytes] = await Promise.all([
      state.policy(),
      queue.count(),
      queue.totalBytes(),
    ]);
    const answer = await api.heartbeat(deviceId, {
      queued_events: queuedEvents,
      queued_bytes: queuedBytes,
      policy_version: policy?.version ?? null,
    });
    if (answer.policy) await state.setPolicy(answer.policy);
    await state.setServerPaused(Boolean(answer.pause));
    await state.setLastBeat(new Date().toISOString());
    await state.setLastError("");
  } catch (error) {
    // A heartbeat that cannot reach the backend is not a reason to stop
    // capturing -- the queue is what capture is for. It is a reason to say so.
    await state.setLastError(error instanceof ApiError ? error.message : String(error));
  }
  await settle();
}

/** Make the browser match what is stored: scripts registered, badge honest. */
async function settle() {
  const [policy, allowed] = await Promise.all([state.policy(), capturing()]);
  await applyPolicy(policy, allowed);
  await badge();
  return status();
}

async function badge() {
  const allowed = await capturing();
  await chrome.action.setBadgeText({ text: allowed.on ? "REC" : "" });
  await chrome.action.setBadgeBackgroundColor({ color: allowed.on ? "#b91c1c" : "#6b7280" });
  await chrome.action.setTitle({
    title: allowed.on ? "AI-SRO — observing" : `AI-SRO — not observing (${allowed.because})`,
  });
}

async function status() {
  const [allowed, deviceId, policy, apiUrl, paused, serverPaused, lastBeat, lastError] =
    await Promise.all([
      capturing(),
      state.deviceId(),
      state.policy(),
      state.apiUrl(),
      state.paused(),
      state.serverPaused(),
      state.lastBeat(),
      state.lastError(),
    ]);
  return {
    capturing: allowed.on,
    because: allowed.because,
    deviceId,
    policy,
    apiUrl,
    paused,
    serverPaused,
    lastBeat,
    lastError,
    version: VERSION,
  };
}

function defaultLabel() {
  // Enough to tell one browser from another in the device list, and nothing
  // about the person: the credential already says who they are.
  const platform = navigator.userAgent.match(/\((.*?)[;)]/)?.[1] || "browser";
  return `${platform} · Chrome`;
}
