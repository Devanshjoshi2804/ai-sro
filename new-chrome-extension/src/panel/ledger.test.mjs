// Self-check for the ledger: a thread, drawn.
//
// What is under test is the shape of what an operator reads and what they can
// press, not the DOM -- so the document here is the same handful of properties
// `panel.test.mjs` fakes, and for the same reason. The difference is that
// `ledger.js` is a pure function of a thread to DOM, so it needs no vm and
// no sandbox: the fake is installed as `globalThis.document` and the real
// module is imported. Nothing in it touches a document until it is called.
//
// Run with `node src/panel/ledger.test.mjs`.

import assert from "node:assert";

import { asMarkup, install, of, words } from "./test-support/fake-document.mjs";

install();

const { composer, ledger } = await import("./ledger.js");

/** The messages, one node each, in the order they were said. */
function messages(node_) {
  return node_.kids.find((kid) => kid.className === "said").kids;
}

const WHEN = "2026-09-02T09:00:00Z";

const tests = [];
const test = (name, fn) => tests.push([name, fn]);

test("each speaker renders as its own kind of thing", () => {
  const node_ = ledger({
    id: "thr-1",
    messages: [
      {
        id: "m1",
        speaker: "operator",
        text: "create a supplier",
        said_at: WHEN,
      },
      { id: "m2", speaker: "assistant", text: "which client?", said_at: WHEN },
      {
        id: "m3",
        speaker: "system",
        text: "A run stopped to ask.",
        said_at: WHEN,
        decision: { kind: "failure", run_id: "run_1", next: "open" },
      },
    ],
  });

  const said = messages(node_);
  assert.equal(said.length, 3);
  assert.deepEqual(
    said.map((message) => message.dataset.speaker),
    ["operator", "assistant", "system"],
  );
  // Everything anybody said is still on the page, in the order it was said.
  assert.match(
    words(node_),
    /create a supplier.*which client\?.*A run stopped to ask/s,
  );
  // Only the decision is answerable. The other two are things that were said,
  // and a button on them would be a button that does nothing.
  assert.deepEqual(
    said.map((message) => of(message, "button").length),
    [0, 0, 1],
  );
});

test("a mining candidate is not offered at all -- this deployment runs the rig", () => {
  // The older pipeline's "you've done this 4 times, want me to do the next
  // one?" offers to teach a SKILL from recordings, which is not the system
  // this browser drives. An operator pressed one and got "the doings differ
  // too much" for work the rig already holds as a seven-step job.
  //
  // Dropped where it is read, not where it is written: the backend goes on
  // mining candidates and the console goes on reviewing them.
  const node_ = ledger({
    id: "thr-1",
    messages: [
      {
        id: "m1",
        speaker: "system",
        text: "Create an equipment type — you've done this 4 times.",
        said_at: WHEN,
        decision: { kind: "offer", candidate_id: "cnd_1", times: 4 },
      },
      { id: "m2", speaker: "operator", text: "ok", said_at: WHEN },
    ],
  });

  const said = messages(node_);
  assert.equal(said.length, 1, "the candidate offer was drawn");
  assert.ok(!words(node_).includes("equipment type"));
});

test("two jobs it could have meant are drawn as a question, not started", () => {
  // A guess that creates one wrong record is a nuisance; the same guess
  // against a list of twenty is twenty wrong records. The press says the job's
  // own name back into the conversation -- nothing starts from here.
  const pressed = [];
  const item = messages(
    ledger(
      {
        id: "thr-1",
        messages: [
          {
            id: "m1",
            speaker: "assistant",
            said_at: WHEN,
            text: "Did you mean Create a Warehouse Equipment Type or Create a Customer Type?",
            decision: {
              kind: "which_job",
              choices: ["wfl_1", "wfl_2"],
              titles: [
                "Create a Warehouse Equipment Type",
                "Create a Customer Type",
              ],
            },
          },
        ],
      },
      {},
      {
        onPress: (answer, _message, _where, _button, values) =>
          pressed.push([answer, values]),
      },
    ),
  )[0];

  const buttons = of(item, "button").map((one) => one.textContent);
  assert.deepEqual(buttons, [
    "Create a Warehouse Equipment Type",
    "Create a Customer Type",
  ]);

  of(item, "button")[1].listeners.click[0]();
  assert.deepEqual(pressed, [
    ["which-job", { title: "Create a Customer Type" }],
  ]);
});

