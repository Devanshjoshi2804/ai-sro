// Self-check for the recorder going back into tabs after an extension reload.
//
// Reloading the extension severs `chrome.runtime` for every content script
// already in a page. The script cannot report that -- there is nobody left to
// report it to -- so the tab goes quiet, while the panel goes on saying
// "watching this tab, since 65m", because the watch is a fact about the tab and
// not about whether anything is still listening. An operator who reloads the
// extension, demonstrates a task and finds nothing was recorded learns exactly
// one thing, and it is not a good one.
//
// Not a browser test: driving a real reload from Playwright loses the extension
// for good, so the rule is checked here against a stubbed `chrome` instead.
//
// Run with `node src/background/watching-across-a-reload.test.mjs`.

import assert from "node:assert";

const injected = [];
const tabs = new Map([
  [11, { id: 11, url: "https://wms.example/portal#work.areas" }],
  [22, { id: 22, url: "https://erp.example/receipts" }],
  // A tab Chrome will not report a URL for: one still opening, or one whose URL
  // this extension has no permission to read.
  [33, { id: 33 }],
]);

globalThis.chrome = {
  tabs: {
    get: async (id) => {
      if (!tabs.has(id)) throw new Error("No tab with id: " + id);
      return tabs.get(id);
    },
  },
  scripting: {
    executeScript: async ({ target }) => {
      injected.push(target.tabId);
      return [];
    },
  },
};

const { injectIntoWatched } = await import("./scripts.js");

const POLICY = { capture_enabled: true, include_hosts: [], exclude_hosts: [] };

// Both watched tabs get the scripts back, and both realms of each: the recorder
// needs the page's own `Ext` registry, which the isolated world cannot see.
const put = await injectIntoWatched([{ tabId: 11 }, { tabId: 22 }], POLICY);
assert.equal(put, 2);
assert.deepEqual([...new Set(injected)].sort(), [11, 22]);

// A watch outlives the tab it names. Chrome hands the same ids out again, so a
// watch on a tab that is gone is not merely useless -- injecting on it would be
// recording whatever tab inherited the number.
injected.length = 0;
assert.equal(await injectIntoWatched([{ tabId: 99 }], POLICY), 0);
assert.deepEqual(injected, []);

// One dead watch does not stop the live ones beside it.
injected.length = 0;
assert.equal(await injectIntoWatched([{ tabId: 99 }, { tabId: 11 }], POLICY), 1);
assert.deepEqual([...new Set(injected)], [11]);

// A host the tenant excludes is not injected into, whoever watched it. The
// watch says which tab the work is in; the policy says what may be recorded at
// all, and it is not the watch's to overrule.
injected.length = 0;
const EXCLUDING = { ...POLICY, exclude_hosts: ["erp.example"] };
assert.equal(await injectIntoWatched([{ tabId: 11 }, { tabId: 22 }], EXCLUDING), 1);
assert.deepEqual([...new Set(injected)], [11]);

// A tab with no URL cannot be judged against the policy, and injecting into a
// page nobody has checked is exactly the thing the policy exists to stop.
injected.length = 0;
assert.equal(await injectIntoWatched([{ tabId: 33 }, { tabId: 11 }], POLICY), 1);
assert.deepEqual([...new Set(injected)], [11]);

// Nothing watched is not an error, it is a browser nobody has pointed at yet.
assert.equal(await injectIntoWatched([], POLICY), 0);
assert.equal(await injectIntoWatched(undefined, POLICY), 0);

console.log("watching-across-a-reload.test.mjs: ok");
