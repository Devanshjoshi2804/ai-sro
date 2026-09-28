// Self-check for how a time is read and a day is named.
//
// Run with `node src/panel/pending.test.mjs`.

import assert from "node:assert";

const { dayNamed, when } = await import("./pending.js");

const NOW = Date.parse("2026-09-18T12:00:00Z");
const HOUR = 3600000;

const tests = [];
const test = (name, fn) => tests.push([name, fn]);
let failed = 0;

test("an ISO string is when something happened, because that is what is stored", () => {
  // What is stored is stamped with `new Date(now).toISOString()`, and
  // everything that reached for it read `Number(at)`, which is NaN. So every request in
  // the list dated to 1 January 1970 and "newest first" sorted nothing, since
  // `NaN - NaN` is not an order. Seen on the deployment 2026-09-18; the tests
  // passed throughout because they were written with numbers.
  assert.equal(when(new Date(NOW).toISOString()), NOW);
  assert.equal(when(NOW), NOW);
  assert.equal(when(undefined), 0);
  assert.equal(when("not a date"), 0);
  assert.equal(dayNamed(new Date(NOW - HOUR).toISOString(), NOW), "Today");
});

test("the days are named the way anybody says them", () => {
  assert.equal(dayNamed(NOW - HOUR, NOW), "Today");
  assert.equal(dayNamed(NOW - 26 * HOUR, NOW), "Yesterday");
  // Past a week a weekday stops being a date anybody can place.
  assert.match(dayNamed(NOW - 30 * 24 * HOUR, NOW), /\d/);
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
  console.error(`pending.test.mjs: ${failed} failed`);
  process.exit(1);
}
console.log(`pending.test.mjs: ok (${tests.length})`);