test("a mail the server will not run by itself asks do it or leave it", () => {
  // The press says the answer back into the conversation, the way a typed
  // "yes" would: the door turns it into the same start a press makes.
  const pressed = [];
  const item = messages(
    ledger(
      {
        id: "thr-1",
        messages: [
          {
            id: "m1",
            speaker: "assistant",
            said_at: WHEN,
            text: "Create a Customer Type. You sent this to colleague@example.com. Should our system do it?",
            decision: {
              kind: "job",
              confirm: true,
              workflow_id: "wfl_1",
              sent_to: ["colleague@example.com"],
            },
          },
        ],
      },
      {},
      {
        onPress: (answer, _message, _where, _button, values) =>
          pressed.push([answer, values]),
      },
    ),
  )[0];

  assert.deepEqual(
    of(item, "button").map((one) => one.textContent),
    ["Do it", "Leave it"],
  );
  of(item, "button")[0].listeners.click[0]();
  of(item, "button")[1].listeners.click[0]();
  assert.deepEqual(pressed, [
    ["say", { said: "yes", answering: "m1" }],
    ["say", { said: "no", answering: "m1" }],
  ]);
});

test("a decision this panel does not know renders its words and no buttons", () => {
  // Forward compatibility. The backend can reach a kind this copy of the
  // extension has never heard of, and every browser in the field is a copy
  // that has not been updated yet. Blanking, or throwing, would mean the
  // backend cannot add one without taking the panel down first.
  const node_ = ledger(
    {
      id: "thr-1",
      messages: [
        {
          id: "m1",
          speaker: "system",
          text: "A run of “Resolve a short ship” finished in 48s.",
          said_at: WHEN,
          decision: { kind: "run-finished", run_id: "run_9", outcome: "clean" },
        },
      ],
    },
    { onPress: () => assert.fail("an unknown decision was made pressable") },
  );

  const [message] = messages(node_);
  assert.match(
    words(message),
    /A run of “Resolve a short ship” finished in 48s\./,
  );
  assert.equal(of(message, "button").length, 0);
});

test("the run a yes started is drawn under the message that names it", () => {
  // The backend starts the run on a yes and says so on the `job` message it
  // answers with; there is no separate `run` announcement any more (S2).
  const drawn = document.createElement("div");
  drawn.className = "live-run";
  const node_ = ledger(
    {
      id: "thr-1",
      messages: [
        {
          id: "m1",
          speaker: "assistant",
          text: "Running Create a Customer Type now.",
          said_at: WHEN,
          decision: { kind: "job", resume: true, run_id: "run_9" },
        },
      ],
    },
    {},
    { runs: new Map([["run_9", drawn]]) },
  );

  const [message] = messages(node_);
  assert.ok(message.kids.includes(drawn), "the running job has no run card");
});

test("message text is never parsed as markup", () => {
  // Message text is operator- and model-supplied, and this panel is an
  // extension origin with `chrome.*` in reach. `innerHTML` here is not a style
  // question.
  const node_ = ledger({
    id: "thr-1",
    messages: [
      {
        id: "m1",
        speaker: "operator",
        text: "<img src=x onerror=alert(1)>",
        said_at: WHEN,
      },
    ],
  });

  // The property, and the one thing a fake document can actually witness: no
  // node in this ledger was ever handed a string to parse.
  assert.deepEqual(
    asMarkup,
    [],
    "message text was assigned as markup, not as text",
  );
  // The other half of the same mutation, from the reading side: the words
  // reached the text of the paragraph a person reads, so a ledger that
  // quietly stopped setting `textContent` cannot pass this by being blank.
  // Found by class rather than position: the time rail is prepended, so the
  // paragraph a person reads is no longer the first child.
  const [what] = messages(node_)[0].kids.filter(
    (kid) => kid.className === "what",
  );
  assert.equal(what.textContent, "<img src=x onerror=alert(1)>");
  // And it is still readable: shown as the string it is, not swallowed.
  assert.match(words(node_), /<img src=x onerror=alert\(1\)>/);
});

