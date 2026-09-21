// The page-realm patch has to install itself on a page served over http.
//
// `crypto.randomUUID()` exists only in a SECURE context. This file runs in the
// page's own realm, so on plain http there is no such method -- and the whole
// IIFE threw on the first line that touched it, uncaught, with every patch
// below it never installed. A tab on http recorded no traffic at all and said
// so once, in a console nobody had open.
//
// Measured on this deployment 2026-09-20: the console is served over http and
// its page said `network.main.js:111 Uncaught`. A warehouse served the same
// way would have been exactly as silent.
//
// Run with `node src/content/network-main-realm.test.mjs`.

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";
import { test } from "node:test";

const here = path.dirname(fileURLToPath(import.meta.url));
const source = readFileSync(path.join(here, "network.main.js"), "utf-8");

/** The page's realm, with whatever crypto that page would have. */
function aPageWith(crypto) {
  const listeners = {};
  const sandbox = {
    crypto,
    CustomEvent: class {
      constructor(type, init) {
        this.type = type;
        this.detail = init?.detail;
      }
    },
    Event: class {},
    window: {
      fetch: async () => ({ clone: () => ({ text: async () => "" }) }),
      XMLHttpRequest: class {
        open() {}
        send() {}
        setRequestHeader() {}
        addEventListener() {}
      },
      addEventListener: (type, fn) => ((listeners[type] ||= []).push(fn), undefined),
      removeEventListener: () => {},
      dispatchEvent: () => true,
      location: { href: "http://10.11.9.25:8088/knowledge" },
    },
    document: { addEventListener: () => {}, dispatchEvent: () => true },
    performance: { now: () => 0 },
  };
  sandbox.globalThis = sandbox;
  sandbox.self = sandbox;
  return sandbox;
}

const RANDOM_BYTES = {
  getRandomValues: (into) => {
    for (let n = 0; n < into.length; n += 1) into[n] = n;
    return into;
  },
};

test("a page on http installs the patch, with no randomUUID to be had", () => {
  // Exactly what an http page offers: `getRandomValues` is not gated on a
  // secure context; `randomUUID` is.
  const page = aPageWith(RANDOM_BYTES);
  const was = page.window.fetch;

  vm.createContext(page);
  vm.runInContext(source, page);

  assert.notEqual(page.window.fetch, was, "fetch was never patched");
});

test("and on a realm with no crypto at all, rather than throwing", () => {
  // A collision is still better than no recorder.
  const page = aPageWith(undefined);
  const was = page.window.fetch;

  vm.createContext(page);
  vm.runInContext(source, page);

  assert.notEqual(page.window.fetch, was, "fetch was never patched");
});

test("two frames of one page do not share a realm id", () => {
  // The whole reason this is random: a counter plus a millisecond collides
  // across frames that load together, and two frames sending the same request
  // id is two exchanges the isolated world reads as one.
  //
  // Read off what the realm actually announces -- `say()` dispatches its id on
  // load -- rather than by reaching inside the IIFE, which holds it in a
  // closure precisely so a page cannot.
  const hello = (bytes) => {
    const said = [];
    const page = aPageWith({
      getRandomValues: (into) => {
        for (let i = 0; i < into.length; i += 1) into[i] = bytes + i;
        return into;
      },
    });
    page.window.dispatchEvent = (event) => (said.push(event), true);
    vm.createContext(page);
    vm.runInContext(source, page);
    return said.map((one) => String(one.detail)).join("|");
  };

  const one = hello(1);
  const other = hello(200);

  assert.ok(one, "the realm announced nothing at all");
  assert.notEqual(one, other, "both frames minted the same realm id");
});
