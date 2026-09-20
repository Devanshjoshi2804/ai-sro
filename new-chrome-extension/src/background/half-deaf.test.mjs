// A tab is reloaded once to repair a half-installed recorder, and once ever.
//
// The guard was a module Set, and a module Set is emptied every time the
// service worker is evicted -- which is every few seconds. So "once per tab,
// ever" held for one eviction cycle and the loop it exists to stop ran anyway,
// with a pause in it.
//
// Measured on the deployment 2026-09-20: the console's own page reloaded 68
// times in four minutes, once every three and a half seconds. Each reload
// reported the same half-installed recorder to a fresh worker that had never
// heard of it, and the extension narrated the repair each time, truthfully.
//
// Run with `node src/background/half-deaf.test.mjs`.

import assert from "node:assert/strict";
import { test } from "node:test";

let stored = {};

globalThis.chrome = {
  storage: {
    local: {
      // A key that was never set is ABSENT, as Chrome leaves it -- not
      // present and undefined. `state.read` returns its fallback on `key in
      // held`, so a fake that always includes the key hands back `undefined`
      // where the real one hands back the default, and every caller that
      // relies on the default is tested against a lie.
      get: async (keys) =>
        Object.fromEntries(
          (Array.isArray(keys) ? keys : [keys])
            .filter((key) => key in stored)
            .map((key) => [key, stored[key]]),
        ),
      set: async (pairs) => Object.assign(stored, pairs),
      remove: async () => {},
    },
  },
  runtime: { lastError: null },
};

const { state } = await import("./state.js");

const fresh = () => {
  stored = {};
};

test("a tab that has been repaired is remembered where a worker cannot forget it", async () => {
  fresh();

  await state.setRepaired([148285683]);

  // What a worker that has just started sees: it has never heard of this tab.
  assert.deepEqual(await state.repaired(), [148285683]);
});

test("a browser that has never repaired anything says so", async () => {
  fresh();

  assert.deepEqual(await state.repaired(), []);
});

test("the list is bounded, so a long-lived browser does not grow one forever", async () => {
  // Tab ids are reused by Chrome, and a list that only grows is a list that
  // refuses a repair to a tab that has never had one.
  fresh();
  const many = Array.from({ length: 60 }, (_, n) => n);

  await state.setRepaired(many.slice(-40));

  assert.equal((await state.repaired()).length, 40);
  assert.equal((await state.repaired())[0], 20, "the oldest went");
});
