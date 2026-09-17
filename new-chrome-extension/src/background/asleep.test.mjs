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
let created = [];
let reloaded = [];
let injectedInto = [];
let result = undefined;
let blockMain = false;
let listeners = [];

globalThis.chrome = {
  tabs: {
    query: async ({ url }) =>
      url ? openTabs.filter((tab) => tab.url.startsWith(url.replace("/*", ""))) : openTabs,
    get: async (id) => openTabs.find((tab) => tab.id === id) || null,
    create: async (options) => {
      created.push(options);
      const made = { id: 99, status: "complete", ...options };
      openTabs.push(made);
      return made;
    },
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
    executeScript: async ({ target, func, world }) => {
      injectedInto.push(target.tabId);
      // The trivial probe the failure path runs in each world answers for
      // itself; everything else gets whatever the test set up.
      if (func && func.length === 0 && func() === true) {
        return world === "MAIN" && blockMain ? [] : [{ result: true }];
      }
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
  // And whether anything can be run in it at all. "The page did not answer"
  // has two causes that want two different people to do two different things:
  // the command ran and produced nothing, or nothing ran. A page whose own
  // content-security policy refuses injected script gives the second, silently
  // and with no error.
  assert.match(answer.error.detail, /script runs in it/, answer.error.detail);
  assert.deepEqual(reloaded, [], "a tab that is awake is not reloaded under the operator");
});

const go = (payload) =>
  perform({ command_id: "cmd-2", kind: "navigate", payload });

test("a navigate opens the page when nothing is open on that system", async () => {
  // Refusing here was refusing to do the one thing a navigate is. `ui.perform`
  // opens a tab through `starts_on` when the operator's browser is elsewhere;
  // a navigate, which carries the url by definition, would not -- so a run
  // whose first warehouse step is "go to the Customer Types screen" died
  // `no_tab_for_system` in front of an operator with that system open in
  // another window. Measured on the deployment, 2026-09-17.
  openTabs = [{ id: 3, url: "https://mail.example/inbox", status: "complete" }];
  created = [];

  const answer = await go({
    url: "https://wms.example/portal/page?menu=wm.config",
    origin: "https://wms.example",
    allow_focus: true,
  });

  assert.equal(answer.ok, true, JSON.stringify(answer));
  assert.equal(answer.result.opened, true);
  assert.equal(created.length, 1, "it should open exactly one tab");
  assert.equal(created[0].url, "https://wms.example/portal/page?menu=wm.config");
  assert.equal(created[0].active, false, "opening a page is not taking somebody's screen");
});

test("a navigate does not open somewhere the command is not for", async () => {
  // The same rule `opensFor` holds for a perform: a url whose origin is not
  // the command's is not this system's page, and opening it would be driving
  // the browser somewhere nobody asked for.
  openTabs = [];
  created = [];

  const answer = await go({
    url: "https://evil.example/portal",
    origin: "https://wms.example",
    allow_focus: true,
  });

  assert.equal(answer.ok, false);
  assert.equal(answer.error.kind, "no_tab_for_system");
  assert.deepEqual(created, []);
});

test("a page whose policy refuses injected script says so", () => {
  // The case this instrument exists for: every UI step ever attempted on the
  // warehouse host failed while the ones on the mailbox held, and the run's
  // side could not tell "ran and produced nothing" from "nothing ran".
  openTabs = [{ id: 7, url: "https://wms.example/portal", status: "complete" }];
  blockMain = true;
  result = undefined;

  return click().then((answer) => {
    blockMain = false;
    assert.match(answer.error.detail, /content-security policy refuses/, answer.error.detail);
  });
});

const at = (payload) =>
  perform({ command_id: "cmd-3", kind: "ui.perform_at", payload });

test("a point that lands on a frame is asked again inside it", async () => {
  // The picture the model is shown is the top document's viewport. A warehouse
  // application inside an iframe puts every control in another document, so
  // the point is right and the document is wrong -- which made the rung that
  // looks at a picture useless on the one system it exists for.
  openTabs = [{ id: 7, url: "https://wms.example/portal", status: "complete" }];
  const asked = [];
  globalThis.chrome.webNavigation.getAllFrames = async () => [
    { frameId: 0, url: "https://wms.example/portal" },
    { frameId: 9, url: "https://wms.example/portal/app" },
  ];
  globalThis.chrome.scripting.executeScript = async ({ target, args }) => {
    asked.push({ frames: target.frameIds, point: args && { x: args[0].x, y: args[0].y } });
    // The top document answers "that is a frame, and here it is"; the frame
    // itself does the click.
    return target.frameIds
      ? [{ result: { ok: true, result: { performed: true } } }]
      : [
          {
            result: {
              ok: false,
              error: {
                kind: "point_in_a_frame",
                detail: "that point is inside a frame",
                frame: { src: "https://wms.example/portal/app", left: 12, top: 80 },
              },
            },
          },
        ];
  };

  const answer = await at({
    origin: "https://wms.example",
    x: 300,
    y: 220,
    action: "click",
  });

  assert.equal(answer.ok, true, JSON.stringify(answer));
  assert.deepEqual(asked[0], { frames: undefined, point: { x: 300, y: 220 } });
  // Into the frame, with the point moved into its coordinates.
  assert.deepEqual(asked[1], { frames: [9], point: { x: 288, y: 140 } });
});

test("a frame this browser cannot name is said so, not clicked anyway", async () => {
  openTabs = [{ id: 7, url: "https://wms.example/portal", status: "complete" }];
  globalThis.chrome.webNavigation.getAllFrames = async () => [
    { frameId: 0, url: "https://wms.example/portal" },
  ];
  globalThis.chrome.scripting.executeScript = async () => [
    {
      result: {
        ok: false,
        error: {
          kind: "point_in_a_frame",
          detail: "that point is inside a frame",
          frame: { src: "https://wms.example/portal/app", left: 12, top: 80 },
        },
      },
    },
  ];

  const answer = await at({ origin: "https://wms.example", x: 300, y: 220, action: "click" });

  assert.equal(answer.ok, false);
  assert.match(answer.error.detail, /cannot reach/);
});

test("a frame that has routed since it loaded is still the frame", async () => {
  // A frame's `src` ATTRIBUTE is the url it was created with, not the url it
  // is showing. Measured on the deployment, 2026-09-17: the point landed on
  // the application's frame, whose src still named the Warehouse route while
  // the app had long since routed to Customer Types inside it. The exact match
  // found nothing, and a run that had reached the right page reported that it
  // could not reach the frame in front of it.
  openTabs = [{ id: 7, url: "https://wms.example/portal", status: "complete" }];
  const asked = [];
  globalThis.chrome.webNavigation.getAllFrames = async () => [
    { frameId: 0, url: "https://wms.example/portal" },
    // A second child, so "the only frame there is" cannot answer this and the
    // match has to be the document itself.
    { frameId: 4, url: "https://analytics.example/beacon" },
    // Same document, and it has routed: a different fragment and a fresh
    // session token in the query.
    { frameId: 9, url: "https://wms.example/portal/page?libraryContext=b2&siteId=SG#customers" },
  ];
  globalThis.chrome.scripting.executeScript = async ({ target, args }) => {
    asked.push({ frames: target.frameIds, point: args && { x: args[0].x, y: args[0].y } });
    return target.frameIds
      ? [{ result: { ok: true, result: { performed: true } } }]
      : [
          {
            result: {
              ok: false,
              error: {
                kind: "point_in_a_frame",
                detail: "that point is inside a frame",
                frame: {
                  src: "https://wms.example/portal/page?libraryContext=a1&siteId=SG#warehouse",
                  left: 0,
                  top: 100,
                },
              },
            },
          },
        ];
  };

  const answer = await at({ origin: "https://wms.example", x: 300, y: 220, action: "click" });

  assert.equal(answer.ok, true, JSON.stringify(answer));
  assert.deepEqual(asked[1], { frames: [9], point: { x: 300, y: 120 } });
});

test("a page with two frames and no match is not guessed at", async () => {
  openTabs = [{ id: 7, url: "https://wms.example/portal", status: "complete" }];
  globalThis.chrome.webNavigation.getAllFrames = async () => [
    { frameId: 0, url: "https://wms.example/portal" },
    { frameId: 8, url: "https://elsewhere.example/one" },
    { frameId: 9, url: "https://elsewhere.example/two" },
  ];
  globalThis.chrome.scripting.executeScript = async () => [
    {
      result: {
        ok: false,
        error: {
          kind: "point_in_a_frame",
          detail: "that point is inside a frame",
          frame: { src: "https://wms.example/portal/app", left: 0, top: 0 },
        },
      },
    },
  ];

  const answer = await at({ origin: "https://wms.example", x: 10, y: 10, action: "click" });

  assert.equal(answer.ok, false);
  assert.match(answer.error.detail, /cannot reach/);
});
