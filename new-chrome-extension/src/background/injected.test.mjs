// Every function this extension injects into a page must be self-contained.
//
// `chrome.scripting.executeScript({func})` serialises that ONE function and
// nothing else. A helper sitting beside it in the module does not exist in the
// page, and calling one throws a ReferenceError there -- which, since Chrome
// 117, does not reject the promise: it resolves with `{result: undefined,
// error}`. Read as a result, that is no answer at all.
//
// Measured on the deployment across 2026-09-16 and 17. `performInPage` called
// `nearMisses`, a module-scope helper, on the one path where no locator
// matched. Every UI step ever attempted on the warehouse host failed with "the
// page did not answer" and the only step that ever held was on a mailbox --
// where a locator DID match, so the broken line was never reached. Three hours
// went on pages, tabs, discarded tabs and content-security policies.
//
// So this re-creates each injected function the way Chrome does -- from its
// own source text, in a scope that holds nothing else -- and runs it against a
// bare document. What it asserts is not what they return; it is that they can
// be called at all.
//
// Run with `node src/background/injected.test.mjs`.

import assert from "node:assert";
import { test } from "node:test";

const injected = await import("./in-page.js");

/** The function as the page gets it: its source, evaluated in an empty scope. */
const asChromeSendsIt = (fn) => new Function(`return (${fn.toString()})`)();

/** Barely a page: enough for a function to run and find nothing. */
function aPage() {
  const el = {
    getAttribute: () => null,
    getBoundingClientRect: () => ({ width: 0, height: 0, top: 0, left: 0 }),
    innerText: "",
    tagName: "BUTTON",
    focus() {},
    click() {},
    dispatchEvent: () => true,
    closest: () => null,
    ownerDocument: null,
  };
  return {
    querySelectorAll: () => [el],
    querySelector: () => null,
    elementFromPoint: () => null,
    documentElement: { scrollTop: 0, clientWidth: 800, clientHeight: 600 },
    body: { innerText: "" },
    title: "",
    cookie: "",
  };
}

const PAYLOADS = {
  performInPage: { action: "click", locators: [{ strategy: "text", query: "Save" }] },
  performAtInPage: { action: "click", x: 10, y: 10 },
  viewportInPage: undefined,
  csrfTokenInPage: { names: ["CSRF-TOKEN"] },
  requestedWithInPage: undefined,
};

test("every injected function runs with nothing but the page around it", () => {
  const named = Object.entries(injected).filter(([name]) => name.endsWith("InPage"));
  assert.ok(named.length >= 4, `only found ${named.length} injected functions`);

  for (const [name, fn] of named) {
    globalThis.document = aPage();
    globalThis.window = { getComputedStyle: () => ({ visibility: "visible", display: "block" }) };
    globalThis.location = { href: "https://wms.example/portal" };
    const alone = asChromeSendsIt(fn);
    try {
      alone(PAYLOADS[name]);
    } catch (error) {
      assert.fail(
        `${name} cannot run in a page: ${error.message}` +
          " — it refers to something that only exists in this module",
      );
    }
  }
});
