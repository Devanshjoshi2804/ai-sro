// Self-check for the transcript: a thread, drawn.
//
// What is under test is the shape of what an operator reads and what they can
// press, not the DOM -- so the document here is the same handful of properties
// `panel.test.mjs` fakes, and for the same reason. The difference is that
// `transcript.js` is a pure function of a thread to DOM, so it needs no vm and
// no sandbox: the fake is installed as `globalThis.document` and the real
// module is imported. Nothing in it touches a document until it is called.
//
// Run with `node src/panel/transcript.test.mjs`.

import assert from "node:assert";

/** Every `innerHTML =` any node here was ever given.
 *
 * A fake document parses nothing, so asking it "did an `<img>` appear?" gets
 * the same answer -- none -- whether the code under test wrote `textContent`
 * or `innerHTML`. What it can see is the assignment itself, so that is what
 * the security test below asserts on: this list staying empty is the property,
 * and it is one the fake cannot be wrong about.
 */
const asMarkup = [];

/** Just enough document to build a transcript in, and to read it back out of. */
function node(tag) {
  return {
    tag,
    className: "",
    dataset: {},
    type: "",
    value: "",
    placeholder: "",
    disabled: false,
    textContent: "",
    kids: [],
    listeners: {},
    set innerHTML(value) {
      asMarkup.push({ tag: this.tag, value });
    },
    get innerHTML() {
      return "";
    },
    append(...added) {
      this.kids.push(...added);
    },
    addEventListener(kind, fn) {
      (this.listeners[kind] ??= []).push(fn);
    },
    querySelectorAll(selector) {
      const all = [];
      const walk = (el) => {
        if (el.tag === selector) all.push(el);
        for (const kid of el.kids) walk(kid);
      };
      walk(this);
      return all;
    },
  };
}

globalThis.document = { createElement: node };

const { transcript } = await import("./transcript.js");

/** Every word the node and its children carry, the way a person reads it. */
function words(el) {
  return [el.textContent, ...el.kids.map(words)].join(" ").replace(/\s+/g, " ").trim();
}

function of(el, tag) {
  return el.querySelectorAll(tag);
}

/** The messages, one node each, in the order they were said. */
function messages(node_) {
  return node_.kids.find((kid) => kid.className === "said").kids;
}

const WHEN = "2026-09-02T09:00:00Z";

const tests = [];
const test = (name, fn) => tests.push([name, fn]);

test("each speaker renders as its own kind of thing", () => {
  const node_ = transcript(
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
    {},
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
  const node_ = transcript({ id: "thr-1", messages: [offer] }, {
    onPress: (...args) => pressed.push(args),
  });

  const [message] = messages(node_);
  const [yes, no] = of(message, "button");
  assert.equal(yes.textContent, "Do the next one");
  assert.equal(no.textContent, "No thanks");

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
  const node_ = transcript(
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
  const node_ = transcript(
    {
      id: "thr-1",
      messages: [
        { id: "m1", speaker: "operator", text: "<img src=x onerror=alert(1)>", said_at: WHEN },
      ],
    },
    {},
  );

  // The property, and the one thing a fake document can actually witness: no
  // node in this transcript was ever handed a string to parse.
  assert.deepEqual(asMarkup, [], "message text was assigned as markup, not as text");
  // The other half of the same mutation, from the reading side: the words
  // reached the text of the paragraph a person reads, so a transcript that
  // quietly stopped setting `textContent` cannot pass this by being blank.
  const [what] = messages(node_)[0].kids;
  assert.equal(what.textContent, "<img src=x onerror=alert(1)>");
  // And it is still readable: shown as the string it is, not swallowed.
  assert.match(words(node_), /<img src=x onerror=alert\(1\)>/);
});

test("the composer hands over what was typed, once, and empties itself", () => {
  const heard = [];
  const node_ = transcript({ id: "thr-1", messages: [] }, { onSay: (text) => heard.push(text) });

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

test("a thread with nothing in it is still a place to say something", () => {
  // The first panel an operator opens. A composer and no transcript is the
  // whole surface, and it must not depend on `messages` being there at all --
  // the endpoint starts a thread when there is none, and a started thread is
  // empty.
  for (const empty of [{ id: "thr-1", messages: [] }, { id: "thr-1" }, null]) {
    const node_ = transcript(empty, {});
    assert.equal(messages(node_).length, 0);
    assert.equal(of(node_, "input").length, 1);
  }
});

let failed = 0;

test("an offer the operator already answered stops asking again", () => {
  // The offer stays -- it is a record of what was said -- but its buttons go.
  // Pressing one is refused by the backend ("this candidate is already
  // taught"), which is safe and useless: the operator answered, and the thread
  // should look like it. Seen live: two answered offers still carrying live
  // buttons above their own answers.
  const node = transcript(
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
    {},
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

for (const [name, fn] of tests) {
  try {
    await fn();
  } catch (error) {
    failed += 1;
    console.error(`  ✗ ${name}\n    ${error.message}`);
  }
}
if (failed) {
  console.error(`transcript.test.mjs: ${failed} failed`);
  process.exit(1);
}
console.log(`transcript.test.mjs: ok (${tests.length})`);
