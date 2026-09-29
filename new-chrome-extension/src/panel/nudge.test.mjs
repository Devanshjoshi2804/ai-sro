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

const { KEPT_MS, LIFETIME_MS, endOfDay, fire, onCall, shouldFire, sweep } =
  await import("./nudge.js");

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

test("once per visit, and a later visit may ask again", () => {
  const one = fire(TAUGHT, T0, { tabId: 1, visit: "1:100" });
  assert.equal(shouldFire(asking({ nudges: [one] })), null, "it asked twice in one visit");
  assert.equal(
    shouldFire(asking({ nudges: [{ ...one, state: "expired" }], visit: "1:101" })),
    TAUGHT,
    "a fresh navigation to the same page never asked again",
  );
});

test("a page two jobs start on offers neither on arrival", () => {
  // QA 2026-09-29: an address alone cannot say which of two jobs somebody is
  // about to do, and naming one is the guess `match` refuses on a tie. The
  // gestures decide instead.
  const create = { ...TAUGHT, id: "wfl_create", title: "Create a supplier", source: "rig" };
  const remove = { ...TAUGHT, id: "wfl_delete", title: "Delete a supplier", source: "rig" };
  assert.equal(shouldFire(asking({ candidates: [create, remove] })), null, "the address picked one");
  assert.equal(shouldFire(asking({ candidates: [remove] })), remove, "a page one job starts on still offers it");

  // Only what is offerable competes: a pattern seen twice is not a job here.
  const unproven = { ...TAUGHT, id: "cnd-2", times_seen: 2, skill_id: null };
  assert.equal(shouldFire(asking({ candidates: [unproven, remove] })), remove);
});

