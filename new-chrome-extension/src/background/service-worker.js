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
  try {
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
  } catch (error) {
    // A full or broken queue is the one failure that must not be silent:
    // capture stopping quietly looks exactly like an operator with nothing
    // to do, and nobody finds out for weeks.
    await state.setLastError(`could not queue a page event: ${String(error)}`);
  }
}

/** What the tenant's policy allows this request to keep.
 *
 * Both of these are delivered on every heartbeat and neither was being read,
 * so a tenant that had switched response bodies off still had them uploaded,
 * and `max_body_bytes` bounded nothing at all. */
function underPolicy(request, policy) {
  if (!request?.request_body && !request?.response_body) return request;
  const limit = policy?.max_body_bytes ?? Infinity;

  const allowed = (body, keep) => {
    if (!body) return body;
    if (!keep) return { ...body, text: null, size_bytes: 0, redacted_fields: ["«not captured»"] };
    if ((body.size_bytes ?? 0) > limit) {
      return {
        ...body,
        text: null,
        size_bytes: 0,
        redacted_fields: ["«dropped: larger than the tenant's max_body_bytes»"],
      };
    }
    return body;
  };

  return {
    ...request,
    request_body: allowed(request.request_body, true),
    response_body: allowed(request.response_body, policy?.capture_response_bodies !== false),
  };
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
    case "request": {
      // Every captured event is judged here, at the one point they all pass
      // through, rather than by whether a content script happens to be
      // running. Withdrawing a registration only stops *future* injections:
      // a tab that was already open keeps its scripts, keeps its patched
      // `fetch`, and keeps sending. Gating only on registration meant an
      // operator who hit pause -- or a host that had just been excluded --
      // went on being recorded for as long as the tab stayed open.
      const [policy, allowed] = await Promise.all([state.policy(), capturing()]);
      const frameUrl = message.frameUrl;
      if (!allowed.on || !allowsHost(frameUrl, policy)) {
        return { ok: false, dropped: allowed.on ? "excluded host" : allowed.because };
      }
      // tab_id comes from the sender, not the content script -- a frame has
      // no chrome.tabs access of its own to ask for it.
      const tab_id = sender?.tab?.id ?? null;
      await queue.enqueue(
        message.kind === "gesture"
          ? { kind: "gesture", gesture: message.gesture, tab_id, frame_url: frameUrl }
          : {
              kind: "request",
              request: underPolicy(message.request, policy),
              tab_id,
              frame_url: frameUrl,
            },
      );
      return { ok: true };
    }
    case "sign-in":
      await state.setApiUrl(message.apiUrl);
      await state.setToken(message.token);
      return register(message.label);
    case "sign-out":
      await unregister();
      // Before the credential goes, so nothing captured under it can be
      // uploaded under the next one. What this browser recorded for one
      // operator must not arrive in another operator's tenant because they
      // shared a machine.
      await queue.clear();
      await state.newQueueEpoch();
      await state.forget();
      await badge();
      return { ok: true };
    case "set-paused":
      await state.setPaused(Boolean(message.paused));
      return settle();
    case "flush":
      // Upload now rather than on the next tick. The options page offers this
      // so an operator who is about to close the laptop can see the queue go,
      // and it is how a test drives a whole capture through without waiting
      // out an alarm.
      return flushQueue();
    case "status":
      return status();
    default:
      return { error: `no such message: ${message?.kind}` };
  }
}

async function flushQueue() {
  const deviceId = await state.deviceId();
  const allowed = await capturing();
  if (!deviceId || !allowed.on) return { uploaded: 0, because: allowed.because || "not registered" };
  try {
    const result = await flush(deviceId);
    if (result.error) await state.setLastError(result.error);
    else if (result.uploaded) await state.setLastError("");
    return result;
  } catch (error) {
    // A 401 already dropped the token in api.js; settle() reflects that as
    // "no credential" on the next status read rather than repeating it here.
    const message = error instanceof ApiError ? error.message : String(error);
    await state.setLastError(message);
    return { uploaded: 0, error: message };
  }
}

/** Register this browser profile, then apply whatever policy came back. */
async function register(label) {
  const previous = await state.deviceId();
  const registered = await api.register(label || defaultLabel(), VERSION);
  if (previous && previous !== registered.device_id) {
    // A different device means a different credential, which may mean a
    // different operator and a different tenant. Whatever the last one
    // captured is theirs, not this one's, and it does not get uploaded here.
    await queue.clear();
    await state.newQueueEpoch();
  }
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
    // The budget is checked here because this tick already pays for a full
    // scan of the store. Enforcing it per event would mean that scan on every
    // click. The backend does not check it at all -- `ingest.py` says so in as
    // many words -- so if this does not hold the line, nothing does.
    const budget = policy?.daily_budget_bytes;
    if (budget) {
      const trimmed = await queue.trim(budget);
      if (trimmed.strippedBodies || trimmed.droppedEvents) {
        await state.setLastError(
          `over the device's byte budget: dropped ${trimmed.droppedEvents} events and ` +
            `${trimmed.strippedBodies} response bodies`,
        );
      }
    }
    const [queuedEvents, queuedBytes] = await Promise.all([queue.count(), queue.totalBytes()]);
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
