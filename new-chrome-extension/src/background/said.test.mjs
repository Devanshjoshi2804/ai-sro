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

const { MAX_SAID, narrate, said, say } = await import("./said.js");

const fresh = () => {
  stored = {};
  shown = [];
};

test("a refusal is kept, because the worker that saw it will not last", async () => {
  fresh();

  await say("warn", "a command was refused", {
    command: "cmd_9f21",
    kind: "ui.perform",
    run: "run_4a57baf0",
    error: "no_tab_for_system",
  });

  const kept = await said();
  assert.equal(kept.length, 1);
  // A string, because `HeartbeatRequest.said` is a list of them and there are
  // browsers in the field that send strings. The ids ride on the end.
  assert.equal(typeof kept[0], "string");
  assert.match(kept[0], /^warn a command was refused/);
  assert.match(kept[0], /run=run_4a57baf0/);
  assert.match(kept[0], /error=no_tab_for_system/);
  // The id the backend minted and said on its own lines while this command was
  // in flight. Both halves of the step join on it.
  assert.match(kept[0], /command=cmd_9f21/);
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

test("narration is kept, because that is what it is for", async () => {
  fresh();

  await narrate("no longer waiting: an offer arrived", { run: "run_1" });

  const kept = await said();
  assert.equal(kept.length, 1);
  assert.match(kept[0], /run=run_1/);
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
  assert.match(kept, /run=run_1/);
  assert.doesNotMatch(kept, /ACME-4471/, "a typed value must not ride along");
  assert.doesNotMatch(kept, /hunter2/, "and nor must a password");
  assert.doesNotMatch(kept, /Customer Type GGD/, "and nor must the page");
});

test("the ring keeps the newest and forgets the oldest", async () => {
  fresh();

  for (let n = 0; n < MAX_SAID + 20; n += 1) {
    await say("warn", `refusal ${n}`, {});
  }

  const kept = await said();
  assert.equal(kept.length, MAX_SAID);
  assert.match(kept[0], /refusal 20$/, "the oldest went");
  assert.match(kept.at(-1), new RegExp(`refusal ${MAX_SAID + 19}$`));
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

test("two refusals at once both survive", async () => {
  // Read-modify-write over `chrome.storage` has no transaction. Before the
  // lock, two refusals a millisecond apart both read the buffer and both wrote
  // it back, and the second took the first with it -- invisibly, because the
  // line simply is not there afterwards.
  fresh();

  await Promise.all([
    say("warn", "one was refused", { run: "run_1" }),
    say("warn", "another was refused", { run: "run_2" }),
  ]);

  const kept = await said();
  assert.equal(kept.length, 2, kept.join(" | "));
});
