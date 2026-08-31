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
  return {
    sent,
    cards,
    ids,
    renderCandidates: sandbox.here,
    plainly: sandbox.plainly,
    previewOf: sandbox.previewOf,
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
          { name: "operation_code", source_step_index: 0, description: "Operation code" },
          { name: "voice_code", source_step_index: 1, description: "Voice Code" },
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


for (const [name, fn] of tests) {
  try {
    await fn();
  } catch (error) {
    throw new Error(`${name}: ${error.message}`, { cause: error });
  }
}
console.log("panel.test.mjs: ok");
