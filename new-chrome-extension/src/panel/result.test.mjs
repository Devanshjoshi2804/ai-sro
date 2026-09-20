// Self-check for what a lookup came back with.
//
// This file used to parse the raw body, hunt for the rows and pick columns,
// and so did the console, and so did anything else that drew an answer. Three
// guesses at one question. Measured on the deployment 2026-09-21, beside the
// warehouse's own screen: the WMS grid showed `Customer Type | Description`,
// and the panel drew `URNFORMAT | ABSOLUTEGROUP | ALLOCATIONSEARCHPATH` as
// columns of em dashes -- the first six KEYS of a payload that alphabetises.
//
// The lookup plane now reads through `application/execution/answer.py`, which
// every other read in this system already used, so what arrives here is a
// structure: the sentence, the count the SYSTEM stated, the columns that
// carry a value ranked with code and name first, and the records projected
// onto them. What is left on this side is one judgement the reader cannot
// make, because it is never given the question: which record was asked about.
//
// Run with `node src/panel/result.test.mjs`.

import assert from "node:assert";

import { install, words } from "./test-support/fake-document.mjs";

install();

const { K_ROWS, result } = await import("./result.js");

const tests = [];
let failed = 0;
const test = (name, fn) => tests.push([name, fn]);

/** The card list, the cards in it, and the pager -- named once, because a
 * test reaching into `kids[0].kids[1]` is a test that breaks when a wrapper
 * moves and says nothing about what broke. */
const records = (card) => card.kids.find((kid) => kid.className === "records");
const shown = (card) =>
  records(card).kids.find((kid) => kid.className === "record-list").kids;
const paging = (card) =>
  records(card).kids.find((kid) => kid.className === "paging");
const next = (card) => {
  paging(card)
    .kids.find((kid) => kid.textContent === "→")
    .listeners.click[0]();
};

/** An answer as the backend now sends one.
 *
 * `over.read` MERGES into the read rather than replacing it -- a helper whose
 * override silently dropped `records` and `columns` would make a test of the
 * count pass on a card with no table at all.
 */
const read = (records, { read: over = {}, ...rest } = {}) => ({
  system: "wms",
  target: "/data/WM/wm/customerTypes",
  ok: true,
  detail: "",
  status: 200,
  body: null,
  truncated: false,
  ...rest,
  read: {
    rows: records.length,
    counted: records.length,
    partial: false,
    subject: "customer type",
    sentence: `There are ${records.length} customer type: …`,
    columns: ["customerType", "longDescription"],
    records,
    ...over,
  },
});

const types = (n, from = 0) =>
  Array.from({ length: n }, (_, at) => ({
    customerType: `CT${at + from}`,
    longDescription: `leaning SRO ${at + from}`,
  }));

/** An answer that is not records at all. */
const raw = (body, over = {}) => ({
  system: "wms",
  target: "/portal",
  ok: true,
  detail: "",
  status: 200,
  body,
  truncated: false,
  read: null,
  ...over,
});

test("the sentence is the first thing, because it is the answer", () => {
  // Somebody asking a question has been answered by a line; the table is what
  // they check it against. The sentence is the READER's -- deterministic,
  // counted and named from the payload, never summarised by a model.
  const card = result(read(types(2)));

  assert.match(words(card), /There are 2 customer type/);
});

test("the columns are the ones the reader ranked, drawn as given", () => {
  // Nothing on this side picks them any more. `URNFormat` and `absoluteGroup`
  // never cross the wire.
  const card = result(read(types(2)));
  const said = words(card);

  assert.match(said, /customerType/);
  assert.match(said, /longDescription/);
  assert.ok(!said.includes("URNFormat"), said);
});

test("a page at a time, and a way to the rest", () => {
  // "first 8 of 110 -- the rest are in the console" is this panel telling
  // somebody to go and use a different product. 110 records is not a report;
  // it is a list somebody can page through where they are standing.
  const card = result(read(types(20)));

  assert.equal(shown(card).length, K_ROWS, "more records than a page holds");
  assert.match(words(card), /1–8 of 20/);

  next(card);

  assert.match(words(card), /9–16 of 20/);
  assert.match(
    words(shown(card)[0]),
    /CT8/,
    "the second page starts where the first ended",
  );
});

test("the last page stops rather than running off the end", () => {
  const card = result(read(types(10)));

  next(card);

  assert.equal(
    shown(card).length,
    2,
    "a short last page was padded or overran",
  );
  assert.match(words(card), /9–10 of 10/);
});

