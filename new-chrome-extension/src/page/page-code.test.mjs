// Self-check for `page-code.js`: the file the extension injects with
// `executeScript({files})` and Steel injects with `add_init_script(path=…)`.
// It is loaded here the way both of them load it -- as a classic script's own
// source, evaluated with nothing else in scope -- so what these tests exercise
// is `globalThis.sroPage`, never an import.
//
// Run with `node src/page/page-code.test.mjs`.

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const source = readFileSync(fileURLToPath(new URL("./page-code.js", import.meta.url)), "utf8");

test("the file is a classic script: no import, no export", () => {
  assert.doesNotMatch(source, /^\s*(import|export)\s/m);
});

test("evaluated alone, it defines every function the worker calls", () => {
  const realm = {};
  new Function("globalThis", source)(realm);
  for (const name of ["perform", "performAt", "screenSize", "viewport", "csrfToken", "requestedWith", "send"]) {
    assert.equal(typeof realm.sroPage[name], "function", name);
  }
});

/** A fresh `sroPage`, the way each of chrome's own injections gets one: a new
 * evaluation of the same source, into whatever globals this test has set up. */
function loadSroPage() {
  new Function("globalThis", source)(globalThis);
  return globalThis.sroPage;
}

class FakeEvent {
  constructor(type, init = {}) {
    this.type = type;
    Object.assign(this, init);
  }
}
globalThis.Event = FakeEvent;
globalThis.MouseEvent = FakeEvent;
globalThis.PointerEvent = FakeEvent;
globalThis.KeyboardEvent = FakeEvent;
globalThis.FocusEvent = FakeEvent;

class HTMLInputElement {
  get value() {
    return this._value ?? "";
  }
  set value(next) {
    this._value = next;
  }
}
class HTMLTextAreaElement extends HTMLInputElement {}
globalThis.HTMLInputElement = HTMLInputElement;
globalThis.HTMLTextAreaElement = HTMLTextAreaElement;

function element({ tagName = "BUTTON", typeable = false, src, box, name = "" } = {}) {
  const el = typeable ? new HTMLInputElement() : {};
  el.tagName = tagName;
  el.innerText = name;
  el.id = "";
  el.getAttribute = () => null;
  if (src !== undefined) el.src = src;
  el.getBoundingClientRect = () => box || { left: 0, top: 0, width: 0, height: 0 };
  el.events = [];
  el.focused = 0;
  el.dispatchEvent = (event) => el.events.push(event.type);
  if (typeable) el.focus = () => (el.focused += 1);
  el.blurred = 0;
  if (typeable) el.blur = () => (el.blurred += 1);
  return el;
}

function control(tagName, name) {
  return {
    tagName,
    innerText: name,
    getAttribute: () => null,
    matches: () => false,
    dispatchEvent: () => {},
  };
}

let at = null;
let onScreen = [];
globalThis.document = {
  elementFromPoint: () => at,
  querySelectorAll: () => onScreen,
};
globalThis.window = { scrollBy: () => {} };

test("nothing at the point is a control that was not found", () => {
  const { performAt } = loadSroPage();
  at = null;
  const answer = performAt({ x: 5, y: 5, action: "click" });
  assert.equal(answer.ok, false);
  assert.equal(answer.error.kind, "control_not_found");
});

test("a point inside a frame says where the frame is, so it can be asked", () => {
  const { performAt } = loadSroPage();
  for (const tagName of ["IFRAME", "FRAME"]) {
    at = element({
      tagName,
      src: "https://wms.example/portal/app",
      box: { left: 12, top: 80, width: 900, height: 600 },
    });
    const answer = performAt({ x: 5, y: 5, action: "click" });
    assert.equal(answer.ok, false, tagName);
    assert.equal(answer.error.kind, "point_in_a_frame");
    assert.equal(answer.error.frame.src, "https://wms.example/portal/app");
    assert.equal(answer.error.frame.left, 12);
    assert.equal(answer.error.frame.top, 80);
    assert.deepEqual(at.events, [], "no event reached the frame element");
  }
});

test("what worked is named, so the job can keep it", () => {
  const { performAt } = loadSroPage();
  at = element({ tagName: "BUTTON", name: "Customer Types" });
  const answer = performAt({ x: 40, y: 30, action: "click" });

  assert.equal(answer.ok, true);
  assert.equal(answer.result.control.tag, "button");
  assert.equal(answer.result.control.name, "Customer Types");
});

test("a click is the whole pointer sequence, on the element at the point", () => {
  const { performAt } = loadSroPage();
  at = element();
  const answer = performAt({ x: 40, y: 30, action: "click" });
  assert.equal(answer.ok, true);
  assert.equal(answer.result.performed, true);
  assert.deepEqual(at.events, ["pointerdown", "mousedown", "pointerup", "mouseup", "click"]);
});

