// Self-check for the run card: a run that changes while somebody watches it.
//
// The panel used to say "step 4 of 7" and a progress bar. A run drives the
// operator's own browser, in front of them, and what they need is which step it
// is on, whether the last one was confirmed, and a way to argue with the next
// one before it is sent.
//
// The two properties worth holding: a step already sent cannot be changed, and
// a step marked done is only marked confirmed when something checked it.
//
// Run with `node src/panel/run-card.test.mjs`.

import assert from "node:assert";

import { asMarkup, install, of, words } from "./test-support/fake-document.mjs";

install();

const { glyphFor, runCard } = await import("./run-card.js");

const SKILL = {
  name: "Create a supplier",
  latest: {
    steps: [
      { index: 0, intent: "open the form", ui_plan: {} },
      { index: 1, intent: "fill four fields", network_plan: { body: "{{address}}" } },
      { index: 2, intent: "save", network_plan: { body: "{{name}}" } },
    ],
  },
};

const RUNNING = {
  id: "run-1",
  status: "running",
  parameters: { address: "A000144886", name: "Acme" },
  steps: [{ index: 0, medium: "network", disposition: "performed", assertion_failures: [] }],
};

/** A run the rig drove. It has no skill in this browser -- the plan was the
 * model's, one step at a time -- so the steps are the run's own record, and
 * `outcome` is the rig's verdict rather than the backend's disposition. */
const RIG = {
  id: "run_a1b2",
  source: "rig",
  status: "running",
  steps: [
    { index: 0, outcome: "held", says: "open the supplier form", reason: "" },
    { index: 1, outcome: "withheld", says: "save the supplier", reason: "dry run" },
  ],
  withheld: [{ origin: "https://wms.test" }],
};

const tests = [];
const test = (name, fn) => tests.push([name, fn]);

test("a step says what happened to it, and confirmed is not the same as done", () => {
  // The distinction the whole ladder rests on. A step that went out and came
  // back 200 has been performed; a step whose effect something read back has
  // been confirmed. Drawing both as a tick would be the panel claiming the
  // stronger of the two.
  assert.equal(glyphFor(null), "○");
  assert.equal(glyphFor({ disposition: "performed", assertion_failures: [], confirmed: true }), "✓");
  assert.equal(
    glyphFor({ disposition: "performed", assertion_failures: [], confirmed: false }),
    "✓!",
    "a step nothing checked was drawn as though something had",
  );
  assert.equal(
    glyphFor({ disposition: "performed", assertion_failures: ["status was 500"], confirmed: true }),
    "✓!",
    "a step whose check failed was drawn as confirmed",
  );
  assert.equal(glyphFor({ disposition: "failed" }), "✗");
  assert.equal(glyphFor({ disposition: "withheld" }), "⏸");
});

test("every step of the plan is a row, and the one in flight says so", () => {
  const card = runCard({ run: RUNNING, skill: SKILL, message: { text: "Running" } }, {});
  const rows = card.kids.filter((kid) => kid.className === "step");

  assert.equal(rows.length, 3, "a run shows what is still to come, not only what is done");
  assert.equal(rows[0].kids[0].textContent, "✓!", "nothing read this back");
  assert.equal(rows[1].kids[0].textContent, "●", "the step in flight");
  assert.equal(rows[2].kids[0].textContent, "○");
  assert.match(words(rows[2]), /save/);
});

test("a step not yet sent can be argued with; one already sent cannot", () => {
  // The point of the card. What has gone to the warehouse has gone, and a
  // control offering to change it would be offering something this system
  // cannot do.
  const changed = [];
  const card = runCard(
    { run: RUNNING, skill: SKILL, message: {} },
    { onChange: (...args) => changed.push(args) },
  );
  const rows = card.kids.filter((kid) => kid.className === "step");
  const changeOn = (row) => row.kids.find((kid) => kid.textContent === "change");

  assert.equal(changeOn(rows[0]), undefined, "a step already sent offered to be changed");
  assert.equal(
    changeOn(rows[1]),
    undefined,
    "the step in flight offered to be changed -- its request may already be in the air",
  );
  assert.ok(changeOn(rows[2]), "a step still to come offered nothing");

  changeOn(rows[2]).listeners.click[0]();
  const [field] = of(rows[2], "input");
  assert.equal(field.placeholder, "name", "the field is the value that step renders");
  assert.equal(field.value, "Acme", "it starts at what the run would use");

  field.value = "Acme Fasteners";
  field.listeners.change[0]();
  assert.deepEqual(changed, [["run-1", "name", "Acme Fasteners"]]);
});

test("a step with no values of its own has nothing to change", () => {
  const card = runCard(
    { run: { ...RUNNING, steps: [] }, skill: SKILL, message: {} },
    { onChange: () => {} },
  );
  const [first] = card.kids.filter((kid) => kid.className === "step");
  assert.equal(
    first.kids.find((kid) => kid.textContent === "change"),
    undefined,
    "a click with no parameters in it offered a box to type in",
  );
});

test("a finished run stops offering to be steered", () => {
  const card = runCard({ run: { ...RUNNING, status: "succeeded" }, skill: SKILL, message: {} }, {});
  assert.deepEqual(
    of(card, "button").map((button) => button.textContent),
    [],
    "a run that is over still offered to be stopped",
  );
});

