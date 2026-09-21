// Self-check for picking the frame a control lives in.
//
// The recorder registers with `allFrames: true` and the driver injected into
// the top document only, so a skill taught on a screen the application renders
// inside an iframe -- a portal shell hosting a configuration app, which is most
// enterprise WMS screens -- replayed against a document that held neither the
// framework nor any recorded css path. Thirteen steps of `control_not_found` on
// a screen whose controls were plainly visible, and no amount of re-teaching
// would have fixed it.
//
// What this checks is the half that has to refuse: acting in the wrong frame is
// worse than not acting, so anything other than exactly one claim is no answer.
//
// Run with `node src/background/frames.test.mjs`.

import assert from "node:assert";

import { claimsOf, frameOf } from "./commands.js";

const claimed = (frameId) => ({ frameId, result: { ok: true, result: { probed: true } } });
const empty = (frameId) => ({ frameId, result: { ok: false, error: { kind: "control_not_found" } } });

// The ordinary case: the top document has nothing, the app's own frame has it.
assert.equal(frameOf([empty(0), claimed(42)]), 42);

// Frame 0 is a real frame id and a falsy number. Returning `undefined` for it
// would send every top-document control down the "nobody claimed it" path.
assert.equal(frameOf([claimed(0), empty(7)]), 0);

// Nobody. The top document is asked anyway, so the run still reads the same
// `control_not_found` with the same list of locators tried.
assert.equal(frameOf([empty(0), empty(9)]), undefined);

// Two frames. A page carrying the same form twice -- a list behind a modal over
// it -- and acting on the wrong one is worse than not acting.
assert.equal(frameOf([claimed(0), claimed(3)]), undefined);

// A frame that could not be scripted answers nothing at all.
assert.equal(frameOf([{ frameId: 0 }, claimed(5)]), 5);
assert.equal(frameOf([]), undefined);
assert.equal(frameOf(undefined), undefined);

console.log("frames.test.mjs: ok");

// -- what every frame answered, which `frameOf` reduces away ------------------
//
// `frameOf` collapses "no frame claimed it" and "three frames claimed it" into
// the same `undefined`, and they are different faults wanting different fixes.
// The same step refused twice on the deployment -- KKYT 2026-09-20, SMK1 the
// night after -- and telling those two apart took five rounds of pasting into a
// console with the dialog held open by hand, because nothing kept the probe.

const someClaimed = [empty(0), claimed(7)];

assert.deepEqual(claimsOf(someClaimed), [
  { frame: 0, ok: false, candidates: 0 },
  { frame: 7, ok: true, candidates: 0 },
]);

// The two cases `frameOf` cannot tell apart, told apart.
assert.equal(frameOf([empty(0), empty(9)]), undefined);
assert.equal(frameOf([claimed(0), claimed(3)]), undefined);
assert.deepEqual(
  claimsOf([empty(0), empty(9)]).map((one) => one.ok),
  [false, false],
  "nobody claimed it",
);
assert.deepEqual(
  claimsOf([claimed(0), claimed(3)]).map((one) => one.ok),
  [true, true],
  "everybody claimed it -- a different fault entirely",
);

// How many each frame had, where the probe said so.
assert.deepEqual(
  claimsOf([{ frameId: 4, result: { ok: true, result: { candidates: 3 } } }]),
  [{ frame: 4, ok: true, candidates: 3 }],
);

// A frame that answered nothing at all is still a frame that was asked.
assert.deepEqual(claimsOf([{ frameId: 2 }]), [{ frame: 2, ok: false, candidates: 0 }]);
assert.deepEqual(claimsOf([]), []);
assert.deepEqual(claimsOf(undefined), []);

console.log("frames: ok");
