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
// The scaffolding `rig-settings.test.mjs` used to carry, inherited here when
// phase 5 deleted that suite with its subject: `case "gesture"`, the panel's
// messages and the two lifecycle hooks live inside service-worker.js's own
// module scope, so reaching them means standing the whole of it up. None of it
// runs anything real -- every hook below is a no-op or a recorder.
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
    // Held rather than dropped: the retired-key removal is wired to both, and
    // a listener nothing can call is a migration nothing can check.
    onInstalled: {
      addListener: (fn) => {
        globalThis.__installed = fn;
      },
    },
    onStartup: {
      addListener: (fn) => {
        globalThis.__started = fn;
      },
    },
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
    // `settle()`, which both lifecycle hooks kick, re-registers the content
    // scripts. Nothing here registers anything.
    getRegisteredContentScripts: async () => [],
    unregisterContentScripts: async () => {},
    registerContentScripts: async () => {},
  },
  permissions: { getAll: async () => ({ origins: [] }), contains: async () => false },
  action: {
    setBadgeText: async () => {},
    setBadgeBackgroundColor: async () => {},
    setTitle: async () => {},
  },
  sidePanel: { open: async () => {}, setPanelBehavior: async () => {} },
};

// -- the rig, as far as this browser can tell --------------------------------

const RIG = "http://rig.test";
/** `DEFAULT_API_URL` in `state.js`, which is what `ready()` leaves in place. */
const BACKEND = "http://localhost:8000";
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
/** How the backend answers the approve door, for the test that a refusal is
 * one. `null` is the door letting the write out. */
let approveRefusal = null;

/** How the backend answers `POST /v1/offers`, for the test that a refusal is
 * `false` and never a throw. `null` is the door recording the fate. */
let offerRefusal = null;

/** The rig and the backend, as far as this browser can tell. Re-installed by
 * `ready()`: a test that swaps it for one of its own must not leave every later
 * test dialling that one.
 *
 * Two bases, told apart by which one the url starts with, because the point of
 * phase 5 is that calls move between them -- a server that assumed one base
 * would record a call to the other under a mangled path and match nothing.
 * `base`, `query` and `headers` are kept as well as the path: which door was
 * knocked on is only half of what any of these calls has to get right.
 *
 * **The rig serves nothing, and nothing points this browser at it any more.**
 * Every door this browser knocks on is the backend's, so a call that reverted
 * to the rig's base, or to the rig's `/v1/runs*` paths on the backend's base,
 * gets the same 404 a real backend would give it -- which is what makes the
 * mutations die rather than pass. `RIG` is kept for exactly that: it is now
 * "any base that is not the backend", not a server this browser can be
 * configured to reach. */
const rigServer = async (url, options = {}) => {
  const full = String(url);
  const base = full.startsWith(BACKEND) ? BACKEND : RIG;
  const [path, query = ""] = full.slice(base.length).split("?");
  calls.push({
    base,
    path,
    query,
    method: options.method || "GET",
    body: options.body,
    headers: options.headers || {},
  });
  if (base !== BACKEND) return json({ detail: `the rig serves nothing: ${path}` }, 404);
  if (path === "/v1/workflow-runs/run-9/approve") {
    return approveRefusal
      ? json({ detail: approveRefusal.detail }, approveRefusal.status)
      : json({ order: 0, first: true });
  }
  if (path === "/v1/shapes") return json({ shapes: shapesServed });
  if (path === "/v1/offers") {
    return offerRefusal
      ? json({ detail: offerRefusal.detail }, offerRefusal.status)
      : json({ offer_id: "off_1" }, 201);
  }
  // The backend answers the whole row, where the rig answered `{run_id}`.
  if (path === "/v1/workflow-runs") return json({ ...rigRunServed, id: "run-9" }, 201);
  if (path === "/v1/workflow-runs/run-9/abort") return json({ ...rigRunServed }, 202);
  if (path === "/v1/workflow-runs/run-9") {
    return rigRunFails ? json({ detail: "the backend is down" }, 503) : json(rigRunServed);
  }
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
  approveRefusal = null;
  offerRefusal = null;
  globalThis.fetch = rigServer;
  // Distinctive on purpose. `dev-1` was the literal that a mutation of
  // `shapes()`'s `?device_id=` was replaced with, and all 27 suites stayed
  // green -- because every assertion about it was against `dev-1` too.
  held.set("sro.token", "tok-ready-77d3");
  held.set("sro.deviceId", "dev-ready-2f8a");
  held.set("sro.deviceSecret", "secret-ready-b061");
  held.set("sro.policy", { capture_enabled: true });
  held.set("sro.watched", [{ tabId: TAB, host: "wms.example", since: 1 }]);
}

