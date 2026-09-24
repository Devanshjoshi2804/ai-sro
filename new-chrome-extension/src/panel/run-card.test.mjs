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

test("the step that is happening is marked as happening", () => {
  // A run in flight and a run that stopped on a live step draw the identical
  // dot. "Still going" is the question somebody watching actually has, so the
  // live one is marked and the stylesheet makes it breathe -- and stops, for
  // anybody who asked for less movement.
  const running = runCard({
    // A backend run, whose rows come from the skill it is performing. A rig
    // run plans one step at a time, so its rows ARE its record and an
    // unrecorded step has nothing to draw.
    run: { id: "r1", status: "running", steps: [], items: [] },
    skill: {
      latest: { steps: [{ index: 0, intent: "type the code" }, { index: 1, intent: "save" }] },
    },
    message: null,
  });
  const stopped = runCard({
    run: { id: "r2", status: "stopped", steps: [], items: [] },
    skill: { latest: { steps: [{ index: 0, intent: "type the code" }] } },
    message: null,
  });

  const lit = (card) =>
    of(card, "span").filter((one) => one.dataset.live === "true").length;

  assert.equal(lit(running), 1, "nothing said which step was happening");
  assert.equal(lit(stopped), 0, "a stopped run had a step marked live");
});

test("a value nobody typed says where it was read", () => {
  // Recorded since the gather existed and shown by nothing: the run carries
  // the message id and the words a value was quoted from, and the person
  // deciding whether it did the right thing could not see either.
  const card = runCard({
    run: {
      id: "run-1", status: "running", source: "rig", steps: [], items: [],
      gathered: {
        "Customer Type": {
          value: "GPP",
          from_message: "1a0a987fc91c3203",
          quoting: "a customer type :- GPP",
        },
      },
    },
    skill: null,
    message: { text: "Create a Customer Type" },
  });

  assert.match(words(card), /Customer Type: GPP — read from your mail/);
  // The span they check the reading against, not the mail: that is in their
  // mailbox where it already was.
  assert.match(words(card), /a customer type :- GPP/);
});

test("a run whose values were all typed says nothing about provenance", () => {
  // "They typed it and they meant it" is not news, and a line per value is a
  // card nobody reads.
  const card = runCard({
    run: { id: "run-2", status: "running", source: "rig", steps: [], items: [] },
    skill: null,
    message: { text: "Create a Customer Type" },
  });

  assert.doesNotMatch(words(card), /read from your mail/);
});

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
    /dry run — 1 write shown here, not sent/,
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

