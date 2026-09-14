// Self-check for watch.js, against the cases the backend's own tests use.
//
// `Watch.matches` in `src/sro/domain/trigger/watch.py` is the definition of
// record and this file is the other implementation of it. Only one of the two
// ever sees a mail -- the browser -- so nothing compares them at runtime and a
// disagreement would be invisible for as long as it took somebody to notice a
// watch that never fires, or one that fires on the wrong mail.
//
// So the cases below are lifted from
// `backend/tests/unit/domain/test_what_a_watch_is_allowed_to_remember.py`,
// under the same names, in the same order. The two files are meant to be read
// side by side. Run with `node src/content/watch.test.mjs`.

import assert from "node:assert";
import vm from "node:vm";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

import { hostMatches } from "../background/scripts.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const SOURCE = readFileSync(path.join(here, "watch.js"), "utf-8");

const GMAIL = "mail.google.com";
const FROM_THE_CUSTOMER = { field: "sender", contains: "@northwind.example" };
const ASKING_FOR_STATUS = { field: "subject", contains: "order status" };
const SENDER_IS_HERE = { strategy: "css_path", query: "span.from" };
const SUBJECT_IS_HERE = { strategy: "css_path", query: "h2.subject" };
const ORDER_NUMBER = { name: "order_id", where: { strategy: "css_path", query: "span.order-ref" } };

function watch(over = {}) {
  return {
    id: "trg-1",
    host: GMAIL,
    terms: [FROM_THE_CUSTOMER, ASKING_FOR_STATUS],
    values: [ORDER_NUMBER],
    sender_at: SENDER_IS_HERE,
    subject_at: SUBJECT_IS_HERE,
    ...over,
  };
}

/** A mail on screen, as the marks see it: a selector to the text under it. */
function mail({ sender, subject, order = "4471" }) {
  return {
    "span.from": sender,
    "h2.subject": subject,
    "span.order-ref": order,
  };
}

/** Runs the real watch.js in a context with just enough page to point at.
 *
 * The selector engine is a lookup table on purpose: what is under test is the
 * rule, not `querySelectorAll`, and a real DOM here would only prove jsdom
 * works. `run()` hands back what the frame sent to the worker.
 */
