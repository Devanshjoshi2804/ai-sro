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

/** How long a burst of typing asks the backend to hold off, and how often that
 * is worth saying. Short, because it is renewed by the next keystroke and a
 * device that overstates how busy it is delays its own work. */
const BUSY_FOR_MS = 5_000;
const BUSY_EVERY_MS = 4_000;

/**
 * One command channel: a socket that dials out, announces itself, keeps
 * itself alive, answers every command exactly once, and redials after a drop.
 *
 * `dial()` answers `{ url, protocols }` or `null` for "do not open one now".
 * `describe` names the channel in error messages. Everything else -- the
 * keepalive, the exactly-once answering, the backoff -- is the same for every
 * channel, which is the point of the factory: the rig gets the backend's
 * socket verbatim, not a second implementation of it.
 *
 * `perform` is an option only so a test can hand in a stub: an ES module
 * namespace is read-only, so `commands.perform` cannot be replaced from
 * outside. Production passes nothing and gets the real one.
 */
export function createChannel({ describe, dial, perform = commands.perform }) {
  // `describe` is this channel's own fallback name, used only when a command
  // carries no `source` of its own -- see `handle()`'s call to `perform`
  // below. There is one channel for both a rig run and a skill run, so
  // `describe` alone cannot say which a given command belongs to.
  let socket = null;
  let keepalive = null;
  let retryIn = FIRST_RETRY_MS;
  let retryTimer = null;
  let answered = new Set();
  let lastBusy = 0;

  function status() {
    if (!socket) return "closed";
    return socket.readyState === WebSocket.OPEN ? "open" : "connecting";
  }

  /**
   * Make the socket match what is stored: open when `dial()` answers a target,
   * closed when it answers `null`.
   *
   * For the backend that is: open when this browser is registered and not
   * switched off by an administrator. The operator's own pause is deliberately
   * not a reason to close it. That switch says "stop watching me"; a skill they
   * asked for is not watching, and a device that goes unreachable whenever
   * somebody pauses observation is a device nobody can schedule work on.
   */
  async function settle() {
    const target = await dial();
    if (!target) {
      close();
      return;
    }
    if (socket) return;
    open(target.url, target.protocols);
  }

  function close() {
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

  function open(url, protocols) {
    let opening;
    try {
      opening = new WebSocket(url, protocols);
    } catch (error) {
      void state.setLastError(`the ${describe} command channel could not be opened: ${error}`);
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
    // A no-op in Chrome, where `setTimeout` returns a number. In node -- which
    // is where this extension's own suites run this file -- a pending timer
    // holds the process open, and both of these reschedule themselves
    // forever: a suite that imports the service worker sat waiting for an
    // event loop that would never drain, for 404 seconds, until the runner
    // was killed. Retrying a socket is not a reason to keep a process alive.
    retryTimer?.unref?.();
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
    keepalive?.unref?.();
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
      void state.setLastError(`the ${describe} command channel would not carry an answer: ${error}`);
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
  function operatorIsWorking() {
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
      // `command.source`, not `describe`. There is one socket for both a
      // workflow run and a skill run, so `describe` -- this channel's own
      // fixed name -- cannot tell them apart; only the backend, sending the
      // command, knows which engine sent it. A rig command with no `source`
      // (an older backend) still falls back to `describe`.
      perform(command, command.source || describe),
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

  return { status, settle, close, operatorIsWorking };
}

// The backend's channel, exactly as before: every export this module had.
//
// The credential and the device's secret both ride in the subprotocol, not
// the query string: a browser cannot set a header on a WebSocket, and a
// token in the URL is a token in every access log and every referrer. Two of
// them because a tenant credential says which tenant and never which
// browser, and this socket is how work is handed to one.
//
// No secret is no channel, deliberately: the backend would close it anyway,
// and dialling once a second at a door that will not open is how a device
// that has fallen behind becomes a device that is hammering the backend. The
// heartbeat is what re-registers and gets one; the next tick dials.
/** Why the backend channel is not dialling, in the words the panel shows.
 *
 * Four different states close this socket and they used to render identically
 * -- "the command channel is closed" -- so an operator looking at the card
 * could not tell a browser an administrator had switched off from one whose
 * secret had gone, and neither could anybody reading a bug report. Written
 * from inside `dial` rather than computed beside it, because a second copy of
 * this condition is how the reason would come to disagree with the socket. */
let backendWhy = "";

const backend = createChannel({
  describe: "backend",
  async dial() {
    const [token, deviceId, secret, serverPaused, apiUrl] = await Promise.all([
      state.token(),
      state.deviceId(),
      state.deviceSecret(),
      state.serverPaused(),
      state.apiUrl(),
    ]);
    // In the order somebody would fix them.
    backendWhy = !token
      ? "this browser has no credential"
      : !deviceId
        ? "this browser is not registered yet"
        : !secret
          ? "this browser has no device secret — the next heartbeat fetches one"
          : serverPaused
            ? "an administrator switched this browser off"
            : "";
    if (backendWhy) return null;
    return {
      url: `${apiUrl.replace(/^http/, "ws")}/v1/agents/${encodeURIComponent(deviceId)}/commands`,
      protocols: ["bearer", token, secret],
    };
  },
});

export const status = backend.status;
/** Empty while the socket has a target to dial, whether or not it is open --
 * so a channel that is merely connecting says nothing here. */
export const why = () => backendWhy;
export const settle = backend.settle;
export const close = backend.close;
export const operatorIsWorking = backend.operatorIsWorking;
