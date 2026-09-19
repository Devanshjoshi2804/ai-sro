// A run goes on driving the tab it pinned, across a worker that was evicted.
//
// Measured on the deployment 2026-09-19, runs `run_fd77a70d` and
// `run_4a57baf0`, two minutes apart and identical: step 0 held -- "the username
// RKUCHIYAGM has been successfully entered into the 'Username or email' field"
// -- and step 1 came back `no_tab_for_system` while the operator sat looking at
// that very page. The evidence holds one tab, 148285749, on the sign-in host
// from 16:23:33 through both runs and past them. Nothing moved and nothing
// closed; this worker did, between two commands, which `perform` already calls
// the ordinary case for a run performed with the panel closed.
//
// Step 0 survives an eviction because a first step carries `starts_on` and can
// open its page again. Every step after the first carries none.
//
// Run with `node src/background/pinned-tab.test.mjs`.

import assert from "node:assert/strict";
import { test } from "node:test";

let openTabs = [];
let stored = {};
let byUrl = true;

globalThis.chrome = {
  tabs: {
    // `byUrl: false` is the browser answering nothing to a url-filtered query
    // while the tab is plainly there -- which is what the deployment did, and
    // what leaves a step with nothing but its pin.
    query: async ({ url }) =>
      url
        ? byUrl
          ? openTabs.filter((tab) => tab.url.startsWith(url.replace("/*", "")))
          : []
        : openTabs,
    get: async (id) => openTabs.find((tab) => tab.id === id) || null,
    create: async (options) => {
      const made = { id: 99, status: "complete", ...options };
      openTabs.push(made);
      return made;
    },
    update: async () => ({}),
    reload: async () => {},
    onUpdated: { addListener: () => {}, removeListener: () => {} },
  },
  scripting: {
    executeScript: async ({ target }) => [
      { result: { ok: true, result: { performed: true, tab: target.tabId } } },
    ],
  },
  webNavigation: { getAllFrames: async () => [] },
  storage: {
    local: {
      get: async (keys) =>
        Object.fromEntries(
          (Array.isArray(keys) ? keys : [keys]).map((key) => [key, stored[key]]),
        ),
      set: async (pairs) => Object.assign(stored, pairs),
      remove: async () => {},
    },
  },
  runtime: { sendMessage: async () => {}, lastError: null },
};

const { perform } = await import("./commands.js");

const ORIGIN = "https://keycloak.example";
const RUN = "run_4a57baf0";

const step = (payload, runId = RUN) =>
  perform({
    command_id: "cmd-1",
    kind: "ui.perform",
    run_id: runId,
    payload: {
      action: "click",
      origin: ORIGIN,
      locators: [{ query: "Password", strategy: "text", visible_only: true }],
      allow_focus: true,
      ...payload,
    },
  });

const fresh = () => {
  openTabs = [{ id: 7, url: `${ORIGIN}/auth/realms/x`, status: "complete" }];
  stored = {};
  byUrl = true;
};

test("the tab a run pinned is written down, not only remembered", async () => {
  fresh();

  await step({ starts_on: `${ORIGIN}/auth/realms/x` });

  assert.equal(stored["sro.activeRun"]?.runId, RUN);
  assert.equal(stored["sro.activeRun"]?.tabId, 7, "the pin went to storage");
});

test("a step after an eviction acts in the tab the run already pinned", async () => {
  fresh();
  // A run id this worker has never seen, which is what an evicted one comes
  // back as: `latest` died with it, so the run it was driving a second ago is
  // indistinguishable from a run it has never heard of. All it has is this.
  const evicted = "run_evicted";
  stored["sro.activeRun"] = { runId: evicted, at: Date.now(), source: "backend", tabId: 7 };
  // And the browser answering nothing to a url query, as it did.
  byUrl = false;

  const answer = await step({}, evicted);

  assert.equal(answer.ok, true, JSON.stringify(answer));
  assert.equal(answer.result.tab, 7, "it drove the tab it had pinned");
});

test("a pin from another run is not this run's tab", async () => {
  fresh();
  stored["sro.activeRun"] = { runId: "run_somebody_else", at: Date.now(), tabId: 7 };
  byUrl = false;

  // A run this worker has never driven, so the only pin on offer is the stored
  // one, and it belongs to somebody else.
  const answer = await step({}, "run_a_third_one");

  assert.equal(answer.ok, false);
  assert.equal(answer.error.kind, "no_tab_for_system");
});

test("a pinned tab that has left the step's system is not used for it", async () => {
  fresh();
  openTabs = [{ id: 7, url: "https://mail.google.com/mail/u/0", status: "complete" }];
  stored["sro.activeRun"] = { runId: "run_wandered", at: Date.now(), tabId: 7 };
  byUrl = false;

  const answer = await step({}, "run_wandered");

  assert.equal(answer.ok, false, "a password must not be typed into the mailbox");
  assert.equal(answer.error.kind, "no_tab_for_system");
});
