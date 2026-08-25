// The socket the backend hands work down.
//
// Commands go down it and answers come back; there is no endpoint that drives
// a device, because one would let a leaked device id reach a browser that is
// not the caller's. The extension dials out, authenticates with the same
// credential everything else uses, and answers every command exactly once.
//
// Nothing here is kept across a service-worker eviction, and nothing needs to
// be: the socket dies with the worker, a run in flight dies with the socket,
// and the alarm that wakes the worker every minute dials again.

import * as commands from "./commands.js";
import { state } from "./state.js";

const VERSION = chrome.runtime.getManifest().version;

/** Chrome closes an idle service worker after 30 seconds, and takes the socket
 * with it. Since Chrome 116 traffic on a WebSocket resets that timer, so this
 * is what keeps the channel open between commands -- comfortably inside the
 * window, because a tick that lands late is a channel that has already gone. */
const KEEPALIVE_MS = 20_000;

/** After a drop. The first retry is quick because most drops are a laptop lid
 * or a wifi hop; the ceiling is there so a backend that is down does not have
 * every operator's browser dialling it once a second. */
const FIRST_RETRY_MS = 1_000;
const MAX_RETRY_MS = 30_000;

let socket = null;
let keepalive = null;
let retryIn = FIRST_RETRY_MS;
let retryTimer = null;
let answered = new Set();
let lastBusy = 0;

/** How long a burst of typing asks the backend to hold off, and how often that
 * is worth saying. Short, because it is renewed by the next keystroke and a
 * device that overstates how busy it is delays its own work. */
const BUSY_FOR_MS = 5_000;
const BUSY_EVERY_MS = 4_000;

export function status() {
  if (!socket) return "closed";
  return socket.readyState === WebSocket.OPEN ? "open" : "connecting";
}

/**
 * Make the socket match what is stored: open when this browser is registered
 * and not switched off by an administrator, closed otherwise.
 *
 * The operator's own pause is deliberately not a reason to close it. That
 * switch says "stop watching me"; a skill they asked for is not watching, and a
 * device that goes unreachable whenever somebody pauses observation is a device
 * nobody can schedule work on.
 */
export async function settle() {
  const [token, deviceId, serverPaused, apiUrl] = await Promise.all([
    state.token(),
    state.deviceId(),
    state.serverPaused(),
    state.apiUrl(),
  ]);

  if (!token || !deviceId || serverPaused) {
    close();
    return;
  }
  if (socket) return;
  open(apiUrl, deviceId, token);
}

export function close() {
  if (retryTimer) {
    clearTimeout(retryTimer);
    retryTimer = null;
  }
  stopKeepalive();
  const going = socket;
  socket = null;
  answered = new Set();
  if (going) {
    // Unhooked first: a close this code asked for must not look like a drop
    // and schedule a reconnect against the credential that was just signed
    // out.
    going.onclose = null;
    going.onerror = null;
    going.onmessage = null;
    try {
      going.close();
    } catch {
      // Already closing. Nothing to do about it and nothing to say.
    }
  }
}

function open(apiUrl, deviceId, token) {
  const url = `${apiUrl.replace(/^http/, "ws")}/v1/agents/${encodeURIComponent(deviceId)}/commands`;

  // The credential rides in the subprotocol, not the query string: a browser
  // cannot set a header on a WebSocket, and a token in the URL is a token in
  // every access log and every referrer.
  let opening;
  try {
    opening = new WebSocket(url, ["bearer", token]);
  } catch (error) {
    void state.setLastError(`the command channel could not be opened: ${error}`);
    retryLater();
    return;
  }
  socket = opening;

  opening.onopen = () => {
    retryIn = FIRST_RETRY_MS;
    void announce(opening);
    startKeepalive(opening);
  };

  opening.onmessage = (event) => {
    void handle(opening, event.data);
  };

  const dropped = () => {
    if (socket !== opening) return;
    stopKeepalive();
    socket = null;
    retryLater();
  };
  opening.onclose = dropped;
  opening.onerror = dropped;
}

/** Dial again later, and further out each time. */
function retryLater() {
  if (retryTimer) return;
  const wait = retryIn;
  retryIn = Math.min(retryIn * 2, MAX_RETRY_MS);
  retryTimer = setTimeout(() => {
    retryTimer = null;
    void settle();
  }, wait);
}

async function announce(open_) {
  const tabs = await chrome.tabs.query({});
  send(open_, { kind: "hello", extension_version: VERSION, tabs: tabs.length });
}

function startKeepalive(open_) {
  stopKeepalive();
  keepalive = setInterval(() => {
    if (open_.readyState !== WebSocket.OPEN) return;
    // Traffic, and nothing else: the backend drops a message with no
    // `command_id` on the floor, which is exactly what this wants it to do.
    send(open_, { kind: "ping" });
  }, KEEPALIVE_MS);
}

function stopKeepalive() {
  if (keepalive) {
    clearInterval(keepalive);
    keepalive = null;
  }
}

function send(open_, message) {
  try {
    open_.send(JSON.stringify(message));
  } catch (error) {
    void state.setLastError(`the command channel would not carry an answer: ${error}`);
  }
}

/**
 * The operator is using this browser right now.
 *
 * Told to the backend so a command queues rather than lands in the middle of
 * somebody typing -- a replay and a person filling the same form is how a run
 * clears a field the operator had half finished. Sent from their own gestures,
 * which means it is only sent where observation is on; a tenant that has it off
 * gets a channel that never says it is busy, and the backend simply acts.
 *
 * Rate-limited rather than sent per keystroke: it renews itself, so one message
 * covers a burst of typing.
 */
export function operatorIsWorking() {
  const open_ = socket;
  if (!open_ || open_.readyState !== WebSocket.OPEN) return;
  const now = Date.now();
  if (now - lastBusy < BUSY_EVERY_MS) return;
  lastBusy = now;
  send(open_, { kind: "busy", reason: "the operator is using this browser", for_ms: BUSY_FOR_MS });
}

/**
 * One command in, one answer out.
 *
 * Exactly once, including the failures: a command left unanswered is read by
 * the backend as a device that went away, which fails the run in a way that
 * blames the browser rather than the page. And answered once, not twice --
 * a second answer to an id that has already been settled would be applied to
 * whatever the backend had moved on to.
 */
async function handle(open_, raw) {
  let command;
  try {
    command = JSON.parse(raw);
  } catch {
    // Nothing to answer: without a command id there is nobody waiting.
    return;
  }
  if (!command || typeof command.command_id !== "string") return;
  if (answered.has(command.command_id)) return;
  answered.add(command.command_id);
  // Bounded, because this worker may live for hours of a busy run. Old ids
  // cannot come back: the backend mints a fresh one per command.
  if (answered.size > 500) answered = new Set();

  const deadline = Number(command.deadline_ms) || 20_000;
  const answer = await Promise.race([
    commands.perform(command),
    new Promise((resolve) =>
      setTimeout(
        () =>
          resolve({
            ok: false,
            // The same word the backend uses when nothing arrives at all, so a
            // command this browser gave up on and one it never answered read
            // the same in the run's record.
            error: { kind: "timeout", detail: `not done within ${deadline}ms` },
          }),
        deadline,
      ),
    ),
  ]);

  send(open_, { command_id: command.command_id, ...answer });
}
