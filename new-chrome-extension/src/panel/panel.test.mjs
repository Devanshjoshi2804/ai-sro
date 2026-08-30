// Self-check for the offer card, which is the whole of what an operator sees
// of a watch.
//
// Everything else the panel draws is a sentence about this browser. This card
// is a decision: a mail matched, these are the values it would run with, and
// pressing starts a run in somebody's warehouse. So the things worth holding
// are what it says before the press -- which values came out of the mail and
// which were already on the task, what recognised it, and what is missing --
// and that pressing sends the press and nothing else.
//
// The real panel.js runs here in a vm against a fake document, the way
// `watch.test.mjs` runs the real watch.js: what is under test is the card, not
// the DOM. Run with `node src/panel/panel.test.mjs`.

import assert from "node:assert";
import vm from "node:vm";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const SOURCE = readFileSync(path.join(here, "panel.js"), "utf-8");

const OFFER = {
  id: "off-1",
  at: Date.now(),
  triggerId: "trg-short-ship",
  skillId: "skl-short-ship",
  skill: "Resolve a short ship",
  host: "mail.acme.test",
  terms: [
    { field: "sender", contains: "dispatch@supplier.test" },
    { field: "subject", contains: "Short ship" },
  ],
  read: { shipment_id: "SH-4471" },
  values: { shipment_id: "SH-4471", facility: "BLR1" },
  missing: [],
};

/** Just enough document to build cards in, and to read them back out of. */
function node(tag) {
  return {
    tag,
    className: "",
    dataset: {},
    hidden: false,
    disabled: false,
    textContent: "",
    kids: [],
    listeners: [],
    get childElementCount() {
      return this.kids.length;
    },
    append(...added) {
      this.kids.push(...added);
    },
    replaceChildren(...added) {
      this.kids = added;
    },
    addEventListener(_kind, fn) {
      this.listeners.push(fn);
    },
  };
}

function words(el) {
  return [el.textContent, ...el.kids.map(words)].join(" ").replace(/\s+/g, " ").trim();
}

function buttons(el) {
  return [...(el.tag === "button" ? [el] : []), ...el.kids.flatMap(buttons)];
}

/** Every message of one kind the panel sent, copied out of the vm's realm:
 * an object made in there has a different `Object.prototype`, which
 * `deepStrictEqual` calls a difference. This is also exactly what
 * `chrome.runtime.sendMessage` serialises. */
function sentOf(sent, kind) {
  return JSON.parse(JSON.stringify(sent.filter((message) => message.kind === kind)));
}

/** The panel, drawn once from one status. `sent` is every message it sent the
 * worker, which is the only thing it can do to the world. */