// -- the tests ----------------------------------------------------------------

// FIRST ON PURPOSE, and it is the cache that decides the order. `shapesFor`
// holds a non-empty answer for five minutes in module scope, so the moment any
// test in this process has seen a shape every later one is served from that
// cache and asks nothing. That makes this the only test in the file that can
// pin what the request itself carries, so it does both jobs.
test("an empty answer is not cached, and the shapes asked for are this browser's", async () => {
  // The survivor task 1 found and could not fix from inside its own subject:
  // `?device_id=` is the only caller-supplied value `shapes()` sends, and
  // replacing it with the literal `dev-1` left all 27 suites green -- because
  // the one browser any test named was `dev-1`. A job's rest is per browser --
  // three refusals quiet it for the browser that refused and for nobody else
  // -- so one browser served another's shapes is one operator spending a
  // colleague's rest, silently, forever.
  //
  // Half a pair is worse than useless: `asking_device` answers a `?device_id=`
  // with no `X-Device-Secret` beside it with a 404, and `shapes()` turns every
  // failure into `[]`, so the whole recogniser would go quiet with nothing
  // anywhere going red. Both halves, pinned separately, against what this
  // browser actually holds rather than against a literal.
  ready();
  shapesServed = [];

  await gesture("a", "NEW");
  const askedWhileEmpty = calls.filter((call) => call.path === "/v1/shapes").length;
  assert.ok(askedWhileEmpty >= 1, "nothing was ever asked for this browser's shapes");

  const asking = calls.filter((call) => call.path === "/v1/shapes").at(-1);
  assert.equal(asking.base, BACKEND, "the shapes were asked of something that is not the backend");
  assert.equal(asking.method, "GET");
  assert.equal(
    new URLSearchParams(asking.query).get("device_id"),
    held.get("sro.deviceId"),
    "the shapes request named no browser, or named a browser that is not this one",
  );
  assert.equal(
    asking.headers["X-Device-Secret"],
    held.get("sro.deviceSecret"),
    "the shapes request proved no browser, so `?device_id=` alone is half a pair and a 404",
  );
  assert.equal(asking.headers.Authorization, `Bearer ${held.get("sro.token")}`);
  assert.equal(
    calls.filter((call) => call.base !== BACKEND).length,
    0,
    "something still dialled the rig for shapes",
  );

  // The backend proves its first job. Held for five minutes, the empty list
  // would still be what this browser matched against -- and this is also the
  // successful request the refusal above is measured against.
  shapesServed = [SHAPE];
  await gesture("a", "NEW");
  await gesture("b", "north");
  await until(() => openOnes().length === 1, "a backend that had answered [] once was never asked again");
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
  held.set("sro.deviceId", "dev-start-a17f");
  held.set("sro.deviceSecret", "secret-start-33c9");
  held.set("sro.token", "tok-start-6d20");
  await gesture("a", "NEW");
  await gesture("b", "north");
  await until(() => openOnes().length === 1, "no offer to accept");
  const offer = openOnes()[0];

  const answer = await send({ kind: "start-rig-run", nudgeId: offer.id, values: { description: "dock" } });

  assert.deepEqual(answer, { ok: true, run_id: "run-9" });
  const press = calls.find((call) => call.path === "/v1/workflow-runs");
  assert.ok(press, "the press never reached `POST /v1/workflow-runs`");
  assert.equal(press.base, BACKEND, "the press went somewhere that is not the backend");
  assert.equal(press.method, "POST");
  assert.equal(
    press.headers["X-Device-Secret"],
    held.get("sro.deviceSecret"),
    "the press did not prove this browser",
  );
  assert.equal(press.headers.Authorization, `Bearer ${held.get("sro.token")}`);
  assert.equal(press.headers["Content-Type"], "application/json");
  // The rig's own door, which on this host means a *skill* run keyed on a
  // different id space, was not knocked on instead or as well.
  assert.equal(
    calls.filter((call) => call.path === "/v1/runs").length,
    0,
    "the press still went to `/v1/runs`, which on the backend is a skill run",
  );
  const started = JSON.parse(press.body);
  assert.equal(started.workflow_id, "wfl_wa");
  assert.equal(started.from_step, 2);
  assert.equal(started.live, true);
  assert.equal(started.allow_focus, true);
  // Which browser to drive is a body field here and not the query, unlike
  // every other call in this file: a supervisor's console holds the tenant's
  // credential and no extension of its own, so the browser named is the one to
  // drive and not the one asking. `StartWorkflowRunRequest`'s docstring is
  // where that is decided.
  assert.equal(
    started.device_id,
    held.get("sro.deviceId"),
    "the press named no browser to drive, or named one that is not this browser",
  );
  // `started_by` is gone: the backend reads it off the credential, and a
  // request that says who authorised it is a signature nobody checked.
  assert.equal(started.started_by, undefined, "the press still claims who started it");
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
    if (String(url).slice(BACKEND.length) === "/v1/workflow-runs") {
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
    const path = String(url).slice(BACKEND.length);
    calls.push({ path, method: options.method || "GET", body: options.body });
    if (path === "/v1/workflow-runs") return json({ detail: "the backend is down" }, 503);
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
    const [path] = String(url).slice(BACKEND.length).split("?");
    calls.push({ path, method: options.method || "GET", body: options.body });
    if (path === "/v1/workflow-runs") {
      held.set("sro.nudges", [...(held.get("sro.nudges") || []), meanwhile]);
      return json({ id: "run-9" }, 201);
    }
    if (path === "/v1/offers") return json({ offer_id: "off_1" }, 201);
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
  assert.equal(calls.filter((call) => call.path === "/v1/workflow-runs").length, 0, "a dropped offer started a run");
  assert.equal(nudges().find((n) => n.id === offer.id).state, "dismissed");
  await new Promise((resolve) => setTimeout(resolve, 30));
  assert.deepEqual(offersSent().map((each) => each.fate), ["dismissed"], "one offer reported two fates");
});

test("an offer's fate is recorded against the browser that showed it, in the query and not the body", async () => {
  // `/v1/offers` refuses a request that names no browser with a 403 and writes
  // nothing: an offer is evidence about the browser that showed it, and a row
  // with no browser on it is a shift nobody worked. The rig read the id out of
  // the body; the backend reads it off `?device_id=` + `X-Device-Secret`, and
  // a body field would be a browser this request merely named -- which could
  // spend a colleague's rest, or earn it.
  ready();
  held.set("sro.deviceId", "dev-offer-9b6c");
  held.set("sro.deviceSecret", "secret-offer-1f74");
  held.set("sro.token", "tok-offer-52ad");
  await gesture("a", "NEW");
  await gesture("b", "north");
  await until(() => openOnes().length === 1, "no offer to drop");

  await send({ kind: "drop-nudge", nudgeId: openOnes()[0].id });
  await until(() => calls.some((call) => call.path === "/v1/offers"), "no fate was reported");

  const fate = calls.find((call) => call.path === "/v1/offers");
  assert.equal(fate.base, BACKEND, "the fate went somewhere that is not the backend");
  assert.equal(fate.method, "POST");
  assert.equal(
    new URLSearchParams(fate.query).get("device_id"),
    held.get("sro.deviceId"),
    "the fate named no browser in the query, so the backend refuses it with a 403",
  );
  assert.equal(
    fate.headers["X-Device-Secret"],
    held.get("sro.deviceSecret"),
    "the fate proved no browser, so `?device_id=` alone is half a pair and a 404",
  );
  assert.equal(fate.headers.Authorization, `Bearer ${held.get("sro.token")}`);
  const body = JSON.parse(fate.body);
  assert.equal(body.fate, "dismissed");
  assert.equal(body.workflow_id, "wfl_wa");
  assert.equal(
    body.device_id,
    undefined,
    "the fate still names a browser in the body, which is a name nothing checks",
  );
});

test("an offer the backend refuses is a false, and never a throw", async () => {
  // `f7c00ca` made this answer whether the fate landed, and its one caller
  // still uses `void`. A throw here is an unhandled rejection on a path that
  // has already happened -- the offer was shown and answered -- so the answer
  // is a boolean and the failure is silent to everything but a caller that
  // asked. Both halves: a refusal test that makes no successful request proves
  // only that something failed.
  ready();
  const { api } = await import("./api.js");
  const offer = { workflow_id: "wfl_wa", k: 2, fate: "did_it", run_id: null, device_id: "dev-1", at: null };

  assert.equal(await api.reportOffer(offer), true, "a fate the backend recorded was reported as lost");

  offerRefusal = { status: 403, detail: "an offer is a browser's to record" };
  assert.equal(
    await api.reportOffer(offer),
    false,
    "a 403 was read as a fate that landed -- every offer would be eaten silently",
  );

  // And not by throwing on the way to `false`.
  globalThis.fetch = async () => {
    throw new TypeError("Failed to fetch");
  };
  assert.equal(await api.reportOffer(offer), false, "a backend that could not be reached threw");
  globalThis.fetch = rigServer;
  offerRefusal = null;
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
    () => calls.some((call) => call.path === "/v1/workflow-runs/run-9"),
    "nothing asked the rig what the run it had just started was doing",
  );

  // Live in this browser, as it is once the rig's channel has had a command
  // performed for it -- which is also what records that the rig is driving.
  await perform({ run_id: "run-9", kind: "nothing-doing" }, "rig");
  const answered = await send({ kind: "status" });
  // The browser it names is the browser it is. `deviceId` is what the options
  // page prints and what the panel gates registration on, and a status frozen
  // to a literal is a screen that says "registered" for somebody else's
  // browser -- checked against what is actually held, never against a literal,
  // because a literal on both sides is what let the same mutation live through
  // 27 suites in task 1.
  assert.equal(answered.deviceId, held.get("sro.deviceId"), "status named a browser that is not this one");
  const shown = answered.performing;
  assert.equal(shown.source, "rig");
  assert.equal(shown.run?.id, "run-9", "the panel was told a rig run is happening but not which");
  abort("run-9");

  const answer = await send({ kind: "approve-rig-run", runId: "run-9" });
  const approve = calls.find((call) => call.path === "/v1/workflow-runs/run-9/approve");
  assert.ok(approve, "Approve never reached the door that lets the write out");
  assert.equal(approve.method, "POST");
  assert.deepEqual(answer, { order: 0, first: true });
});

