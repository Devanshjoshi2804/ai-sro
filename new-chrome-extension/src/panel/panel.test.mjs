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
//
// `ledger.js` is concatenated ahead of it rather than imported into the
// sandbox the way `hostMatches` is: it builds DOM, so it has to see the fake
// `document` this harness makes, and a function imported into the sandbox from
// this realm would close over node's own (absent) one instead. As a script,
// its top-level declarations are properties of the sandbox's global, which is
// exactly how `panel.js` reaches it.
//
// The strip is global (`gm`, not `m`): with two import lines a first-only
// replace leaves the second, and `vm.runInContext` throws on it.
const SOURCE = [
  readFileSync(path.join(here, "ledger.js"), "utf-8"),
  readFileSync(path.join(here, "strip.js"), "utf-8"),
  readFileSync(path.join(here, "today.js"), "utf-8"),
  readFileSync(path.join(here, "run-card.js"), "utf-8"),
  readFileSync(path.join(here, "panel.js"), "utf-8"),
]
  .join("\n")
  .replace(/^import .*?;$/gm, "")
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
    prepend(...added) {
      this.kids.unshift(...added);
    },
    replaceChildren(...added) {
      this.kids = added;
    },
    addEventListener(_kind, fn) {
      this.listeners.push(fn);
    },
    setAttribute(name, value) {
      this[name] = value;
    },
  };
}

function words(el) {
  return [el.textContent, ...el.kids.map(words)].join(" ").replace(/\s+/g, " ").trim();
}

function buttons(el) {
  return [...(el.tag === "button" ? [el] : []), ...el.kids.flatMap(buttons)];
}

