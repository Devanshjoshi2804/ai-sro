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
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const pageCode = readFileSync(
  fileURLToPath(new URL("../page/page-code.js", import.meta.url)),
  "utf8",
);
const { send: sendInPage } = (() => {
  const realm = {};
  new Function("globalThis", pageCode)(realm);
  return realm.sroPage;
})();

/** What a browser rejects an aborted fetch with, made without naming
 * `DOMException` -- which node has and eslint's browser globals do not. */
const abortError = () =>
  Object.assign(new Error("aborted"), { name: "AbortError" });

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

/** A system that fails the call and, asked again without following redirects,
 * answers with one. `redirect: "manual"` is how the second ask is told apart
 * from the first. */
const failingThenRedirecting = () => {
  globalThis.fetch = async (_url, options = {}) => {
    if (options.redirect === "manual")
      return { type: "opaqueredirect", status: 0 };
    throw new TypeError("Failed to fetch");
  };
  online(true);
};

test("a call that worked carries what the system said", async () => {
  answering(async () => ({
    status: 201,
    headers: { forEach: (fn) => fn("application/json", "content-type") },
    text: async () => '{"id":1}',
  }));

  const said = await sendInPage({
    url: "https://wms.example/api/x",
    method: "POST",
  });

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
  assert.match(
    said.error.detail,
    /Failed to fetch after \d+ms/,
    said.error.detail,
  );
});

test("a session that has gone is not reported as an unreachable host", async () => {
  // The fifth fault, and the commonest in a warehouse. It is not in the list
  // above because it is not a network fault at all: the session expired, the
  // endpoint answered 302 to an identity provider on another origin, and
  // `redirect: "follow"` walked the fetch across a boundary it may not cross.
  // Same `TypeError: Failed to fetch`.
  //
  // Measured on the deployment 2026-09-21. `GET /data/WM/wm/customerTypes`
  // answered 200 with fifty records at 18:30 and `Failed to fetch after
  // 341ms` at 20:10, with the operator's own machine reaching that exact
  // address in 12ms and being answered 302. The panel said "unreachable",
  // which sent everybody looking at the network.
  failingThenRedirecting();

  const said = await sendInPage({
    url: "https://wms.example/data/WM/wm/customerTypes",
  });

  assert.equal(said.ok, false);
  assert.equal(said.error.kind, "signed_out");
  assert.match(said.error.detail, /session has gone/, said.error.detail);
});

test("and a host that really is unreachable still says so", async () => {
  // The probe answers nothing useful, so the original reading stands.
  globalThis.fetch = async (_url, options = {}) => {
    if (options.redirect === "manual") throw new TypeError("Failed to fetch");
    throw new TypeError("Failed to fetch");
  };
  online(true);

  const said = await sendInPage({ url: "https://wms.example/api/x" });

  assert.equal(said.error.kind, "unreachable");
});

test("the probe is never asked on a call that worked", async () => {
  // It costs a request, and it only ever runs on a path that is already
  // reporting a failure.
  const asked = [];
  globalThis.fetch = async (_url, options = {}) => {
    asked.push(options.redirect || "follow");
    return {
      status: 200,
      headers: { forEach: () => {} },
      text: async () => "{}",
    };
  };
  online(true);

  await sendInPage({ url: "https://wms.example/api/x" });

  assert.deepEqual(asked, ["follow"]);
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
        options.signal.addEventListener("abort", () => reject(abortError()));
      }),
  );

  const said = await sendInPage({
    url: "https://wms.example/api/x",
    timeout_ms: 30,
  });

  assert.equal(said.ok, false);
  assert.match(
    said.error.detail,
    /did not answer within \d+ms/,
    said.error.detail,
  );
  assert.doesNotMatch(
    said.error.detail,
    /AbortError/,
    "it blamed itself in its own words",
  );
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
