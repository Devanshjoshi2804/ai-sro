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
  readFileSync(path.join(here, "result.js"), "utf-8"),
  readFileSync(path.join(here, "ledger.js"), "utf-8"),
  readFileSync(path.join(here, "strip.js"), "utf-8"),
  readFileSync(path.join(here, "today.js"), "utf-8"),
  readFileSync(path.join(here, "run-card.js"), "utf-8"),
  readFileSync(path.join(here, "waiting.js"), "utf-8"),
  readFileSync(path.join(here, "panes.js"), "utf-8"),
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
    scrollTop: 0,
    scrollHeight: 0,
    clientHeight: 0,
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
/** Let what a listener started finish.
 *
 * The tab listeners are `() => void whereWeAre()`: Chrome does not await a
 * listener, so neither do they, and firing one returns before the tab has been
 * looked up. A handful of turns is enough -- `beside()` is one await over a
 * fake `chrome.tabs.query` -- and this is not a timer, so it cannot pass by
 * waiting longer than the thing it is waiting for.
 */
async function settled() {
  for (let turn = 0; turn < 8; turn += 1) await Promise.resolve();
}

function sentOf(sent, kind) {
  return JSON.parse(JSON.stringify(sent.filter((message) => message.kind === kind)));
}

/** The panel, drawn once from one status. `sent` is every message it sent the
 * worker, which is the only thing it can do to the world. */
/** One control of the navigation cluster.
 *
 * It lives in the strip now rather than on a row of its own -- a 360-pixel
 * panel has about six rows of usable height and two of them were being spent
 * saying where you are -- so a test reaches it by walking the strip rather
 * than by the id of a row that no longer exists.
 */
const navTab = (ids, which) => {
  const found = [];
  const walk = (el) => {
    if (el?.dataset?.pane === which) found.push(el);
    for (const kid of el?.kids || []) walk(kid);
  };
  walk(ids["strip"]);
  return found[0];
};

