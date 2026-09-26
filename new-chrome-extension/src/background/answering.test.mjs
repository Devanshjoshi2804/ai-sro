// An answer pressed under a question carries that question's id.
//
// The door acts on the offer recorded under the id and no other, so a press
// under an older question can never start the newest offer's job.
//
// Run with `node src/background/answering.test.mjs`.

import assert from "node:assert/strict";
import { test } from "node:test";

const stored = { "sro.apiUrl": "http://api", "sro.token": "t" };
globalThis.chrome = {
  storage: {
    local: {
      get: async (keys) =>
        Object.fromEntries(
          (Array.isArray(keys) ? keys : [keys]).map((key) => [key, stored[key]]),
        ),
      set: async (pairs) => Object.assign(stored, pairs),
      remove: async () => {},
    },
  },
  runtime: { lastError: null },
};

const sent = [];
globalThis.fetch = async (url, options) => {
  sent.push([url, JSON.parse(options.body)]);
  return { ok: true, status: 200, json: async () => ({}), text: async () => "{}" };
};

const { api } = await import("./api.js");

test("the press sends the id of the question it was pressed under", async () => {
  await api.say("thr-1", "yes", "msg_7");
  await api.say("thr-1", "hello");

  assert.deepEqual(sent[0][1], { text: "yes", answering: "msg_7" });
  assert.deepEqual(sent[1][1], { text: "hello" });
  assert.match(sent[0][0], /\/v1\/threads\/thr-1\/messages$/);
});
