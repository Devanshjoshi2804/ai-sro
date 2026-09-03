import assert from "node:assert/strict";
import test from "node:test";

import { mirrorTo } from "./mirror.js";

test("a mirror posts the same body to the second base", async () => {
  const seen = [];
  const fetcher = async (url, options) => {
    seen.push({ url, options });
    return { ok: true, status: 202 };
  };

  await mirrorTo("http://localhost:8100", "rig-token", "/v1/observations", {
    body: { batch_id: "bat_1" },
    fetcher,
  });

  assert.equal(seen.length, 1);
  assert.equal(seen[0].url, "http://localhost:8100/v1/observations");
  assert.equal(seen[0].options.headers.Authorization, "Bearer rig-token");
  assert.equal(JSON.parse(seen[0].options.body).batch_id, "bat_1");
});

test("a mirror to a rig that is down does not throw", async () => {
  const fetcher = async () => {
    throw new Error("ECONNREFUSED");
  };

  await mirrorTo("http://localhost:8100", "t", "/v1/observations", {
    body: {},
    fetcher,
  });
});

test("a mirror that is refused does not throw", async () => {
  const fetcher = async () => ({ ok: false, status: 401 });

  await mirrorTo("http://localhost:8100", "t", "/v1/observations", {
    body: {},
    fetcher,
  });
});

test("no rig configured means no request at all", async () => {
  let called = false;
  const fetcher = async () => {
    called = true;
    return { ok: true, status: 202 };
  };

  await mirrorTo("", "t", "/v1/observations", { body: {}, fetcher });

  assert.equal(called, false);
});
