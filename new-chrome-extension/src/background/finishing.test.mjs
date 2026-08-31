// Self-check for what commands.js persists about the run it is driving, so a
// run that finishes with the panel closed can still be noticed once the
// worker wakes back up.
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

const { perform } = await import("./commands.js");
const { state } = await import("./state.js");

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

await demo();
console.log("finishing.test.mjs: ok");
