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
// The panel is an ES module and `vm.runInContext` evaluates a script, so the
// import is lifted out and the one symbol it names is put in the sandbox
// instead. Imported in the real file rather than restated there: `hostMatches`
// is the single definition of the host rule, and a second copy in the panel is
// how it would come to disagree with the worker about whether a page is being
// recorded.
//
// `export` is stripped the same way, for the same reason: a script is not a
// module and `vm.runInContext` throws `Unexpected token 'export'` on the
// first one. The function it was guarding is not lost -- a top-level
// declaration in a script is a property of the sandbox's global either way,
// which is already how this harness reaches `render` and `here`.
const SOURCE = readFileSync(path.join(here, "panel.js"), "utf-8")
  .replace(/^import .*?;$/m, "")
  .replace(/^export /gm, "");
const { hostMatches } = await import("../background/scripts.js");

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
function panel(status, here = null, replies = {}) {
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
          if (message.kind === "status") return { deviceId: "" };
          // A list where the panel expects a list. With a current tab set, it
          // goes on to ask what is offerable here, and `{}` reaching
          // `.filter` throws after the assertions have already passed --
          // which is a green test run and a red exit code.
          return Array.isArray(replies[message.kind]) ? replies[message.kind] : [];
        },
        openOptionsPage: () => {},
      },
      // The tab the panel is docked beside. Every card about "this tab" is
      // chosen by matching it against the watch list, so a panel with no tab
      // draws the not-watching card whatever else the status says -- which is
      // how two tests here passed while asserting on cards that were never
      // drawn.
      tabs: {
        query: async () => (here ? [here] : []),
        reload: async () => {},
      },
    },
  };
  sandbox.hostMatches = hostMatches;
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(SOURCE, sandbox);
  // Which tab the panel is docked beside. The real one learns this from an
  // async `chrome.tabs.query` that `render` does not wait for, and every card
  // about "this tab" is chosen by matching it against the watch list -- so a
  // harness that leaves it unset draws the not-watching card whatever the
  // status says, which is how two tests here once passed while asserting on
  // cards that were never drawn. Assigned into the same context rather than
  // through the sandbox object because `let` at a script's top level is a
  // lexical binding, not a property of the global.
  if (here) {
    vm.runInContext(
      `tabHere = ${JSON.stringify({ tabId: here.id, host: here.host, url: here.url })}`,
      sandbox,
    );
  }
  sandbox.render(status);
  const cards = ids["cards"].kids;
  // `render` only ever draws the synchronous "cards" column. The list of
  // tasks noticed on this host is a second, async fetch (`here()`, over
  // `ask({kind: "candidates"})`) that a real load triggers separately from
  // `whereWeAre` -- so nothing above has populated `ids["candidates"]` yet,
  // and a test of that list has to trigger and await this itself.
  return { sent, cards, ids, renderCandidates: sandbox.here, plainly: sandbox.plainly };
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

test("a tab that stopped recording calls says so instead of looking healthy", async () => {
  // The worst shape a failure takes here. The page-realm patch outlives the
  // extension that installed it, so what the operator does is recorded and what
  // they ask the system for is not -- and nothing says so: the panel reads
  // "watching this tab, since 65m", uploads keep arriving, and it only shows up
  // days later as a skill that checks nothing, by which time the demonstrations
  // are gone. An operator lost two to exactly that.
  const { cards } = panel(
    {
      deviceId: "dev-1",
      capturing: true,
      watched: [{ tabId: 7, host: "wms.example", since: new Date().toISOString() }],
      deaf: [7],
    },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
  );

  const said = cards.map(words).join(" ");
  assert.ok(
    /only recording half/i.test(said),
    `a half-deaf tab was not called out: ${said.slice(0, 200)}`,
  );
  // And the fix is offered, because reloading the page is the whole of it and
  // the sentence explaining why is on this card.
  assert.ok(/Reload this page/i.test(said), "no way to fix it was offered");
  // Teaching is not, because a demonstration recorded this way is worse than
  // none: it looks like a success and induces to a skill that asserts nothing.
  assert.ok(!/Start teaching/i.test(said), "teaching was still offered on a half-deaf tab");
});

