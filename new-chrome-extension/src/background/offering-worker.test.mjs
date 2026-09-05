// Self-check for the offer paths that live in service-worker.js: recognising a
// job from a live gesture, taking the offer, and dropping it.
//
// `decideOffer` is pure and tested in `offering.test.mjs`. What is here is
// everything the worker does *around* it -- which record it writes, what it
// tells the rig, and what it refuses to do -- because that is where the two
// defects this file exists for lived: an upgraded offer reported a dismissal
// nobody made, and a run was accepted by writing back a list read before the
// POST that started it.
//
// Same scaffolding as `rig-settings.test.mjs`: `case "gesture"` and the panel's
// messages live inside an unexported dispatcher, so reaching them means
// standing up the worker's module-scope wiring. None of it runs anything real.
//
// Run with `node src/background/offering-worker.test.mjs`.

import assert from "node:assert/strict";
import test from "node:test";

import { fakeIndexedDB } from "./test-support/fake-indexeddb.mjs";

globalThis.indexedDB = fakeIndexedDB();

const held = new Map();
/** Every script the worker painted into a page: the nudge pill, mostly. */
const painted = [];

globalThis.chrome = {
  storage: {
    local: {
      get: async (key) => (held.has(key) ? { [key]: held.get(key) } : {}),
      set: async (pairs) => {
        for (const [key, value] of Object.entries(pairs)) held.set(key, value);
      },
      remove: async (keys) => {
        for (const key of [keys].flat()) held.delete(key);
      },
    },
  },
  runtime: {
    onInstalled: { addListener: () => {} },
    onStartup: { addListener: () => {} },
    onMessage: {
      addListener: (fn) => {
        globalThis.__handle = fn;
      },
    },
    getManifest: () => ({ version: "0.0.0-test" }),
    sendMessage: () => {},
  },
  alarms: { create: () => {}, onAlarm: { addListener: () => {} } },
  webNavigation: {
    onCommitted: { addListener: () => {} },
    onCompleted: { addListener: () => {} },
    onCreatedNavigationTarget: { addListener: () => {} },
  },
  tabs: {
    onRemoved: { addListener: () => {} },
    get: async (tabId) => ({ id: tabId, url: PAGE }),
    captureVisibleTab: async () => {
      throw new Error("no pictures in a test");
    },
  },
  scripting: {
    executeScript: async (call) => {
      painted.push(call);
      return [];
    },
  },
  action: {
    setBadgeText: async () => {},
    setBadgeBackgroundColor: async () => {},
    setTitle: async () => {},
  },
  sidePanel: { open: async () => {}, setPanelBehavior: async () => {} },
};

// -- the rig, as far as this browser can tell --------------------------------

const RIG = "http://rig.test";
const H = "https://wms.example";
const PAGE = `${H}/wa`;
const TAB = 1;

const SHAPE = {
  id: "wfl_wa",
  title: "Create Work Area",
  held_runs: 2,
  starts_on: PAGE,
  shape: [
    [H, "a", "type"],
    [H, "b", "type"],
    [H, "c", "type"],
    [H, "d", "type"],
  ],
  parameters: [{ name: "workArea", at: 0 }],
};

/** Every call this browser made to the rig, in order. */
let calls = [];
let shapesServed = [SHAPE];

globalThis.fetch = async (url, options = {}) => {
  const path = String(url).slice(RIG.length);
  calls.push({ path, method: options.method || "GET", body: options.body });
  if (path === "/v1/shapes") return json({ shapes: shapesServed });
  if (path === "/v1/offers") return json({ offer_id: "off_1" });
  if (path === "/v1/runs") return json({ run_id: "run-9" });
  return json({ detail: `nothing serves ${path}` }, 404);
};

function json(body, status = 200) {
  return {
    ok: status < 400,
    status,
    statusText: "",
    json: async () => body,
  };
}

const offersSent = () => calls.filter((call) => call.path === "/v1/offers").map((call) => JSON.parse(call.body));

await import("./service-worker.js");
const { perform, abort } = await import("./commands.js");

// -- driving it ---------------------------------------------------------------