test("Approve proves this browser twice -- the query and the secret -- or the backend records nobody", async () => {
  // The whole of task 1. `POST /v1/workflow-runs/{id}/approve` reads the
  // browser through `asking_device`, which needs `?device_id=` and
  // `X-Device-Secret` TOGETHER. Half a pair is a 404, which is loud. Neither
  // half is `asking = None` -- and that is a 200 with a NULL approver and the
  // driving-browser check never evaluated, on the one door whose entire job is
  // recording who let a live warehouse write out. Nothing goes red. So each
  // half is pinned separately here, and against what this browser actually
  // holds rather than against a literal: a `device_id` or a secret frozen into
  // `api.js` would have to be these exact strings to survive.
  ready();
  held.set("sro.deviceId", "dev-approve-e3f1");
  held.set("sro.deviceSecret", "secret-approve-9ab2");
  held.set("sro.token", "tok-approve-4c7d");
  held.set("sro.activeRun", { runId: "run-9", at: Date.now(), source: "rig" });

  const answer = await send({ kind: "approve-rig-run", runId: "run-9" });

  const approve = calls.find((call) => call.path === "/v1/workflow-runs/run-9/approve");
  assert.ok(approve, "Approve did not reach /v1/workflow-runs/{id}/approve");
  assert.equal(approve.base, BACKEND, "Approve went somewhere that is not the backend");
  assert.equal(approve.method, "POST");
  assert.equal(
    new URLSearchParams(approve.query).get("device_id"),
    held.get("sro.deviceId"),
    "the tap named no browser in the query, so the backend resolves nobody and records nobody",
  );
  assert.equal(
    approve.headers["X-Device-Secret"],
    held.get("sro.deviceSecret"),
    "the tap proved no browser, so `?device_id=` alone is half a pair and the row names nobody",
  );
  assert.equal(
    approve.headers.Authorization,
    `Bearer ${held.get("sro.token")}`,
    "the tap carried the rig's bearer, or none",
  );
  // No body at all: the route takes none, and a `device_id` in one would be a
  // second answer to which browser is asking that nothing checks.
  assert.equal(approve.body, undefined, "the tap sent a body the route does not read");
  // And the old rig door was not knocked on instead, or as well.
  assert.equal(
    calls.filter((call) => call.path === "/v1/runs/run-9/approve").length,
    0,
    "Approve still went to the rig's `/v1/runs` path, which on the backend means a skill run",
  );
  assert.deepEqual(answer, { order: 0, first: true });

  held.delete("sro.activeRun");
});

