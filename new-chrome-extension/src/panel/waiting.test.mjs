// Self-check for the banner that holds what arrived while nobody was looking.
//
// Every offer this panel makes ends -- pressed, done by hand, dismissed, or
// swept -- except the ones that came in by mail, which are kept because the
// backend offers each message exactly once and a swept card is work silently
// dropped. Three of those over a morning is three cards that cannot be swept,
// in a column where four is already a lot.
//
// So what is checked here is the fold: the number first, the detail one tap
// behind it, and nothing at all when nothing is waiting.
//
// Run with `node src/panel/waiting.test.mjs`.

import assert from "node:assert";

import { install, words } from "./test-support/fake-document.mjs";

install();

const { waiting } = await import("./waiting.js");

const tests = [];
let failed = 0;
const test = (name, fn) => tests.push([name, fn]);

const one = (n, at = "2026-09-16T09:0" + n + ":00Z") => ({
  id: `n_${n}`,
  at,
  title: `Create a Customer Type ${n}`,
  state: "open",
  missed: true,
});

const card = (nudge) => {
  const li = document.createElement("li");
  li.textContent = nudge.title;
  return li;
};

test("nothing waiting draws nothing at all", () => {
  // Not an empty banner. A line that says "0 requests" is a panel reporting on
  // its own machinery to somebody who came here to do something else.
  assert.equal(waiting([], { card }), null);
});

test("the number first, and the cards behind one tap", () => {
  const folded = waiting([one(1), one(2), one(3)], { open: false, card });

  assert.match(words(folded), /3 requests arrived while you were away/);
  assert.match(words(folded), /Show/);
  assert.doesNotMatch(words(folded), /Create a Customer Type/, "the cards were drawn folded");
});

test("opened, it drops the cards down, newest first", () => {
  const open = waiting([one(1), one(3), one(2)], { open: true, card });

  assert.match(words(open), /Hide/);
  const titles = words(open).match(/Create a Customer Type \d/g);
  assert.deepEqual(titles, [
    "Create a Customer Type 3",
    "Create a Customer Type 2",
    "Create a Customer Type 1",
  ]);
});

test("one request is still the banner, not a card somewhere else", () => {
  // The alternative -- a lone card in the stack, folding only from two -- is a
  // card that moves depending on how many of its kind exist, and an operator
  // looking for yesterday's in the wrong place today.
  assert.match(words(waiting([one(1)], { card })), /1 request arrived while you were away/);
});

test("the whole line is the control, and it says which way it goes", () => {
  // A chevron is a four-pixel target on a panel somebody uses one-handed
  // beside a warehouse system.
  const flipped = [];
  const folded = waiting([one(1)], { open: false, onToggle: (open) => flipped.push(open), card });
  const head = folded.kids.find((kid) => kid.tag === "button");

  assert.equal(head.getAttribute("aria-expanded"), "false");
  head.listeners.click[0]();

  assert.deepEqual(flipped, [true]);
});

test("it is a state, so it is toned and never accented", () => {
  // `brand.css`: state colours are not the accent. It reuses the enum the
  // cards already have rather than inventing a class of its own.
  const folded = waiting([one(1)], { card });

  assert.equal(folded.className, "card");
  assert.equal(folded.dataset.tone, "attention");
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
  console.error(`waiting.test.mjs: ${failed} failed`);
  process.exit(1);
}
console.log(`waiting.test.mjs: ok (${tests.length})`);
