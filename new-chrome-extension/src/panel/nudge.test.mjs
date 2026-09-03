// Self-check for the nudge: the panel offering to do a task the moment somebody
// lands where it starts.
//
// The rule that matters is not when it fires but when it stops. A prompt that
// outlives the task it offered is a prompt that was ignored, and a product that
// nags is one whose notifications get switched off in week two. So a nudge ends
// three ways -- answered, done by hand, or ninety seconds -- and every one of
// them is here.
//
// Pure over an injected clock, which is what makes ninety seconds a test rather
// than a wait.
//
// Run with `node src/panel/nudge.test.mjs`.

import assert from "node:assert";

const { LIFETIME_MS, fire, mute, onCall, shouldFire, sweep } = await import("./nudge.js");

const T0 = Date.parse("2026-09-03T12:00:00Z");
const PAGE = "https://wms.example/ui/suppliers/new";
const TAUGHT = {
  id: "cnd-1",
  title: "Create a supplier",
  starts_on: "wms.example/ui/suppliers/new",
  times_seen: 5,
  skill_id: "skl-1",
};

const asking = (over = {}) => ({
  url: PAGE,
  visit: "1:100",
  candidates: [TAUGHT],
  nudges: [],
  muted: {},
  performing: null,
  now: T0,
  ...over,
});

const tests = [];
const test = (name, fn) => tests.push([name, fn]);

test("landing where a known task starts is what fires it", () => {
  assert.equal(shouldFire(asking()), TAUGHT);
  assert.equal(
    shouldFire(asking({ url: "https://wms.example/ui/suppliers/new?sid=abc&t=1" })),
    TAUGHT,
    "a session id in the query made the page unrecognisable",
  );
  assert.equal(shouldFire(asking({ url: "https://wms.example/ui/suppliers" })), null);
});

test("a task nobody has done often enough says nothing", () => {
  // The offer threshold, not a second one. Two doings is a coincidence.
  const twice = { ...TAUGHT, times_seen: 2, skill_id: null };
  assert.equal(shouldFire(asking({ candidates: [twice] })), null);

  // Unless somebody already taught it. Then the count is beside the point: the
  // skill exists, and offering to run it is not a guess about a pattern.
  const taught = { ...twice, skill_id: "skl-1" };
  assert.equal(shouldFire(asking({ candidates: [taught] })), taught);
});

test("nothing is offered over a run that is already happening", () => {
  // The browser is being driven. Offering to drive it again is the panel
  // talking over itself.
  assert.equal(shouldFire(asking({ performing: { runId: "run-1" } })), null);
});

test("once per visit, and a later visit may ask again", () => {
  const one = fire(TAUGHT, T0, { tabId: 1, visit: "1:100" });
  assert.equal(shouldFire(asking({ nudges: [one] })), null, "it asked twice in one visit");
  assert.equal(
    shouldFire(asking({ nudges: [{ ...one, state: "expired" }], visit: "1:101" })),
    TAUGHT,
    "a fresh navigation to the same page never asked again",
  );
});

test("a nudge already open anywhere stops another being made", () => {
  // Two at once is a queue, and a queue of prompts is the thing this design
  // exists to not be.
  const elsewhere = fire({ ...TAUGHT, starts_on: "other.example/x" }, T0, {
    tabId: 2,
    visit: "2:1",
  });
  assert.equal(shouldFire(asking({ nudges: [elsewhere] })), null);
});

test("doing the task yourself ends it, and reading does not", () => {
  const one = fire(TAUGHT, T0, { tabId: 1, visit: "1:100" });
  const wrote = onCall([one], { url: "https://wms.example/api/suppliers", method: "POST" }, T0 + 5000);
  assert.equal(wrote[0].state, "by-hand");

  const read = onCall([one], { url: "https://wms.example/api/suppliers", method: "GET" }, T0 + 5000);
  assert.equal(read[0].state, "open", "looking something up is not doing the task");

  const elsewhere = onCall([one], { url: "https://other.example/api/x", method: "POST" }, T0 + 5000);
  assert.equal(elsewhere[0].state, "open", "a write on another host ended it");
});

test("ninety seconds, and not a second before", () => {
  const one = fire(TAUGHT, T0, { tabId: 1, visit: "1:100" });
  assert.equal(sweep([one], { url: PAGE, now: T0 + LIFETIME_MS - 1 })[0].state, "open");
  assert.equal(sweep([one], { url: PAGE, now: T0 + LIFETIME_MS })[0].state, "expired");
});

test("walking away ends it too", () => {
  const one = fire(TAUGHT, T0, { tabId: 1, visit: "1:100" });
  const gone = sweep([one], { url: "https://wms.example/ui/orders", now: T0 + 1000 });
  assert.equal(gone[0].state, "expired", "it outlived the page it was about");
});

test("a nudge that already ended is left alone", () => {
  // Its `endedAt` is when it ended, not when a sweep noticed. The ledger draws
  // one line from it either way, but a record that moves is one nobody trusts.
  const done = { ...fire(TAUGHT, T0, { tabId: 1, visit: "1:100" }), state: "by-hand", endedAt: T0 + 9 };
  assert.deepEqual(sweep([done], { url: PAGE, now: T0 + LIFETIME_MS * 4 })[0], done);
});

test("not for this page holds until the end of the day", () => {
  const muted = mute({}, TAUGHT.starts_on, T0);
  assert.equal(shouldFire(asking({ muted })), null);
  assert.ok(muted[TAUGHT.starts_on] > T0);

  // Tomorrow it is a fair question again: the page may matter to them next week
  // even if it did not this afternoon.
  const tomorrow = muted[TAUGHT.starts_on] + 1;
  assert.equal(shouldFire(asking({ muted, now: tomorrow })), TAUGHT);
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
  console.error(`nudge.test.mjs: ${failed} failed`);
  process.exit(1);
}
console.log(`nudge.test.mjs: ok (${tests.length})`);
