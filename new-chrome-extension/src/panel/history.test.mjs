// Self-check for the history overlay: a glance at what happened, not a log.
//
// Run with `node src/panel/history.test.mjs`.

import assert from "node:assert";

import { install, of, words } from "./test-support/fake-document.mjs";

install();

const { ENDINGS, K_LINES, K_SAID, ago, history } = await import("./history.js");
// The other side of the seam, and the reason this import is here: the list is
// never given a backend row. It is given whatever `asPanelRun` kept.
const { asPanelRun } = await import("../background/api.js");

const tests = [];
let failed = 0;
const test = (name, fn) => tests.push([name, fn]);
const press = (el) => el.listeners.click[0]();

const NOW = Date.parse("2026-09-17T10:00:00Z");
const HOUR = 3600000;
const iso = (at) => new Date(at).toISOString();
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
  // `onOpen` is optional: the pane is drawn by more than one caller and a
  // missing handler must not be a missing list.
  const over = history([run()], { now: NOW });
  const [button] = of(over, "button").filter(
    (one) => one.className === "history-line",
  );

  press(button);
});

test("there is no way out, because it is a place", () => {
  // It was an overlay with a ✕ and an Escape handler. A pane is left by going
  // somewhere else, which is what the navigation is for -- a second way out,
  // on the surface itself, is a control that has to be found and then
  // explained. And `role="dialog"` told a screen reader it had been
  // interrupted and must get out; this is somewhere somebody walked to.
  const over = history([run()], { now: NOW });

  assert.equal(over.getAttribute("role"), "region");
  assert.equal(
    of(over, "button").filter((one) => one.textContent === "✕").length,
    0,
    "a pane grew a dismiss control",
  );
  assert.equal(over.listeners.keydown, undefined, "a pane listened for Escape");
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
  // The heading this is about, and not every heading: the list is grouped by
  // the day a run happened, and those are headings too.
  assert.equal(
    of(box, "h4").filter((one) => one.className === "history-said-head").length,
    0,
  );
});

test("the list is drawn from what the worker actually keeps, not from the backend row", () => {
  // How this broke: `asPanelRun` is a whitelist -- what is not named in it
  // does not reach the panel -- and it named neither `started_at` nor a time
  // of any kind. So `Recent tasks` drew twelve lines reading `Log in to
  // Keycloak`, no outcome and no time on any of them, while the backend was
  // answering all three on every row. Measured on the deployment 2026-09-21.
  //
  // The mapping's own comment records that this has happened three times
  // before, to three other fields. A test across the seam is cheaper than a
  // fourth paragraph.
  const fromTheBackend = {
    id: "run_9",
    workflow_id: "wfl_1",
    outcome: "failed",
    started_at: iso(NOW - 3 * HOUR),
    finished_at: iso(NOW - 3 * HOUR + 60000),
    steps: [],
  };

  const box = history([{ ...asPanelRun(fromTheBackend), title: "Log in" }], {
    now: NOW,
  });

  const said = words(box);
  assert.match(said, /Log in/);
  assert.match(said, /failed/, "the line said nothing of how it ended");
  assert.match(said, /3h ago/, "the line said nothing of when it happened");
});

test("the days are named, so twelve lines of the same job are twelve distinguishable lines", () => {
  // What this pane looked like without it, measured on the deployment
  // 2026-09-21: twelve entries reading `Log in to Keycloak`, no outcome and
  // no time on any of them, because the row the list is given carried
  // neither `status` nor `started_at`.
  const box = history(
    [
      run({ id: "r1", status: "held", started_at: iso(NOW - 2 * HOUR) }),
      run({ id: "r2", status: "failed", started_at: iso(NOW - 26 * HOUR) }),
    ],
    { now: NOW },
  );

  const days = of(box, "h4").map((one) => words(one));
  assert.deepEqual(days, ["Today · 1", "Yesterday · 1"]);
  assert.match(words(box), /done/);
  assert.match(words(box), /failed/);
  assert.match(words(box), /2h ago/);
});

test("the one that went wrong is findable in a list where every line reads the same", () => {
  const box = history(
    [
      run({ id: "r1", status: "held" }),
      run({ id: "r2", status: "failed" }),
      run({ id: "r3", status: "stopped" }),
    ],
    { now: NOW },
  );

  const toned = [];
  const walk = (el) => {
    if (el?.dataset?.ended !== undefined && el.tag === "li")
      toned.push(el.dataset.ended);
    for (const kid of el?.kids || []) walk(kid);
  };
  walk(box);
  assert.deepEqual(toned, ["", "bad", "asking"]);
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