test("typing focuses the element at the point and puts the value through its setter", () => {
  const { performAt } = loadSroPage();
  at = element({ typeable: true });
  const answer = performAt({ x: 40, y: 30, action: "type", value: "ab" });
  assert.equal(answer.ok, true);
  assert.equal(at.focused, 1, "focused explicitly: a synthetic click moves no focus");
  assert.equal(at.value, "ab");
  assert.deepEqual(at.events, [
    "click", "input",
    "keydown", "input", "keyup",
    "keydown", "input", "keyup",
    "change", "focusout", "blur",
  ]);
  assert.equal(at.blurred, 1, "it typed into the field and never left it");
});

test("typing into something that cannot be typed into says so rather than performing", () => {
  const { performAt } = loadSroPage();
  at = element();
  const answer = performAt({ x: 40, y: 30, action: "type", value: "ab" });
  assert.equal(answer.ok, false);
  assert.equal(answer.error.kind, "not_actionable");
  assert.deepEqual(at.events, ["click"], "the click went; the keystrokes did not");
});

test("a press lands on the element at the point, Enter by default", () => {
  const { performAt } = loadSroPage();
  at = element({ typeable: true });
  const answer = performAt({ x: 40, y: 30, action: "press" });
  assert.equal(answer.ok, true);
  assert.equal(at.focused, 1);
  assert.deepEqual(at.events, ["keydown", "keyup"]);
});

test("an action a point cannot take is refused", () => {
  const { performAt } = loadSroPage();
  at = element();
  const answer = performAt({ x: 40, y: 30, action: "select", value: "D3" });
  assert.equal(answer.ok, false);
  assert.equal(answer.error.kind, "not_actionable");
});

test("a control that was not found says what the page does have", () => {
  const { perform } = loadSroPage();
  onScreen = [control("BUTTON", "Save and close"), control("BUTTON", "Cancel")];
  globalThis.document.querySelectorAll = () => onScreen;

  const answer = perform({
    action: "click",
    locators: [{ strategy: "role_and_name", query: "button|Save" }],
  });

  assert.equal(answer.ok, false);
  assert.equal(answer.error.kind, "control_not_found");
  assert.deepEqual(
    answer.error.nearby,
    [{ tag: "button", name: "Save and close" }],
    "Cancel is not a near miss",
  );
  assert.match(answer.error.detail, /the page has button "Save and close"/, (
    "the socket keeps a reply's kind and detail and drops the rest, so the near"
    + " miss has to be in the sentence to reach the run's record at all"
  ));
});

test("a page with nothing like it says so with an empty list, not a catalogue", () => {
  const { perform } = loadSroPage();
  onScreen = [control("BUTTON", "Cancel"), control("A", "Help")];

  const answer = perform({
    action: "click",
    locators: [{ strategy: "role_and_name", query: "button|Save" }],
  });

  assert.deepEqual(answer.error.nearby, []);
});

test("the locator path leaves the field too, not only the point path", () => {
  const { perform } = loadSroPage();
  const field = new HTMLInputElement();
  Object.assign(field, {
    tagName: "INPUT",
    innerText: "",
    id: "customerType",
    getAttribute: () => null,
    matches: (selector) => selector.includes("customerType"),
    events: [],
    focused: 0,
    blurred: 0,
    scrollIntoView: () => {},
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 80, height: 20 }),
  });
  field.dispatchEvent = (event) => field.events.push(event.type);
  field.focus = () => (field.focused += 1);
  field.blur = () => (field.blurred += 1);
  onScreen = [field];
  globalThis.document.querySelectorAll = () => onScreen;

  const answer = perform({
    action: "type",
    value: "GT2",
    locators: [{ strategy: "css_path", query: "#customerType" }],
  });

  assert.equal(answer.ok, true, JSON.stringify(answer));
  assert.equal(field.value, "GT2");
  assert.equal(field.blurred, 1, "it typed into the field and never left it");
  assert.deepEqual(field.events.slice(-3), ["change", "focusout", "blur"]);
});

test("a box that would not take what it was given says how much it kept", () => {
  const { perform } = loadSroPage();
  const field = new HTMLInputElement();
  Object.assign(field, {
    tagName: "INPUT",
    innerText: "",
    id: "longDescription",
    getAttribute: () => null,
    matches: (selector) => selector.includes("longDescription"),
    events: [],
    focused: 0,
    blurred: 0,
    scrollIntoView: () => {},
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 80, height: 20 }),
  });
  field.dispatchEvent = () => {};
  field.focus = () => (field.focused += 1);
  field.blur = () => (field.blurred += 1);
  Object.defineProperty(field, "value", {
    get() {
      return String(this._value ?? "").slice(0, 8);
    },
    configurable: true,
  });
  onScreen = [field];
  globalThis.document.querySelectorAll = () => onScreen;

  const answer = perform({
    action: "type",
    value: "a description far longer than the box",
    locators: [{ strategy: "css_path", query: "#longDescription" }],
  });

  assert.equal(answer.ok, true, JSON.stringify(answer));
  assert.equal(answer.result.short.kept, 8);
  assert.equal(answer.result.short.asked, 37);
  assert.equal(answer.result.short.truncated, true);
});

