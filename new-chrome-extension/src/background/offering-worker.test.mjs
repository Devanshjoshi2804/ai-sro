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
/** What the rig says the started run looks like, for the poll to find.
 *
 * Deliberately not `running`: the poll only asks again while it is, and a test
 * that left a one-second timer behind would hold the process open forever.
 */
let rigRunServed = { id: "run-9", outcome: "held", steps: [] };
/** A rig that cannot be reached, for the tick that has to be retried. */
let rigRunFails = false;
let shapesServed = [SHAPE];

/** The rig, as far as this browser can tell. Re-installed by `ready()`: a test
 * that swaps it for one of its own must not leave every later test dialling
 * that one. */
const rigServer = async (url, options = {}) => {
  const path = String(url).slice(RIG.length).split("?")[0];
  calls.push({ path, method: options.method || "GET", body: options.body });
  if (path === "/v1/shapes") return json({ shapes: shapesServed });
  if (path === "/v1/offers") return json({ offer_id: "off_1" });
  if (path === "/v1/runs") return json({ run_id: "run-9" });
  if (path === "/v1/runs/run-9") {
    return rigRunFails ? json({ detail: "the rig is down" }, 503) : json(rigRunServed);
  }
  if (path === "/v1/runs/run-9/approve") return json({ ok: true });
  return json({ detail: `nothing serves ${path}` }, 404);
};

globalThis.fetch = rigServer;

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
  rigRunServed = { id: "run-9", outcome: "held", steps: [] };
  rigRunFails = false;
  globalThis.fetch = rigServer;
  held.set("sro.token", "tok");
  held.set("sro.deviceId", "dev-1");
  held.set("sro.policy", { capture_enabled: true });
  held.set("sro.watched", [{ tabId: TAB, host: "wms.example", since: 1 }]);
  held.set("sro.rigUrl", RIG);
  held.set("sro.rigToken", "rig-tok");
}

// -- the tests ----------------------------------------------------------------

// FIRST ON PURPOSE. `shapesFor` holds a non-empty answer for five minutes in
// module scope, so the moment any test in this process has seen a shape every
// later one is served from that cache -- and this is the one test that needs
// the rig asked twice.
test("an empty answer from the rig is not cached, so the first shape it proves is offered on", async () => {
  ready();
  shapesServed = [];

  await gesture("a", "NEW");
  const askedWhileEmpty = calls.filter((call) => call.path === "/v1/shapes").length;
  assert.ok(askedWhileEmpty >= 1, "the rig was never asked for its shapes");

  // The rig proves its first job. Held for five minutes, the empty list would
  // still be what this browser matched against.
  shapesServed = [SHAPE];
  await gesture("a", "NEW");
  await gesture("b", "north");
  await until(() => openOnes().length === 1, "a rig that had answered [] once was never asked again");
  assert.ok(
    calls.filter((call) => call.path === "/v1/shapes").length > askedWhileEmpty,
    "the empty answer was cached",
  );
});

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

  // Exactly one. The offer leaves `open` before the POST rather than after it,
  // so a sweep or a gesture landing while the run was starting found a record
  // already claimed and had no fate of its own to report.
  await new Promise((resolve) => setTimeout(resolve, 30));
  assert.equal(offersSent().length, 1, "one offer reported two fates");
});

test("an offer taken has left open before the run is asked for, so nothing else can end it", async () => {
  // The window this closes: the POST takes as long as the rig takes, and while
  // it was in flight the offer was still `open`. A drop landing meanwhile ended
  // it and reported a dismissal; the accept that followed reported a second
  // fate for the same offer -- with a live run in a warehouse behind it.
  ready();
  await gesture("a", "NEW");
  await gesture("b", "north");
  await until(() => openOnes().length === 1, "no offer to accept");
  const offer = openOnes()[0];

  let whileStarting = null;
  globalThis.fetch = async (url, options = {}) => {
    if (String(url).slice(RIG.length) === "/v1/runs") {
      whileStarting = nudges().find((n) => n.id === offer.id).state;
      await send({ kind: "drop-nudge", nudgeId: offer.id });
    }
    return rigServer(url, options);
  };

  const answer = await send({ kind: "start-rig-run", nudgeId: offer.id, values: {} });

  assert.deepEqual(answer, { ok: true, run_id: "run-9" });
  assert.equal(whileStarting, "accepted", "the offer was still open while its run was being started");
  assert.equal(nudges().find((n) => n.id === offer.id).state, "accepted");
  await new Promise((resolve) => setTimeout(resolve, 30));
  assert.deepEqual(offersSent().map((each) => each.fate), ["accepted"], "one offer reported two fates");
});

