// Self-check for the gesture relay.
//
// What is under test is the thing that used to be enforced by an exception.
// `observe.js` had no guard against being run twice in one world; its
// top-level `const` threw instead, which killed the second copy before it
// could add a second listener. That worked, and it filled the extension's
// error list -- measured on the deployment 2026-09-21, forty of
// `Identifier 'MAX_GESTURE_CHARS' has already been declared`, one per
// re-injection per frame.
//
// `injectInto` re-runs these files on every already-open watched tab: on a
// policy refresh, on an extension reload, on a second press of "watch".
//
// Run with `node src/content/observe.test.mjs`.

import assert from "node:assert";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const here = path.dirname(fileURLToPath(import.meta.url));
const SOURCE = readFileSync(path.join(here, "observe.js"), "utf-8");

const tests = [];
let failed = 0;
const test = (name, fn) => tests.push([name, fn]);

/** A world a content script can be run in, twice. */
function aWorld({ runtimeId = "ext-1" } = {}) {
  const sent = [];
  /** Every call the script MADE, whether or not it got through. */
  const tried = [];
  const listeners = {};
  const sandbox = {
    window: {
      addEventListener: (type, fn) => {
        (listeners[type] ||= []).push(fn);
      },
      dispatchEvent: (event) => {
        for (const fn of [...(listeners[event.type] || [])]) fn(event);
      },
    },
    location: { href: "https://wms.example/receiving" },
    chrome: {
      runtime: {
        get id() {
          return sandbox.chrome.runtime._id;
        },
        _id: runtimeId,
        sendMessage: (message) => {
          tried.push(message);
          if (!sandbox.chrome.runtime._id) {
            // Chrome throws this SYNCHRONOUSLY, which is why a `.catch()` on
            // the promise never sees it.
            throw new Error("Extension context invalidated.");
          }
          sent.push(message);
          return Promise.resolve();
        },
      },
    },
    sent,
    tried,
    listeners,
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  return sandbox;
}

const run = (world) => vm.runInContext(SOURCE, world);
const gesture = (world, detail) =>
  world.window.dispatchEvent({ type: "sro:gesture", detail });

test("running it twice in one world does not throw", () => {
  const world = aWorld();

  run(world);
  run(world);
});

test("and does not relay a gesture twice", () => {
  // The whole reason the SyntaxError mattered. Two listeners would forward
  // every gesture twice -- which is exactly what happened to CALLS, where the
  // IIFE meant there was no accident to save it: 173 of 367 duplicated in one
  // day of real recording.
  const world = aWorld();
  run(world);
  run(world);
  world.sent.length = 0;

  gesture(world, JSON.stringify({ kind: "click" }));

  assert.equal(world.sent.length, 1, `relayed ${world.sent.length} times`);
});

test("what is left behind is a question, not a flag", () => {
  // Not a plain "already installed" flag. After an extension reload the copy
  // in residence can forward nothing, and a flag it had set would keep the
  // live replacement out -- a tab that records gestures nobody receives,
  // which is the failure the reload repair exists to prevent.
  //
  // Asserted on what is LEFT ON THE WINDOW rather than by re-running in a
  // sandbox: two injections of a content script get two `chrome.runtime`
  // bindings in the real browser and one here, so a sandbox cannot tell a
  // dead residence from a live one by running it twice. What it can tell --
  // and what the whole decision rests on -- is whether the thing in residence
  // is re-asked at call time.
  const world = aWorld();
  run(world);

  assert.equal(typeof world.window.__sroRelayingGestures, "function");
  assert.equal(
    world.window.__sroRelayingGestures(),
    true,
    "a live copy says it is live",
  );

  world.chrome.runtime._id = null; // the extension was reloaded under it

  assert.equal(
    world.window.__sroRelayingGestures(),
    false,
    "an orphaned copy still claims the world, and the live one is kept out",
  );
});

test("an orphan that is asked to relay says nothing and does not throw", () => {
  // `sendMessage` throws `Extension context invalidated` synchronously, so a
  // `.catch()` on the promise never sees it. Most of that error list is this.
  const world = aWorld();
  run(world);
  world.chrome.runtime._id = null;
  const before = world.tried.length;

  gesture(world, JSON.stringify({ kind: "click" }));

  // Not called AT ALL, which is the half a `try` cannot give. Chrome logs an
  // unchecked `runtime.lastError` for the call itself, in the page's own
  // console, on a page an operator is working in -- and a content script that
  // has nobody to talk to should be silent rather than caught.
  assert.equal(world.tried.length, before, "an orphan went on calling out");
});

test("it announces itself on arrival", () => {
  const world = aWorld();

  run(world);

  assert.deepEqual(world.sent, [
    { kind: "content-ready", url: "https://wms.example/receiving" },
  ]);
});

test("nothing the page dispatches is trusted", () => {
  // Any script in the page can fire this event.
  const world = aWorld();
  run(world);
  world.sent.length = 0;

  gesture(world, "not json at all");
  gesture(world, JSON.stringify({ no: "kind" }));
  gesture(world, JSON.stringify("a string"));
  gesture(world, "x".repeat(128 * 1024 + 1));

  assert.deepEqual(world.sent, []);
});

for (const [name, fn] of tests) {
  try {
    await fn();
  } catch (error) {
    failed += 1;
    console.error(`  ✗ ${name}\n    ${error.message}`);
  }
}
if (failed) {
  console.error(`observe.test.mjs: ${failed} failed`);
  process.exit(1);
}
console.log(`observe.test.mjs: ok (${tests.length})`);