test("the composer hands over what was typed, once, and empties itself", () => {
  const heard = [];
  // Built on its own now: the panel pins it to the bottom of the frame rather
  // than putting it after the last message, so a long conversation cannot push
  // the box off the bottom.
  const node_ = composer((text) => heard.push(text));

  const [box] = of(node_, "input");
  const [send] = of(node_, "button");
  assert.match(
    box.placeholder,
    /ask for a task/i,
    "the box suggests nothing to ask",
  );

  // Nothing typed is nothing said: an empty post would be a message in the
  // operator's own thread that nobody wrote.
  send.listeners.click[0]();
  box.value = "   ";
  send.listeners.click[0]();
  assert.deepEqual(heard, []);

  box.value = "  make a work area for receiving  ";
  send.listeners.click[0]();
  assert.deepEqual(heard, ["make a work area for receiving"]);
  // Cleared, because the post answers with the whole thread and what was typed
  // comes back as a message in it. Left in the box it would read as unsent.
  assert.equal(box.value, "");

  // Enter is how anybody sends a chat message.
  box.value = "and one for shipping";
  box.listeners.keydown[0]({ key: "Enter" });
  assert.deepEqual(heard, [
    "make a work area for receiving",
    "and one for shipping",
  ]);
  box.listeners.keydown[0]({ key: "a" });
  assert.equal(
    heard.length,
    2,
    "a keystroke that was not Enter sent the message anyway",
  );
});

test("a thread with nothing in it draws nothing, and does not throw", () => {
  // The first panel an operator opens. A composer and no ledger is the
  // whole surface, and it must not depend on `messages` being there at all --
  // the endpoint starts a thread when there is none, and a started thread is
  // empty.
  for (const empty of [{ id: "thr-1", messages: [] }, { id: "thr-1" }, null]) {
    const node_ = ledger(empty);
    assert.equal(messages(node_).length, 0);
    assert.equal(
      of(node_, "input").length,
      0,
      "the composer is the panel's to place",
    );
  }
});

test("the time rail says the minute once, not once per message", () => {
  // A day of work is read down the left edge. Repeating 12:04 against three
  // things said in the same minute is noise where the eye is looking for
  // structure.
  const node_ = ledger({
    id: "thr-1",
    messages: [
      {
        id: "1",
        speaker: "system",
        text: "a",
        said_at: "2026-09-03T12:04:10Z",
        decision: {},
      },
      {
        id: "2",
        speaker: "operator",
        text: "b",
        said_at: "2026-09-03T12:04:40Z",
        decision: {},
      },
      {
        id: "3",
        speaker: "system",
        text: "c",
        said_at: "2026-09-03T12:06:00Z",
        decision: {},
      },
    ],
  });

  const shown = of(node_, "time").map((t) => t.textContent);
  assert.equal(shown.length, 3, "every entry gets a rail cell, filled or not");
  assert.equal(shown[0] !== "", true, "the first entry says its minute");
  assert.equal(shown[1], "", "the same minute again says nothing");
  assert.equal(shown[2] !== "", true, "a new minute says itself");
  assert.notEqual(shown[0], shown[2]);
});

test("every kind draws its own buttons, and one nobody knows draws none", () => {
  // The panel must not blank or throw on a kind a newer backend reached and
  // this copy of the extension has never heard of: a backend has to be able to
  // add one without every browser in the field going dark first.
  const one = (kind, extra = {}) => ({
    id: kind,
    speaker: "system",
    text: kind,
    said_at: WHEN,
    decision: { kind, ...extra },
  });
  const node_ = ledger({
    id: "thr-1",
    messages: [
      one("result", { run_id: "r1" }),
      one("failure", { run_id: "r2", next: "open" }),
      one("question", { run_id: "r3", choices: ["A000144886", "A000221"] }),
      one("somethingnew"),
    ],
  });

  const labels = (i) =>
    of(messages(node_)[i], "button").map((b) => b.textContent);
  assert.deepEqual(labels(0), [
    "Undo that",
    "It\u2019s wrong \u2014 I\u2019ll fix it",
  ]);
  assert.deepEqual(
    labels(1),
    ["Open the page"],
    "a failure offers the one thing that helps",
  );
  assert.deepEqual(labels(2), ["A000144886", "A000221"]);
  assert.equal(
    of(messages(node_)[2], "input").length,
    1,
    "a question also takes a typed answer",
  );
  assert.deepEqual(
    labels(3),
    [],
    "an unknown kind grew buttons nobody wired up",
  );
  assert.ok(
    /somethingnew/.test(words(messages(node_)[3])),
    "an unknown kind lost its words",
  );
});

