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

await demo();
ageBound();
keyedOnThePress();
await stoppingIsNotAnAlarm();
console.log("finishing.test.mjs: ok");
