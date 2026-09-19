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
  const node_ = ledger(
    {
      id: "thr-1",
      messages: [
        { id: "m1", speaker: "operator", text: "create a supplier", said_at: WHEN },
        { id: "m2", speaker: "assistant", text: "which client?", said_at: WHEN },
        {
          id: "m3",
          speaker: "system",
          text: "A run stopped to ask.",
          said_at: WHEN,
          decision: { kind: "failure", run_id: "run_1", next: "open" },
        },
      ],
    },
  );

  const said = messages(node_);
  assert.equal(said.length, 3);
  assert.deepEqual(
    said.map((message) => message.dataset.speaker),
    ["operator", "assistant", "system"],
  );
  // Everything anybody said is still on the page, in the order it was said.
  assert.match(words(node_), /create a supplier.*which client\?.*A run stopped to ask/s);
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
    ledger({
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
            titles: ["Create a Warehouse Equipment Type", "Create a Customer Type"],
          },
        },
      ],
    }, {}, { onPress: (answer, _message, _where, _button, values) => pressed.push([answer, values]) }),
  )[0];

  const buttons = of(item, "button").map((one) => one.textContent);
  assert.deepEqual(buttons, ["Create a Warehouse Equipment Type", "Create a Customer Type"]);

  of(item, "button")[1].listeners.click[0]();
  assert.deepEqual(pressed, [["which-job", { title: "Create a Customer Type" }]]);
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
  assert.match(words(message), /A run of “Resolve a short ship” finished in 48s\./);
  assert.equal(of(message, "button").length, 0);
});

test("message text is never parsed as markup", () => {
  // Message text is operator- and model-supplied, and this panel is an
  // extension origin with `chrome.*` in reach. `innerHTML` here is not a style
  // question.
  const node_ = ledger(
    {
      id: "thr-1",
      messages: [
        { id: "m1", speaker: "operator", text: "<img src=x onerror=alert(1)>", said_at: WHEN },
      ],
    },
  );

  // The property, and the one thing a fake document can actually witness: no
  // node in this ledger was ever handed a string to parse.
  assert.deepEqual(asMarkup, [], "message text was assigned as markup, not as text");
  // The other half of the same mutation, from the reading side: the words
  // reached the text of the paragraph a person reads, so a ledger that
  // quietly stopped setting `textContent` cannot pass this by being blank.
  // Found by class rather than position: the time rail is prepended, so the
  // paragraph a person reads is no longer the first child.
  const [what] = messages(node_)[0].kids.filter((kid) => kid.className === "what");
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
  assert.match(box.placeholder, /ask for a task/i, "the box suggests nothing to ask");

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
  assert.deepEqual(heard, ["make a work area for receiving", "and one for shipping"]);
  box.listeners.keydown[0]({ key: "a" });
  assert.equal(heard.length, 2, "a keystroke that was not Enter sent the message anyway");
});

test("a thread with nothing in it draws nothing, and does not throw", () => {
  // The first panel an operator opens. A composer and no ledger is the
  // whole surface, and it must not depend on `messages` being there at all --
  // the endpoint starts a thread when there is none, and a started thread is
  // empty.
  for (const empty of [{ id: "thr-1", messages: [] }, { id: "thr-1" }, null]) {
    const node_ = ledger(empty);
    assert.equal(messages(node_).length, 0);
    assert.equal(of(node_, "input").length, 0, "the composer is the panel's to place");
  }
});

