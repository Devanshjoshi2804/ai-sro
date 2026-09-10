// Self-check for what commands.js persists about the run it is driving, so a
// run that finishes with the panel closed can still be noticed once the
// worker wakes back up, and for the two pure decisions in state.js that grew
// out of round 2's review of that mechanism.
//
// `perform()` mirrors `{runId, at}` into `chrome.storage` on every run-bearing
// command -- `commands.js`'s own `latest` is a module variable and does not
// survive this worker idling out, which is the *ordinary* case for a run
// performed with nobody looking at the panel; `service-worker.js`'s
// `checkFinishing()` reads the mirror instead, off both the panel poll and the
// heartbeat alarm. And a new run starting clears whatever the last one left
// behind to be shown, because "Undo that" for the run before this one, next to
// a card saying this one is performing right now, is confusing even though
// neither fact is wrong.
//
// `activeRunAge` bounds how old a survivor may be before it is worth asking
// the backend about at all -- surviving eviction was the point, surviving
// indefinitely was not. `afterRunWrong` decides whether a finished-run row
// outlives a `run-wrong` call, keyed on which button sent it rather than on
// whether the run happens to have a reversal -- see the module comment on
// each in state.js for the reviews that produced them.
//
// Run with `node src/background/finishing.test.mjs`.

import assert from "node:assert";

// The same minimal chrome.storage.local fake `queue.test.mjs` uses: a dozen
// keys in a Map is the whole of what state.js needs from that API.
const held = new Map();
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
};

// What `api.call` reaches for. Set per-test by `stoppingIsNotAnAlarm` below;
// nothing else in this file makes a request, so an unset one is a test that
// would have gone to the network and did not mean to.
let answer = () => {
  throw new Error("no fetch was expected here");
};
globalThis.fetch = async (...args) => answer(...args);

const { perform } = await import("./commands.js");
const { activeRunAge, afterRunWrong, state } = await import("./state.js");
const { api } = await import("./api.js");
const { noteFinished } = await import("./finishing.js");

async function demo() {
  await perform({ command_id: "cmd-1", run_id: "run-1", kind: "not-a-real-kind" });
  const active = await state.activeRun();
  assert.strictEqual(active?.runId, "run-1", "a run-bearing command was not mirrored to storage");
  assert.ok(Number.isFinite(active.at), "no timestamp was recorded for the mirrored run");

  // Seed a finished card as though an earlier, different run had just been
  // confirmed -- the shape `service-worker.js`'s `noteFinished` writes.
  await state.setFinishedRun({
    id: "run-0",
    status: "succeeded",
    derived: {},
    reversal: null,
    failure: null,
    at: Date.now(),
  });

  // The same run continuing (another command for "run-1") must not touch it.
  await perform({ command_id: "cmd-2", run_id: "run-1", kind: "not-a-real-kind" });
  assert.ok(
    await state.finishedRun(),
    "the same run continuing cleared what an earlier, different run finished",
  );

  // A genuinely new run starting supersedes it.
  await perform({ command_id: "cmd-3", run_id: "run-2", kind: "not-a-real-kind" });
  assert.strictEqual(
    await state.finishedRun(),
    null,
    "a new run starting did not clear the last one's finished card",
  );
  const activeNow = await state.activeRun();
  assert.strictEqual(activeNow.runId, "run-2", "the newly active run was not recorded");
}

/** Round 2 review: `state.activeRun()` surviving a worker eviction had no
 * upper bound, so a run that went quiet before a laptop closed could be
 * "confirmed" a day after it actually finished, handing it a fresh hour of
 * "Undo that" for work nobody would recognise as recent. */
function ageBound() {
  const QUIET_MS = 30_000;
  const now = Date.now();

  assert.strictEqual(activeRunAge(null, now, QUIET_MS), "wait", "nothing active still asked the backend");
  assert.strictEqual(
    activeRunAge({ runId: "run-1", at: now - 5_000 }, now, QUIET_MS),
    "wait",
    "a run only 5s quiet was already asked about",
  );
  assert.strictEqual(
    activeRunAge({ runId: "run-1", at: now - 40_000 }, now, QUIET_MS),
    "confirm",
    "a genuinely quiet run was not offered up for a backend check",
  );
  assert.strictEqual(
    activeRunAge({ runId: "run-1", at: now - 25 * 3600_000 }, now, QUIET_MS),
    "stale",
    "a day-old quiet run was still confirmed, handing it a fresh hour of offering an undo",
  );
}

