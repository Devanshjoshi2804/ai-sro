// Self-check for `page-code.js`: the file the extension injects with
// `executeScript({files})` and Steel injects with `add_init_script(path=…)`.
// It is loaded here the way both of them load it -- as a classic script's own
// source, evaluated with nothing else in scope -- so what these tests exercise
// is `globalThis.sroPage`, never an import.
//
// Run with `node src/page/page-code.test.mjs`.

import assert from "node:assert/strict";
import { test } from "node:test";
import { loadSroPage, pageCodeSource as source } from "./load-sro-page.mjs";
import { lift } from "../content/evidence.test.mjs";

test("the file is a classic script: no import, no export", () => {
  assert.doesNotMatch(source, /^\s*(import|export)\s/m);
});

test("evaluated alone, it defines every function the worker calls", () => {
  const sroPage = loadSroPage();
  for (const name of ["perform", "performAt", "screenSize", "viewport", "csrfToken", "requestedWith", "send"]) {
    assert.equal(typeof sroPage[name], "function", name);
  }
});

test("re-evaluating the file in the same realm does not throw, and replaces sroPage", () => {
  // The extension re-injects on every command, into whatever document the
  // tab is currently showing -- which is the same document, most of the
  // time. A `sroPage` that could only ever be defined once would break the
  // second command of any run, so a re-evaluation must not throw.
  //
  // It must also actually REPLACE the object, not keep the first one: after
  // an extension reload or update, a document that has been open for hours
  // (an ordinary BY tab) is re-injected with today's page-code.js, and it
  // has to start running that version rather than the one it loaded an hour
  // ago. Two open documents running two different versions of the page code
  // is exactly the drift "one page-code source" (spec §6.4) exists to rule
  // out.
  const realm = {};
  const first = loadSroPage(realm);
  let second;
  assert.doesNotThrow(() => {
    second = loadSroPage(realm);
  });
  assert.notEqual(realm.sroPage, first, "the second evaluation kept the first sroPage");
  assert.equal(realm.sroPage, second);
});

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
    globalThis.document = aPage();
    globalThis.window = { getComputedStyle: () => ({ visibility: "visible", display: "block" }) };
    globalThis.location = { href: "https://wms.example/portal" };
    const sroPage = loadSroPage();
    try {
      sroPage[name](PAYLOADS[name]);
    } catch (error) {
      assert.fail(
        `sroPage.${name} cannot run in a page: ${error.message}` +
          " — it refers to something that only exists outside the injected script",
      );
    }
  }
});

// --- resolve/act/holds/hitTest: the strategy order, bounds, snapshot repair -

globalThis.getComputedStyle = () => ({ visibility: "visible", display: "block" });
globalThis.CSS = { escape: (value) => String(value) };

/** A bare element for the strategy ladder: enough shape for `roleOf`, `nameOf`,
 * `landmarksOf`, `xpathOf` and `shown` to read, with nothing pre-wired to any
 * particular strategy. */
function elem(tag, { attrs = {}, box = { x: 0, y: 0, width: 20, height: 20 }, text = "" } = {}) {
  return {
    nodeType: 1,
    tagName: tag.toUpperCase(),
    parentElement: null,
    children: [],
    innerText: text,
    disabled: false,
    getAttribute: (name) => (name in attrs ? attrs[name] : null),
    hasAttribute: (name) => name in attrs,
    getBoundingClientRect: () => ({ x: box.x, y: box.y, width: box.width, height: box.height, top: box.y, left: box.x }),
  };
}

function button(name, box) {
  return elem("button", { text: name, box });
}

/** A page whose `document.querySelectorAll` answers every selector with the
 * same flat list -- enough where only strategy ORDER is under test, since a
 * strategy earlier in the ladder that finds nothing never calls this at all.
 * Also gives every element a shared parent, so two elements of one tag get
 * two different `xpathOf` answers rather than the same one. */
function page(elements) {
  const root = elem("div", { box: { x: 0, y: 0, width: 2000, height: 2000 } });
  root.children = elements;
  for (const one of elements) one.parentElement = root;
  globalThis.document.querySelectorAll = () => elements;
}

test("a component chain wins over a css path when both match different elements", () => {
  const { resolve } = loadSroPage();
  const byChain = elem("input", { box: { x: 0, y: 0, width: 40, height: 20 } });
  const byCssPath = elem("input", { box: { x: 400, y: 0, width: 40, height: 20 } });
  page([byCssPath]);
  withExt([{ isVisible: () => true, inputEl: { dom: byChain }, el: { dom: byChain } }]);

  const found = resolve({
    target: {
      component: { chain: ["panel#clients", "textfield#code"] },
      css_path: "#stale-id-4821",
    },
  });

  assert.equal(found.strategy, "component_chain");
  assert.equal(found.candidates, 1);
});

