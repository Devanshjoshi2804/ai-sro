// Self-check for accessibility trees taken while nobody is teaching.
//
// The tree is what makes a locator survive a re-render. Without one a skill has
// only a css path of framework ids assigned in render order --
// `span#button-1350-btnIconEl` is a different element after a reload -- so
// until this existed, every skill that arrived the way this product intends
// got the weaker ladder, and the good locators were reserved for the one path
// an operator has to remember to press a button for.
//
// What this checks is mostly what it must NOT do. A tree costs the tab's
// debugger and, outside a policy-managed install, a banner across the
// operator's screen; taking one where it was not agreed to is worse than
// having none.
//
// Run with `node src/background/trees.test.mjs`.

import assert from "node:assert";

const attached = new Set();
const detached = [];
const commands = [];
let attachFails = false;
let times = [];
let nextTree = null;

globalThis.chrome = {
  debugger: {
    attach: async ({ tabId }) => {
      if (attachFails) throw new Error("Another debugger is already attached");
      attached.add(tabId);
    },
    detach: async ({ tabId }) => {
      attached.delete(tabId);
      detached.push(tabId);
    },
    sendCommand: async ({ tabId }, method) => {
      commands.push([tabId, method]);
      if (method === "Accessibility.enable") return {};
      if (nextTree) return nextTree;
      return { nodes: [{ nodeId: "1", role: { value: "button" }, name: { value: "Add" } }] };
    },
  },
  storage: {
    local: {
      get: async (key) => ({ [key]: key === "sro.treeTimes" ? times : null }),
      set: async (entry) => {
        if ("sro.treeTimes" in entry) times = entry["sro.treeTimes"];
      },
    },
  },
};

const { takeTree, takeTreeSoon, release, releaseAll } = await import("./trees.js");

const ON = { capture_enabled: true, capture_snapshots: true, exclude_hosts: [], include_hosts: [] };
const PAGE = "https://wms.example/portal#work.operations";

// Off unless the tenant said so, and nothing is attached to find out.
assert.equal(await takeTreeSoon(1, PAGE, { ...ON, capture_snapshots: false }), null);
assert.equal(attached.size, 0, "a browser nobody agreed to debug was attached to");

// A host the tenant excludes gets no tree and no debugger either -- the same
// rule a screenshot goes by, and for the stronger reason: an excluded page is
// one nothing of ours may touch.
assert.equal(await takeTreeSoon(1, PAGE, { ...ON, exclude_hosts: ["wms.example"] }), null);
assert.equal(attached.size, 0, "an excluded page was attached to");

// The ordinary case.
const taken = await takeTreeSoon(1, PAGE, ON);
assert.ok(taken, "no tree was taken on an allowed page with the policy on");
assert.equal(taken.kind, "snapshot");
assert.equal(taken.url, PAGE);
assert.ok(taken.snapshot.nodes.length);
assert.deepEqual([...attached], [1]);

// It is held for the gesture *after* the one that caused it. The assembler
// attaches a snapshot to the frame of the gesture before it, and that frame's
// locator is built from the tree -- so it has to be the screen the operator was
// looking at when they decided to act, not the page their click produced.
assert.equal(takeTree(1), taken);
assert.equal(takeTree(1), null, "the same tree was handed out twice");

// The debugger is held, not re-attached per gesture: attaching and detaching
// around every click would flash the banner all day on an unmanaged install.
const before = commands.filter(([, method]) => method === "Accessibility.enable").length;
await takeTreeSoon(1, PAGE, ON);
const after = commands.filter(([, method]) => method === "Accessibility.enable").length;
assert.equal(after, before, "the debugger was re-attached for a second gesture");

// The cap. Its own budget, not the screenshots': a tree is a round trip and
// some JSON, a picture is a PNG, and one shared counter would have whichever
// happened first spend the other's allowance.
times = Array.from({ length: 20 }, () => Date.now());
assert.equal(await takeTreeSoon(1, PAGE, ON), null, "the per-minute cap was not enforced");
// A tenant that raised its own cap gets what it asked for.
assert.ok(
  await takeTreeSoon(1, PAGE, { ...ON, snapshot_max_per_minute: 50 }),
  "the tenant's own cap was ignored in favour of the default",
);
times = [];

