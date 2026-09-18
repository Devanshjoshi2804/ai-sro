// Self-check for the backlog: everything waiting, grouped by the day it came.
//
// The same fake document `ledger.test.mjs` uses, for the same reason: what is
// under test is what an operator reads and what they can press, not the DOM.
//
// Run with `node src/panel/pending.test.mjs`.

import assert from "node:assert";

import { install, words } from "./test-support/fake-document.mjs";

install();

const { dayNamed, pending } = await import("./pending.js");

const NOW = Date.parse("2026-09-18T12:00:00Z");
const HOUR = 3600000;

function one(over = {}) {
  return {
    id: "n1",
    state: "open",
    source: "rig",
    title: "Create a Customer Type",
    workflowId: "wfl_1",
    values: { "Customer Type": "GU9" },
    missing: [],
    at: NOW - HOUR,
    ...over,
  };
}

const tests = [];
const test = (name, fn) => tests.push([name, fn]);
let failed = 0;

test("nothing waiting draws nothing at all", () => {
  // An overlay that opens on an empty list is a press that appears to do
  // nothing, twice: once opening it and once closing it again.
  assert.equal(pending([]), null);
  assert.equal(pending([one({ state: "dismissed" })]), null);
});

test("the head says how many, and how much of it is today's", () => {
  // A backlog nobody can date reads as one undifferentiated pile. "Six, four
  // of them today" is a person deciding what to do this afternoon.
  const box = pending(
    [one({ id: "a" }), one({ id: "b" }), one({ id: "c", at: NOW - 48 * HOUR })],
    { now: NOW },
  );

  assert.match(words(box), /3 requests waiting/);
  assert.match(words(box), /2 today/);
});

test("one waiting is not called 1 requests", () => {
  assert.match(words(pending([one()], { now: NOW })), /1 request waiting/);
});

test("the days are named the way anybody says them", () => {
  assert.equal(dayNamed(NOW - HOUR, NOW), "Today");
  assert.equal(dayNamed(NOW - 26 * HOUR, NOW), "Yesterday");
  // Past a week a weekday stops being a date anybody can place.
  assert.match(dayNamed(NOW - 30 * 24 * HOUR, NOW), /\d/);
});

test("each request says what it carries, because that is what tells them apart", () => {
  // Eleven cards all reading `Create a Customer Type` is a list nobody can act
  // on. Seen on the deployment 2026-09-18.
  const box = pending(
    [
      one({ id: "a", values: { "Customer Type": "GU9" } }),
      one({ id: "b", values: { "Customer Type": "WDSL" } }),
    ],
    { now: NOW },
  );

  assert.match(words(box), /Customer Type: GU9/);
  assert.match(words(box), /Customer Type: WDSL/);
});

test("a request nothing was read out of says so rather than showing a blank", () => {
  assert.match(
    words(pending([one({ values: {} })], { now: NOW })),
    /nothing read out of it yet/,
  );
});

test("a request still short of a value says which", () => {
  // Pressing yes on this opens a question rather than starting a job, and that
  // is a different decision to be making.
  assert.match(
    words(pending([one({ missing: ["Customer Type"] })], { now: NOW })),
    /still needs Customer Type/,
  );
});

test("a press here is the press on Home", () => {
  const pressed = [];
  const box = pending([one()], {
    now: NOW,
    onPress: (...args) => pressed.push(args),
  });

  const yes = find(box, (el) => String(el.textContent).trim() === "Do it");
  assert.ok(yes, "no way to answer a request in the list of requests");
  yes.listeners.click[0]();

  assert.deepEqual(
    pressed.map((each) => [each[0], each[1].id]),
    [["do", "n1"]],
  );
});

test("one press ends the row", () => {
  // The list does not redraw on an answer, so without this both buttons stay
  // live under the cursor -- and "No thanks" then "Do it" is two fates for one
  // request.
  const pressed = [];
  const box = pending([one()], {
    now: NOW,
    onPress: (...args) => pressed.push(args),
  });
  const yes = find(box, (el) => String(el.textContent).trim() === "Do it");
  const no = find(box, (el) => String(el.textContent).trim() === "No thanks");

  yes.listeners.click[0]();
  no.listeners.click?.[0]?.();

  assert.equal(pressed.length, 1, "one request was answered twice");
  assert.equal(no.disabled, true);
});

test("the newest is at the top, because that is the one anybody acts on", () => {
  const box = pending(
    [
      one({ id: "old", at: NOW - 5 * HOUR }),
      one({ id: "new", at: NOW - HOUR }),
    ],
    { now: NOW },
  );

  const rows = [];
  walk(box, (el) => {
    if (el.dataset?.id) rows.push(el.dataset.id);
  });
  assert.deepEqual(rows, ["new", "old"]);
});

function walk(el, visit) {
  visit(el);
  for (const kid of el?.kids || []) walk(kid, visit);
}

function find(el, matches) {
  let found = null;
  walk(el, (each) => {
    if (!found && matches(each)) found = each;
  });
  return found;
}

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
