// Self-check for what a lookup came back with.
//
// The panel showed 240 characters of raw JSON per system, which is a preview of
// an answer rather than an answer: "how many suppliers are at SG" got
// `{"data":[{"supplierNumber":"100012","supplierName":"ACME LOGIS` and the
// person counted nothing.
//
// The shapes here are the real ones. Across the 296 captured exchange files in
// this repository's knowledge base, 88 of the list responses put their rows
// under `data` -- `activityCodes` answers 257 of them with `activityCode` and
// `description` among the columns -- and three carry `errors` with `errorCode`
// and `userMessage`.
//
// Run with `node src/panel/result.test.mjs`.

import assert from "node:assert";

import { install, words } from "./test-support/fake-document.mjs";

install();

const { K_ROWS, result } = await import("./result.js");

const tests = [];
let failed = 0;
const test = (name, fn) => tests.push([name, fn]);

const answered = (body, over = {}) => ({
  system: "wms",
  target: "activityCodes",
  ok: true,
  detail: "",
  status: 200,
  body: typeof body === "string" ? body : JSON.stringify(body),
  ...over,
});

const codes = (n) =>
  Array.from({ length: n }, (_, at) => ({
    activityCode: `AC${at}`,
    description: `activity ${at}`,
    activityCategory: "PICK",
  }));

test("the count is the first thing, because it is the answer", () => {
  // Somebody asking "how many" has been answered the moment they read it. The
  // table is what they check it against.
  const card = result(answered({ data: codes(257) }));

  assert.match(words(card), /257 found/);
  assert.match(words(card), /activityCode/);
  assert.match(words(card), /first 8 of 257/);
});

test("eight rows, six columns, and the rest are in the console", () => {
  // A panel beside a warehouse screen is not where somebody reads two hundred
  // rows, and a record with forty fields makes a table nobody can read on a
  // 360-pixel column.
  const wide = codes(20).map((one, at) => ({
    ...one,
    a: at,
    b: at,
    c: at,
    d: at,
    e: at,
  }));
  const card = result(answered({ data: wide }));
  const rows = card.kids.find((kid) => kid.className === "rows");
  const table = rows.kids[0];

  assert.equal(
    table.kids.length - 1,
    K_ROWS,
    "more rows than the panel can hold",
  );
  assert.equal(table.kids[0].kids.length, 6, "more columns than fit");
});

test("a field the record does not carry is a dash, not a blank", () => {
  // In a warehouse "no value" and "the value is empty" are different facts.
  const card = result(
    answered({ data: [{ activityCode: "AC1" }, { description: "only me" }] }),
  );

  assert.match(words(card), /—/);
});

test("an empty list says so rather than drawing an empty table", () => {
  const card = result(answered({ data: [] }));

  assert.match(words(card), /0 found/);
  assert.ok(!card.kids.some((kid) => kid.className === "rows"));
});

test("the system's own words, where it answered with an error", () => {
  // Better than ours: a message written by the people who know what it means.
  const card = result(
    answered({
      errors: [{ errorCode: "WM-1234", userMessage: "Record already exists" }],
    }),
  );

  assert.match(words(card), /WM-1234 — Record already exists/);
  assert.doesNotMatch(words(card), /found/);
});

test("a refusal says the status and what came with it", () => {
  const card = result(
    answered("", { ok: false, status: 403, detail: "Forbidden" }),
  );

  assert.equal(card.dataset.ok, "false");
  assert.match(words(card), /Forbidden/);
});

test("an answer that is not a list is shown as it came", () => {
  // One record, a number, a page. Trimmed, not parsed into a table it is not.
  const card = result(
    answered({ customerType: "GPP", longDescription: "leaning" }),
  );

  assert.doesNotMatch(words(card), /found/);
  assert.match(words(card), /customerType/);
});

test("a screen lookup says the screen came up, since its picture is not here", () => {
  const card = result({
    system: "wms",
    target: "the customer types screen",
    ok: true,
    detail: "",
    status: null,
    body: null,
    seen: { text_digest: "d4f1a9c0b7e2" },
  });

  assert.match(words(card), /the screen came up/);
});

