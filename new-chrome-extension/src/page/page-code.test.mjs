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

function fakeInput({ type = "text", autocomplete = "", hidden = false, visibility = "visible" } = {}) {
  return {
    type,
    computed: { visibility, display: "block" },
    getAttribute: (name) => (name === "autocomplete" ? autocomplete : null),
    getBoundingClientRect: () => (hidden ? { width: 0, height: 0 } : { width: 10, height: 10 }),
  };
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

  assert.equal(found.strategy, "within_role_name");
  assert.equal(found.candidates, 2);
  assert.equal(found.xpath, "/div/button[2]");
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

// --- snapshot repair: kind and scope are gates, and a write is never repaired -

const CANDIDATE_SELECTOR = "input, select, textarea, button, a, [role], [tabindex]";

/** An element that can hold children and be typed into -- enough of a node
 * for every reader `resolve`, `act` and `holds` use. */
function node(tag, { attrs = {}, box = { x: 0, y: 0, width: 40, height: 20 }, text = "", children = [] } = {}) {
  const el = tag === "input" ? new HTMLInputElement() : {};
  Object.assign(el, elem(tag, { attrs, box, text }));
  el.children = children;
  el.type = attrs.type || "";
  el.focus = () => {};
  el.blur = () => {};
  el.scrollIntoView = () => {};
  el.dispatchEvent = () => true;
  el.moveTo = (next) => {
    el.getBoundingClientRect = () => ({ ...next, top: next.y, left: next.x });
  };
  el.contains = (other) => other === el || below(el).includes(other);
  el.closest = (selector) => {
    for (let here = el; here; here = here.parentElement) {
      if (matching([here], selector).length) return here;
    }
    return null;
  };
  return el;
}

const below = (el) => el.children.flatMap((child) => [child, ...below(child)]);
const candidate = (el) =>
  ["input", "select", "textarea", "button", "a"].includes(el.tagName.toLowerCase()) ||
  el.hasAttribute("role") ||
  el.hasAttribute("tabindex");
const matching = (els, selector) =>
  selector === "*" ? els : selector === CANDIDATE_SELECTOR ? els.filter(candidate) : [];

/** A real tree: parents linked, and `querySelectorAll` answering the two
 * selectors the repair path asks (`*` and the candidate list) from it, and
 * nothing for any other -- the same answer a real DOM gives these pages,
 * since none of their elements carries a name, autocomplete, id or test id
 * an earlier strategy would find. */
function mount(root) {
  const link = (el) => {
    for (const child of el.children) {
      child.parentElement = el;
      link(child);
    }
  };
  link(root);
  for (const el of [root, ...below(root)]) el.querySelectorAll = (s) => matching(below(el), s);
  globalThis.document.querySelectorAll = (s) => matching([root, ...below(root)], s);
  globalThis.document.evaluate = undefined;
}

const RENAMED = {
  role: "textbox",
  name: "Client",
  attributes: { placeholder: "Enter code" },
  landmarks: [{ role: "form", name: "Customer" }],
  bounds: { x: 10, y: 10, width: 40, height: 20 },
};

function customerForm(...fields) {
  const form = node("form", { attrs: { "aria-label": "Customer" }, children: fields });
  mount(node("body", { children: [form] }));
  return form;
}

test("a read repairs a renamed control when its kind, its scope and more of it agree", () => {
  const { resolve } = loadSroPage();
  customerForm(
    node("input", { attrs: { "aria-label": "Client code", placeholder: "Enter code" }, box: { x: 12, y: 10, width: 40, height: 20 } }),
    node("input", { attrs: { "aria-label": "Notes" }, box: { x: 600, y: 600, width: 40, height: 20 } }),
  );

  const found = resolve({ write: false, action: "click", target: RENAMED });

  assert.equal(found.strategy, "repair");
  assert.equal(found.xpath, "/body/form[1]/input[1]");
});

test("a write is never repaired: every strategy missing leaves nothing to act on", () => {
  const { resolve, act } = loadSroPage();
  const renamed = node("input", {
    attrs: { "aria-label": "Client code", placeholder: "Enter code" },
    box: { x: 12, y: 10, width: 40, height: 20 },
  });
  customerForm(renamed);

  assert.equal(resolve({ write: true, target: RENAMED }).found, false);
  assert.equal(resolve({ target: RENAMED }).found, false, "a payload that does not say it reads is a write");
  const answer = act({ action: "type", value: "X9", write: true, target: RENAMED });
  assert.equal(answer.ok, false);
  assert.equal(answer.error.kind, "control_not_found");
  assert.equal(renamed.value, "", "the write reached a repaired control");
});

test("repair never picks a control of another kind", () => {
  const { resolve } = loadSroPage();
  customerForm(
    node("input", { attrs: { "aria-label": "Client" }, box: { x: 600, y: 600, width: 40, height: 20 } }),
    node("button", { text: "Customer", box: { x: 10, y: 10, width: 40, height: 20 } }),
  );

  const found = resolve({ write: false, target: { ...RENAMED, name: "Customer" } });

  assert.equal(found.found, false, `repair chose ${found.xpath}`);
});

test("repair never picks the same name in another landmark: Delete in the Orders section", () => {
  const { resolve } = loadSroPage();
  const orders = node("section", {
    attrs: { "aria-label": "Orders" },
    children: [node("button", { text: "Delete", box: { x: 10, y: 10, width: 40, height: 20 } })],
  });
  mount(node("body", { children: [orders] }));

  const found = resolve({
    write: false,
    target: {
      role: "button",
      name: "Delete",
      landmarks: [{ role: "dialog", name: "Confirm delete" }],
      bounds: { x: 10, y: 10, width: 40, height: 20 },
    },
  });

  assert.equal(found.found, false, `repair chose ${found.xpath}`);
});

test("two controls that resemble the evidence equally are refused, not guessed between", () => {
  const { resolve } = loadSroPage();
  const twin = () => node("input", { attrs: { "aria-label": "Client code", placeholder: "Enter code" }, box: { x: 600, y: 600, width: 40, height: 20 } });
  customerForm(twin(), twin());

  assert.equal(resolve({ write: false, target: RENAMED }).found, false);
});

test("a near tie is refused and a clear lead is taken", () => {
  const { resolve } = loadSroPage();
  const best = { attrs: { "aria-label": "Client code", placeholder: "Enter code" }, box: { x: 12, y: 10, width: 40, height: 20 } };
  const far = { x: 600, y: 600, width: 40, height: 20 };

  customerForm(node("input", best), node("input", { attrs: { "aria-label": "Client ref", placeholder: "Enter code" }, box: far }));
  assert.equal(resolve({ write: false, target: RENAMED }).found, false, "3 against 2 was taken");

  customerForm(node("input", best), node("input", { attrs: { "aria-label": "Notes", placeholder: "Enter code" }, box: far }));
  const found = resolve({ write: false, action: "click", target: RENAMED });
  assert.equal(found.strategy, "repair", "3 against 1 was refused");
  assert.equal(found.xpath, "/body/form[1]/input[1]");
});

test("repair never types: a renamed Quantity field is left alone on a type action", () => {
  const { resolve, act } = loadSroPage();
  const qty = { attrs: { "aria-label": "Quantity to cancel", placeholder: "0" }, box: { x: 10, y: 10, width: 40, height: 20 } };
  const form = () => node("form", { attrs: { "aria-label": "Order" }, children: [node("input", qty)] });
  mount(node("body", { children: [form()] }));
  const target = {
    role: "textbox",
    name: "Quantity",
    attributes: { placeholder: "0" },
    landmarks: [{ role: "form", name: "Order" }],
    bounds: { x: 10, y: 10, width: 40, height: 20 },
  };

  const found = resolve({ write: false, action: "type", target });
  assert.equal(found.found, false, `repair chose ${found.xpath}`);

  const answer = act({ action: "type", value: "50", write: false, target });
  assert.equal(answer.ok, false);
  assert.equal(answer.error.kind, "control_not_found");
});

test("repair never selects or toggles a checkbox", () => {
  const { resolve } = loadSroPage();
  const box = node("input", {
    attrs: { type: "checkbox", "aria-label": "Include cancelled orders", placeholder: "cancelled" },
    box: { x: 10, y: 10, width: 16, height: 16 },
  });
  mount(node("body", { children: [box] }));
  const target = {
    role: "checkbox",
    name: "Include",
    attributes: { placeholder: "cancelled" },
    bounds: { x: 10, y: 10, width: 16, height: 16 },
  };

  const found = resolve({ write: false, action: "click", target });

  assert.equal(found.found, false, `repair chose ${found.xpath}`);
});

// --- act pins what it touched, and holds checks exactly that -----------------

test("after act scrolls, holds still checks the Qty field it typed into, not the other one", () => {
  const { act, holds } = loadSroPage();
  const first = node("input", { attrs: { "aria-label": "Qty" }, box: { x: 10, y: 100, width: 40, height: 20 } });
  const second = node("input", { attrs: { "aria-label": "Qty" }, box: { x: 10, y: 900, width: 40, height: 20 } });
  second.value = "7";
  mount(node("body", { children: [first, second] }));
  first.scrollIntoView = () => {
    first.moveTo({ x: 10, y: -700, width: 40, height: 20 });
    second.moveTo({ x: 10, y: 100, width: 40, height: 20 });
  };
  const target = { role: "textbox", name: "Qty", bounds: { x: 10, y: 100, width: 40, height: 20 } };

  const answer = act({ action: "type", value: "9", write: true, target });

  assert.equal(answer.ok, true);
  assert.equal(first.value, "9");
  assert.equal(answer.repaired, false);
  assert.ok(answer.pin, "act handed back nothing to pin the control by");
  assert.deepEqual(holds({ pin: answer.pin, expect: { value: "9" } }), { repaired: false });
  assert.equal(holds({ pin: answer.pin, expect: { value: "7" } }), null, "held the other Qty field");
  assert.equal(holds({ target, expect: { value: "7" } }), null, "re-resolved without a pin");
});

test("holds says no once the control it pinned has left the page", () => {
  const { act, holds } = loadSroPage();
  const field = node("input", { attrs: { "aria-label": "Qty" } });
  mount(node("body", { children: [field] }));
  const answer = act({ action: "type", value: "9", target: { role: "textbox", name: "Qty" } });

  field.isConnected = false;

  assert.equal(holds({ pin: answer.pin, expect: { value: "9" } }), null);
});

test("act never throws: typing into something that is not a field is an answer", () => {
  const { act } = loadSroPage();
  const div = node("div", { attrs: { role: "textbox", "aria-label": "Qty" } });
  div.focus = () => {
    throw new TypeError("Illegal invocation");
  };
  mount(node("body", { children: [div] }));

  const answer = act({ action: "type", value: "9", target: { role: "textbox", name: "Qty" } });

  assert.equal(answer.ok, false);
  assert.equal(answer.error.kind, "not_actionable");
});

// --- bounds are page coordinates -----------------------------------------------

test("bounds recorded at the top of the page still pick the top control after a scroll", () => {
  const { resolve } = loadSroPage();
  const top = node("button", { text: "Save", box: { x: 10, y: 100 - 1700, width: 60, height: 20 } });
  const low = node("button", { text: "Save", box: { x: 10, y: 1800 - 1700, width: 60, height: 20 } });
  mount(node("body", { children: [top, low] }));
  globalThis.window.scrollX = 0;
  globalThis.window.scrollY = 1700;
  try {
    const found = resolve({
      target: { role: "button", name: "Save", bounds: { x: 10, y: 100, width: 60, height: 20 } },
    });
    assert.equal(found.xpath, "/body/button[1]");
  } finally {
    globalThis.window.scrollY = 0;
  }
});

// --- an ExtJS combo box opens by its trigger on the strategy ladder too -------

test("the Create Shipment By list opens: a component-chain click lands on its trigger", () => {
  const { act } = loadSroPage();
  const arrow = node("div", { box: { x: 60, y: 0, width: 20, height: 20 } });
  const input = node("input", { box: { x: 0, y: 0, width: 60, height: 20 } });
  let opened = false;
  arrow.dispatchEvent = (event) => {
    if (event.type === "click") opened = true;
    return true;
  };
  const combo = { isVisible: () => true, inputEl: { dom: input }, el: { dom: input }, triggerEl: { dom: arrow } };
  globalThis.window.Ext = { ComponentQuery: { query: () => [combo] } };
  try {
    const answer = act({
      action: "click",
      target: { component: { chain: ["form#shipment", "combobox#createShipmentBy"] } },
    });
    assert.equal(answer.ok, true);
    assert.equal(answer.matched_by, "component_chain");
    assert.ok(opened, "the list's trigger was never clicked");
  } finally {
    delete globalThis.window.Ext;
  }
});

// --- a sight hit holds only when the recorded locator IS the control it hit --

test("a hit on a button's inner span confirms the recorded button", () => {
  const realm = {};
  const { holds } = loadSroPage(realm);
  const label = node("span", {});
  mount(node("body", { children: [node("button", { attrs: { "aria-label": "Save" }, children: [label] })] }));
  realm.__sroHits = new Map([["p-save", label]]);

  const held = holds({ pin: "p-save", action: "click", target: { role: "button", name: "Save" }, expect: {} });

  assert.deepEqual(held, { repaired: false });
});

test("a container locator never confirms a click on the wrong child inside it", () => {
  const realm = {};
  const { holds } = loadSroPage(realm);
  const cell = node("span", {});
  const wrong = node("div", { attrs: { role: "row", "aria-label": "456" }, children: [cell] });
  const right = node("div", { attrs: { role: "row", "aria-label": "123" } });
  const grid = node("div", { attrs: { role: "grid", "aria-label": "Orders" }, children: [right, wrong] });
  mount(node("body", { children: [grid] }));
  realm.__sroHits = new Map([["p-row", cell]]);

  const held = holds({ pin: "p-row", action: "click", target: { role: "grid", name: "Orders" }, expect: {} });

  assert.equal(held, null, "the grid confirmed a click on row 456");
});

// --- hitTest teaches only locators that find the element -----------------------

test("hitTest names an ExtJS button by its component, not the span under the point", () => {
  const { hitTest } = loadSroPage();
  const inner = node("span", { attrs: {} });
  inner.id = "button-1012-btnInnerEl";
  const btn = node("a", { children: [node("span", { children: [inner] })] });
  btn.id = "button-1012";
  mount(node("body", { children: [btn] }));
  const cmp = { itemId: "saveButton", xtype: "button", isVisible: () => true, btnEl: { dom: btn } };
  globalThis.window.Ext = {
    getCmp: (id) => (id === "button-1012" ? cmp : undefined),
    ComponentQuery: { query: (q) => (q === "#saveButton" ? [cmp] : []) },
  };
  globalThis.document.elementFromPoint = () => inner;
  try {
    const taught = hitTest(5, 5);
    assert.equal(taught.strategy, "component");
    assert.equal(taught.query, "#saveButton");
    assert.deepEqual(taught.frame_path, []);
  } finally {
    delete globalThis.window.Ext;
    globalThis.document.elementFromPoint = () => at;
  }
});

test("hitTest refuses to teach an xpath that finds nothing", () => {
  const { hitTest } = loadSroPage();
  const lone = node("div", {});
  mount(node("body", { children: [lone] }));
  globalThis.document.elementFromPoint = () => lone;
  globalThis.document.evaluate = () => ({ snapshotLength: 0, snapshotItem: () => null });
  globalThis.XPathResult = { ORDERED_NODE_SNAPSHOT_TYPE: 7 };
  try {
    assert.equal(hitTest(5, 5), null);
  } finally {
    globalThis.document.elementFromPoint = () => at;
  }
});

// --- signals: what the page shows, never what was typed into it --------------

test("the page says what credential inputs it shows", () => {
  const { signals } = loadSroPage();
  globalThis.document.querySelectorAll = () => [
    fakeInput({ type: "password", autocomplete: "current-password" }),
    fakeInput({ type: "text", autocomplete: "username" }),
    fakeInput({ type: "text", hidden: true, autocomplete: "one-time-code" }),
  ];
  try {
    assert.deepEqual(signals(), { password: true, autocomplete: ["current-password", "username"] });
  } finally {
    globalThis.document.querySelectorAll = () => onScreen;
  }
});

test("a visibility:hidden password field is not shown", () => {
  const { signals } = loadSroPage();
  const style = globalThis.getComputedStyle;
  globalThis.getComputedStyle = (el) => el.computed ?? style(el);
  globalThis.document.querySelectorAll = () => [fakeInput({ type: "password", visibility: "hidden" })];
  try {
    assert.deepEqual(signals(), { password: false, autocomplete: [] });
  } finally {
    globalThis.getComputedStyle = style;
    globalThis.document.querySelectorAll = () => onScreen;
  }
});

test("autocomplete is read as a token list, and a new-password field is no prompt", () => {
  const { signals } = loadSroPage();
  globalThis.document.querySelectorAll = () => [
    fakeInput({ type: "text", autocomplete: "section-login Username webauthn" }),
    fakeInput({ type: "password", autocomplete: "new-password" }),
  ];
  try {
    assert.deepEqual(signals(), { password: false, autocomplete: ["section-login", "username", "webauthn", "new-password"] });
  } finally {
    globalThis.document.querySelectorAll = () => onScreen;
  }
});

test("a hidden password field is not shown, and a page with none reports none", () => {
  const { signals } = loadSroPage();
  globalThis.document.querySelectorAll = () => [fakeInput({ type: "password", hidden: true })];
  try {
    assert.deepEqual(signals(), { password: false, autocomplete: [] });
  } finally {
    globalThis.document.querySelectorAll = () => onScreen;
  }
});

test("the page code can outline the live screen", () => {
  assert.equal(typeof loadSroPage().outline, "function");
});

test("resolve reads the value the one control holds, never a password's", () => {
  const { resolve } = loadSroPage();
  const chosen = Object.assign(elem("select", { attrs: { name: "department" } }), { value: "3" });
  const secret = Object.assign(elem("input", { attrs: { name: "pw" } }), { value: "hunter2", type: "password" });

  page([chosen]);
  assert.equal(resolve({ target: { attributes: { name: "department" } } }).held, "3");
  page([secret]);
  assert.equal(resolve({ target: { attributes: { name: "pw" } } }).held, null);
  page([]);
  assert.equal(resolve({ target: { attributes: { name: "department" } } }).held, null);
});

for (const [rule, attrs, props] of [
  ["a card number", { autocomplete: "cc-number" }, {}],
  ["a card code", { autocomplete: "cc-csc" }, {}],
  ["a one-time code", { autocomplete: "one-time-code" }, {}],
  ["a password by its autocomplete", { autocomplete: "current-password" }, {}],
  ["a secret-named id", {}, { id: "apiToken" }],
  ["a secret-named aria-label", { "aria-label": "Security PIN" }, {}],
]) {
  test(`resolve never reads the value of ${rule}`, () => {
    const { resolve, act } = loadSroPage();
    const field = Object.assign(elem("input", { attrs: { name: "field", ...attrs } }), {
      value: "4111111111111111",
      type: "text",
      ...props,
    });
    page([field]);

    assert.equal(resolve({ target: { attributes: { name: "field" } } }).held, null);
    const acted = act({ action: "click", target: { attributes: { name: "field" } } });
    assert.equal(acted.state?.value ?? null, null);
  });
}
