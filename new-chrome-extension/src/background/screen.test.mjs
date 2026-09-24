// A screenshot command that answers, even when the page will not.
//
// Measured on the deployment, 2026-09-17: four runs failed
// `no screen to look at: timeout: the browser did not answer within 20s`. A
// timeout is the one failure that cannot say which part of itself was slow --
// the run waits its whole deadline and is told a word that names nothing. So
// both halves of a look have a budget, and missing one costs the digest rather
// than the picture.
//
// Run with `node src/background/screen.test.mjs`.

import assert from "node:assert/strict";
import { test } from "node:test";

let captured = [];
let captureDelay = 0;
let measureDelay = 0;
let activated = [];
let raised = [];
/** What the frames of the page answer, where a test has more than one. Null
 * means the single-frame fake below. */
let frames = null;

const sleep = (ms) => new Promise((go) => setTimeout(go, ms));

globalThis.chrome = {
  tabs: {
    query: async () => [
      { id: 7, windowId: 1, active: true, status: "complete", url: "https://wms.example/portal" },
    ],
    get: async () => ({ id: 7, windowId: 1, active: true, url: "https://wms.example/portal" }),
    update: async (id, what) => {
      activated.push([id, what]);
      return { id: 7, windowId: 1, active: true, url: "https://wms.example/portal" };
    },
    captureVisibleTab: async () => {
      if (captureDelay) await sleep(captureDelay);
      captured.push(true);
      // `isPng` wants the signature and more than 24 bytes behind it, which a
      // real capture always has and an eight-byte header does not.
      const png = new Uint8Array(64);
      png.set([0x89, 0x50, 0x4e, 0x47, 13, 10, 26, 10]);
      return "data:image/png;base64," + Buffer.from(png).toString("base64");
    },
    onUpdated: { addListener: () => {}, removeListener: () => {} },
  },
  windows: {
    update: async (windowId, what) => {
      raised.push([windowId, what]);
      return {};
    },
  },
  scripting: {
    executeScript: async ({ target, args, files }) => {
      // `sroCall` injects `page-code.js` itself first, as a plain file with no
      // `func` -- nothing for this fake to answer beyond an empty result.
      if (files) return [];
      // The full measure is the slow one; the cheap probe answers at once. The
      // dispatcher `commands.js` hands `executeScript` is the same shape for
      // every call now, so which `sroPage` method was asked for is read off
      // its own arguments rather than off the function's source text.
      const whole = args?.[0] === "viewport";
      if (whole && measureDelay) await sleep(measureDelay);
      // As Chrome does it: without `allFrames` only the main frame answers,
      // which is the whole of what this is about.
      if (whole && frames)
        return target?.allFrames
          ? frames
          : frames.filter((one) => one.frameId === 0);
      return [
        {
          result: whole
            ? { url: "https://wms.example/portal", width: 1200, height: 800, digest: "Add: 50,60" }
            : { url: "https://wms.example/portal", width: 1200, height: 800, digest: "" },
        },
      ];
    },
  },
  webNavigation: { getAllFrames: async () => [] },
  storage: { local: { get: async () => ({}), set: async () => {} } },
};

const { perform } = await import("./commands.js");

const shot = (payload = {}) =>
  perform({
    command_id: "cmd-1",
    kind: "screenshot",
    payload: { inline: true, origin: "https://wms.example", allow_focus: true, ...payload },
  });

const fresh = () => {
  captured = [];
  activated = [];
  raised = [];
  captureDelay = 0;
  measureDelay = 0;
  frames = null;
};

test("an ordinary look carries the picture and the names beside it", async () => {
  fresh();
  const said = await shot();

  assert.equal(said.ok, true, JSON.stringify(said));
  assert.equal(said.result.width, 1200);
  assert.equal(said.result.text_digest, "Add: 50,60");
  assert.equal(said.result.measured, true);
  assert.ok(said.result.image_base64);
});

test("a page that will not be measured still gets photographed", async () => {
  // The fault itself. A Blue Yonder grid can take longer to measure than the
  // run waits for the whole command, and the picture is the part the rung
  // that looks actually needs -- the digest is a help.
  fresh();
  measureDelay = 6000;

  const said = await shot();

  assert.equal(said.ok, true, JSON.stringify(said));
  assert.equal(said.result.text_digest, "", "it waited for the digest it could not have");
  // The viewport is NOT optional: the model answers in those coordinates and
  // `ui.perform_at` acts in them, so a picture with no size is one nothing can
  // act on.
  assert.equal(said.result.width, 1200);
  assert.equal(said.result.height, 800);
  assert.equal(said.result.measured, false);
  assert.match(said.result.slow, /longer than \d+ms to measure/);
  assert.equal(captured.length, 1);
});