test("an older answer is its count and a way back to it", () => {
  // A conversation with four tables in it is a conversation nobody scrolls.
  const opened = [];
  const card = result(answered({ data: codes(239) }), {
    open: false,
    onOpen: () => opened.push(1),
  });

  assert.match(words(card), /239 found/);
  assert.ok(
    !card.kids.some((kid) => kid.className === "rows"),
    "the table was drawn in a collapsed answer",
  );
  card.kids.find((kid) => kid.tag === "button").listeners.click[0]();
  assert.deepEqual(opened, [1]);
});

test("a column that is empty in every row is not one of the six", () => {
  // Measured on the deployment 2026-09-21, beside the warehouse's own screen.
  // The WMS grid showed `Customer Type | Description`; the panel showed
  //
  //     URNFORMAT  ABSOLUTEGROUP  ALLOCATIONSEARCHPATH  ALLOWSOURCE…  BULKPI…
  //         —            —                 —                 —          false
  //
  // because it took the first six KEYS and Blue Yonder alphabetises its
  // payload. A column empty in every row it is drawn for cannot tell anybody
  // anything, and it costs the one that could.
  const rows = [
    {
      URNFormat: null,
      absoluteGroup: null,
      customerType: "KKYT",
      longDescription: "my sro",
    },
    {
      URNFormat: null,
      absoluteGroup: null,
      customerType: "DDD",
      longDescription: "leaning",
    },
  ];
  const card = result(answered({ data: rows }));
  const said = words(card);

  assert.match(said, /customerType/);
  assert.match(said, /longDescription/);
  assert.ok(!said.includes("URNFormat"), `an empty column was drawn: ${said}`);
  assert.ok(
    !said.includes("absoluteGroup"),
    `an empty column was drawn: ${said}`,
  );
});

test("records that are genuinely all blank still draw a table", () => {
  // Drawing nothing would be worse than drawing what is there.
  const card = result(
    answered({
      data: [
        { a: null, b: null },
        { a: null, b: null },
      ],
    }),
  );

  assert.match(words(card), /2 found/);
  assert.ok(
    card.kids.some((kid) => kid.className === "rows"),
    "no table at all",
  );
});

test("the row the question names comes first, and says so", () => {
  // "is there a customer type called KKYT" was answered with eight rows of
  // whatever the system returned first, and KKYT was not among them -- an
  // answer that contains the answer and does not show it.
  const many = codes(30).map((one, at) => ({
    ...one,
    activityCode: `AC${at}`,
  }));
  const card = result(
    answered({
      data: [...many, { activityCode: "KKYT", description: "mine" }],
    }),
    {
      asked: "is there a customer type called KKYT",
    },
  );
  const table = card.kids.find((kid) => kid.className === "rows").kids[0];
  const first = table.kids[1];

  assert.match(
    words(first),
    /KKYT/,
    `the row asked about is not first: ${words(table)}`,
  );
  assert.equal(first.dataset.asked, "1", "the row asked about is not marked");
});

test("a question that names nothing in the data leaves the order alone", () => {
  // A system's own order is a fact about the system, and shuffling what
  // nobody asked about would be this panel inventing a ranking.
  const card = result(answered({ data: codes(5) }), {
    asked: "how many are there",
  });
  const table = card.kids.find((kid) => kid.className === "rows").kids[0];

  assert.match(words(table.kids[1]), /AC0/);
});

test("a trimmed answer does not report its own trim as the total", () => {
  // The body is cut BY RECORD so it stays parseable, which means the count is
  // the count of what arrived and not of what the system holds. "40 found" is
  // a number nobody can act on, presented as one they can.
  const card = result(answered({ data: codes(40) }, { truncated: true }));

  assert.match(words(card), /at least 40 found/);
  assert.match(words(card), /first 8 of 40\+/);
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
