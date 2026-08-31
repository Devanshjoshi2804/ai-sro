// Self-check for the band a driven page shows about itself.
//
// The sentence is the whole product here. Everything else in `showing.js` is
// placement -- a shadow root, a z-index, a timer -- and none of it matters if
// the words are wrong, because the words are what somebody reads before
// deciding whether their screen has been taken over by a colleague, by a bug,
// or by a task they set up themselves.
//
// Run with `node src/background/showing.test.mjs`.

import assert from "node:assert";

import { sentence } from "./showing.js";

// Named, numbered, and with a total: what an ordinary run of a taught skill
// looks like from inside the page it is driving.
assert.equal(
  sentence({ skill: "add the work area", step: 4, of: 13 }),
  "AI-SRO is doing “add the work area” — step 4 of 13",
);

// No total. The vision rung and the self-healer both drive steps the version's
// count does not describe, and a denominator invented here would be read as a
// promise about how much longer this goes on.
assert.equal(
  sentence({ skill: "add the work area", step: 4 }),
  "AI-SRO is doing “add the work area” — step 4",
);

// Nothing named at all. Still a band: "something is driving this tab" is worth
// more than silence, and silence is what the page showed before any of this.
assert.equal(sentence({}), "AI-SRO is working in this tab");
assert.equal(sentence({ skill: "", step: null, of: null }), "AI-SRO is working in this tab");

// A step with no name is still a step. Losing the number because the intent was
// empty would leave the one band a long run shows saying the least.
assert.equal(sentence({ step: 2, of: 9 }), "AI-SRO is working in this tab — step 2 of 9");

console.log("showing.test.mjs: ok");
