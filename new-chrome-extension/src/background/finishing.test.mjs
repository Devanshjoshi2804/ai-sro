// Self-check for how a watched run's end is noticed and kept for the card, and
// for the pure decision in state.js that bounds how old a watched run may be.
//
// `service-worker.js`'s `checkFinishing()` reads `state.activeRun()` off both
// the panel poll and the heartbeat alarm, and hands the record to
// `noteFinished`, which asks the right door and keeps what came back.
// `activeRunAge` bounds how old a survivor may be before it is worth asking
// the backend about at all -- surviving eviction was the point, surviving
// indefinitely was not.
//
// Run with `node src/background/finishing.test.mjs`.

import { DEFAULT_API_URL } from "./deployment.generated.js";
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

const { activeRunAge, state } = await import("./state.js");
const { api } = await import("./api.js");
const { noteFinished } = await import("./finishing.js");

/** Round 2 review: `state.activeRun()` surviving a worker eviction had no
 * upper bound, so a run that went quiet before a laptop closed could be
 * "confirmed" a day after it actually finished, handing it a fresh hour of a
 * card for work nobody would recognise as recent. */
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
    "a day-old quiet run was still confirmed, handing it a fresh hour of a card",
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
      // Which thing on the list, and which step of the job. Null and the same
      // number for a job that does one thing once, which is most of them.
      item: null,
      of_step: 0,
      // Nothing created: most steps make no record, and the ones that do are
      // what a person goes and looks at.
      made: {},
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
      item: null,
      of_step: 1,
      made: {},
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
    `${DEFAULT_API_URL}/v1/workflow-runs/run_a1b2`,
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
  assert.strictEqual(wire[0].url, `${DEFAULT_API_URL}/v1/workflow-runs/run_c9d4`);

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
 * decides is the `source` written beside the run id when the panel started
 * watching it.
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

/** What the card reads about a run has to survive the mapping.
 *
 * `api.rigRun` is a whitelist: a field not named there does not reach the
 * panel. `watched` and `needs` were added to the row and read by the card
 * without ever being added in between, so every run drew "Nobody was watching,
 * so it replayed the call" -- including the ones somebody pressed and watched
 * -- and a run that stopped to ask carried no names for the panel to notice.
 * Measured on the deployment, 2026-09-17 at 10:49: `watched=true` on the row,
 * "nobody was watching" on the card.
 */
async function theCardGetsWhatItDraws() {
  const row = {
    id: "run_1",
    outcome: "held",
    watched: true,
    needs: ["Customer Type Description"],
    gathered: { "Customer Type": { value: "GQX" } },
    doing: "looking in your mail",
    steps: [],
  };
  answer = async () =>
    new Response(JSON.stringify(row), {
      status: 200,
      headers: { "content-type": "application/json" },
    });

  const mapped = await api.rigRun("run_1");

  assert.equal(mapped.watched, true, "every run read as unwatched");
  assert.deepEqual(mapped.needs, ["Customer Type Description"]);
  assert.equal(mapped.gathered["Customer Type"].value, "GQX");
  assert.equal(mapped.doing, "looking in your mail");
}

/** The card names the record a run wrote, and could not, because this
 * projection is a SUBSET of the run and `values` was not in it.
 *
 * `WorkflowRunModel` carries them and `api.rigRun` maps them; nothing carried
 * them this far. So a card built to name the record named nothing, and looked
 * exactly like a card that had not been changed. */
async function theStoredRunCarriesWhatItWrote() {
  await state.setActiveRun({ runId: "run_w", at: Date.now(), source: "rig" });
  answer = async () =>
    new Response(
      JSON.stringify({
        id: "run_w",
        outcome: "held",
        values: {
          "Customer Type": "NSSR",
          "Customer Type Description": "Leaning new SRO type 050",
        },
        steps: [],
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    );

  await noteFinished({ runId: "run_w", source: "rig" });

  const held = await state.finishedRun();
  assert.ok(held, "nothing was stored for a finished run");
  assert.deepEqual(
    held.values,
    {
      "Customer Type": "NSSR",
      "Customer Type Description": "Leaning new SRO type 050",
    },
    "the card cannot name what the run wrote",
  );
}

await theStoredRunCarriesWhatItWrote();
await whoIsAskedHowItEnded();
ageBound();
await stoppingIsNotAnAlarm();
await theRigsRunInThePanelsWords();
await theCardGetsWhatItDraws();
console.log("finishing.test.mjs: ok");