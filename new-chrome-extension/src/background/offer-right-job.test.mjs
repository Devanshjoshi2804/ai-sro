// The offer names the job the operator is doing, not a job that shares the page.
//
// QA 2026-09-29 ~14:14 IST, tenant greyorange: on Blue Yonder's Customer Types
// screen the operator pressed Add and typed YHEU into Customer Type, and the
// panel offered "Delete a Customer Type" and never changed its mind. Driven
// through the real worker with what really happened: the gestures as the
// recorder uploaded them (`fixtures/batch-qa-customer-type-yheu.json`) against the
// shapes `/v1/shapes` served that tenant (`test-support/served-shapes-greyorange.json`).
//
// Run with `node --test src/background/offer-right-job.test.mjs`.

import assert from "node:assert";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { page } from "../panel/nudge.js";

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
  runtime: { onMessage: { addListener: (fn) => (listeners.message = fn) },
    onInstalled: { addListener: () => {} },
    onStartup: { addListener: () => {} }, getManifest: () => ({ version: "0.1.0" }), id: "ext" },
  tabs: { query: async () => [], onRemoved: { addListener: () => {} },
    onUpdated: { addListener: () => {} }, onActivated: { addListener: () => {} },
    sendMessage: async () => {}, get: async (id) => ({ id }) },
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

const read = (url) => JSON.parse(readFileSync(new URL(url, import.meta.url), "utf8"));
const SERVED = read("./test-support/served-shapes-greyorange.json");
const DONE = read("../../fixtures/batch-qa-customer-type-yheu.json").events;

const BACKEND = "http://backend.test";
const BY = "https://bf56-kms-wms-web-np2.jdadelivers.com";
const WAREHOUSE = `${BY}/portal?siteId=SG#wm.config/wm.config.warehouse.warehouse////`;
const TRANSPORT = `${BY}/portal?siteId=SG#wm.config/wm.config.equipment.equipment.transportequipmenttype////`;
const CUSTOMER_TYPES = `${BY}/portal?siteId=SG#wm.config/wm.config.partners.customers.types////`;

globalThis.fetch = async (url) => {
  const path = String(url).slice(BACKEND.length);
  if (path.startsWith("/v1/shapes")) {
    return { ok: true, status: 200, json: async () => ({ shapes: SERVED }) };
  }
  return { ok: true, status: 200, json: async () => [] };
};

await import("./service-worker.js");

held.set("sro.apiUrl", BACKEND);
held.set("sro.token", "tok");
held.set("sro.deviceId", "dev-1");
held.set("sro.deviceSecret", "sec");
held.set("sro.policy", { capture_enabled: true });
held.set("sro.watched", [7, 9].map((tabId) => ({ tabId, host: new URL(BY).host, since: 0 })));

const open = () => (held.get("sro.nudges") || []).filter((one) => one.state === "open");

async function settle() {
  for (let n = 0; n < 40; n++) await new Promise((r) => setTimeout(r, 5));
}

/** One uploaded gesture, sent the way the content script sent it. */
function send({ gesture, page_url: tabUrl }) {
  return new Promise((resolve) =>
    listeners.message({ kind: "gesture", frameUrl: tabUrl, gesture }, { tab: { id: 7, url: tabUrl } }, resolve),
  );
}

test("arriving on a screen one served job starts on offers it", async () => {
  await listeners.committed({ frameId: 0, tabId: 9, url: TRANSPORT, timeStamp: 500 });
  await settle();
  assert.deepEqual(open().map((one) => one.title), ["Create a Transport Equipment Type"]);

  await listeners.fragment({ frameId: 0, tabId: 9, url: WAREHOUSE, timeStamp: 600 });
  await settle();
  assert.deepEqual(open(), [], "the offer outlived the screen it was about");
});

test("arriving on a screen two served jobs start on offers neither", async () => {
  // Create and Delete a Customer Type both begin on Customer Types, as served.
  await listeners.committed({ frameId: 0, tabId: 7, url: CUSTOMER_TYPES, timeStamp: 1000 });
  await settle();

  assert.deepEqual(open().map((one) => one.title), [], "the address picked one of two jobs");
});

test("Add and YHEU typed into Customer Type are Create a Customer Type, with YHEU", async () => {
  for (const one of DONE) await send(one);
  await settle();

  const offers = open();
  assert.deepEqual(offers.map((one) => one.title), ["Create a Customer Type"], "the gestures never named the job");
  assert.deepEqual(offers[0].values, { "Customer Type": "YHEU" });
  // Made on this screen, so walking off it ends it and "Always on this page"
  // is about this page -- not the screen the recording's first click was on.
  assert.equal(offers[0].startsOn, page(CUSTOMER_TYPES));
});
