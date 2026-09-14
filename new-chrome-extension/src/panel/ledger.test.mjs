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
          text: "You've done this 3 times.",
          said_at: WHEN,
          decision: { kind: "offer", candidate_id: "cnd_1", times: 3 },
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
  assert.match(words(node_), /create a supplier.*which client\?.*You've done this 3 times/s);
  // Only the offer is answerable. The other two are things that were said, and
  // a button on them would be a button that does nothing.
  assert.deepEqual(
    said.map((message) => of(message, "button").length),
    [0, 0, 2],
  );
});

test("an offer renders the two answers, and pressing one starts nothing itself", () => {
  const pressed = [];
  const offer = {
    id: "m1",
    speaker: "system",
    text: "You've created a carrier cross-reference here 3 times. Want me to do the next one?",
    said_at: WHEN,
    decision: { kind: "offer", candidate_id: "cnd_1", times: 3, seconds_each: 51 },
  };
  const node_ = ledger({ id: "thr-1", messages: [offer] }, undefined, {
    onPress: (...args) => pressed.push(args),
  });

  const [message] = messages(node_);
  const [yes, no] = of(message, "button");
  assert.equal(yes.textContent, "Do the next one");
  assert.equal(no.textContent, "Not now");

  // Drawing the offer did nothing. This is the separation the design turns on:
  // a message is a thing said, the press is the authorisation, and an assisted
  // run records the press.
  assert.deepEqual(pressed, []);

  yes.listeners.click[0]();
  assert.equal(pressed.length, 1);
  const [answer, message_, where] = pressed[0];
  assert.equal(answer, "do");
  // The whole message, so the caller reads the candidate off the decision
  // rather than off anything this file invented, and the node it was drawn in,
  // so an answer can be reported on the offer itself.
  assert.equal(message_.decision.candidate_id, "cnd_1");
  assert.equal(where, message);

  no.listeners.click[0]();
  assert.equal(pressed[1][0], "no");
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
      one("offer", { candidate_id: "c1" }),
      one("result", { run_id: "r1" }),
      one("failure", { run_id: "r2", next: "open" }),
      one("question", { run_id: "r3", choices: ["A000144886", "A000221"] }),
      one("somethingnew"),
    ],
  });

  const labels = (i) => of(messages(node_)[i], "button").map((b) => b.textContent);
  assert.deepEqual(labels(0), ["Do the next one", "Not now"]);
  assert.deepEqual(labels(1), ["Undo that", "It\u2019s wrong \u2014 I\u2019ll fix it"]);
  assert.deepEqual(labels(2), ["Open the page"], "a failure offers the one thing that helps");
  assert.deepEqual(labels(3), ["A000144886", "A000221"]);
  assert.equal(of(messages(node_)[3], "input").length, 1, "a question also takes a typed answer");
  assert.deepEqual(labels(4), [], "an unknown kind grew buttons nobody wired up");
  assert.ok(/somethingnew/.test(words(messages(node_)[4])), "an unknown kind lost its words");
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

test("an offer the operator already answered stops asking again", () => {
  // The offer stays -- it is a record of what was said -- but its buttons go.
  // Pressing one is refused by the backend ("this candidate is already
  // taught"), which is safe and useless: the operator answered, and the thread
  // should look like it. Seen live: two answered offers still carrying live
  // buttons above their own answers.
  const node = ledger(
    {
      messages: [
        {
          id: "m1",
          speaker: "system",
          text: "Create a supplier — you've done this 5 times. Want me to do the next one?",
          said_at: WHEN,
          decision: { kind: "offer", candidate_id: "cnd-1", times: 5 },
        },
        {
          id: "m2",
          speaker: "system",
          text: "Create a supplier — you asked for this one, so I learned it.",
          said_at: WHEN,
          decision: { kind: "answered", candidate_id: "cnd-1", answer: "asked" },
        },
        {
          id: "m3",
          speaker: "system",
          text: "Create a work area — you've done this 4 times. Want me to do the next one?",
          said_at: WHEN,
          decision: { kind: "offer", candidate_id: "cnd-2", times: 4 },
        },
      ],
    },
  );

  const said = messages(node);
  const [answeredOffer, itsAnswer, openOffer] = said;
  assert.equal(
    of(answeredOffer, "button").length,
    0,
    "an offer that was already answered still invited an answer",
  );
  assert.equal(answeredOffer.dataset.answered, "asked");
  assert.ok(
    /Create a supplier/.test(words(answeredOffer)),
    "the offer's own words were dropped along with its buttons",
  );
  assert.equal(of(itsAnswer, "button").length, 0, "the answer itself grew buttons");
  assert.equal(of(openOffer, "button").length, 2, "an unanswered offer lost its buttons");
});

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