test("a backend that refuses the approval is a refusal in the panel, not a success", async () => {
  // The status check, which is the difference between an operator seeing why
  // the write did not go out and an operator watching a button do nothing. The
  // test above is the success half: a refusal test that never makes a
  // successful request proves only that something failed.
  ready();
  approveRefusal = { status: 403, detail: "that browser is not driving this run" };
  held.set("sro.activeRun", { runId: "run-9", at: Date.now(), source: "rig" });

  assert.deepEqual(await send({ kind: "approve-rig-run", runId: "run-9" }), {
    ok: false,
    error: "that browser is not driving this run",
  });

  held.delete("sro.activeRun");
});

/** How many times this browser has asked the rig what the run is doing. */
const asked = () => calls.filter((call) => call.path === "/v1/workflow-runs/run-9").length;

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

// LAST ON PURPOSE. `abort` in `commands.js` refuses every later command for a
// run in module scope and there is no undo, so a test that stops `run-9` has
// to be the last one that wants `run-9` driven.
test("Stop tells the backend to stop the workflow run, with no body naming a browser", async () => {
  // The row already says which browser is driving it. A `device_id` in the
  // body would be a second answer to that question which can disagree with the
  // first, and `abort_workflow_run` takes none -- a bare POST is what a tap
  // is. On `/v1/runs/{id}/abort` this would be a 404 on a skill run's id space
  // while the workflow run went on stepping: a Stop button that stops the
  // browser and not the run.
  ready();
  held.set("sro.deviceSecret", "secret-abort-0e5b");
  held.set("sro.token", "tok-abort-c483");
  held.set("sro.activeRun", { runId: "run-9", at: Date.now(), source: "rig" });

  const answer = await send({ kind: "abort-run", runId: "run-9" });

  assert.equal(answer.ok, true);
  assert.equal(answer.error, undefined, `Stop reported a failure: ${answer.error}`);
  const stop = calls.find((call) => call.path === "/v1/workflow-runs/run-9/abort");
  assert.ok(stop, "Stop never reached the backend's abort door");
  assert.equal(stop.base, BACKEND);
  assert.equal(stop.method, "POST");
  assert.equal(stop.body, undefined, "Stop sent a body the route does not read");
  assert.equal(
    stop.headers["X-Device-Secret"],
    held.get("sro.deviceSecret"),
    "Stop did not prove this browser",
  );
  assert.equal(stop.headers.Authorization, `Bearer ${held.get("sro.token")}`);
  assert.equal(
    calls.filter((call) => call.path === "/v1/runs/run-9/abort").length,
    0,
    "Stop still went to `/v1/runs`, which on the backend is a skill run",
  );
  assert.equal(
    calls.filter((call) => call.path === "/v1/runs/run-9/stop").length,
    0,
    "a workflow run was stopped through the skill-run door",
  );

  // The run id is the caller's and is never a constant. Directly on `api`,
  // because the worker only ever stops the run it is driving and this file has
  // one of those: a frozen id here would stop somebody else's run and report
  // the operator's as stopped.
  const { api } = await import("./api.js");
  const asked = [];
  globalThis.fetch = async (url) => (asked.push(String(url)), json({ id: "run-c4e7" }, 202));
  await api.rigAbort("run-c4e7");
  assert.equal(asked.at(-1), `${BACKEND}/v1/workflow-runs/run-c4e7/abort`);
  globalThis.fetch = rigServer;

  held.delete("sro.activeRun");
});

