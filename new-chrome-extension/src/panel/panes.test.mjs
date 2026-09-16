// Self-check for the two halves of the panel.
//
// The panel has been one scrolling column -- the strip, the day, the cards, the
// whole conversation, the composer under all of it -- which is what "the panel
// is chaotic" means in practice: a card about a run happening now sitting
// between two sentences somebody typed an hour ago.
//
// Run with `node src/panel/panes.test.mjs`.

import assert from "node:assert";

import { install, words } from "./test-support/fake-document.mjs";

install();

const { PANES, panes } = await import("./panes.js");

const tests = [];
let failed = 0;
const test = (name, fn) => tests.push([name, fn]);

const tabs = (row) => row.kids.filter((kid) => kid.tag === "button");

test("two halves and two things to do, in the order they are read", () => {
  assert.deepEqual(PANES, ["home", "chat"]);
  const row = panes("home");
  assert.deepEqual(tabs(row).map((tab) => tab.dataset.pane), [
    "home",
    "chat",
    "history",
    "new",
  ]);
});

test("a glyph is not a name, so every one of them carries the word", () => {
  // Four unlabelled shapes is what an icon cluster is when nobody says what
  // the icons are -- to the pointer on hover, and to a reader always.
  for (const tab of tabs(panes("home"))) {
    assert.ok(tab.title, `${tab.dataset.pane} had no tooltip`);
    assert.ok(tab.getAttribute("aria-label"), `${tab.dataset.pane} had no name`);
  }
});

test("only the halves are tabs; the other two are things to do", () => {
  // History is an overlay you close and come back from, and a new conversation
  // is an action. Marking either as a tab would have a screen reader announce
  // "4 of 4, not selected" for a button that selects nothing.
  const [, , recent, made] = tabs(panes("home"));
  assert.equal(recent.getAttribute("role"), null);
  assert.equal(made.getAttribute("aria-selected"), null);
});

test("history and a new conversation each say which was pressed", () => {
  const picked = [];
  const row = panes("home", { onPick: (what) => picked.push(what) });
  tabs(row)[2].listeners.click[0]();
  tabs(row)[3].listeners.click[0]();
  assert.deepEqual(picked, ["history", "new"]);
});

test("the one you are on says so, to a screen reader as well as to an eye", () => {
  const row = panes("chat");
  const [home, chat] = tabs(row);

  assert.equal(home.getAttribute("aria-selected"), "false");
  assert.equal(chat.getAttribute("aria-selected"), "true");
  assert.equal(row.getAttribute("role"), "tablist");
  assert.equal(home.getAttribute("role"), "tab");
});

test("what is waiting is counted on Home, from the other pane", () => {
  // The one thing a person on the wrong pane needs to know.
  const row = panes("chat", { waiting: 3 });

  assert.match(words(row), /3/);
  assert.equal(tabs(row)[0].getAttribute("aria-label"), "Home, 3 waiting");
});

test("nothing is counted beside the pane you are already looking at", () => {
  // A number describing the screen to itself. The cards are right there.
  const row = panes("home", { waiting: 3 });

  assert.doesNotMatch(words(row), /3/);
});

test("nothing waiting is no badge at all", () => {
  assert.doesNotMatch(words(panes("chat", { waiting: 0 })), /0/);
});

test("picking the other half says which", () => {
  const picked = [];
  const row = panes("home", { onPick: (pane) => picked.push(pane) });

  tabs(row)[1].listeners.click[0]();

  assert.deepEqual(picked, ["chat"]);
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
  console.error(`panes.test.mjs: ${failed} failed`);
  process.exit(1);
}
console.log(`panes.test.mjs: ok (${tests.length})`);