test("a start whose POST fails leaves the offer open and reports nothing", async () => {
  // The other side of claiming it early. The offer is marked accepted before
  // the run is asked for; if the rig refuses, nothing happened, and an offer
  // stuck on `accepted` is one the operator can neither take nor refuse.
  ready();
  await gesture("a", "NEW");
  await gesture("b", "north");
  await until(() => openOnes().length === 1, "no offer to accept");
  const offer = openOnes()[0];

  globalThis.fetch = async (url, options = {}) => {
    const path = String(url).slice(RIG.length);
    calls.push({ path, method: options.method || "GET", body: options.body });
    if (path === "/v1/runs") return json({ detail: "the rig is down" }, 503);
    return rigServer(url, options);
  };

  const answer = await send({ kind: "start-rig-run", nudgeId: offer.id, values: {} });

  assert.equal(answer.ok, false);
  assert.equal(nudges().find((n) => n.id === offer.id).state, "open", "a refused start ended the offer");
  assert.equal(held.get("sro.activeRun"), undefined, "a run that never started is being drawn");
  await new Promise((resolve) => setTimeout(resolve, 30));
  assert.deepEqual(offersSent(), [], "a start that failed reported a fate");

  // And it is still the operator's to answer.
  assert.deepEqual(await send({ kind: "drop-nudge", nudgeId: offer.id }), { ok: true });
  assert.equal(nudges().find((n) => n.id === offer.id).state, "dismissed");
});