function panel(status, here = null, replies = {}) {
  const sent = [];
  const ids = {};
  // Every tab the panel opened. The panel's other way of acting on the world:
  // `sent` is what it told the worker, this is what it put in front of the
  // operator -- and which URL that is, is the whole of what a "details" link
  // gets right or wrong.
  const opened = [];
  // The panel opens a port to the worker at load and draws whatever it pushes.
  const ports = [];
  // What the panel asked Chrome to tell it about. Held so a test can fire one
  // the way the browser would.
  const watchers = { activated: [], updated: [], focused: [] };
  const sandbox = {
    document: {
      getElementById: (id) => (ids[id] ??= node("div")),
      createElement: (tag) => node(tag),
      // The panel does nothing while it is not on screen. Unset, every push
      // and every beat would be skipped and every test here would be about a
      // hidden panel.
      visibilityState: "visible",
    },
    setInterval: () => 0,
    setTimeout: () => 0,
    URL: URL,
    chrome: {
      runtime: {
        id: "test",
        connect: ({ name }) => {
          const port = {
            name,
            listeners: { message: [], disconnect: [] },
            onMessage: { addListener: (fn) => port.listeners.message.push(fn) },
            onDisconnect: { addListener: (fn) => port.listeners.disconnect.push(fn) },
            postMessage: () => {},
            disconnect: () => {},
          };
          ports.push(port);
          return port;
        },
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
      // The events that tell a side panel it is beside something else. One
      // panel serves the whole window, so nothing about this document changes
      // on a tab switch and these are the only notice it gets -- the beat is
      // twenty seconds, and for that whole stretch every card would be about
      // the tab the operator had just left.
      tabs: {
        query: async () => (here ? [here] : []),
        reload: async () => {},
        create: async ({ url }) => opened.push(url),
        onActivated: { addListener: (fn) => watchers.activated.push(fn) },
        onUpdated: { addListener: (fn) => watchers.updated.push(fn) },
      },
      windows: {
        onFocusChanged: { addListener: (fn) => watchers.focused.push(fn) },
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
    ports,
    watchers,
    // What the browser does when the operator switches tabs: a different tab
    // is the active one, and then Chrome says so.
    switchTo: (tab) => {
      here = tab;
    },
    // Which tab the panel believes it is beside, read out of the sandbox
    // rather than off a card: what a tab switch has to change is this, and
    // every card is drawn from it.
    where: () => vm.runInContext("JSON.stringify(tabHere)", sandbox),
    // Exposed so a test can simulate the panel's own two-second poll --
    // `refresh()` calling `render(status)` again with nothing changed --
    // separately from whatever else a click already triggered.
    render: sandbox.render,
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
    // An offer arriving, as the worker actually delivers one: a status push
    // carrying the nudges, and then whatever the thread happens to say. Both,
    // because an open offer is drawn on HOME -- it is a thing to press, not a
    // thing that was said -- and the thread is what `show` draws.
    offerLocally: (nudges, thread) => {
      sandbox.render({ ...status, nudges });
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

test("arriving on the conversation arrives at the end of it", async () => {
  // Nothing in this panel has ever scrolled, so Chat showed the OLDEST message
  // with the newest below the fold. The thing you came to read was the one
  // place the panel did not put you.
  const { ids } = panel({ deviceId: "dev-1", nudges: [] });
  const tab = (which) =>
    navTab(ids, which).listeners[0];
  // Once, to make the scroller: this fake document builds an element the first
  // time somebody asks for it by id.
  tab("chat")();
  const scroll = ids["scroll"];
  scroll.scrollHeight = 2400;
  scroll.clientHeight = 600;
  scroll.scrollTop = 0;

  tab("home")();
  tab("chat")();

  assert.equal(scroll.scrollTop, 2400, "it left them at the top of the conversation");
});

test("a status landing does not move the view out from under them", async () => {
  // Somebody who has scrolled up is reading something, and the worker pushes a
  // status every couple of seconds.
  const { ids, render } = panel({ deviceId: "dev-1", nudges: [] });
  navTab(ids, "chat").listeners[0]();
  const scroll = ids["scroll"];
  scroll.scrollHeight = 2400;
  scroll.clientHeight = 600;
  scroll.scrollTop = 300;

  render({ deviceId: "dev-1", nudges: [] });

  assert.equal(scroll.scrollTop, 300);
});

test("a run reading the mailbox says so, rather than saying Step 0", async () => {
  // Everything a run does is a step except this one thing: the gather runs
  // before the first step, because a value nobody typed has to be found before
  // anything can be planned with it. On the deployment 2026-09-16 the card
  // said "Step 0" for three and a half minutes while the mailbox was read and
  // the model retried a 5xx, which reads exactly like a run that has hung.
  const { cards } = panel({
    deviceId: "dev-1",
    performing: {
      runId: "run-9",
      kind: "rig",
      since: new Date().toISOString(),
      step: 0,
      doing: "looking in your mail for Customer Type",
    },
  });

  const card = cards.find((one) => words(one).includes("is performing here"));
  assert.match(words(card), /looking in your mail for Customer Type/);
  assert.doesNotMatch(words(card), /Step 0/, "it said which step it was on instead");
});

test("it opens on Home, with the conversation one tap away", async () => {
  // Somebody opening this panel is looking for what the system is doing or
  // wants from them, which is a glance. A conversation is something you go to,
  // and opening on it puts a text box in front of a person whose actual
  // question is "did it work".
  const { ids } = panel({ deviceId: "dev-1", nudges: [] });

  assert.equal(ids["cards"].hidden, false);
  assert.equal(ids["thread"].hidden, true, "the conversation was in front of them");
  // The composer stays. It used to go with the conversation, so somebody who
  // thought of something while looking at their cards had to find the other
  // tab before they could say it -- and a run's question arrives in the
  // conversation, so the box they answer in belongs under their hand on both.
  assert.ok(!ids["ask-bar"]?.hidden, "the panel hid the one box it is typed into");
});

test("the other half hides the cards and brings the composer", async () => {
  const { ids } = panel({ deviceId: "dev-1", nudges: [] });
  const chat = navTab(ids, "chat");

  chat.listeners[0]();

  assert.equal(ids["thread"].hidden, false);
  assert.ok(!ids["ask-bar"]?.hidden);
  assert.equal(ids["cards"].hidden, true);
  assert.equal(ids["today"].hidden, true);
});

test("a request waiting is not drawn while the conversation is showing", async () => {
  // The banner is Home's. On Chat what says so is the count on the tab.
  const { ids } = panel({
    deviceId: "dev-1",
    nudges: [
      {
        id: "n_mail", source: "rig", state: "open", missed: true, tabId: null,
        title: "Create a Customer Type", workflowId: "wfl_1", k: 0,
        values: {}, missing: [], parameters: [], at: new Date().toISOString(),
      },
    ],
  });
  const chat = navTab(ids, "chat");

  chat.listeners[0]();

  assert.equal(ids["waiting"].hidden, true);
  assert.match(
    words(navTab(ids, "home")),
    /1/,
    "nothing on Chat said a request was waiting",
  );
});

test("a request that waited is in the banner and nowhere else", async () => {
  // Two places is one an operator answers twice. The banner holds what arrived
  // while nobody was looking; the stream below holds what is true right now.
  const { ids } = panel({
    deviceId: "dev-1",
    nudges: [
      {
        id: "n_mail", source: "rig", state: "open", missed: true, tabId: null,
        title: "Create a Customer Type", workflowId: "wfl_1", k: 0,
        values: { "Customer Type": "GPX" }, missing: [], parameters: [],
        at: new Date().toISOString(),
      },
    ],
  });

  assert.equal(ids["waiting"].hidden, false, "nothing said anything was waiting");
  assert.match(words(ids["waiting"]), /1 request arrived while you were away/);
  assert.doesNotMatch(words(ids["cards"]), /Create a Customer Type/, "drawn in both places");
});

test("an unchanged banner is left alone, with whatever was typed into it", async () => {
  // The panel repaints on every push from the worker. Rebuilding these cards
  // each time takes the half-typed value in one of them with it -- the defect
  // the ledger's own redraw guard exists for, in a place with boxes to type
  // into -- and replaces identical children under a live region, which is a
  // screen reader saying "1 request arrived" all afternoon.
  const status = {
    deviceId: "dev-1",
    nudges: [
      {
        id: "n_mail", source: "rig", state: "open", missed: true, tabId: null,
        title: "Create a Customer Type", workflowId: "wfl_1", k: 0,
        values: {}, missing: ["Customer Type"], parameters: [],
        at: new Date().toISOString(),
      },
    ],
  };
  const { ids, render } = panel(status);
  const drawn = ids["waiting"].kids[0];

  render(status);

  assert.strictEqual(ids["waiting"].kids[0], drawn, "the banner was rebuilt for nothing");
});

test("nothing waiting leaves no banner behind", async () => {
  const { ids } = panel({ deviceId: "dev-1", nudges: [] });

  assert.equal(ids["waiting"].hidden, true);
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

test("a match on a job the run can gather for is offered rather than refused", async () => {
  // The same card, on a deployment that can read the operator's mailbox. What
  // the mail did not say is what the run goes and finds, so refusing to start
  // would be the panel asking for what the run already knows how to get.
  const { cards } = panel({
    deviceId: "dev-1",
    offers: [
      {
        ...OFFER,
        skillId: null,
        workflowId: "wfl_watched",
        skill: "Create a Customer Type",
        read: {},
        values: {},
        missing: ["Customer Type"],
        canFind: true,
      },
    ],
  });

  const card = cards.find((c) => words(c).includes("A mail matched"));
  assert.match(words(card), /Create a Customer Type/);
  assert.match(words(card), /I read those out of the mail when it runs/);
  const [run] = buttons(card);
  assert.strictEqual(run.disabled, false, "a value the run can find stopped the press");
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

test("switching tabs is noticed when it happens, not on the twenty-second beat", async () => {
  // One side panel serves the whole window, so a tab switch does not reload
  // this document and nothing about it changes by itself. `whereWeAre` used to
  // be a passenger on the two-second poll; when the worker's push replaced
  // that poll the beat went to twenty seconds and took `whereWeAre` with it --
  // and the push gave nothing back, because it carries the WORKER's status and
  // which tab an operator is looking at is not worker state.
  //
  // Every card is about "this tab". Until this fired, the state line, the
  // watch button and what was offerable all belonged to the tab they had left.
  const status = { deviceId: "dev-1", capturing: true, watched: [] };
  const panelHere = panel(status, { id: 7, host: "wms.example", url: "https://wms.example/portal" });

  assert.ok(panelHere.watchers.activated.length, "nothing asked Chrome about a tab switch");

  panelHere.switchTo({ id: 9, host: "mail.example", url: "https://mail.example/inbox" });
  panelHere.watchers.activated.forEach((fn) => fn({ tabId: 9 }));
  await settled();

  assert.deepEqual(JSON.parse(panelHere.where()), {
    tabId: 9,
    host: "mail.example",
    url: "https://mail.example/inbox",
  });
});

test("a second tab on the same host is redrawn, not assumed to be the first", async () => {
  // The watch list is keyed by tab id, so "is this tab being watched" has two
  // different answers for two tabs of one warehouse. What decided whether to
  // redraw was the HOST, so moving between them updated the tab underneath and
  // left every card as it was -- the panel saying "Watching this tab" beside a
  // tab nothing was recording, until the twenty-second beat.
  //
  // The redraw is what is asserted, not `tabHere`: the tab was always assigned.
  const status = { deviceId: "dev-1", capturing: true, watched: [] };
  const panelHere = panel(status, { id: 7, host: "wms.example", url: "https://wms.example/portal" });
  const before = sentOf(panelHere.sent, "status").length;

  panelHere.switchTo({ id: 8, host: "wms.example", url: "https://wms.example/orders" });
  panelHere.watchers.activated.forEach((fn) => fn({ tabId: 8 }));
  await settled();

  assert.equal(JSON.parse(panelHere.where()).tabId, 8, "the panel still believes it is on tab 7");
  assert.ok(
    sentOf(panelHere.sent, "status").length > before,
    "the tab changed under the panel and nothing was redrawn",
  );
});

test("the tab navigating under the panel counts as arriving somewhere else", async () => {
  // A warehouse screen that routes without a page load, and a sign-in that
  // lands somewhere afterwards. `onActivated` never fires for either.
  const status = { deviceId: "dev-1", capturing: true, watched: [] };
  const panelHere = panel(status, { id: 7, host: "wms.example", url: "https://wms.example/portal" });

  assert.ok(panelHere.watchers.updated.length, "nothing asked Chrome about a navigation");

  panelHere.switchTo({ id: 7, host: "mail.example", url: "https://mail.example/inbox" });
  panelHere.watchers.updated.forEach((fn) => fn(7, { url: "https://mail.example/inbox" }));
  await settled();

  assert.equal(JSON.parse(panelHere.where()).host, "mail.example");
});

test("a tab reporting anything other than a new address is left alone", async () => {
  // `onUpdated` fires for a favicon, a title, a loading state. Re-resolving on
  // every one of them would be the two-second poll back under another name.
  const status = { deviceId: "dev-1", capturing: true, watched: [] };
  const panelHere = panel(status, { id: 7, host: "wms.example", url: "https://wms.example/portal" });

  panelHere.switchTo({ id: 9, host: "mail.example", url: "https://mail.example/inbox" });
  panelHere.watchers.updated.forEach((fn) => fn(7, { status: "complete", title: "Orders" }));
  await settled();

  assert.equal(JSON.parse(panelHere.where()).tabId, 7);
});

test("moving to another window is noticed, and it activates no tab", async () => {
  // The tab being focused was already the active one in its own window, so
  // `onActivated` does not fire and this is the only notice there is.
  const status = { deviceId: "dev-1", capturing: true, watched: [] };
  const panelHere = panel(status, { id: 7, host: "wms.example", url: "https://wms.example/portal" });

  assert.ok(panelHere.watchers.focused.length, "nothing asked Chrome about a window change");

  panelHere.switchTo({ id: 11, host: "mail.example", url: "https://mail.example/inbox" });
  panelHere.watchers.focused.forEach((fn) => fn(2));
  await settled();

  assert.equal(JSON.parse(panelHere.where()).tabId, 11);
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

test("a run that came up short takes the operator to the question", async () => {
  // The dead end this replaces: the run went looking for a value nobody typed,
  // could not find it, and the panel drew "The run stopped" on the Home tab
  // while the question about that value sat unread behind the other one.
  const { cards, ids } = panel(
    {
      deviceId: "dev-1",
      capturing: true,
      watched: [{ tabId: 7, host: "wms.example", since: new Date().toISOString() }],
      finished: {
        id: "run_short",
        source: "rig",
        status: "stopped",
        steps: [],
        needs: ["Customer Type"],
      },
    },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
  );

  const said = cards.map(words).join(" ");
  assert.match(said, /could not find Customer Type/);
  assert.ok(!/The run stopped/.test(said), "it reported the dead end instead of the way out");
  // And the conversation is what is on screen, because that is where the
  // question is. A question behind the other tab is a question nobody answers.
  assert.equal(ids["thread"].hidden, false, "the panel stayed on Home with a question waiting");
  assert.equal(ids["cards"].hidden, true);
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

  // On HOME, which is where a thing to press belongs. It used to be drawn in
  // the conversation, interleaved with what was said -- right when the panel
  // was one column, wrong the moment it became two: splitting it left Home
  // empty and put the card a person was waiting to press behind the other tab.
  assert.match(
    words(ids["cards"]),
    /Create a Work Area/,
    "the offer was never drawn: the thread had not changed",
  );
  assert.match(words(ids["cards"]), /finish it/i, "drawn, but not as something to answer");
  assert.doesNotMatch(words(ids["said"]), /Create a Work Area/, "drawn in both places");
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

test("the poll does not empty the box somebody is typing their password into", async () => {
  // The card asked for the password, the operator started typing it, and the
  // two-second poll rebuilt every card from scratch -- taking the box and what
  // was in it. The thread has held this rule since the composer was built; the
  // cards column had nothing typed into it until this card existed.
  const status = {
    deviceId: "dev-1",
    finished: {
      id: "run_1",
      source: "rig",
      status: "stopped",
      steps: [
        {
          index: 0,
          outcome: "failed",
          says: "Type the password.",
          sent: {
            kind: "none",
            payload: { needs_secret: { system: "keycloak.test", field: "password" } },
          },
        },
      ],
    },
  };
  const made = panel(status);
  const box = inputs(made.ids["cards"]).find((one) => one.type === "password");
  assert.ok(box, "the card that asked for a password drew no box");

  box.value = "half-ty";
  made.focus(box);
  made.render(status);

  assert.strictEqual(
    inputs(made.ids["cards"]).find((one) => one.type === "password"),
    box,
    "the poll replaced the box somebody was typing into",
  );
  assert.equal(box.value, "half-ty", "what they had typed was thrown away");
});

test("the worker pushes the state and the panel draws it without asking", async () => {
  // It used to poll every two seconds: two redraws a second of work nobody
  // did, and a state change waiting up to two seconds to appear. A rule fires,
  // a run starts, an offer lands -- and the panel sat on the old picture.
  const made = panel({ deviceId: "dev-1" });
  const [port] = made.ports;
  assert.ok(port, "the panel never opened a port to the worker");
  assert.equal(port.name, "panel");

  // The panel's own load-time fetch first, so what is on screen when the push
  // lands is what the worker last answered rather than a half-built page.
  await new Promise((resolve) => setTimeout(resolve, 0));
  const before = made.sent.filter((message) => message.kind === "status").length;
  port.listeners.message[0]({
    kind: "status",
    status: { deviceId: "dev-1", teaching: { startedAt: new Date().toISOString() } },
  });
  await new Promise((resolve) => setTimeout(resolve, 0));

  const drawn = `${words(made.ids["expanded"])} ${words(made.ids["cards"])}`;
  assert.match(drawn, /[Rr]ecording/, "a pushed status was not drawn");
  assert.equal(
    made.sent.filter((message) => message.kind === "status").length,
    before,
    "the panel asked for a status it had just been given",
  );
});

test("a port that dies is dropped rather than retried into a storm", async () => {
  const made = panel({ deviceId: "dev-1" });
  const [port] = made.ports;

  port.listeners.disconnect[0]();

  assert.equal(made.ports.length, 1, "the panel reconnected the instant it was disconnected");
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
