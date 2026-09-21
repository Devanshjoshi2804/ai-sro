// Self-check for `performAtInPage`: the half of the sight rung that runs
// inside the page. It is handed to `executeScript` as source, so it reaches
// only what a page has -- `document.elementFromPoint`, the event classes, the
// input prototypes -- and every one of those is faked here, minimally, so the
// question the test asks is "which events reach which element", not "does a
// DOM exist". Run with `node src/background/in-page.test.mjs`.

import assert from "node:assert/strict";
import test from "node:test";

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
globalThis.window = { scrollBy: () => {} };

// The two input prototypes `type` writes through. A `value` accessor on the
// prototype is what the page code looks up; the fake keeps the field itself.
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
  // Every element a page script touches can be asked about its attributes;
  // the naming a successful command reports back reads three of them.
  el.getAttribute = () => null;
  if (src !== undefined) el.src = src;
  // Only a frame is measured, and only by the branch that hands its position
  // to the worker.
  el.getBoundingClientRect = () => box || { left: 0, top: 0, width: 0, height: 0 };
  el.events = [];
  el.focused = 0;
  el.dispatchEvent = (event) => el.events.push(event.type);
  if (typeable) el.focus = () => (el.focused += 1);
  // Left as well as entered: a field commits its value to the framework behind
  // it when it is blurred, and nothing here did that until 2026-09-17.
  el.blurred = 0;
  if (typeable) el.blur = () => (el.blurred += 1);
  return el;
}

let at = null;
let onScreen = [];
globalThis.document = {
  elementFromPoint: () => at,
  querySelectorAll: () => onScreen,
};

const { performAtInPage, performInPage } = await import("./in-page.js");

/** A control on the page, as `nearMisses` reads one. */
function control(tagName, name) {
  return {
    tagName,
    innerText: name,
    getAttribute: () => null,
    matches: () => false,
    dispatchEvent: () => {},
  };
}

test("nothing at the point is a control that was not found", () => {
  at = null;
  const answer = performAtInPage({ x: 5, y: 5, action: "click" });
  assert.equal(answer.ok, false);
  assert.equal(answer.error.kind, "control_not_found");
});

test("a point inside a frame says where the frame is, so it can be asked", () => {
  // The picture the model is shown is the top document's viewport, and a
  // warehouse application inside an iframe puts every control in another
  // document: the point is right and the document is wrong. Firing here would
  // hit the frame element, reach nothing, and report `performed`.
  //
  // Measured on the deployment, 2026-09-17: the rung that looks at a picture
  // finally pointed at a control and got "that point is inside a frame", which
  // made it useless on the one system it exists for.
  for (const tagName of ["IFRAME", "FRAME"]) {
    at = element({
      tagName,
      src: "https://wms.example/portal/app",
      box: { left: 12, top: 80, width: 900, height: 600 },
    });
    const answer = performAtInPage({ x: 5, y: 5, action: "click" });
    assert.equal(answer.ok, false, tagName);
    assert.equal(answer.error.kind, "point_in_a_frame");
    assert.equal(answer.error.frame.src, "https://wms.example/portal/app");
    assert.equal(answer.error.frame.left, 12);
    assert.equal(answer.error.frame.top, 80);
    assert.deepEqual(at.events, [], "no event reached the frame element");
  }
});

test("what worked is named, so the job can keep it", () => {
  // A step whose recorded identity has rotted is found by a rung further down
  // -- text, a css path, a point on a picture -- and that discovery used to
  // live for exactly one command. Measured on the deployment, 2026-09-17: the
  // rung that looks at a picture worked out "Customer Types is under Partners"
  // three times in one afternoon, and the job knew no more at the end of it.
  // Through the point, which is the expensive rung: a model looked at a
  // picture to find this control, and naming it is what lets the next run
  // find it with a locator instead of another picture.
  at = element({ tagName: "BUTTON", name: "Customer Types" });
  const answer = performAtInPage({ x: 40, y: 30, action: "click" });

  assert.equal(answer.ok, true);
  assert.equal(answer.result.control.tag, "button");
  assert.equal(answer.result.control.name, "Customer Types");
});

test("a click is the whole pointer sequence, on the element at the point", () => {
  at = element();
  const answer = performAtInPage({ x: 40, y: 30, action: "click" });
  assert.equal(answer.ok, true);
  assert.equal(answer.result.performed, true);
  assert.deepEqual(at.events, ["pointerdown", "mousedown", "pointerup", "mouseup", "click"]);
});

test("typing focuses the element at the point and puts the value through its setter", () => {
  at = element({ typeable: true });
  const answer = performAtInPage({ x: 40, y: 30, action: "type", value: "ab" });
  assert.equal(answer.ok, true);
  assert.equal(at.focused, 1, "focused explicitly: a synthetic click moves no focus");
  assert.equal(at.value, "ab");
  // click, cleared (input), then per character keydown/input/keyup, then
  // change -- and then LEFT, which is when a field commits its value to the
  // framework behind it. Measured on the deployment, 2026-09-17 at 23:40:
  // `run_6ddc89d5` typed GT2, the screen showed GT2, and the Save came back
  // "a validation error on Customer Type" because ExtJS still held the empty
  // value it had never been told to replace. A person never hits this: their
  // click on the next control blurs the last one, and a synthetic click moves
  // no focus.
  assert.deepEqual(at.events, [
    "click", "input",
    "keydown", "input", "keyup",
    "keydown", "input", "keyup",
    "change", "focusout", "blur",
  ]);
  assert.equal(at.blurred, 1, "it typed into the field and never left it");
});