test("a backend nudge a prefix match supersedes ends as expired, not as nothing", async () => {
  // Two open at once is the queue this design exists to not be, so the arrival
  // nudge goes when the rig recognises the job for real. Dropping the record
  // altogether loses an offer that was made and shown, which is the one thing
  // the day is drawn from.
  ready();
  const arrival = {
    id: "n_arrival", at: new Date().toISOString(), title: "Create Work Area",
    startsOn: PAGE, tabId: TAB, state: "open", source: "backend",
    workflowId: null, k: 0, values: {}, missing: [], parameters: [],
  };
  held.set("sro.nudges", [arrival]);

  await gesture("a", "NEW");
  await gesture("b", "north");
  await until(() => openOnes()[0]?.source === "rig", "the prefix match never landed");

  assert.equal(openOnes().length, 1, "two offers are open at once");
  const was = nudges().find((n) => n.id === "n_arrival");
  assert.ok(was, "the arrival nudge was thrown away rather than ended");
  assert.equal(was.state, "expired");
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

test("the run the rig is driving is drawn while it runs, and Approve reaches the rig", async () => {
  // Two halves of the same gate. The panel can only show a live rig run if
  // something in this worker keeps asking the rig for it -- nothing pushes --
  // and the Approve on that row has to land on the rig without the panel ever
  // holding the bearer, which is why it is a message and not a fetch.
  ready();
  await gesture("a", "NEW");
  await gesture("b", "north");
  await until(() => openOnes().length === 1, "no offer to accept");

  await send({ kind: "start-rig-run", nudgeId: openOnes()[0].id, values: {} });
  await until(
    () => calls.some((call) => call.path === "/v1/runs/run-9"),
    "nothing asked the rig what the run it had just started was doing",
  );

  // Live in this browser, as it is once the rig's channel has had a command
  // performed for it -- which is also what records that the rig is driving.
  await perform({ run_id: "run-9", kind: "nothing-doing" }, "rig");
  const shown = (await send({ kind: "status" })).performing;
  assert.equal(shown.source, "rig");
  assert.equal(shown.run?.id, "run-9", "the panel was told a rig run is happening but not which");
  abort("run-9");

  const answer = await send({ kind: "approve-rig-run", runId: "run-9" });
  const approve = calls.find((call) => call.path === "/v1/runs/run-9/approve");
  assert.ok(approve, "Approve never reached the rig");
  assert.equal(approve.method, "POST");
  assert.deepEqual(
    JSON.parse(approve.body),
    { device_id: "dev-1" },
    "the tap names the browser it came from, and the route wants a JSON body",
  );
  assert.deepEqual(answer, { ok: true });
});

/** How many times this browser has asked the rig what the run is doing. */
const asked = () => calls.filter((call) => call.path === "/v1/runs/run-9").length;

test("a rig run this browser did not start is polled from status, and a failed ask is asked again", async () => {
  // No `start-rig-run` here. `commands.js` writes this record for every command
  // that arrives on the rig's channel, whoever started the run -- a run started
  // from the rig's own screen, or one this worker was evicted in the middle of
  // -- and none of those routes goes through the panel's press.
  ready();
  held.set("sro.activeRun", { runId: "run-9", at: Date.now(), source: "rig" });
  rigRunFails = true;

  await send({ kind: "status" });
  await until(() => asked() === 1, "opening the panel over a rig run asked the rig nothing");
  // One ask per status read, however slow the rig is. Without the in-flight
  // guard the panel's two-second poll would stack a request per read on top of
  // the timer's own.
  await new Promise((resolve) => setTimeout(resolve, 30));
  assert.equal(asked(), 1, "one status read asked the rig more than once");

  // The rig comes back. Nothing rescheduled off a *successful* answer here --
  // the first ask failed -- so if a failed tick did not keep the chain alive,
  // this next status read is the only thing left that can restart it.
  rigRunFails = false;
  await send({ kind: "status" });
  await until(() => asked() >= 2, "a poll whose first ask failed was never asked again");

  held.delete("sro.activeRun");
});

test("a run parked on an approval is still drawn, and nothing is offered over it", async () => {
  // The failure this exists for: `commands.js` calls a run over thirty seconds
  // after its last command, and a write waiting on a person can wait five
  // minutes. For four and a half of them the panel showed no run, no steps and
  // no Approve -- the one control the run was actually waiting on.
  ready();
  rigRunServed = {
    id: "run-9",
    outcome: "running",
    steps: [{ order: 0, says: "save the work area", verdict: "awaiting" }],
  };
  held.set("sro.activeRun", { runId: "run-9", at: Date.now(), source: "rig" });

  let shown = null;
  for (let tries = 0; tries < 200 && !shown?.run; tries += 1) {
    shown = (await send({ kind: "status" })).performing;
    if (!shown?.run) await new Promise((resolve) => setTimeout(resolve, 5));
  }
  assert.ok(shown, "a run waiting on an approval vanished from the panel");
  assert.equal(shown.source, "rig");
  assert.equal(shown.kind, "rig");
  assert.equal(shown.run?.id, "run-9");
  assert.equal(shown.run.steps[0].outcome, "awaiting");

  // And no offer over it. The gestures arriving now are the operator doing that
  // very step by hand while the rig waits, and offering to start a second run
  // on top of a parked write is the worst moment this panel has.
  await gesture("a", "NEW");
  await gesture("b", "north");
  await new Promise((resolve) => setTimeout(resolve, 60));
  assert.deepEqual(openOnes(), [], "it offered a run over a write parked for approval");

  held.delete("sro.activeRun");
});

test("Approve is refused for a run this browser is not driving", async () => {
  // The panel draws Approve off a status read that can be seconds old. A card
  // left standing after the run ended, or a second window showing a superseded
  // one, must not be able to authorise a live write against it.
  ready();
  held.set("sro.activeRun", { runId: "run-9", at: Date.now(), source: "rig" });

  assert.deepEqual(await send({ kind: "approve-rig-run", runId: "run-8" }), {
    ok: false,
    error: "that run is not the one this browser is driving",
  });
  assert.equal(
    calls.filter((call) => call.path.endsWith("/approve")).length,
    0,
    "a write was approved against a run this browser is not driving",
  );

  held.delete("sro.activeRun");
});
