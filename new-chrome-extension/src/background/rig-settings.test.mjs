// Self-check for service-worker.js's "rig" message handler: a blank token
// field means "leave the saved token alone", not "clear it" -- status()
// never returns the secret, so the field renders empty every time the
// options page draws itself, and blank is that field's resting state, not
// an instruction. See options.js's render() and the "rig" case's own
// comment for the reasoning.
//
// `case "rig":` lives inside service-worker.js's unexported message
// dispatcher, and importing that file at all means standing up its whole
// module-scope wiring: chrome.runtime, chrome.alarms, chrome.webNavigation,
// chrome.tabs, chrome.sidePanel, chrome.runtime.getManifest() (channel.js
// reads it at import), and status()'s own queue.count() needs indexedDB.
// None of it runs anything real here -- every hook below is a no-op, or the
// existing fake-indexeddb.mjs -- it is just the scaffolding required to
// reach three lines of logic without changing how service-worker.js is
// written.
//
// Run with `node src/background/rig-settings.test.mjs`.

import assert from "node:assert/strict";
import test from "node:test";

import { fakeIndexedDB } from "./test-support/fake-indexeddb.mjs";

globalThis.indexedDB = fakeIndexedDB();

// The same minimal chrome.storage.local fake the other background tests use.
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
  runtime: {
    onInstalled: { addListener: () => {} },
    onStartup: { addListener: () => {} },
    onMessage: {
      addListener: (fn) => {
        globalThis.__handle = fn;
      },
    },
    getManifest: () => ({ version: "0.0.0-test" }),
  },
  alarms: { create: () => {}, onAlarm: { addListener: () => {} } },
  webNavigation: {
    onCommitted: { addListener: () => {} },
    onCompleted: { addListener: () => {} },
    onCreatedNavigationTarget: { addListener: () => {} },
  },
  tabs: { onRemoved: { addListener: () => {} } },
  action: {
    setBadgeText: async () => {},
    setBadgeBackgroundColor: async () => {},
    setTitle: async () => {},
  },
  sidePanel: { open: async () => {}, setPanelBehavior: async () => {} },
  // Sign-in unregisters and re-registers the content scripts; none here.
  scripting: {
    getRegisteredContentScripts: async () => [],
    unregisterContentScripts: async () => {},
    registerContentScripts: async () => {},
  },
  permissions: { getAll: async () => ({ origins: [] }), contains: async () => false },
};

await import("./service-worker.js");

function sendRig(message) {
  return new Promise((resolve) => {
    globalThis.__handle({ kind: "rig", ...message }, {}, resolve);
  });
}

test("submitting a URL and a token saves both", async () => {
  held.clear();

  await sendRig({ rigUrl: "http://localhost:8100", rigToken: "tok-1" });

  assert.equal(held.get("sro.rigUrl"), "http://localhost:8100");
  assert.equal(held.get("sro.rigToken"), "tok-1");
});

test("a changed URL with a blank token leaves the saved token intact", async () => {
  held.clear();
  held.set("sro.rigUrl", "http://localhost:8100");
  held.set("sro.rigToken", "tok-1");

  await sendRig({ rigUrl: "http://localhost:9999", rigToken: "" });

  assert.equal(held.get("sro.rigUrl"), "http://localhost:9999", "the URL change was not saved");
  assert.equal(held.get("sro.rigToken"), "tok-1", "a blank token field wiped the saved token");
});

test("a blank URL clears both the URL and the token", async () => {
  held.clear();
  held.set("sro.rigUrl", "http://localhost:8100");
  held.set("sro.rigToken", "tok-1");

  await sendRig({ rigUrl: "", rigToken: "" });

  assert.equal(held.get("sro.rigUrl"), "");
  assert.equal(held.get("sro.rigToken"), "");
});

test("a rig URL that is not http(s) is refused, and says so where it was typed", async () => {
  // mirrorTo would drop this silently -- correctly, since the mirror must
  // never reach upload.js's decision -- and the operator would never learn the
  // field was wrong. A rejected configuration is not a network failure.
  held.clear();
  held.set("sro.rigUrl", "http://localhost:8100");
  held.set("sro.rigToken", "tok-1");

  const answer = await sendRig({ rigUrl: "javascript:fetch('//evil')", rigToken: "" });

  assert.match(answer.error ?? "", /http/, "the options page was told nothing");
  assert.equal(held.get("sro.rigUrl"), "http://localhost:8100", "the bad URL was saved anyway");
});