test("a matched mail draws the values the browser is holding, not the thread", () => {
  // The message carries names; the values stay in the browser that read them
  // out of somebody's mail. So the fields come from the offer beside it, and
  // when that offer is gone the card says so rather than drawing empty boxes
  // and pretending a press would work.
  const message = {
    id: "m",
    speaker: "system",
    text: "A mail matched Create a supplier",
    said_at: WHEN,
    decision: {
      kind: "mail_match",
      offer_id: "off_1",
      skill_name: "Create a supplier",
      read: ["name"],
      missing: ["address"],
    },
  };
  // No sender and no subject, deliberately: `watch.js` is explicit that neither
  // ever leaves the frame that read the mail, and an offer is held in
  // `chrome.storage`. What recognised it is the operator's own terms, which are
  // already here and say more.
  const offer = {
    id: "off_1",
    host: "mail.example",
    terms: [{ field: "subject", contains: "New supplier" }],
    values: { name: "Acme" },
    missing: ["address"],
  };

  const pressed = [];
  const node_ = ledger(
    { id: "t", messages: [message] },
    { offers: [offer] },
    {
      onPress: (...args) => pressed.push(args),
    },
  );
  const item = messages(node_)[0];
  assert.ok(
    /mail.example/.test(words(item)),
    "the card must say where this matched",
  );
  assert.ok(
    /subject contains/.test(words(item)),
    "and what the operator pointed it at",
  );
  assert.equal(
    /procurement@|New supplier: Acme <|@kenco/.test(words(item)),
    false,
  );
  const fields = of(item, "input");
  assert.deepEqual(
    fields.map((f) => [f.placeholder, f.value]),
    [
      ["name", "Acme"],
      ["address", ""],
    ],
  );

  fields[1].value = "A000221";
  of(item, "button")
    .find((b) => b.textContent === "Run it")
    .listeners.click[0]();
  assert.equal(pressed[0][0], "run");
  assert.deepEqual(pressed[0][4], { name: "Acme", address: "A000221" });

  const gone = ledger({ id: "t", messages: [message] }, { offers: [] });
  assert.equal(
    of(messages(gone)[0], "button").length,
    0,
    "a press with no values behind it",
  );
  assert.ok(/no longer held/.test(words(messages(gone)[0])));
});

let failed = 0;

// -- reading a drawn item ------------------------------------------------------
//
// The fake document matches on tags, so the assertions below read fields off
// the nodes rather than through a selector engine that is not there.

const what = (item) =>
  of(item, "p").find((p) => p.className === "what").textContent;
const labelled = (item, label) =>
  of(item, "button").find((b) => label.test(b.textContent));
/** What a browser does on a click, the way this fake supports -- and what a
 * real one does not do to a disabled button. */
const press = (button) => {
  if (button.disabled) return;
  for (const fn of button.listeners.click || []) fn();
};
// -- what the systems answered -----------------------------------------------

/** One answer, drawn through the whole ledger, handed back as its list item. */
function renderAnswer(answer) {
  const local = {
    offers: [],
    answer: { askedAt: Date.parse(WHEN), ...answer },
  };
  return messages(ledger({ id: "thr-1", messages: [] }, local, {}))[0];
}

test("an answer names the system and the thing that was read, and offers no press", () => {
  const item = renderAnswer({
    question: "which suppliers are set up at SG",
    answers: [
      {
        system: "blue_yonder",
        target: "/data/WM/wm/suppliers",
        ok: true,
        status: 200,
        body: '{"rows":\n  5}',
      },
    ],
  });

  assert.match(what(item), /which suppliers are set up at SG/);
  // An answer whose source cannot be seen is one nobody can check.
  assert.match(words(item), /blue_yonder · \/data\/WM\/wm\/suppliers/);
  assert.match(
    words(item),
    /\{"rows": 5\}/,
    "the body was not folded onto one line",
  );
  // A read has already happened by the time this is drawn: a card saying
  // "shall I go and look?" would be a question about a question.
  assert.equal(of(item, "button").length, 0);
});

