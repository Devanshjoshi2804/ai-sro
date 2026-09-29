// mail-runs.test.mjs
//
// A run the mail started, found in the list the panel polls, and what it ends.
// QA 2026-09-29: the backend read a mail, started its run on Steel, and it held
// in 12 s while Home said "0 offers". And the user's race: a mail the reader
// already ran, offered again as "Yes, do it" beside it.
//
// Run with `node src/background/mail-runs.test.mjs`.

import assert from "node:assert/strict";
import test from "node:test";
import { endTheOffersThatRan, mailRunsOfToday } from "./mail-runs.js";

const NOW = new Date("2026-09-29T11:20:00");
const run = (id, over = {}) => ({
  id,
  status: "running",
  workflow_id: "wfl_te",
  offer: `mail:m-${id}`,
  started_at: "2026-09-29T11:02:10",
  values: { Equipment: "AITE4" },
  mail: { subject: "new equipment type", sender: "Alex <a@x>", thread: "t-1", link: "L" },
  ...over,
});

test("today's mail runs, titled, and nothing else", () => {
  const got = mailRunsOfToday(
    [
      run("1"),
      run("2", { mail: null, offer: "" }),
      run("3", { started_at: "2026-09-28T23:59:00" }),
      run("4"),
    ],
    { now: NOW, dismissed: ["4"], titles: new Map([["wfl_te", "Create a Transport Equipment Type"]]) },
  );

  assert.deepEqual(
    got.map((one) => [one.id, one.title]),
    [["1", "Create a Transport Equipment Type"]],
  );
});

test("a run that knows only its thread takes the subject its card showed", () => {
  const [got] = mailRunsOfToday([run("1", { mail: { thread: "t-1", link: "L" } })], {
    now: NOW,
    nudges: [{ offer: "mail:m-1", mailSubject: "new equipment type", title: "Create TE" }],
  });

  assert.equal(got.mail.subject, "new equipment type");
  assert.equal(got.title, "Create TE");
});

test("an open card for an offer a run has taken ends, naming the run", () => {
  const nudges = [
    { id: "n1", state: "open", offer: "mail:m-1" },
    { id: "n2", state: "open", offer: "mail:m-9" },
    { id: "n3", state: "dismissed", offer: "mail:m-1" },
  ];

  const after = endTheOffersThatRan(nudges, [run("1")], 5);

  assert.deepEqual(after[0], {
    id: "n1",
    state: "accepted",
    offer: "mail:m-1",
    endedAt: 5,
    runId: "1",
  });
  assert.equal(after[1], nudges[1], "a card nothing ran stays as it was");
  assert.equal(after[2], nudges[2], "an ended card is not ended twice");
});
