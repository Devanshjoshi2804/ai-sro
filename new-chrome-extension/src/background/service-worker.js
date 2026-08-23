// Registration, heartbeat, and the truthful badge.
//
// Nothing here holds state in a module variable: MV3 evicts this worker while
// it is idle and every wake-up starts from storage.

import { api, ApiError } from "./api.js";
import { applyPolicy, unregister } from "./scripts.js";
import { capturing, state } from "./state.js";

const BEAT = "sro-heartbeat";
const EVERY_MINUTES = 1;

const VERSION = chrome.runtime.getManifest().version;

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create(BEAT, { periodInMinutes: EVERY_MINUTES });
  void settle();
});

chrome.runtime.onStartup.addListener(() => {
  chrome.alarms.create(BEAT, { periodInMinutes: EVERY_MINUTES });
  void settle();
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === BEAT) void beat();
});

chrome.runtime.onMessage.addListener((message, _sender, respond) => {
  // Returning true keeps the channel open for the async answer.
  handle(message).then(respond, (error) => respond({ error: String(error) }));
  return true;
});

async function handle(message) {
  switch (message?.kind) {
    case "content-ready":
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
    const policy = await state.policy();
    const answer = await api.heartbeat(deviceId, {
      queued_events: 0,
      queued_bytes: 0,
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