test("a system that would not answer says which, rather than being left out", () => {
  const item = renderAnswer({
    question: "any open orders",
    answers: [
      {
        system: "mail",
        target: "/gmail/v1/threads",
        ok: false,
        detail: "nothing here has been to /gmail/v1/threads",
      },
    ],
  });

  assert.match(words(item), /nothing here has been to/);
});

test("a word this deployment calls ambiguous is drawn as the question it is", () => {
  const item = renderAnswer({
    question: "which suppliers are set up at SG",
    asks: {
      question: "which collection is a supplier in?",
      options: ["WMSupplier", "A000144886"],
    },
    answers: [],
  });

  assert.match(words(item), /which collection is a supplier in\?/);
  assert.match(words(item), /WMSupplier or A000144886/);
});

test("no markup reaches the page, whatever a system answered", () => {
  const before = asMarkup.length;
  const item = renderAnswer({
    question: "which suppliers",
    answers: [
      {
        system: "blue_yonder",
        target: "/data/WM/wm/suppliers",
        ok: true,
        body: '<img src=x onerror="alert(1)">',
      },
    ],
  });

  assert.match(words(item), /<img src=x/, "the answer was not drawn at all");
  assert.equal(
    asMarkup.length,
    before,
    "a system's answer was assigned as markup",
  );
});

test("a rule that almost fired is drawn, and offers nothing to press", () => {
  // The quietest failure this panel had: a mail arrived, the rule was about
  // that conversation, and nothing happened. A button that ran it anyway would
  // be the panel deciding the operator's words meant something they did not
  // write, so what it gives them is the term they wrote.
  const local = {
    offers: [],
    nearMisses: [
      { triggerId: "trg-1", terms: ["order status"], at: Date.parse(WHEN) },
    ],
  };
  const item = messages(ledger({ id: "thr-1", messages: [] }, local, {}))[0];

  assert.match(words(item), /nearly matched "order status"/);
  assert.equal(of(item, "button").length, 0);
});

test("a rule that fired and stopped to ask is drawn where the operator is", () => {
  // The card an operator could not see: a page rule fired on the page in front
  // of them, the fire became a confirmation, and the confirmation was drawn in
  // the console -- another tab, which from where they were standing is
  // indistinguishable from nothing having happened.
  const pressed = [];
  const local = {
    waiting: [
      {
        id: "cnf-1",
        skill_name: "Log In",
        because: "a page rule fired",
        asked_at: WHEN,
        values: { site: "SG" },
      },
    ],
  };
  const item = messages(
    ledger({ id: "thr-1", messages: [] }, local, {
      onPress: (answer) => pressed.push(answer),
    }),
  )[0];

  assert.match(words(item), /Log In .* a page rule fired\. Shall I\?/);
  // What it would run with, before it runs: the one moment somebody can read a
  // write's values and still stop it.
  assert.match(words(item), /site: SG/);
  press(labelled(item, /Yes, do it/));
  assert.deepEqual(pressed, ["waiting-approve"]);
});

