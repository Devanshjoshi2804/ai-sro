// "Do this here": the rule an operator makes by standing somewhere, and this
// browser firing it when it lands there again.
//
// The wire that was missing. This extension could offer a job it recognised
// and could carry out a run somebody else started, and nothing joined them.
//
// Run with `node --test src/background/page-rules.test.mjs`.

import assert from "node:assert";
import { test } from "node:test";

const held = new Map();
const calls = [];
let fires = 0;
let refuse = null;

globalThis.chrome = {
  storage: {
    local: {
      get: async (key) => (held.has(key) ? { [key]: held.get(key) } : {}),
      set: async (kv) => Object.entries(kv).forEach(([k, v]) => held.set(k, v)),
      remove: async () => {},
    },
  },
  runtime: { onMessage: { addListener: () => {} }, onInstalled: { addListener: () => {} },
    onStartup: { addListener: () => {} }, getManifest: () => ({ version: "0.1.0" }), id: "ext" },
  tabs: { query: async () => [], onRemoved: { addListener: () => {} },
    onUpdated: { addListener: () => {} }, onActivated: { addListener: () => {} },
    sendMessage: async () => {}, get: async () => ({ id: 7, url: PAGE_URL }) },
  webNavigation: {
    onCommitted: { addListener: (fn) => (globalThis.__navigated = fn) },
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

const BACKEND = "http://backend.test";
const WMS = "bf56-kms-wms-web-np2.jdadelivers.com";
const THE_PAGE = `${WMS}/portal/page`;
const PAGE_URL = `https://${WMS}/portal/page?siteId=SG#wm.config.partners.suppliers////`;

globalThis.fetch = async (url, options = {}) => {
  const path = String(url).slice(BACKEND.length);
  calls.push({ path, method: options.method || "GET" });
  if (path.endsWith("/fire")) {
    fires += 1;
    if (refuse) return { ok: false, status: refuse, statusText: "", json: async () => ({ detail: "no" }) };
    return { ok: true, status: 202, json: async () => ({ trigger_id: "trg-1", run_id: "run-1" }) };
  }
  return { ok: true, status: 200, json: async () => ({}) };
};

await import("./service-worker.js");
const navigated = globalThis.__navigated;

function ready({ rules = [{ id: "trg-1", page: THE_PAGE }], paused = false } = {}) {
  held.clear();
  calls.length = 0;
  fires = 0;
  refuse = null;
  held.set("sro.apiUrl", BACKEND);
  held.set("sro.token", "tok");
  held.set("sro.deviceId", "dev-1");
  held.set("sro.deviceSecret", "sec");
  held.set("sro.arrivals", rules);
  held.set("sro.paused", paused);
}

/** One navigation, as `webNavigation.onCommitted` reports it. */
async function land(url = PAGE_URL, at = 1000) {
  await navigated({ frameId: 0, tabId: 7, url, timeStamp: at });
  // The listener fires and forgets; give the fire its turn.
  for (let n = 0; n < 40 && fires === 0; n++) await new Promise((r) => setTimeout(r, 5));
}

test("landing on the page an operator made a rule about starts the job", async () => {
  ready();

  await land();

  assert.equal(fires, 1, "the rule did not fire");
  assert.ok(
    calls.some((c) => c.path === "/v1/agents/dev-1/arrivals/trg-1/fire" && c.method === "POST"),
    `nothing was fired: ${JSON.stringify(calls)}`,
  );
  // Drawn where the operator can see why their browser is doing something.
  assert.equal(held.get("sro.activeRun")?.runId, "run-1");
});

test("the same navigation does not fire it twice", async () => {
  ready();

  await land(PAGE_URL, 2000);
  await navigated({ frameId: 0, tabId: 7, url: PAGE_URL, timeStamp: 2000 });
  await new Promise((r) => setTimeout(r, 30));

  assert.equal(fires, 1, "one commit started two runs");
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

  assert.equal(fires, 0, "a rule about one page fired on another");
});

test("a paused browser does what the badge says it does: nothing", async () => {
  // A standing rule is not an exception to the operator having said stop.
  ready({ paused: true });

  await navigated({ frameId: 0, tabId: 7, url: PAGE_URL, timeStamp: 4000 });
  await new Promise((r) => setTimeout(r, 30));

  assert.equal(fires, 0);
});

test("the browser's own pages are not a system to drive", async () => {
  ready({ rules: [{ id: "trg-1", page: "settings" }] });

  await navigated({ frameId: 0, tabId: 7, url: "chrome://settings", timeStamp: 5000 });
  await new Promise((r) => setTimeout(r, 30));

  assert.equal(fires, 0);
});

test("a rule the backend refuses is said out loud, not swallowed", async () => {
  // A rule that silently stopped firing is the worst of the failures here:
  // the operator believes their browser is doing something and it is not.
  ready();
  refuse = 404;

  await land(PAGE_URL, 6000);

  assert.match(held.get("sro.lastError") || "", /page rule did not fire/);
});