test("an ordinary watched tab is not accused of being half deaf", async () => {
  const { cards } = panel(
    {
      deviceId: "dev-1",
      capturing: true,
      watched: [{ tabId: 7, host: "wms.example", since: new Date().toISOString() }],
      deaf: [],
    },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
  );

  const said = cards.map(words).join(" ");
  assert.ok(/Watching this tab/i.test(said));
  assert.ok(!/only recording half/i.test(said));
});

test("the offer is about their work, not about our system", async () => {
  // What it said before: "Create workOperations on bf56-kms-wms-web-np2
  // .jdadelivers.com / Seen 3 times / [Teach it] [Not worth it]". The title is
  // an API endpoint, the count is telemetry about the person reading it, and
  // both buttons ask them to work for us or to judge us. Nobody presses that.
  const { ids, renderCandidates } = panel(
    {
      deviceId: "dev-1",
      capturing: true,
      watched: [{ tabId: 7, host: "wms.example", since: new Date().toISOString() }],
    },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
    {
      candidates: [
        {
          id: "cnd-1",
          title: "Create workOperations on wms.example",
          signature: "POST data/WM/wm/workOperations",
          status: "new",
          times_seen: 3,
          median_duration_ms: 40000,
          minutes_so_far: 5,
          episodes: [],
          joins: [],
        },
      ],
    },
  );
  // The one card `render` never draws on its own: this is the same fetch a
  // real load makes from `whereWeAre`, awaited here instead of raced.
  await renderCandidates();

  const said = words(ids["candidates"]);
  assert.ok(/work operations/i.test(said), `no plain noun in: ${said.slice(0, 200)}`);
  assert.ok(/do the next one/i.test(said), "it never offers to do anything");
  assert.ok(!/teach/i.test(said), "the panel still asks to be taught");
  assert.ok(!/workOperations/.test(said), "an endpoint name reached the operator");
  assert.ok(!/seen 3 times/i.test(said), "telemetry about the operator is still shown");
});

test("a model's title is said as its own sentence, not spliced into the count's", async () => {
  // Round 1 regression: the count template ("You've created 3 ___ here") was
  // reused for a model's title too, which is a full sentence rather than a
  // noun -- "You've created 3 Adjust an LPN after a short ship here — about
  // 40s each." A model writes a title; only a noun goes in that slot.
  const { plainly } = panel({ deviceId: "dev-1" });
  const said = plainly({
    id: "cnd-2",
    title: "Adjust an LPN after a short ship",
    signature: "POST data/WM/wm/lpnAdjustments",
    named_by_model: true,
    status: "new",
    times_seen: 3,
    median_duration_ms: 40000,
    minutes_so_far: 5,
  });
  assert.ok(
    said.startsWith("Adjust an LPN after a short ship"),
    `the title was not said as a title: ${said}`,
  );
  assert.ok(!/created 3 Adjust/i.test(said), `the title was spliced into the noun's slot: ${said}`);
  assert.match(said, /you've done this 3 times, about 40s each/i);
  assert.match(said, /next one/i, "the offer's own meaning -- doing the next one -- was dropped");
});

test("a wildcarded id in the path is not offered as the noun, and nothing left is not either", async () => {
  // A real, plausible shape the count-noun path didn't cover: an update-by-id
  // endpoint like `PUT .../workOperations/*` popped the id's own `*` as the
  // noun -- "You've created 3 *s here."
  const { plainly } = panel({ deviceId: "dev-1" });
  const withId = plainly({
    signature: "PUT data/WM/wm/workOperations/*",
    status: "new",
    times_seen: 4,
    median_duration_ms: 20000,
  });
  assert.ok(/work operations/i.test(withId), `no plain noun in: ${withId}`);
  assert.ok(!/\*/.test(withId), `a wildcard reached the operator: ${withId}`);

  // And where no real word survives the path at all, a vaguer sentence beats
  // a visibly broken one -- never a bare placeholder standing in for a noun.
  const noNoun = plainly({ signature: "", status: "new", times_seen: 4, median_duration_ms: 20000 });
  assert.ok(!/\*/.test(noNoun), `a wildcard reached the operator: ${noNoun}`);
  assert.match(noNoun, /you've done this 4 times/i);
});

for (const [name, fn] of tests) {
  try {
    await fn();
  } catch (error) {
    throw new Error(`${name}: ${error.message}`, { cause: error });
  }
}
console.log("panel.test.mjs: ok");