test("the card asking for a decision reads like one", () => {
  // The shape borrowed from the tool-call block a person already answers
  // elsewhere: what it wants, the request behind a disclosure, and a band of
  // two controls with their keys named on them.
  const pressed = [];
  const item = messages(
    ledger(
      { id: "thr-1", messages: [] },
      {
        waiting: [
          {
            id: "cnf-1",
            skill_name: "Log In",
            because: "a page rule fired",
            asked_at: WHEN,
            values: { site: "SG", user: "ops" },
          },
        ],
      },
      { onPress: (answer) => pressed.push(answer) },
    ),
  )[0];

  // Shut, and counted, so a write with twelve values cannot push the two
  // controls this card exists for below the fold.
  const request = of(item, "details")[0];
  assert.ok(request, "the values were not behind a disclosure");
  assert.match(words(request), /what it would use \(2\)/);
  assert.match(words(request), /site: SG/);

  // The keys, named where they are pressed.
  // The way out first and the primary press last, which is the order of every
  // dialog this panel sits beside. The modifier is whichever this machine
  // uses -- a Mac told to press Ctrl is a Mac told the wrong thing.
  const keys = of(item, "kbd").map((one) => one.textContent);
  assert.equal(keys[0], "Esc");
  assert.match(keys[1], /\u23ce$/, keys.join());

  // And they work, while this card has the focus. Not on the document: Esc
  // taken globally throws away what somebody is typing in the composer.
  const keydown = item.listeners.keydown[0];
  keydown({ key: "Escape" });
  assert.deepEqual(pressed, ["waiting-decline"]);
  // One answer however it arrives -- the key and the press are the same
  // decision, not two paths that can both be taken.
  keydown({ key: "Enter", metaKey: true });
  press(labelled(item, /Yes, do it/));
  assert.deepEqual(pressed, ["waiting-decline"]);
});

test("one press settles it: the buttons do not stay live under the cursor", () => {
  const pressed = [];
  const item = messages(
    ledger(
      { id: "thr-1", messages: [] },
      {
        waiting: [
          {
            id: "cnf-1",
            skill_name: "Log In",
            because: "a rule fired",
            asked_at: WHEN,
          },
        ],
      },
      { onPress: (answer) => pressed.push(answer) },
    ),
  )[0];

  press(labelled(item, /^No$/));
  press(labelled(item, /Yes, do it/));

  assert.deepEqual(
    pressed,
    ["waiting-decline"],
    "a declined card started a run",
  );
});

test("a card waiting on the operator can be answered from the thread", () => {
  const pressed = [];
  const item = messages(
    ledger(
      { id: "thr-1", messages: [] },
      {
        waiting: [
          {
            id: "cnf-1",
            skill_name: "Log In",
            because: "an arrival trigger fired",
            asked_at: WHEN,
          },
        ],
      },
      { onPress: (answer) => pressed.push(answer) },
    ),
  )[0];

  press(labelled(item, /Yes, do it/));
  assert.deepEqual(pressed, ["waiting-approve"]);
});

test("a sentence that has been sent shows before the answer does", () => {
  // What a sentence costs varies from nothing to several seconds. For that
  // whole stretch the box emptied and the panel showed what it showed before,
  // so the one thing the operator knows for certain -- that they pressed send
  // -- was the one thing nothing on screen agreed with.
  const item = messages(
    ledger(
      { id: "thr-1", messages: [] },
      {
        sending: { text: "NSRO", at: "2026-09-18T10:20:00Z" },
      },
      { onPress: () => {} },
    ),
  ).at(-1);

  assert.match(words(item), /NSRO/, "their own words are not on screen");
  assert.equal(item.dataset.speaker, "operator");
  // Marked as not yet answered, so a draw that never lands cannot be mistaken
  // for one that did.
  assert.equal(item.dataset.state, "sending");
  // And something says an answer is being worked out.
  assert.match(words(item), /thinking/i);
});

test("the sentence being sent is last, whatever the clock says", () => {
  // A locally-stamped time can lose a race with the server's own, and a
  // sentence that sorted above the reply to it reads as a panel out of order.
  const item = messages(
    ledger(
      {
        id: "thr-1",
        messages: [
          {
            id: "m1",
            speaker: "assistant",
            text: "What should Customer Type be?",
            said_at: "2099-01-01T00:00:00Z",
          },
        ],
      },
      { sending: { text: "NSRO", at: "2026-09-18T10:20:00Z" } },
      { onPress: () => {} },
    ),
  ).at(-1);

  assert.match(words(item), /NSRO/);
});

test("nothing in flight draws no sentence and no spinner", () => {
  const drawn = messages(
    ledger({ id: "thr-1", messages: [] }, {}, { onPress: () => {} }),
  );

  assert.equal(drawn.length, 0);
});