test("a rig that mints a device token is given the tenant's, and the browser keeps its own", async () => {
  held.clear();
  held.set("sro.deviceId", "dev-9");
  const asked = [];
  const fetchWas = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    asked.push({ url, init });
    return { ok: true, status: 201, json: async () => ({ device_id: "dev-9", token: "dev_minted" }) };
  };
  try {
    const answer = await sendRig({ rigUrl: "http://localhost:8100", rigToken: "tenant-secret" });
    assert.equal(answer.registered, true);
  } finally {
    globalThis.fetch = fetchWas;
  }
  assert.equal(asked.length, 1);
  assert.equal(asked[0].url, "http://localhost:8100/v1/devices/register");
  assert.equal(asked[0].init.headers.Authorization, "Bearer tenant-secret");
  assert.deepEqual(JSON.parse(asked[0].init.body), { device_id: "dev-9" });
  assert.equal(held.get("sro.rigToken"), "dev_minted", "the tenant's secret is not kept");
});

test("an older rig that cannot register leaves the typed token in place", async () => {
  held.clear();
  held.set("sro.deviceId", "dev-9");
  const fetchWas = globalThis.fetch;
  globalThis.fetch = async () => ({ ok: false, status: 404, json: async () => ({ detail: "Not Found" }) });
  try {
    const answer = await sendRig({ rigUrl: "http://localhost:8100", rigToken: "tenant-secret" });
    assert.equal(answer.registered, false);
  } finally {
    globalThis.fetch = fetchWas;
  }
  assert.equal(held.get("sro.rigToken"), "tenant-secret");
});

test("a browser with no device id yet keeps the typed token and asks nothing", async () => {
  held.clear();
  let asked = 0;
  const fetchWas = globalThis.fetch;
  globalThis.fetch = async () => {
    asked += 1;
    return { ok: true, status: 201, json: async () => ({ token: "dev_x" }) };
  };
  try {
    await sendRig({ rigUrl: "http://localhost:8100", rigToken: "tenant-secret" });
  } finally {
    globalThis.fetch = fetchWas;
  }
  assert.equal(asked, 0);
  assert.equal(held.get("sro.rigToken"), "tenant-secret");
});

test("a browser that already holds its own token does not ask for another on save", async () => {
  held.clear();
  held.set("sro.deviceId", "dev-9");
  held.set("sro.rigUrl", "http://localhost:8100");
  let asked = 0;
  const fetchWas = globalThis.fetch;
  globalThis.fetch = async () => {
    asked += 1;
    return { ok: true, status: 201, json: async () => ({ token: "dev_again" }) };
  };
  try {
    // A blank token field leaves the held `dev_` token alone; nothing to mint.
    await sendRig({ rigUrl: "http://localhost:8100", rigToken: "" });
  } finally {
    globalThis.fetch = fetchWas;
  }
  assert.equal(asked, 0);
});

test("signing in after the rig was pasted mints the token the save could not", async () => {
  held.clear();
  held.set("sro.rigUrl", "http://localhost:8100");
  held.set("sro.rigToken", "tenant-secret");
  const asked = [];
  let answer;
  let minted;
  const fetchWas = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    asked.push({ url: String(url), init });
    if (String(url).endsWith("/v1/devices/register")) {
      return { ok: true, status: 201, json: async () => ({ device_id: "dev-9", token: "dev_minted" }) };
    }
    return {
      ok: true,
      status: 200,
      json: async () => ({ device_id: "dev-9", device_secret: "s", policy: null }),
    };
  };
  try {
    answer = await new Promise((resolve) => {
      globalThis.__handle(
        { kind: "sign-in", apiUrl: "http://backend.test", token: "backend-tok", label: "x" },
        {},
        resolve,
      );
    });
    minted = held.get("sro.rigToken");
    // Sign out again: sign-in dialled both sockets, and an open socket or its
    // retry timer would keep this process alive after the last test. Sign-out
    // forgets every credential, the rig's too, so the token is read first.
    await new Promise((resolve) => globalThis.__handle({ kind: "sign-out" }, {}, resolve));
  } finally {
    globalThis.fetch = fetchWas;
  }
  const rig = asked.find((a) => a.url.endsWith("/v1/devices/register"));
  assert.ok(rig, `sign-in never asked the rig: ${JSON.stringify({ asked: asked.map((a) => a.url), answer })}`);
  assert.equal(rig.init.headers.Authorization, "Bearer tenant-secret");
  assert.equal(minted, "dev_minted");
});
