// Self-check for the learned-job card.
//
// What it must get right is the claim it makes about each job: which rung it
// stands on and how far it is toward writing alone. That comes from counted
// facts only -- a job with held runs and nothing verified has not earned
// anything, and the card must not say it has.
//
// Run with `node src/panel/learned.test.mjs`.

import assert from "node:assert";

import { install, words } from "./test-support/fake-document.mjs";

install();

const { learned, learnedHere, standing } = await import("./learned.js");

const tests = [];
let failed = 0;
const test = (name, fn) => tests.push([name, fn]);

const job = (id, runs = {}, systems = ["wms.example"]) => ({
  id,
  title: `Job ${id}`,
  systems,
  offered: true,
  runs: { total: 0, held: 0, stale: 0, earned: false, proven: 0, needed: 3, ...runs },
});

/** Every node under `el` whose class list names `name`. */
const find = (el, name, found = []) => {
  if (String(el.className).split(" ").includes(name)) found.push(el);
  for (const kid of el.kids) find(kid, name, found);
  return found;
};

/** The ladder of the one job opened, rung by rung. */
const rungs = (one) =>
  find(learned([one], { open: true, opened: one.id }), "ladder")[0].kids.map(
    (rung) => rung.dataset.state,
  );

test("only the jobs on this host are shown, whole origin or bare host", () => {
  // What the miner actually writes is an origin. Compared as-is against the
  // tab's hostname nothing ever matched, and this card appeared nowhere.
  const jobs = [
    job("a"),
    job("b", {}, ["mail.example"]),
    job("c", {}, ["WMS.example"]),
    job("d", {}, ["https://wms.example"]),
    job("e", {}, ["https://mail.google.com", "https://WMS.example/portal"]),
    job("f", {}, ["https://other.example"]),
  ];
  assert.deepEqual(learnedHere(jobs, "wms.example").map((one) => one.id), [
    "a",
    "c",
    "d",
    "e",
  ]);
  assert.deepEqual(learnedHere(jobs, ""), []);
});

test("only the jobs the backend offers are shown", () => {
  // Seen on QA: Reply to Email and Forward Email were listed here. Chores,
  // mail-only doings, fragments and extra copies of a title are the backend's
  // to rule out (`offered`, the chat's own rule); this card never re-decides.
  const jobs = [
    job("real"),
    { ...job("reply"), title: "Reply to Email", offered: false },
    { ...job("older"), offered: undefined },
  ];
  assert.deepEqual(learnedHere(jobs, "wms.example").map((one) => one.id), ["real"]);
});

test("no job claims a write waits for anybody", () => {
  // Full autonomy from the first run: nothing holds a write for approval, so
  // no rung or sentence may say one does.
  for (const one of [
    job("a"),
    job("b", { total: 4, held: 3, proven: 2 }),
    { id: "c", title: "Job c", systems: ["wms.example"], runs: { total: 4, held: 4 } },
    job("d", { total: 3, held: 3, proven: 3, earned: true }),
  ]) {
    const card = learned([one], { open: true, opened: one.id });
    assert.doesNotMatch(words(card), /ask you|approv|on its own|unasked/i);
  }
});

test("nothing learned here draws nothing", () => {
  assert.equal(learned([]), null);
});

test("Home gets one quiet row, however many jobs were learned", () => {
  // QA 2026-09-29: a full ladder card per learned job cluttered Home.
  const card = learned(["a", "b", "c", "d", "e"].map((id) => job(id)));
  assert.equal(words(card), "5 jobs learned on this page ›");
  assert.equal(card.dataset.tone, undefined, "a row of standing facts is not a loud card");
  const head = card.kids[0];
  assert.equal(head.getAttribute("aria-expanded"), "false");
  assert.equal(find(card, "job").length, 0);
  assert.equal(find(card, "ladder").length, 0);
  assert.equal(words(learned([job("a")])), "1 job learned on this page ›");
});