test("a drafted mail is shown whole, with the press under it", () => {
  // The one thing this system writes that leaves the company, over the
  // operator's name, to somebody outside every system here -- and it cannot be
  // unsent. An authorisation given without reading is not one, so the words
  // are on the card rather than behind a disclosure: nobody expands a details
  // element before pressing a button they have already decided about.
  const pressed = [];
  const item = messages(
    ledger(
      {
        id: "thr-1",
        messages: [
          {
            id: "m-draft",
            speaker: "system",
            text: "I can ask tanisha@example.com. This is what I would send — read it first.",
            said_at: "2026-09-18T13:00:00Z",
            decision: {
              kind: "mail_draft",
              run_id: "run_1",
              to: "tanisha@example.com",
              subject: "Re: Customer type for the SRO pilot",
              body: "I am working on Create a Customer Type from your request.\n\nCustomer Type needs to be 4 characters or fewer.",
            },
          },
        ],
      },
      {},
      { onPress: (...args) => pressed.push(args) },
    ),
  )[0];

  const said = words(item);
  assert.match(said, /To tanisha@example\.com/);
  assert.match(said, /Re: Customer type for the SRO pilot/);
  // The body, in full: this is what they are authorising.
  assert.match(said, /Customer Type needs to be 4 characters or fewer/);

  press(labelled(item, /Send it/));
  assert.deepEqual(
    pressed.map((each) => each[0]),
    ["send-draft"],
  );
  assert.ok(labelled(item, /ask them myself/), "no way to decline");
});

test("a mail sent with no run behind it is not offered again", () => {
  // The half `run_id` never covered. A card asks before any run exists, so the
  // sent row carries an empty run and the claim keyed on it claimed nothing --
  // `Send it` stayed live under a mail already in somebody's inbox. Seen on
  // the deployment 2026-09-18: two identical mails about one request.
  const item = messages(
    ledger(
      {
        id: "thr-1",
        messages: [
          {
            id: "m-draft",
            speaker: "system",
            text: "This is what I would send.",
            said_at: "2026-09-18T13:00:00Z",
            decision: {
              kind: "mail_draft",
              run_id: "",
              to: "tanisha@example.com",
              subject: "Re: it",
              body: "the words",
            },
          },
          {
            id: "m-sent",
            speaker: "system",
            text: "Asked tanisha@example.com.",
            said_at: "2026-09-18T13:01:00Z",
            decision: {
              kind: "mail_sent",
              run_id: "",
              draft_id: "m-draft",
              sent: true,
            },
          },
        ],
      },
      {},
      { onPress: () => {} },
    ),
  )[0];

  assert.equal(
    labelled(item, /Send it/),
    undefined,
    "it still offers to send a mail that went",
  );
  assert.equal(item.dataset.answered, "sent");
});

test("a mail that has gone is not offered again", () => {
  // The claim is taken before the mailbox is reached, so a second press could
  // send a second mail about one request -- or worse, one nobody can tell went.
  const item = messages(
    ledger(
      {
        id: "thr-1",
        messages: [
          {
            id: "m-draft",
            speaker: "system",
            text: "This is what I would send.",
            said_at: "2026-09-18T13:00:00Z",
            decision: {
              kind: "mail_draft",
              run_id: "run_1",
              to: "tanisha@example.com",
              subject: "Re: it",
              body: "the words",
            },
          },
          {
            id: "m-sent",
            speaker: "system",
            text: "Asked tanisha@example.com.",
            said_at: "2026-09-18T13:01:00Z",
            decision: { kind: "mail_sent", run_id: "run_1", sent: true },
          },
        ],
      },
      {},
      { onPress: () => {} },
    ),
  )[0];

  assert.equal(
    labelled(item, /Send it/),
    undefined,
    "it still offers to send a mail that went",
  );
  assert.equal(item.dataset.answered, "sent");
});