test("a mail waiting for approval is shown whole before it can be sent", () => {
  // Approving it is sending it, and its words are a model's.
  const run = {
    id: "run_1",
    source: "rig",
    status: "running",
    steps: [
      {
        index: 0,
        outcome: "awaiting",
        says: "Click Send",
        sent: {
          kind: "mail.send",
          payload: { to: "alex@example.com", subject: "Re: client", body: "SROCLS8 is set up." },
        },
      },
    ],
  };
  const card = runCard({ run }, {});
  const row = card.kids.filter((kid) => kid.className === "step")[0];

  assert.match(words(row), /send to alex@example\.com/);
  assert.match(words(row), /Re: client/);
  assert.match(words(row), /SROCLS8 is set up\./, "the body was not shown before approval");
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

test("a rig row says what it was matched to and what it cost, and never prices a call it could not", () => {
  const run = {
    id: "run_1",
    source: "rig",
    status: "held",
    steps: [
      { index: 0, outcome: "held", says: "open the form", matched_by: "step 2", cost_usd: 0.0123 },
      // A call that never returned. Drawing this as $0.0000 would be the panel
      // reporting a cost the rig explicitly said it could not establish.
      { index: 1, outcome: "held", says: "save", cost_usd: null, unpriced: true },
    ],
  };
  const card = runCard({ run }, {});
  const rows = card.kids.filter((kid) => kid.className === "step");
  assert.match(words(rows[0]), /step 2/, "the row did not say which taught step it matched");
  assert.match(words(rows[0]), /\$0\.0123/, "the row did not say what the step cost");
  assert.match(words(rows[1]), /unpriced/, "a call that never returned was not said to be unpriced");
  assert.doesNotMatch(words(rows[1]), /\$/, "a call with no established cost was given a price");
  assert.deepEqual(asMarkup, [], "the rig's own accounting reached the page as markup");
});

test("a step found by sight, or on a page that moved, says so on its row", () => {
  const run = {
    id: "run_1",
    source: "rig",
    status: "held",
    steps: [
      { index: 0, outcome: "held", says: "type the code", matched_by: "sight", stale: true, cost_usd: 0.02 },
      { index: 1, outcome: "held", says: "save", matched_by: "css_path", stale: true, cost_usd: 0.01 },
      { index: 2, outcome: "held", says: "close", matched_by: "role_and_name", stale: false, cost_usd: 0.01 },
    ],
  };
  const rows = runCard({ run }, {}).kids.filter((kid) => kid.className === "step");
  assert.match(words(rows[0]), /found by sight/, "a workaround the operator should see");
  assert.match(words(rows[0]), /page moved/);
  assert.doesNotMatch(words(rows[0]), /\bsight\b(?! )/, "the bare strategy name is not the word");
  assert.match(words(rows[1]), /css_path · page moved/);
  assert.doesNotMatch(words(rows[2]), /page moved|sight/);
});

test("only the step the rig is waiting on is offered an approval", () => {
  // Two ways to draw an Approve where nothing is waiting. A step already held
  // is over; an `awaiting` row on a run that has since ended is a record, and
  // pressing it would approve a run that is not running.
  const live = {
    id: "run_1",
    source: "rig",
    status: "running",
    steps: [{ index: 0, outcome: "held", says: "open the form" }],
  };
  const over = {
    id: "run_1",
    source: "rig",
    status: "aborted",
    steps: [{ index: 0, outcome: "awaiting", says: "save", sent: { kind: "ui.perform", payload: {} } }],
  };
  const approvesIn = (run) =>
    runCard({ run }, {})
      .kids.filter((kid) => kid.className === "step")
      .flatMap((row) => of(row, "button").map((button) => button.textContent));

  assert.deepEqual(approvesIn(live), [], "a step already held offered an approval");
  assert.deepEqual(approvesIn(over), [], "a run that has ended offered to approve a write");
});

test("drawn under a card that already stops the run, the card-level Stop is not repeated", () => {
  const run = { id: "run_1", source: "rig", status: "running", steps: [{ index: 0, outcome: "held", says: "s" }] };
  const withStop = runCard({ run }, {});
  const without = runCard({ run }, { stop: false });
  const labels = (card) => [...card.querySelectorAll("button")].map((b) => b.textContent);
  assert.ok(labels(withStop).includes("Stop"));
  assert.ok(!labels(without).includes("Stop"));
});


test("a step refused for want of a password asks the person watching for it", async () => {
  // The refusal a real operator hit. The step types a credential, the vault
  // holds none, and the run ends -- and what the panel used to draw was a
  // sentence naming a vault key, which is actionable by whoever deploys this
  // system and by nobody standing in a warehouse. The field is here because
  // the person who knows the password is here.
  const run = {
    id: "run_1",
    source: "rig",
    status: "failed",
    steps: [
      { index: 0, outcome: "held", says: "type the username" },
      {
        index: 1,
        outcome: "failed",
        says: "Type the password.",
        sent: {
          kind: "none",
          payload: {
            needs_secret: {
              system: "keycloak.test",
              field: "password",
              key: "new/keycloak.test/password",
            },
          },
        },
      },
    ],
  };
  const kept = [];
  const card = runCard(
    { run },
    {
      onSecret: (one) => {
        kept.push(one);
        return { ok: true };
      },
    },
  );
  const row = card.kids.filter((kid) => kid.className === "step")[1];

  assert.match(
    words(row),
    /needs your password for keycloak\.test/,
    "the row did not say which password it wanted, in words anybody can act on",
  );
  assert.ok(
    !words(row).includes("new/keycloak.test/password"),
    "the vault key was put in front of somebody who cannot use it",
  );

  const field = of(row, "input")[0];
  assert.equal(field.type, "password", "a password was asked for in a field that shows it");
  field.value = "not-in-any-fixture-9c41";
  const save = of(row, "button").find((button) => button.textContent === "Save for this job");
  await save.listeners.click[0]();

  assert.deepEqual(kept, [
    {
      system: "keycloak.test",
      field: "password",
      value: "not-in-any-fixture-9c41",
      once: false,
      runId: "run_1",
    },
  ]);
  assert.equal(field.value, "", "the password was left sitting in the panel");
  assert.match(words(row), /Kept\./, "saving a password said nothing back");
  assert.deepEqual(asMarkup, [], "a password reached the page as markup");

  // And the other answer: lent for the next run rather than kept.
  //
  // Offering only "Save for this job" made every password a permanent one,
  // which is a decision nobody was asked about -- and on a system whose
  // credential is not this deployment's to hold, storing it was the only way
  // through.
  field.value = "lent-9c41";
  const once = of(row, "button").find(
    (button) => button.textContent === "Just this once",
  );
  assert.ok(once, "the card offered no way to lend a password for one run");
  await once.listeners.click[0]();

  assert.deepEqual(kept[1], {
    system: "keycloak.test",
    field: "password",
    value: "lent-9c41",
    once: true,
    runId: "run_1",
  });
  assert.equal(field.value, "", "the password was left sitting in the panel");
  assert.match(words(row), /next run only/, "it did not say what it did with it");
  assert.deepEqual(asMarkup, [], "a password reached the page as markup");
});

test("a blank box sends nothing, and a vault that refuses says so", async () => {
  const run = {
    id: "run_2",
    source: "rig",
    status: "failed",
    steps: [
      {
        index: 0,
        outcome: "failed",
        says: "Type the password.",
        sent: { kind: "none", payload: { needs_secret: { system: "wms.test", field: "password" } } },
      },
    ],
  };
  const kept = [];
  const card = runCard(
    { run },
    {
      onSecret: (one) => {
        kept.push(one);
        return { ok: false, error: "the secret store refused a write" };
      },
    },
  );
  const row = card.kids.filter((kid) => kid.className === "step")[0];
  const save = of(row, "button").find((button) => button.textContent === "Save for this job");

  await save.listeners.click[0]();
  assert.deepEqual(kept, [], "an empty box was sent to the vault as a password");

  of(row, "input")[0].value = "x";
  await save.listeners.click[0]();
  assert.match(
    words(row),
    /could not be kept: the secret store refused a write/,
    "a vault that refused let the operator believe their password was stored",
  );
});

test("a job done once per thing says which thing each run of the block is for", () => {
  // Nineteen rows of "Click Save." with nothing saying which record each
  // belongs to is a run nobody can read. The question somebody watching has is
  // not which step it is on -- it is how many of the three are done.
  const run = {
    id: "run_1",
    source: "rig",
    status: "running",
    items: [
      { code: "8SITDWN2", name: "8-Sitdown Fork" },
      { code: "8STANDUP2", name: "8-Stand Up Fork" },
    ],
    steps: [
      { index: 0, item: null, of_step: 0, outcome: "held", says: "Read the mail." },
      { index: 1, item: 0, of_step: 1, outcome: "held", says: "Click Add." },
      { index: 2, item: 0, of_step: 2, outcome: "held", says: "Click Save." },
      { index: 3, item: 1, of_step: 1, outcome: "held", says: "Click Add." },
      { index: 4, item: 1, of_step: 2, says: "Click Save." },
    ],
  };

  const card = runCard({ run });
  const headings = card.kids.filter((kid) => kid.className === "thing").map((kid) => kid.textContent);

  assert.deepEqual(headings, ["1 of 2 — 8SITDWN2 8-Sitdown Fork", "2 of 2 — 8STANDUP2 8-Stand Up Fork"]);
  // One line per thing, not one per row: the block's six rows sit under it.
  assert.equal(card.kids.filter((kid) => kid.className === "step").length, 5);
  // And the step that is not part of the block has no line above it: the
  // first heading comes after it, where the block begins.
  const drawn = card.kids.map((kid) => kid.className);
  assert.equal(drawn.indexOf("thing") > drawn.indexOf("step"), true, (
    "the mail, which was read once, was given a heading of its own"
  ));
});

test("a job that does one thing once draws exactly what it always did", () => {
  const run = {
    id: "run_2",
    source: "rig",
    status: "running",
    items: [],
    steps: [
      { index: 0, item: null, outcome: "held", says: "type the code" },
      { index: 1, item: null, says: "save" },
    ],
  };

  const card = runCard({ run });

  assert.deepEqual(card.kids.filter((kid) => kid.className === "thing"), []);
});

test("a finished run says which records it made", () => {
  // Nothing in this system can take a warehouse record back. The guards in
  // front of a run stop wrong records being made and do nothing about one that
  // was, so a run says what it made in the warehouse's own words and a person
  // can go and look.
  const run = {
    id: "run_1",
    source: "rig",
    status: "held",
    items: [{ code: "8SITDWN2" }, { code: "8STANDUP2" }],
    steps: [
      { index: 0, item: 0, outcome: "held", says: "Click Save.", made: { equipmentTypeId: "4471" } },
      { index: 1, item: 1, outcome: "held", says: "Click Save.", made: { equipmentTypeId: "4472" } },
    ],
  };

  const card = runCard({ run });

  assert.match(words(card), /Made 2 records/);
  // In the warehouse's own field names, and whatever fields it sent. This was
  // the values alone -- "made 2 records: 4471, 4472" -- which drops the half
  // that says what each value is, one line before somebody reads it.
  assert.match(words(card), /equipmentTypeId: 4471/);
  assert.match(words(card), /equipmentTypeId: 4472/);
  assert.match(words(card), /Nothing here can take them back/, (
    "an operator who has just watched two records be made has to know the"
    + " taking-back is theirs to do"
  ));
});

test("where a job of theirs takes the records back, the card says so", () => {
  const run = {
    id: "run_3",
    source: "rig",
    status: "held",
    undo: "wfl_delete",
    steps: [{ index: 0, outcome: "held", says: "Click Save.", made: { id: "4471" } }],
  };

  const said = words(runCard({ run }));

  assert.match(said, /A job you have done before takes these back/);
  // Said, not drawn as a button: what an undo has to do is address each record
  // by whatever the warehouse called it, and a wrong mapping deletes the wrong
  // record.
  assert.ok(!of(runCard({ run }), "button").some((one) => /undo/i.test(one.textContent)));
});

test("a run that made nothing says nothing about records", () => {
  const run = {
    id: "run_2",
    source: "rig",
    status: "held",
    steps: [{ index: 0, outcome: "held", says: "open the form", made: {} }],
  };

  assert.ok(!words(runCard({ run })).includes("made"));
});

test("a run that stopped to ask still says what it asked", () => {
  // Twelve runs in one day, every one ending `stopped`, and every one drew
  // this row as a bare pause glyph with no question on it -- the sentence was
  // in the record and rendered only inside the branch that also holds the
  // Approve, which a stopped run is not live enough to get.
  const run = {
    id: "run_1",
    source: "rig",
    status: "stopped",
    steps: [
      {
        index: 0,
        outcome: "awaiting",
        says: "Click Save.",
        reason: "the first of 3 is done — 8SITDWN2. Approve to do the other 2",
      },
    ],
  };

  const card = runCard({ run });

  assert.match(words(card), /the first of 3 is done/, "the question was not drawn");
  // The buttons stay with the live run: an awaiting row on a run that has
  // ended is a record, and pressing Approve on it would approve nothing.
  assert.deepEqual(of(card, "button").map((one) => one.textContent), []);
});

test("a live run still gets the two answers beside the question", () => {
  const run = {
    id: "run_2",
    source: "rig",
    status: "running",
    steps: [
      { index: 0, outcome: "awaiting", says: "save", sent: { kind: "ui.perform", payload: { action: "click" } } },
    ],
  };

  // `stop: false`, so the card-level "Stop this run" is not also drawn: what
  // is under test is the two answers on the ROW.
  const card = runCard({ run }, { onPress: () => {}, stop: false });

  assert.deepEqual(of(card, "button").map((one) => one.textContent), ["Approve", "Stop"]);
});

test("what the dictionary knows is drawn beside the write, before the buttons", () => {
  // The thing the person tapping Approve most needs and would otherwise never
  // learn. A column that keeps four characters of six answers 201 either way,
  // so no rung of the ladder can say it and no later screen shows it.
  const parked = {
    ...RIG,
    live: true,
    steps: [
      {
        index: 0,
        outcome: "awaiting",
        says: "save the customer type",
        reason: "",
        notes: ["Customer Type holds 4 characters and this run supplies 6"],
      },
    ],
  };

  const card = runCard({ run: parked }, { onPress: () => {} });
  const said = words(card);

  assert.ok(said.includes("holds 4 characters"), `the note was not drawn: ${said}`);
  assert.ok(
    said.indexOf("holds 4 characters") < said.indexOf("Approve"),
    "the note was drawn after the button that acts on it",
  );
});

test("a step the dictionary had nothing to say about draws no note", () => {
  const card = runCard({ run: RIG }, {});

  assert.ok(!words(card).includes("holds"), "an empty notes list still drew something");
});

test("not_needed is a dash: a tick would say it happened", () => {
  // Measured on a real card, 2026-09-16: five ticks and one cross, above a
  // line reading "the page never moved". The operator read five things done
  // and one failed; nothing at all had been done on the page. A tick is this
  // panel's mark for "that happened", and the whole meaning of `not_needed` is
  // that it did not happen and did not need to.
  //
  // It fell through to `✓!` before that, which means a third thing again: "it
  // went out and nothing could say whether it landed".
  assert.equal(glyphFor("not_needed"), "–");
  assert.notEqual(glyphFor("not_needed"), glyphFor("held"));
  assert.notEqual(glyphFor("not_needed"), glyphFor("skipped"));
  assert.equal(glyphFor("held"), "✓");
  assert.equal(glyphFor("awaiting"), "⏸");
});


test("a record is drawn in whatever fields the system sent back", () => {
  // Nothing here knows which fields a system will answer with: a customer type
  // comes back named `customerType`, an order with an id and a status. The
  // backend picks the fields that name the row out of the create's own answer;
  // this draws what arrived rather than a shape it was taught.
  const card = runCard({
    run: {
      id: "run_2",
      source: "rig",
      status: "held",
      items: [],
      steps: [
        {
          index: 0,
          outcome: "held",
          says: "Click Save.",
          made: { customerType: "GQV", longDescription: "leaning new SRO type 006" },
        },
      ],
    },
  });

  const said = words(card);
  assert.match(said, /customerType: GQV/);
  assert.match(said, /longDescription: leaning new SRO type 006/);
});

test("a run nobody watched says it replayed the call", () => {
  // The run finishes, the record is in the warehouse, and the page in front of
  // the person never moved. With nothing said, that is indistinguishable from
  // a run that did nothing at all.
  const replayed = runCard({
    run: { id: "run-3", status: "done", source: "rig", steps: [], items: [], watched: false },
    skill: null,
    message: { text: "Create a Customer Type" },
  });
  assert.match(words(replayed), /replayed the call/);

  // And the other way round it is noise: they watched it type into the form.
  const watched = runCard({
    run: { id: "run-4", status: "done", source: "rig", steps: [], items: [], watched: true },
    skill: null,
    message: { text: "Create a Customer Type" },
  });
  assert.doesNotMatch(words(watched), /replayed the call/);
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