test("a rig offer asks for what is missing and cannot start until it has it", () => {
  const nudge = { id: "n_1", source: "rig", state: "open", title: "Create Work Area", k: 2,
    values: { workArea: "NEWTESTS" }, missing: ["description"], parameters: ["workArea", "description"], tabId: 1 };
  const item = renderNudge(nudge);
  assert.match(what(item), /NEWTESTS, so far\. Want me to finish it\?/);
  const field = named(item, "description");
  assert.ok(field);
  const yes = labelled(item, /Yes, finish it/);
  assert.equal(yes.disabled, true);
  typing(field, "north dock");
  assert.equal(yes.disabled, false);
  // Blank again is blank: a space is not an answer to a question the run needs.
  typing(field, "   ");
  assert.equal(yes.disabled, true, "a field of spaces started a run");
});

test("a rig arrival nudge offers to do it from the start", () => {
  const nudge = { id: "n_2", source: "rig", state: "open", title: "Create Work Area", k: 0,
    values: {}, missing: ["workArea"], parameters: ["workArea"], tabId: 1 };
  const item = renderNudge(nudge);
  assert.match(what(item), /want me to do it\?/);
  assert.ok(labelled(item, /Yes, do it/));
});

test("a rig offer hands the press the values that were typed into it", () => {
  const pressed = [];
  const nudge = { id: "n_4", source: "rig", state: "open", title: "Create Work Area", k: 1,
    values: { workArea: "NEWTESTS" }, missing: ["description"], parameters: ["workArea", "description"], tabId: 1 };
  const item = renderNudge(nudge, (...args) => pressed.push(args));
  typing(named(item, "description"), "  north dock  ");
  press(labelled(item, /Yes, finish it/));
  // `start-rig-run` and not `nudge-answer`: the worker reports one fate per
  // path, and an offer that took both would be counted twice.
  assert.deepEqual(pressed.map((each) => each[0]), ["start-rig-run"]);
  assert.deepEqual(pressed[0][4], { values: { description: "north dock" } });
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
  typing(named(item, "description"), "north dock");
  assert.equal(yes.disabled, false);

  press(labelled(item, /No thanks/));
  assert.equal(yes.disabled, true, "No thanks left Yes live");
  assert.equal(labelled(item, /No thanks/).disabled, true, "No thanks could be pressed twice");

  // Nor by typing into the box again: the input handler must not undo it.
  typing(named(item, "description"), "somewhere else");
  assert.equal(yes.disabled, true, "typing brought a spent offer back to life");
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

test("a rig offer carries a third answer: always, here", () => {
  // A rule rather than a run. Nothing starts on this press, so it does not end
  // the card -- somebody can make the rule and still say yes to the doing in
  // front of them.
  const pressed = [];
  const item = renderNudge(
    { id: "n_9", state: "open", source: "rig", title: "Create an equipment type",
      startsOn: "wms.test/portal/page", workflowId: "wfl_1", k: 0, values: {}, missing: [] },
    (answer) => pressed.push(answer),
  );

  const always = labelled(item, /Always, here/);
  assert.ok(always, "the offer had no way to become a rule");
  press(always);
  assert.deepEqual(pressed, ["do-this-here"]);
  assert.equal(labelled(item, /Yes, do it/).disabled, false, "making a rule ended the offer");
});

test("an offer that names no page cannot become a rule about one", () => {
  const item = renderNudge({
    id: "n_10", state: "open", source: "rig", title: "Create an equipment type",
    startsOn: "", workflowId: "wfl_1", k: 0, values: {}, missing: [],
  });

  assert.equal(labelled(item, /Always, here/), undefined);
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

test("an offer about another system keeps its words and loses its buttons", () => {
  // What an operator actually saw: standing on their login page, shown "create
  // an equipment type -- want me to do the next one?" with live buttons, for a
  // warehouse host they were not on. Pressing it would drive a tab they are
  // not looking at, off evidence from hours before.
  const thread = {
    id: "thr-1",
    messages: [
      {
        id: "m1",
        speaker: "system",
        said_at: WHEN,
        text: "Create an equipment type — you've done this 4 times.",
        decision: { kind: "offer", candidate_id: "cnd-1", host: "wms.test" },
      },
    ],
  };

  const away = messages(ledger(thread, { here: "login.test" }, {}))[0];
  assert.match(words(away), /Create an equipment type/, "the offer stopped being said at all");
  assert.match(words(away), /on wms.test/);
  assert.equal(of(away, "button").length, 0);

  const there = messages(ledger(thread, { here: "wms.test" }, {}))[0];
  assert.equal(of(there, "button").length, 2, "the offer lost its buttons where it applies");
});

test("an offer whose host nobody knows keeps its buttons", () => {
  // Hiding a control on a guess is worse than showing one that turns out to be
  // about the next tab: an older backend sends no host, and a panel that has
  // not learned which tab it is beside knows no `here`.
  const thread = {
    id: "thr-1",
    messages: [
      {
        id: "m1",
        speaker: "system",
        said_at: WHEN,
        text: "Create an equipment type.",
        decision: { kind: "offer", candidate_id: "cnd-1" },
      },
    ],
  };

  assert.equal(of(messages(ledger(thread, { here: "login.test" }, {}))[0], "button").length, 2);
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
