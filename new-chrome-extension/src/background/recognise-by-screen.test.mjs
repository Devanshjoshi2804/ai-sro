// "You've started job X -- shall I?" is asked on the job's own screen.
//
// HOME1, 2026-09-29: the backend keys a shape's steps by screen (origin plus
// Blue Yonder's fragment route) and this worker keyed the operator's tail by
// origin alone, so no tail ever matched a served shape and the prefix offer
// never fired. Driven through the real worker: the gestures the recorder
// captured (`fixtures/batch.json`), moved onto Blue Yonder, against the shape
// `shape_of` serves for them (`fixtures/served-shape.json`, held equal to the
// backend's output by `test_shapes.py`).
//
// Run with `node --test src/background/recognise-by-screen.test.mjs`.

import assert from "node:assert";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const held = new Map();
const calls = [];

globalThis.chrome = {
  storage: {
    local: {
      get: async (key) => (held.has(key) ? { [key]: held.get(key) } : {}),
      set: async (kv) => Object.entries(kv).forEach(([k, v]) => held.set(k, v)),
      remove: async () => {},
    },
  },
  runtime: { onMessage: { addListener: (fn) => (globalThis.__handle = fn) },
    onInstalled: { addListener: () => {} },
    onStartup: { addListener: () => {} }, getManifest: () => ({ version: "0.1.0" }), id: "ext" },
  tabs: { query: async () => [], onRemoved: { addListener: () => {} },
    onUpdated: { addListener: () => {} }, onActivated: { addListener: () => {} },
    sendMessage: async () => {}, get: async (id) => ({ id }) },
  webNavigation: {
    onCommitted: { addListener: () => {} },
    onReferenceFragmentUpdated: { addListener: () => {} },
    onCompleted: { addListener: () => {} },
    onCreatedNavigationTarget: { addListener: () => {} },
  },
  action: { setBadgeText: async () => {}, setBadgeBackgroundColor: async () => {}, setTitle: async () => {} },
  alarms: { create: () => {}, onAlarm: { addListener: () => {} } },
  scripting: { executeScript: async () => [{ result: undefined }], registerContentScripts: async () => {},
    getRegisteredContentScripts: async () => [], unregisterContentScripts: async () => {} },
  permissions: { contains: async () => true },
  windows: { update: async () => {} },
};

globalThis.indexedDB = {
  open: () => {
    const request = {};
    setTimeout(() => request.onerror?.({ target: { error: new Error("no store here") } }), 0);
    return request;
  },
};

const fixture = (name) => readFileSync(new URL(`../../fixtures/${name}`, import.meta.url), "utf8");

const BACKEND = "http://backend.test";
const BY = "https://bf56-kms-wms-web-np2.jdadelivers.com";
const CUSTOMER_TYPES = `${BY}/portal?siteId=SG#wm.config/wm.config.partners.customers.types////`;
const TRANSPORT = `${BY}/portal?siteId=SG#wm.config/wm.config.equipment.equipment.transportequipmenttype////`;
// Where `batch.json` was captured; `test_shapes.py` moves it the same way.
const CAPTURED_ON = "http://127.0.0.1:60989/";

const SERVED = JSON.parse(fixture("served-shape.json"));

/** The recorder's own gestures, as they would have been on `url`. */
const doneOn = (url) =>
  JSON.parse(fixture("batch.json").replaceAll(CAPTURED_ON, url))
    .events.filter((one) => one.kind === "gesture")
    .map((one) => one.gesture);

globalThis.fetch = async (url, options = {}) => {
  const path = String(url).slice(BACKEND.length);
  calls.push({ path, method: options.method || "GET" });
  if (path.startsWith("/v1/shapes")) {
    return { ok: true, status: 200, json: async () => ({ shapes: [SERVED] }) };
  }
  return { ok: true, status: 200, json: async () => [] };
};

await import("./service-worker.js");

held.set("sro.apiUrl", BACKEND);
held.set("sro.token", "tok");
held.set("sro.deviceId", "dev-1");
held.set("sro.deviceSecret", "sec");
held.set("sro.policy", { capture_enabled: true });
held.set("sro.watched", [
  { tabId: 7, host: new URL(BY).host, since: 0 },
  { tabId: 8, host: new URL(BY).host, since: 0 },
]);

const open = (tabId) =>
  (held.get("sro.nudges") || []).filter((one) => one.state === "open" && one.tabId === tabId);

/** One recorded gesture, as the content script sends it from the tab on `url`. */
function send(gesture, tabId, url) {
  return new Promise((resolve) =>
    globalThis.__handle(
      { kind: "gesture", frameUrl: url, gesture },
      { tab: { id: tabId, url } },
      resolve,
    ),
  );
}

async function settle() {
  for (let n = 0; n < 40; n++) await new Promise((r) => setTimeout(r, 5));
}

test("the first two steps of Create a Customer Type on its screen are offered", async () => {
  const [typed, chose] = doneOn(CUSTOMER_TYPES);
  await send(typed, 7, CUSTOMER_TYPES);
  await send(chose, 7, CUSTOMER_TYPES);
  await settle();

  const offers = open(7);
  assert.deepEqual(offers.map((one) => one.title), ["Create a Customer Type"], "no prefix offer on the job's own screen");
  assert.equal(offers[0].workflowId, SERVED.id);
  assert.equal(offers[0].k, 2);
  assert.deepEqual(offers[0].values, { clientCode: "ACME-4471" });
  assert.equal(
    calls.filter((call) => call.method === "POST" && call.path === "/v1/workflow-runs").length,
    0,
    "recognising a job started it -- only a press starts a run",
  );
});

test("the same gestures on the transport equipment screen are offered nothing", async () => {
  const [typed, chose] = doneOn(TRANSPORT);
  await send(typed, 8, TRANSPORT);
  await send(chose, 8, TRANSPORT);
  await settle();

  assert.deepEqual(open(8), [], "a job was offered on another screen of the portal");
});
