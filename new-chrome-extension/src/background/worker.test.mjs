// Self-check for what service-worker.js does with what it is told: what it
// records, which runs it watches, what it asks the backend, and -- one engine
// -- that nothing it sees or is asked ever starts a run from this browser.
//
// The scaffolding `rig-settings.test.mjs` used to carry, inherited here when
// phase 5 deleted that suite with its subject: `case "gesture"`, the panel's
// messages and the two lifecycle hooks live inside service-worker.js's own
// module scope, so reaching them means standing the whole of it up. None of it
// runs anything real -- every hook below is a no-op or a recorder.
//
// Run with `node src/background/worker.test.mjs`.

import { DEFAULT_API_URL } from "./deployment.generated.js";
import assert from "node:assert/strict";
import test from "node:test";

import { fakeIndexedDB } from "./test-support/fake-indexeddb.mjs";
// The evidence plane itself. Every gate below is about what does and does not
// reach it, and the count is the only honest way to ask.
const queue = await import("./queue.js");

globalThis.indexedDB = fakeIndexedDB();

const held = new Map();
const badges = [];
const titles = [];

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
  // The beat is held rather than dropped: what the worker does when nobody is
  // watching is exactly what a panel-driven test cannot see.
  alarms: {
    create: () => {},
    onAlarm: {
      addListener: (fn) => {
        globalThis.__beat = fn;
      },
    },
  },
  webNavigation: {
    onCommitted: { addListener: (fn) => (globalThis.__committed = fn) },
    onCompleted: { addListener: () => {} },
    onCreatedNavigationTarget: { addListener: (fn) => (globalThis.__popup = fn) },
  },
  tabs: {
    onRemoved: { addListener: () => {} },
    get: async (tabId) => ({ id: tabId, url: PAGE }),
    // The one tab this browser has, however a caller asks for it. `drivenTab`
    // looks a run's tab up this way, and without it no command here ever
    // reaches a tab -- so nothing could test what a run does to one.
    query: async () => [{ id: TAB, url: PAGE, active: true }],
    reload: async (tabId) => {
      reloads.push(tabId);
    },
    captureVisibleTab: async () => {
      throw new Error("no pictures in a test");
    },
  },
  scripting: {
    executeScript: async () => [],
    // `settle()`, which both lifecycle hooks kick, re-registers the content
    // scripts. Nothing here registers anything.
    getRegisteredContentScripts: async () => [],
    unregisterContentScripts: async () => {},
    registerContentScripts: async () => {},
  },
  permissions: {
    getAll: async () => ({ origins: [] }),
    contains: async () => false,
  },
  // Held rather than dropped: four characters have to say the most important
  // true thing, and which one they say is a rule worth a test.
  action: {
    setBadgeText: async (what) => void badges.push(what),
    setBadgeBackgroundColor: async () => {},
    setTitle: async (what) => void titles.push(what.title),
  },
  sidePanel: { open: async () => {}, setPanelBehavior: async () => {} },
};

// -- the rig, as far as this browser can tell --------------------------------

const RIG = "http://rig.test";
/** What `ready()` leaves in place: whichever deployment this build was
 * generated for. Read rather than written down, because `make gen-deployment`
 * changes it -- a suite that hardcodes one address fails the moment somebody
 * points the extension at a real deployment, which is not a defect. */
const BACKEND = DEFAULT_API_URL;
const H = "https://wms.example";
const PAGE = `${H}/wa`;
const TAB = 1;

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
/** How the backend answers the approve door, for the test that a refusal is
 * one. `null` is the door letting the write out. */
let approveRefusal = null;

let chatRead = null;
let threadSaid = null;
/** What `GET /v1/threads/current` answers: the thread as the panel rereads it. */
let threadCurrent = null;
/** Every tab the worker reloaded to repair its recording. */
const reloads = [];
let lookupRead = null;
let lookedUp = [];

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
  if (base !== BACKEND)
    return json({ detail: `the rig serves nothing: ${path}` }, 404);
  if (path === "/v1/workflow-runs/run-9/approve") {
    return approveRefusal
      ? json({ detail: approveRefusal.detail }, approveRefusal.status)
      : json({ order: 0, first: true });
  }
  if (path.endsWith("/heartbeat"))
    return json({ policy_version: 0, policy: null, pause: false });
  // The evidence door takes what this browser recorded, as the backend does.
  if (path === "/v1/observations") return json({ accepted: 1, rejected: [] });
  if (path === "/v1/observations/artifacts") return json({}, 201);
  if (path === "/v1/threads/current")
    return json(threadCurrent || { id: "thr-1", messages: [] });
  if (path === "/v1/threads/thr-1/messages")
    return json(threadSaid || { id: "thr-1", messages: [] });
  if (path === "/v1/chat")
    return chatRead ? json(chatRead) : json({ detail: "no model" }, 503);
  if (path === "/v1/chat/from-the-mail") {
    mailLooks.push(options.method || "GET");
    return mailLooked ? json(mailLooked) : json({ detail: "no model" }, 503);
  }
  // The one door in front of both worlds. The backend decides which a sentence
  // is -- the rule lives there so this side carries no copy of it -- so the
  // fake answers by the same shape the route does.
  if (path === "/v1/lookups") {
    lookedUp.push(JSON.parse(options.body || "{}"));
    return json(lookupRead || { question: "", lookups: [], answers: [] });
  }
  if (path === "/v1/ask") {
    if (lookupRead) return json({ kind: "lookup", lookup: lookupRead });
    return chatRead
      ? json({ kind: "job", job: chatRead })
      : json({ detail: "no model" }, 503);
  }
  // The backend answers the whole row, where the rig answered `{run_id}`.
  if (path === "/v1/workflow-runs")
    return json({ ...rigRunServed, id: "run-9" }, 201);
  if (path === "/v1/workflow-runs/run-9/abort")
    return json({ ...rigRunServed }, 202);
  if (path === `/v1/workflow-runs/${rigRunServed.id}`) {
    return rigRunFails
      ? json({ detail: "the backend is down" }, 503)
      : json(rigRunServed);
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

let mailLooked = null;
const mailLooks = [];

const { lookInTheMail } = await import("./service-worker.js");

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
      gesture: {
        url: PAGE,
        target: { component: { itemId: identity } },
        kind: "type",
        value,
        at: 1,
      },
    },
    { tab: { id: TAB, url: PAGE } },
  );
}

