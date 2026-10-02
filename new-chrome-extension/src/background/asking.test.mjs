// Self-check for the waiting question.
//
// Run with `node src/background/asking.test.mjs`.

import assert from "node:assert";
import { test } from "node:test";

const { questionAmong, questionIn, questionsAmong, waitingOnReply } = await import(
  "./asking.js"
);

const asked = {
  id: "msg_1",
  speaker: "assistant",
  text: "I could not find To recipients for Forward an Email. What should To recipients be?",
  said_at: "2026-09-17T03:36:00Z",
  decision: {
    kind: "needs_values",
    workflow_id: "wfl_2",
    title: "Forward an Email",
    missing: ["To recipients"],
  },
};

test("the newest thing the assistant decided is the whole state", () => {
  const found = questionIn({ messages: [{ speaker: "operator", text: "do it" }, asked] });
  assert.equal(found.workflowId, "wfl_2");
  assert.deepEqual(found.missing, ["To recipients"]);
  assert.match(found.text, /What should To recipients be\?/);
});

test("a conversation that moved on is not waiting on anything", () => {
  // Otherwise the panel raises a banner about a job somebody abandoned twenty
  // minutes ago.
  const after = { speaker: "assistant", text: "239 suppliers", decision: { kind: "answer" } };
  assert.equal(questionIn({ messages: [asked, { speaker: "operator", text: "x" }, after] }), null);
});

test("an empty conversation is waiting on nothing", () => {
  assert.equal(questionIn({ messages: [] }), null);
  assert.equal(questionIn(null), null);
  assert.equal(questionIn({ messages: [{ speaker: "operator", text: "hello" }] }), null);
});

test("a request the server will not run by itself is waiting on the operator", () => {
  const found = questionIn({
    messages: [
      {
        id: "msg_2",
        speaker: "assistant",
        text: "Create a Customer Type. Should our system do it?",
        decision: { kind: "job", confirm: true, workflow_id: "wfl_1", title: "Create a Customer Type" },
      },
    ],
  });
  assert.equal(found.workflowId, "wfl_1");
  assert.deepEqual(found.missing, []);
  const offered = { speaker: "assistant", text: "x", decision: { kind: "job", workflow_id: "wfl_1" } };
  assert.equal(questionIn({ messages: [offered] }), null);
});

test("a question says which chat it is waiting in", () => {
  // It is asked in a chat of its own, and "Answer it" opens that chat.
  const found = questionIn({ id: "thr_ask_1", messages: [asked] });
  assert.equal(found.threadId, "thr_ask_1");
});

test("of several chats, the newest question waiting is the one held", () => {
  const older = { ...asked, id: "msg_old", said_at: "2026-09-17T03:00:00Z" };
  const answered = {
    id: "thr_ask_2",
    messages: [
      asked,
      { speaker: "assistant", text: "Running it now.", decision: { kind: "job", run_id: "run_1" } },
    ],
  };
  const found = questionAmong([
    { id: "thr-long", messages: [] },
    { id: "thr_ask_1", messages: [older] },
    answered,
    null,
  ]);
  assert.equal(found.id, "msg_old");
  assert.equal(found.threadId, "thr_ask_1");
  assert.equal(questionAmong([answered]), null);
});

test("every standing question is kept, newest first -- one card each", () => {
  const older = { ...asked, id: "msg_0", said_at: "2026-09-17T03:00:00Z" };
  const threads = [{ id: "t1", messages: [older] }, { id: "t2", messages: [asked] }];

  assert.deepEqual(questionsAmong(threads).map((one) => one.id), ["msg_1", "msg_0"]);
  assert.equal(questionAmong(threads).id, "msg_1");
});

// A wait on a reply is read off the chats, never stored: a stored one went
// stale (QA 2026-09-30, YPHD: "Waiting on a reply" two hours after the reply
// was read and the run finished) and, with no thread recorded, matched every
// other mail's question.
const sentAt = (at, to = "asker@example.com") => ({
  speaker: "system",
  said_at: at,
  text: "Sent.",
  decision: { kind: "mail_sent", sent: true, to, draft_id: "d1" },
});
const drafted = { speaker: "system", text: "Draft.", decision: { kind: "mail_draft" } };
const chat = (id, ...messages) => ({ id, messages });

test("a chat whose mail was sent and whose question still stands is waiting on the reply", () => {
  const waiting = waitingOnReply([
    chat("thr_a", asked, drafted, sentAt("2026-09-30T13:00:00Z")),
  ]);
  assert.equal(waiting.to, "asker@example.com");
  assert.equal(waiting.at, Date.parse("2026-09-30T13:00:00Z"));
});

test("a mail that definitely did not go is not a wait", () => {
  const notSent = { ...sentAt("2026-09-30T13:00:00Z"), decision: { kind: "mail_not_sent", sent: false } };
  assert.equal(waitingOnReply([chat("thr_a", asked, drafted, notSent)]), null);
});

test("a draft nobody sent is not a wait", () => {
  assert.equal(waitingOnReply([chat("thr_a", asked, drafted)]), null);
});

test("a reply read, a run started and finished ends the wait, whatever else is asked", () => {
  const yphd = chat(
    "thr_yphd",
    asked,
    drafted,
    sentAt("2026-09-30T11:00:00Z"),
    { speaker: "assistant", text: "A reply answered", decision: { kind: "note" } },
    { speaker: "assistant", text: "Should we?", decision: { kind: "job", workflow_id: "wfl_2" } },
    { speaker: "operator", text: "yes" },
    { speaker: "assistant", text: "Running", decision: { kind: "job", workflow_id: "wfl_2" } },
    { speaker: "assistant", text: "Done", decision: { kind: "run_done" } },
  );
  const other = chat("thr_pj26", asked);
  assert.equal(waitingOnReply([yphd, other]), null);
});

test("of two mails, only the one still awaiting its reply keeps a wait", () => {
  const answered = chat(
    "thr_1",
    asked,
    drafted,
    sentAt("2026-09-30T11:00:00Z", "one@example.com"),
    { speaker: "assistant", text: "A reply answered", decision: { kind: "needs_values", workflow_id: "wfl_2", missing: ["x"] } },
  );
  const waiting = chat("thr_2", asked, drafted, sentAt("2026-09-30T12:00:00Z", "two@example.com"));
  assert.equal(waitingOnReply([answered, waiting]).to, "two@example.com");
  assert.equal(waitingOnReply([answered]), null);
});