test("a live run can be stopped, and the press decides nothing itself", () => {
  const pressed = [];
  const card = runCard(
    { run: RUNNING, skill: SKILL, message: {} },
    { onPress: (...args) => pressed.push(args) },
  );
  const stop = of(card, "button").find((button) => button.textContent === "Stop");
  assert.ok(stop);
  stop.listeners.click[0]();
  assert.equal(pressed[0][0], "stop");
  assert.equal(pressed[0][1], RUNNING);
});

test("something said to the run appears under the step it arrived during", () => {
  const card = runCard(
    { run: RUNNING, skill: SKILL, message: {}, notes: [{ at_step: 1, text: "use the north yard" }] },
    {},
  );
  const rows = card.kids.filter((kid) => kid.className === "step");
  assert.match(words(rows[1]), /use the north yard/);
  assert.doesNotMatch(words(rows[0]), /north yard/);
});

test("a run whose skill is unknown still draws what it has", () => {
  // The skill fetch can fail, or lag the run by a moment. A card that threw
  // here would take the ledger with it.
  const card = runCard({ run: RUNNING, skill: null, message: { text: "Running" } }, {});
  assert.match(words(card), /Running/);
  assert.deepEqual(asMarkup, []);
});

test("a rig run draws its own steps -- there is no skill in this browser to draw", () => {
  const card = runCard({ run: RIG, skill: null, message: {} }, {});
  const rows = card.kids.filter((kid) => kid.className === "step");
  assert.equal(rows.length, 2, "a rig run drew nothing: it has no skill, only its own record");
  assert.match(words(rows[0]), /open the supplier form/);
  assert.equal(rows[0].kids[0].textContent, "✓", "a step whose reading held was not drawn as held");
  assert.equal(rows[1].kids[0].textContent, "⏸", "a withheld step was not drawn as withheld");
  assert.deepEqual(asMarkup, [], "run text reached the page as markup");
});

test("a rig run can be stopped, and offers nothing the rig cannot do", () => {
  const pressed = [];
  const card = runCard({ run: RIG, skill: null, message: {} }, { onPress: (...a) => pressed.push(a) });
  const labels = of(card, "button").map((button) => button.textContent);
  assert.ok(labels.includes("Stop"), "a rig run that is happening could not be stopped");
  assert.ok(
    !labels.includes("Stop after this step"),
    "a rig run offered a pause the rig has no way to honour",
  );
  of(card, "button")
    .find((button) => button.textContent === "Stop")
    .listeners.click[0]();
  assert.equal(pressed[0][0], "stop");
  assert.equal(pressed[0][1], RIG);
});

test("a finished rig run offers no reversal, and says what the dry run held back", () => {
  const card = runCard({ run: { ...RIG, status: "held" }, skill: null, message: {} }, {});
  assert.deepEqual(
    of(card, "button").map((button) => button.textContent),
    [],
    "a finished rig run offered a press -- the rig has no reversal and no 'It's wrong'",
  );
  assert.doesNotMatch(words(card), /wrong|Undo/i, "a rig run offered an undo it cannot perform");
  assert.match(
    words(card),
    /dry run — 1 write shown on the rig, not sent/,
    "a dry run did not say what it withheld",
  );
});

test("an awaiting step shows what would go out and asks for approval", () => {
  // The whole of the approval gate, seen from the panel: the write has not
  // gone, what it would send is in front of the operator in words, and the two
  // answers are on the row rather than at the bottom of the card. A press
  // decides nothing here -- `panel.js` is what carries it to the worker, which
  // is where the rig's bearer lives.
  const run = {
    id: "run_1",
    source: "rig",
    status: "running",
    steps: [
      { index: 0, outcome: "held", says: "type the code" },
      {
        index: 1,
        outcome: "awaiting",
        says: "save",
        sent: {
          kind: "ui.perform",
          payload: {
            action: "click",
            locators: [{ strategy: "role_and_name", query: "button|Save" }],
          },
        },
      },
    ],
  };
  const pressed = [];
  const card = runCard({ run }, { onPress: (answer) => pressed.push(answer) });
  const row = card.kids.filter((kid) => kid.className === "step")[1];

  assert.equal(row.kids[0].textContent, "⏸", "a step waiting on a person was not drawn as waiting");
  assert.match(words(row), /click button\|Save/, "the operator was asked to approve an unnamed write");

  const approve = of(row, "button").find((button) => button.textContent === "Approve");
  const stop = of(row, "button").find((button) => button.textContent === "Stop");
  assert.ok(approve, "a step waiting for approval offered no way to give it");
  assert.ok(stop, "a step waiting for approval offered no way to refuse it");

  approve.listeners.click[0]();
  assert.deepEqual(pressed, ["approve"]);
  assert.deepEqual(asMarkup, [], "a planned command reached the page as markup");
});

test("a step the operator did is drawn done, not in flight", () => {
  // The operator went and did it themselves while the rig waited. That step is
  // over -- drawing it as the one in flight would leave the panel pointing at
  // a write nobody is going to send.
  const run = {
    id: "run_1",
    source: "rig",
    status: "running",
    steps: [{ index: 0, outcome: "done_by_operator", says: "type the code" }],
  };
  const card = runCard({ run }, {});
  const row = card.kids.filter((kid) => kid.className === "step")[0];
  assert.equal(row.kids[0].textContent, "✓", "a step the operator did was not drawn as done");
  assert.deepEqual(
    of(row, "button").map((button) => button.textContent),
    [],
    "a step nothing is waiting on offered an approval",
  );
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
  console.error(`run-card.test.mjs: ${failed} failed`);
  process.exit(1);
}
console.log(`run-card.test.mjs: ok (${tests.length})`);
