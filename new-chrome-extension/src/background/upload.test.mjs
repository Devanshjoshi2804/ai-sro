// Self-check for the client half of the evidence pipeline: `flush()`.
//
// Every gesture an operator makes leaves this browser through here, and until
// now nothing stood the function up -- so a whole-branch review could replace
// `device_id` with a literal, `batch_id` with a constant, `frame_index` with
// zero, widen `isPermanent` over 401 and 429, and delete the device-secret
// guard, and all 25 suites stayed green. The worst of those is silent: a
// constant `batch_id` makes the backend answer the second batch
// `already_had_it`, and its rows are then deleted as though they had been
// stored.
//
// The real queue against a fake IndexedDB, the real `state` against a Map, and
// a recording `fetch`: what is checked here is what actually goes on the wire,
// because that is where every one of those mutations shows up.
//
// Run with `node src/background/upload.test.mjs`.

import assert from "node:assert/strict";
import test from "node:test";

import { fakeIndexedDB } from "./test-support/fake-indexeddb.mjs";

globalThis.indexedDB = fakeIndexedDB();
globalThis.crypto ??= (await import("node:crypto")).webcrypto;

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

const BACKEND = "http://backend.test";
// Distinctive on purpose, and nothing like the `dev-1` a mutation reaches for:
// an assertion written against the same literal the mutation uses pins nothing.
const DEVICE = "dev_9f3c1a";

held.set("sro.apiUrl", BACKEND);
held.set("sro.token", "tok-upload-4b12");
held.set("sro.deviceSecret", "secret-upload-77e9");

/** Every request `flush()` made, in order. */
let asked = [];
/** What the next request is answered with, by path. */
let serve = {};

function json(body, status = 200) {
  return { ok: status < 400, status, statusText: "", json: async () => body };
}

globalThis.fetch = async (url, options = {}) => {
  const path = String(url).slice(BACKEND.length);
  asked.push({ path, method: options.method || "GET", body: options.body });
  return serve[path] ?? json({ accepted: 1 });
};

const queue = await import("./queue.js");
const { state } = await import("./state.js");
const { flush } = await import("./upload.js");

function ready() {
  asked = [];
  serve = {};
}

const gesture = (n) => ({ kind: "gesture", n });
const picture = (n) => ({ bytes: new Uint8Array([n, n, n]), mime: "image/png", size: 3 });

const batchesSent = () => asked.filter((call) => call.path === "/v1/observations");
const shotsSent = () => asked.filter((call) => call.path === "/v1/observations/artifacts");

test("a batch names this browser and its own id, and a picture names the gesture it followed", async () => {
  ready();
  await queue.clear();
  // Two gestures, only the second photographed: a `frame_index` replaced by a
  // constant zero would still look right if the picture hung on the first.
  const firstRow = await queue.enqueue(gesture(1));
  await queue.enqueue(gesture(2), picture(2));

  const first = await flush(DEVICE);
  assert.equal(first.uploaded, 2, "both queued gestures should have gone");
  assert.equal(first.screenshots, 1);

  const body = JSON.parse(batchesSent()[0].body);
  assert.equal(body.device_id, DEVICE, "the batch was uploaded under some other browser's id");
  assert.deepEqual(
    body.events.map((event) => event.n),
    [1, 2],
    "the batch did not carry the queued events",
  );

  const epoch = await state.queueEpoch();
  assert.equal(
    body.batch_id,
    `bat_9f3c1a_${epoch}_${firstRow}`,
    "the batch id is not derived from this browser, this store and its oldest row",
  );

  const form = shotsSent()[0].body;
  assert.equal(form.get("device_id"), DEVICE, "the picture was uploaded under some other browser's id");
  assert.equal(form.get("batch_id"), body.batch_id, "the picture names a batch other than its own");
  assert.equal(
    form.get("frame_index"),
    "1",
    "the picture claims to illustrate a gesture other than the one it followed",
  );

  // The id must move with the batch. Frozen to a constant, the backend answers
  // the second batch `already_had_it` and this client deletes its rows.
  ready();
  await queue.enqueue(gesture(3));
  await flush(DEVICE);
  const second = JSON.parse(batchesSent()[0].body);
  assert.notEqual(second.batch_id, body.batch_id, "a second batch reused the first batch's id");
  assert.equal(await queue.count(), 0, "an accepted batch left rows behind");
});

test("a refusal waiting will fix keeps the rows; one it will not drops them", async () => {
  // 429: the backend is asking for a slower minute, not refusing the evidence.
  ready();
  await queue.clear();
  await queue.enqueue(gesture(4));
  serve["/v1/observations"] = json({ detail: "slow down" }, 429);
  const throttled = await flush(DEVICE);
  assert.equal(throttled.uploaded, 0);
  assert.equal(await queue.count(), 1, "a 429 threw the operator's evidence away instead of retrying");

  // 401: the credential needs replacing, which the heartbeat does. The rows
  // wait for it -- and the caller hears about it rather than reading a zero.
  ready();
  serve["/v1/observations"] = json({ detail: "no" }, 401);
  await assert.rejects(() => flush(DEVICE), /not accepted/, "a 401 did not reach the caller");
  assert.equal(await queue.count(), 1, "a 401 threw the operator's evidence away instead of re-authenticating");
  held.set("sro.token", "tok-upload-4b12"); // `call()` drops it on a 401.

  // 413: too large is too large on every later attempt too, and a batch
  // retried forever blocks everything queued behind it.
  ready();
  serve["/v1/observations"] = json({ detail: "that batch is too large" }, 413);
  const refused = await flush(DEVICE);
  assert.equal(refused.dropped, 1);
  assert.match(refused.error, /permanently \(413\)/, "a dropped batch was dropped quietly");
  assert.equal(await queue.count(), 0, "a permanently refused batch stayed at the head of the queue");
});

test("a browser that cannot prove who it is sends nothing and keeps everything", async () => {
  ready();
  await queue.clear();
  await queue.enqueue(gesture(5));
  held.set("sro.deviceSecret", "");

  assert.deepEqual(await flush(DEVICE), { uploaded: 0 });
  assert.deepEqual(asked, [], "a browser with no secret still called the backend");
  // The 404 a secretless browser gets reads as permanent, so trying would drop
  // the queue a minute before the heartbeat hands this browser a secret.
  assert.equal(await queue.count(), 1, "the queue was emptied while the browser had nothing to prove itself with");

  held.set("sro.deviceSecret", "secret-upload-77e9");
});

test("a 401 for a credential since replaced does not take the new one with it", async () => {
  // A call already in flight when somebody signs in was made with the old
  // credential; its refusal is about that one.
  ready();
  await queue.clear();
  await queue.enqueue(gesture(9));
  const before = globalThis.fetch;
  globalThis.fetch = async () => {
    held.set("sro.token", "tok-pasted-just-now");
    return json({ detail: "no" }, 401);
  };
  try {
    await assert.rejects(() => flush(DEVICE), /not accepted/);
  } finally {
    globalThis.fetch = before;
  }
  assert.equal(held.get("sro.token"), "tok-pasted-just-now", "a stale 401 signed the operator out");
  held.set("sro.token", "tok-upload-4b12");
});