test("a tab that is already active is still raised, because occluded is not visible", async () => {
  // The fault this cost an afternoon on. A window behind another application
  // is occluded, its renderer stops producing frames, and `captureVisibleTab`
  // waits for one that is not coming -- on a tab that is active, on the right
  // page, with the control plainly on it. Being the active tab inside Chrome
  // says nothing about whether Chrome is in front of anything else.
  fresh();
  await shot({ allow_focus: true });

  assert.deepEqual(raised, [[1, { focused: true }]], "it trusted `tab.active`");
});

test("a run that may not take the screen does not raise the window", async () => {
  // Taking somebody's screen while they are working in it is worse than a run
  // that did not finish, and that judgement is the run's rather than this
  // browser's.
  fresh();
  await shot({ allow_focus: false });

  assert.deepEqual(raised, []);
});

test("a browser that will not be photographed says so rather than saying nothing", async () => {
  // Not a timeout for the run to interpret: the command answers, with the kind
  // that tells `drivers.py` this is a browser fault and not a fact about the
  // page, so a working skill is not demoted for it.
  fresh();
  captureDelay = 12_000;

  const said = await shot();

  assert.equal(said.ok, false);
  assert.equal(said.error.kind, "no_tab_for_system");
  assert.match(said.error.detail, /did not answer with a picture within \d+ms/);
});

test("the slow half is bounded on its own, not against the whole command", async () => {
  // Two budgets rather than one. A page that measures slowly and photographs
  // quickly is the common case, and one shared budget would have the first
  // half spend the second half's.
  fresh();
  measureDelay = 6000;
  captureDelay = 2000;

  const said = await shot();

  assert.equal(said.ok, true, JSON.stringify(said));
  assert.equal(said.result.measured, false);
  assert.ok(said.result.image_base64, "the picture was lost to the digest's budget");
});

test("the names come from every frame, not from the portal's top bar", async () => {
  // The fault itself. Measured on the deployment 2026-09-19: `Delete a
  // Customer Type` failed five times on "Opens the filter dropdown", the
  // control found and pressed every time, and the screen belt was given a
  // digest of the portal's nav bar -- because the warehouse application runs
  // in a frame and a look at the screen read the top document only.
  fresh();
  // The application's frame first in the list, so that "the top document's
  // size" is a choice this makes rather than the order it was handed.
  frames = [
    {
      frameId: 4,
      result: { url: "https://wms.example/app", width: 900, height: 700, digest: "Customer Type A: 300,400" },
    },
    {
      frameId: 0,
      result: { url: "https://wms.example/portal", width: 1200, height: 800, digest: "Search: 858,20" },
    },
  ];

  const said = await shot();

  assert.equal(said.ok, true, JSON.stringify(said));
  assert.match(said.result.text_digest, /Customer Type A: 300,400/);
  assert.match(said.result.text_digest, /Search: 858,20/);
  // The picture's own space, which is the top document's -- the frame is 900
  // by 700 and the model answers coordinates in the window.
  assert.equal(said.result.height, 800);
  assert.equal(said.result.width, 1200);
  assert.equal(said.result.measured, true);
});

test("a frame that throws does not cost the look the other frames", async () => {
  fresh();
  frames = [
    { frameId: 0, error: { message: "blocked" } },
    {
      frameId: 4,
      result: { url: "https://wms.example/app", width: 1200, height: 700, digest: "Customer Type A: 300,400" },
    },
  ];

  const said = await shot();

  assert.equal(said.ok, true, JSON.stringify(said));
  assert.equal(said.result.text_digest, "Customer Type A: 300,400");
  assert.equal(said.result.width, 1200);
});

test("a page whose every frame refuses is measured the cheap way", async () => {
  fresh();
  frames = [{ frameId: 0, error: { message: "blocked" } }];

  const said = await shot();

  assert.equal(said.ok, true, JSON.stringify(said));
  assert.equal(said.result.text_digest, "");
  assert.equal(said.result.width, 1200, "the cheap probe still gives the viewport");
});
