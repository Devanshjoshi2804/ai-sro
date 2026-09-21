// Self-check for the backlog: everything waiting, grouped by the day it came.
//
// The same fake document `ledger.test.mjs` uses, for the same reason: what is
// under test is what an operator reads and what they can press, not the DOM.
//
// Run with `node src/panel/pending.test.mjs`.

import assert from "node:assert";

import { install, words } from "./test-support/fake-document.mjs";

install();

const { dayNamed, pending, when } = await import("./pending.js");

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
    at: new Date(NOW - HOUR).toISOString(),
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
    [
      one({ id: "a" }),
      one({ id: "b" }),
      one({ id: "c", at: new Date(NOW - 48 * HOUR).toISOString() }),
    ],
    { now: NOW },
  );

  assert.match(words(box), /3 requests waiting/);
  assert.match(words(box), /2 today/);
});

test("one waiting is not called 1 requests", () => {
  assert.match(words(pending([one()], { now: NOW })), /1 request waiting/);
});

test("an ISO string is when something happened, because that is what is stored", () => {
  // `nudge.js` stamps `at` with `new Date(now).toISOString()`, and everything
  // that reached for it read `Number(at)`, which is NaN. So every request in
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
      one({ id: "old", at: new Date(NOW - 5 * HOUR).toISOString() }),
      one({ id: "new", at: new Date(NOW - HOUR).toISOString() }),
    ],
    { now: NOW },
  );

  const rows = [];
  walk(box, (el) => {
    if (el.dataset?.id) rows.push(el.dataset.id);
  });
  assert.deepEqual(rows, ["new", "old"]);
});

test("a month of requests goes in one press, and its confirmation", () => {
  // Why this exists: the queue is deep because clearing it was one press per
  // card, so nobody cleared it and this morning's request sat under a
  // fortnight of dead ones. Why it asks twice: a dismissal reports a fate, a
  // fate is counted, and thirty of them written by a misplaced thumb is a lie
  // told to whatever decides what to offer next.
  const cleared = [];
  const box = pending(
    [
      one({ id: "a" }),
      one({ id: "b", at: new Date(NOW - 26 * HOUR).toISOString() }),
      one({ id: "c", at: new Date(NOW - 30 * 24 * HOUR).toISOString() }),
    ],
    { now: NOW, onClear: (ids) => cleared.push(ids) },
  );

  const all = find(box, (el) => /^Dismiss all 3$/.test(el.textContent || ""));
  assert.ok(all, "a backlog with no way to put it down");
  all.listeners.click[0]();
  assert.deepEqual(cleared, [], "a pile was cleared on one press");
  assert.match(all.textContent, /sure\?/);
  all.listeners.click[0]();
  assert.deepEqual(cleared, [["a", "b", "c"]]);
  assert.equal(all.disabled, true, "a spent control stayed live");
});

test("a day at a time, so clearing a month does not clear this morning", () => {
  const cleared = [];
  const box = pending(
    [
      one({ id: "today" }),
      one({ id: "old-1", at: new Date(NOW - 30 * 24 * HOUR).toISOString() }),
      one({ id: "old-2", at: new Date(NOW - 30 * 24 * HOUR).toISOString() }),
    ],
    { now: NOW, onClear: (ids) => cleared.push(ids) },
  );

  const day = find(box, (el) => /^Dismiss 2$/.test(el.textContent || ""));
  assert.ok(day, "the days are grouped for reading and not for acting on");
  day.listeners.click[0]();
  day.listeners.click[0]();
  assert.deepEqual(cleared, [["old-1", "old-2"]], "the wrong day was cleared");
});

test("one request, and one day, are not offered a way to clear in bulk", () => {
  // A second control that does what the card under it already does, and a
  // "Dismiss 3" beside the only heading that is the same as "Dismiss all 3".
  const onClear = () => assert.fail("nothing should have been cleared");
  const alone = pending([one()], { now: NOW, onClear });
  assert.equal(
    find(alone, (el) => /Dismiss/.test(el.textContent || "")),
    null,
  );
  const oneDay = pending([one({ id: "a" }), one({ id: "b" })], {
    now: NOW,
    onClear,
  });
  assert.ok(find(oneDay, (el) => /^Dismiss all 2$/.test(el.textContent || "")));
  assert.equal(
    find(oneDay, (el) => /^Dismiss 2$/.test(el.textContent || "")),
    null,
  );
});

test("a day's control is in that day's heading, and the day still says its name", () => {
  // Where it is IS what it means: "Dismiss 1" adrift between two days clears
  // whichever one the reader guesses. And the heading is what makes the queue
  // readable in the first place, so it still has to read as a day.
  const box = pending(
    [
      one({ id: "a" }),
      one({ id: "b", at: new Date(NOW - 26 * HOUR).toISOString() }),
    ],
    { now: NOW, onClear: () => {} },
  );

  const days = [];
  walk(box, (el) => {
    if (el.className === "pending-day") days.push(el);
  });
  assert.deepEqual(
    days.map((el) => words(el)),
    ["Today · 1 Dismiss 1", "Yesterday · 1 Dismiss 1"],
  );
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