function send(message, sender = {}) {
  return new Promise((resolve) => {
    globalThis.__handle(message, sender, resolve);
  });
}

/** One gesture on the watched tab, as the content script sends it. */
function gesture(identity, value) {
  return send(
    {
      kind: "gesture",
      frameUrl: PAGE,
      gesture: { url: PAGE, target: { component: { itemId: identity } }, kind: "type", value, at: 1 },
    },
    { tab: { id: TAB, url: PAGE } },
  );
}

/** The offer is made off the gesture path, not on it -- `considerOffer` is
 * deliberately not awaited so recognising a job may never cost recording one.
 * So the test waits for the answer rather than assuming it has landed. */
async function until(what, why) {
  for (let tries = 0; tries < 200; tries++) {
    if (what()) return;
    await new Promise((resolve) => setTimeout(resolve, 5));
  }
  assert.fail(why);
}

const nudges = () => held.get("sro.nudges") || [];
const openOnes = () => nudges().filter((n) => n.state === "open");

function ready() {
  held.clear();
  calls = [];
  painted.length = 0;
  shapesServed = [SHAPE];
  held.set("sro.token", "tok");
  held.set("sro.deviceId", "dev-1");
  held.set("sro.policy", { capture_enabled: true });
  held.set("sro.watched", [{ tabId: TAB, host: "wms.example", since: 1 }]);
  held.set("sro.rigUrl", RIG);
  held.set("sro.rigToken", "rig-tok");
}

// -- the tests ----------------------------------------------------------------

test("two gestures into a proven job become one offer, and a third upgrades it", async () => {
  ready();

  await gesture("a", "NEW");
  await gesture("b", "north");
  await until(() => openOnes().length === 1, "two gestures into the job offered nothing");

  const first = openOnes()[0];
  assert.equal(first.source, "rig");
  assert.equal(first.workflowId, "wfl_wa");
  assert.equal(first.k, 2);
  assert.deepEqual(first.values, { workArea: "NEW" });

  // The pill says the task's name and only that: `paintNudge` wraps whatever
  // it is given in "do ...?", so a sentence would render as a question about a
  // question.
  const pill = painted.at(-1);
  assert.deepEqual(pill.args.slice(1, 2), ["Create Work Area"]);

  await gesture("c", "x");
  await until(() => openOnes()[0]?.k === 3, "the third gesture did not carry the offer further");

  // One record, still the same one. A longer prefix is the same offer knowing
  // more, so nothing ended and the rig was told about no fate at all.
  assert.equal(nudges().length, 1, "the upgrade left a second record behind");
  assert.equal(openOnes()[0].id, first.id, "the upgrade minted a new offer");
  assert.equal(openOnes()[0].at, first.at, "the upgrade moved when the offer was made");
  assert.deepEqual(offersSent(), [], `an upgrade reported ${JSON.stringify(offersSent())}`);
});

test("nothing is offered while this browser is performing a run", async () => {
  ready();
  await gesture("a", "NEW");

  // A run is driving the browser. The gestures arriving now are its own.
  await perform({ run_id: "run-live", kind: "nothing-doing" });
  await gesture("b", "north");

  // Long enough for the offer to have appeared if the guard were not there:
  // the same wait the test above needs to see one.
  await new Promise((resolve) => setTimeout(resolve, 60));
  assert.deepEqual(openOnes(), [], "it offered over a run it was already performing");

  abort("run-live");
});

test("yes starts the run, and marks the offer accepted on the list as it is then", async () => {
  ready();
  await gesture("a", "NEW");
  await gesture("b", "north");
  await until(() => openOnes().length === 1, "no offer to accept");
  const offer = openOnes()[0];

  const answer = await send({ kind: "start-rig-run", nudgeId: offer.id, values: { description: "dock" } });

  assert.deepEqual(answer, { ok: true, run_id: "run-9" });
  const started = JSON.parse(calls.find((call) => call.path === "/v1/runs").body);
  assert.equal(started.workflow_id, "wfl_wa");
  assert.equal(started.from_step, 2);
  // What the panel was told wins over what the page was read for, and what the
  // page gave is still there.
  assert.deepEqual(started.values, { workArea: "NEW", description: "dock" });

  assert.equal(nudges().find((n) => n.id === offer.id).state, "accepted");
  assert.deepEqual(held.get("sro.activeRun"), { runId: "run-9", at: held.get("sro.activeRun").at, source: "rig" });
  await until(() => offersSent().length === 1, "the rig was never told the offer was taken");
  assert.equal(offersSent()[0].fate, "accepted");
  assert.equal(offersSent()[0].run_id, "run-9");
  assert.equal(offersSent()[0].k, 2);
});

