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

// Bytes, not UTF-16 characters: a multibyte payload must not under-report.
{
  await queue.clear();
  await queue.enqueue({ kind: "page", url: "«»«»«»" });
  const bytes = await queue.totalBytes();
  const chars = JSON.stringify({ kind: "page", url: "«»«»«»" }).length;
  assert.ok(bytes > chars, `multibyte payload sized in bytes (${bytes}) not chars (${chars})`);
}

// clear() empties the store -- the sign-out path depends on it.
{
  await queue.enqueue({ kind: "gesture", n: 9 });
  await queue.clear();
  assert.strictEqual(await queue.count(), 0);
}

// trim() gives up response bodies before events, and never gives up a gesture.
{
  await queue.clear();
  const big = "x".repeat(4000);
  await queue.enqueue({ kind: "gesture", n: 1 });
  await queue.enqueue({
    kind: "request",
    request: { url: "https://a.test/1", response_body: { text: big, size_bytes: big.length } },
  });
  await queue.enqueue({
    kind: "request",
    request: { url: "https://a.test/2", response_body: { text: big, size_bytes: big.length } },
  });
  await queue.enqueue({ kind: "gesture", n: 2 });

  const before = await queue.totalBytes();
  assert.ok(before > 8000, "the fixture is big enough to need trimming");

  const result = await queue.trim(2000);
  assert.ok(result.strippedBodies > 0, "response bodies are given up first");

  const rows = await queue.peek(10);
  const gestures = rows.filter((r) => r.event.kind === "gesture");
  assert.strictEqual(gestures.length, 2, "a gesture is never dropped");
  for (const row of rows.filter((r) => r.event.kind === "request")) {
    assert.strictEqual(row.event.request.response_body.text, null, "body text is gone");
  }
  assert.ok((await queue.totalBytes()) < before, "trimming actually reduced the queue");
}

// A queue already under budget is left alone.
{
  await queue.clear();
  await queue.enqueue({ kind: "gesture", n: 1 });
  const before = await queue.totalBytes();
  const result = await queue.trim(1024 * 1024);
  assert.deepStrictEqual(
    { stripped: result.strippedBodies, dropped: result.droppedEvents },
    { stripped: 0, dropped: 0 },
  );
  assert.strictEqual(await queue.totalBytes(), before);
}

// Gestures alone over budget: kept anyway, because losing one loses the fact
// that the operator did anything at all.
{
  await queue.clear();
  for (let n = 0; n < 5; n += 1) await queue.enqueue({ kind: "gesture", n, pad: "y".repeat(500) });
  const result = await queue.trim(100);
  assert.strictEqual(result.droppedEvents, 0);
  assert.strictEqual(await queue.count(), 5);
}

console.log("queue.test.mjs: ok");
