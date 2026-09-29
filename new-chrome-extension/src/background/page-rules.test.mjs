// "Do this here": the rule an operator makes by standing somewhere, and this
// browser OFFERING it when they land there again -- with the values the rule
// holds. Never firing it: a job that started because somebody opened a page is
// what QA saw on 2026-09-28. The operator's press is the start.
//
// Run with `node --test src/background/page-rules.test.mjs`.

import assert from "node:assert";
import { test } from "node:test";

const held = new Map();
const calls = [];
let fires = 0;

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
    sendMessage: async () => {}, get: async () => ({ id: 7, url: PAGE_URL }) },
  webNavigation: {
    onCommitted: { addListener: (fn) => (globalThis.__navigated = fn) },
    onReferenceFragmentUpdated: { addListener: () => {} },
    onCompleted: { addListener: () => {} },
    onCreatedNavigationTarget: { addListener: () => {} },
  },
  action: { setBadgeText: async () => {}, setBadgeBackgroundColor: async () => {}, setTitle: async () => {} },
  alarms: { create: () => {}, onAlarm: { addListener: (fn) => (globalThis.__beat = fn) } },
  scripting: { executeScript: async () => [{ result: undefined }], registerContentScripts: async () => {},
    getRegisteredContentScripts: async () => [], unregisterContentScripts: async () => {} },
  permissions: { contains: async () => true },
  windows: { update: async () => {} },
};

// The heartbeat flushes the queue on its way past, and the queue is IndexedDB.
// A store that refuses to open is a browser with nothing queued as far as
// `flushQueue` is concerned -- which is exactly this test's browser.
globalThis.indexedDB = {
  open: () => {
    const request = {};
    setTimeout(() => request.onerror?.({ target: { error: new Error("no store here") } }), 0);
    return request;
  },
};

const BACKEND = "http://backend.test";
const WMS = "bf56-kms-wms-web-np2.jdadelivers.com";
// A rule keeps the screen it was made on: Blue Yonder routes on the fragment.
const THE_PAGE = `${WMS}/portal/page#wm.config.partners.suppliers`;
const PAGE_URL = `https://${WMS}/portal/page?siteId=SG#wm.config.partners.suppliers////`;
const OTHER_SCREEN = `https://${WMS}/portal/page?siteId=SG#wm.config.partners.customers.types////`;

let served = [];

globalThis.fetch = async (url, options = {}) => {
  const path = String(url).slice(BACKEND.length);
  calls.push({ path, method: options.method || "GET", body: options.body });
  if (path === "/v1/triggers") return { ok: true, status: 201, json: async () => ({ id: "trg-new" }) };
  if (path.endsWith("/arrivals")) {
    return { ok: true, status: 200, json: async () => served };
  }
  if (path.endsWith("/fire") || path === "/v1/workflow-runs") fires += 1;
  return { ok: true, status: 200, json: async () => ({}) };
};

const worker = await import("./service-worker.js");
const navigated = globalThis.__navigated;

const RULE = { id: "trg-1", page: THE_PAGE, workflowId: "wfl_ct", values: { "Customer Type": "GT2" } };

function ready({ rules = [RULE] } = {}) {
  held.clear();
  calls.length = 0;
  fires = 0;
  held.set("sro.apiUrl", BACKEND);
  held.set("sro.token", "tok");
  held.set("sro.deviceId", "dev-1");
  held.set("sro.deviceSecret", "sec");
  held.set("sro.arrivals", rules);
  // Offers are made on a tab the operator watches, and on no other.
  held.set("sro.watched", [{ tabId: 7, host: WMS, since: 0 }]);
  served = [];
}

const open = () => (held.get("sro.nudges") || []).filter((one) => one.state === "open");

/** One navigation, as `webNavigation.onCommitted` reports it. */
async function land(url = PAGE_URL, at = 1000) {
  await navigated({ frameId: 0, tabId: 7, url, timeStamp: at });
  // The listener fires and forgets; give the offer its turn.
  for (let n = 0; n < 40 && open().length === 0; n++) await new Promise((r) => setTimeout(r, 5));
}

test("a rule made anywhere else reaches this browser, with the job and values to offer", async () => {
  // The list was fetched when the browser registered and at no other time, so
  // a rule made in the console never reached the one process that evaluates
  // it. The heartbeat asks for them now, beside the mail watches.
  ready({ rules: [] });
  served = [
    {
      id: "trg-9",
      workflow_id: "wfl_ct",
      parameters: { "Customer Type": "GT2" },
      arrival: { page: THE_PAGE },
    },
  ];

  await worker.refreshArrivals();

  assert.deepEqual(held.get("sro.arrivals"), [
    { id: "trg-9", page: THE_PAGE, workflowId: "wfl_ct", values: { "Customer Type": "GT2" } },
  ]);
});

test("landing on the page a rule is about offers the job, and starts nothing", async () => {
  ready();

  await land();
  await new Promise((r) => setTimeout(r, 30));

  const [offer] = open();
  assert.ok(offer, "landing on the rule's page offered nothing");
  assert.equal(offer.workflowId, "wfl_ct");
  assert.deepEqual(offer.values, { "Customer Type": "GT2" });
  assert.equal(fires, 0, "landing on a page started a run without a press");
});

test("the same navigation offers once", async () => {
  ready();

  await land(PAGE_URL, 2000);
  await navigated({ frameId: 0, tabId: 7, url: PAGE_URL, timeStamp: 2000 });
  await new Promise((r) => setTimeout(r, 30));

  assert.equal((held.get("sro.nudges") || []).length, 1, "one commit made two offers");
});

test("a different page is not this rule", async () => {
  ready();

  await navigated({
    frameId: 0,
    tabId: 7,
    url: `https://${WMS}/portal/page/suppliers`,
    timeStamp: 3000,
  });
  await new Promise((r) => setTimeout(r, 30));

  assert.equal(open().length, 0, "a rule about one page was offered on another");
});

test("another screen of the same portal is not this rule", async () => {
  ready();

  await navigated({ frameId: 0, tabId: 7, url: OTHER_SCREEN, timeStamp: 4000 });
  await new Promise((r) => setTimeout(r, 30));

  assert.equal(open().length, 0, "a rule made on one Blue Yonder screen was offered on another");
});

test("a rule made from an offer keeps the offer's screen", async () => {
  ready({ rules: [] });
  // An offer as the worker holds it: `startsOn` is `page()` of what was served.
  held.set("sro.nudges", [
    { id: "n_1", state: "open", source: "rig", workflowId: "wfl_ct", startsOn: THE_PAGE, values: {} },
  ]);

  const answer = await new Promise((resolve) =>
    globalThis.__handle({ kind: "do-this-here", nudgeId: "n_1" }, {}, resolve),
  );

  assert.equal(answer.ok, true, answer.error);
  const made = calls.find((call) => call.path === "/v1/triggers");
  assert.equal(JSON.parse(made.body).arrival.page, THE_PAGE, "the rule dropped the screen's route");
});

test("the browser's own pages are not a system to offer work on", async () => {
  ready({ rules: [{ ...RULE, page: "settings" }] });

  await navigated({ frameId: 0, tabId: 7, url: "chrome://settings", timeStamp: 5000 });
  await new Promise((r) => setTimeout(r, 30));

  assert.equal(open().length, 0);
});
