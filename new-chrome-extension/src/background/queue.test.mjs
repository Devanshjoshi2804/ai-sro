// Self-check for the IndexedDB queue: no test framework in this extension yet,
// so this is a plain Node script against a minimal fake indexedDB. Run with
// `node src/background/queue.test.mjs`.

import assert from "node:assert";
import { fakeIndexedDB } from "./test-support/fake-indexeddb.mjs";

globalThis.indexedDB = fakeIndexedDB();
// queue.js rotates the epoch and clears any pending batch when it finds the
// store freshly created, and both of those live in chrome.storage. A dozen
// keys in a Map is the whole of what this needs from that API.
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
globalThis.crypto ??= (await import("node:crypto")).webcrypto;

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

// A screenshot rides with its gesture, is counted in the byte total, and is
// the first thing given up when the device is over budget -- before a response
// body, and long before the gesture it illustrates.
{
  await queue.clear();
  const shot = { mime: "image/png", size: 4000, bytes: new Uint8Array(4000) };
  await queue.enqueue({ kind: "gesture", n: 1 }, shot);
  await queue.enqueue({
    kind: "request",
    request: { url: "https://a.test/1", response_body: { text: "x".repeat(400), size_bytes: 400 } },
  });

  const withShot = await queue.totalBytes();
  assert.ok(withShot > 4000, `the picture is counted in the queue's bytes (${withShot})`);
  assert.strictEqual((await queue.peek(1))[0].shot.size, 4000, "the picture comes back with its row");

  const result = await queue.trim(1000);
  assert.strictEqual(result.strippedShots, 1, "the screenshot is given up first");
  assert.strictEqual(result.strippedBodies, 0, "a response body outlives a screenshot");
  assert.strictEqual(result.droppedEvents, 0, "nothing was dropped that could be stripped");

  const rows = await queue.peek(10);
  assert.strictEqual(rows[0].shot, null, "the picture is gone from the row");
  assert.strictEqual(rows[0].event.n, 1, "the gesture it illustrated is not");
  assert.ok((await queue.totalBytes()) < withShot, "trimming actually reduced the queue");
}

// Enqueued without one, and nothing pretends otherwise.
{
  await queue.clear();
  await queue.enqueue({ kind: "gesture", n: 1 });
  assert.strictEqual((await queue.peek(1))[0].shot, null);
}

// A staged screenshot survives its batch, is keyed by the frame it
// illustrates, and staging the same batch twice does not double it.
{
  await queue.clear();
  const shot = (n) => ({ mime: "image/png", size: 100 * n, bytes: new Uint8Array(100 * n) });
  // Staged out of the rows they were captured on, by id: the bytes are read
  // inside the transaction and nothing hands them around.
  const first = await queue.enqueue({ kind: "gesture", n: 1 }, shot(1));
  const second = await queue.enqueue({ kind: "gesture", n: 2 }, shot(2));
  await queue.stageShots("bat_1", [
    { rowId: first, frameIndex: 0 },
    { rowId: second, frameIndex: 2 },
  ]);
  await queue.stageShots("bat_1", [{ rowId: first, frameIndex: 0 }]);

  const staged = await queue.peekShots(10);
  assert.strictEqual(staged.length, 2, "a re-staged batch replaced its rows instead of doubling");
  // Order is not asserted here: re-staging bat_1:0 updates its stagedAt, and
  // peekShots sorts by stagedAt, so which row sorts first depends on whether
  // the two stageShots calls landed in the same millisecond. Only the keys matter.
  assert.deepStrictEqual(
    staged.map((row) => row.id).sort(),
    ["bat_1:0", "bat_1:2"],
    "keyed by the batch and the frame it illustrates",
  );
  const byId = Object.fromEntries(staged.map((row) => [row.id, row]));
  assert.strictEqual(byId["bat_1:0"].attempts, 0);
  assert.ok((await queue.totalBytes()) >= 300, "staged pictures are counted in the queue's bytes");
  assert.strictEqual(byId["bat_1:2"].size, 200, "the picture's bytes came off the row it was captured on");

  // Counted per picture, which is what decides when one is given up.
  assert.strictEqual(await queue.noteShotAttempt("bat_1:0"), 1);
  assert.strictEqual(await queue.noteShotAttempt("bat_1:0"), 2);
  const afterAttempt = Object.fromEntries((await queue.peekShots(10)).map((row) => [row.id, row]));
  assert.strictEqual(afterAttempt["bat_1:2"].attempts, 0, "only the one that failed");

  await queue.removeShots(["bat_1:0"]);
  assert.deepStrictEqual((await queue.peekShots(10)).map((row) => row.id), ["bat_1:2"]);
}

// Over budget, a staged picture goes before one still riding on a gesture that
// has not been sent -- its evidence is already stored, so it is the only thing
// left to lose.
{
  await queue.clear();
  const sent = await queue.enqueue(
    { kind: "gesture", n: 0 },
    { mime: "image/png", size: 4000, bytes: new Uint8Array(4000) },
  );
  await queue.stageShots("bat_1", [{ rowId: sent, frameIndex: 0 }]);
  await queue.remove([sent]);
  await queue.enqueue(
    { kind: "gesture", n: 1 },
    { mime: "image/png", size: 300, bytes: new Uint8Array(300) },
  );

  const result = await queue.trim(3000);
  assert.strictEqual(result.droppedShots, 1, "the staged picture went first");
  assert.strictEqual(result.strippedShots, 0, "and that was enough, so the queued one stayed");
  assert.strictEqual((await queue.peekShots(10)).length, 0);
  assert.strictEqual((await queue.peek(1))[0].shot.size, 300, "the unsent gesture kept its picture");
}

// A change of credential takes the pictures with it. One operator's screen
// must not be uploaded into the next operator's tenant.
{
  await queue.clear();
  const row = await queue.enqueue(
    { kind: "gesture", n: 1 },
    { mime: "image/png", size: 10, bytes: new Uint8Array(10) },
  );
  await queue.stageShots("bat_1", [{ rowId: row, frameIndex: 0 }]);
  await queue.clear();
  assert.strictEqual((await queue.peekShots(10)).length, 0);
  assert.strictEqual(await queue.totalBytes(), 0);
}

console.log("queue.test.mjs: ok");
