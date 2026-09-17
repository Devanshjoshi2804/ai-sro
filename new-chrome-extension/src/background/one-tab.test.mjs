// A run drives one tab, and every command it sends drives the same one.
//
// `tabForRun` has always known which tab a run is driving -- it pins it on the
// first command and keeps it while it is on the step's own origin. Only
// `ui.perform` asked it. `screenshot`, `ui.url`, `ui.perform_at` and `navigate`
// each called `drivenTab(origin)` instead, which answers "some tab on that
// host": with ten Blue Yonder tabs open and none of them the active one, that
// is an arbitrary one of the ten.
//
// So the click acted on the run's tab and the picture beside it could be of a
// different tab -- which is the exact fault the screenshot's own comment says
// it exists to prevent, defeated by pairing it with a different tab-finder.
// Measured on the deployment, 2026-09-17: `run_e1ff6362` step 3
// `focus_not_permitted: the page to be driven is not the visible one`.
//
// Run with `node src/background/one-tab.test.mjs`.

import assert from "node:assert/strict";
import { test } from "node:test";

const ORIGIN = "https://wms.example";
let tabs = [];
let raised = [];
let captured = [];

const png = () => {
  const bytes = new Uint8Array(64);
  bytes.set([0x89, 0x50, 0x4e, 0x47, 13, 10, 26, 10]);
  return "data:image/png;base64," + Buffer.from(bytes).toString("base64");
};

globalThis.chrome = {
  tabs: {
    query: async ({ url, active }) => {
      if (url) return tabs.filter((one) => one.url.startsWith(url.replace("/*", "")));
      if (active) return tabs.filter((one) => one.active);
      return tabs;
    },
    get: async (id) => {
      const found = tabs.find((one) => one.id === id);
      if (!found) throw new Error(`No tab with id: ${id}.`);
      return found;
    },
    update: async (id, what) => {
      const found = tabs.find((one) => one.id === id);
      if (what?.active) {
        for (const one of tabs) one.active = one.id === id;
        raised.push(id);
      }
      return found;
    },
    captureVisibleTab: async () => {
      captured.push(tabs.find((one) => one.active)?.id);
      return png();
    },
    onUpdated: { addListener: () => {}, removeListener: () => {} },
  },
  windows: { update: async () => ({}) },
  scripting: {
    // Two shapes, because the page answers in two: the viewport probe returns
    // its measurements bare, and everything else answers `{ok, result}` the
    // way `whatItSaid` unwraps.
    executeScript: async ({ target, func }) => {
      if (String(func).includes("innerWidth"))
        return [{ result: { url: `${ORIGIN}/portal`, width: 1200, height: 800, digest: "" } }];
      return [
        {
          result: {
            ok: true,
            // `tab` is not something the page returns; it is how a test tells
            // which tab answered.
            result: { performed: true, matched_by: "component", candidates: 1, tab: target.tabId },
          },
        },
      ];
    },
  },
  webNavigation: { getAllFrames: async () => [] },
  storage: { local: { get: async () => ({}), set: async () => {} } },
};

const { perform } = await import("./commands.js");

/** Ten tabs on the one host and none of them the active one -- an operator who
 * has been working all afternoon, which is the state this was measured in. */
const aPileOfTabs = () => {
  tabs = [
    { id: 1, windowId: 1, active: true, status: "complete", url: "https://other.example/" },
    ...Array.from({ length: 10 }, (_, n) => ({
      id: 10 + n,
      windowId: 1,
      active: false,
      status: "complete",
      url: `${ORIGIN}/portal?tab=${n}`,
    })),
  ];
  raised = [];
  captured = [];
};

const run = (kind, payload, runId = "run_1") =>
  perform({ command_id: `cmd-${kind}`, kind, run_id: runId, payload });

test("the picture is of the tab the run has been driving, not one of ten", async () => {
  aPileOfTabs();
  // The run acts first, which is what pins its tab -- and `drivenTab` would
  // hand back tab 10, the first on that host, for every command after it.
  const acted = await run("ui.perform", {
    origin: ORIGIN,
    action: "click",
    locators: [{ strategy: "component", query: "button#add", visible_only: true }],
  });
  assert.equal(acted.ok, true, JSON.stringify(acted));
  const drivingTab = acted.result.tab;

  // And now the operator looks at a DIFFERENT tab on the same host, which is
  // what people do while a run is going. `drivenTab` prefers the active one,
  // so from here the two finders disagree -- and the run's own tab is the
  // right answer, because that is where its click landed.
  for (const one of tabs) one.active = one.id === 15;

  const shot = await run("screenshot", { inline: true, origin: ORIGIN, allow_focus: true });

  assert.equal(shot.ok, true, JSON.stringify(shot));
  assert.equal(
    captured[0],
    drivingTab,
    "it photographed a different tab from the one it clicked in",
  );
});

test("the url a step reports is the url of that same tab", async () => {
  aPileOfTabs();
  const acted = await run("ui.perform", {
    origin: ORIGIN,
    action: "click",
    locators: [{ strategy: "component", query: "button#add", visible_only: true }],
  });
  tabs.find((one) => one.id === acted.result.tab).url = `${ORIGIN}/portal#the-right-screen`;
  // Somebody else's tab is in front now.
  for (const one of tabs) one.active = one.id === 15;

  const said = await run("ui.url", { origin: ORIGIN });

  assert.match(said.result.url, /the-right-screen/, JSON.stringify(said));
});

test("a refused screen says which of the three refusals it was", async () => {
  // `focus_not_permitted` covered three different faults -- no permission, a
  // window that went away, a stale tab id -- and a run recorded the same six
  // words for all of them.
  aPileOfTabs();
  const said = await run("screenshot", { inline: true, origin: ORIGIN, allow_focus: false });

  assert.equal(said.ok, false);
  assert.equal(said.error.kind, "focus_not_permitted");
  assert.match(said.error.detail, /may not bring the page forward/, said.error.detail);
});