test("a box that took what it was given says nothing", () => {
  const { perform } = loadSroPage();
  const field = new HTMLInputElement();
  Object.assign(field, {
    tagName: "INPUT",
    innerText: "",
    id: "customerType",
    getAttribute: () => null,
    matches: (selector) => selector.includes("customerType"),
    scrollIntoView: () => {},
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 80, height: 20 }),
  });
  field.dispatchEvent = () => {};
  field.focus = () => {};
  field.blur = () => {};
  onScreen = [field];
  globalThis.document.querySelectorAll = () => onScreen;

  const answer = perform({
    action: "type",
    value: "GV3",
    locators: [{ strategy: "css_path", query: "#customerType" }],
  });

  assert.equal(answer.result.short, null);
});

// --- which part of a component a click lands on ------------------------------

function field({ trigger = null, composite = false, named = false } = {}) {
  const input = element({ tagName: "INPUT", typeable: true });
  input.scrollIntoView = () => {};
  if (trigger) trigger.scrollIntoView = () => {};
  const c = { isVisible: () => true, inputEl: { dom: input }, el: { dom: input } };
  if (trigger && composite) c.triggerEl = { item: (n) => (n === 0 ? { dom: trigger } : null) };
  else if (trigger && named) c.triggers = { picker: { el: { dom: trigger } } };
  else if (trigger) c.triggerEl = { dom: trigger };
  return { c, input };
}

function withExt(components) {
  globalThis.window.Ext = { ComponentQuery: { query: () => components } };
}

test("a click on a dropdown lands on its trigger, not on its text box", () => {
  const { perform } = loadSroPage();
  const arrow = element({ tagName: "DIV" });
  const { c, input } = field({ trigger: arrow });
  withExt([c]);

  const answer = perform({
    action: "click",
    locators: [{ strategy: "component", query: "combobox#createShipmentBy" }],
  });

  assert.equal(answer.ok, true);
  assert.ok(arrow.events.includes("click"), "the arrow was never clicked");
  assert.ok(!input.events.includes("click"), "the text box was clicked instead");
});

test("the trigger is found whichever shape this Ext keeps it in", () => {
  const { perform } = loadSroPage();
  for (const shape of [{ composite: true }, { named: true }]) {
    const arrow = element({ tagName: "DIV" });
    const { c } = field({ trigger: arrow, ...shape });
    withExt([c]);

    perform({
      action: "click",
      locators: [{ strategy: "component", query: "combobox#x" }],
    });

    assert.ok(arrow.events.includes("click"), `the ${Object.keys(shape)[0]} shape was missed`);
  }
});

test("a field with no trigger is still clicked where it always was", () => {
  const { perform } = loadSroPage();
  const { c, input } = field();
  withExt([c]);

  const answer = perform({
    action: "click",
    locators: [{ strategy: "component", query: "textfield#code" }],
  });

  assert.equal(answer.ok, true);
  assert.ok(input.events.includes("click"));
});

test("typing still goes to the text box, never to the trigger", () => {
  const { perform } = loadSroPage();
  const arrow = element({ tagName: "DIV" });
  const { c, input } = field({ trigger: arrow });
  withExt([c]);

  perform({
    action: "type",
    value: "NRT2",
    locators: [{ strategy: "component", query: "combobox#createShipmentBy" }],
  });

  assert.equal(input.value, "NRT2");
  assert.ok(!arrow.events.includes("click"), "the arrow was typed into");
});

test("a rung scoped to a view clicks inside that view, not the first match on the page", () => {
  const { perform } = loadSroPage();
  const elsewhere = element({ tagName: "DIV" });
  const inside = element({ tagName: "DIV" });
  for (const one of [elsewhere, inside]) one.scrollIntoView = () => {};
  onScreen = [elsewhere, inside];
  const view = { el: { dom: { contains: (el) => el === inside } } };
  withExt([view]);

  const answer = perform({
    action: "click",
    locators: [
      {
        strategy: "css_path",
        query: "div.x-grid-row-checker",
        within: "rpFilterableGrid#customer-types gridview",
      },
    ],
  });

  assert.equal(answer.ok, true);
  assert.ok(inside.events.includes("click"), "the row inside the view was never clicked");
  assert.ok(!elsewhere.events.includes("click"), "a match outside the view was clicked");
});

// --- every function survives being handed to `executeScript` alone -----------

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
  perform: { action: "click", locators: [{ strategy: "text", query: "Save" }] },
  performAt: { action: "click", x: 10, y: 10 },
  screenSize: undefined,
  viewport: undefined,
  csrfToken: { names: ["CSRF-TOKEN"] },
  requestedWith: undefined,
};

test("every sroPage function runs with nothing but the page around it", () => {
  for (const name of Object.keys(PAYLOADS)) {
    const realm = {};
    globalThis.document = aPage();
    globalThis.window = { getComputedStyle: () => ({ visibility: "visible", display: "block" }) };
    globalThis.location = { href: "https://wms.example/portal" };
    new Function("globalThis", source)(realm);
    try {
      realm.sroPage[name](PAYLOADS[name]);
    } catch (error) {
      assert.fail(
        `sroPage.${name} cannot run in a page: ${error.message}` +
          " — it refers to something that only exists outside the injected script",
      );
    }
  }
});