test("a backend that will not stop the run says so to the operator who pressed Stop", async () => {
  // The other half. A stop that failed is a run still stepping somewhere with
  // nobody told about it, and the operator who just pressed Stop is the one
  // person who can act on that -- so it must not be swallowed. The test above
  // is the successful request this one is measured against.
  ready();
  held.set("sro.activeRun", { runId: "run-9", at: Date.now(), source: "rig" });
  globalThis.fetch = async (url, options = {}) => {
    const [path] = String(url).slice(BACKEND.length).split("?");
    calls.push({ path, method: options.method || "GET", body: options.body });
    if (path === "/v1/workflow-runs/run-9/abort") return json({ detail: "no such run here" }, 404);
    return rigServer(url, options);
  };

  const answer = await send({ kind: "abort-run", runId: "run-9" });

  assert.equal(answer.ok, true, "the local half of Stop is unconditional");
  assert.match(
    answer.error || "",
    /no such run here/,
    "a run the backend would not stop was reported to the operator as stopped",
  );

  held.delete("sro.activeRun");
});

/** `shapes()`'s two rules, at the level they live: the browser the caller
 * names is the browser the request asks for, and a refusal is `[]` and never a
 * throw. Directly on `api.shapes` rather than through a gesture, because
 * `considerOffer` is not awaited on the gesture path -- a shape served through
 * the worker here would be stamped into `shapesFor`'s five-minute cache by a
 * call landing after the test returned. */
