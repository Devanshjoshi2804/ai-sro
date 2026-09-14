// A click is not over when the click returns.
//
// Sign In is a form submit: the in-page action dispatches and answers at once,
// and the run then photographs a page that has not started navigating yet. On
// a real login that cost a step -- username typed, password typed from the
// vault, Sign In pressed, and the verifier reporting "the browser remains on
// the Keycloak login page with the sign-in form still visible", about a login
// that had in fact worked.
//
// So a click waits for the page to react. What is held here is that the wait
// is bounded at both ends: it ends early when nothing loads, it ends when the
// load completes, and typing never waits at all.
//
// Run with `node src/background/reacting.test.mjs`.

import assert from "node:assert";
import { test } from "node:test";

let listeners = [];
let times = [];

/** Chrome's clock, as far as this module is concerned. Every `setTimeout` is
 * recorded rather than run, so a test can say what happened and in which
 * order without waiting real seconds for it. */
function fireAfter(ms) {
  for (const fire of times.filter((one) => one.ms <= ms && !one.done)) {
    fire.done = true;
    fire.fn();
  }
}

globalThis.chrome = {
  tabs: {
    query: async () => [{ id: 7, url: "https://keycloak.test/auth", active: true }],
    get: async () => ({ id: 7, url: "https://keycloak.test/auth" }),
    update: async () => ({}),
    onUpdated: {
      addListener: (fn) => listeners.push(fn),
      removeListener: (fn) => {
        listeners = listeners.filter((one) => one !== fn);
      },
    },
  },
  scripting: {
    executeScript: async () => [{ result: { ok: true, result: { matched_by: "css_path" } } }],
  },
};

const realTimeout = globalThis.setTimeout;
globalThis.setTimeout = (fn, ms) => {
  const entry = { fn, ms, done: false };
  times.push(entry);
  return entry;
};
globalThis.clearTimeout = (entry) => {
  if (entry && typeof entry === "object") entry.done = true;
};

const { perform } = await import("./commands.js");

function acting(action) {
  listeners = [];
  times = [];
  return perform({
    command_id: "cmd-1",
    kind: "ui.perform",
    payload: { action, origin: "https://keycloak.test", locators: [{ query: "button" }] },
  });
}

/** Let the promise chain inside `perform` get as far as it can. */
const settle = () => new Promise((resolve) => realTimeout(resolve, 0));

test("a click that navigates is not answered until the page has loaded", async () => {
  const answering = acting("click");
  await settle();
  const [watch] = listeners;
  assert.ok(watch, "nothing was watching the tab after a click");

  watch(7, { status: "loading" });
  // The early exit's moment passes with the page loading: it must not end the
  // wait, or the run photographs the page mid-navigation.
  fireAfter(900);
  await settle();
  assert.equal(times.filter((one) => !one.done).length > 0, true);

  watch(7, { status: "complete" });
  await answering;
  assert.deepEqual(listeners, [], "the listener outlived the command that added it");
});

test("a click that navigates nowhere does not hold the run up", async () => {
  const answering = acting("click");
  await settle();

  // Nothing loads. A click that opens a menu is most clicks, and a run that
  // waited on every one of them would spend a second a step doing nothing.
  fireAfter(900);

  const answer = await answering;
  assert.equal(answer.ok, true);
  assert.deepEqual(listeners, []);
});

test("a page that never finishes loading still gets looked at", async () => {
  const answering = acting("click");
  await settle();
  const [watch] = listeners;

  watch(7, { status: "loading" });
  fireAfter(8_000);

  await answering;
  assert.deepEqual(listeners, [], "a page held open by a script stopped the run instead");
});

test("typing does not wait for anything", async () => {
  const answer = await acting("type");

  assert.equal(answer.ok, true);
  assert.deepEqual(listeners, [], "a keystroke waited on a navigation that was never coming");
});
