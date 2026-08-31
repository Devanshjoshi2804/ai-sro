// Self-check for the page-realm patch surviving an extension reload.
//
// Reloading the extension leaves the patch on `window.fetch` exactly where it
// was -- a replacement emits its records as CustomEvents, which need nothing
// from the extension that installed it. What does not survive is the
// handshake: the isolated half is replaced by a fresh one that knows no realm,
// and the page-realm half that could tell it is the *old* one, which answered
// its single hello long ago and stopped listening.
//
// So every call went on being emitted and every one was dropped on arrival. A
// reloaded extension recorded gestures and no calls at all, silently, until the
// page next navigated -- long enough to teach a skill that asserts nothing
// about the system it changes.
//
// This runs network.main.js twice in one realm, which is what a re-injection
// does, and checks that the second run speaks for the patch the first left.
//
// Run with `node src/content/reintroducing-the-patch.test.mjs`.

import assert from "node:assert";
import vm from "node:vm";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import crypto from "node:crypto";

const here = path.dirname(fileURLToPath(import.meta.url));
const SOURCE = readFileSync(path.join(here, "network.main.js"), "utf-8");

/** A page realm: the DOM event bus both halves share, and nothing else. */
function page() {
  const listeners = {};
  const said = [];
  const sandbox = {
    window: {
      fetch: async () => ({}),
      XMLHttpRequest: function XMLHttpRequest() {},
      addEventListener: (type, fn) => {
        (listeners[type] ||= []).push(fn);
      },
      removeEventListener: (type, fn) => {
        listeners[type] = (listeners[type] || []).filter((each) => each !== fn);
      },
      dispatchEvent: (event) => {
        if (event.type === "sro:hello") said.push(event.detail);
        for (const fn of [...(listeners[event.type] || [])]) fn(event);
        return true;
      },
    },
    CustomEvent: class {
      constructor(type, init) {
        this.type = type;
        this.detail = init?.detail;
      }
    },
    crypto: { randomUUID: () => crypto.randomUUID() },
    performance: { now: () => 0 },
    Response, Request, Headers, URL, URLSearchParams, TextEncoder, TextDecoder,
    setTimeout, clearTimeout, AbortController,
    console: { debug() {}, warn() {} },
    said,
  };
  sandbox.window.XMLHttpRequest.prototype = { open() {}, send() {}, setRequestHeader() {} };
  sandbox.globalThis = sandbox;
  sandbox.self = sandbox;
  vm.createContext(sandbox);
  return sandbox;
}

const realm = new vm.Script(SOURCE);

// First run: patches, and announces itself once.
const world = page();
realm.runInContext(world);
const first = [...world.said];
assert.equal(first.length, 1, "the patch did not announce itself on install");
assert.ok(first[0], "the announced realm is empty");
const patched = world.window.fetch;

// The reload. Same realm, same page, the file executed again.
world.said.length = 0;
realm.runInContext(world);

// It did not wrap its own wrapper -- that was the bug the guard exists for, and
// it reported every call twice.
assert.equal(world.window.fetch, patched, "the second run re-patched an already-patched fetch");

// It spoke for the patch that is there, with that patch's realm. A fresh realm
// would be answering on behalf of a patch that signs its records with another,
// which reads to the isolated half exactly like a forgery.
assert.deepEqual(world.said, [first[0]], "the second run did not re-introduce the existing patch");

// And it keeps listening. This run exists because an isolated half turned up
// late; there is no reason to assume it is the last one to.
//
// More than one answer is fine and expected -- the first run's own responder is
// still armed, having never been asked -- because the isolated half latches the
// first realm it is told and stops listening. What would not be fine is two
// *different* realms, so that is what this checks rather than the count.
world.said.length = 0;
world.window.dispatchEvent(new world.CustomEvent("sro:need-hello"));
assert.ok(world.said.length > 0, "a later hello went unanswered");
assert.deepEqual([...new Set(world.said)], [first[0]], "a later hello was answered with a realm the patch does not sign with");

console.log("reintroducing-the-patch.test.mjs: ok");