test("typing into something that cannot be typed into says so rather than performing", () => {
  at = element();
  const answer = performAtInPage({ x: 40, y: 30, action: "type", value: "ab" });
  assert.equal(answer.ok, false);
  assert.equal(answer.error.kind, "not_actionable");
  assert.deepEqual(at.events, ["click"], "the click went; the keystrokes did not");
});

test("a press lands on the element at the point, Enter by default", () => {
  at = element({ typeable: true });
  const answer = performAtInPage({ x: 40, y: 30, action: "press" });
  assert.equal(answer.ok, true);
  assert.equal(at.focused, 1);
  assert.deepEqual(at.events, ["keydown", "keyup"]);
});

test("an action a point cannot take is refused", () => {
  at = element();
  const answer = performAtInPage({ x: 40, y: 30, action: "select", value: "D3" });
  assert.equal(answer.ok, false);
  assert.equal(answer.error.kind, "not_actionable");
});

test("a control that was not found says what the page does have", () => {
  // "no control matched: role_and_name=button|Save, css_path=..." says what
  // was tried and nothing about what is there. A screen whose Save became
  // "Save and close" read as a screen with no Save at all -- to the person
  // reading the run, and to the model asked to rescue the step.
  onScreen = [control("BUTTON", "Save and close"), control("BUTTON", "Cancel")];
  globalThis.document.querySelectorAll = () => onScreen;

  const answer = performInPage({
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
  onScreen = [control("BUTTON", "Cancel"), control("A", "Help")];

  const answer = performInPage({
    action: "click",
    locators: [{ strategy: "role_and_name", query: "button|Save" }],
  });

  assert.deepEqual(answer.error.nearby, []);
});

test("the locator path leaves the field too, not only the point path", () => {
  // The path a run actually takes. `run_6ddc89d5`, the deployment,
  // 2026-09-17 at 23:40, matched `component` -- which is `performInPage`, not
  // `performAtInPage` -- typed GT2, showed GT2 on the screen, and had the Save
  // refused with "a validation error on Customer Type". The framework behind
  // the box keeps its own value and takes the DOM's when the field is LEFT,
  // and nothing here ever left it.
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

  const answer = performInPage({
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
  // The browser truncates silently and BEFORE the request. On the deployment
  // `Warehouse.Description` stops at about 28 characters with no error and no
  // warning, so the shortened value is what goes into the body, comes back
  // from the read, and appears in the photograph. Every belt the run has
  // agrees, because every one of them compares the record to itself. This is
  // the only moment the difference exists.
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
  // A field with a maxlength keeps a prefix and drops the rest, exactly as a
  // real one does. Modelled on the READ rather than the write, because the
  // page code assigns through the PROTOTYPE's setter -- deliberately, so a
  // framework watching the property sees the change -- and an instance setter
  // would never be called.
  Object.defineProperty(field, "value", {
    get() {
      return String(this._value ?? "").slice(0, 8);
    },
    configurable: true,
  });
  onScreen = [field];
  globalThis.document.querySelectorAll = () => onScreen;

  const answer = performInPage({
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

  const answer = performInPage({
    action: "type",
    value: "GV3",
    locators: [{ strategy: "css_path", query: "#customerType" }],
  });

  assert.equal(answer.result.short, null);
});

// --- which part of a component a click lands on ------------------------------

/** An Ext field, as `ComponentQuery` hands one back. */
function field({ trigger = null, composite = false, named = false } = {}) {
  const input = element({ tagName: "INPUT", typeable: true });
  // `act` scrolls a control into view before it touches it; the point-path
  // fixtures above never reach that line, so the fake has no such method.
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
  // Measured on the deployment 2026-09-22. `Click the Create Shipment By
  // dropdown` landed every time -- ok: true, matched_by: component -- and the
  // list never opened, so the step after it had no option to select and the
  // job could not finish. A combobox's `inputEl` is its text box; the list
  // opens from the arrow beside it. The operator's own recording of that click
  // names the trigger: div#ext-gen2855, xtype combobox.
  const arrow = element({ tagName: "DIV" });
  const { c, input } = field({ trigger: arrow });
  withExt([c]);

  const answer = performInPage({
    action: "click",
    locators: [{ strategy: "component", query: "combobox#createShipmentBy" }],
  });

  assert.equal(answer.ok, true);
  assert.ok(arrow.events.includes("click"), "the arrow was never clicked");
  assert.ok(!input.events.includes("click"), "the text box was clicked instead");
});

test("the trigger is found whichever shape this Ext keeps it in", () => {
  for (const shape of [{ composite: true }, { named: true }]) {
    const arrow = element({ tagName: "DIV" });
    const { c } = field({ trigger: arrow, ...shape });
    withExt([c]);

    performInPage({
      action: "click",
      locators: [{ strategy: "component", query: "combobox#x" }],
    });

    assert.ok(arrow.events.includes("click"), `the ${Object.keys(shape)[0]} shape was missed`);
  }
});

test("a field with no trigger is still clicked where it always was", () => {
  const { c, input } = field();
  withExt([c]);

  const answer = performInPage({
    action: "click",
    locators: [{ strategy: "component", query: "textfield#code" }],
  });

  assert.equal(answer.ok, true);
  assert.ok(input.events.includes("click"));
});

test("typing still goes to the text box, never to the trigger", () => {
  // `type` and `select` want the input they always wanted. Sending them to the
  // arrow would break every field that works today to fix one that does not.
  const arrow = element({ tagName: "DIV" });
  const { c, input } = field({ trigger: arrow });
  withExt([c]);

  performInPage({
    action: "type",
    value: "NRT2",
    locators: [{ strategy: "component", query: "combobox#createShipmentBy" }],
  });

  assert.equal(input.value, "NRT2");
  assert.ok(!arrow.events.includes("click"), "the arrow was typed into");
});
