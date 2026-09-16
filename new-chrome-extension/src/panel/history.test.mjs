// Self-check for the history overlay: a glance at what happened, not a log.
//
// Run with `node src/panel/history.test.mjs`.

import assert from "node:assert";

import { install, of, words } from "./test-support/fake-document.mjs";

install();

const { ENDINGS, K_LINES, ago, history } = await import("./history.js");

const tests = [];
let failed = 0;
const test = (name, fn) => tests.push([name, fn]);

const NOW = Date.parse("2026-09-17T10:00:00Z");
const run = (over = {}) => ({
  id: "run_1",
  workflow_id: "wfl_1",
  title: "Create a Customer Type",
  outcome: "held",
  started_at: "2026-09-17T09:58:00Z",
  ...over,
});

test("a line each: what it was, what came of it, and when", () => {
  const over = history([run()], { now: NOW });

  const line = of(over, "li")[0];
  assert.ok(line, "nothing was drawn for a run that happened");
  assert.match(words(line), /Create a Customer Type/);
  assert.match(words(line), /done/, "it did not say what came of it");
  assert.match(words(line), /2m ago/);
});

test("the rig's own words, not the backend's", () => {
  // `held` is a run every step of which held. Calling it "succeeded" would be
  // this panel translating a verdict it did not make.
  assert.equal(ENDINGS.held, "done");
  assert.equal(ENDINGS.stopped, "stopped to ask");
  // And an outcome this browser has never heard of is shown as it came: a
  // deployment may add one, and drawing nothing would hide the run.
  assert.match(words(history([run({ outcome: "quarantined" })], {})), /quarantined/);
});

test("a job with no title is named by the only thing there is", () => {
  const over = history([run({ title: "" })], { now: NOW });
  assert.match(words(over), /wfl_1/);
});

test("it stops at a screenful; a log is what the console is for", () => {
  const many = Array.from({ length: K_LINES + 6 }, (_, n) => run({ id: `run_${n}` }));
  assert.equal(of(history(many, { now: NOW }), "li").length, K_LINES);
});

test("nothing yet says so without claiming nothing has happened", () => {
  // This browser may simply not have been told. A panel that reports an
  // absence it has not established is one that lies quietly.
  const over = history([], {});
  assert.match(words(over), /Nothing here yet/);
  assert.doesNotMatch(words(over), /never|no runs/i);
});

test("the way out is a press and the escape key", () => {
  // An overlay somebody can only dismiss by finding one small button is a trap
  // on a 360-pixel panel.
  const shut = [];
  const over = history([run()], { onClose: () => shut.push(true), now: NOW });

  of(over, "button")[0].listeners.click[0]();
  over.listeners.keydown[0]({ key: "Escape" });

  assert.equal(shut.length, 2);
});

test("how long ago, in the words somebody would use", () => {
  assert.equal(ago("2026-09-17T09:59:40Z", NOW), "just now");
  assert.equal(ago("2026-09-17T09:30:00Z", NOW), "30m ago");
  assert.equal(ago("2026-09-17T04:00:00Z", NOW), "6h ago");
  assert.equal(ago("2026-09-14T10:00:00Z", NOW), "3d ago");
  // A row whose time this browser cannot read says nothing rather than
  // "NaN ago".
  assert.equal(ago("", NOW), "");
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
  console.error(`history.test.mjs: ${failed} failed`);
  process.exit(1);
}
console.log(`history.test.mjs: ok (${tests.length})`);
