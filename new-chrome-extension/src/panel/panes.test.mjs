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

test("four places and one thing to do, in the order they are read", () => {
  assert.deepEqual(PANES, ["home", "chat", "waiting", "tasks"]);
  const row = panes("home");
  assert.deepEqual(tabs(row).map((tab) => tab.dataset.pane), [
    "home",
    "chat",
    "waiting",
    "tasks",
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

test("every place is a tab; the one action is not", () => {
  // Waiting and Tasks are places now -- full-width panes rather than dialogs
  // over the pane behind them. New is not: starting a conversation is
  // something you do, and it leaves you in Chat. Marking it as a tab would
  // have a screen reader announce "5 of 5, not selected" for a button that
  // selects nothing.
  const [, , waiting, recent, made] = tabs(panes("home"));

  assert.equal(waiting.getAttribute("role"), "tab");
  assert.equal(recent.getAttribute("role"), "tab");
  assert.equal(made.getAttribute("role"), null);
  assert.equal(made.getAttribute("aria-selected"), null);
});

test("waiting, tasks and a new conversation each say which was pressed", () => {
  const picked = [];
  const row = panes("home", { onPick: (what) => picked.push(what) });
  tabs(row)[2].listeners.click[0]();
  tabs(row)[3].listeners.click[0]();
  tabs(row)[4].listeners.click[0]();
  assert.deepEqual(picked, ["waiting", "tasks", "new"]);
});

test("the count is not drawn on the pane you are standing on", () => {
  // A badge on the screen you are reading is a number describing the screen
  // to itself, and one that stays lit while somebody works through the queue
  // in front of them is a number they learn to stop believing.
  const away = tabs(panes("home", { waiting: 3 }))[2];
  const on = tabs(panes("waiting", { waiting: 3 }))[2];

  assert.match(away.getAttribute("aria-label"), /Waiting for you, 3/);
  assert.equal(on.getAttribute("aria-label"), "Waiting for you");
});

test("the one you are on says so, to a screen reader as well as to an eye", () => {
  const row = panes("chat");
  const [home, chat] = tabs(row);

  assert.equal(home.getAttribute("aria-selected"), "false");
  assert.equal(chat.getAttribute("aria-selected"), "true");
  assert.equal(row.getAttribute("role"), "tablist");
  assert.equal(home.getAttribute("role"), "tab");
});

test("what is waiting is counted on the tray that holds it", () => {
  // The one thing a person needs to know without opening anything.
  const row = panes("chat", { waiting: 3 });

  assert.match(words(row), /3/);
  assert.equal(tabs(row)[2].getAttribute("aria-label"), "Waiting for you, 3");
});

test("the count is drawn on whichever pane you are standing on", () => {
  // It used to be hidden on Home, and that was right when everything waiting
  // WAS on Home -- the badge only said you had not been there. Home keeps the
  // newest one now and the rest are behind the tray, so a count that vanished
  // on Home would be hiding the queue from the pane it is nearest to.
  assert.match(words(panes("home", { waiting: 3 })), /3/);
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
