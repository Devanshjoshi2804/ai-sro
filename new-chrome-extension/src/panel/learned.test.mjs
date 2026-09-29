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

const rungs = (card) =>
  card.kids
    .find((kid) => kid.className === "job")
    .kids.find((kid) => kid.className === "ladder")
    .kids.map((rung) => rung.dataset.state);

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

test("no card claims a write waits for anybody", () => {
  // Full autonomy from the first run: nothing holds a write for approval, so
  // no rung or sentence may say one does.
  const cards = [
    learned([job("a")]),
    learned([job("b", { total: 4, held: 3, proven: 2 })]),
    learned([{ id: "c", title: "Job c", systems: ["wms.example"], runs: { total: 4, held: 4 } }]),
    learned([job("d", { total: 3, held: 3, proven: 3, earned: true })]),
  ];
  for (const card of cards) {
    assert.doesNotMatch(words(card), /ask you|approv|on its own|unasked/i);
  }
});

test("nothing learned here draws nothing", () => {
  assert.equal(learned([]), null);
});

test("held runs with nothing verified have earned nothing", () => {
  const card = learned([job("a", { total: 5, held: 5, proven: 0 })]);
  assert.deepEqual(rungs(card), ["done", "done", "done", "now"]);
  assert.match(words(card), /0 of 3 runs checked against the warehouse/);
});

test("the count is the backend's, capped at what is needed", () => {
  assert.match(standing({ total: 4, held: 3, proven: 2, needed: 3 }), /2 of 3/);
  assert.match(standing({ total: 9, held: 9, proven: 7, needed: 3, earned: false }), /3 of 3/);
});

test("an earned job says so and draws no count", () => {
  const card = learned([job("a", { total: 3, held: 3, proven: 3, earned: true })]);
  assert.deepEqual(rungs(card), ["done", "done", "done", "done"]);
  assert.match(words(card), /Checked against the warehouse/);
  assert.equal(card.dataset.tone, undefined, "an earned job is not the loud card");
});

test("a job never run is at its second rung", () => {
  const card = learned([job("a")]);
  assert.deepEqual(rungs(card), ["done", "now", "todo", "todo"]);
  assert.equal(card.dataset.tone, "live");
});

test("one primary press per card, and the press names the job", () => {
  const pressed = [];
  const card = learned([job("a"), job("b")], { onRun: (one) => pressed.push(one.id) });
  const runs = card.kids
    .filter((kid) => kid.className === "job")
    .map((one) => one.kids.find((kid) => kid.className === "row").kids[0]);
  assert.deepEqual(runs.map((button) => button.className), ["", "quiet"]);
  runs[1].listeners.click[0]();
  assert.deepEqual(pressed, ["b"]);
});

test("a backend that does not say how far along it is gets no invented number", () => {
  // An older deployment serves runs without `proven`. "0 of 3" there would be
  // this panel making up a fact about somebody's warehouse.
  const card = learned([
    { id: "a", title: "Job a", systems: ["wms.example"], runs: { total: 4, held: 4 } },
  ]);
  assert.doesNotMatch(words(card), /of 3/);
  assert.equal(
    card.kids.find((kid) => kid.className === "job").kids.some((kid) => kid.className === "clean"),
    false,
    "it drew a progress bar out of nothing",
  );
});

test("more than three is a line, not more cards", () => {
  const card = learned(["a", "b", "c", "d", "e"].map((id) => job(id)));
  assert.equal(card.kids.filter((kid) => kid.className === "job").length, 3);
  assert.match(words(card), /2 more learned here/);
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
