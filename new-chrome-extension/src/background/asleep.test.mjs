// A tab Chrome put away, and a failure that says which page it was.
//
// Measured on the deployment, 2026-09-16: three runs failed `not_actionable:
// the page did not answer` and both the operator and I read it as "the locator
// did not match" -- it means the injection produced no result at all, which is
// a different fault with a different fix.
//
// Run with `node src/background/asleep.test.mjs`.

import assert from "node:assert";
import { test } from "node:test";

let openTabs = [];
let reloaded = [];
let injectedInto = [];
let result = undefined;
let listeners = [];

globalThis.chrome = {
  tabs: {
    query: async ({ url }) =>
      url ? openTabs.filter((tab) => tab.url.startsWith(url.replace("/*", ""))) : openTabs,
    get: async (id) => openTabs.find((tab) => tab.id === id) || null,
    create: async (options) => ({ id: 99, ...options }),
    update: async () => ({}),
    reload: async (id) => {
      reloaded.push(id);
      // What a reload does: the tab comes back, no longer discarded, and
      // reports itself complete to whoever is listening.
      const tab = openTabs.find((one) => one.id === id);
      if (tab) tab.discarded = false;
      for (const watch of listeners) watch(id, { status: "complete" });
    },
    onUpdated: {
      addListener: (fn) => listeners.push(fn),
      removeListener: (fn) => {
        listeners = listeners.filter((one) => one !== fn);
      },
    },
  },
  scripting: {
    executeScript: async ({ target }) => {
      injectedInto.push(target.tabId);
      return [{ result }];
    },
  },
  webNavigation: { getAllFrames: async () => [] },
};

const { perform } = await import("./commands.js");

const click = () =>
  perform({
    command_id: "cmd-1",
    kind: "ui.perform",
    payload: {
      action: "click",
      origin: "https://wms.example",
      locators: [{ query: "Customer Types", strategy: "text", visible_only: true }],
      allow_focus: true,
    },
  });

test("a tab Chrome discarded is woken, not reported as a page that said nothing", async () => {
  // Chrome discards background tabs under memory pressure, and a discarded tab
  // is still in `tabs.query` with its url. Injecting into one returns nothing:
  // no error, no result. An operator whose warehouse tab has been behind their
  // mail for an hour has exactly this tab.
  openTabs = [{ id: 7, url: "https://wms.example/portal", discarded: true, status: "complete" }];
  reloaded = [];
  injectedInto = [];
  result = { ok: true, result: { performed: true } };

  const answer = await click();

  assert.deepEqual(reloaded, [7], "it acted on a tab Chrome had put away");
  assert.equal(answer.ok, true);
  // Every injection this command made went into the operator's own tab: the
  // alternative is a second tab at the same origin, which leaves them with two
  // and loses whatever was on the screen in the first.
  assert.deepEqual([...new Set(injectedInto)], [7]);
});

test("a page that still says nothing is named, with its status", async () => {
  openTabs = [{ id: 7, url: "https://wms.example/portal", discarded: false, status: "loading" }];
  reloaded = [];
  result = undefined;

  const answer = await click();

  assert.equal(answer.ok, false);
  assert.equal(answer.error.kind, "not_actionable");
  assert.match(answer.error.detail, /wms\.example\/portal/, answer.error.detail);
  assert.match(answer.error.detail, /status loading/, answer.error.detail);
  assert.deepEqual(reloaded, [], "a tab that is awake is not reloaded under the operator");
});
