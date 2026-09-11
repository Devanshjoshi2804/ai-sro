// One socket, and the factory it is built with.
//
// Phase 5 deleted the second caller (`rig-channel.js`); `channel.js` and
// `createChannel` stay, and so does every check here that was about the
// factory rather than about the rig. Where a test needed a second channel to
// say anything -- a gesture going down one socket and not the other, a `dial`
// that names nowhere -- it now builds one through `stubbedChannel`, which is
// the same factory the backend channel is built with.
//
// `commands.perform` cannot be stubbed by assigning to the module namespace
// (an ES module namespace is read-only, and the assignment throws), so
// `createChannel` takes `perform` as an option defaulting to the real one.
// The tests that need a stub build their own channel through the same
// factory the two production channels are built with.
//
// Run with `node src/background/channel.test.mjs`.
import assert from "node:assert/strict";
import test, { after } from "node:test";

// The minimum of `chrome` these modules touch at import and in the paths under test.
const stored = new Map([
  ["sro.token", "backend-token"],
  ["sro.deviceId", "dev_1"],
  ["sro.deviceSecret", "shh"],
  ["sro.apiUrl", "http://backend:8000"],
]);
globalThis.chrome = {
  runtime: { getManifest: () => ({ version: "0.1.0" }) },
  storage: {
    local: {
      get: async (key) => (stored.has(key) ? { [key]: stored.get(key) } : {}),
      set: async (pairs) => Object.entries(pairs).forEach(([k, v]) => stored.set(k, v)),
      remove: async () => {},
    },
  },
  tabs: { query: async () => [{}, {}] },
};

// A WebSocket that records what was dialled and what was sent, and lets the
// test deliver a message. `readyState` is OPEN from construction so keepalive
// and answers flow without an event loop tick.
const opened = [];
class FakeSocket {
  constructor(url, protocols) {
    this.url = url;
    this.protocols = protocols;
    this.readyState = 1;
    this.sent = [];
    opened.push(this);
    queueMicrotask(() => this.onopen?.());
  }
  send(text) { this.sent.push(JSON.parse(text)); }
  close() { this.readyState = 3; this.onclose?.(); }
  deliver(message) { this.onmessage?.({ data: JSON.stringify(message) }); }
}
FakeSocket.OPEN = 1;
globalThis.WebSocket = FakeSocket;

const channel = await import("./channel.js");

const settle = () => new Promise((r) => setTimeout(r, 0));

// An open channel holds a 20-second keepalive interval, which would keep node
// running long after the last check.
after(() => {
  channel.close();
});

/** A second channel through the same factory, answering with a stub. `dial`
 * returning null is a channel with nowhere to dial, which is a state the
 * factory has to hold without erroring. */
function stubbedChannel(describe, perform, dial) {
  return channel.createChannel({
    describe,
    perform,
    dial:
      dial ||
      (async () => ({
        url: `ws://${describe}.test/v1/agents/dev_1/commands`,
        protocols: ["bearer", "tok"],
      })),
  });
}

test("the backend channel dials the backend with token and secret", async () => {
  await channel.settle();
  await settle();
  const socket = opened.find((s) => s.url.startsWith("ws://backend:8000"));
  assert.ok(socket, "dialled the backend");
  assert.equal(socket.url, "ws://backend:8000/v1/agents/dev_1/commands");
  assert.deepEqual(socket.protocols, ["bearer", "backend-token", "shh"]);
  assert.equal(socket.sent[0].kind, "hello");
});

test("a command is answered exactly once, on the socket it came in on", async () => {
  const one = stubbedChannel("second", async (command) => ({
    ok: true,
    result: { echoed: command.kind },
  }));
  await one.settle();
  await settle();
  const socket = opened.at(-1);
  socket.deliver({ command_id: "cmd_1", kind: "ui.url", deadline_ms: 1000, payload: {} });
  socket.deliver({ command_id: "cmd_1", kind: "ui.url", deadline_ms: 1000, payload: {} });
  await settle();
  const answers = socket.sent.filter((m) => m.command_id === "cmd_1");
  assert.equal(answers.length, 1, "a duplicate id is not answered twice");
  assert.deepEqual(answers[0], { command_id: "cmd_1", ok: true, result: { echoed: "ui.url" } });
  one.close();
});

