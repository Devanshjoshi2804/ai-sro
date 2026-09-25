// Acting at a point through the browser instead of through the page.
//
// The rung that looks at a picture answers in viewport coordinates, and until
// this the extension had to work out which document owned that pixel before it
// could act. On the one system the rung exists for -- a warehouse application
// rendered entirely inside an iframe -- that lookup is the whole game, and it
// failed on 2026-09-17 for a reason the point was not wrong about.
//
// Run with `node src/background/pointing.test.mjs`.

import assert from "node:assert";
import { test } from "node:test";

let sent = [];
let attached = [];
let detached = [];
let refuseAttach = false;
let refuseInput = false;
let named = { tag: "button", name: "Add", item_id: "addButton" };

globalThis.chrome = {
  debugger: {
    attach: async ({ tabId }) => {
      if (refuseAttach) throw new Error("Another debugger is already attached to the tab");
      attached.push(tabId);
    },
    detach: async ({ tabId }) => {
      detached.push(tabId);
    },
    sendCommand: async ({ tabId }, method, params) => {
      sent.push({ tabId, method, params });
      if (refuseInput && method.startsWith("Input.")) {
        throw new Error("Detached while handling command.");
      }
      if (method === "DOM.getNodeForLocation") return { backendNodeId: 42 };
      if (method === "DOM.resolveNode") return { object: { objectId: "obj-1" } };
      if (method === "Runtime.callFunctionOn") return { result: { value: named } };
      return {};
    },
  },
};

const { pointAt } = await import("./pointing.js");

const fresh = () => {
  sent = [];
  attached = [];
  detached = [];
  refuseAttach = false;
  refuseInput = false;
  named = { tag: "button", name: "Add", item_id: "addButton" };
};

const inputs = () => sent.filter((one) => one.method.startsWith("Input."));

test("a click goes to the pixel, and nothing asks which frame owns it", async () => {
  // The whole point. `webNavigation.getAllFrames` is not even defined on the
  // fake chrome above: a lookup would throw, and the absence of a throw is the
  // assertion. The browser routes the event to whichever renderer owns the
  // pixel, exactly as it routes a real mouse.
  fresh();
  const said = await pointAt(7, { x: 612, y: 214, action: "click" });

  assert.equal(said.ok, true, JSON.stringify(said));
  const mouse = inputs().map((one) => one.params.type);
  assert.deepEqual(mouse, ["mouseMoved", "mousePressed", "mouseReleased"]);
  // Moved to before pressed: a button that appears on hover has to see the
  // pointer arrive, and a real mouse is never anywhere else first.
  for (const one of inputs()) {
    assert.equal(one.params.x, 612);
    assert.equal(one.params.y, 214);
  }
});

test("what the point turned out to be is named, and that is the expensive part", async () => {
  // A picture cost a model call to produce this point. What it found -- that
  // the thing at (612, 214) is called "Add" -- is what lets the next run skip
  // the picture, so a reply that acts and says nothing has thrown the finding
  // away.
  fresh();
  const said = await pointAt(7, { x: 612, y: 214, action: "click" });

  assert.deepEqual(said.result.control, {
    tag: "button",
    name: "Add",
    item_id: "addButton",
  });
  // Named BEFORE the press. A click can navigate, and a control that is gone
  // cannot say what it was called.
  const naming = sent.findIndex((one) => one.method === "Runtime.callFunctionOn");
  const pressing = sent.findIndex((one) => one.params?.type === "mousePressed");
  assert.ok(naming < pressing, "it named the control after clicking it away");
});

test("a point that cannot be named is still a point that can be clicked", async () => {
  fresh();
  named = null;

  const said = await pointAt(7, { x: 10, y: 10, action: "click" });
  assert.equal(said.ok, true);
  assert.equal(said.result.control, null);
  assert.ok(inputs().length, "it refused to act because it could not name");
});

test("typing selects what is there and types over it", async () => {
  // "Type this" has always meant the field ends up holding this and nothing
  // else, and a form a run has been down before has a value in it already.
  fresh();
  const said = await pointAt(7, { x: 300, y: 120, action: "type", value: "GS1" });

  assert.equal(said.ok, true);
  const keys = inputs().filter((one) => one.method === "Input.dispatchKeyEvent");
  assert.ok(keys.length, "nothing selected what was already in the field");
  // Ctrl and Meta together: this does not know which platform it is on, and
  // the browser ignores the modifier its own platform does not use.
  assert.equal(keys[0].params.key, "a");
  assert.equal(keys[0].params.modifiers, 6);
  const text = sent.find((one) => one.method === "Input.insertText");
  assert.equal(text.params.text, "GS1");
  // `insertText` and not a loop of synthetic key events: it goes through the
  // same editing machinery a keyboard does, which is what a framework watching
  // its own input expects to see.
});

test("typing nothing clears the field rather than inserting nothing", async () => {
  fresh();
  await pointAt(7, { x: 300, y: 120, action: "type", value: "" });

  assert.ok(
    !sent.some((one) => one.method === "Input.insertText"),
    "it asked the browser to insert an empty string, which does nothing",
  );
  assert.ok(sent.some((one) => one.params?.key === "Backspace"));
});

test("a tab this cannot drive says so, and does not report the step failed", async () => {
  // One debugger per tab, and an operator with DevTools open has it. That is
  // the right way round -- their tab, their tools -- so this is the caller's
  // cue to try the page instead, not a fact about the control.
  fresh();
  refuseAttach = true;
  refuseInput = true;

  const said = await pointAt(7, { x: 1, y: 2, action: "click" });
  assert.equal(said.ok, false);
  assert.equal(said.error.kind, "cannot_drive_tab");
  assert.notEqual(said.error.kind, "control_not_found");
});

test("it detaches what it attached and nothing else", async () => {
  // A tab someone else already holds refuses our attach, and detaching it
  // would pull the floor out from under them.
  fresh();
  await pointAt(7, { x: 1, y: 2, action: "click" });
  assert.deepEqual(attached, [7]);
  assert.deepEqual(detached, [7]);

  fresh();
  refuseAttach = true;
  await pointAt(7, { x: 1, y: 2, action: "click" });
  assert.deepEqual(attached, []);
  assert.deepEqual(detached, [], "it detached a tab somebody else was holding");
});

test("a scroll is a wheel, and does not bother naming what is under it", async () => {
  fresh();
  const said = await pointAt(7, { x: 5, y: 5, action: "scroll", value: 600 });

  assert.equal(said.ok, true);
  const wheel = inputs().find((one) => one.params.type === "mouseWheel");
  assert.equal(wheel.params.deltaY, 600);
  assert.ok(
    !sent.some((one) => one.method === "DOM.getNodeForLocation"),
    "it paid for a node lookup to scroll past it",
  );
});

test("Enter carries the text that makes it do something", async () => {
  // A keydown with no `text` moves a caret and submits nothing.
  fresh();
  const said = await pointAt(7, { x: 5, y: 5, action: "press", value: "Enter" });

  assert.equal(said.ok, true);
  const down = sent.find((one) => one.params?.type === "keyDown" && one.params.key === "Enter");
  assert.equal(down.params.text, "\r");
  assert.equal(down.params.windowsVirtualKeyCode, 13);
});

test("an action nobody can do at a point is refused, not attempted", async () => {
  fresh();
  const said = await pointAt(7, { x: 5, y: 5, action: "upload" });

  assert.equal(said.ok, false);
  assert.equal(said.error.kind, "not_actionable");
  assert.equal(inputs().length, 0);
});