/** Round 2 review: the keep-vs-delete decision after `run-wrong` used to be
 * keyed on whether the run had a reversal at all, so pressing "It's wrong --
 * I'll fix it" on a run that also had one left the row -- and "Undo that" --
 * standing for an hour. Pressing it then would reverse the very correction
 * the operator had just been told to make by hand. Both presses below answer
 * for the *same* run, one that does have a reversal, so a fix that merely
 * stopped keying on `reversal` without keying on the press itself would still
 * pass the first assertion and only the second would catch it.
 */
function keyedOnThePress() {
  const withReversal = { id: "run-1", reversal: { skill_id: "skl-2", parameters: {} } };

  // "Undo that" pressed: `undoRun` in panel.js sends `keepForRetry: true`
  // because it still has a second step left -- starting the reversal.
  const afterUndo = afterRunWrong(withReversal, "undone by the operator", true);
  assert.ok(afterUndo, "'Undo that' on a run with a reversal did not keep the row to retry");
  assert.strictEqual(afterUndo.wrongBecause, "undone by the operator");

  // "It's wrong -- I'll fix it" pressed on that *same* run: `wasWrong` in
  // panel.js never sends `keepForRetry`. The operator's own hands are the
  // correction from here, so the row -- and "Undo that" alongside it -- must
  // end, reversal or not.
  const afterWrong = afterRunWrong(withReversal, "the operator said this was wrong", false);
  assert.strictEqual(
    afterWrong,
    null,
    "'It's wrong' on a run with a reversal left the row -- and 'Undo that' -- standing",
  );
}

/** A workflow run, in the panel's vocabulary, off the backend's own door.
 *
 * Two vocabularies meet in `api.rigRun` and nowhere else: a workflow run's
 * `outcome` is the panel's `status`, and its `{order, says, verdict}` is the
 * card's `{index, outcome, says, reason}`. Every other test here stubs that
 * call, so this is the one that would notice if the mapping read the wrong
 * field -- `order` as `index` is the whole of what puts a step's glyph on the
 * right row.
 *
 * Driven through the real `fetch` stub above rather than a fake `api`, because
 * the thing under test *is* what the answer is turned into.
 *
 * The wire is pinned as well as the mapping. `/v1/runs/{id}` on this host is a
 * *skill* run keyed on a different id space, so a call that reverted to it
 * would 404 in production and answer somebody else's row in the worst case;
 * and `X-Device-Secret` is what makes this browser itself rather than anyone
 * holding the tenant's token. Both are asserted against values chosen so that
 * a literal frozen into `api.js` could not be them by accident.
 */