test("every command carries the channel it came in on as its source", async () => {
  const sources = [];
  for (const describe of ["second", "backend"]) {
    const one = stubbedChannel(describe, async (_command, source) => {
      sources.push(source);
      return { ok: true, result: {} };
    });
    await one.settle();
    await settle();
    opened
      .at(-1)
      // A deadline, only so the losing half of `handle`'s race is not a
      // twenty-second timer this process then waits out.
      .deliver({
        command_id: `cmd_${describe}`,
        run_id: "run_r1",
        kind: "ui.url",
        deadline_ms: 50,
        payload: {},
      });
    await settle();
    one.close();
  }
  assert.deepEqual(sources, ["second", "backend"]);
});

test("a command naming its own source wins over the channel it arrived on", async () => {
  // The one socket carries both a rig run's commands and a skill run's, so
  // `describe` -- this channel's own fixed name -- cannot tell them apart.
  // Only the backend, sending the command, knows which engine it is; a
  // command with no `source` of its own (an older backend) still falls back
  // to `describe`, which is the case above.
  const sources = [];
  const one = stubbedChannel("backend", async (_command, source) => {
    sources.push(source);
    return { ok: true, result: {} };
  });
  await one.settle();
  await settle();
  opened
    .at(-1)
    .deliver({
      command_id: "cmd_rig",
      run_id: "run_r1",
      kind: "ui.url",
      source: "rig",
      deadline_ms: 50,
      payload: {},
    });
  await settle();
  one.close();
  assert.deepEqual(sources, ["rig"]);
});

test("busy goes down the channel the gesture is told to, and no other", async () => {
  // Two channels exist again the moment anything is added beside the backend's,
  // and `operatorIsWorking` is per channel: a browser that told the wrong
  // socket somebody is typing is one that queues a command against the wrong
  // run, or lands one mid-keystroke on the right one.
  channel.close();
  await channel.settle();
  const other = stubbedChannel("second", async () => ({ ok: true, result: {} }));
  await other.settle();
  await settle();
  const otherSocket = opened.at(-1);
  const backendSocket = opened.findLast((s) => s.url.startsWith("ws://backend:8000"));
  assert.ok(backendSocket, "the backend was not dialled");
  assert.ok(otherSocket.url.startsWith("ws://second.test"));

  const busy = (socket) => socket.sent.filter((m) => m.kind === "busy");
  channel.operatorIsWorking();
  assert.equal(busy(backendSocket).length, 1, "the backend was not told");
  assert.equal(busy(otherSocket).length, 0, "the backend's gesture went down the other socket");

  other.operatorIsWorking();
  assert.equal(busy(otherSocket).length, 1, "the other channel was not told");
  assert.equal(busy(backendSocket).length, 1, "the other channel's gesture went down the backend's");
  other.close();
});

test("a dial that names nowhere opens no socket, and no error", async () => {
  // `dial` answering null is how a channel says it has nothing to dial at --
  // no credential yet, no device id yet. Silence, not a throw and not a
  // retry storm: the absence of somewhere to dial is not a fault.
  const nowhere = stubbedChannel("nowhere", async () => ({ ok: true, result: {} }), async () => null);
  const before = opened.length;
  await nowhere.settle();
  await settle();
  assert.equal(opened.length, before, "something was dialled");
  assert.equal(nowhere.status(), "closed");
  nowhere.close();
});

test("a channel that will not dial says which of the four reasons it is", async () => {
  // All four states closed this socket identically -- "the command channel is
  // closed" -- so a browser an administrator had switched off looked exactly
  // like one whose secret had gone, both in the panel and in a bug report.
  await channel.settle();
  await settle();
  assert.equal(channel.why(), "", "a channel with a target to dial blamed something");

  const secret = stored.get("sro.deviceSecret");
  stored.delete("sro.deviceSecret");
  channel.close();
  await channel.settle();
  await settle();
  assert.match(channel.why(), /device secret/, "a missing secret was not named");

  stored.delete("sro.token");
  channel.close();
  await channel.settle();
  await settle();
  // Reported in the order somebody would fix them: no credential outranks
  // everything downstream of holding one.
  assert.match(channel.why(), /no credential/, "the missing credential was not named first");

  stored.set("sro.token", "backend-token");
  stored.set("sro.deviceSecret", secret);
  channel.close();
  await channel.settle();
  await settle();
  assert.equal(channel.why(), "", "the reason outlived what caused it");
});