test("marking accepted does not write back a list read before the run started", async () => {
  ready();
  await gesture("a", "NEW");
  await gesture("b", "north");
  await until(() => openOnes().length === 1, "no offer to accept");
  const offer = openOnes()[0];

  // Something else writes the list while the POST is in flight -- a sweep, a
  // gesture on another tab. Writing back the copy read before the POST would
  // silently undo it.
  const meanwhile = { id: "n_other", state: "open", source: "backend", tabId: 2, at: offer.at };
  globalThis.fetch = async (url, options = {}) => {
    const path = String(url).slice(RIG.length);
    calls.push({ path, method: options.method || "GET", body: options.body });
    if (path === "/v1/runs") {
      held.set("sro.nudges", [...(held.get("sro.nudges") || []), meanwhile]);
      return json({ run_id: "run-9" });
    }
    if (path === "/v1/offers") return json({ offer_id: "off_1" });
    if (path === "/v1/shapes") return json({ shapes: shapesServed });
    return json({ detail: "no" }, 404);
  };

  await send({ kind: "start-rig-run", nudgeId: offer.id, values: {} });

  assert.ok(
    nudges().some((n) => n.id === "n_other"),
    "accepting the offer threw away a record written while the run was starting",
  );
  assert.equal(nudges().find((n) => n.id === offer.id).state, "accepted");
});

test("dropping an offer ends it and says so once", async () => {
  ready();
  await gesture("a", "NEW");
  await gesture("b", "north");
  await until(() => openOnes().length === 1, "no offer to drop");
  const offer = openOnes()[0];

  assert.deepEqual(await send({ kind: "drop-nudge", nudgeId: offer.id }), { ok: true });
  assert.equal(nudges().find((n) => n.id === offer.id).state, "dismissed");
  await until(() => offersSent().length === 1, "the rig was never told the offer was refused");
  assert.equal(offersSent()[0].fate, "dismissed");

  // Dropping it again, or answering it after it was dropped: an offer with two
  // fates is one the rig cannot count.
  await send({ kind: "drop-nudge", nudgeId: offer.id });
  await send({ kind: "nudge-answer", id: offer.id, answer: "not-here" });
  await new Promise((resolve) => setTimeout(resolve, 30));
  assert.equal(offersSent().length, 1, "one offer reported two fates");
});

test("an offer that was dropped cannot then be started", async () => {
  // The other half of the panel disabling its card on the first press. A stale
  // panel, a second window, or a card the ledger never redrew would otherwise
  // send "no" and then "yes" for one offer -- a live run in somebody's
  // warehouse, off an offer already reported dismissed.
  ready();
  await gesture("a", "NEW");
  await gesture("b", "north");
  await until(() => openOnes().length === 1, "no offer to drop");
  const offer = openOnes()[0];

  await send({ kind: "drop-nudge", nudgeId: offer.id });
  const answer = await send({ kind: "start-rig-run", nudgeId: offer.id, values: { description: "dock" } });

  assert.deepEqual(answer, { ok: false, error: "this offer has already ended" });
  assert.equal(calls.filter((call) => call.path === "/v1/runs").length, 0, "a dropped offer started a run");
  assert.equal(nudges().find((n) => n.id === offer.id).state, "dismissed");
  await new Promise((resolve) => setTimeout(resolve, 30));
  assert.deepEqual(offersSent().map((each) => each.fate), ["dismissed"], "one offer reported two fates");
});

// Not tested here: that a browser with no rig writes no tail. `shapesFor`
// caches for five minutes in module scope, so once any test in this process
// has seen a shape every later one does too, and a test that ran first would
// cache the empty list for every test after it.