test("a rule the operator made for this page is explicit and still offers", () => {
  const create = { ...TAUGHT, id: "wfl_create", source: "rig" };
  const remove = { ...TAUGHT, id: "wfl_delete", source: "rig" };
  const rule = { ...remove, rule: true, values: { Code: "X" } };
  assert.equal(shouldFire(asking({ candidates: [create, remove, rule] })), rule);
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

test("the beat sweeps for time alone, not for a page it cannot see", () => {
  // `sweepNudges` runs off the heartbeat and knows no url. Passed `""` that
  // read as "they have walked away from everywhere", so every open offer ended
  // within a beat and the fate table said `expired` for an operator still
  // standing on the page.
  const one = fire(TAUGHT, T0, { tabId: 1, visit: "1:100" });
  assert.equal(sweep([one], { url: null, now: T0 + LIFETIME_MS - 1 })[0].state, "open");
  assert.equal(sweep([one], { url: null, now: T0 + LIFETIME_MS })[0].state, "expired");
});

test("a nudge that already ended is left alone", () => {
  // Its `endedAt` is when it ended, not when a sweep noticed. The ledger draws
  // one line from it either way, but a record that moves is one nobody trusts.
  const done = { ...fire(TAUGHT, T0, { tabId: 1, visit: "1:100" }), state: "by-hand", endedAt: T0 + 9 };
  assert.deepEqual(sweep([done], { url: PAGE, now: T0 + LIFETIME_MS * 4 })[0], done);
});

test("a rig offer carries what it would take to finish the job", () => {
  // The prefix match already knows which job, how far in, and what was typed.
  // A nudge that dropped any of it would be an offer nobody could act on.
  const offered = fire(
    {
      id: "wfl_wa",
      title: "Create Work Area",
      starts_on: "wms.example/wa",
      source: "rig",
      workflow_id: "wfl_wa",
      k: 2,
      values: { workArea: "NEW" },
      missing: ["description"],
      parameters: ["workArea", "description"],
    },
    T0,
    { tabId: 1, visit: "1:100" },
  );
  assert.equal(offered.source, "rig");
  assert.equal(offered.workflowId, "wfl_wa");
  assert.equal(offered.k, 2);
  assert.deepEqual(offered.values, { workArea: "NEW" });
  assert.deepEqual(offered.missing, ["description"]);
  assert.deepEqual(offered.parameters, ["workArea", "description"]);

  // And the arrival nudge, which is the same object made from a candidate: no
  // prefix behind it, so nothing typed and no step reached.
  const arrived = fire(TAUGHT, T0, { tabId: 1, visit: "1:100" });
  assert.equal(arrived.source, "backend");
  assert.equal(arrived.k, 0);
  assert.deepEqual(arrived.values, {});
  assert.equal(arrived.workflowId, null);
});

test("a job the rig has proved is offerable without a count behind it", () => {
  // The rig serves a shape only for a workflow whose runs were held. There is
  // no `times_seen` to reach and no skill to have been taught -- the proof is
  // that it ran.
  const proved = {
    id: "wfl_wa",
    title: "Create Work Area",
    starts_on: TAUGHT.starts_on,
    source: "rig",
    workflow_id: "wfl_wa",
    times_seen: 0,
    skill_id: null,
  };
  assert.equal(shouldFire(asking({ candidates: [proved] })), proved);
});

let failed = 0;
test("a navigation in another tab does not end an offer open in this one", () => {
  const one = fire({ id: "c_1", title: "T", starts_on: PAGE }, T0, { tabId: 7 });
  const other = sweep([one], { url: "https://wms.example/ui/orders", now: T0 + 1000, tabId: 9 });
  assert.equal(other[0].state, "open", "tab 9 left a page; tab 7's offer stands");
  const same = sweep([one], { url: "https://wms.example/ui/orders", now: T0 + 1000, tabId: 7 });
  assert.equal(same[0].state, "expired");
});

test("an offer that was never about a page goes quiet rather than ending", () => {
  // A mail arrives while the operator is on the floor. Swept by the arrival
  // rules it would end twice over -- ninety seconds, and the first moment they
  // looked at anything but the job's own screen -- and a request nobody has
  // answered has not stopped being a request.
  const card = fire(
    { id: "mail_m-7", title: "Create a Customer Type", starts_on: "wms.example/ui/customer-types",
      source: "rig", workflow_id: "wfl_1", keeps: true, expires_at: endOfDay(T0) },
    T0,
  );

  const later = sweep([card], { url: "https://mail.google.com/mail/u/0", now: T0 + LIFETIME_MS * 4 });

  assert.strictEqual(later[0].state, "open", "a request was swept away unanswered");
  assert.strictEqual(later[0].missed, undefined, "quiet before its day was over");

  const tomorrow = sweep(later, { url: null, now: endOfDay(T0) + 1 });

  assert.strictEqual(tomorrow[0].state, "open", "still askable");
  assert.strictEqual(tomorrow[0].missed, true, "nothing said it had been missed");
});

test("a request nobody answered goes after a day, not for ever", () => {
  // `keeps` was written to mean "a request nobody answered has not stopped
  // being a request", which is true for an afternoon and not for a week.
  // Measured on the deployment 2026-09-18: thirteen cards stacked in one
  // panel, six of them from the day before, and the only thing between an
  // operator and an unbounded column was pressing No thanks on each.
  const card = fire(
    { id: "mail_m-9", title: "Create a Customer Type", starts_on: "wms.example/ui/customer-types",
      source: "rig", workflow_id: "wfl_1", keeps: true, expires_at: endOfDay(T0) },
    T0,
  );

  // Quiet at the end of its day, and still there to be answered.
  const tonight = sweep([card], { url: null, now: endOfDay(T0) + 1 });
  assert.strictEqual(tonight[0].state, "open", "it ended the same day it arrived");
  assert.strictEqual(tonight[0].missed, true);

  // Gone a day after it ARRIVED, not a day after its day ended: a mail at
  // 23:50 would otherwise get ten minutes.
  const stillHere = sweep(tonight, { url: null, now: T0 + KEPT_MS - 1000 });
  assert.strictEqual(stillHere[0].state, "open", "a card went before its day was up");

  const gone = sweep(stillHere, { url: null, now: T0 + KEPT_MS + 1000 });
  assert.strictEqual(gone[0].state, "expired", "yesterday's card is still on the panel");
});

test("an arrival offer is swept exactly as it always was", () => {
  // The two rules above are a second shape, not a replacement. An offer that
  // sets neither keeps ninety seconds and leaving the page.
  const nudge = fire(TAUGHT, T0, { tabId: 1, visit: "v1" });

  assert.strictEqual(sweep([nudge], { url: PAGE, now: T0 + LIFETIME_MS })[0].state, "expired");
  assert.strictEqual(
    sweep([nudge], { url: "https://wms.example/ui/home", now: T0 + 1000 })[0].state,
    "expired",
  );
});

test("the operator doing it themselves ends a kept offer like any other", () => {
  // The rule that matters is not when it fires but when it stops. A request
  // they went and did by hand is not one to keep asking about.
  const card = fire(
    { id: "mail_m-7", title: "Create a Customer Type", starts_on: "wms.example/ui/customer-types",
      source: "rig", workflow_id: "wfl_1", keeps: true, expires_at: endOfDay(T0) },
    T0,
  );

  const after = onCall([card], { url: "https://wms.example/ui/customer-types", method: "POST" }, T0 + 60);

  assert.strictEqual(after[0].state, "by-hand");
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
  console.error(`nudge.test.mjs: ${failed} failed`);
  process.exit(1);
}
console.log(`nudge.test.mjs: ok (${tests.length})`);