test("the recorded bounds pick between two controls of one name", () => {
  const { resolve } = loadSroPage();
  const left = button("Save", { x: 10, y: 10, width: 60, height: 20 });
  const right = button("Save", { x: 400, y: 10, width: 60, height: 20 });
  page([left, right]);

  const found = resolve({
    target: { role: "button", name: "Save", bounds: { x: 395, y: 12, width: 60, height: 20 } },
  });

  const xpathOf = liftFromPageCode("xpathOf");
  assert.equal(found.strategy, "within_role_name");
  assert.equal(found.candidates, 2);
  assert.equal(found.xpath, xpathOf(right));
});

test("a stale css_path with a surviving name attribute resolves by attributes", () => {
  const { resolve } = loadSroPage();
  const field = elem("input", {
    attrs: { name: "clientCode" },
    box: { x: 0, y: 0, width: 80, height: 20 },
  });
  globalThis.document.querySelectorAll = (selector) =>
    selector === 'input[name="clientCode"]' ? [field] : [];

  const found = resolve({
    target: { tag: "input", attributes: { name: "clientCode" }, css_path: "#gen4821" },
  });

  assert.equal(found.strategy, "attributes");
  assert.equal(found.candidates, 1);
});

test("a control renamed and moved still resolves by repair when its role, attributes and landmarks match", () => {
  const { resolve } = loadSroPage();
  const dialog = elem("div", { attrs: { role: "dialog", "aria-label": "Customer" } });
  const liveButton = elem("button", {
    attrs: { name: "saveBtn" },
    box: { x: 900, y: 900, width: 40, height: 20 },
    text: "Save",
  });
  liveButton.parentElement = dialog;
  const CANDIDATES = "input, select, textarea, button, a, [role], [tabindex]";
  globalThis.document.querySelectorAll = (selector) => (selector === CANDIDATES ? [liveButton] : []);

  const found = resolve({
    target: {
      role: "button",
      name: "Save Changes",
      attributes: { name: "saveBtn", autocomplete: "off" },
      landmarks: [{ role: "dialog", name: "Customer" }],
      bounds: { x: 10, y: 10, width: 40, height: 20 },
    },
  });

  assert.equal(found.strategy, "repair");
  assert.equal(found.found, true);
  assert.ok(found.score >= 6, `score ${found.score} did not clear the threshold`);
});

test("a lone weak resemblance resolves nothing", () => {
  const { resolve } = loadSroPage();
  const decoy = elem("button", {
    box: { x: 900, y: 900, width: 40, height: 20 },
    text: "Something Else Entirely",
  });
  const CANDIDATES = "input, select, textarea, button, a, [role], [tabindex]";
  globalThis.document.querySelectorAll = (selector) => (selector === CANDIDATES ? [decoy] : []);

  const found = resolve({
    target: {
      role: "button",
      name: "Save Changes",
      attributes: { name: "saveBtn" },
      landmarks: [{ role: "dialog", name: "Customer" }],
      bounds: { x: 10, y: 10, width: 40, height: 20 },
    },
  });

  assert.equal(found.found, false);
  assert.equal(found.strategy, null);
  assert.equal(found.candidates, 0);
});

/** `roleOf`, lifted out of `page-code.js` by matching its braces -- the same
 * trick `roles.test.mjs` uses on the generated recorder, because this file
 * has no export either. */
function liftFromPageCode(name) {
  const at = source.indexOf(`const ${name} = (el) => {`);
  assert.notEqual(at, -1, `${name} is not in page-code.js`);
  let depth = 0;
  for (let i = source.indexOf("{", at); i < source.length; i += 1) {
    if (source[i] === "{") depth += 1;
    else if (source[i] === "}") {
      depth -= 1;
      if (depth === 0) {
        return new Function(`${source.slice(at, i + 1)}; return ${name};`)();
      }
    }
  }
  throw new Error(`${name} never closes`);
}

test("the recorder's roleOf and page code's role function agree", () => {
  // The table `roles.test.mjs` checks the recorder against, run a second time
  // against `page-code.js`'s own copy -- so the two cannot drift apart
  // without a test going red on the day they do.
  const { roleOf: recorderRoleOf } = lift(["roleOf"]);
  const pageRoleOf = liftFromPageCode("roleOf");
  const el = (tag, attrs = {}) => ({
    tagName: tag.toUpperCase(),
    getAttribute: (name) => (name in attrs ? attrs[name] : null),
    hasAttribute: (name) => name in attrs,
  });
  const cases = [
    ["div", { role: "alert" }],
    ["input", { role: "combobox" }],
    ["button", {}],
    ["a", { href: "/x" }],
    ["select", {}],
    ["textarea", {}],
    ["input", {}],
    ["input", { type: "email" }],
    ["input", { type: "checkbox" }],
    ["input", { type: "submit" }],
    ["input", { type: "password" }],
    ["div", { "aria-label": "Devansh Joshi" }],
    ["span", {}],
    ["td", {}],
    ["a", {}],
  ];
  for (const [tag, attrs] of cases) {
    const fake = el(tag, attrs);
    assert.equal(pageRoleOf(fake), recorderRoleOf(fake), `${tag} ${JSON.stringify(attrs)}`);
  }
});
