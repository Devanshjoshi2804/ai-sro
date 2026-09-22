// Self-check for the today line: three numbers, each of them measured.
//
// The panel is about to claim that it saved somebody time, which is the one
// sentence in this product a person will repeat to their manager. So every
// number in it comes off `GET /v1/analytics/summary`, which counts rows
// somebody can open, and nothing here computes a figure of its own.
//
// Run with `node src/panel/today.test.mjs`.

import assert from "node:assert";

import { install, words } from "./test-support/fake-document.mjs";

install();

const { today } = await import("./today.js");

const tests = [];
const test = (name, fn) => tests.push([name, fn]);

test("a day with nothing in it says nothing", () => {
  // The first panel somebody opens. "0 done · 0 offers · 0 min saved" is a
  // scoreboard of failure on a product that has not been given anything to do
  // yet, and it is the first thing they would read.
  assert.equal(today({ doing: { runs: 0, minutes_saved: 0 } }, 0), null);
  assert.equal(today(null, 0), null);
});

test("the three numbers, in the order somebody reads them", () => {
  const line = today({ doing: { runs: 3, minutes_saved: 4.2 } }, 2);
  assert.deepEqual(
    line.kids.map(words),
    ["3 done", "2 offers", "4 min saved"],
  );
});

test("under a minute and a half is said in seconds", () => {
  // "0 min saved" after a run that took thirty seconds off somebody's day
  // reads as nothing happening, which is the opposite of true.
  const line = today({ doing: { runs: 1, minutes_saved: 0.5 } }, 0);
  assert.match(words(line), /30 s saved/);
});

test("one of anything is singular", () => {
  const line = today({ doing: { runs: 1, minutes_saved: 2 } }, 1);
  assert.deepEqual(
    line.kids.map(words),
    ["1 done", "1 offer", "2 min saved"],
  );
});

test("a summary missing a field counts it as nothing, and still draws", () => {
  // An older backend, or one that answered before the sweep ran. A panel that
  // threw here would take the whole ledger with it.
  const line = today({}, 1);
  assert.match(words(line), /0 done/);
  assert.match(words(line), /1 offer/);
});

let failed = 0;
for (const [name, fn] of tests) {
  try {
    await fn();
  } catch (error) {
    failed += 1;
    console.error(`  ✗ ${name}\n    ${error.message}`);
  }
}
if (failed) {
  console.error(`today.test.mjs: ${failed} failed`);
  process.exit(1);
}
console.log(`today.test.mjs: ok (${tests.length})`);