test("the time rail says the minute once, not once per message", () => {
  // A day of work is read down the left edge. Repeating 12:04 against three
  // things said in the same minute is noise where the eye is looking for
  // structure.
  const node_ = ledger({
    id: "thr-1",
    messages: [
      { id: "1", speaker: "system", text: "a", said_at: "2026-09-03T12:04:10Z", decision: {} },
      { id: "2", speaker: "operator", text: "b", said_at: "2026-09-03T12:04:40Z", decision: {} },
      { id: "3", speaker: "system", text: "c", said_at: "2026-09-03T12:06:00Z", decision: {} },
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

  const labels = (i) => of(messages(node_)[i], "button").map((b) => b.textContent);
  assert.deepEqual(labels(0), ["Undo that", "It\u2019s wrong \u2014 I\u2019ll fix it"]);
  assert.deepEqual(labels(1), ["Open the page"], "a failure offers the one thing that helps");
  assert.deepEqual(labels(2), ["A000144886", "A000221"]);
  assert.equal(of(messages(node_)[2], "input").length, 1, "a question also takes a typed answer");
  assert.deepEqual(labels(3), [], "an unknown kind grew buttons nobody wired up");
  assert.ok(/somethingnew/.test(words(messages(node_)[3])), "an unknown kind lost its words");
});

test("a nudge the browser is holding is merged into the day by time", () => {
  // A nudge is never written to the server -- it lives about ninety seconds and
  // a conversation full of them is noise. It still belongs in the one place the
  // operator reads, in the order things happened.
  const node_ = ledger(
    {
      id: "thr-1",
      messages: [
        { id: "1", speaker: "system", text: "earlier", said_at: "2026-09-03T12:04:10Z" },
        { id: "2", speaker: "system", text: "later", said_at: "2026-09-03T12:09:00Z" },
      ],
    },
    {
      nudges: [
        {
          id: "n1",
          at: "2026-09-03T12:05:00Z",
          candidateId: "c1",
          title: "Create a supplier",
          state: "open",
        },
      ],
    },
  );

  const said = messages(node_);
  assert.equal(said.length, 3);
  assert.equal(said[1].dataset.kind, "nudge", "the nudge landed out of order");
  assert.deepEqual(
    of(said[1], "button").map((b) => b.textContent),
    ["Do it", "Not for this page"],
  );
});

test("a nudge that ended keeps one line and stops asking", () => {
  // Three ways a nudge ends and only one is an answer: they did it themselves,
  // or they did something else. Neither is a decision to record, and a prompt
  // still offering to act on a task already done is the failure this whole
  // ninety-second life exists to avoid.
  for (const [state, saying] of [
    ["by-hand", /did it yourself/],
    ["expired", /Create a supplier/],
  ]) {
    const node_ = ledger({ id: "t" }, { nudges: [{ id: "n1", at: WHEN, title: "Create a supplier", state }] });
    const [only] = messages(node_);
    assert.equal(of(only, "button").length, 0, `a ${state} nudge still had buttons`);
    assert.ok(saying.test(words(only)), `a ${state} nudge said: ${words(only)}`);
  }
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
  const node_ = ledger({ id: "t", messages: [message] }, { offers: [offer] }, {
    onPress: (...args) => pressed.push(args),
  });
  const item = messages(node_)[0];
  assert.ok(/mail.example/.test(words(item)), "the card must say where this matched");
  assert.ok(/subject contains/.test(words(item)), "and what the operator pointed it at");
  assert.equal(/procurement@|New supplier: Acme <|@kenco/.test(words(item)), false);
  const fields = of(item, "input");
  assert.deepEqual(
    fields.map((f) => [f.placeholder, f.value]),
    [["name", "Acme"], ["address", ""]],
  );

  fields[1].value = "A000221";
  of(item, "button")
    .find((b) => b.textContent === "Run it")
    .listeners.click[0]();
  assert.equal(pressed[0][0], "run");
  assert.deepEqual(pressed[0][4], { name: "Acme", address: "A000221" });

  const gone = ledger({ id: "t", messages: [message] }, { offers: [] });
  assert.equal(of(messages(gone)[0], "button").length, 0, "a press with no values behind it");
  assert.ok(/no longer held/.test(words(messages(gone)[0])));
});

let failed = 0;

// -- the rig's own offer ------------------------------------------------------

/** One nudge, drawn through the whole ledger, handed back as its list item.
 *
 * The fake document matches on tags, so the assertions below read fields off
 * the nodes rather than through a selector engine that is not there. */
function renderNudge(nudge, onPress) {
  const local = { offers: [], nudges: [{ at: WHEN, ...nudge }] };
  return messages(ledger({ id: "thr-1", messages: [] }, local, { onPress }))[0];
}
const what = (item) => of(item, "p").find((p) => p.className === "what").textContent;
const named = (item, placeholder) => of(item, "input").find((f) => f.placeholder === placeholder);
const labelled = (item, label) => of(item, "button").find((b) => label.test(b.textContent));
/** What a browser does on a click, the way this fake supports -- and what a
 * real one does not do to a disabled button. */
const press = (button) => {
  if (button.disabled) return;
  for (const fn of button.listeners.click || []) fn();
};
/** What a browser does on a keystroke, the way this fake supports. */
const typing = (field, value) => {
  field.value = value;
  for (const fn of field.listeners.input || []) fn();
};

test("an offer for several things says how many, and which", () => {
  // One press, three records, and a warehouse record cannot be un-created. The
  // count is in the sentence rather than under the button, because a count
  // below the button is a count somebody reads after deciding.
  const item = messages(
    ledger({ id: "thr-1", messages: [] }, {
      nudges: [
        {
          id: "n-1",
          source: "rig",
          state: "open",
          tabId: 7,
          k: 0,
          title: "Create a Warehouse Equipment Type",
          values: {},
          items: [
            { code: "8SITDWN2", name: "8-Sitdown Fork" },
            { code: "8STANDUP2", name: "8-Stand Up Fork" },
            { code: "8REACHT2", name: "8-Reach Truck" },
          ],
          missing: [],
        },
      ],
    }, { onPress: () => {} }),
  )[0];

  assert.match(words(item), /for 3 things/);
  assert.match(words(item), /8SITDWN2 8-Sitdown Fork/, "the things themselves were not said");
  assert.match(words(item), /8REACHT2/);
});

test("an offer for one thing reads exactly as it always did", () => {
  const item = messages(
    ledger({ id: "thr-1", messages: [] }, {
      nudges: [
        {
          id: "n-1",
          source: "rig",
          state: "open",
          tabId: 7,
          k: 0,
          title: "Create a work area",
          values: {},
          items: [{ areaName: "NEWTEST9" }],
          missing: [],
        },
      ],
    }, { onPress: () => {} }),
  )[0];

  assert.match(words(item), /Create a work area — want me to do it\?/);
  assert.ok(!words(item).includes("things"));
});

test("a rig offer short of a value asks in the conversation, not in a box", () => {
  // The card used to grow a text input per name and disable the press until
  // they were full. A panel that is already a conversation does not need a
  // form in it, and the form was wrong as well as redundant: on `Create a
  // Customer Type` it drew four boxes for two values, because that job
  // declares each field under a label and a body key.
  const pressed = [];
  const nudge = { id: "n_1", source: "rig", state: "open", title: "Create Work Area", k: 2,
    values: { workArea: "NEWTESTS" }, missing: ["description"], parameters: ["workArea", "description"], tabId: 1 };
  const item = renderNudge(nudge, (...args) => pressed.push(args));

  assert.match(what(item), /NEWTESTS, so far\. Want me to finish it\?/);
  assert.equal(of(item, "input").length, 0, "the card still draws a box");

  // Pressable, always. A disabled button on a card with nothing in it to fill
  // is a dead end somebody has to guess their way out of.
  const yes = labelled(item, /Yes, finish it/);
  assert.equal(yes.disabled, false);
  press(yes);
  assert.deepEqual(pressed.map((each) => each[0]), ["ask-about-offer"]);
});

test("a card the run can gather for draws no boxes and simply starts", () => {
  // Seen on the deployment 2026-09-16: `Create a Customer Type` was offered
  // with four required boxes -- two of them `customertype-customerType` and
  // `customertype-longDescription`, the body keys a form posts, which nobody
  // has ever typed -- for values sitting in the mail that asked for the job.
  const pressed = [];
  const nudge = { id: "n_7", source: "rig", state: "open", title: "Create a Customer Type", k: 0,
    values: { "Customer Type": "GPP" }, canFind: true, missing: [],
    parameters: ["Customer Type", "customertype-customerType"], tabId: 1 };
  const item = renderNudge(nudge, (...args) => pressed.push(args));

  const yes = labelled(item, /Yes, do it/);
  assert.equal(yes.disabled, false);
  assert.equal(of(item, "input").length, 0, "the card still draws a box");
  assert.equal(labelled(item, /I'll type them/), undefined, "the typing button is still there");

  // Nothing outstanding, so the press is the run itself and carries no values
  // of its own -- what it would have carried is already on the offer.
  press(yes);
  assert.deepEqual(pressed.map((each) => each[0]), ["start-rig-run"]);
  assert.deepEqual(pressed[0][4], { values: {} });
});

test("a rig arrival nudge offers to do it from the start", () => {
  const nudge = { id: "n_2", source: "rig", state: "open", title: "Create Work Area", k: 0,
    values: {}, missing: ["workArea"], parameters: ["workArea"], tabId: 1 };
  const item = renderNudge(nudge);
  assert.match(what(item), /want me to do it\?/);
  assert.ok(labelled(item, /Yes, do it/));
});

test("one press ends the card, so a refused offer cannot then be started", () => {
  // The ledger does not redraw when an offer is answered. Without this, "No
  // thanks" leaves Yes live under the cursor, and pressing it starts a live run
  // on an offer the worker has already reported dismissed -- two fates for one
  // offer. The worker refuses that as well; this is the half that keeps the
  // panel from ever asking.
  const pressed = [];
  const item = renderNudge(
    { id: "n_5", source: "rig", state: "open", title: "Create Work Area", k: 2,
      values: { workArea: "NEWTESTS" }, missing: ["description"], parameters: ["workArea", "description"], tabId: 1 },
    (...args) => pressed.push(args),
  );
  const yes = labelled(item, /Yes, finish it/);
  assert.equal(yes.disabled, false);

  press(labelled(item, /No thanks/));
  assert.equal(yes.disabled, true, "No thanks left Yes live");
  assert.equal(labelled(item, /No thanks/).disabled, true, "No thanks could be pressed twice");
  press(yes);
  assert.deepEqual(pressed.map((each) => each[0]), ["drop-nudge"], "a spent card pressed twice");
});

test("a title or a value that looks like markup is shown as the string it is", () => {
  const before = asMarkup.length;
  const item = renderNudge({
    id: "n_6", source: "rig", state: "open", k: 2, tabId: 1,
    title: "<img src=x onerror=alert(1)>",
    values: { workArea: "<script>alert(2)</script>" },
    missing: ["description"], parameters: ["workArea", "description"],
  });
  assert.equal(asMarkup.length, before, "the rig card put a string through innerHTML");
  assert.match(what(item), /<img src=x onerror=alert\(1\)>/);
  assert.match(what(item), /<script>alert\(2\)<\/script>/);
});

test("a backend nudge is drawn exactly as before", () => {
  const item = renderNudge({ id: "n_3", state: "open", title: "Create workOperations", tabId: 1 });
  assert.match(what(item), /you have done this here before/);
  assert.equal(of(item, "input").length, 0);
  assert.deepEqual(
    of(item, "button").map((b) => b.textContent),
    ["Do it", "Not for this page"],
  );
});

// -- what the systems answered -----------------------------------------------

/** One answer, drawn through the whole ledger, handed back as its list item. */
function renderAnswer(answer) {
  const local = { offers: [], nudges: [], answer: { askedAt: Date.parse(WHEN), ...answer } };
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
  assert.match(words(item), /\{"rows": 5\}/, "the body was not folded onto one line");
  // A read has already happened by the time this is drawn: a card saying
  // "shall I go and look?" would be a question about a question.
  assert.equal(of(item, "button").length, 0);
});

test("a system that would not answer says which, rather than being left out", () => {
  const item = renderAnswer({
    question: "any open orders",
    answers: [
      { system: "mail", target: "/gmail/v1/threads", ok: false, detail: "nothing here has been to /gmail/v1/threads" },
    ],
  });

  assert.match(words(item), /nothing here has been to/);
});

test("a word this deployment calls ambiguous is drawn as the question it is", () => {
  const item = renderAnswer({
    question: "which suppliers are set up at SG",
    asks: { question: "which collection is a supplier in?", options: ["WMSupplier", "A000144886"] },
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
  assert.equal(asMarkup.length, before, "a system's answer was assigned as markup");
});

test("an offer about a page carries a third answer: a standing rule", () => {
  // A rule rather than a run. Nothing starts on this press, so it does not end
  // the card -- somebody can make the rule and still say yes to the doing in
  // front of them.
  const pressed = [];
  const item = renderNudge(
    { id: "n_9", state: "open", source: "rig", title: "Create an equipment type",
      startsOn: "wms.test/portal/page", workflowId: "wfl_1", k: 0, values: {}, missing: [] },
    (answer) => pressed.push(answer),
  );

  const always = labelled(item, /Always on this page/);
  assert.ok(always, "the offer had no way to become a rule");
  press(always);
  assert.deepEqual(pressed, ["do-this-here"]);
  assert.equal(labelled(item, /Yes, do it/).disabled, false, "making a rule ended the offer");
});

test("a request naming a field this job cannot write says so before the press", () => {
  // A job's parameters are what two demonstrations proved VARY, and the form
  // has far more fields than that -- so "code GV3, description X, Department
  // Inbound" is a perfectly reasonable request, and this made a record with no
  // Department in it and said nothing. The run says so AFTER the press, and
  // after the press is after the record.
  const item = renderNudge({
    id: "n_12", state: "open", source: "rig", title: "Create a Customer Type",
    startsOn: "wms.test/portal", workflowId: "wfl_1", k: 0,
    values: { "Customer Type": "GV3" }, missing: [],
    unasked: ["Department", "Region"],
  });

  assert.match(words(item), /cannot set Department, Region/);
  // Said and not enforced: the job is still worth doing for the fields it does
  // hold, and what somebody needs is to know before they press.
  assert.ok(labelled(item, /Yes, do it/));
  assert.equal(labelled(item, /Yes, do it/).disabled, false);
});

test("a request this job can write whole says nothing about fields", () => {
  const item = renderNudge({
    id: "n_13", state: "open", source: "rig", title: "Create a Customer Type",
    startsOn: "wms.test/portal", workflowId: "wfl_1", k: 0,
    values: { "Customer Type": "GV3" }, missing: [], unasked: [],
  });

  assert.doesNotMatch(words(item), /cannot set/);
});

test("the card says what the press would write, before it is pressed", () => {
  // The card named the values and never the act. A person pressing yes is
  // agreeing to a record being made in a warehouse, and until this the only
  // place that was said was the run, afterwards.
  const item = renderNudge({
    id: "n_14", state: "open", source: "rig", title: "Create a Customer Type",
    startsOn: "wms.test/portal", workflowId: "wfl_1", k: 0,
    values: { "Customer Type": "GV3" }, missing: [],
    writes: [{ does: "create", record: "customerTypes", on: "https://wms.test" }],
  });

  assert.match(words(item), /It will create a customerTypes record on wms\.test\./);
});

test("a job with two writes in it says both", () => {
  // One line per writing step. A job that posts twice makes two records, and
  // saying it once describes half of what the press does.
  const item = renderNudge({
    id: "n_15", state: "open", source: "rig", title: "Create and file it",
    startsOn: "wms.test/portal", workflowId: "wfl_1", k: 0, values: {}, missing: [],
    writes: [
      { does: "create", record: "customerTypes", on: "https://wms.test" },
      { does: "change", record: "clients", on: "https://wms.test" },
    ],
  });

  assert.match(words(item), /create a customerTypes record/);
  assert.match(words(item), /change a clients record/);
});

test("a job whose evidence says nothing about a write says nothing", () => {
  // Empty is empty. A job whose gestures have aged out and one that only reads
  // look the same from here, and inventing a sentence for either is the card
  // telling somebody something nobody measured.
  const item = renderNudge({
    id: "n_16", state: "open", source: "rig", title: "Look something up",
    startsOn: "wms.test/portal", workflowId: "wfl_1", k: 0, values: {}, missing: [],
    writes: [],
  });

  assert.doesNotMatch(words(item), /It will/);
});

test("an offer that names no page cannot become a rule about one", () => {
  const item = renderNudge({
    id: "n_10", state: "open", source: "rig", title: "Create an equipment type",
    startsOn: "", workflowId: "wfl_1", k: 0, values: {}, missing: [],
  });

  assert.equal(labelled(item, /Always on this page/), undefined);
});

test("a request that came by mail is not offered as a standing rule", () => {
  // The gate was "does this offer name a page", and every offer does: a mined
  // job carries the screen it was recorded starting on. So one customer type,
  // asked for once by mail, was offering to run itself every time anybody
  // opened the Customer Types screen. Asked about it on 2026-09-18 and the
  // honest answer was that the button should not have been there.
  const item = renderNudge({
    id: "n_11", state: "open", source: "rig", title: "Create a Customer Type",
    startsOn: "wms.test/portal/page", workflowId: "wfl_1", k: 0,
    values: { "Customer Type": "NGSL" }, missing: [],
    thread: "1a0b571a6f1bf6a8", subject: "Customer type for the SRO pilot",
  });

  assert.equal(labelled(item, /Always on this page/), undefined);
  // The two that ARE about this one request stay exactly as they were.
  assert.ok(labelled(item, /Yes, do it/));
  assert.ok(labelled(item, /No thanks/));
});

test("a rule that almost fired is drawn, and offers nothing to press", () => {
  // The quietest failure this panel had: a mail arrived, the rule was about
  // that conversation, and nothing happened. A button that ran it anyway would
  // be the panel deciding the operator's words meant something they did not
  // write, so what it gives them is the term they wrote.
  const local = {
    offers: [],
    nudges: [],
    nearMisses: [{ triggerId: "trg-1", terms: ["order status"], at: Date.parse(WHEN) }],
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
  const item = messages(ledger({ id: "thr-1", messages: [] }, local, {
    onPress: (answer) => pressed.push(answer),
  }))[0];

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
    ledger({ id: "thr-1", messages: [] }, {
      waiting: [{ id: "cnf-1", skill_name: "Log In", because: "a rule fired", asked_at: WHEN }],
    }, { onPress: (answer) => pressed.push(answer) }),
  )[0];

  press(labelled(item, /^No$/));
  press(labelled(item, /Yes, do it/));

  assert.deepEqual(pressed, ["waiting-decline"], "a declined card started a run");
});

test("a card about a page nobody is on any more keeps its words and loses its buttons", () => {
  // What this is: the operator signed in, the run took the tab off the login
  // page, and the card that fired on arriving there was still in the panel.
  // Pressing it started a run with nowhere to go -- "no tab is open on
  // keycloak-...", a red cross, and eighteen seconds of a model working out
  // there was nothing to work on.
  const pressed = [];
  const item = messages(
    ledger({ id: "thr-1", messages: [] }, {
      waiting: [
        {
          id: "cnf-1",
          skill_name: "Log In",
          because: "an arrival trigger fired",
          asked_at: WHEN,
          page: "keycloak.test/auth",
          still_there: false,
        },
      ],
    }, { onPress: (answer) => pressed.push(answer) }),
  )[0];

  assert.match(words(item), /Log In .* an arrival trigger fired\. Shall I\?/, "the card lost what it was about, not just its buttons");
  assert.match(words(item), /moved on from that page/);
  assert.equal(of(item, "button").length, 0, "a doomed run could still be started");
  assert.deepEqual(pressed, []);
});

test("a card about the page in front of them is still answerable", () => {
  const pressed = [];
  const item = messages(
    ledger({ id: "thr-1", messages: [] }, {
      waiting: [
        {
          id: "cnf-1",
          skill_name: "Log In",
          because: "an arrival trigger fired",
          asked_at: WHEN,
          page: "keycloak.test/auth",
          still_there: true,
        },
      ],
    }, { onPress: (answer) => pressed.push(answer) }),
  )[0];

  press(labelled(item, /Yes, do it/));
  assert.deepEqual(pressed, ["waiting-approve"]);
});

test("a job already started with nothing typed does not say ', so far'", () => {
  // "Forward an Email — , so far. Want me to finish it?" on the deployment,
  // 2026-09-18: a dangling comma where the values were. `k` counts the steps
  // the operator has done, and a run reaches its second step without a value
  // having been typed into either.
  const item = messages(
    ledger({ id: "thr-1", messages: [] }, {
      nudges: [
        {
          id: "n_started",
          source: "rig",
          state: "open",
          k: 2,
          title: "Forward an Email",
          values: {},
          items: [],
          missing: ["To recipients"],
        },
      ],
    }, { onPress: () => {} }),
  )[0];

  assert.doesNotMatch(words(item), /— ,/, words(item));
  assert.match(words(item), /already started\. Want me to finish it\?/);
});

test("an offer read out of a mail says what it would create", () => {
  // Four of these stacked up on the deployment, 2026-09-18, every one of them
  // "Create a Customer Type — want me to do it?", and there was nothing on any
  // of them to tell one request from another or to check a reading against.
  // Nobody can consent to a write they cannot see.
  const item = messages(
    ledger({ id: "thr-1", messages: [] }, {
      nudges: [
        {
          id: "n_mail",
          source: "rig",
          state: "open",
          k: 0,
          title: "Create a Customer Type",
          values: {
            "Customer Type": "GU3",
            "Customer Type Description": "leaning new SRO type 038",
          },
          items: [],
          missing: [],
          canFind: true,
        },
      ],
    }, { onPress: () => {} }),
  )[0];

  assert.match(words(item), /GU3/);
  assert.match(words(item), /leaning new SRO type 038/);
  assert.match(words(item), /Want me to do it\?/);
});

test("an offer with nothing read yet still asks plainly", () => {
  const item = messages(
    ledger({ id: "thr-1", messages: [] }, {
      nudges: [
        {
          id: "n_bare",
          source: "rig",
          state: "open",
          k: 0,
          title: "Create a Customer Type",
          values: {},
          items: [],
          missing: ["Customer Type"],
        },
      ],
    }, { onPress: () => {} }),
  )[0];

  assert.match(words(item), /Create a Customer Type — want me to do it\?/);
});

test("a value the box will not hold is said before the press, and asked in words", () => {
  // The run already refuses this -- it types, the browser silently keeps 28
  // characters, and the run stops rather than write a record that does not say
  // what was asked for. It can only refuse standing in front of the box, so
  // the operator pressed, watched half a form fill, and got a question back.
  // The limit is known before the press, so it is said before the press -- and
  // the shorter value is asked for in the conversation, one question, in
  // words, rather than in an input stapled to a card.
  const pressed = [];
  const nudge = {
    id: "n_long", source: "rig", state: "open", k: 0,
    title: "Create a Customer Type",
    values: {
      "Customer Type": "GU9",
      "Customer Type Description": "leaning new SRO type 044 for the north dock",
    },
    items: [], missing: [], canFind: true,
    tooLong: { "Customer Type Description": 28 },
  };
  const item = renderNudge(nudge, (...args) => pressed.push(args));

  // The limit and how far over, because "this will not fit" sends somebody
  // back with a second value that does not fit either.
  assert.match(words(item), /takes 28 characters and this is 43/);
  assert.match(words(item), /ask you for a shorter one/);
  assert.equal(of(item, "input").length, 0, "the card still draws a box");

  press(labelled(item, /Yes, do it/));
  assert.deepEqual(pressed.map((each) => each[0]), ["ask-about-offer"]);
});

test("a value inside a known limit is not asked about at all", () => {
  const nudge = {
    id: "n_fits", source: "rig", state: "open", k: 0,
    title: "Create a Customer Type",
    values: { "Customer Type Description": "north dock" },
    items: [], missing: [], canFind: true,
    tooLong: { "Customer Type Description": 28 },
  };
  const pressed = [];
  const item = renderNudge(nudge, (...args) => pressed.push(args));
  // Not merely pressable -- unmentioned. A card that says "this takes 28
  // characters and this is 10, that fits" about a value nobody asked about is
  // a job explaining its own internals to somebody deciding.
  assert.doesNotMatch(words(item), /28 characters/, words(item));
  assert.equal(labelled(item, /Yes, do it/).disabled, false);
  // And nothing to sort out, so the press is the run.
  press(labelled(item, /Yes, do it/));
  assert.deepEqual(pressed.map((each) => each[0]), ["start-rig-run"]);
});

test("a sentence that has been sent shows before the answer does", () => {
  // What a sentence costs varies from nothing to several seconds. For that
  // whole stretch the box emptied and the panel showed what it showed before,
  // so the one thing the operator knows for certain -- that they pressed send
  // -- was the one thing nothing on screen agreed with.
  const item = messages(
    ledger({ id: "thr-1", messages: [] }, {
      sending: { text: "NSRO", at: "2026-09-18T10:20:00Z" },
    }, { onPress: () => {} }),
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
    ledger({
      id: "thr-1",
      messages: [
        { id: "m1", speaker: "assistant", text: "What should Customer Type be?",
          said_at: "2099-01-01T00:00:00Z" },
      ],
    }, { sending: { text: "NSRO", at: "2026-09-18T10:20:00Z" } }, { onPress: () => {} }),
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
    ledger({
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
    }, {}, { onPress: (...args) => pressed.push(args) }),
  )[0];

  const said = words(item);
  assert.match(said, /To tanisha@example\.com/);
  assert.match(said, /Re: Customer type for the SRO pilot/);
  // The body, in full: this is what they are authorising.
  assert.match(said, /Customer Type needs to be 4 characters or fewer/);

  press(labelled(item, /Send it/));
  assert.deepEqual(pressed.map((each) => each[0]), ["send-draft"]);
  assert.ok(labelled(item, /ask them myself/), "no way to decline");
});

test("a mail sent with no run behind it is not offered again", () => {
  // The half `run_id` never covered. A card asks before any run exists, so the
  // sent row carries an empty run and the claim keyed on it claimed nothing --
  // `Send it` stayed live under a mail already in somebody's inbox. Seen on
  // the deployment 2026-09-18: two identical mails about one request.
  const item = messages(
    ledger({
      id: "thr-1",
      messages: [
        {
          id: "m-draft", speaker: "system", text: "This is what I would send.",
          said_at: "2026-09-18T13:00:00Z",
          decision: {
            kind: "mail_draft", run_id: "", to: "tanisha@example.com",
            subject: "Re: it", body: "the words",
          },
        },
        {
          id: "m-sent", speaker: "system", text: "Asked tanisha@example.com.",
          said_at: "2026-09-18T13:01:00Z",
          decision: { kind: "mail_sent", run_id: "", draft_id: "m-draft", sent: true },
        },
      ],
    }, {}, { onPress: () => {} }),
  )[0];

  assert.equal(labelled(item, /Send it/), undefined, "it still offers to send a mail that went");
  assert.equal(item.dataset.answered, "sent");
});

test("a mail that has gone is not offered again", () => {
  // The claim is taken before the mailbox is reached, so a second press could
  // send a second mail about one request -- or worse, one nobody can tell went.
  const item = messages(
    ledger({
      id: "thr-1",
      messages: [
        {
          id: "m-draft", speaker: "system", text: "This is what I would send.",
          said_at: "2026-09-18T13:00:00Z",
          decision: {
            kind: "mail_draft", run_id: "run_1", to: "tanisha@example.com",
            subject: "Re: it", body: "the words",
          },
        },
        {
          id: "m-sent", speaker: "system", text: "Asked tanisha@example.com.",
          said_at: "2026-09-18T13:01:00Z",
          decision: { kind: "mail_sent", run_id: "run_1", sent: true },
        },
      ],
    }, {}, { onPress: () => {} }),
  )[0];

  assert.equal(labelled(item, /Send it/), undefined, "it still offers to send a mail that went");
  assert.equal(item.dataset.answered, "sent");
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
  assert.equal(item.dataset.state, undefined, "it says it is reading when it is not");
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
    ledger({ id: "thr-1", messages: [] }, { mail: { looking: false } }, { onPress: () => {} }),
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
