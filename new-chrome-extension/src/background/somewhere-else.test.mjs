// A run that is not where it thought it was says where it IS.
//
// Measured on the deployment 2026-09-19. The operator's WMS session had
// expired, so the run's navigate landed on `blueyonderalphaus.b2clogin.com` --
// the platform's sign-in host, which is not the step's origin. `tabForRun`
// will not answer with a tab that has left the step's origin, which is right
// for driving and blinding for reading: `ui.url` failed `no_tab_for_system`,
// the run built a look with no url at all, and the step reported
//
//     the browser is on None, not https://…/portal#…customers.types////
//
// with the person looking at the sign-in page the whole time. Nothing said
// "sign in and start it again", and `sign_in` could not have fired either --
// it asked the same origin-scoped question, so the one command that exists for
// a login page could never find one.
//
// Run with `node src/background/somewhere-else.test.mjs`.

import assert from "node:assert/strict";
import { test } from "node:test";

const ORIGIN = "https://wms.example";
const SIGN_IN_PAGE = "https://login.example/oauth2/authorize?client_id=abc";

let tabs = [];
let signedInAt = [];

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
      if (what?.active) for (const one of tabs) one.active = one.id === id;
      return found;
    },
    captureVisibleTab: async () => "data:image/png;base64,",
    onUpdated: { addListener: () => {}, removeListener: () => {} },
  },
  windows: { update: async () => ({}) },
  scripting: {
    executeScript: async ({ target, func }) => {
      const said = String(func);
      if (said.includes("innerWidth"))
        return [{ result: { url: SIGN_IN_PAGE, width: 1200, height: 800, digest: "" } }];
      // `whatIsOnThisPage`, answering for the sign-in page the browser is on.
      if (said.includes("signed_out"))
        return [{ result: { signed_out: true, dialog: "", loading: false } }];
      // `fillTheLoginForm`, which is what this test wants to see reached.
      // Its own answer shape: what it filled, and whether it submitted.
      signedInAt.push(target.tabId);
      return [{ result: { did: ["username", "password"], submitted: true } }];
    },
  },
  webNavigation: { getAllFrames: async () => [] },
  storage: { local: { get: async () => ({}), set: async () => {} } },
};

const { perform } = await import("./commands.js");

/** The run's own tab, having followed a redirect off the step's origin. */
const bouncedToSignIn = () => {
  tabs = [
    { id: 7, windowId: 1, active: true, status: "complete", url: SIGN_IN_PAGE },
  ];
  signedInAt = [];
};

const run = (kind, payload, runId = "run_1") =>
  perform({ command_id: `cmd-${kind}`, kind, run_id: runId, payload });

test("a look that finds no tab on the origin answers with the page in front of the person", async () => {
  bouncedToSignIn();

  const said = await run("ui.url", { origin: ORIGIN });

  assert.equal(said.ok, true, "it refused to say anything at all");
  // Still no url ON THE ORIGIN -- the step has not arrived and must not be
  // read as having arrived.
  assert.equal(said.result.url, null);
  assert.equal(said.result.elsewhere, SIGN_IN_PAGE);
  // And what that page is, which is the whole point: a run can now say "the
  // session has gone" instead of "no control matched".
  assert.equal(said.result.signed_out, true);
});

test("a sign-in is driven in the tab the login actually happened in", async () => {
  // The one command that must look past the origin. A sign-in page is on
  // another host by design, so an origin-scoped lookup could never find one.
  bouncedToSignIn();

  const said = await run("sign_in", { origin: ORIGIN, username: "u", password: "p" });

  assert.equal(said.ok, true, said.error?.detail);
  assert.deepEqual(signedInAt, [7]);
});

test("a browser with no usable tab at all still says so plainly", async () => {
  tabs = [{ id: 9, windowId: 1, active: true, status: "complete", url: "chrome://newtab" }];

  const said = await run("ui.url", { origin: ORIGIN });

  assert.equal(said.ok, false);
  assert.equal(said.error.kind, "no_tab_for_system");
});
