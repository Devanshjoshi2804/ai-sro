// `calls.since`: the calls the page made because of the command just sent.
//
// This is the answer the backend's strongest verification rung is built on --
// a step held by the status the warehouse actually returned, instead of a
// screenshot and a model asked what it saw. It answered `{calls: []}` for
// every step this deployment ever ran: the backend sends `since` as server
// epoch seconds and the recorder's calls carry ISO strings, so the filter
// `"2026-09-14T19:41:09.469Z" >= 1789414869.469` was false every time. The
// rung never fired once in 91 recorded steps, and `RunStep.made` -- which is
// filled from the same answer -- was empty on every run, so no run could say
// which records it created.
//
// Run with `node src/background/calls-since.test.mjs`.

import assert from "node:assert";
import { test } from "node:test";

const THE_TAB = { id: 7, url: "https://wms.example/portal", active: true };

globalThis.chrome = {
  tabs: {
    query: async () => [THE_TAB],
    get: async (id) => (id === THE_TAB.id ? THE_TAB : null),
    sendMessage: async () => ({}),
    update: async () => THE_TAB,
    // `reacted()` watches the tab for the page's answer to the click. Nothing
    // here fires them; they exist so the wait tidies up after itself.
    onUpdated: { addListener: () => {}, removeListener: () => {} },
  },
  webNavigation: {
    onHistoryStateUpdated: { addListener: () => {}, removeListener: () => {} },
  },
  scripting: { executeScript: async () => [{ result: { ok: true } }] },
  runtime: { sendMessage: async () => ({}), lastError: null },
  storage: { local: { get: async () => ({}), set: async () => {} } },
};

const { perform, noteDriven } = await import("./commands.js");

const RUN = "run-1";
const TAB = 7;

/** A command that touches the page, which is what starts a window of calls. */
const acted = () =>
  perform({
    command_id: "cmd-act",
    kind: "ui.perform",
    run_id: RUN,
    payload: { origin: "https://wms.example", action: "click", target: { css: "#save" } },
  });

const asked = () =>
  perform({
    command_id: "cmd-since",
    kind: "calls.since",
    run_id: RUN,
    // What the backend really sends: the server's own clock, in epoch
    // seconds. Nothing here may depend on it.
    payload: { since: Date.now() / 1000 },
  });

const captured = (over) => ({
  method: "POST",
  url: "https://wms.example/wm/equipmentTypes",
  status: 201,
  // As the recorder produces it, and the shape that made the old comparison
  // always false.
  started_at: new Date().toISOString(),
  ...over,
});

test("a create made after the command comes back with its status", async () => {
  await acted();
  noteDriven(TAB, captured());

  const answer = await asked();

  assert.equal(answer.ok, true);
  assert.equal(answer.result.calls.length, 1, "the status rung was answered nothing again");
  assert.equal(answer.result.calls[0].status, 201);
});

test("what the page was already doing before the command is not this step's", async () => {
  noteDriven(TAB, captured({ url: "https://wms.example/telemetry", status: 200 }));
  await acted();
  noteDriven(TAB, captured());

  const answer = await asked();

  assert.deepEqual(
    answer.result.calls.map((call) => call.url),
    ["https://wms.example/wm/equipmentTypes"],
  );
});

test("the second step of a run does not see the first step's create", async () => {
  // The repeat case, and why this is a counter and not a parsed timestamp: a
  // browser a few minutes off the server would pass item 1's 201 into item
  // 2's verify, which takes the first method-and-shape match walking
  // backwards -- item 2 would be held by item 1's write and would report item
  // 1's identifier as the record it made.
  await acted();
  noteDriven(TAB, captured({ url: "https://wms.example/wm/equipmentTypes/first" }));
  await asked();

  await acted();
  const second = await asked();

  assert.deepEqual(second.result.calls, [], "item 2 was held by item 1's write");
});

test("looking does not move the window: asking twice answers twice", async () => {
  await acted();
  noteDriven(TAB, captured());

  const first = await asked();
  const again = await asked();

  assert.equal(first.result.calls.length, 1);
  assert.equal(again.result.calls.length, 1, "asking consumed the evidence it was asked for");
});

test("a call still in flight is not evidence of anything", async () => {
  await acted();
  noteDriven(TAB, captured({ status: null }));

  const answer = await asked();

  assert.deepEqual(answer.result.calls, []);
});