/** The offer is made off the gesture path, not on it -- `considerOffer` is
 * deliberately not awaited so recognising a job may never cost recording one.
 * So the test waits for the answer rather than assuming it has landed. */
async function until(what, why) {
  for (let tries = 0; tries < 200; tries++) {
    // Awaited, so a condition that has to ask the worker something -- "has the
    // panel drawn the run yet" -- can be written as one.
    if (await what()) return;
    await new Promise((resolve) => setTimeout(resolve, 5));
  }
  assert.fail(why);
}

/** Every run this browser tried to start itself. One engine: always none. */
const startedHere = () =>
  calls.filter((call) => call.method === "POST" && call.path === "/v1/workflow-runs");

function ready() {
  held.clear();
  calls = [];
  rigRunServed = { id: "run-9", outcome: "held", steps: [] };
  rigRunFails = false;
  approveRefusal = null;
  chatRead = null;
  lookupRead = null;
  mailLooked = null;
  mailLooks.length = 0;
  badges.length = 0;
  titles.length = 0;
  lookedUp = [];
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
test("just this once sends a password to the door that keeps nothing", async () => {
  // Two doors, because there are two answers. `PUT /v1/secrets` is the
  // deployment keeping a credential; `POST /v1/secrets/once` is an operator
  // lending one for the job in front of them, held for the step that types it
  // and forgotten. A password lent must never reach the vault.
  ready();
  held.set("sro.deviceId", "dev-start-a17f");
  held.set("sro.deviceSecret", "secret-start-33c9");
  held.set("sro.token", "tok-start-6d20");

  await send({
    kind: "hold-secret-once",
    system: "keycloak.test",
    field: "password",
    value: "lent-33f1",
    runId: "run_g33f1",
  });

  const kept = calls.find((call) => call.path === "/v1/secrets");
  assert.equal(kept, undefined, "a password lent for one run reached the vault");
  const lent = calls.find((call) => call.path === "/v1/secrets/once");
  assert.ok(lent, "the press never reached `POST /v1/secrets/once`");
  assert.equal(lent.method, "POST");
  assert.deepEqual(JSON.parse(lent.body), {
    system: "keycloak.test",
    field: "password",
    value: "lent-33f1",
    run_id: "run_g33f1",
  });
});

test("one row has one reader: the run is not fetched twice in a second", async () => {
  // The worker polls a running job once a second and the panel asked for the
  // same row on every one of its own refreshes -- about two
  // `GET /v1/workflow-runs/{id}` a second for the length of a run, measured
  // on the deployment 2026-09-22. The picture already held is the same
  // answer.
  ready();
  held.set("sro.deviceId", "dev-start-a17f");
  held.set("sro.deviceSecret", "secret-start-33c9");
  held.set("sro.token", "tok-start-6d20");

  const asked = () =>
    calls.filter((call) => call.path === "/v1/workflow-runs/run-9").length;

  const before = asked();
  await send({ kind: "run", runId: "run-9", source: "rig" });
  await send({ kind: "run", runId: "run-9", source: "rig" });
  await send({ kind: "run", runId: "run-9", source: "rig" });

  assert.ok(
    asked() - before <= 1,
    `three asks in one second fetched the row ${asked() - before} times`,
  );
});

test("the day's summary asks for the window the backend reads", async () => {
  // The route reads `days`. It used to be sent `since`, which it ignored, so
  // the panel's "today" line counted the last seven days.
  ready();
  await send({ kind: "summary", days: 1 });
  const asked = calls.find((call) => call.path === "/v1/analytics/summary");
  assert.ok(asked, "the summary was never asked for");
  assert.equal(asked.query, "days=1");
});

// Not tested here: that a browser with no rig writes no tail. `shapesFor`
// caches for five minutes in module scope, so once any test in this process
// has seen a shape every later one does too, and a test that ran first would
// cache the empty list for every test after it.

test("the run a yes started is drawn while it runs, and Approve reaches the backend", async () => {
  // Two halves of the same gate. The panel can only show a live run if
  // something in this worker keeps asking the backend for it -- nothing
  // pushes -- and the Approve on that row has to land without the panel ever
  // holding the bearer, which is why it is a message and not a fetch.
  ready();
  rigRunServed = {
    id: "run-9",
    outcome: "running",
    steps: [{ order: 0, says: "save the work area", verdict: "awaiting" }],
  };
  threadSaid = {
    id: "thr-1",
    messages: [
      {
        id: "m2",
        speaker: "assistant",
        text: "Running Create Work Area now.",
        said_at: "2026-09-28T10:20:02Z",
        decision: { kind: "job", workflow_id: "wfl_wa", resume: true, run_id: "run-9" },
      },
    ],
  };
  await send({ kind: "thread-say", threadId: "thr-1", text: "yes", tabId: TAB });

  let answered = null;
  await until(async () => {
    answered = await send({ kind: "status" });
    return answered.performing?.run?.id === "run-9";
  }, "the panel was never shown the run the backend started");
  // The browser it names is the browser it is. `deviceId` is what the options
  // page prints and what the panel gates registration on, and a status frozen
  // to a literal is a screen that says "registered" for somebody else's
  // browser -- checked against what is actually held, never against a literal.
  assert.equal(
    answered.deviceId,
    held.get("sro.deviceId"),
    "status named a browser that is not this one",
  );
  assert.equal(answered.performing.source, "rig");

  const answer = await send({ kind: "approve-rig-run", runId: "run-9" });
  const approve = calls.find(
    (call) => call.path === "/v1/workflow-runs/run-9/approve",
  );
  assert.ok(approve, "Approve never reached the door that lets the write out");
  assert.equal(approve.method, "POST");
  assert.deepEqual(answer, { order: 0, first: true });
  threadSaid = null;
  held.delete("sro.activeRun");
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

  const approve = calls.find(
    (call) => call.path === "/v1/workflow-runs/run-9/approve",
  );
  assert.ok(approve, "Approve did not reach /v1/workflow-runs/{id}/approve");
  assert.equal(
    approve.base,
    BACKEND,
    "Approve went somewhere that is not the backend",
  );
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
  assert.equal(
    approve.body,
    undefined,
    "the tap sent a body the route does not read",
  );
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
  approveRefusal = {
    status: 403,
    detail: "that browser is not driving this run",
  };
  held.set("sro.activeRun", { runId: "run-9", at: Date.now(), source: "rig" });

  assert.deepEqual(await send({ kind: "approve-rig-run", runId: "run-9" }), {
    ok: false,
    error: "that browser is not driving this run",
  });

  held.delete("sro.activeRun");
});

/** How many times this browser has asked the rig what the run is doing. */
const asked = () =>
  calls.filter((call) => call.path === "/v1/workflow-runs/run-9").length;

test("a rig run this browser did not start is polled from status, and a failed ask is asked again", async () => {
  // A run this worker was evicted in the middle of, or one a yes started in
  // another window: the record is there and nothing in this worker's life
  // wrote it.
  ready();
  held.set("sro.activeRun", { runId: "run-9", at: Date.now(), source: "rig" });
  rigRunFails = true;

  await send({ kind: "status" });
  await until(
    () => asked() === 1,
    "opening the panel over a rig run asked the rig nothing",
  );
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
  await until(
    () => asked() >= 2,
    "a poll whose first ask failed was never asked again",
  );

  held.delete("sro.activeRun");
});

test("a run parked on an approval is still drawn", async () => {
  // A write waiting on a person can wait five minutes, and for all of them the
  // panel has to show the run, its steps and the Approve -- the one control
  // the run is actually waiting on.
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

  held.delete("sro.activeRun");
});

test("Approve is refused for a run this panel is not watching", async () => {
  // The panel draws Approve off a status read that can be seconds old. A card
  // left standing after the run ended, or a second window showing a superseded
  // one, must not be able to authorise a live write against it.
  ready();
  held.set("sro.activeRun", { runId: "run-9", at: Date.now(), source: "rig" });

  assert.deepEqual(await send({ kind: "approve-rig-run", runId: "run-8" }), {
    ok: false,
    error: "that run is not the one this panel is watching",
  });
  assert.equal(
    calls.filter((call) => call.path.endsWith("/approve")).length,
    0,
    "a write was approved against a run this panel is not watching",
  );

  held.delete("sro.activeRun");
});

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
  assert.equal(
    answer.error,
    undefined,
    `Stop reported a failure: ${answer.error}`,
  );
  const stop = calls.find(
    (call) => call.path === "/v1/workflow-runs/run-9/abort",
  );
  assert.ok(stop, "Stop never reached the backend's abort door");
  assert.equal(stop.base, BACKEND);
  assert.equal(stop.method, "POST");
  assert.equal(
    stop.body,
    undefined,
    "Stop sent a body the route does not read",
  );
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
  globalThis.fetch = async (url) => (
    asked.push(String(url)),
    json({ id: "run-c4e7" }, 202)
  );
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
    if (path === "/v1/workflow-runs/run-9/abort")
      return json({ detail: "no such run here" }, 404);
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

  const batch = {
    batch_id: "bat-7c31",
    device_id: "dev-ready-2f8a",
    events: [{ at: 91 }],
  };
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
  assert.equal(
    sent.url,
    `${BACKEND}/v1/observations`,
    `the batch was posted to ${sent.url}`,
  );
  assert.equal(sent.method, "POST");
  // The body, not a body. A batch replaced by a constant is every operator's
  // demonstration uploaded as somebody else's.
  assert.deepEqual(
    JSON.parse(sent.body),
    batch,
    "the batch posted was not the batch given",
  );
  assert.equal(sent.headers.Authorization, `Bearer ${held.get("sro.token")}`);
  assert.equal(sent.headers["X-Device-Secret"], held.get("sro.deviceSecret"));

  // A picture is the same road, and the multipart body is passed through
  // rather than stringified -- a `JSON.stringify(FormData)` is "{}".
  const form = { pretend: "multipart" };
  served = json({ artifact_id: "art_4d02" });
  assert.deepEqual(await api.artifact(form), { artifact_id: "art_4d02" });
  assert.equal(
    asked.at(-1).url,
    `${BACKEND}/v1/observations/artifacts`,
    "a picture went somewhere else",
  );
  assert.equal(
    asked.at(-1).body,
    form,
    "the multipart body was mangled on the way out",
  );
  assert.equal(
    asked.at(-1).headers["Content-Type"],
    undefined,
    "a boundary-less Content-Type was set",
  );

  // The status `upload.js` reads to decide whether to drop the rows. It must
  // be the backend's, unchanged, and it must arrive as a throw -- a refusal
  // returned instead of thrown is a batch reported as uploaded and lost.
  served = json({ detail: "that batch is too large" }, 413);
  await assert.rejects(
    () => api.observations(batch),
    (error) => {
      assert.ok(
        error instanceof ApiError,
        "a refused upload did not come back as an ApiError",
      );
      assert.equal(
        error.status,
        413,
        "the status upload.js drops rows on was not the backend's",
      );
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
  await until(
    () => !held.has("sro.rigToken"),
    "the update left the tenant's rig bearer on this browser",
  );
  assert.equal(held.has("sro.rigUrl"), false, "the rig url outlived the rig");
  assert.equal(
    held.has("sro.rigRefusal"),
    false,
    "a refusal from a rig there no longer is",
  );
  assert.equal(
    held.get("sro.token"),
    "tenant-cred-4e17",
    "the credential still in use was taken too",
  );

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

test("a run started elsewhere is drawn with its steps even when no source word arrived", async () => {
  // The defect an operator hit on a real login page. The panel polled the
  // workflow-run door only when the command envelope said `source: "rig"`, so
  // a browser older than that field drew "a run is performing here" with no
  // steps and no Approve -- while the console showed the same run parked on a
  // person, with the button.
  ready();
  rigRunServed = {
    id: "run-elsewhere",
    outcome: "running",
    steps: [
      { order: 1, verdict: "held", says: "Enter username." },
      {
        order: 2,
        verdict: "awaiting",
        says: "Sign in.",
        sent: { kind: "ui.perform" },
      },
    ],
  };
  held.set("sro.activeRun", {
    runId: "run-elsewhere",
    at: Date.now(),
    source: "backend",
  });

  // Polled, as the panel really does it: `status` kicks the fetch and does not
  // wait for it, so the picture lands on a later tick than the one that asked.
  let status = await send({ kind: "status" });
  await until(async () => {
    status = await send({ kind: "status" });
    return Boolean(status.performing?.run);
  }, "the run was never drawn, however many times the panel asked");

  assert.equal(
    status.performing?.runId,
    "run-elsewhere",
    "the run was not drawn at all",
  );
  assert.equal(
    status.performing?.run?.steps?.find((step) => step.outcome === "awaiting")
      ?.index,
    2,
    "the parked step never reached the panel, so neither did its Approve",
  );
});

test("a yes the backend already started is watched, never started again", async () => {
  // The backend starts the run itself on a yes, from every door (S2), and says
  // so with the run's id. A second start from this browser would be a second
  // run of one offer -- refused by the backend's unique index, but a write
  // nobody asked for is not this browser's to attempt.
  ready();
  threadSaid = {
    id: "thr-1",
    messages: [
      {
        id: "m1",
        speaker: "operator",
        text: "NSRO",
        said_at: "2026-09-18T10:20:01Z",
      },
      {
        id: "m2",
        speaker: "assistant",
        text: "Running Create a Customer Type now.",
        said_at: "2026-09-18T10:20:02Z",
        decision: {
          kind: "job",
          workflow_id: "wfl_wa",
          resume: true,
          run_id: "run-9",
          from_step: 4,
          values: { workArea: "NSRO" },
          watched: true,
          offer: "m-question",
        },
      },
    ],
  };

  await send({
    kind: "thread-say",
    threadId: "thr-1",
    text: "NSRO",
    tabId: TAB,
  });
  await until(
    () => held.get("sro.activeRun")?.runId === "run-9",
    "the panel was never told which run the backend started",
  );

  assert.equal(held.get("sro.activeRun").source, "rig");
  assert.deepEqual(
    calls.filter(
      (call) =>
        call.path === "/v1/workflow-runs" ||
        call.path === "/v1/chat/run-started",
    ),
    [],
    "this browser started, or announced, a run the backend had already started",
  );
  assert.ok(
    !JSON.stringify(held.get("sro.nudges") || []).includes("wfl_wa"),
    "a card offered the job that is already running",
  );
  threadSaid = null;
  held.delete("sro.activeRun");
});

/** A thread whose yes was said somewhere else: the backend's "Running", then a
 * later "no longer open" from a second press that lost the race to it. */
function startedElsewhere(runId) {
  return {
    id: "thr-1",
    messages: [
      {
        id: "m1",
        speaker: "assistant",
        text: "Running Compose and Send Email now.",
        said_at: "2026-09-28T10:20:02Z",
        decision: { kind: "job", workflow_id: "wfl_mail", resume: true, run_id: runId },
      },
      { id: "m2", speaker: "operator", text: "yes", said_at: "2026-09-28T10:20:03Z" },
      {
        id: "m3",
        speaker: "assistant",
        text: "That question is no longer open, so nothing was done.",
        said_at: "2026-09-28T10:20:03Z",
        decision: {},
      },
    ],
  };
}

test("a run a yes in the console started is watched when the thread is next read", async () => {
  // S2 review M2: the backend starts the run from every door, but the panel
  // watched only the run its own reply named -- a console yes left the ledger
  // saying "Running" with no card under it.
  ready();
  const served = rigRunServed;
  rigRunServed = { id: "run-7", outcome: "running", steps: [] };
  threadCurrent = startedElsewhere("run-7");

  await send({ kind: "thread" });
  await until(
    () => held.get("sro.activeRun")?.runId === "run-7",
    "the panel never watched the run the console's yes started",
  );

  assert.equal(held.get("sro.activeRun").source, "rig");
  assert.deepEqual(
    calls.filter((call) => call.path === "/v1/workflow-runs"),
    [],
    "this browser started a run the backend had already started",
  );
  held.delete("sro.activeRun");
  rigRunServed = served;
  threadCurrent = null;
});

test("a run the thread names that has already ended is not brought back", async () => {
  ready();
  const served = rigRunServed;
  rigRunServed = { id: "run-6", outcome: "held", steps: [] };
  threadCurrent = startedElsewhere("run-6");

  await send({ kind: "thread" });
  await until(
    () => calls.some((call) => call.path === "/v1/workflow-runs/run-6"),
    "the run was never looked at",
  );
  await new Promise((resolve) => setTimeout(resolve, 20));

  assert.equal(held.get("sro.activeRun") ?? null, null, "an ended run was watched again");
  rigRunServed = served;
  threadCurrent = null;
});

test("a sentence typed under a standing question is not read a second time", async () => {
  // Measured on the deployment 2026-09-19, thread thr_163bf91b. The operator
  // was asked "Create a Client. Address takes 40 characters. What should it
  // be?" and typed `testing for new purpose`. The conversation did the right
  // thing -- the reading said that was not an answer, and it asked again --
  // and the browser then read the SAME words a second time against the rig's
  // jobs and drew an open offer to create a warehouse equipment type.
  //
  // Two answers on screen to one sentence, and the wrong one was the one with
  // a button on it.
  ready();
  chatRead = { workflow_id: "wfl_wa", values: {}, missing: [] };
  threadSaid = {
    id: "thr-1",
    messages: [
      {
        id: "m1",
        speaker: "assistant",
        text: "I am still waiting on this one. Address takes 40 characters. What should it be?",
        said_at: "2026-09-19T10:20:02Z",
        decision: {
          kind: "needs_values",
          workflow_id: "wfl_client",
          missing: ["Address", "Name"],
        },
      },
    ],
  };

  await send({
    kind: "thread-say",
    threadId: "thr-1",
    text: "testing for new purpose",
    tabId: TAB,
  });
  // The offer is made off the reply and not awaited by it, so this has to let
  // the worker finish being wrong before it can say it was not.
  await new Promise((resolve) => setTimeout(resolve, 100));

  assert.deepEqual(
    calls.filter((call) => call.path === "/v1/ask").map((call) => call.path),
    [],
    "the sentence was read a second time while its question was still standing",
  );
  assert.deepEqual(
    startedHere(),
    [],
    "a standing question became an offer to do something else",
  );
  threadSaid = null;
});

test("a question is answered rather than turned into an offer", async () => {
  // The other half of the same box. An instruction becomes a card somebody
  // presses; a question has already been looked up by the time the answer
  // arrives -- a read writes nothing -- so what is left is to put it where the
  // panel draws it.
  ready();
  lookupRead = {
    question: "which suppliers are set up at SG",
    lookups: [
      { system: "blue_yonder", how: "call", target: "/data/WM/wm/suppliers" },
    ],
    answers: [
      {
        system: "blue_yonder",
        target: "/data/WM/wm/suppliers",
        ok: true,
        status: 200,
        body: '{"rows":5}',
      },
    ],
  };

  await send({
    kind: "thread-say",
    threadId: "thr-1",
    text: "which suppliers are set up at SG",
    tabId: TAB,
  });
  await until(() => held.get("sro.answer"), "the question produced no answer");

  const answered = held.get("sro.answer");
  assert.equal(answered.said, "which suppliers are set up at SG");
  assert.equal(answered.answers[0].status, 200);
  assert.deepEqual(
    startedHere(),
    [],
    "a question was turned into an offer to run something",
  );
});

test("a rule that almost fired is held where the panel can say so", async () => {
  // The third failure, and the one that was silent. A rule that misses without
  // saying so is worse than one that fires half-way: the operator believes
  // their browser is watching for something and it is not.
  ready();
  held.set("sro.watches", [
    {
      id: "trg-1",
      host: "mail.google.com",
      terms: [{ field: "subject", contains: "order status" }],
      values: [],
    },
  ]);

  const said = await send(
    { kind: "watch-nearly", triggerId: "trg-1", terms: ["order status"] },
    { url: "https://mail.google.com/mail/u/0/#inbox" },
  );

  assert.equal(said.ok, true);
  assert.deepEqual(held.get("sro.nearMisses")[0].terms, ["order status"]);
  const status = await send({ kind: "status" });
  assert.deepEqual(status.nearMisses[0].terms, ["order status"]);
});

test("a page cannot put its own words on the panel through a near miss", async () => {
  // The terms are read from the rule this worker holds, never from the
  // message: a page that sent a different string would otherwise be writing
  // on the operator's panel.
  ready();
  held.set("sro.watches", [
    {
      id: "trg-1",
      host: "mail.google.com",
      terms: [{ field: "subject", contains: "order status" }],
      values: [],
    },
  ]);

  await send(
    {
      kind: "watch-nearly",
      triggerId: "trg-1",
      terms: ["click here to claim your prize"],
    },
    { url: "https://mail.google.com/mail/u/0/#inbox" },
  );

  assert.deepEqual(held.get("sro.nearMisses") || [], []);
});

test("a mail whose watch asks is answered, not turned into an offer to run", async () => {
  // The other end of the same idea, arriving from a mailbox instead of the
  // panel's box. A watch that asks reads the question out of the mail the way
  // every other watch reads an order number -- at match time, as a parameter,
  // never written down -- and what comes back is an answer.
  ready();
  held.set("sro.watches", [
    {
      id: "trg-ask",
      asks: true,
      host: "mail.google.com",
      terms: [{ field: "subject", contains: "how many" }],
      values: [
        {
          name: "question",
          where: { strategy: "css_path", query: "div.mail-body" },
        },
      ],
    },
  ]);
  lookupRead = {
    question: "how many suppliers are set up at SG",
    lookups: [
      { system: "blue_yonder", how: "call", target: "/data/WM/wm/suppliers" },
    ],
    answers: [
      {
        system: "blue_yonder",
        target: "/data/WM/wm/suppliers",
        ok: true,
        body: "5",
      },
    ],
  };

  const answered = await send(
    {
      kind: "watch-matched",
      triggerId: "trg-ask",
      values: { question: "how many suppliers are set up at SG" },
    },
    { url: "https://mail.google.com/mail/u/0/#inbox", tab: { id: TAB } },
  );

  assert.equal(answered.asked, true);
  assert.deepEqual(lookedUp, [
    { question: "how many suppliers are set up at SG" },
  ]);
  assert.equal(held.get("sro.answer").answers[0].body, "5");
  assert.deepEqual(
    calls.filter((call) => call.path.includes("/matched")),
    [],
    "a question was reported as a mail match for a job",
  );
  assert.deepEqual(
    held.get("sro.offers") || [],
    [],
    "a question left an offer nobody can press",
  );
});

test("a watch that asks and finds no question in the mail says so and asks nobody", async () => {
  // A rule matching a sender with the question mark pointed at the wrong place
  // would otherwise look up the empty string on every mail from them.
  ready();
  held.set("sro.watches", [
    {
      id: "trg-ask",
      asks: true,
      host: "mail.google.com",
      terms: [{ field: "subject", contains: "how many" }],
      values: [
        {
          name: "question",
          where: { strategy: "css_path", query: "div.mail-body" },
        },
      ],
    },
  ]);

  const answered = await send(
    { kind: "watch-matched", triggerId: "trg-ask", values: {} },
    { url: "https://mail.google.com/mail/u/0/#inbox", tab: { id: TAB } },
  );

  assert.match(answered.error, /no question/);
  assert.deepEqual(lookedUp, []);
});

test("a sentence about nothing says something and offers nothing", async () => {
  // No model configured, over the day's cap, or a sentence that named no job.
  // The thread still has what they said.
  ready();
  // `ready()` above already signed this browser in.
  chatRead = { workflow_id: null, values: {}, missing: [] };

  const said = await send({
    kind: "thread-say",
    threadId: "thr-1",
    text: "how do I log in",
    tabId: TAB,
  });

  assert.ok(said, "the sentence was not said at all");
  await new Promise((resolve) => setTimeout(resolve, 20));
  assert.deepEqual(startedHere(), []);
});

test("the panel's tick reads the mailbox, and not on every tick", async () => {
  // The panel asks on the poll it already runs -- "has anything been said to
  // me" -- and a mail asking for a job is the system being asked something.
  // The throttle is here rather than in the panel because the panel is closed
  // most of the day and there may be more than one of them.
  ready();
  mailLooked = {
    offered: [
      {
        message: "m-1",
        workflow_id: "wfl_1",
        title: "Create a Customer Type",
        values: {},
        missing: [],
      },
    ],
    read: 4,
    why: "offered Create a Customer Type",
  };

  const first = await lookInTheMail();
  const second = await lookInTheMail();

  assert.deepEqual(first, { ok: true, offered: 1, read: 4 });
  assert.equal(second.skipped, "looked recently");
  assert.deepEqual(
    mailLooks,
    ["POST"],
    "the mailbox was read twice in five seconds",
  );
});

test("what a mail look found is said, and never becomes a card this browser starts", async () => {
  // The backend acts on a mail itself: it starts the run, or asks in the
  // conversation. A card here with its own Yes was a second engine behind the
  // first. So each thing a look found is said, and nothing is held to press.
  ready();
  mailLooked = {
    offered: [
      { message: "m-6", workflow_id: "wfl_1", title: "Create a Customer Type", started: true },
      { message: "m-7", workflow_id: "wfl_2", title: "Create a Work Area", asked: true },
      {
        message: "m-8",
        workflow_id: "wfl_3",
        title: "Delete a Customer Type",
        values: { "Customer Type": "GPX" },
      },
    ],
    read: 4,
    why: "offered three",
  };

  const looked = await lookInTheMail();

  assert.equal(looked.offered, 3);
  const said = (held.get("sro.said") || []).join("\n");
  assert.match(said, /Create a Customer Type is running on the answer that came back/);
  assert.match(said, /Create a Work Area is asked in the conversation/);
  assert.match(
    said,
    /mail offer for Delete a Customer Type was neither started nor asked by the backend/,
  );
  assert.ok(!said.includes("GPX"), "a value out of somebody's mail was narrated");
  assert.equal(held.get("sro.nudges"), undefined, "a mail became a card to press");
  assert.deepEqual(
    calls.filter((call) => call.method === "POST" && call.path === "/v1/workflow-runs"),
    [],
    "a mail started a run from this browser",
  );
});

test("the mailbox is read on the beat, not only while somebody is watching", async () => {
  // A request that arrived while the panel was closed is exactly the one
  // somebody needs to find waiting when they open it, and a look that runs
  // only on the panel's own tick cannot produce one.
  ready();
  mailLooked = {
    offered: [],
    read: 2,
    why: "read 2, and none of them asks for a job",
  };

  await globalThis.__beat({ name: "sro-heartbeat" });
  // The alarm's work is fired and not awaited -- nothing is waiting on it --
  // so the call lands on the next turn.
  await new Promise((resolve) => setTimeout(resolve, 20));

  assert.deepEqual(mailLooks, ["POST"], "the beat did not read the mailbox");
});

test("the icon says whether this browser is recording, and nothing else", async () => {
  // Four characters, and the one fact the operator cannot discover any other
  // way and may want to stop this second.
  ready();
  await send({ kind: "set-paused", paused: false });
  assert.equal(badges.at(-1).text, "REC");
  assert.match(titles.at(-1), /observing$/);

  await send({ kind: "set-paused", paused: true });
  assert.equal(badges.at(-1).text, "");
  assert.match(titles.at(-1), /not observing \(paused here\)/);
});

test("a browser with no mailbox behind it stops asking rather than calling all day", async () => {
  // Most browsers have no connector at all. The backend answers that as a
  // sentence rather than an error, and a look that took it as "try again in a
  // minute" would be a call every minute forever for an answer that cannot
  // change until somebody authorises one.
  ready();
  mailLooked = {
    offered: [],
    read: 0,
    why: "the mailbox could not be reached: no grant",
  };

  await lookInTheMail();
  const again = await lookInTheMail();

  assert.equal(again.skipped, "looked recently");
  assert.deepEqual(mailLooks, ["POST"]);
});

test("a look that fails is not a red line in the panel", async () => {
  // A door that is not there yet, a backend restarting, a browser with no
  // credential. The look is a background convenience: the operator can always
  // type the request.
  ready();
  mailLooked = null;

  const looked = await lookInTheMail();

  assert.equal(looked.ok, true);
  assert.match(looked.skipped, /no model/);
});

test("a tab that records half is repaired once, and only once", async () => {
  // The reload is a repair, and a repair that did not work is not worth
  // repeating: the fresh page reports the same fault a second later and the
  // worker reloads it again. Measured on the deployment 2026-09-18 -- one tab
  // reloaded fourteen times running, which is a browser nobody can use.
  ready();
  reloads.length = 0;

  const deaf = { tab: { id: 4242 } };
  await globalThis.__handle(
    { kind: "calls-not-recordable", holding: false },
    deaf,
    () => {},
  );
  await until(
    () => reloads.length === 1,
    "a page with nothing typed in it was not repaired",
  );

  // It is still deaf a second later, because the reload did not take. It is
  // not reloaded again: it goes on the card and waits to be asked, which is
  // where it was before any of this.
  await globalThis.__handle(
    { kind: "calls-not-recordable", holding: false },
    deaf,
    () => {},
  );
  await new Promise((done) => setTimeout(done, 20));
  assert.deepEqual(reloads, [4242], "the worker reloaded the same tab twice");
});

test("a page whose frames all report at once is still repaired only once", async () => {
  // The case the sequential test above could not see. One page is one tab id
  // and MANY FRAMES: a page with a dozen iframes reports a half-installed
  // recorder a dozen times in the same turn, from the same `sender.tab.id`.
  //
  // The guard asked storage whether the tab had been repaired and marked it
  // afterwards, with an await between -- so every report that arrived before
  // the first one finished reading saw an unclaimed tab, and every one of
  // them reloaded it. Measured on the deployment 2026-09-20: tab 148284819
  // reloaded fifteen times and 148284734 eight, inside one minute, each
  // reload narrated truthfully by a guard doing exactly what it was written
  // to do and unable to see the other fourteen.
  ready();
  reloads.length = 0;

  const page = { tab: { id: 7373 } };
  // Not awaited in between, which is the whole point: this is one turn.
  await Promise.all(
    Array.from({ length: 12 }, () =>
      globalThis.__handle(
        { kind: "calls-not-recordable", holding: false },
        page,
        () => {},
      ),
    ),
  );
  await new Promise((done) => setTimeout(done, 30));

  assert.deepEqual(
    reloads,
    [7373],
    `one page was reloaded ${reloads.length} times`,
  );
});

test("the reload a repair performs does not undo the claim that made it", async () => {
  // The loop, and the guard drove it.
  //
  // `chrome.tabs.reload` commits like any other navigation, so the reload the
  // worker had just performed arrived at `onCommitted`, which forgot the
  // claim -- and the fresh page reported the same half-installed recorder to
  // a worker that had never heard of it. Measured on the deployment
  // 2026-09-20: two tabs, twenty-three reloads, inside one minute, every one
  // of them narrated truthfully.
  ready();
  reloads.length = 0;

  const deaf = { tab: { id: 8484 } };
  await globalThis.__handle(
    { kind: "calls-not-recordable", holding: false },
    deaf,
    () => {},
  );
  await until(() => reloads.length === 1, "the page was not repaired at all");

  // The reload commits. Chrome says what kind of navigation it was.
  await globalThis.__committed({
    frameId: 0,
    tabId: 8484,
    url: "https://wms.example/receiving",
    timeStamp: Date.now(),
    transitionType: "reload",
  });
  await globalThis.__handle(
    { kind: "calls-not-recordable", holding: false },
    deaf,
    () => {},
  );
  await new Promise((done) => setTimeout(done, 30));

  assert.deepEqual(
    reloads,
    [8484],
    `the page was reloaded ${reloads.length} times`,
  );
});

test("a tab that goes somewhere else gets its own repair", async () => {
  // The other side, and the reason the forgetting exists at all: a fresh
  // document gets a fresh patch at `document_start`, so whatever was wrong
  // with the last one is not wrong with this one. An operator who works in
  // one tab all day must not spend its only repair on the first page.
  ready();
  reloads.length = 0;

  const deaf = { tab: { id: 9595 } };
  await globalThis.__handle(
    { kind: "calls-not-recordable", holding: false },
    deaf,
    () => {},
  );
  await until(() => reloads.length === 1, "the page was not repaired at all");

  await globalThis.__committed({
    frameId: 0,
    tabId: 9595,
    url: "https://wms.example/somewhere-else",
    timeStamp: Date.now(),
    transitionType: "link",
  });
  await globalThis.__handle(
    { kind: "calls-not-recordable", holding: false },
    deaf,
    () => {},
  );
  await until(
    () => reloads.length === 2,
    "a different page was refused a repair it never had",
  );
});

test("a tab holding something typed is never reloaded", async () => {
  // A half-filled form is exactly the state this system spends its care
  // protecting, and throwing it away to repair this system's own plumbing
  // would be the worst trade it could make.
  ready();
  reloads.length = 0;

  await globalThis.__handle(
    { kind: "calls-not-recordable", holding: true },
    { tab: { id: 5151 } },
    () => {},
  );
  await new Promise((done) => setTimeout(done, 20));

  assert.deepEqual(
    reloads,
    [],
    "somebody's half-filled form was reloaded away",
  );
});

test("a finished card ends when the operator says they have read it", async () => {
  // Their press and nothing else. It used to go when the hour ran out or when
  // the next run started, so a card nobody had looked at could vanish and one
  // they had finished with sat there for an hour.
  ready();
  held.set("sro.finishedRun", {
    id: "run-9",
    source: "rig",
    status: "held",
    values: { "Customer Type": "NEX" },
    steps: [],
    at: Date.now(),
  });

  await send({ kind: "forget-run" });

  assert.equal(
    held.get("sro.finishedRun"),
    null,
    "the card the operator dismissed is still held",
  );
});

test("what this browser decided rides out on the next beat", async () => {
  // The extension had no voice. `run_workflow` narrates every rung it climbs
  // and the deployment's log reads like a transcript; the browser half of the
  // same run was a black box whose only voice was a service worker console
  // nobody can reach from a server, from another machine, or at two in the
  // morning. Measured over 2026-09-17: four faults in the backend were each
  // found within one run of being narrated, and the one that lived in here
  // took four runs and was still not found.
  ready();
  // After `ready()`, which resets both: it clears the storage AND sets
  // `mailLooked` back to null.
  held.delete("sro.mailLooked");
  mailLooked = {
    read: 1,
    why: "offered Create a Customer Type",
    offered: [
      {
        message: "m-88",
        workflow_id: "wfl-1",
        title: "Create a Customer Type",
        values: { "Customer Type": "GU9" },
        missing: [],
      },
    ],
  };

  await lookInTheMail();
  await globalThis.__beat({ name: "sro-heartbeat" });
  // The alarm's work is fired and not awaited, so the beat lands next turn.
  await new Promise((resolve) => setTimeout(resolve, 20));

  const beat = calls.filter((call) => call.path.endsWith("/heartbeat")).pop();
  const said = (JSON.parse(beat.body).said || []).join("\n");
  assert.match(said, /1 read, 1 offered/, said);
  assert.match(
    said,
    /mail offer for Create a Customer Type was neither started nor asked by the backend/,
    said,
  );
  // And the value the operator was sent is not in it. A line about a decision
  // is not a copy of the request.
  assert.ok(!said.includes("GU9"), said);
  // Carried ONCE. A buffer that is not emptied by the beat that carried it
  // repeats every line for ever, which is a log nobody can read and a browser
  // shouting the same sentence a minute.
  await globalThis.__beat({ name: "sro-heartbeat" });
  await new Promise((resolve) => setTimeout(resolve, 20));
  const beats = calls
    .filter((call) => call.path.endsWith("/heartbeat"))
    .map((call) => (JSON.parse(call.body).said || []).join("\n"))
    .filter((lines) => lines.includes("neither started nor asked"));
  assert.equal(
    beats.length,
    1,
    `it said the same line on ${beats.length} beats`,
  );
});

// -- what may become evidence -------------------------------------------------
//
// Three gates stand between a gesture and the evidence plane, and not one of
// them had a test: deleting any of the three left all 287 extension checks
// green. They are each about somebody's privacy or about what this system
// learns from, which makes an untested gate the most expensive kind here.

/** How many rows are waiting to go up. */
async function queued() {
  return queue.count();
}

test("a tab nobody is watching is not recorded, whatever it sends", async () => {
  // A content script outlives the watch that installed it -- a tab whose
  // grant expired, one the operator stopped watching, one left open from
  // before. The gate is here and not in the page because a page cannot be
  // trusted to stop sending.
  ready();
  held.set("sro.watched", []);
  await queue.clear();

  const said = await gesture("a", "NEW");

  assert.equal(said.ok, false);
  assert.equal(await queued(), 0, "an unwatched tab was recorded");
});

test("an excluded host is not recorded even when its tab is watched", async () => {
  // The tenant's own policy, enforced a second time here because the first
  // enforcement is a content script that may be old, wrong or lying. What
  // this protects is a mailbox: the comment above the gate records a
  // deployment where one host became 97% of a day's capture.
  ready();
  held.set("sro.policy", {
    capture_enabled: true,
    exclude_hosts: ["wms.example"],
  });
  await queue.clear();

  const said = await gesture("a", "NEW");

  assert.equal(said.ok, false);
  assert.equal(
    await queued(),
    0,
    "an excluded host reached the evidence plane",
  );
});

test("a question that has stopped standing is put down as soon as the reply says so", async () => {
  // Measured on the deployment 2026-09-22 at 01:24. The operator was four
  // answers into `Create a Customer Type`, could not supply Manufacturer, and
  // typed `no`. The door dropped the job and said so -- and the question they
  // had just dropped went on sitting under that sentence, a job that no longer
  // existed asking for a value.
  //
  // `lookForAQuestion` is the only other writer of this key and it runs on the
  // minute beat, so the stale card had up to a minute to be read as live. The
  // reply to the sentence already carries the whole thread.
  ready();
  held.set("sro.question", {
    id: "m_asked",
    text: "Manufacturer takes 10 characters. What should it be?",
    title: "Create a Customer Type",
    workflowId: "wfl_ct",
    missing: ["Manufacturer"],
    at: "2026-09-22T01:23:00Z",
  });
  chatRead = null;
  threadSaid = {
    id: "thr-1",
    messages: [
      {
        id: "m_asked",
        speaker: "assistant",
        text: "Manufacturer takes 10 characters. What should it be?",
        said_at: "2026-09-22T01:23:00Z",
        decision: { kind: "needs_values", workflow_id: "wfl_ct", missing: ["Manufacturer"] },
      },
      { id: "m_no", speaker: "operator", text: "no", said_at: "2026-09-22T01:24:00Z" },
      {
        id: "m_dropped",
        speaker: "assistant",
        text: "Dropped Create a Customer Type.",
        said_at: "2026-09-22T01:24:01Z",
        decision: { kind: "note" },
      },
    ],
  };

  await send({ kind: "thread-say", threadId: "thr-1", text: "no", tabId: TAB });

  assert.equal(
    held.get("sro.question") ?? null,
    null,
    "the panel went on drawing a question for a job that had been dropped",
  );
  threadSaid = null;
});

test("a question the reply still holds is put where the panel draws it", async () => {
  // The half that keeps this a hold rather than a clear: it must not put the
  // question down every time somebody types. An answer that did not settle it
  // leaves it standing, and the reply is where that is known -- a minute
  // before the beat would otherwise find out.
  ready();
  chatRead = null;
  const asking = {
    id: "m_again",
    speaker: "assistant",
    text: "I am still waiting on this one. Manufacturer takes 10 characters.",
    said_at: "2026-09-22T01:24:00Z",
    decision: { kind: "needs_values", workflow_id: "wfl_ct", missing: ["Manufacturer"] },
  };
  threadSaid = { id: "thr-1", messages: [asking] };

  await send({ kind: "thread-say", threadId: "thr-1", text: "i dont have one", tabId: TAB });

  assert.equal(held.get("sro.question")?.workflowId, "wfl_ct");
  assert.deepEqual(held.get("sro.question")?.missing, ["Manufacturer"]);
  threadSaid = null;
});

test("a popup says which tab opened it", async () => {
  ready();
  await queue.clear();

  // `popupEvent` is fired and forgotten from the listener, same as every
  // other `webNavigation` handler here, so the test waits for the row rather
  // than assuming one await landed it.
  const findMark = async () => {
    const rows = await queue.peek(20);
    return rows
      .map((row) => row.event)
      .find((event) => event.kind === "page" && event.page_kind === "popup_opened");
  };

  await globalThis.__popup({
    sourceTabId: TAB,
    tabId: 2,
    url: `${H}/picker`,
    timeStamp: Date.now(),
  });

  await until(async () => Boolean(await findMark()), "the popup was never recorded");
  const mark = await findMark();
  assert.equal(mark.tab_id, 2);
  assert.equal(mark.opener_tab_id, TAB);
});


test("nothing this browser sees or is asked starts a run: one engine, and it is the backend's", async () => {
  // Measured on QA 2026-09-28: one yes made three runs, a job started because
  // the operator opened a page, and 104 of 173 runs stopped when this browser
  // lost its tab. The backend starts every run and Steel runs it; this browser
  // records and watches. So a walk it recognises, a page it lands on, and
  // every press the panel ever sent for a run of its own start nothing here.
  ready();
  held.set("sro.arrivals", [{ id: "trg-page", page: "wms.example/wa" }]);
  await gesture("a", "A1");
  await gesture("b", "B1");
  await gesture("c", "C1");
  await globalThis.__committed({
    frameId: 0,
    tabId: TAB,
    url: PAGE,
    timeStamp: 42,
    transitionType: "link",
  });
  const offered = "n_1";
  for (const press of [
    { kind: "start-rig-run", nudgeId: offered, values: {} },
    { kind: "run-workflow", workflowId: "wfl_wa" },
    { kind: "retry-rig-run", workflowId: "wfl_wa", values: { workArea: "A1" } },
    {
      kind: "undo-rig-run",
      workflowId: "wfl_wa",
      values: { workArea: "A1" },
      undoesRun: "run-1",
    },
    { kind: "do-this-here", nudgeId: offered },
  ])
    await send(press);
  // And a yes, which is the conversation's to act on.
  threadSaid = {
    id: "thr-1",
    messages: [
      {
        id: "m2",
        speaker: "assistant",
        text: "Create Work Area -- want me to do it?",
        said_at: "2026-09-28T10:20:02Z",
        decision: { kind: "job", workflow_id: "wfl_wa", values: {} },
      },
    ],
  };
  await send({ kind: "thread-say", threadId: "thr-1", text: "yes", tabId: TAB });
  // What the navigation and the gestures set off is fired and forgotten, so
  // every turn that work could take is let run before anything is counted.
  for (let turn = 0; turn < 20; turn += 1)
    await new Promise((resolve) => setImmediate(resolve));

  const started = calls.filter(
    (call) =>
      call.method === "POST" &&
      (call.path === "/v1/workflow-runs" ||
        /\/arrivals\/[^/]+\/fire$/.test(call.path) ||
        /\/runs\/from-preview$/.test(call.path)),
  );
  assert.deepEqual(started, [], "this browser started a run of its own");
  assert.ok(
    calls.some(
      (call) => call.method === "POST" && call.path === "/v1/threads/thr-1/messages",
    ),
    "the yes never reached the backend's conversation",
  );
  threadSaid = null;
});
