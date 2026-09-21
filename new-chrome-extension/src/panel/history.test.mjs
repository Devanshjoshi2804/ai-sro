// Self-check for the history overlay: a glance at what happened, not a log.
//
// Run with `node src/panel/history.test.mjs`.

import assert from "node:assert";

import { install, of, words } from "./test-support/fake-document.mjs";

install();

const { ENDINGS, K_LINES, K_SAID, ago, history } = await import("./history.js");

const tests = [];
let failed = 0;
const test = (name, fn) => tests.push([name, fn]);
const press = (el) => el.listeners.click[0]();

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
  assert.match(
    words(history([run({ outcome: "quarantined" })], {})),
    /quarantined/,
  );
});

test("a job with no title is named by the only thing there is", () => {
  const over = history([run({ title: "" })], { now: NOW });
  assert.match(words(over), /wfl_1/);
});

test("it stops at a screenful; a log is what the console is for", () => {
  const many = Array.from({ length: K_LINES + 6 }, (_, n) =>
    run({ id: `run_${n}` }),
  );
  assert.equal(of(history(many, { now: NOW }), "li").length, K_LINES);
});

test("nothing yet says so without claiming nothing has happened", () => {
  // This browser may simply not have been told. A panel that reports an
  // absence it has not established is one that lies quietly.
  const over = history([], {});
  assert.match(words(over), /Nothing here yet/);
  assert.doesNotMatch(words(over), /never|no runs/i);
});

test("a recent task is a line you can open", () => {
  // These were three spans and nothing to press, over a run the browser was
  // already holding whole -- the list door answers whole rows. A list of
  // titles over records nobody can reach stops one question short of the
  // question somebody opened it to answer: did the customer type one get
  // made.
  const opened = [];
  const over = history([run()], {
    now: NOW,
    onOpen: (one) => opened.push(one.id),
  });
  const [button] = of(over, "button").filter(
    (one) => one.className === "history-line",
  );

  assert.ok(button, "the line is not a control");
  press(button);

  assert.deepEqual(opened, ["run_1"]);
});

test("and it is a button, so a keyboard reaches it", () => {
  // A row that does something is a control, and a control that is not a
  // button is one a keyboard cannot reach and a screen reader does not
  // announce.
  const over = history([run()], { now: NOW });
  const [button] = of(over, "button").filter(
    (one) => one.className === "history-line",
  );

  assert.equal(button.type, "button");
  assert.match(words(button), /Create a Customer Type/);
});

test("a list nobody gave an opener to still draws", () => {
  // `onOpen` is optional, like `onClose`: the overlay is drawn by more than
  // one caller and a missing handler must not be a missing list.
  const over = history([run()], { now: NOW });
  const [button] = of(over, "button").filter(
    (one) => one.className === "history-line",
  );

  press(button);
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

const saidList = (box) =>
  of(box, "ul").find((one) => one.className === "history-said");

test("this browser's own refusals are under the runs", () => {
  // The lines are already kept and already shipped -- the heartbeat carries
  // them and the deployment writes them beside its own. What was missing is
  // the operator's copy: they stand in front of the browser that refused,
  // being told nothing, while the only account of it goes to a server they
  // cannot read.
  const box = history([run()], {
    said: [
      "warn a command was refused [command=cmd_9f21 kind=ui.perform run=run_1 error=no_tab_for_system]",
    ],
    now: NOW,
  });

  const said = saidList(box);
  assert.ok(said, "the operator's own copy is not there");
  assert.equal(of(said, "li").length, 1);
  // As it was written: an operator reading one to somebody on a call is
  // reading the same string that is in the deployment's log.
  assert.match(words(said), /no_tab_for_system/);
  assert.match(words(said), /cmd_9f21/);
});

test("newest first, and only the last few", () => {
  const many = Array.from({ length: 20 }, (_, n) => `warn refusal ${n}`);

  const box = history([], { said: many, now: NOW });

  const rows = of(saidList(box), "li");
  assert.equal(rows.length, K_SAID);
  assert.match(words(rows[0]), /refusal 19$/, "the newest is first");
});

test("nothing said draws no heading", () => {
  // A heading over an empty list is a panel telling somebody where a thing
  // would be if it existed.
  const box = history([run()], { now: NOW });

  assert.equal(saidList(box), undefined);
  assert.equal(of(box, "h4").length, 0);
});

test("a browser with no runs but something to say still says it", () => {
  const box = history([], { said: ["error a command blew up"], now: NOW });

  assert.match(words(box), /a command blew up/);
  assert.doesNotMatch(words(box), /Nothing here yet/);
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
