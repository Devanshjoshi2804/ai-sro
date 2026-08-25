// The one thing queue.test.mjs cannot check: what happens when the database is
// already there.
//
// queue.js bumped to version 2 for the shot store, and the rule that came with
// it is that a *created* store rotates the queue epoch while an *upgraded* one
// does not. The epoch is in every batch id; rotating it over live rows re-mints
// an id for a batch already in flight, and the backend stores that batch twice.
//
// Its own file because queue.js opens the database once, when it is imported:
// a single process can only ever see one of the two cases.

import assert from "node:assert";
import { fakeIndexedDB } from "./test-support/fake-indexeddb.mjs";

const held = new Map([["sro.queueEpoch", "epoch-from-before"]]);
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
globalThis.crypto ??= (await import("node:crypto")).webcrypto;

// A database already at version 1: the shape every browser that ran the last
// release has on disk.
globalThis.indexedDB = fakeIndexedDB(1);

const queue = await import("./queue.js");
const { state } = await import("./state.js");

await queue.enqueue({ kind: "gesture", n: 1 });

assert.strictEqual(
  await state.queueEpoch(),
  "epoch-from-before",
  "a version upgrade rotated the queue epoch, so a batch in flight would be re-minted and stored twice",
);

// And the store the upgrade was for is really there.
const row = await queue.enqueue(
  { kind: "gesture", n: 2 },
  { mime: "image/png", size: 8, bytes: new Uint8Array(8) },
);
await queue.stageShots("bat_1", [{ rowId: row, frameIndex: 0 }]);
assert.strictEqual((await queue.peekShots(10)).length, 1, "the upgrade did not create the shot store");

console.log("queue.upgrade.test.mjs: ok");
