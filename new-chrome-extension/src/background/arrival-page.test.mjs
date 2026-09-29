// "You've done this here before" is said on the job's own screen and no other.
//
// QA 2026-09-29: `Create a Warehouse Equipment Type` was offered on Blue
// Yonder's Transport Equipment page. The WMS routes on the fragment, and both
// the served `starts_on` and `page()` dropped it, so every screen of the portal
// was every job's page. Driven through the real worker, off the shape as
// `/v1/shapes` serves it.
//
// Run with `node --test src/background/arrival-page.test.mjs`.

import assert from "node:assert";
import { test } from "node:test";

const held = new Map();
const listeners = {};

globalThis.chrome = {
  storage: {
    local: {
      get: async (key) => (held.has(key) ? { [key]: held.get(key) } : {}),
      set: async (kv) => Object.entries(kv).forEach(([k, v]) => held.set(k, v)),
      remove: async () => {},
    },
  },
  runtime: { onMessage: { addListener: () => {} },
    onInstalled: { addListener: () => {} },
    onStartup: { addListener: () => {} }, getManifest: () => ({ version: "0.1.0" }), id: "ext" },
  tabs: { query: async () => [], onRemoved: { addListener: () => {} },
    onUpdated: { addListener: () => {} }, onActivated: { addListener: () => {} },
    sendMessage: async () => {}, get: async () => ({ id: 7, url: TRANSPORT }) },
  webNavigation: {
    onCommitted: { addListener: (fn) => (listeners.committed = fn) },
    onReferenceFragmentUpdated: { addListener: (fn) => (listeners.fragment = fn) },
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

const BACKEND = "http://backend.test";
const BY = "https://bf56-kms-wms-web-np2.jdadelivers.com";
const TRANSPORT = `${BY}/portal?siteId=SG#wm.config/wm.config.equipment.equipment.transportequipmenttype////`;
const WAREHOUSE = `${BY}/portal?siteId=SG#wm.config/wm.config.equipment.equipment.warehouseequipmenttype////`;

// As `shape.py` serves it: the first step's screen, fragment route and all.
const SHAPE = {
  id: "wfl_wet",
  title: "Create a Warehouse Equipment Type",
  starts_on: `${BY}/portal#wm.config/wm.config.equipment.equipment.warehouseequipmenttype`,
  hosts: [BY],
  shape: [
    [`${BY}/portal#wm.config/wm.config.equipment.equipment.warehouseequipmenttype`, "addButton", "click"],
    [`${BY}/portal#wm.config/wm.config.equipment.equipment.warehouseequipmenttype`, "name|Code", "type"],
    [`${BY}/portal#wm.config/wm.config.equipment.equipment.warehouseequipmenttype`, "saveButton", "click"],
  ],
  parameters: [{ name: "Code", at: 1 }],
  writes: [],
};

globalThis.fetch = async (url) => {
  const path = String(url).slice(BACKEND.length);
  if (path.startsWith("/v1/shapes")) {
    return { ok: true, status: 200, json: async () => ({ shapes: [SHAPE] }) };
  }
  return { ok: true, status: 200, json: async () => [] };
};

await import("./service-worker.js");

held.set("sro.apiUrl", BACKEND);
held.set("sro.token", "tok");
held.set("sro.deviceId", "dev-1");
held.set("sro.deviceSecret", "sec");
held.set("sro.watched", [{ tabId: 7, host: new URL(BY).host, since: 0 }]);

const open = () => (held.get("sro.nudges") || []).filter((one) => one.state === "open");

async function settle() {
  for (let n = 0; n < 40; n++) await new Promise((r) => setTimeout(r, 5));
}

test("another screen of the same portal is not this job's page", async () => {
  await listeners.committed({ frameId: 0, tabId: 7, url: TRANSPORT, timeStamp: 1000 });
  await settle();

  assert.deepEqual(open().map((one) => one.title), [], "the warehouse job was offered on the transport page");
});

test("moving to the job's own screen by its fragment offers it there", async () => {
  await listeners.fragment({ frameId: 0, tabId: 7, url: WAREHOUSE, timeStamp: 2000 });
  await settle();

  assert.deepEqual(open().map((one) => one.title), ["Create a Warehouse Equipment Type"]);
});

test("and leaving that screen by its fragment ends the offer", async () => {
  await listeners.fragment({ frameId: 0, tabId: 7, url: TRANSPORT, timeStamp: 3000 });
  await settle();

  assert.deepEqual(open(), [], "the offer outlived the screen it was about");
});
