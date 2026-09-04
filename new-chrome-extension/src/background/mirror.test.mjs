import assert from "node:assert/strict";
import test from "node:test";

import { isMirrorable, mirrorSafely, mirrorTo } from "./mirror.js";

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

test("a rig that accepts the connection and never answers does not hang the caller", async () => {
  // The down case fails fast. This one holds the promise open forever, and
  // upload.js does not remove queued rows until the caller returns.
  const fetcher = (url, options) =>
    new Promise((_, reject) => {
      options.signal?.addEventListener("abort", () => reject(new Error("aborted")));
    });

  await mirrorTo("http://localhost:8100", "t", "/v1/observations", {
    body: {},
    fetcher,
    timeoutMs: 10,
  });
});

test("a settings read that throws does not fail the upload", async () => {
  // chrome.storage rejecting mid-update used to surface as a failed upload of
  // a batch the backend had already stored.
  const angry = async () => {
    throw new Error("extension context invalidated");
  };

  await mirrorSafely(angry, angry, "/v1/observations", { body: {}, fetcher: async () => ({ ok: true }) });
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

// --- Open item 1: what travels here is live customer traffic ----------------

test("a mirror URL that is not http(s) is refused without a fetch", async () => {
  // The field is free text with no default host, mirrorTo is silent about
  // failure by design, and what goes down this path is a copy of every batch
  // of live customer WMS traffic. A value that is not an absolute http(s) URL
  // must not produce a request at all.
  for (const base of ["javascript:fetch('//evil')", "file:///etc/passwd", "/v1", "not a url", ""]) {
    let called = false;
    const fetcher = async () => {
      called = true;
      return { ok: true };
    };

    await mirrorTo(base, "t", "/v1/observations", { body: {}, fetcher });

    assert.equal(called, false, `${base} was posted to`);
    assert.equal(isMirrorable(base), false, `${base} was judged mirrorable`);
  }
});

test("an ordinary https rig still mirrors", async () => {
  const seen = [];
  const fetcher = async (url) => {
    seen.push(url);
    return { ok: true };
  };

  await mirrorTo("https://rig.example:8100", "t", "/v1/observations", { body: {}, fetcher });

  assert.deepEqual(seen, ["https://rig.example:8100/v1/observations"]);
  assert.equal(isMirrorable("http://localhost:8100"), true);
});
