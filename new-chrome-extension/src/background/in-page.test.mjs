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

function element({ tagName = "BUTTON", typeable = false } = {}) {
  const el = typeable ? new HTMLInputElement() : {};
  el.tagName = tagName;
  el.events = [];
  el.focused = 0;
  el.dispatchEvent = (event) => el.events.push(event.type);
  if (typeable) el.focus = () => (el.focused += 1);
  return el;
}

let at = null;
globalThis.document = { elementFromPoint: () => at };

const { performAtInPage } = await import("./in-page.js");

test("nothing at the point is a control that was not found", () => {
  at = null;
  const answer = performAtInPage({ x: 5, y: 5, action: "click" });
  assert.equal(answer.ok, false);
  assert.equal(answer.error.kind, "control_not_found");
});

test("a point inside a frame is a control this document did not find", () => {
  for (const tagName of ["IFRAME", "FRAME"]) {
    at = element({ tagName });
    const answer = performAtInPage({ x: 5, y: 5, action: "click" });
    assert.equal(answer.ok, false, tagName);
    assert.equal(answer.error.kind, "control_not_found");
    assert.deepEqual(at.events, [], "no event reached the frame element");
  }
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
  // click, cleared (input), then per character keydown/input/keyup, then change.
  assert.deepEqual(at.events, [
    "click", "input",
    "keydown", "input", "keyup",
    "keydown", "input", "keyup",
    "change",
  ]);
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
