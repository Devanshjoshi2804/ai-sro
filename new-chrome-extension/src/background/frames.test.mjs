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

import { frameOf } from "./commands.js";

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
