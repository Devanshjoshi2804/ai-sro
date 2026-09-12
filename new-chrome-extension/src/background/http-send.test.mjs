// `httpSend`'s live-header fetch: a verified write names a header in
// `payload.live_headers` rather than carrying it on the wire, and this
// extension is the one that has to go get it off the page before sending.
//
// Run with `node src/background/http-send.test.mjs`.

import assert from "node:assert";
import { test } from "node:test";

const TAB = { id: 7, url: "https://wms.example/app" };

globalThis.chrome = {
  tabs: { query: async () => [TAB] },
  scripting: {
    executeScript: async ({ func, args }) => [{ result: await func(...(args || [])) }],
  },
};

const { perform } = await import("./commands.js");

test("a verified call has its named header fetched live and merged in", async () => {
  globalThis.window = { Ext: { Ajax: { defaultHeaders: { "CSRF-ENCRYPT-TOKEN": "live-value" } } } };
  let sentHeaders;
  globalThis.fetch = async (_url, init) => {
    sentHeaders = init.headers;
    return { status: 200, headers: new Map(), text: async () => "" };
  };

  const answer = await perform({
    command_id: "cmd-1",
    kind: "http.send",
    payload: {
      method: "POST",
      url: "https://wms.example/data/WM/wm/customerTypes",
      headers: { "Content-Type": "application/json" },
      live_headers: ["CSRF-ENCRYPT-TOKEN"],
    },
  });

  assert.equal(answer.ok, true);
  assert.equal(sentHeaders["CSRF-ENCRYPT-TOKEN"], "live-value");
  assert.equal(sentHeaders["Content-Type"], "application/json");
});

test("a live header with no source on the page is unreachable, not silently dropped", async () => {
  globalThis.window = { Ext: {} };

  const answer = await perform({
    command_id: "cmd-2",
    kind: "http.send",
    payload: {
      method: "POST",
      url: "https://wms.example/data/WM/wm/customerTypes",
      headers: {},
      live_headers: ["CSRF-ENCRYPT-TOKEN"],
    },
  });

  assert.equal(answer.ok, false);
  assert.equal(answer.error.kind, "unreachable");
});

test("a header name this extension has no menu entry for is unreachable", async () => {
  const answer = await perform({
    command_id: "cmd-3",
    kind: "http.send",
    payload: {
      method: "POST",
      url: "https://wms.example/data/WM/wm/customerTypes",
      headers: {},
      live_headers: ["SOME-OTHER-TOKEN"],
    },
  });

  assert.equal(answer.ok, false);
  assert.equal(answer.error.kind, "unreachable");
});

test("names that only exist on Object.prototype are unreachable, not a thrown lookup", async () => {
  // A plain `LIVE_HEADER_SOURCES[name]` lookup answers truthily for
  // "constructor" and "__proto__" -- they are not in the menu, they are on
  // every object there is -- and the value it finds is not a header source
  // function, so the code past the `if (!source)` guard throws trying to
  // call it. The menu has to be asked with `Object.hasOwn`, not indexed.
  for (const name of ["constructor", "__proto__"]) {
    const answer = await perform({
      command_id: `cmd-proto-${name}`,
      kind: "http.send",
      payload: {
        method: "POST",
        url: "https://wms.example/data/WM/wm/customerTypes",
        headers: {},
        live_headers: [name],
      },
    });

    assert.equal(answer.ok, false, `${name} should be refused, not thrown on`);
    assert.equal(answer.error.kind, "unreachable");
  }
});

test("no live_headers at all sends exactly the headers it was given", async () => {
  let sentHeaders;
  globalThis.fetch = async (_url, init) => {
    sentHeaders = init.headers;
    return { status: 200, headers: new Map(), text: async () => "" };
  };

  const answer = await perform({
    command_id: "cmd-4",
    kind: "http.send",
    payload: {
      method: "GET",
      url: "https://wms.example/data/WM/wm/customerTypes",
      headers: { "Content-Type": "application/json" },
    },
  });

  assert.equal(answer.ok, true);
  assert.deepEqual(sentHeaders, { "Content-Type": "application/json" });
});