async function theRigsRunInThePanelsWords() {
  await state.setToken("tok-run-5d19");
  await state.setDeviceSecret("sec-run-8c40");
  /** Every request `api.rigRun` made: url, method, headers. */
  const wire = [];
  const record = (url, options = {}) => {
    wire.push({
      url: String(url),
      method: options.method || "GET",
      headers: options.headers || {},
      body: options.body,
    });
  };

  answer = async (url, options) => (record(url, options), {
    ok: true,
    status: 200,
    json: async () => ({
      id: "run_a1b2",
      outcome: "held",
      steps: [
        {
          order: 0,
          says: "open the supplier form",
          verdict: "held",
          reason: "it did",
          matched_by: "css_path",
          stale: true,
          cost_usd: 0.0123,
        },
        // A step the rig has stopped on: the write is planned, nothing has
        // been sent, and it is waiting for a person. The panel cannot ask for
        // approval of a command it was never given, so `sent` comes across
        // with the rest of the record rather than being dropped here.
        {
          order: 1,
          says: "save",
          verdict: "awaiting",
          reason: "",
          sent: { kind: "ui.perform", payload: { action: "click" } },
          // A call that never returned. It is not a free one, and the panel
          // must not draw it as $0.0000.
          unpriced: true,
        },
      ],
      withheld: [{ origin: "https://wms.test" }],
    }),
  });
  const mapped = await api.rigRun("run_a1b2");
  assert.strictEqual(mapped.source, "rig");
  assert.strictEqual(mapped.status, "held", "the rig's outcome is the panel's status");
  assert.deepStrictEqual(mapped.steps, [
    {
      index: 0,
      outcome: "held",
      says: "open the supplier form",
      reason: "it did",
      sent: null,
      matched_by: "css_path",
      stale: true,
      cost_usd: 0.0123,
      unpriced: false,
    },
    {
      index: 1,
      outcome: "awaiting",
      says: "save",
      reason: "",
      sent: { kind: "ui.perform", payload: { action: "click" } },
      matched_by: null,
      stale: false,
      cost_usd: null,
      unpriced: true,
    },
  ]);
  assert.strictEqual(mapped.withheld.length, 1);

  // The door, whole. Not `/v1/runs/{id}`, which on this host is a skill run
  // keyed on a `RunId` -- see `workflow_runs.py`'s module docstring.
  assert.strictEqual(wire.length, 1, "one read of the run, and one request for it");
  assert.strictEqual(
    wire[0].url,
    "http://localhost:8000/v1/workflow-runs/run_a1b2",
    "a workflow run was read from somewhere other than the backend's workflow-run door",
  );
  assert.strictEqual(wire[0].method, "GET");
  assert.strictEqual(wire[0].body, undefined, "a read carried a body");
  assert.strictEqual(
    wire[0].headers["X-Device-Secret"],
    "sec-run-8c40",
    "the run was read without this browser proving it is itself",
  );
  assert.strictEqual(wire[0].headers.Authorization, "Bearer tok-run-5d19");

  // The run id is the caller's and is never a constant: a frozen one would
  // draw whatever run happened to be named in `api.js` over the one the
  // operator is watching.
  wire.length = 0;
  await api.rigRun("run_c9d4");
  assert.strictEqual(wire[0].url, "http://localhost:8000/v1/workflow-runs/run_c9d4");

  // The one status both vocabularies share, and it has to survive the mapping:
  // a run still running is what `noteFinished` refuses to write a card for.
  answer = async () => ({ ok: true, status: 200, json: async () => ({ id: "r", outcome: "running" }) });
  assert.strictEqual((await api.rigRun("r")).status, "running");

  // And a backend that has never heard of the run says so with a status on it
  // -- `noteFinished` reads that 404 to stop asking. A failed read must never
  // be mapped as though it were a row.
  answer = async () => ({ ok: false, status: 404, json: async () => ({}) });
  await assert.rejects(() => api.rigRun("nope"), (error) => error.status === 404);
}

/** Which failures of `POST /runs/{id}/stop` are worth telling an operator
 * about, and which are the ordinary race.
 *
 * The Stop button does two things: it refuses every further command for the
 * run in this browser, and it tells the backend to stop driving it. The second
 * can fail, and the two ways it fails are not alike. A 409 is the backend
 * saying there was nothing left to stop -- the run finished a moment ago, or
 * the press landed twice -- which is what happens whenever somebody presses
 * Stop as a run is ending, and reporting it made the button read "the run
 * could not be told: that run already succeeded". A stop control alarming
 * about a run that had already stopped is worse than the silence it replaced.
 *
 * Anything else means a run still stepping somewhere with nobody told to stop
 * it, and the operator who just pressed Stop is the only person who can act
 * on that, so it still throws.
 *
 * Exercised through `api.stopRun` rather than through the worker's message
 * handler, which is where this decision used to sit: `service-worker.js`
 * registers chrome listeners the moment it is imported and cannot be loaded
 * here at all, and a rule nothing can test is a rule that drifts.
 */
