// Self-check for the IndexedDB queue: no test framework in this extension yet,
// so this is a plain Node script against a minimal fake indexedDB. Run with
// `node src/background/queue.test.mjs`.

import assert from "node:assert";
import { fakeIndexedDB } from "./test-support/fake-indexeddb.mjs";

globalThis.indexedDB = fakeIndexedDB();
const queue = await import("./queue.js");

await queue.enqueue({ kind: "gesture", n: 1 });
await queue.enqueue({ kind: "gesture", n: 2 });
await queue.enqueue({ kind: "gesture", n: 3 });

assert.strictEqual(await queue.count(), 3);

const first = await queue.peek(2);
assert.deepStrictEqual(
  first.map((r) => r.event.n),
  [1, 2],
  "peek returns oldest-first",
);

const totalBefore = await queue.totalBytes();
assert.ok(totalBefore > 0, "totalBytes sums recorded sizes");

await queue.remove([first[0].id]);
assert.strictEqual(await queue.count(), 2);

const remaining = await queue.peek(10);
assert.deepStrictEqual(
  remaining.map((r) => r.event.n),
  [2, 3],
  "remove drops only the given rows, order preserved",
);

console.log("queue.test.mjs: ok");