function panel(status) {
  const sent = [];
  const ids = {};
  const sandbox = {
    document: {
      getElementById: (id) => (ids[id] ??= node("div")),
      createElement: (tag) => node(tag),
    },
    setInterval: () => 0,
    setTimeout: () => 0,
    URL: URL,
    chrome: {
      runtime: {
        id: "test",
        sendMessage: async (message) => {
          sent.push(message);
          // The status the panel reads for itself on its own two-second poll.
          // Deliberately nothing: every card under test is drawn by the
          // explicit `render` below, so a poll that raced it would be the
          // thing being asserted on.
          return message.kind === "status" ? { deviceId: "" } : {};
        },
        openOptionsPage: () => {},
      },
      tabs: { query: async () => [] },
    },
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(SOURCE, sandbox);
  sandbox.render(status);
  const cards = ids["cards"].kids;
  return { sent, cards, ids };
}

const tests = [];
const test = (name, fn) => tests.push([name, fn]);

test("the ordinary resting state does not wear the colour trouble wears", async () => {
  // Not watching is what this panel looks like on a quiet Tuesday. It carried
  // `data-tone="attention"` -- the same amber as "not observing", "this browser
  // cannot be reached" and "last error" -- so a real fault looked exactly like
  // the normal case, and the alarm meant nothing.
  const { cards } = panel({ deviceId: "dev-1", capturing: true });

  const idle = cards.find((c) => words(c).includes("Not watching this tab"));
  assert.ok(idle, "the offer to watch this tab was not drawn at all");
  assert.strictEqual(idle.dataset.tone, undefined, "the resting state is not an alarm");
});

test("something actually wrong still wears it", async () => {
  // The other half: quieting the ordinary case is only worth anything if the
  // faults are still loud.
  const { cards } = panel({ deviceId: "dev-1", lastError: "the upload was refused" });

  const wrong = cards.find((c) => words(c).includes("Last error"));
  assert.ok(wrong, "an error this browser hit was not shown");
  assert.strictEqual(wrong.dataset.tone, "attention");
});

test("a mail that matched is a card naming the task and what it read", async () => {
  const { cards } = panel({ deviceId: "dev-1", offers: [OFFER] });

  const said = words(cards.find((c) => words(c).includes("Resolve a short ship")));
  assert.match(said, /A mail matched “Resolve a short ship”/);
  // What it read, and where each value came from: one of these is what
  // somebody just wrote to this operator, the other is what they set up.
  assert.match(said, /shipment_id: SH-4471 — read from the mail/);
  assert.match(said, /facility: BLR1 — already on the task/);
  // Which of their own terms caught it. Never the subject or the sender
  // themselves -- those were compared in the frame and forgotten there.
  assert.match(said, /sender contains “dispatch@supplier\.test”/);
  assert.match(said, /subject contains “Short ship”/);
});

test("a match that is short of a required value says so, and cannot be run", async () => {
  const { cards, sent } = panel({
    deviceId: "dev-1",
    offers: [{ ...OFFER, read: {}, values: {}, missing: ["shipment_id"] }],
  });

  const card = cards.find((c) => words(c).includes("A mail matched"));
  assert.match(words(card), /Nothing said shipment_id, so this one cannot run/);
  const [run] = buttons(card);
  assert.strictEqual(run.textContent, "Run it");
  assert.strictEqual(run.disabled, true, "a run that would be skipped was offered anyway");
  assert.deepStrictEqual(sentOf(sent, "watch-fire"), []);
});

test("the press sends the press and nothing else", async () => {
  const { cards, sent } = panel({ deviceId: "dev-1", offers: [OFFER] });
  const card = cards.find((c) => words(c).includes("A mail matched"));
  const [run] = buttons(card);

  run.listeners[0]();
  await Promise.resolve();

  assert.deepStrictEqual(
    sentOf(sent, "watch-fire"),
    // The offer's id and nothing else: the values are the worker's copy of
    // what it read, and a panel that resent them would be a second place they
    // could be edited on the way to a run.
    [{ kind: "watch-fire", offerId: "off-1" }],
  );
});

test("an offer nobody wants is dismissed rather than left to rot", async () => {
  const { cards, sent } = panel({ deviceId: "dev-1", offers: [OFFER] });
  const card = cards.find((c) => words(c).includes("A mail matched"));
  const [, notNow] = buttons(card);

  assert.strictEqual(notNow.textContent, "Not now");
  notNow.listeners[0]();
  await Promise.resolve();

  assert.deepStrictEqual(
    sentOf(sent, "drop-offer"),
    [{ kind: "drop-offer", offerId: "off-1" }],
  );
});

test("a demonstration in progress is the only thing the panel is about", async () => {
  // The panel's own rule, and an offer does not get to break it: what is being
  // recorded is what the operator is doing right now, and the offer keeps.
  const { cards } = panel({
    deviceId: "dev-1",
    teaching: { startedAt: new Date().toISOString() },
    offers: [OFFER],
  });

  assert.ok(!cards.some((c) => words(c).includes("A mail matched")), words(cards[0]));
});

for (const [name, fn] of tests) {
  try {
    await fn();
  } catch (error) {
    throw new Error(`${name}: ${error.message}`, { cause: error });
  }
}
console.log("panel.test.mjs: ok");
