// The race between the two round trips `sroCall` makes: load `page-code.js`
// into the target, then dispatch by name in a second call.
//
// Real Chrome answers the dispatch call whether the document it landed in is
// the one that was just loaded or not -- a click that navigates, a frame that
// reloads under `allFrames`, between the two calls, lands the dispatch in a
// document with no `globalThis.sroPage` at all. Since Chrome 117 a function
// that throws does not reject `executeScript`'s promise: it resolves with
// `{result: undefined, error}`, so `globalThis.sroPage[called]` throwing
// `TypeError: Cannot read properties of undefined` comes back as an error
// this code then reads as "the injected command threw in the page" -- which
// blames page-code.js for what is a navigation, not a bug in it. The old,
// single-call `func` never had this gap: in a fresh document it either ran or
// produced no result, and "no result" already has an honest diagnosis at
// `didNotAnswer`.
//
// Run with `node src/background/sro-call.test.mjs`.

import assert from "node:assert/strict";
import { test } from "node:test";

const openTabs = [{ id: 7, url: "https://wms.example/portal", status: "complete" }];

globalThis.chrome = {
  tabs: {
    query: async ({ url } = {}) =>
      url ? openTabs.filter((tab) => tab.url.startsWith(url.replace("/*", ""))) : openTabs,
    get: async (id) => openTabs.find((tab) => tab.id === id) || null,
  },
  scripting: {
    executeScript: async ({ func, args, files }) => {
      // The `page-code.js` injection itself. Landing on the document that is
      // about to navigate away: nothing about it matters to what comes next.
      if (files) return [];
      // The dispatch call, answered the way real Chrome answers one: `func`
      // is serialised to source and evaluated fresh IN THE TARGET REALM, not
      // called as the same closure -- Chrome never ships a live function
      // across realms. So `globalThis` is re-bound to a brand new object on
      // every call here too, one with no `sroPage` of its own, simulating a
      // document the file injection never reached (a click that navigated it
      // between the two round trips). A throw is turned into `{error}`
      // rather than a rejected promise, exactly as `executeScript` does.
      const [called, given] = args || [];
      const dispatch = new Function(
        "globalThis",
        "called",
        "given",
        `return (${func.toString()})(called, given);`,
      );
      try {
        return [{ result: dispatch({}, called, given) }];
      } catch (error) {
        return [{ result: undefined, error: { message: String(error) } }];
      }
    },
  },
  webNavigation: { getAllFrames: async () => [] },
};

const { perform } = await import("./commands.js");

test("a navigation between loading the page code and dispatching does not blame the page code", async () => {
  const answer = await perform({
    command_id: "cmd-1",
    kind: "ui.perform",
    payload: {
      action: "click",
      origin: "https://wms.example",
      locators: [{ strategy: "text", query: "Save" }],
    },
  });

  assert.equal(answer.ok, false);
  assert.equal(answer.error.kind, "not_actionable");
  // The old failure: a thrown `TypeError` inside the dispatch, surfaced
  // through `whatItSaid` as though page-code.js itself were broken.
  assert.doesNotMatch(
    answer.error.detail,
    /threw in the page/,
    "a navigation between the two calls was read as a bug in the page code",
  );
  // The honest diagnosis this already has for "no result at all":
  // `didNotAnswer` names the tab, its status and which worlds run script.
  assert.match(answer.error.detail, /did not answer/, answer.error.detail);
});