test("the row opens to one compact line per job, and no ladder", () => {
  const flips = [];
  const closed = learned([job("a")], { onToggle: (open) => flips.push(open) });
  closed.kids[0].listeners.click[0]();
  assert.deepEqual(flips, [true]);

  const card = learned(
    [job("a", { total: 3, held: 3, proven: 2 }), job("b"), job("c", { total: 3, held: 3, proven: 3, earned: true })],
    { open: true },
  );
  assert.equal(card.kids[0].getAttribute("aria-expanded"), "true");
  assert.deepEqual(find(card, "job").map(words), [
    "Job a 2 of 3 runs checked Run it here",
    "Job b not run yet Run it here",
    "Job c proven Run it here",
  ]);
  assert.equal(find(card, "ladder").length, 0, "the ladder is only for the job somebody opened");
});

test("tapping a title opens that job's ladder, and tapping it again closes it", () => {
  const opened = [];
  const card = learned([job("a"), job("b", { total: 5, held: 5 })], {
    open: true,
    opened: "b",
    onOpen: (id) => opened.push(id),
  });
  const [a, b] = find(card, "job");
  assert.equal(find(a, "ladder").length, 0);
  assert.equal(find(b, "ladder").length, 1);
  assert.match(words(b), /0 of 3 runs checked against the warehouse/);
  find(a, "title")[0].listeners.click[0]();
  find(b, "title")[0].listeners.click[0]();
  assert.deepEqual(opened, ["a", null]);
});

test("0 of 3 checked never lights Proven", () => {
  // QA 2026-09-29: "0 of 3 runs checked against the warehouse" under a ladder
  // whose Proven rung glowed. The lit rung is where the job stands.
  const states = rungs(job("a", { total: 5, held: 5, proven: 0 }));
  assert.deepEqual(states, ["done", "done", "now", "todo"]);
  assert.deepEqual(rungs(job("a", { total: 5, held: 5, proven: 2 })), ["done", "done", "now", "todo"]);
});

test("the count is the backend's, capped at what is needed", () => {
  assert.match(standing({ total: 4, held: 3, proven: 2, needed: 3 }), /2 of 3/);
  assert.match(standing({ total: 9, held: 9, proven: 7, needed: 3, earned: false }), /3 of 3/);
});

test("an earned job says so, lights every rung and draws no count", () => {
  const one = job("a", { total: 3, held: 3, proven: 3, earned: true });
  assert.deepEqual(rungs(one), ["done", "done", "done", "done"]);
  const card = learned([one], { open: true, opened: "a" });
  assert.match(words(card), /Checked against the warehouse/);
  assert.equal(find(card, "clean").length, 0);
});

test("a job never run stands on its first rung", () => {
  assert.deepEqual(rungs(job("a")), ["now", "todo", "todo", "todo"]);
});

test("the press names the job, and every press here is quiet", () => {
  const pressed = [];
  const card = learned([job("a"), job("b")], { open: true, onRun: (one) => pressed.push(one.id) });
  const runs = find(card, "job").map((one) =>
    one.querySelectorAll("button").find((button) => button.textContent === "Run it here"),
  );
  assert.deepEqual(runs.map((button) => button.className), ["quiet", "quiet"]);
  runs[1].listeners.click[0]();
  assert.deepEqual(pressed, ["b"]);
});

test("a backend that does not say how far along it is gets no invented number", () => {
  // An older deployment serves runs without `proven`. "0 of 3" there would be
  // this panel making up a fact about somebody's warehouse.
  const one = { id: "a", title: "Job a", systems: ["wms.example"], runs: { total: 4, held: 4 } };
  const card = learned([one], { open: true, opened: "a" });
  assert.doesNotMatch(words(card), /of 3/);
  assert.equal(find(card, "clean").length, 0, "it drew a progress bar out of nothing");
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
  console.error(`learned.test.mjs: ${failed} failed`);
  process.exit(1);
}
console.log(`learned.test.mjs: ok (${tests.length})`);