test("a lookup's answer is a count and a table, not a wall of JSON", () => {
  // Measured on the deployment 2026-09-21. Asked "is there a customer type
  // called KKYT", the conversation carried the SCREEN WALK -- "Nobody has
  // demonstrated reading that, so I will work it out on the screen" -- while
  // the answer arrived beside it as
  //
  //   {"@type":"ResponseBodyWrapper","data":[{"URNFormat":null,"absoluteGrou…
  //
  // which answers nothing and never reaches the row the question was about.
  // `result()` already knew how to draw this; the thread had no way to reach
  // it.
  const [item] = messages(
    ledger(
      {
        id: "thr-1",
        messages: [
          {
            id: "m1",
            speaker: "assistant",
            text: "Read from /data/WM/wm/customerTypes.",
            said_at: WHEN,
            decision: {
              kind: "looked",
              question: "is there a customer type called KKYT",
              answers: [
                {
                  system: "WM",
                  target: "/data/WM/wm/customerTypes",
                  ok: true,
                  status: 200,
                  detail: "",
                  truncated: false,
                  body: null,
                  read: {
                    rows: 2,
                    counted: 2,
                    partial: false,
                    subject: "customer type",
                    sentence:
                      "There are 2 customer type: KKYT (my sro is best), DDD (leaning SRO 2).",
                    columns: ["customerType", "longDescription"],
                    records: [
                      {
                        customerType: "KKYT",
                        longDescription: "my sro is best",
                      },
                      { customerType: "DDD", longDescription: "leaning SRO 2" },
                    ],
                  },
                },
              ],
            },
          },
        ],
      },
      {},
      { onPress: () => {} },
    ),
  );

  const said = words(item);
  assert.equal(item.dataset.kind, "looked");
  assert.match(said, /There are 2 customer type/, `no sentence: ${said}`);
  assert.match(
    said,
    /KKYT/,
    `the row the question was about is not there: ${said}`,
  );
  assert.match(said, /my sro is best/);
});

test("an unfamiliar decision still renders its words and nothing else", () => {
  // The rule the `looked` branch sits beside: a kind a newer backend reached
  // and this copy of the extension has never heard of renders the sentence. A
  // panel that blanked or threw would mean a backend could not add one
  // without every browser in the field going dark first.
  const [item] = messages(
    ledger(
      {
        id: "thr-1",
        messages: [
          {
            id: "m1",
            speaker: "assistant",
            text: "something a later backend says",
            said_at: WHEN,
            decision: { kind: "not-invented-yet" },
          },
        ],
      },
      {},
      { onPress: () => {} },
    ),
  );

  assert.match(words(item), /something a later backend says/);
});

test("a mail that has gone and not been answered is drawn as a state, not a sentence", () => {
  // A mail leaves over the operator's name and the reply arrives by a poll
  // nobody can see. What that looked like was one sentence -- "I will carry on
  // when they reply" -- and then a panel doing visibly nothing for as long as
  // it took.
  const [item] = messages(
    ledger(
      { id: "thr-1", messages: [] },
      {
        mail: {
          awaiting: { to: "asker@example.com", at: Date.now() - 240000 },
          looking: false,
          lookedAt: Date.now() - 40000,
        },
      },
      { onPress: () => {} },
    ),
  );

  const said = words(item);
  assert.match(said, /Waiting for asker@example\.com/);
  // Every number is something this browser did, and it says which.
  assert.match(said, /asked 4m ago/);
  assert.match(said, /last read 40s ago/);
  assert.equal(
    item.dataset.state,
    undefined,
    "it says it is reading when it is not",
  );
});

test("while the mailbox is actually being read, it says so", () => {
  const [item] = messages(
    ledger(
      { id: "thr-1", messages: [] },
      {
        mail: {
          awaiting: { to: "asker@example.com", at: Date.now() - 1000 },
          looking: true,
          lookedAt: Date.now(),
        },
      },
      { onPress: () => {} },
    ),
  );

  assert.equal(item.dataset.state, "looking");
  // The words carry it, not only the animation: a stylesheet may decline to
  // run one, and a line that reads the same either way is the line this
  // replaces.
  assert.match(words(item), /reading the mailbox/);
});

test("nothing is waited on when no mail has gone", () => {
  const drawn = messages(
    ledger(
      { id: "thr-1", messages: [] },
      { mail: { looking: false } },
      { onPress: () => {} },
    ),
  );

  assert.equal(drawn.length, 0, "it invented a wait");
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
  console.error(`ledger.test.mjs: ${failed} failed`);
  process.exit(1);
}
console.log(`ledger.test.mjs: ok (${tests.length})`);
