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

test("X-Requested-With is taken off the page when the app sets one", async () => {
  // Read first and only then defaulted: what the application sends beats what
  // a spec says it ought to. Blue Yonder's ExtJS puts it on
  // `Ajax.defaultHeaders` beside the CSRF token.
  globalThis.window = {
    Ext: { Ajax: { defaultHeaders: { "X-Requested-With": "WMS-Client" } } },
  };
  let sentHeaders;
  globalThis.fetch = async (_url, init) => {
    sentHeaders = init.headers;
    return { status: 201, headers: new Map(), text: async () => "" };
  };

  const answer = await perform({
    command_id: "cmd-xrw",
    kind: "http.send",
    payload: {
      method: "POST",
      url: "https://wms.example/data/WM/wm/workAreas",
      headers: { "Content-Type": "application/json" },
      live_headers: ["X-Requested-With"],
    },
  });

  assert.equal(answer.ok, true);
  assert.equal(sentHeaders["X-Requested-With"], "WMS-Client");
});

test("a page that sets none still sends the marker every XHR library sends", async () => {
  // The difference between this header and the CSRF one: that is a credential
  // and has no default, so a page without it is `unreachable`. This one is a
  // fixed marker, struck out of the recording only because it sits in
  // SECRET_HEADERS beside the real credentials -- and a write that arrives
  // without it is refused before it is routed.
  globalThis.window = { Ext: {} };
  let sentHeaders;
  globalThis.fetch = async (_url, init) => {
    sentHeaders = init.headers;
    return { status: 201, headers: new Map(), text: async () => "" };
  };

  const answer = await perform({
    command_id: "cmd-xrw-2",
    kind: "http.send",
    payload: {
      method: "POST",
      url: "https://wms.example/data/WM/wm/workAreas",
      headers: {},
      live_headers: ["X-Requested-With"],
    },
  });

  assert.equal(answer.ok, true);
  assert.equal(sentHeaders["X-Requested-With"], "XMLHttpRequest");
});

/** Run the page functions against a list of frames instead of one window.
 *
 * `executeScript` with `allFrames: true` answers once per frame, top first,
 * and each answer is that frame's own realm. The default mock above has one
 * window and so cannot tell a page with frames from a page without.
 */
function framesAre(windows) {
  globalThis.chrome.scripting.executeScript = async ({ target, func, args }) => {
    const realms = target?.allFrames ? windows : windows.slice(0, 1);
    const answers = [];
    for (const realm of realms) {
      globalThis.window = realm;
      answers.push({ result: await func(...(args || [])) });
    }
    return answers;
  };
}

test("a live header is read from the frame that has it, not only the top one", async () => {
  // Measured on the real system 2026-09-16. Blue Yonder's portal is a shell
  // hosting the application in an iframe, and BOTH have an `Ext`: the shell's
  // `Ajax.defaultHeaders` carries only `Accept`, the iframe's carries the
  // token. Reading the top frame alone found an Ext, found no token, and
  // refused -- which failed every replay of every write on that system, with
  // the token one frame down.
  framesAre([
    { Ext: { Ajax: { defaultHeaders: { Accept: "application/json" } } } },
    { Ext: { Ajax: { defaultHeaders: { "CSRF-ENCRYPT-TOKEN": "from-the-iframe" } } } },
  ]);
  let sentHeaders;
  globalThis.fetch = async (_url, init) => {
    sentHeaders = init.headers;
    return { status: 201, headers: new Map(), text: async () => "" };
  };

  const answer = await perform({
    command_id: "cmd-frame-1",
    kind: "http.send",
    payload: {
      method: "POST",
      url: "https://wms.example/data/WM/wm/customerTypes",
      headers: {},
      live_headers: ["CSRF-ENCRYPT-TOKEN"],
    },
  });

  assert.equal(answer.ok, true);
  assert.equal(sentHeaders["CSRF-ENCRYPT-TOKEN"], "from-the-iframe");
});

test("no frame having it is still unreachable, and says every frame was asked", async () => {
  framesAre([{ Ext: { Ajax: { defaultHeaders: { Accept: "x" } } } }, { Ext: {} }]);

  const answer = await perform({
    command_id: "cmd-frame-2",
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
  assert.match(answer.error.detail, /any frame/);
});

test("the top frame still wins where it is the one that has it", async () => {
  // First non-null and not a merge: a header has one value, and Chrome
  // enumerates the top frame first, so a page that does put it on the shell
  // behaves exactly as it did before frames were looked at.
  framesAre([
    { Ext: { Ajax: { defaultHeaders: { "CSRF-ENCRYPT-TOKEN": "from-the-top" } } } },
    { Ext: { Ajax: { defaultHeaders: { "CSRF-ENCRYPT-TOKEN": "from-a-frame" } } } },
  ]);
  let sentHeaders;
  globalThis.fetch = async (_url, init) => {
    sentHeaders = init.headers;
    return { status: 201, headers: new Map(), text: async () => "" };
  };

  await perform({
    command_id: "cmd-frame-3",
    kind: "http.send",
    payload: {
      method: "POST",
      url: "https://wms.example/data/WM/wm/customerTypes",
      headers: {},
      live_headers: ["CSRF-ENCRYPT-TOKEN"],
    },
  });

  assert.equal(sentHeaders["CSRF-ENCRYPT-TOKEN"], "from-the-top");
});