function inputs(el) {
  return [...(el.tag === "input" ? [el] : []), ...el.kids.flatMap(inputs)];
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
  // Every tab the panel opened. The panel's other way of acting on the world:
  // `sent` is what it told the worker, this is what it put in front of the
  // operator -- and which URL that is, is the whole of what a "details" link
  // gets right or wrong.
  const opened = [];
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
          // A reply the fixture actually named, object or list alike --
          // `resolve-intent`, `teach-candidate` and `skill` all answer with an
          // object, and a guard that only ever returned an object for
          // `status` made every fixture for those three silently discarded.
          // Where nothing was named, `[]`: a list where the panel expects a
          // list, because with a current tab set it goes on to ask what is
          // offerable here, and `{}` reaching `.filter` throws after the
          // assertions have already passed -- which is a green test run and a
          // red exit code.
          return message.kind in replies ? replies[message.kind] : [];
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
        create: async ({ url }) => opened.push(url),
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
  // Both bands. The state of this tab moved into the one the strip's chevron
  // opens; everything else -- a run, what it made, what is wrong -- is where it
  // was. What each test is asking is "was this card built", which is the same
  // question either side of that move.
  const cards = [...(ids["expanded"]?.kids || []), ...ids["cards"].kids];
  // `render` only ever draws the synchronous "cards" column. The list of
  // tasks noticed on this host is a second, async fetch (`here()`, over
  // `ask({kind: "candidates"})`) that a real load triggers separately from
  // `whereWeAre` -- so nothing above has populated `ids["candidates"]` yet,
  // and a test of that list has to trigger and await this itself.
  return {
    sent,
    opened,
    cards,
    ids,
    renderCandidates: sandbox.here,
    // Exposed so a test can simulate the panel's own two-second poll --
    // `refresh()` calling `render(status)` again with nothing changed --
    // separately from whatever else a click already triggered.
    render: sandbox.render,
    plainly: sandbox.plainly,
    previewOf: sandbox.previewOf,
    // The nudge and offer press path, as the ledger calls it. Reached here
    // rather than through a rendered card because the thread is drawn from a
    // separate fetch: what is under test is which message a press sends, and
    // that is this function whatever drew the button.
    answered: sandbox.answered,
    // The conversation. `say` is what the composer calls, and `focus` is what
    // a real browser does on its own when somebody types into the box and
    // presses Enter -- the cursor is still in there when the answer lands.
    say: sandbox.say,
    focus: (el) => {
      sandbox.document.activeElement = el;
    },
    // The ledger's LOCAL half: the offers this browser made, which live in no
    // thread. Set and redrawn the way a poll does it -- `refresh()` stores the
    // status, `conversation()` calls `show` with whatever thread it fetched.
    offerLocally: (nudges, thread) => {
      vm.runInContext(`lastStatus = ${JSON.stringify({ nudges })}`, sandbox);
      sandbox.show(thread);
    },
    // The same half, for whatever else lives in it. `offerLocally` names the
    // one field it sets; this draws the thread from the whole local status,
    // which is how a press in the ledger is actually reached -- the handler
    // the ledger gets is chosen inside `show`, and calling the exported
    // `answered` directly cannot tell whether it did.
    locally: (status, thread) => {
      vm.runInContext(`lastStatus = ${JSON.stringify(status)}`, sandbox);
      sandbox.show(thread);
    },
  };
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

test("a steady watching state is one line", async () => {
  // Nothing about an ordinary watched tab is asking to be answered, so the
  // card that used to take a third of the panel -- title, sentence, metrics,
  // three buttons -- is not on screen at all. Its actions are not gone (see
  // the chip test below), only not shouted before anybody asked for them.
  //
  // Held at the band rather than in the card: the strip decides what is open,
  // and a card that also decided would be a second answer to one question.
  const { ids } = panel(
    {
      deviceId: "dev-1",
      capturing: true,
      watched: [{ tabId: 7, host: "wms.example", since: new Date(Date.now() - 53 * 60_000).toISOString() }],
    },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
  );

  const chip = ids["strip"].kids
    .flatMap((kid) => [kid, ...kid.kids])
    .find((kid) => kid.className === "chip");
  assert.ok(words(chip).includes("wms.example"), "the steady watching state named no tab");
  assert.equal(
    ids["expanded"].hidden,
    true,
    "a steady watching state showed its actions before being asked to",
  );
});

test("the collapsed row has a chevron, and pressing it reveals the actions", async () => {
  const { ids } = panel(
    {
      deviceId: "dev-1",
      capturing: true,
      watched: [{ tabId: 7, host: "wms.example", since: new Date(Date.now() - 53 * 60_000).toISOString() }],
    },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
  );

  // The chip in the strip, which is where the collapsed row went: one line
  // naming the tab and what is happening to it, and pressing it opens the card.
  const chip = ids["strip"].kids
    .flatMap((kid) => [kid, ...kid.kids])
    .find((kid) => kid.className === "chip");
  assert.ok(chip, "the strip drew no chip for the tab this panel is beside");
  assert.ok(words(chip).includes("wms.example"), "the chip did not name the tab");
  assert.equal(ids["expanded"].hidden, true, "a steady tab opened its card unasked");

  chip.listeners[0]();

  const opened = ids["expanded"].kids.find((c) => words(c).includes("Watching this tab"));
  assert.ok(opened, "pressing the chip did not redraw the watching card at all");
  assert.ok(
    buttons(opened).some((b) => b.textContent === "Start teaching"),
    "pressing the chip did not reveal the actions",
  );
});

test("a manual expansion survives a redraw", async () => {
  // The panel polls `status` every couple of seconds and redraws from it --
  // `refresh()` calling `render(status)` again with nothing about the state
  // having changed. An expansion the operator just pressed for must still be
  // there on the far side of that, or pressing "Start teaching" a moment
  // later is a race against the panel's own clock.
  const status = {
    deviceId: "dev-1",
    capturing: true,
    watched: [{ tabId: 7, host: "wms.example", since: new Date(Date.now() - 53 * 60_000).toISOString() }],
  };
  const { ids, render } = panel(status, { id: 7, host: "wms.example", url: "https://wms.example/portal" });

  const chip = ids["strip"].kids
    .flatMap((kid) => [kid, ...kid.kids])
    .find((kid) => kid.className === "chip");
  chip.listeners[0]();

  render(status); // the poll's own redraw, simulated

  assert.equal(ids["expanded"].hidden, false, "the next redraw closed what the operator opened");
  const opened = ids["expanded"].kids.find((c) => words(c).includes("Watching this tab"));
  assert.ok(opened, "the next redraw drew no card in the band it had just opened");
  assert.ok(
    buttons(opened).some((b) => b.textContent === "Start teaching"),
    "the redraw kept the card open but lost its actions",
  );
});

test("a state with something to press expands itself", async () => {
  // A host the tenant excludes by default, actively being watched, is the one
  // place somebody agreed to their own mailbox being recorded -- that stays
  // the full card, buttons included, every time it is drawn.
  const { cards } = panel(
    {
      deviceId: "dev-1",
      capturing: true,
      policy: { exclude_hosts: ["wms.example"] },
      watched: [{ tabId: 7, host: "wms.example", since: new Date().toISOString() }],
    },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
  );

  const card = cards.find((c) => words(c).includes("normally excluded"));
  assert.ok(card, "a watched-but-excluded host was not called out");
  assert.ok(buttons(card).length > 0, "a state that still needs an answer offered nothing to press");
});

test("a card that cannot close has no chevron on it", async () => {
  // A control that visibly does nothing. `needsAnswer` forces the card open
  // whatever `watchOpen` says, so a chevron there is one an operator presses
  // and watches nothing happen to.
  const { cards } = panel(
    {
      deviceId: "dev-1",
      capturing: true,
      policy: { exclude_hosts: ["wms.example"] },
      watched: [{ tabId: 7, host: "wms.example", since: new Date().toISOString() }],
    },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
  );

  const card = cards.find((c) => words(c).includes("normally excluded"));
  assert.ok(
    !buttons(card).some((button) => button.className === "chevron"),
    "a card that is always open still drew the control for closing it",
  );
});

test("the collapsed row still says whether this tab is evidence", async () => {
  // The words matter: an operator who cannot tell whether they are being
  // recorded is the failure this panel guards against, collapsed or not.
  const { cards } = panel(
    {
      deviceId: "dev-1",
      capturing: true,
      watched: [{ tabId: 7, host: "wms.example", since: new Date().toISOString() }],
    },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
  );

  const said = cards.map(words).join(" ");
  assert.match(said, /Watching this tab/i);
  assert.match(said, /wms\.example/);
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

test("both offer shapes read correctly at a count of one, not '1 times'", async () => {
  // Round 2 review: unchanged, pre-existing wording, but reachable in
  // practice -- the panel offers everything `status === "new"` regardless of
  // `times_seen`, and a fresh candidate really does sit at 1.
  const { plainly } = panel({ deviceId: "dev-1" });

  const titled = plainly({
    title: "Adjust an LPN after a short ship",
    signature: "POST data/WM/wm/lpnAdjustments",
    named_by_model: true,
    times_seen: 1,
    median_duration_ms: 40000,
  });
  assert.match(titled, /you've done this once/i, `"1 times" survived: ${titled}`);
  assert.ok(!/\b1 times\b/.test(titled), `"1 times" survived: ${titled}`);

  const counted = plainly({
    signature: "POST data/WM/wm/workOperations",
    times_seen: 1,
    median_duration_ms: 40000,
  });
  assert.match(counted, /created one work operation here/i, `noun stayed plural: ${counted}`);
  assert.ok(!/\bwork operations\b/i.test(counted), `noun stayed plural: ${counted}`);
});

test("the preview shrinks as the version earns it", async () => {
  // Requiring approval for every action an agent takes defeats the point of
  // automating it. The rungs already say when a version has earned the
  // benefit of the doubt; until now nothing read them for this.
  //
  // `panel()` rather than `await import("./panel.js")`: the module's own
  // bottom lines wire real listeners against a real `document` the moment it
  // loads, and a plain Node import hits those with no `document` to find --
  // the same reason every other export here is read off the vm sandbox
  // `panel()` already built instead of a second, incompatible way to load
  // the same file.
  const { previewOf } = panel({ deviceId: "dev-1" });
  const steps = [
    { intent: "Type the Operation code.", value: "NDPCK" },
    { intent: "Press Save.", value: null },
  ];

  const first = previewOf({ stage: "recorded", clean_streak: 0 }, steps);
  assert.equal(first.show, "every-step", "a first press hid what it would do");

  const trusted = previewOf({ stage: "assisted", clean_streak: 4 }, steps);
  assert.equal(trusted.show, "one-line", "a version with a streak still asked in full");

  const earned = previewOf({ stage: "autonomous", clean_streak: 10 }, steps);
  assert.equal(earned.show, "nothing", "an autonomous version still asked first");
});

test("what it could not work out, it asks for by the screen's own name", async () => {
  const { previewOf } = panel({ deviceId: "dev-1" });

  const asked = previewOf({ stage: "recorded", clean_streak: 0 }, [
    { intent: "Type the Operation code.", value: "NDPCK" },
    { intent: "Enter the Voice Code.", value: null, missing: "voice_code", label: "Voice Code" },
  ]);

  assert.deepEqual(asked.missing, ["Voice Code"]);
});

/** A candidate `here()` can offer, minus whatever one test cares about
 * itself -- so a change to a field none of these tests read does not become
 * a change to every fixture that builds one. */
function offerableCandidate(overrides = {}) {
  return {
    id: "cnd-1",
    signature: "POST data/WM/wm/workOperations",
    status: "new",
    times_seen: 3,
    median_duration_ms: 40000,
    minutes_so_far: 5,
    episodes: [],
    joins: [],
    ...overrides,
  };
}

/** Drives a candidate row all the way to "Do the next one" being pressed and
 * the box it always opens with waiting for a sentence -- teaching succeeds,
 * which is the same for both tests below; what happens once a sentence is
 * typed into that box and asked is what each of them is actually about.
 * `replies` is folded in under the fixtures this needs to get there, so a
 * test only has to name the reply it cares about. */
async function openedOffer(replies) {
  const { sent, ids, renderCandidates } = panel(
    {
      deviceId: "dev-1",
      capturing: true,
      watched: [{ tabId: 7, host: "wms.example", since: new Date().toISOString() }],
    },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
    {
      candidates: [offerableCandidate()],
      "teach-candidate": { skill_id: "skl-offered", needs_demonstration: false },
      ...replies,
    },
  );
  await renderCandidates();
  const row = ids["candidates"].kids[0];
  const [doNext] = buttons(row);
  await doNext.listeners[0]();
  return { sent, row };
}

test("the box a candidate's offer opens still runs a sentence naming a different task", async () => {
  // Spec §6: a sentence that names no offered task still resolves, across the
  // whole library, and the offer is a pre-filled message into the same box --
  // not a restriction on what that box can be asked. `resolve-intent` carries
  // no field to pin it to the offered skill in the first place, which is
  // most of the proof: there is nothing here to restrict it with. The rest is
  // that a sentence naming a wholly different, unoffered skill still runs
  // that skill rather than the one the row was about.
  const { sent, row } = await openedOffer({
    "resolve-intent": {
      matched: { skill_id: "skl-9", name: "Create a work area", version: 1, stage: "autonomous" },
      confident: true,
      choices: [],
      missing_parameters: [],
    },
    skill: {
      id: "skl-9",
      name: "Create a work area",
      versions: [
        { version: 1, stage: "autonomous", track_record: { clean_streak: 12 }, steps: [], parameters: [] },
      ],
    },
  });

  const [ask] = buttons(row).filter((button) => button.textContent === "Ask");
  const [utterance] = inputs(row);
  utterance.value = "make a work area for receiving";
  await ask.listeners[0]();

  const asked = sent.filter((message) => message.kind === "resolve-intent");
  assert.equal(asked.length, 1);
  assert.ok(!("skillId" in asked[0]), "the box only ever asks about the offered skill");

  // Autonomous, with a streak: `previewOf` says nothing to show, and the
  // press happens on its own -- for the task the sentence named, "skl-9",
  // never "skl-offered", the one the row was about.
  const ran = sent.filter((message) => message.kind === "run-skill");
  assert.equal(ran.length, 1);
  assert.equal(ran[0].skillId, "skl-9");
});

test("a sentence it is unsure about is not resolved by picking the top match", async () => {
  // `ResolveIntent` already refuses rather than guess between two close
  // skills. What must not happen on this side is the panel taking the first
  // of several and running it -- a warehouse write on a coin toss.
  const { sent, row } = await openedOffer({
    "resolve-intent": {
      matched: null,
      choices: [
        { skill_id: "skl-1", name: "Create a work area", version: 1, stage: "assisted" },
        { skill_id: "skl-2", name: "Create a work operation", version: 1, stage: "assisted" },
      ],
      missing_parameters: [],
      question:
        "More than one taught skill fits that. Which did you mean: Create a work area or Create a work operation?",
    },
  });

  const [ask] = buttons(row).filter((button) => button.textContent === "Ask");
  const [utterance] = inputs(row);
  utterance.value = "create a work thing";
  await ask.listeners[0]();

  const said = words(row);
  assert.ok(/Create a work area/.test(said) && /Create a work operation/.test(said));
  assert.ok(/which/i.test(said), "it did not ask which one was meant");
  assert.ok(
    !sent.some((message) => message.kind === "run-skill"),
    "a run started before anyone said which one was meant",
  );
});

test("the row's box is prefilled with a sentence that names the task, never UI chrome", async () => {
  // Round 1 fix: with no model title -- the common case -- the box was
  // prefilled with the literal string "Do the next one", which names no
  // task, and pressing Ask ranked that across the whole library.
  const { row } = await openedOffer({});
  const [utterance] = inputs(row);
  assert.notEqual(utterance.value, "Do the next one", `still UI chrome: ${utterance.value}`);
  assert.match(utterance.value, /work operation/i, `no task named in: ${utterance.value}`);
});

test("a match the reading is not confident about is asked about, never previewed straight through", async () => {
  // Round 1 fix: `renderResolution` read only `matched`/`choices` and threw
  // away `confident` and the hedge in `question`. An unconfident match on an
  // autonomous version reached `renderReady` with `show: "nothing"` and
  // pressed on its own -- a skill the operator never saw named, chosen by a
  // ranker that said out loud it was not sure.
  const { sent, row } = await openedOffer({
    "resolve-intent": {
      matched: { skill_id: "skl-9", name: "Create a work area", version: 1, stage: "autonomous" },
      confident: false,
      question: "Did you mean “Create a work area”? Nothing it does accounts for “urgently”.",
      choices: [],
      missing_parameters: [],
    },
  });

  const [ask] = buttons(row).filter((button) => button.textContent === "Ask");
  const [utterance] = inputs(row);
  utterance.value = "create a work area urgently";
  await ask.listeners[0]();

  assert.ok(
    !sent.some((message) => message.kind === "run-skill"),
    "an unconfident match ran without being confirmed",
  );
  const said = words(row);
  assert.match(said, /urgently/, "the backend's own hedge was not shown");

  // Confirming it is what actually runs it -- the operator, not the ranker,
  // said yes.
  const [yes] = buttons(row).filter((button) => button.textContent.startsWith("Yes"));
  await yes.listeners[0]();
  assert.ok(sent.some((message) => message.kind === "run-skill" && message.skillId === "skl-9"));
});

test("an autonomous press still says which task it started", async () => {
  // The second half of the same finding: "nothing beforehand" was earned for
  // a step-by-step account, never for the operator not knowing which task a
  // one-press run just started -- and that stopped being implied by which
  // row's button was clicked the moment a sentence could name any taught
  // skill, not only the one offered. The name has to survive whatever the
  // press itself goes on to say, refusal included, so this makes the press
  // fail and checks the name is still there rather than overwritten by it.
  const { row } = await openedOffer({
    "resolve-intent": {
      matched: { skill_id: "skl-9", name: "Create a work area", version: 1, stage: "autonomous" },
      confident: true,
      choices: [],
      missing_parameters: [],
    },
    "run-skill": { error: "a looped skill cannot be run this way" },
  });

  const [ask] = buttons(row).filter((button) => button.textContent === "Ask");
  const [utterance] = inputs(row);
  utterance.value = "make a work area";
  await ask.listeners[0]();

  assert.match(words(row), /Create a work area/, "the task that just ran, unattended, was never named");
  assert.match(words(row), /looped skill cannot be run/, "the refusal itself was swallowed");
});

test("a value the sentence supplied is sent, and a blank left in a form is asked for again rather than sent as one", async () => {
  const skillWithParameters = (stage) => ({
    id: "skl-2",
    name: "Adjust an LPN",
    versions: [
      {
        version: 1,
        stage,
        track_record: { clean_streak: 0 },
        steps: [
          { index: 0, intent: "Type the Operation code." },
          { index: 1, intent: "Enter the Voice Code." },
          { index: 2, intent: "Press Save." },
        ],
        parameters: [
          { name: "operation_code", kind: "input", source_step_index: 0, description: "Operation code" },
          { name: "voice_code", kind: "input", source_step_index: 1, description: "Voice Code" },
        ],
      },
    ],
  });

  // First half: the parser read `operation_code` out of the sentence, so it
  // is not in `missing_parameters` -- and it must still reach the press.
  const { sent, row } = await openedOffer({
    "resolve-intent": {
      matched: { skill_id: "skl-2", name: "Adjust an LPN", version: 1, stage: "recorded" },
      confident: true,
      choices: [],
      missing_parameters: ["voice_code"],
      items: [{ operation_code: "NDPCK" }],
    },
    skill: skillWithParameters("recorded"),
  });

  const [ask] = buttons(row).filter((button) => button.textContent === "Ask");
  const [utterance] = inputs(row);
  utterance.value = "adjust the LPN, operation NDPCK";
  await ask.listeners[0]();

  // Second half: the box for the still-missing `voice_code` is on the page.
  // Leaving it blank and continuing must not be accepted as an answer.
  const [voiceCode] = inputs(row).filter((field) => field !== utterance);
  voiceCode.value = "";
  const [go] = buttons(row).filter((button) => button.textContent === "Continue");
  await go.listeners[0]();

  assert.ok(
    !sent.some((message) => message.kind === "run-skill"),
    "a blank field was accepted as an answer and the run started anyway",
  );
  assert.match(words(row), /cannot be left blank/i, "a blank field was silently accepted");

  // Filled in properly, it is accepted -- a `recorded` skill previews every
  // step before the press, so what carries both values is that press.
  voiceCode.value = "VC-7";
  await go.listeners[0]();
  const [doIt] = buttons(row).filter((button) => button.textContent === "Do it");
  await doIt.listeners[0]();

  const ran = sent.filter((message) => message.kind === "run-skill");
  assert.equal(ran.length, 1);
  assert.deepEqual(ran[0].parameters, { operation_code: "NDPCK", voice_code: "VC-7" });
});

test("why teaching needs one more demonstration is said in an operator's own words, not the induction failure's", async () => {
  // `taught.because` is `str(InductionFailed)`: a recording id, an
  // objective-key slug, a JSON pointer diffing two demonstrations -- the one
  // place a skill id or a pointer would otherwise reach an operator's screen.
  const { ids, renderCandidates } = panel(
    {
      deviceId: "dev-1",
      capturing: true,
      watched: [{ tabId: 7, host: "wms.example", since: new Date().toISOString() }],
    },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
    {
      candidates: [offerableCandidate()],
      "teach-candidate": {
        needs_demonstration: true,
        because: "recording rec-8f2c is draft; only sealed recordings can be induced",
      },
    },
  );
  await renderCandidates();
  const row = ids["candidates"].kids[0];
  const [doNext] = buttons(row);
  await doNext.listeners[0]();

  const said = words(row);
  assert.ok(!/rec-8f2c/.test(said), `a recording id reached the operator: ${said}`);
  assert.match(said, /I've watched this a few times/i, "no operator-facing sentence was shown");
});

test("a row that could not be taught is not left dead -- 'Do the next one' works again", async () => {
  const { ids, renderCandidates } = panel(
    {
      deviceId: "dev-1",
      capturing: true,
      watched: [{ tabId: 7, host: "wms.example", since: new Date().toISOString() }],
    },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
    { candidates: [offerableCandidate()], "teach-candidate": { error: "the server is unreachable" } },
  );
  await renderCandidates();
  const row = ids["candidates"].kids[0];
  const [doNext] = buttons(row);
  await doNext.listeners[0]();

  assert.strictEqual(doNext.disabled, false, "a failed teach left the row permanently disabled");
});


test("a picked ambiguous choice sends no value for a parameter nobody supplied one for -- never an empty string", async () => {
  // The regression this round found: picking a choice off the ambiguous list
  // called `preview(version, [])` with nothing known, every input-bearing
  // step still got a name, and the old parameter-building sent `""` under
  // it. `ensure_runnable` counts a present key as supplied and skips shape
  // checks on a falsy value, so a run that used to be refused for a missing
  // value started instead and wrote a blank field -- one click on a
  // disambiguation button, live, if the picked skill was autonomous.
  const { sent, row } = await openedOffer({
    "resolve-intent": {
      matched: null,
      choices: [
        { skill_id: "skl-1", name: "Create a work area", version: 1, stage: "autonomous" },
        { skill_id: "skl-2", name: "Create a work operation", version: 1, stage: "autonomous" },
      ],
      missing_parameters: [],
    },
    skill: {
      id: "skl-1",
      name: "Create a work area",
      versions: [
        {
          version: 1,
          stage: "autonomous",
          track_record: { clean_streak: 12 },
          steps: [
            { index: 0, intent: "Type the Area code." },
            { index: 1, intent: "Press Save." },
          ],
          parameters: [{ name: "area_code", kind: "input", source_step_index: 0, description: "Area code" }],
        },
      ],
    },
  });

  const [ask] = buttons(row).filter((button) => button.textContent === "Ask");
  const [utterance] = inputs(row);
  utterance.value = "create a work thing";
  await ask.listeners[0]();

  const [pick] = buttons(row).filter((button) => button.textContent === "Create a work area");
  await pick.listeners[0]();

  const ran = sent.filter((message) => message.kind === "run-skill");
  assert.equal(ran.length, 1, "picking a choice did not run it");
  assert.deepEqual(
    ran[0].parameters,
    {},
    "a parameter nobody supplied a value for was sent -- as \"\", the exact refusal this closes",
  );
});

test("two presses on 'Do it' are not two runs", async () => {
  const { sent, row } = await openedOffer({
    "resolve-intent": {
      matched: { skill_id: "skl-4", name: "Log a shortage", version: 1, stage: "recorded" },
      confident: true,
      choices: [],
      missing_parameters: [],
    },
    skill: {
      id: "skl-4",
      name: "Log a shortage",
      versions: [
        { version: 1, stage: "recorded", track_record: { clean_streak: 0 }, steps: [], parameters: [] },
      ],
    },
  });

  const [ask] = buttons(row).filter((button) => button.textContent === "Ask");
  const [utterance] = inputs(row);
  utterance.value = "log a shortage";
  await ask.listeners[0]();

  const [doIt] = buttons(row).filter((button) => button.textContent === "Do it");
  assert.ok(doIt, "no 'Do it' button was offered for a version that has not earned silence");
  const first = doIt.listeners[0]();
  const second = doIt.listeners[0]();
  await Promise.all([first, second]);

  assert.equal(
    sent.filter((message) => message.kind === "run-skill").length,
    1,
    "a second click on 'Do it' started a second run",
  );
  assert.strictEqual(doIt.disabled, true, "the button was left pressable after the first click");
});

test("a sentence naming several things says so, and runs only the first of them", async () => {
  // "Evidence, never inference" governs what the panel runs; it governs what
  // it tells somebody it is running just as much. Silently discarding five
  // of six things a person asked for is the worst version of that rule
  // broken.
  const { row } = await openedOffer({
    "resolve-intent": {
      matched: { skill_id: "skl-9", name: "Create a work area", version: 1, stage: "autonomous" },
      confident: true,
      choices: [],
      missing_parameters: [],
      items: [{ area_code: "A1" }, { area_code: "A2" }, { area_code: "A3" }],
    },
    skill: {
      id: "skl-9",
      name: "Create a work area",
      versions: [
        { version: 1, stage: "autonomous", track_record: { clean_streak: 12 }, steps: [], parameters: [] },
      ],
    },
  });

  const [ask] = buttons(row).filter((button) => button.textContent === "Ask");
  const [utterance] = inputs(row);
  utterance.value = "create work areas A1, A2 and A3";
  await ask.listeners[0]();

  const said = words(row);
  assert.match(said, /3 things/, "how many things the sentence named was never said");
  assert.match(said, /area_code: A1/, "which one will actually run was never said");
});

test("a derived value is never sent as a parameter, even when the parser read something under its name", async () => {
  // Minor from round 2: `preview()` matched a step's parameter by
  // `source_step_index` alone, so a `derived` parameter -- "never prompted
  // for", produced by an earlier step's response -- was named exactly like
  // an operator-supplied one. Proven with a value present in `known` under
  // that same name, so this fails if the fix were merely "nothing was known"
  // rather than "derived is never eligible at all".
  const { sent, row } = await openedOffer({
    "resolve-intent": {
      matched: { skill_id: "skl-5", name: "Scan a case", version: 1, stage: "recorded" },
      confident: true,
      choices: [],
      missing_parameters: [],
      items: [{ barcode: "should-not-be-sent" }],
    },
    skill: {
      id: "skl-5",
      name: "Scan a case",
      versions: [
        {
          version: 1,
          stage: "recorded",
          track_record: { clean_streak: 0 },
          steps: [
            { index: 0, intent: "Scan the case barcode." },
            { index: 1, intent: "Press Save." },
          ],
          parameters: [{ name: "barcode", kind: "derived", source_step_index: 0, description: "Barcode" }],
        },
      ],
    },
  });

  const [ask] = buttons(row).filter((button) => button.textContent === "Ask");
  const [utterance] = inputs(row);
  utterance.value = "scan a case";
  await ask.listeners[0]();

  const [doIt] = buttons(row).filter((button) => button.textContent === "Do it");
  await doIt.listeners[0]();

  const ran = sent.filter((message) => message.kind === "run-skill");
  assert.equal(ran.length, 1);
  assert.deepEqual(ran[0].parameters, {}, "a derived value was sent as though an operator supplied it");
});


test("a whitespace-only field is not an answer either", async () => {
  // Same rule as the blank-field test above, applied to the gap it missed:
  // `!field.value` let "   " straight through, because three spaces is
  // truthy. Sent, it is a value the operator never actually gave.
  const { sent, row } = await openedOffer({
    "resolve-intent": {
      matched: { skill_id: "skl-6", name: "Adjust an LPN", version: 1, stage: "recorded" },
      confident: true,
      choices: [],
      missing_parameters: ["voice_code"],
    },
    skill: {
      id: "skl-6",
      name: "Adjust an LPN",
      versions: [
        {
          version: 1,
          stage: "recorded",
          track_record: { clean_streak: 0 },
          steps: [{ index: 0, intent: "Enter the Voice Code." }],
          parameters: [{ name: "voice_code", kind: "input", source_step_index: 0, description: "Voice Code" }],
        },
      ],
    },
  });

  const [ask] = buttons(row).filter((button) => button.textContent === "Ask");
  const [utterance] = inputs(row);
  utterance.value = "adjust the LPN";
  await ask.listeners[0]();

  const [voiceCode] = inputs(row).filter((field) => field !== utterance);
  voiceCode.value = "   ";
  const [go] = buttons(row).filter((button) => button.textContent === "Continue");
  await go.listeners[0]();

  assert.ok(
    !sent.some((message) => message.kind === "run-skill"),
    "a whitespace-only field was accepted as an answer and the run started anyway",
  );
  assert.match(words(row), /cannot be left blank/i, "a whitespace-only field was silently accepted");
});

test("a value the parser read as empty is not sent as one", async () => {
  // Same rule again, at the other entry point: `resolution.items` carrying
  // `""` (or whitespace) under a parameter's name is not the parser having
  // read something -- it is the parser having read nothing -- and the old
  // `known[name] ?? null` kept an empty string as though it were a value.
  const { sent, row } = await openedOffer({
    "resolve-intent": {
      matched: { skill_id: "skl-7", name: "Adjust an LPN", version: 1, stage: "recorded" },
      confident: true,
      choices: [],
      missing_parameters: [],
      items: [{ voice_code: "   " }],
    },
    skill: {
      id: "skl-7",
      name: "Adjust an LPN",
      versions: [
        {
          version: 1,
          stage: "recorded",
          track_record: { clean_streak: 0 },
          steps: [{ index: 0, intent: "Enter the Voice Code." }],
          parameters: [{ name: "voice_code", kind: "input", source_step_index: 0, description: "Voice Code" }],
        },
      ],
    },
  });

  const [ask] = buttons(row).filter((button) => button.textContent === "Ask");
  const [utterance] = inputs(row);
  utterance.value = "adjust the LPN, voice code  ";
  await ask.listeners[0]();

  const [doIt] = buttons(row).filter((button) => button.textContent === "Do it");
  await doIt.listeners[0]();

  const ran = sent.filter((message) => message.kind === "run-skill");
  assert.equal(ran.length, 1);
  assert.deepEqual(
    ran[0].parameters,
    {},
    "an empty value the parser read was sent as a real one",
  );
});


test("it shows what it made and offers to take it back", async () => {
  const { cards } = panel(
    {
      deviceId: "dev-1",
      capturing: true,
      watched: [{ tabId: 7, host: "wms.example", since: new Date().toISOString() }],
      finished: {
        id: "run-1",
        status: "succeeded",
        derived: { operation: "NDPCK", description: "north dock picking" },
        reversal: { skill_id: "skl-2", parameters: { operation_id: "NDPCK" } },
      },
    },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
  );

  const said = cards.map(words).join(" ");
  assert.ok(/NDPCK/.test(said), "it did not show what it made");
  assert.ok(/Undo that/i.test(said), "no undo was offered when one exists");
  assert.ok(!/come out right/i.test(said), "it is still asking a survey question");
});

test("with no way to reverse it, it says so rather than offering a dead button", async () => {
  const { cards } = panel(
    {
      deviceId: "dev-1",
      capturing: true,
      watched: [{ tabId: 7, host: "wms.example", since: new Date().toISOString() }],
      finished: { id: "run-1", status: "succeeded", derived: { operation: "NDPCK" }, reversal: null },
    },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
  );

  const said = cards.map(words).join(" ");
  assert.ok(!/Undo that/i.test(said), "an undo was offered with nothing behind it");
  assert.ok(/I'll fix it/i.test(said), "no way to say it was wrong at all");
});

test("each kind of run is linked into the console route that can read its id", async () => {
  // Both kinds have a page now, and they are different pages because the ids
  // are from different spaces: `/jobs/runs/` reads a workflow-run id and
  // `/runs/` a skill-run id. Sending a workflow run to `/runs/` would look up
  // its id in the skill-run repository, find nothing, and draw "no such run"
  // -- so which route the press opens is the whole of what this card gets
  // right or wrong. Everything else about it -- the band, the step count,
  // Stop -- is the same for both.
  const driving = { runId: "run_a1b2", kind: "ui", since: Date.now(), step: 2 };
  const address = { "panel-console": { consoleUrl: "https://console.test" } };
  const press = async (drawn) => {
    const link = drawn.cards.flatMap(buttons).find((b) => /Details/.test(b.textContent));
    assert.equal(link?.textContent, "Details in console", "a run was offered no console link");
    link.listeners[0]();
    // `openConsole` asks the worker for the address and opens the tab in the
    // reply, so the press only reaches `chrome.tabs.create` a turn later.
    await new Promise((resolve) => setTimeout(resolve, 0));
    return drawn.opened;
  };

  const workflow = panel(
    { deviceId: "dev-1", capturing: true, performing: { ...driving, source: "rig" } },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
    address,
  );
  assert.ok(
    workflow.cards.flatMap(buttons).some((b) => /Stop this run/.test(b.textContent)),
    "the card lost its Stop",
  );
  assert.deepEqual(
    await press(workflow),
    ["https://console.test/jobs/runs/run_a1b2"],
    "a workflow run was sent to the route that reads skill-run ids",
  );

  // No `source` at all -- an older worker's status, or the backend's own run.
  const backend = panel(
    { deviceId: "dev-1", capturing: true, performing: driving },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
    address,
  );
  assert.deepEqual(
    await press(backend),
    ["https://console.test/runs/run_a1b2"],
    "a skill run was sent to the workflow route",
  );
});

test("a run the rig drove shows its own steps and offers nothing the rig cannot do", async () => {
  // The rig has no reversal and nowhere to send "It's wrong", and its outcomes
  // are not the backend's -- "held" is not "succeeded", and a card that read it
  // through the backend's vocabulary would call every rig run a failure.
  const { cards } = panel(
    {
      deviceId: "dev-1",
      capturing: true,
      watched: [{ tabId: 7, host: "wms.example", since: new Date().toISOString() }],
      finished: {
        id: "run_a1b2",
        source: "rig",
        status: "held",
        steps: [{ index: 0, outcome: "held", says: "open the supplier form" }],
        withheld: [{ origin: "https://wms.example" }],
      },
    },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
  );

  const said = cards.map(words).join(" ");
  assert.ok(/open the supplier form/.test(said), "a rig run drew none of its own steps");
  assert.ok(!/Undo that|I'll fix it/i.test(said), "a rig run offered a press the rig cannot answer");
  assert.ok(!/last run failed/i.test(said), "a rig run that held was called a failure");
  assert.ok(/not sent/.test(said), "a dry run did not say what it withheld");
});

test("undo records the ask and starts the reversal skill, nothing else", async () => {
  // The two things "Undo that" means: the record that the operator asked for
  // a reversal, and the reversal run itself -- and nothing besides those two
  // messages, because everything the reversal needs (the skill, its
  // parameters) came back from the backend already computed.
  const { cards, sent } = panel(
    {
      deviceId: "dev-1",
      capturing: true,
      watched: [{ tabId: 7, host: "wms.example", since: new Date().toISOString() }],
      finished: {
        id: "run-1",
        status: "succeeded",
        derived: { operation: "NDPCK" },
        reversal: { skill_id: "skl-2", parameters: { operation_id: "NDPCK" } },
      },
    },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
  );
  const card = cards.find((c) => words(c).includes("NDPCK"));
  const [undo] = buttons(card);
  assert.strictEqual(undo.textContent, "Undo that");

  await undo.listeners[0]();

  assert.deepStrictEqual(sentOf(sent, "run-wrong"), [
    { kind: "run-wrong", runId: "run-1", because: "undone by the operator", keepForRetry: true },
  ]);
  const [ran] = sentOf(sent, "run-skill");
  assert.strictEqual(ran.skillId, "skl-2");
  assert.deepStrictEqual(ran.parameters, { operation_id: "NDPCK" });
  assert.strictEqual(ran.intent, "Undo that");
});

test("'it's wrong' records why without offering a run it cannot take back", async () => {
  const { cards, sent } = panel(
    {
      deviceId: "dev-1",
      capturing: true,
      watched: [{ tabId: 7, host: "wms.example", since: new Date().toISOString() }],
      finished: { id: "run-1", status: "succeeded", derived: { operation: "NDPCK" }, reversal: null },
    },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
  );
  const card = cards.find((c) => words(c).includes("NDPCK"));
  const [wrong] = buttons(card);
  assert.match(wrong.textContent, /I'll fix it/i);

  await wrong.listeners[0]();

  assert.deepStrictEqual(sentOf(sent, "run-wrong"), [
    { kind: "run-wrong", runId: "run-1", because: "the operator said this was wrong" },
  ]);
  assert.deepStrictEqual(sentOf(sent, "run-skill"), []);
});

test("a run that failed is not shown as though it made something", async () => {
  // Round 1 review: `noteFinished` stores any non-"running" status and the
  // card ignored it entirely -- a run that failed partway through, having
  // already read something back, rendered "Created NDPCK." A card must never
  // claim more than the run's own record says.
  const { cards } = panel(
    {
      deviceId: "dev-1",
      capturing: true,
      watched: [{ tabId: 7, host: "wms.example", since: new Date().toISOString() }],
      finished: {
        id: "run-1",
        status: "failed",
        derived: { operation: "NDPCK" },
        reversal: null,
        failure: "the system rejected the write",
      },
    },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
  );

  const card = cards.find((c) => /last run failed/i.test(words(c)));
  assert.ok(card, "a failed run was not reported at all");
  const said = words(card);
  assert.ok(!/Created/i.test(said), "a failed run was shown as though it made something");
  assert.match(said, /the system rejected the write/, "the run's own failure reason was dropped");
  assert.strictEqual(
    buttons(card).length,
    0,
    "a failed run offered a button -- undo or 'wrong' -- with nothing behind it",
  );
});

test("a run already called wrong keeps its retry, not a second way to call it wrong", async () => {
  // Round 1 review: the worker used to delete the finished-run row the moment
  // `run-wrong` was accepted. If starting the reversal then failed (a tab
  // closed, a network blip), the card vanished on refresh with a marked-wrong
  // run, nothing reversed, and no way back to retry. The worker now keeps the
  // row and marks it `wrongBecause`; this is the panel half -- retry the
  // reversal without recording a second, refused `run-wrong`.
  const { cards, sent } = panel(
    {
      deviceId: "dev-1",
      capturing: true,
      watched: [{ tabId: 7, host: "wms.example", since: new Date().toISOString() }],
      finished: {
        id: "run-1",
        status: "succeeded",
        derived: { operation: "NDPCK" },
        reversal: { skill_id: "skl-2", parameters: { operation_id: "NDPCK" } },
        wrongBecause: "undone by the operator",
      },
    },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
  );

  const card = cards.find((c) => words(c).includes("NDPCK"));
  assert.ok(
    !/I'll fix it/i.test(words(card)),
    "a run already called wrong still offered a second way to call it wrong",
  );
  const [undo] = buttons(card);
  assert.strictEqual(undo.textContent, "Undo that");

  await undo.listeners[0]();

  assert.deepStrictEqual(
    sentOf(sent, "run-wrong"),
    [],
    "an already-recorded run was called wrong a second time, which the backend refuses",
  );
  const [ran] = sentOf(sent, "run-skill");
  assert.strictEqual(ran.skillId, "skl-2", "retrying the undo did not start the reversal");
});

/** Every element of one tag under `el` -- the disclosure tests need to know
 * that the steps are *inside* a `details`, which `words()` alone cannot say
 * because it flattens the whole tree into one string. */
function tagged(el, tag) {
  return [...(el.tag === tag ? [el] : []), ...el.kids.flatMap((kid) => tagged(kid, tag))];
}

/** A skill version as the API hands one back, minus whatever the test cares
 * about itself. Two input parameters on the same step by default: that is the
 * shape `preview()` used to lose one half of. */
function previewableVersion(overrides = {}) {
  return {
    version: 3,
    stage: "recorded",
    track_record: { clean_streak: 0 },
    starts_on: "https://wms.example/portal/workOperations",
    steps: [
      { index: 0, intent: "Type the Operation code." },
      { index: 1, intent: "Press Save." },
    ],
    parameters: [
      {
        name: "operation_code",
        kind: "input",
        source_step_index: 0,
        description: "Operation code",
      },
      { name: "priority", kind: "input", source_step_index: 0, description: "Priority" },
    ],
    ...overrides,
  };
}

/** Drives a sentence all the way to a rendered preview: the offer row, the box
 * it opens, and one `resolve-intent` answered by `version`. What each test
 * below does from there is press, or read what is on the screen before
 * pressing. */
async function previewOf_(version, resolution = {}) {
  const { sent, row } = await openedOffer({
    "resolve-intent": {
      matched: {
        skill_id: "skl-9",
        name: "Create a work operation",
        version: version.version,
        stage: version.stage,
      },
      confident: true,
      choices: [],
      missing_parameters: [],
      items: [{ operation_code: "NDPCK", priority: "5" }],
      ...resolution,
    },
    skill: { id: "skl-9", name: "Create a work operation", versions: [version] },
  });
  const [ask] = buttons(row).filter((button) => button.textContent === "Ask");
  const [utterance] = inputs(row);
  utterance.value = "create work operation NDPCK, priority 5";
  await ask.listeners[0]();
  return { sent, row };
}

test("the press names the version the preview was drawn from", async () => {
  // The whole of ADR 014. `resolve-intent` matches on `skill.runnable or
  // skill.latest`, and the preview is built from *that* version -- but the
  // press sent no version at all, so the backend took `skill.latest`. Any
  // skill with a newer RECORDED version (re-teaching, a drift repair, or
  // either of the two console screens that reset a version for review) had
  // the operator reading v1 while v2 wrote, with v1's parameters, and an
  // unreviewed version promoted to assisted by a press that never showed it.
  //
  // Nothing here can prove what the backend does with the number. What it can
  // prove is the half that lives in this file: the number the operator's
  // preview was built from is the number the press carries.
  const { sent, row } = await previewOf_(previewableVersion());

  const [go] = buttons(row).filter((button) => button.textContent === "Do it");
  assert.ok(go, "no press was offered at all");
  await go.listeners[0]();

  const [ran] = sentOf(sent, "run-skill");
  assert.strictEqual(ran.version, 3, "the press could not name which version it read");
  assert.strictEqual(ran.skillId, "skl-9");
});

test("the preview names the tab the run will act in", async () => {
  // Design line 144 and ADR 014's closed list both say it does, and the run
  // genuinely uses it: `starts_on` is navigated to before step one. A preview
  // that listed the steps and left the screen out was describing the same
  // clicks happening somewhere else, and the residual-risk argument that
  // decision rests on depends on that list being exhaustive.
  const { row } = await previewOf_(previewableVersion());

  assert.match(
    words(row),
    /In https:\/\/wms\.example\/portal\/workOperations/,
    "the preview never said which screen the run would act on",
  );
});

test("a step that takes two typed values shows and sends both", async () => {
  // `preview()` matched one parameter per step with `.find()`, so a step that
  // is the source of two -- a code and a priority in the same dialog -- showed
  // one of them and sent one of them. The other was never on the screen the
  // operator read and never in `parameters` at the press, which means a
  // required value silently missing and a preview that was not what ran.
  const { sent, row } = await previewOf_(previewableVersion());

  const said = words(row);
  assert.match(said, /NDPCK/, "the first value was not shown");
  assert.match(said, /\b5\b/, "the second value on the same step was never shown");

  const [go] = buttons(row).filter((button) => button.textContent === "Do it");
  await go.listeners[0]();

  const [ran] = sentOf(sent, "run-skill");
  assert.deepStrictEqual(
    ran.parameters,
    { operation_code: "NDPCK", priority: "5" },
    "a value on the same step as another was never sent",
  );
});

test("the one-line ask still keeps the steps one click away", async () => {
  // Design line 154. A version with a streak has earned the shorter question
  // -- that is the point of tying the ceremony to the rung -- but "earned a
  // shorter question" is not "may no longer be asked what it is about to do".
  const { row } = await previewOf_(
    previewableVersion({ stage: "assisted", track_record: { clean_streak: 4 } }),
  );

  assert.match(words(row), /do it\?/i, "the one-line ask was not drawn");
  const [more] = tagged(row, "details");
  assert.ok(more, "the steps behind a disclosure were not offered at all");
  assert.match(words(more), /Type the Operation code/, "the disclosure held no steps");
  assert.match(words(more), /workOperations/, "the disclosure did not name the screen either");
});

test("undo says what it is about to delete, and pins the version it was offered", async () => {
  // "Undo that" routes through the same press as any other run, and the
  // reversal skill's steps and values are rendered nowhere -- this button is
  // the only place it ever appears. ADR 014's argument for a press promoting
  // a version is that the operator read what it would do; nobody could read
  // this. One press is the design and stays one press, but one press with no
  // idea what is about to be deleted is not something this design ever argued
  // for.
  const { cards, sent } = panel(
    {
      deviceId: "dev-1",
      capturing: true,
      watched: [{ tabId: 7, host: "wms.example", since: new Date().toISOString() }],
      finished: {
        id: "run-1",
        status: "succeeded",
        derived: { operation: "NDPCK" },
        reversal: {
          skill_id: "skl-undo",
          version: 2,
          removes: "Delete the work operation",
          parameters: { operation_id: "NDPCK" },
        },
      },
    },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
  );

  const card = cards.find((c) => words(c).includes("NDPCK"));
  const said = words(card);
  assert.match(said, /Delete the work operation/, "the undo never named what it would remove");
  assert.match(said, /operation_id: NDPCK/, "the undo never named which record");

  const [undo] = buttons(card).filter((button) => button.textContent === "Undo that");
  await undo.listeners[0]();

  const [ran] = sentOf(sent, "run-skill");
  assert.strictEqual(ran.skillId, "skl-undo");
  assert.strictEqual(ran.version, 2, "the undo ran whatever version was newest, not the one it was offered");
});

test("sending with Enter paints the answer, with the cursor still in the box", async () => {
  // The primary way anybody sends a chat message. The redraw a poll makes must
  // not take a half-typed sentence with it -- but this redraw is the
  // operator's own press landing, and skipping it clears the box and paints
  // nothing until they click away.
  const spoke = { id: "thr-1", messages: [] };
  const answered = {
    id: "thr-1",
    messages: [{ id: "m1", speaker: "operator", text: "make a work area for receiving" }],
  };
  const { ids, say, focus } = panel({ deviceId: "dev-1" }, null, {
    thread: spoke,
    "thread-say": answered,
  });
  // The load's own `conversation()` first, which is what learns the thread id.
  await new Promise((resolve) => setTimeout(resolve, 0));

  focus({ tagName: "INPUT" });
  await say("make a work area for receiving");

  assert.match(
    words(ids["said"]),
    /make a work area for receiving/,
    "what the operator sent was never painted",
  );
});

test("a task the conversation already carries is not drawn as a row as well", async () => {
  // The offer is a message in the thread now, with the same two buttons. Drawn
  // here as well, the panel asks twice and then disagrees with itself: `here()`
  // only re-runs on a host change, so dismissing in the ledger left the row
  // live indefinitely, and dismissing on the row left the message live.
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
          id: "cnd-said",
          title: "Create a supplier",
          signature: "POST data/WM/wm/suppliers",
          status: "new",
          times_seen: 4,
          median_duration_ms: 40000,
          minutes_so_far: 5,
          offered_at: "2026-09-02T11:10:08Z",
          episodes: [],
          joins: [],
        },
        {
          id: "cnd-building",
          title: "Create a work area",
          signature: "POST data/WM/wm/workAreas",
          status: "new",
          times_seen: 2,
          median_duration_ms: 20000,
          minutes_so_far: 1,
          offered_at: null,
          episodes: [],
          joins: [],
        },
      ],
    },
  );
  await renderCandidates();

  const said = words(ids["candidates"]);
  assert.ok(!/supplier/i.test(said), `the offered task was drawn twice: ${said.slice(0, 200)}`);
  assert.ok(/work area/i.test(said), "a task still building up stopped being shown");
});


test("yes on a rig offer sends the run with the values typed on the card", async () => {
  // The offer card is the panel's only path to starting a rig run, and this is
  // the message it must send: `start-rig-run`, never `nudge-answer`. The worker
  // reports one fate per path, so an offer that sent both would be counted
  // twice.
  const { sent, answered } = panel({ deviceId: "dev-1" });
  const nudge = { id: "n_1", source: "rig", state: "open", title: "Create Work Area", k: 2 };
  const button = node("button");

  await answered("start-rig-run", nudge, node("li"), button, { values: { description: "x" } });

  assert.deepEqual(sentOf(sent, "start-rig-run"), [
    { kind: "start-rig-run", nudgeId: "n_1", values: { description: "x" } },
  ]);
  assert.deepEqual(sentOf(sent, "nudge-answer"), [], "the offer answered down two paths at once");
  assert.equal(button.disabled, true, "the pressed button stayed live");
});

test("no thanks on a rig offer drops it and starts nothing", async () => {
  const { sent, answered } = panel({ deviceId: "dev-1" });
  const nudge = { id: "n_2", source: "rig", state: "open", title: "Create Work Area", k: 2 };

  await answered("drop-nudge", nudge, node("li"), node("button"));

  assert.deepEqual(sentOf(sent, "drop-nudge"), [{ kind: "drop-nudge", nudgeId: "n_2" }]);
  assert.deepEqual(sentOf(sent, "start-rig-run"), [], "saying no started a run");
  assert.deepEqual(sentOf(sent, "nudge-answer"), []);
});

test("an offer made while the thread is quiet is still drawn", async () => {
  // `show` redrew only when the THREAD changed, and its signature was built
  // from the thread alone. A rig offer is local -- `considerOffer` stores a
  // nudge and prompts on the page, and writes nothing to the thread -- so an
  // offer made while nobody was talking was stored, prompted, and never drawn
  // in the panel. Every poll computed the same signature and returned.
  //
  // Found by a browser on 2026-09-14: the worker matched a shape, made the
  // offer, and the ledger stayed empty. Neither side's tests could see it --
  // the worker's prove the match, the panel's drew their own fixtures.
  const thread = { id: "thr-1", messages: [{ id: "m1", speaker: "system", text: "hello" }] };
  const { ids, offerLocally } = panel(
    {
      deviceId: "dev-1",
      capturing: true,
      watched: [{ tabId: 7, host: "wms.example", since: new Date().toISOString() }],
    },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
    { thread },
  );
  // The load's own `conversation()`, which draws once with no offer in hand.
  await new Promise((resolve) => setTimeout(resolve, 0));

  offerLocally(
    [
      {
        id: "n-1",
        source: "rig",
        state: "open",
        tabId: 7,
        k: 2,
        title: "Create a Work Area",
        values: { workArea: "NEWTESTS" },
        missing: [],
        parameters: ["workArea"],
      },
    ],
    thread,
  );

  assert.match(
    words(ids["said"]),
    /Create a Work Area/,
    "the offer was never drawn: the thread had not changed",
  );
  assert.match(words(ids["said"]), /finish it/i, "drawn, but not as something to answer");
});

test("the same thread and the same offers are not redrawn", async () => {
  // The guard is worth keeping: a redraw replaces the composer and takes
  // whatever somebody was half way through typing with it. Widening the
  // signature must not turn every poll into a redraw.
  const thread = { id: "thr-1", messages: [{ id: "m1", speaker: "system", text: "hello" }] };
  const { ids, offerLocally } = panel({ deviceId: "dev-1" }, null, { thread });
  await new Promise((resolve) => setTimeout(resolve, 0));

  const nudges = [{ id: "n-1", source: "rig", state: "open", tabId: 7, k: 2, title: "A job" }];
  offerLocally(nudges, thread);
  const first = ids["said"].kids[0];
  offerLocally(nudges, thread);

  assert.strictEqual(ids["said"].kids[0], first, "nothing changed and it was redrawn anyway");
});

test("pressing Yes on a rule that fired actually answers it", async () => {
  // A rule fired, the panel drew "Log In - an arrival trigger fired. Shall I?",
  // the operator pressed Yes twice thirteen minutes apart, and both
  // confirmations were still `waiting` in the database: no POST had ever
  // reached the backend.
  //
  // `show` had grown a local named `answered`, which shadowed the press
  // handler of the same name it hands to the ledger -- so `onPress` was a
  // signature string, and every press in the thread threw "onPress is not a
  // function" inside a click listener with nobody watching.
  //
  // This presses the button that is actually drawn rather than calling the
  // exported handler, because what broke was the wiring between the two.
  const made = panel({ deviceId: "dev-1" }, null, {
    "answer-waiting": { ok: true, run_id: "run_9" },
  });
  made.locally(
    {
      waiting: [
        { id: "cnf_1", skill_name: "Log In", because: "an arrival trigger fired", asked_at: 1000 },
      ],
    },
    { id: "thr_1", messages: [] },
  );

  const yes = buttons(made.ids["said"]).find((one) => one.textContent === "Yes, do it");
  assert.ok(yes, "the card a rule left waiting drew no way to say yes");
  await yes.listeners[0]();

  assert.deepEqual(sentOf(made.sent, "answer-waiting"), [
    { kind: "answer-waiting", confirmationId: "cnf_1", answer: "approve" },
  ]);
});

for (const [name, fn] of tests) {
  try {
    await fn();
  } catch (error) {
    throw new Error(`${name}: ${error.message}`, { cause: error });
  }
}
console.log("panel.test.mjs: ok");
