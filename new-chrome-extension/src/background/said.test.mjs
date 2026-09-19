// What this browser did, kept where a person can still read it.
//
// A service worker's console dies with the worker, and this extension knows
// that happens constantly: a worker evicted between two commands is what lost
// a run its tab and cost an operator an evening of sign-in loops. The console
// had the whole story and nobody could ever read it.
//
// Run with `node src/background/said.test.mjs`.

import assert from "node:assert/strict";
import { test } from "node:test";

let stored = {};
let shown = [];

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

for (const level of ["log", "warn", "error"]) {
  console[level] = (...said) => shown.push([level, said.join(" ")]);
}

const { K_KEPT, forgetSaid, said, say } = await import("./said.js");

const fresh = () => {
  stored = {};
  shown = [];
};

test("a refusal is kept, because the worker that saw it will not last", async () => {
  fresh();

  await say("warn", "a command was refused", {
    kind: "ui.perform",
    run: "run_4a57baf0",
    error: "no_tab_for_system",
  });

  const kept = await said();
  assert.equal(kept.length, 1);
  assert.equal(kept[0].what, "a command was refused");
  assert.equal(kept[0].run, "run_4a57baf0");
  assert.equal(kept[0].error, "no_tab_for_system");
  assert.equal(kept[0].level, "warn");
  assert.ok(kept[0].at > 0, "and when");
});

test("an ordinary line reaches the console and is not kept", async () => {
  // A ring full of "sent ui.perform" is a ring with no room for the failure,
  // and a storage write per command is the cost this codebase already refuses
  // for a write per keystroke.
  fresh();

  await say("info", "sent a command", { kind: "ui.perform" });

  assert.deepEqual(await said(), []);
  assert.equal(shown.length, 1, "the console still has it");
});

test("a line worth reading afterwards is kept even when it is ordinary", async () => {
  fresh();

  await say("info", "a run started", { run: "run_1" }, { keep: true });

  assert.equal((await said()).length, 1);
});

test("only ids are kept, whatever a caller passes", async () => {
  // This buffer exists to be handed to somebody, so a typed value, a password
  // or a page's text must not be able to reach it through an attribution.
  fresh();

  await say("warn", "a command was refused", {
    run: "run_1",
    value: "ACME-4471",
    password: "hunter2",
    page_text: "Customer Type GGD",
  });

  const [kept] = await said();
  assert.deepEqual(Object.keys(kept).sort(), ["at", "level", "run", "what"]);
});

test("the ring keeps the newest and forgets the oldest", async () => {
  fresh();

  for (let n = 0; n < K_KEPT + 20; n += 1) {
    await say("warn", `refusal ${n}`, {});
  }

  const kept = await said();
  assert.equal(kept.length, K_KEPT);
  assert.equal(kept[0].what, "refusal 20", "the oldest went");
  assert.equal(kept.at(-1).what, `refusal ${K_KEPT + 19}`);
});

test("a ring that cannot be written does not fail what it was logging about", async () => {
  fresh();
  const was = chrome.storage.local.set;
  chrome.storage.local.set = async () => {
    throw new Error("quota");
  };

  await say("error", "a command blew up", { run: "run_1" });

  chrome.storage.local.set = was;
  assert.equal(shown.at(-1)[0], "error", "the console still has it");
});

test("forgetting takes the lot, because the buffer is this operator's", async () => {
  fresh();
  await say("warn", "a command was refused", {});

  await forgetSaid();

  assert.deepEqual(await said(), []);
});
