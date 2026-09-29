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

  assert.match(words(card), /Completed at \d\d:\d\d/);
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

  assert.match(words(card), /Did not finish at \d\d:\d\d: the session expired/);
  assert.equal(card.dataset.tone, "attention");
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