function open(watches, onScreen) {
  const sent = [];
  let due = null;
  const node = (text) => ({
    textContent: text,
    childNodes: [{ nodeType: 3, textContent: text }],
    contains: () => false,
  });
  const sandbox = {
    document: {
      documentElement: {},
      querySelectorAll: (selector) =>
        selector in onScreen && onScreen[selector] !== undefined
          ? [node(onScreen[selector])]
          : [],
    },
    CSS: { escape: (value) => value },
    MutationObserver: class {
      observe() {}
    },
    setTimeout: (fn) => {
      due = fn;
      return 1;
    },
    clearTimeout: () => {
      due = null;
    },
    chrome: {
      runtime: {
        sendMessage: (message) => {
          if (message.kind === "watches") return Promise.resolve({ watches });
          sent.push(message);
          return Promise.resolve({ ok: true });
        },
      },
      storage: { onChanged: { addListener: () => {} } },
    },
    sent,
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(SOURCE, sandbox);

  /** Let the worker's answer land, then let the page settle. Twice over, so a
   * second call is a second chance to make the same offer -- which is what
   * the dedup case needs to be able to fail.
   *
   * Copied out of the vm's realm on the way back: an object made in there has
   * a different `Object.prototype`, and `deepStrictEqual` calls that a
   * difference. This is also exactly what `chrome.runtime.sendMessage`
   * serialises, so it is the right thing to be asserting on.
   */
  const run = async () => {
    for (let turn = 0; turn < 4; turn += 1) await Promise.resolve();
    if (due) due();
    return JSON.parse(JSON.stringify(sent));
  };
  return { run, sent };
}

const tests = [];
const test = (name, fn) => tests.push([name, fn]);

// --- what the matcher actually decides --------------------------------------

test("a mail that matches every term is one of these", async () => {
  const { run } = open(
    [watch()],
    mail({ sender: "ops@northwind.example", subject: "Order status for PO 4471?" }),
  );

  assert.deepStrictEqual(await run(), [
    { kind: "watch-matched", triggerId: "trg-1", values: { order_id: "4471" } },
  ]);
});

test("the terms are all of them, not any of them", async () => {
  const { run } = open(
    [watch()],
    mail({ sender: "hr@acme.example", subject: "Order status for PO 4471?" }),
  );

  // Nothing at all: the subject term matched and the SENDER did not, and a
  // sender is not something a mail can nearly be from. Every address shares
  // `example` with every other one.
  assert.deepStrictEqual(await run(), []);
});

test("the same mail, framed the way the next person wrote it", async () => {
  // The weakness an operator named. A substring matched the mail they pointed
  // at and nothing else anybody wrote: order, punctuation and case are what
  // vary between two people writing about the same thing, and none of them is
  // what the operator was choosing when they marked a phrase.
  for (const subject of [
    "Status of your order, PO 4471",
    "ORDER-STATUS: PO 4471",
    "orders status update",
  ]) {
    const { run } = open([watch()], mail({ sender: "ops@northwind.example", subject }));
    const said = await run();
    assert.strictEqual(
      said.filter((one) => one.kind === "watch-matched").length,
      1,
      `no match for: ${subject}`,
    );
  }
});

test("a mail about something else is not a near miss either", async () => {
  const { run } = open(
    [watch()],
    mail({ sender: "ops@northwind.example", subject: "Your payslip is ready" }),
  );

  assert.deepStrictEqual(await run(), [], "a mail with none of the words was reported");
});

test("a subject with some of the words is a near miss, said in the operator's own", async () => {
  // The third failure, and the one that was silent. A rule that misses without
  // saying so is worse than one that fires half-way: the operator believes
  // their browser is watching for something and it is not. What leaves the
  // frame is the term THEY wrote -- never a word of the mail, which is the
  // line ADR 008 draws.
  const { run } = open(
    [watch()],
    mail({ sender: "ops@northwind.example", subject: "Status of PO 9999" }),
  );

  const said = await run();
  assert.deepStrictEqual(said, [
    { kind: "watch-nearly", triggerId: "trg-1", terms: ["order status"] },
  ]);
  assert.doesNotMatch(JSON.stringify(said), /9999/, "the mail's own text left the frame");
});

test("nobody writes a subject the way they typed it yesterday", async () => {
  const { run } = open(
    [watch()],
    mail({ sender: "OPS@Northwind.Example", subject: "ORDER STATUS: 4471" }),
  );

  assert.strictEqual((await run()).length, 1);
});

test("a lookalike host is not the mailbox this was made for", () => {
  // The host half of `Watch.matches`, which the worker applies before a page
  // is handed a rule at all: `domain_matches`, never a suffix test.
  assert.strictEqual(hostMatches("notmail.google.com", GMAIL), false);
});

test("a subdomain of the watched host still counts", () => {
  assert.strictEqual(hostMatches("mail.acme.example", "acme.example"), true);
  assert.strictEqual(hostMatches(GMAIL, GMAIL), true);
  assert.strictEqual(hostMatches("mail.google.com.", "mail.google.com"), true);
});

test("a term with nothing in it is the same as no term at all", async () => {
  // The domain refuses one, because `"" in anything` is true and the watch
  // would fire on every mail that arrives. A browser handed one anyway is the
  // case worth being narrow about.
  const { run } = open(
    [watch({ terms: [{ field: "subject", contains: "  " }] })],
    mail({ sender: "ops@northwind.example", subject: "Order status" }),
  );

  assert.deepStrictEqual(await run(), []);
});

// --- what a match is allowed to say -----------------------------------------

test("a mark that points at nothing is a mail that did not match", async () => {
  // A client that re-rendered, or a page in that mailbox that is not a mail.
  // An unreadable header is an empty one, and no term that exists matches an
  // empty string -- so the miss is silent and the false match impossible.
  const { run } = open(
    [watch()],
    mail({ sender: undefined, subject: "Order status for PO 4471?" }),
  );

  assert.deepStrictEqual(await run(), []);
});

test("nothing but the watch id and the values leaves the page", async () => {
  const [offer] = await open(
    [watch()],
    mail({ sender: "ops@northwind.example", subject: "Order status for PO 4471?" }),
  ).run();

  assert.deepStrictEqual(Object.keys(offer).sort(), ["kind", "triggerId", "values"]);
  // The proof, rather than the intention: the subject and the sender are in
  // the frame's memory and in nothing it sent.
  const wire = JSON.stringify(offer);
  assert.ok(!wire.includes("northwind"), wire);
  assert.ok(!wire.toLowerCase().includes("order status"), wire);
});

test("a watch that reads nothing still fires", async () => {
  const { run } = open(
    [watch({ values: [] })],
    mail({ sender: "ops@northwind.example", subject: "Order status" }),
  );

  assert.deepStrictEqual(await run(), [
    { kind: "watch-matched", triggerId: "trg-1", values: {} },
  ]);
});

test("a mail is offered once, not once a second", async () => {
  // A mail client mutates its DOM constantly, and the offer is re-evaluated
  // every time it settles. Without this an open mail is an offer a second for
  // as long as somebody is reading it.
  const open_ = open(
    [watch()],
    mail({ sender: "ops@northwind.example", subject: "Order status for PO 4471?" }),
  );
  await open_.run();

  assert.strictEqual((await open_.run()).length, 1);
});

test("a body that arrived through a sloppy mark is not a value", async () => {
  const body = "x".repeat(5000);
  const [offer] = await open(
    [watch()],
    mail({ sender: "ops@northwind.example", subject: "Order status", order: body }),
  ).run();

  assert.strictEqual(offer.values.order_id.length, 200);
});

// The house style here is a straight line of asserts and one line of output:
// each case above is named so a failure says which rule broke, and the first
// one stops the run.
for (const [name, fn] of tests) {
  try {
    await fn();
  } catch (error) {
    throw new Error(`${name}: ${error.message}`, { cause: error });
  }
}
console.log("watch.test.mjs: ok");