test("the shapes read are the ones the named browser is served, and a refusal is []", async () => {
  ready();
  const { api } = await import("./api.js");
  const asked = [];
  globalThis.fetch = async (url) => {
    asked.push(String(url));
    return json({ shapes: [SHAPE] });
  };

  assert.deepEqual(await api.shapes("dev-other-6b90"), [SHAPE], "a served list came back as nothing");
  assert.equal(
    new URLSearchParams(asked.at(-1).split("?")[1] || "").get("device_id"),
    "dev-other-6b90",
    "the browser named by the caller is not the browser the request asks for",
  );
  assert.ok(asked.at(-1).startsWith(`${BACKEND}/v1/shapes`), `shapes were read from ${asked.at(-1)}`);

  globalThis.fetch = async () => json({ detail: "device was not found" }, 404);
  assert.deepEqual(await api.shapes("dev-other-6b90"), [], "a refused read threw on the gesture path");
  globalThis.fetch = rigServer;
});

/** The upload path, which had no test of its own in any suite and is the only
 * road every demonstration travels.
 *
 * Written when phase 5 deleted `mirror.js`. The mirror posted a copy of each
 * upload to the rig and its docstring said why it was silent: *"upload.js
 * drops queued rows on a permanent 4xx from the backend, and a rig that is
 * down, slow, or refusing must never be able to reach that decision."* That
 * decision is `isPermanent(error.status)` in `upload.js`, and after the
 * deletion its whole guarantee is this: **the only thing `api.observations`
 * can throw is the backend's own answer, with the backend's own status on
 * it.** Nothing stands between `call()` and the caller any more, so nothing
 * can invent a status the backend did not give -- and a 413 invented by a
 * second reader would have dropped a batch the backend had accepted.
 *
 * Directly on `api` rather than through `flush()`: `upload.js` exports only
 * `flush`, has no suite, and standing one up means a queue, a device and a
 * clock. What is pinned here is the one thing the deletion changed. */
