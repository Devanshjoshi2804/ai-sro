// Which tabs are inside an OAuth/OIDC sign-in, across a worker that is evicted.
//
// Spec 5.6: every page between the authorize request and the return to the
// `redirect_uri`'s origin is a sign-in page, and a sign-in page is captured
// structure-only. A flow lasts as long as somebody takes to type a code, which
// is longer than this worker lives -- so it is kept in storage, not in a Map.
//
// Run with `node src/background/signing-in.test.mjs`.

import assert from "node:assert/strict";
import { test } from "node:test";

let stored = {};
globalThis.chrome = {
  storage: {
    local: {
      get: async (key) => (key in stored ? { [key]: stored[key] } : {}),
      set: async (entries) => Object.assign(stored, entries),
      remove: async () => {},
    },
  },
};

const { navigated, inSignInFlow, forgetSignIn } = await import("./signing-in.js");

const AUTHORIZE =
  "https://login.idp.example/authorize?client_id=app&response_type=code" +
  "&redirect_uri=https%3A%2F%2Fwms.example%2Fcallback&state=s1";

test("a tab is inside from the authorize request to the return with a code", async () => {
  stored = {};
  await navigated(7, "https://wms.example/orders");
  assert.equal(await inSignInFlow(7), false);
  await navigated(7, AUTHORIZE);
  assert.equal(await inSignInFlow(7), true);
  await navigated(7, "https://login.idp.example/otc");
  assert.equal(await inSignInFlow(7), true);
  assert.equal(await inSignInFlow(8), false, "another tab is not in this one's flow");
  await navigated(7, "https://wms.example/callback?code=c&state=s1");
  assert.equal(await inSignInFlow(7), false);
});

test("the flow survives the worker, because it is in storage", async () => {
  stored = {};
  await navigated(3, AUTHORIZE);
  const { inSignInFlow: again } = await import(`./signing-in.js?evicted=${Date.now()}`);
  assert.equal(await again(3), true);
});

test("asking waits for a navigation that was already under way", async () => {
  stored = {};
  void navigated(4, AUTHORIZE);
  assert.equal(await inSignInFlow(4), true);
});

test("a closed tab takes its flow with it", async () => {
  stored = {};
  await navigated(5, AUTHORIZE);
  await forgetSignIn(5);
  assert.equal(await inSignInFlow(5), false);
});
