// Part-way through a job, the panel offers THAT job and carries what was typed.
//
// QA 2026-09-29 ~14:49 IST, tenant greyorange: the operator added a customer
// type, typed YDGY, walked off to Warehouse, came back, pressed Add again and
// typed YYDS -- and the panel went on offering "Delete a Customer Type". The
// first attempt stayed in the tail and every later gesture was read against
// where it had got to, so the second was never seen at all. Driven through the
// real worker with what really happened (`fixtures/batch-qa-customer-type-yyds.json`,
// navigations where the tab's screen changed) against the shapes `/v1/shapes`
// serves that tenant (`test-support/served-shapes-greyorange.json`).
//
// Run with `node --test src/background/offer-mid-job.test.mjs`.

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
const DONE = read("../../fixtures/batch-qa-customer-type-yyds.json").events;
const CREATE = SERVED.find((one) => one.title === "Create a Customer Type");
const DELETE = SERVED.find((one) => one.title === "Delete a Customer Type");

const BACKEND = "http://backend.test";
const BY = "https://bf56-kms-wms-web-np2.jdadelivers.com";
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
const host = new URL(BY).host;
held.set("sro.watched", [7, 8, 9].map((tabId) => ({ tabId, host, since: 0 })));

const open = (tabId) =>
  (held.get("sro.nudges") || []).filter((one) => one.state === "open" && one.tabId === tabId);

async function settle() {
  for (let n = 0; n < 40; n++) await new Promise((r) => setTimeout(r, 5));
}

/** What the operator did on `tabId`, in order: each gesture as the content
 * script sent it, and a screen change wherever the tab's screen changed. */
async function replay(events, tabId) {
  let screen = null;
  for (const { gesture, page_url: url } of events) {
    if (page(url) !== screen) {
      const at = Math.round(gesture.at * 1000) - 1;
      await (screen === null ? listeners.committed : listeners.fragment)({ frameId: 0, tabId, url, timeStamp: at });
      await settle();
      screen = page(url);
    }
    await new Promise((resolve) =>
      listeners.message({ kind: "gesture", frameUrl: url, gesture }, { tab: { id: tabId, url } }, resolve),
    );
  }
  await settle();
}

test("the second attempt at a job is recognised, with what was typed this time", async () => {
  await replay(DONE, 7);

  const offers = open(7);
  assert.deepEqual(offers.map((one) => one.title), ["Create a Customer Type"], "the second attempt was never read");
  assert.deepEqual(offers[0].values, { "Customer Type": "YYDS" }, "the abandoned attempt's value was carried");
  assert.ok(offers[0].missing.includes("Customer Type Description"), "what is still to be given is not asked for");
});

test("an operator who starts part-way through, form open and a value typed, is offered that job", async () => {
  // The extension came up on the Add form: all it has is the typing and the
  // click into the next field.
  await replay(DONE.slice(-2), 8);

  const offers = open(8);
  assert.deepEqual(offers.map((one) => one.title), ["Create a Customer Type"]);
  assert.deepEqual(offers[0].values, { "Customer Type": "YYDS" });
});

test("what the operator is doing outranks what the address offered", async () => {
  for (const tabId of [7, 8]) {
    await listeners.committed({ frameId: 0, tabId, url: `${BY}/portal?siteId=SG#wm.config/wm.config.warehouse.warehouse////`, timeStamp: 9000 + tabId });
  }
  await settle();
  // A rule the operator made: on Customer Types, offer Delete.
  held.set("sro.arrivals", [{ id: "trg-1", page: page(CUSTOMER_TYPES), workflowId: DELETE.id, values: {} }]);

  const secondAttempt = DONE.slice(-4); // on Customer Types: Add, the field, YYDS, the next field
  await replay(secondAttempt.slice(0, 1), 9);
  assert.deepEqual(open(9).map((one) => one.title), ["Delete a Customer Type"], "the rule offered nothing");
  const arrival = open(9)[0];

  await replay(secondAttempt.slice(1), 9);

  assert.deepEqual(open(9).map((one) => [one.title, one.workflowId]), [["Create a Customer Type", CREATE.id]]);
  const ended = (held.get("sro.nudges") || []).find((one) => one.id === arrival.id);
  assert.equal(ended?.state, "expired", "the Delete offer was renamed into Create rather than ended");
  assert.equal(ended?.workflowId, DELETE.id);
});
