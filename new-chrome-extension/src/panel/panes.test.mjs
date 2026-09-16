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

const { PANES, BELONGS, panes } = await import("./panes.js");

const tests = [];
let failed = 0;
const test = (name, fn) => tests.push([name, fn]);

const tabs = (row) => row.kids.filter((kid) => kid.tag === "button");

test("two halves, in the order they are read", () => {
  assert.deepEqual(PANES, ["home", "chat"]);
  const row = panes("home");
  assert.deepEqual(tabs(row).map((tab) => tab.dataset.pane), ["home", "chat"]);
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

test("the composer belongs to the conversation, and that is the arguable half", () => {
  // Said here rather than in the markup because it is a decision: a box you
  // type into, pinned under a column of cards about what is happening now, is
  // what made the old panel one long thing.
  assert.deepEqual(BELONGS.home, ["today", "waiting", "cards"]);
  assert.deepEqual(BELONGS.chat, ["thread", "here", "ask-bar"]);
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