// DevTools has the debugger, or another extension does. Their tab, their tools:
// capture carries on without trees rather than fighting for it.
attachFails = true;
await release(2);
assert.equal(await takeTreeSoon(2, PAGE, ON), null);
assert.equal(attached.has(2), false);

// And it is not asked again. A tab with DevTools open refuses every time, and
// asking on every click spends a round trip per gesture to be told the same
// thing -- on some Chrome versions, with an error in the operator's own console
// for each one.
attachFails = false;
assert.equal(await takeTreeSoon(2, PAGE, ON), null, "a tab that refused was asked again");

// Letting go clears that, so a tab that closed DevTools is asked once more the
// next time anything releases it -- a navigation, a re-watch.
await release(2);
assert.ok(await takeTreeSoon(2, PAGE, ON), "a released tab was still treated as refused");

// What a person typed is gone from the tree, wherever CDP put it: the box's
// own `value`, and the `name` of the StaticText child it renders that text
// into -- an OTP box leaked exactly this way, with no attribute in either
// place a name rule could have judged it by. An ordinary heading survives.
nextTree = {
  nodes: [
    {
      nodeId: "1",
      role: { value: "textbox" },
      name: { value: "" },
      value: { value: "424242" },
      properties: [{ name: "editable", value: { value: "plaintext" } }],
      childIds: ["2"],
    },
    { nodeId: "2", role: { value: "StaticText" }, name: { value: "424242" }, childIds: [] },
    { nodeId: "3", role: { value: "heading" }, name: { value: "Sign in" }, childIds: [] },
    { nodeId: "4", role: { value: "combobox" }, value: { value: "Dock 3" }, childIds: [] },
  ],
};
const scrubbed = await takeTreeSoon(3, PAGE, ON);
nextTree = null;
await release(3);
const serialized = JSON.stringify(scrubbed.snapshot.nodes);
assert.ok(!serialized.includes("424242"), "a typed value survived scrubbing");
assert.deepEqual(
  scrubbed.snapshot.nodes.map((node) => node.nodeId),
  ["1", "3", "4"],
  "the StaticText child that rendered the typed value was not dropped",
);
assert.deepEqual(scrubbed.snapshot.nodes[0].childIds, [], "the editable node kept its child");
assert.equal(scrubbed.snapshot.nodes[1].name.value, "Sign in", "ordinary page text was scrubbed too");
assert.equal(scrubbed.snapshot.nodes[2].value.value, "Dock 3", "a select lost the option it shows");

// The page's own URL rides in the tree -- Chrome writes it on the root, and
// every link carries one -- and the page an OAuth flow returns to has the
// `code` in it. The real-Chrome proof of spec 5.6 found it there.
nextTree = {
  nodes: [
    {
      nodeId: "1",
      role: { value: "RootWebArea" },
      properties: [
        { name: "url", value: { type: "string", value: "https://wms.example/cb?code=AUTHCODE&state=s1" } },
      ],
      childIds: [],
    },
  ],
};
const rooted = await takeTreeSoon(5, PAGE, ON);
nextTree = null;
await release(5);
assert.ok(!JSON.stringify(rooted.snapshot).includes("AUTHCODE"), "the code in the root's url survived");
assert.ok(JSON.stringify(rooted.snapshot).includes("cb?code="), "the url itself was dropped");

// Stop watching, stop debugging. An operator left with the banner up after
// pressing "stop watching" would have every reason to disbelieve the panel
// about anything else it says.
detached.length = 0;
await release(1);
assert.deepEqual(detached, [1]);
assert.equal(takeTree(1), null, "a released tab kept a tree waiting for it");

// And a policy that switches this off takes every banner down now, rather than
// at the next tab close.
detached.length = 0;
await releaseAll();
assert.deepEqual([...detached].sort(), [2]);
assert.equal(attached.size, 0);

console.log("trees.test.mjs: ok");
