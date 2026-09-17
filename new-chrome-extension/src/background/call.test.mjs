// A replayed call that fails says enough to tell which failure it was.
//
// `TypeError: Failed to fetch` is what a browser says for every one of: the
// host did not resolve, the connection was refused, CORS refused the response,
// and the document running the request was torn down mid-flight. Four faults,
// one sentence.
//
// Measured on the deployment, 2026-09-17: `run_e1ff6362` step 6 failed
// `unreachable: TypeError: Failed to fetch`, and the only reason anybody knows
// it stalled for 54 seconds first is that two log lines on the SERVER happened
// to bracket it. An instant failure is a refusal; a long one is a connection
// nobody answered. Those want different fixes.
//
// Run with `node src/background/call.test.mjs`.

import assert from "node:assert/strict";
import { test } from "node:test";

const { sendInPage } = await import("./in-page.js");

/** What a browser rejects an aborted fetch with, made without naming
 * `DOMException` -- which node has and eslint's browser globals do not. */
const abortError = () => Object.assign(new Error("aborted"), { name: "AbortError" });

// Node has its own `navigator` and it is a getter, so it is redefined rather
// than assigned. The page code reads `navigator.onLine` and nothing else.
const online = (is) =>
  Object.defineProperty(globalThis, "navigator", {
    value: { onLine: is },
    configurable: true,
  });

const answering = (fn) => {
  globalThis.fetch = fn;
  online(true);
};

test("a call that worked carries what the system said", async () => {
  answering(async () => ({
    status: 201,
    headers: { forEach: (fn) => fn("application/json", "content-type") },
    text: async () => '{"id":1}',
  }));

  const said = await sendInPage({ url: "https://wms.example/api/x", method: "POST" });

  assert.equal(said.ok, true);
  assert.equal(said.result.status, 201);
  assert.equal(said.result.body, '{"id":1}');
});

test("a refusal says how long it took to be refused", async () => {
  // The fact that tells a refusal from a stall, and it costs nothing.
  answering(async () => {
    throw new TypeError("Failed to fetch");
  });

  const said = await sendInPage({ url: "https://wms.example/api/x" });

  assert.equal(said.ok, false);
  assert.equal(said.error.kind, "unreachable");
  assert.match(said.error.detail, /Failed to fetch after \d+ms/, said.error.detail);
});

test("a browser with no network says so, rather than blaming the system", async () => {
  answering(async () => {
    throw new TypeError("Failed to fetch");
  });
  online(false);

  const said = await sendInPage({ url: "https://wms.example/api/x" });

  assert.match(said.error.detail, /this browser is offline/, said.error.detail);
});

test("a call that hangs is given up on, and says that is what happened", async () => {
  // Without this the call outlives the deadline the run is waiting on, and the
  // run records "the browser did not answer" -- which names the browser for
  // something the warehouse did.
  answering(
    (_url, options) =>
      new Promise((_resolve, reject) => {
        options.signal.addEventListener("abort", () =>
          reject(abortError()),
        );
      }),
  );

  const said = await sendInPage({ url: "https://wms.example/api/x", timeout_ms: 30 });

  assert.equal(said.ok, false);
  assert.match(said.error.detail, /did not answer within \d+ms/, said.error.detail);
  assert.doesNotMatch(said.error.detail, /AbortError/, "it blamed itself in its own words");
});

test("the deadline is the command's where it carries one", async () => {
  // A call has no business outliving the deadline the run is waiting on, and
  // how long that is belongs to the run rather than to this file.
  let waited = 0;
  answering(
    (_url, options) =>
      new Promise((_resolve, reject) => {
        const began = Date.now();
        options.signal.addEventListener("abort", () => {
          waited = Date.now() - began;
          reject(abortError());
        });
      }),
  );

  await sendInPage({ url: "https://wms.example/api/x", timeout_ms: 40 });

  assert.ok(waited < 1000, `it waited ${waited}ms for a 40ms deadline`);
});