test("an upload names this browser to the backend, and only the backend's refusal comes back", async () => {
  ready();
  const { api, ApiError } = await import("./api.js");

  const batch = { batch_id: "bat-7c31", device_id: "dev-ready-2f8a", events: [{ at: 91 }] };
  let served = json({ accepted: 1, batch_id: "bat-7c31" });
  const asked = [];
  globalThis.fetch = async (url, options = {}) => {
    asked.push({ url: String(url), ...options });
    return served;
  };

  assert.deepEqual(
    await api.observations(batch),
    { accepted: 1, batch_id: "bat-7c31" },
    "what the backend said about the upload did not reach the caller",
  );
  const sent = asked.at(-1);
  assert.equal(sent.url, `${BACKEND}/v1/observations`, `the batch was posted to ${sent.url}`);
  assert.equal(sent.method, "POST");
  // The body, not a body. A batch replaced by a constant is every operator's
  // demonstration uploaded as somebody else's.
  assert.deepEqual(JSON.parse(sent.body), batch, "the batch posted was not the batch given");
  assert.equal(sent.headers.Authorization, `Bearer ${held.get("sro.token")}`);
  assert.equal(sent.headers["X-Device-Secret"], held.get("sro.deviceSecret"));

  // A picture is the same road, and the multipart body is passed through
  // rather than stringified -- a `JSON.stringify(FormData)` is "{}".
  const form = { pretend: "multipart" };
  served = json({ artifact_id: "art_4d02" });
  assert.deepEqual(await api.artifact(form), { artifact_id: "art_4d02" });
  assert.equal(asked.at(-1).url, `${BACKEND}/v1/observations/artifacts`, "a picture went somewhere else");
  assert.equal(asked.at(-1).body, form, "the multipart body was mangled on the way out");
  assert.equal(asked.at(-1).headers["Content-Type"], undefined, "a boundary-less Content-Type was set");

  // The status `upload.js` reads to decide whether to drop the rows. It must
  // be the backend's, unchanged, and it must arrive as a throw -- a refusal
  // returned instead of thrown is a batch reported as uploaded and lost.
  served = json({ detail: "that batch is too large" }, 413);
  await assert.rejects(
    () => api.observations(batch),
    (error) => {
      assert.ok(error instanceof ApiError, "a refused upload did not come back as an ApiError");
      assert.equal(error.status, 413, "the status upload.js drops rows on was not the backend's");
      return true;
    },
    "a backend that refused the batch was reported to the caller as success",
  );

  globalThis.fetch = rigServer;
});

test("an update takes the rig's settings off this browser, and a launch tries again", async () => {
  // The rig token is the *tenant's* bearer, not this browser's device secret --
  // `call()` sends `sro.deviceSecret`, which `register()` mints and which is
  // untouched by any of this. So nothing here can leave a browser holding a
  // credential the backend does not recognise; what it can leave behind is a
  // spendable tenant credential in `chrome.storage.local` with no door in this
  // extension that uses it, on every browser that ever had a rig configured.
  // The keys left `KEYS` in phase 5, so `forget()` no longer takes them at
  // sign-out and this is the only thing that does.
  //
  // No device id: `dial()` answers null without one, so `settle()` -- which
  // both hooks kick -- opens no socket this test would then have to close.
  held.clear();
  held.set("sro.token", "tenant-cred-4e17");
  held.set("sro.rigUrl", "http://rig.test");
  held.set("sro.rigToken", "dev_minted-8b40");
  held.set("sro.rigRefusal", "/v1/observations 403: not yours");

  globalThis.__installed();
  await until(() => !held.has("sro.rigToken"), "the update left the tenant's rig bearer on this browser");
  assert.equal(held.has("sro.rigUrl"), false, "the rig url outlived the rig");
  assert.equal(held.has("sro.rigRefusal"), false, "a refusal from a rig there no longer is");
  assert.equal(held.get("sro.token"), "tenant-cred-4e17", "the credential still in use was taken too");

  // Fire-and-forget in a worker Chrome may evict at any await point, and
  // `onInstalled` does not fire again until the next update -- which may never
  // come. Every browser launch tries again, and removing an absent key is free.
  held.set("sro.rigToken", "dev_minted-8b40");
  globalThis.__started();
  await until(
    () => !held.has("sro.rigToken"),
    "a browser that missed the update-time removal never got another chance",
  );
});
