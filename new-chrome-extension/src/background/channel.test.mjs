// One socket, dialled twice: at the backend and at the rig.
//
// The point of the factory is that there is only one implementation of the
// keepalive, the exactly-once answering and the backoff, so these checks are
// about the two things that actually differ -- where a channel dials and what
// it offers -- plus the shared behaviour, exercised once.
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
  ["sro.rigUrl", "http://rig:8100"],
  ["sro.rigToken", "rig-token"],
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
const rig = await import("./rig-channel.js");

const settle = () => new Promise((r) => setTimeout(r, 0));

// An open channel holds a 20-second keepalive interval, which would keep node
// running long after the last check.
after(() => {
  channel.close();
  rig.close();
});

/** A channel shaped like the rig's, but answering with a stub. */
function stubbedChannel(describe, perform) {
  return channel.createChannel({
    describe,
    perform,
    dial: async () => ({
      url: `ws://${describe}.test/v1/agents/dev_1/commands`,
      protocols: ["bearer", "tok"],
    }),
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

test("the rig channel dials the rig with the rig token and no secret", async () => {
  await rig.settle();
  await settle();
  const socket = opened.find((s) => s.url.startsWith("ws://rig:8100"));
  assert.ok(socket, "dialled the rig");
  assert.equal(socket.url, "ws://rig:8100/v1/agents/dev_1/commands");
  assert.deepEqual(socket.protocols, ["bearer", "rig-token"]);
});

test("a command is answered exactly once, on the socket it came in on", async () => {
  const one = stubbedChannel("rig", async (command) => ({
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
  for (const describe of ["rig", "backend"]) {
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
  assert.deepEqual(sources, ["rig", "backend"]);
});

test("a re-pointed rig is dialled at its new url, and the old socket is dropped", async () => {
  // `settle()` alone would not do it: an open socket makes it a no-op, so
  // without the `close()` service-worker.js's "rig" case does first, a browser
  // pointed at a second rig would go on taking commands from the first.
  rig.close();
  await rig.settle();
  await settle();
  const before = opened.at(-1);
  assert.equal(before.url, "ws://rig:8100/v1/agents/dev_1/commands");

  stored.set("sro.rigUrl", "http://rig-two:8100");
  rig.close();
  await rig.settle();
  await settle();

  const after = opened.at(-1);
  assert.notEqual(after, before, "nothing was re-dialled");
  assert.equal(after.url, "ws://rig-two:8100/v1/agents/dev_1/commands");
  assert.equal(before.readyState, 3, "the socket authenticated at the old rig is still open");
  stored.set("sro.rigUrl", "http://rig:8100");
});

test("busy goes down the channel the gesture is told to, and no other", async () => {
  rig.close();
  channel.close();
  await channel.settle();
  await rig.settle();
  await settle();
  const backendSocket = opened.at(-2);
  const rigSocket = opened.at(-1);
  assert.ok(backendSocket.url.startsWith("ws://backend:8000"));
  assert.ok(rigSocket.url.startsWith("ws://rig:8100"));

  const busy = (socket) => socket.sent.filter((m) => m.kind === "busy");
  channel.operatorIsWorking();
  assert.equal(busy(backendSocket).length, 1, "the backend was not told");
  assert.equal(busy(rigSocket).length, 0, "the backend's gesture went down the rig's socket");

  rig.operatorIsWorking();
  assert.equal(busy(rigSocket).length, 1, "the rig was not told");
  assert.equal(busy(backendSocket).length, 1, "the rig's gesture went down the backend's socket");
});

test("no rig url means no rig socket, and no error", async () => {
  stored.set("sro.rigUrl", "");
  rig.close();
  const before = opened.length;
  await rig.settle();
  await settle();
  assert.equal(opened.length, before, "nothing dialled");
  assert.equal(rig.status(), "closed");
});