async function stoppingIsNotAnAlarm() {
  answer = async () => ({
    ok: false,
    status: 409,
    json: async () => ({ detail: "that run already succeeded" }),
  });
  assert.strictEqual(
    await api.stopRun("run-1"),
    null,
    "a run that had already ended was reported to the operator as a failure to stop",
  );

  answer = async () => {
    throw new TypeError("Failed to fetch");
  };
  await assert.rejects(
    () => api.stopRun("run-1"),
    /Failed to fetch/,
    "a backend that could not be reached at all was swallowed, leaving a run stepping unstopped",
  );

  // And a refusal that is neither: still the operator's business.
  answer = async () => ({
    ok: false,
    status: 500,
    json: async () => ({ detail: "the run store is down" }),
  });
  await assert.rejects(() => api.stopRun("run-1"), /run store is down/);
}

/** Which process is asked how a run ended.
 *
 * A run the rig drove is a run the backend has never heard of: its id is the
 * rig's, and `GET /v1/runs/{id}` there answers 404 -- so a browser that asked
 * the backend about it would store nothing and go on asking forever. What
 * decides is the `source` the command arrived on, mirrored beside the run id
 * by `perform()` above.
 *
 * A record with no `source` at all is a backend run: older workers wrote none,
 * and reading a missing field as "rig" would send every one of them to a rig
 * that may not even be configured.
 */
async function whoIsAskedHowItEnded() {
  const asked = [];
  const realRun = api.run;
  const realRigRun = api.rigRun;
  api.run = async (runId) => {
    asked.push(["backend", runId]);
    return { id: runId, status: "succeeded", derived: {}, reversal: null };
  };
  api.rigRun = async (runId) => {
    asked.push(["rig", runId]);
    return {
      id: runId,
      source: "rig",
      status: "held",
      steps: [{ index: 0, outcome: "held", says: "open the supplier form", reason: "" }],
      withheld: [{ origin: "https://wms.test" }],
    };
  };
  try {
    await state.setActiveRun({ runId: "run-rig", at: Date.now(), source: "rig" });
    await noteFinished(await state.activeRun());
    const rigRow = await state.finishedRun();
    assert.strictEqual(rigRow?.source, "rig", "a rig run was not recorded as one");
    assert.strictEqual(rigRow.status, "held", "the rig's own outcome was not kept");
    assert.deepStrictEqual(
      rigRow.steps.map((step) => step.says),
      ["open the supplier form"],
      "the rig run's steps were not kept, so the card has nothing to draw",
    );
    assert.strictEqual(rigRow.withheld.length, 1, "what the dry run withheld was dropped");
    assert.deepStrictEqual(
      asked,
      [["rig", "run-rig"]],
      "the backend was asked how a rig run ended -- it has never heard of it",
    );
    assert.strictEqual(
      await state.activeRun(),
      null,
      "a confirmed rig run stayed active, so it will be asked about forever",
    );

    // No `source` at all: an older worker's row, or the backend's own path.
    asked.length = 0;
    await state.setActiveRun({ runId: "run-old", at: Date.now() });
    await noteFinished(await state.activeRun());
    const backendRow = await state.finishedRun();
    assert.strictEqual(
      backendRow?.source,
      "backend",
      "a record with no source was not read as a backend run",
    );
    assert.deepStrictEqual(asked, [["backend", "run-old"]], "a backend run went to the rig");

    // A rig that answered "no such run" will go on answering it -- its store
    // went with its last restart -- so this browser stops asking rather than
    // polling for the hour it takes to age out.
    api.rigRun = async () => {
      const gone = new Error("the rig has no run run-gone");
      gone.status = 404;
      throw gone;
    };
    await state.setActiveRun({ runId: "run-gone", at: Date.now(), source: "rig" });
    await noteFinished(await state.activeRun());
    assert.strictEqual(
      await state.activeRun(),
      null,
      "a run the rig says does not exist was still being asked about",
    );
  } finally {
    api.run = realRun;
    api.rigRun = realRigRun;
  }
}

await demo();
await whoIsAskedHowItEnded();
ageBound();
keyedOnThePress();
await stoppingIsNotAnAlarm();
await theRigsRunInThePanelsWords();
console.log("finishing.test.mjs: ok");
