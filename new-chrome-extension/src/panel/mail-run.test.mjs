// mail-run.test.mjs
//
// The card for a run a mail started: the mail arrived, this job was noticed,
// and how it went -- live, and the only card for that mail.
//
// Run with `node src/panel/mail-run.test.mjs`.

import assert from "node:assert/strict";
import test from "node:test";

import { asMarkup, install, words } from "./test-support/fake-document.mjs";

install();

const { mailRunCard } = await import("./mail-run.js");

const run = (over = {}) => ({
  id: "run_1",
  status: "running",
  title: "Create a Transport Equipment Type",
  values: { Equipment: "AITE4", longDescription: "AI-SRO test" },
  started_at: "2026-09-29T11:02:10",
  finished_at: null,
  steps: [],
  mail: {
    subject: "create transport equipment type AITE4",
    sender: "Devansh <devansh@example.com>",
    arrived: "2026-09-29T11:02:07+05:30",
    thread: "t-1",
    link: "https://mail.google.com/mail/#all/t-1",
  },
  ...over,
});

const buttons = (card) => {
  const all = [];
  const walk = (el) => {
    if (el.tag === "button") all.push(el);
    for (const kid of el.kids || []) walk(kid);
  };
  walk(card);
  return all;
};

test("running: arrived, noticed with its values, running -- and where to look", () => {
  const card = mailRunCard(run(), { live: { liveViewUrl: "https://steel/v" } });
  const said = words(card);

  assert.match(said, /create transport equipment type AITE4/);
  assert.match(said, /Arrived .* from Devansh <devansh@example.com>/);
  assert.match(said, /Noticed: Create a Transport Equipment Type/);
  assert.match(said, /Equipment: AITE4/);
  assert.match(said, /Running/);
  assert.deepEqual(
    buttons(card).map((one) => one.textContent),
    ["Open the mail", "Watch it run", "Review in console", "Stop", "Dismiss"],
  );
  assert.equal(card.dataset.tone, "live");
  assert.deepEqual(asMarkup, [], "mail text reached innerHTML");
});

test("held: completed, and nothing left to stop or watch", () => {
  const card = mailRunCard(run({ status: "held", finished_at: "2026-09-29T11:02:22" }));

  assert.match(words(card), /Completed at \d\d:\d\d in 12 s\./);
  assert.deepEqual(
    buttons(card).map((one) => one.textContent),
    ["Open the mail", "Review in console", "Dismiss"],
  );
});

test("did not finish: says why", () => {
  const card = mailRunCard(
    run({
      status: "failed",
      finished_at: "2026-09-29T11:03:00",
      steps: [
        { index: 0, outcome: "held", reason: "" },
        { index: 1, outcome: "failed", reason: "the session expired" },
      ],
    }),
  );

  assert.match(words(card), /Not created: the session expired\./);
  assert.doesNotMatch(words(card), /Running/);
  assert.equal(card.dataset.tone, "attention");
});

test("parked on a person: Needs you and the question, never Running", () => {
  const answered = [];
  const card = mailRunCard(
    run({ asking: "'Click the save button.' was sent and nothing confirms it" }),
    { onAnswer: (question, one) => answered.push([question, one.id]) },
  );
  const said = words(card);

  assert.match(said, /Needs you: 'Click the save button.' was sent/);
  assert.doesNotMatch(said, /Running/);
  assert.equal(card.dataset.tone, "attention");
  const labels = buttons(card).map((one) => one.textContent);
  assert.equal(labels[0], "Answer it", "the way out is the first thing on the card");
  assert.ok(labels.includes("Stop"), "a parked run can still be stopped");
  buttons(card)[0].listeners.click[0]();
  assert.deepEqual(answered, [[null, "run_1"]]);
});

test("refused, with its question standing: Needs you, not Not created", () => {
  const question = {
    id: "m-9",
    run: "run_1",
    threadId: "thr_ask_1",
    text: "Create a Customer Type was not done: the system refused it: code 42 is used. What should Voice Code be?",
  };
  const answered = [];
  const card = mailRunCard(
    run({
      status: "failed",
      finished_at: "2026-09-29T11:03:00",
      steps: [{ index: 0, outcome: "failed", reason: "the system refused it: code 42 is used" }],
    }),
    { questions: [question], onAnswer: (one) => answered.push(one.threadId) },
  );
  const said = words(card);

  assert.match(said, /Needs you: .*What should Voice Code be\?/);
  assert.doesNotMatch(said, /Running|Not created/);
  assert.equal(buttons(card)[0].textContent, "Answer it");
  buttons(card)[0].listeners.click[0]();
  assert.deepEqual(answered, ["thr_ask_1"]);
});

test("another run's question is not this card's", () => {
  const card = mailRunCard(
    run({ status: "failed", steps: [{ index: 0, outcome: "failed", reason: "refused" }] }),
    { questions: [{ id: "m-1", run: "run_2", text: "What should X be?" }] },
  );

  assert.match(words(card), /Not created: refused\./);
  assert.ok(!buttons(card).some((one) => one.textContent === "Answer it"));
});

test("each press hands the run to its caller", () => {
  const pressed = [];
  const card = mailRunCard(run(), {
    live: { liveViewUrl: "https://steel/v" },
    onOpen: (url) => pressed.push(["open", url]),
    onReview: (one) => pressed.push(["review", one.id]),
    onStop: (one) => pressed.push(["stop", one.id]),
    onDismiss: (one) => pressed.push(["dismiss", one.id]),
  });

  for (const one of buttons(card)) one.listeners.click[0]();

  assert.deepEqual(pressed, [
    ["open", "https://mail.google.com/mail/#all/t-1"],
    ["open", "https://steel/v"],
    ["review", "run_1"],
    ["stop", "run_1"],
    ["dismiss", "run_1"],
  ]);
});

test("two mails asked about: each card is drawn from its own question", () => {
  // The newest question was the only one held, so the older refused mail said
  // "Not created" with no way to answer while its question still stood.
  const failed = { status: "failed", steps: [{ index: 0, outcome: "failed", reason: "refused" }] };
  const questions = [
    { id: "m-2", run: "run_2", threadId: "thr_2", text: "What should Y be?" },
    { id: "m-1", run: "run_1", threadId: "thr_1", text: "What should X be?" },
  ];
  const answered = [];
  const onAnswer = (one) => answered.push(one.threadId);

  const older = mailRunCard(run({ id: "run_1", ...failed }), { questions, onAnswer });
  const newer = mailRunCard(run({ id: "run_2", ...failed }), { questions, onAnswer });

  assert.match(words(older), /Needs you: What should X be\?/);
  assert.match(words(newer), /Needs you: What should Y be\?/);
  buttons(older)[0].listeners.click[0]();
  assert.deepEqual(answered, ["thr_1"], "Answer it went to another mail's chat");
});
