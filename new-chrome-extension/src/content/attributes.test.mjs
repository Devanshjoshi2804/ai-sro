// A target's attributes reach the worker exactly as the recorder described them.
//
// Everything downstream that decides from HTML structure reads
// `target.attributes`: the menu-opening rule for a sign-out (`aria-haspopup`),
// the replayer's attribute locator (`name`, `autocomplete`, `type`), and the
// identity-field rule (`autocomplete="username"`, `type="email"`). QA found them
// empty on stored gestures (2026-09-28, F5), so this pins the extension's half
// of the path: the generated recorder's own `describe`, handed to the page-realm
// bridge, relayed by the isolated-world `observe.js`, arriving at the worker.
//
// Run with `node src/content/attributes.test.mjs`.

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const read = (name) => readFileSync(fileURLToPath(new URL(name, import.meta.url)), "utf8");
const RECORDER = read("./recorder.generated.js");
const BRIDGE = read("./recorder-bridge.main.js");
const RELAY = read("./observe.js");

function body(name) {
  const at = RECORDER.indexOf(`const ${name} = (`);
  assert.notEqual(at, -1, `${name} is not in the generated recorder`);
  let depth = 0;
  for (let i = RECORDER.indexOf("{", RECORDER.indexOf("=>", at)); i < RECORDER.length; i += 1) {
    if (RECORDER[i] === "{") depth += 1;
    else if (RECORDER[i] === "}" && (depth -= 1) === 0) return RECORDER.slice(at, i + 1);
  }
  throw new Error(`${name} never closes`);
}

/** The recorder's own `describe` and credential rule, with the locators it
 * also calls stubbed: they are not what is under test, and each is covered by
 * its own suite. */
function recorder() {
  const words = RECORDER.match(/const SECRET_WORDS = new Set\((\[.*?\])\);/);
  const globals = {
    SECRET_WORDS: new Set(JSON.parse(words[1])),
    wordsOf: (text) =>
      String(text || "")
        .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
        .split(/[^A-Za-z]+/)
        .filter(Boolean)
        .map((word) => word.toLowerCase()),
    roleOf: () => null,
    label: () => null,
    requiredOf: () => null,
    cssPath: () => "form > input",
    xpathOf: () => "/html/body/form/input",
    boundsOf: () => ({ x: 0, y: 0, width: 200, height: 30 }),
    component: () => null,
    landmarksOf: () => [],
    labelOf: () => "",
    fullNameOf: () => null,
    siblingOf: () => ({ index: 0, count: 1 }),
  };
  const names = ["isSecretName", "drawnMasked", "labelledText", "isSecretField", "describe"];
  return new Function(
    ...Object.keys(globals),
    `const MAX_TEXT = 200; ${names.map(body).join(";\n")}; return { describe };`,
  )(...Object.values(globals));
}

/** An element as the DOM hands it to `describe`: `attributes` is the
 * NamedNodeMap, iterated as `{name, value}` pairs. */
const element = (tag, attrs) => ({
  nodeType: 1,
  tagName: tag.toUpperCase(),
  attributes: Object.entries(attrs).map(([name, value]) => ({ name, value })),
  getAttribute: (name) => (name in attrs ? attrs[name] : null),
  hasAttribute: (name) => name in attrs,
  type: attrs.type,
  name: attrs.name,
  id: attrs.id,
  innerText: "",
});

/** One window both realms share, as the page's and the isolated world's do:
 * the bridge and the relay meet only over its events. */
function aWorld() {
  const sent = [];
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
    location: { href: "https://accounts.example/signin" },
    CustomEvent: class {
      constructor(type, init) {
        this.type = type;
        this.detail = init?.detail;
      }
    },
    chrome: {
      runtime: {
        id: "ext-1",
        sendMessage: (message) => {
          sent.push(message);
          return Promise.resolve({ ok: true });
        },
      },
    },
    sent,
    // Serialised, as `chrome.runtime.sendMessage` serialises: the worker
    // receives JSON, not the sandbox's objects.
    gestures: () =>
      JSON.parse(JSON.stringify(sent.filter((message) => message.kind === "gesture"))),
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(BRIDGE, sandbox);
  vm.runInContext(RELAY, sandbox);
  return sandbox;
}

/** What `emit` hands the bridge for a `change`, minus the page-state fields. */
const typed = (target) =>
  JSON.stringify({ kind: "type", target, value: null, secret: target.secret, modifiers: [], ref: "r.1", at: 1, url: "https://accounts.example/signin" });

test("an identity field's attributes arrive at the worker", () => {
  const { describe } = recorder();
  const world = aWorld();
  const email = element("input", {
    id: "identifierId",
    type: "email",
    name: "identifier",
    autocomplete: "username",
    "aria-haspopup": "true",
  });

  world.window.__sroRecord(typed(describe(email)));

  assert.equal(world.gestures().length, 1);
  assert.deepEqual(world.gestures()[0].gesture.target.attributes, {
    id: "identifierId",
    type: "email",
    name: "identifier",
    autocomplete: "username",
    "aria-haspopup": "true",
  });
});

test("a credential field keeps its attributes and never its value", () => {
  const { describe } = recorder();
  const world = aWorld();
  const password = element("input", {
    type: "password",
    name: "Passwd",
    autocomplete: "current-password",
    value: "hunter2",
  });

  world.window.__sroRecord(typed(describe(password)));

  const target = world.gestures()[0].gesture.target;
  assert.equal(target.secret, true);
  assert.deepEqual(target.attributes, {
    type: "password",
    name: "Passwd",
    autocomplete: "current-password",
  });
  assert.equal(JSON.stringify(world.sent).includes("hunter2"), false);
});
