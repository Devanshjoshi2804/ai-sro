// Self-check for the waiting question.
//
// Run with `node src/background/asking.test.mjs`.

import assert from "node:assert";
import { test } from "node:test";

const { questionAmong, questionIn } = await import("./asking.js");

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
