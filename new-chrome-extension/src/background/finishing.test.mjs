// Self-check for the quiet-run bookkeeping `service-worker.js` reads on the
// panel's own status poll to decide when to ask the backend whether a run
// that stopped sending commands actually finished.
//
// `performing()` going quiet is a local guess, never a verdict -- a run can
// legitimately pause between two of its own steps for longer than the quiet
// window. `runAwaitingFinish()` is what turns that guess into "go ask the
// backend", and `finishConfirmed()` is the only thing allowed to take it back,
// and only for the run it was told to. What matters here is that flag surviving
// exactly as long as it should: set the moment a run goes quiet, left alone by
// a confirmation naming some other run, and cleared by the one that names it.
//
// Run with `node src/background/finishing.test.mjs`.

import assert from "node:assert";

import { finishConfirmed, perform, performing, runAwaitingFinish } from "./commands.js";

// A command this browser has no handler for still updates the run this browser
// is performing -- `perform` records that before it ever looks at
// `command.kind` -- so this is enough to seed one without touching `chrome.*`
// at all (no `payload.origin`, so `announce()`'s own lookup never fires).
const RUN = { command_id: "cmd-1", run_id: "run-1", kind: "not-a-real-kind" };

const realNow = Date.now;

async function demo() {
  await perform(RUN);
  assert.ok(performing(), "a run just given a command is not performing");
  assert.strictEqual(runAwaitingFinish(), null, "nothing is awaiting confirmation yet");

  try {
    // Thirty-one seconds later, from this run's own point of view -- past the
    // quiet window `commands.js` uses everywhere else.
    Date.now = () => realNow() + 31_000;
    assert.strictEqual(performing(), null, "a quiet run is still claiming the panel");
    assert.strictEqual(
      runAwaitingFinish(),
      "run-1",
      "going quiet did not flag the run for a backend check",
    );

    // A confirmation naming a different run must not clear this one's flag --
    // the single slot is what makes that possible to get wrong.
    finishConfirmed("run-2");
    assert.strictEqual(
      runAwaitingFinish(),
      "run-1",
      "a different run's confirmation cleared this one's flag",
    );

    finishConfirmed("run-1");
    assert.strictEqual(runAwaitingFinish(), null, "confirming the right run left it flagged");
  } finally {
    Date.now = realNow;
  }
}

await demo();
console.log("finishing.test.mjs: ok");
