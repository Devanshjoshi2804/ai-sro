// `tab.open`: somewhere for a lookup to look, on a system nobody has open.
//
// Run with `node src/background/tab-open.test.mjs`.

import assert from "node:assert";
import { test } from "node:test";

let created = [];
let openTabs = [];

globalThis.chrome = {
  tabs: {
    query: async ({ url }) =>
      url ? openTabs.filter((tab) => tab.url.startsWith(url.replace("/*", ""))) : openTabs,
    create: async (options) => {
      created.push(options);
      return { id: 42, ...options };
    },
    update: async () => ({}),
  },
  scripting: { executeScript: async () => [{ result: undefined }] },
};

const { perform } = await import("./commands.js");

const open = (payload) => perform({ command_id: "cmd-1", kind: "tab.open", payload });

test("a system nobody has open gets a tab, behind what the operator is doing", async () => {
  created = [];
  openTabs = [{ id: 1, url: "https://mail.example/inbox" }];

  const answer = await open({ url: "https://wms.example/portal/page?siteId=SG" });

  assert.equal(answer.ok, true);
  assert.equal(answer.result.opened, true);
  assert.equal(created.length, 1);
  assert.equal(created[0].active, false, "a lookup does not take somebody's screen");
});

test("a system already open is answered with the tab that is there", async () => {
  created = [];
  openTabs = [{ id: 9, url: "https://wms.example/portal" }];

  const answer = await open({ url: "https://wms.example/data/WM/wm/suppliers" });

  assert.equal(answer.ok, true);
  assert.equal(answer.result.opened, false);
  assert.equal(answer.result.tab_id, 9);
  assert.equal(created.length, 0, "a second tab on a system they have open is theirs to tidy up");
});

test("only http and https: a chrome:// url is not a system with a session", async () => {
  created = [];
  openTabs = [];

  const answer = await open({ url: "chrome://settings/passwords" });

  assert.equal(answer.ok, false);
  assert.equal(answer.error.kind, "not_actionable");
  assert.equal(created.length, 0);
});

test("no url, and an unreadable one, are refused rather than opening something", async () => {
  created = [];
  openTabs = [];

  assert.equal((await open({})).ok, false);
  assert.equal((await open({ url: "not a url" })).ok, false);
  assert.equal(created.length, 0);
});