test("one page of records is drawn without controls nobody needs", () => {
  const card = result(read(types(3)));

  assert.equal(paging(card), undefined, "paging was drawn for a single page");
  assert.match(words(card), /1–3 of 3/);
});

test("a record reads downwards, and the fields it does not carry are left out", () => {
  // A table needs every row to have every column. A card does not, and eight
  // dashes under a heading is a card that says nothing.
  const card = result(read([{ customerType: "KKYT", longDescription: "" }]));
  const [only] = shown(card);
  const said = words(only);

  assert.match(said, /KKYT/);
  assert.ok(
    !said.includes("longDescription"),
    `an empty field was drawn: ${said}`,
  );
});

test("the record the question names comes first, and says so", () => {
  // "is there a customer type called KKYT" was answered with eight rows of
  // whatever the system returned first, and KKYT was not among them -- an
  // answer that contains the answer and does not show it.
  const card = result(
    read([
      ...types(30),
      { customerType: "KKYT", longDescription: "my sro is best" },
    ]),
    { asked: "is there a customer type called KKYT" },
  );
  const [first] = shown(card);

  assert.match(words(first), /KKYT/, "the record asked about is not first");
  assert.equal(
    first.dataset.asked,
    "1",
    "the record asked about is not marked",
  );
});

test("a word that describes the whole result names nothing in it", () => {
  // Measured on the deployment 2026-09-21. Asked "is there a customer type
  // called KKYT" over 110 records, `type` appeared in forty descriptions
  // ("leaning new SRO type 004"). Forty were promoted ahead of the one the
  // question named, and KKYT was not in the eight drawn.
  const noisy = Array.from({ length: 40 }, (_, at) => ({
    customerType: `CT${at}`,
    longDescription: `leaning new SRO type ${at}`,
  }));
  const card = result(
    read([...noisy, { customerType: "KKYT", longDescription: "mine" }]),
    {
      asked: "is there a customer type called KKYT",
    },
  );
  const [first] = shown(card);

  assert.match(
    words(first),
    /KKYT/,
    `a word matching most of the result won: ${words(first)}`,
  );
});

test("a question that names nothing in the records leaves the order alone", () => {
  // A system's own order is a fact about the system, and shuffling what
  // nobody asked about would be this panel inventing a ranking.
  const card = result(read(types(5)), { asked: "how many are there" });

  assert.match(words(shown(card)[0]), /CT0/);
});

test("a count nobody could state is never drawn as one", () => {
  // A page whose envelope did not say how large the set is. "50" would be a
  // fact about the request, not about the warehouse.
  const card = result(
    read(types(50), { read: { counted: null, partial: true } }),
  );

  assert.match(words(card), /1–8 of 50\+/);
});

test("a collapsed answer says what it found and offers to show it", () => {
  const opened = [];
  const card = result(read(types(239)), {
    open: false,
    onOpen: () => opened.push(1),
  });

  assert.match(words(card), /There are 239 customer type/);
  assert.equal(
    records(card),
    undefined,
    "the list was drawn in a collapsed answer",
  );
  card.kids.find((kid) => kid.tag === "button").listeners.click[0]();
  assert.deepEqual(opened, [1]);
});

test("nothing found is said, not drawn as an empty table", () => {
  const card = result(
    read([], {
      read: {
        counted: 0,
        sentence: "Nothing matched — no customer type came back.",
      },
    }),
  );

  assert.match(words(card), /Nothing matched/);
  assert.ok(
    !card.kids.some((kid) => kid.className === "rows"),
    "an empty table was drawn",
  );
});

test("a refusal says what the system said, not a table", () => {
  const card = result({
    ...raw(null),
    ok: false,
    detail: "no tab is open on that system",
  });

  assert.match(words(card), /no tab is open/);
});

test("an error body is quoted in the system's own words", () => {
  // Ours would be a translation of a message written by the people who know
  // what it means.
  const card = result(
    raw(
      JSON.stringify({
        errors: [{ errorCode: "WM-404", userMessage: "no such site" }],
      }),
    ),
  );

  assert.match(words(card), /WM-404 — no such site/);
});

test("an answer that is not records is shown as it came", () => {
  const card = result(raw("<html><body>a page</body></html>"));

  assert.match(words(card), /a page/);
});

test("a screen that came up says so", () => {
  const card = result({
    ...raw(null),
    seen: { text_digest: "Customer Types" },
  });

  assert.match(words(card), /the screen came up/);
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
  console.error(`result.test.mjs: ${failed} failed`);
  process.exit(1);
}
console.log(`result.test.mjs: ok (${tests.length})`);
