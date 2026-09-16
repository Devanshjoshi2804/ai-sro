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
  const wide = codes(20).map((one, at) => ({ ...one, a: at, b: at, c: at, d: at, e: at }));
  const card = result(answered({ data: wide }));
  const rows = card.kids.find((kid) => kid.className === "rows");
  const table = rows.kids[0];

  assert.equal(table.kids.length - 1, K_ROWS, "more rows than the panel can hold");
  assert.equal(table.kids[0].kids.length, 6, "more columns than fit");
});

test("a field the record does not carry is a dash, not a blank", () => {
  // In a warehouse "no value" and "the value is empty" are different facts.
  const card = result(answered({ data: [{ activityCode: "AC1" }, { description: "only me" }] }));

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
    answered({ errors: [{ errorCode: "WM-1234", userMessage: "Record already exists" }] }),
  );

  assert.match(words(card), /WM-1234 — Record already exists/);
  assert.doesNotMatch(words(card), /found/);
});

test("a refusal says the status and what came with it", () => {
  const card = result(answered("", { ok: false, status: 403, detail: "Forbidden" }));

  assert.equal(card.dataset.ok, "false");
  assert.match(words(card), /Forbidden/);
});

test("an answer that is not a list is shown as it came", () => {
  // One record, a number, a page. Trimmed, not parsed into a table it is not.
  const card = result(answered({ customerType: "GPP", longDescription: "leaning" }));

  assert.doesNotMatch(words(card), /found/);
  assert.match(words(card), /customerType/);
});

test("a screen lookup says the screen came up, since its picture is not here", () => {
  const card = result({
    system: "wms", target: "the customer types screen", ok: true, detail: "", status: null,
    body: null, seen: { text_digest: "d4f1a9c0b7e2" },
  });

  assert.match(words(card), /the screen came up/);
});

test("an older answer is its count and a way back to it", () => {
  // A conversation with four tables in it is a conversation nobody scrolls.
  const opened = [];
  const card = result(answered({ data: codes(239) }), { open: false, onOpen: () => opened.push(1) });

  assert.match(words(card), /239 found/);
  assert.ok(
    !card.kids.some((kid) => kid.className === "rows"),
    "the table was drawn in a collapsed answer",
  );
  card.kids.find((kid) => kid.tag === "button").listeners.click[0]();
  assert.deepEqual(opened, [1]);
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
