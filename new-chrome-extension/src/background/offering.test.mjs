// offering.test.mjs
//
// The decision, without the worker around it: what a tail of gestures does to
// the offer that is open. Pure, so every one of these is arithmetic rather than
// a browser.
//
// Run with `node src/background/offering.test.mjs`.

import assert from "node:assert/strict";
import test from "node:test";
import { decideOffer } from "./offering.js";
import { K_STRAY, tailWith } from "./recognise.js";

const H = "https://wms.example";
// Four steps, not three: `match` offers a strict prefix only, so a job whose
// every step the operator has already done is a job with nothing left to offer.
// A three-step shape would make the third gesture a completion rather than the
// longer prefix the second test is about.
const shape = { id: "wfl_wa", title: "Create Work Area", held_runs: 1, starts_on: `${H}/wa`,
  shape: [[H, "a", "type"], [H, "b", "type"], [H, "save", "click"], [H, "confirm", "click"]],
  parameters: [{ name: "workArea", at: 0 }] };
const typed = (id, value) => ({ triple: [H, id, "type"], value, secret: false, at: 1 });

test("a matched prefix becomes a rig offer carrying k and the values", () => {
  const tail = tailWith(tailWith([], typed("a", "NEW")), typed("b", "x"));
  const { replace, end } = decideOffer({ tail, shapes: [shape], open: null, origin: H, now: 1000 });
  assert.equal(end, null);
  assert.equal(replace.source, "rig");
  assert.equal(replace.workflowId, "wfl_wa");
  assert.equal(replace.k, 2);
  assert.deepEqual(replace.values, { workArea: "NEW" });
  assert.equal(replace.state, "open");
});

test("an open offer is replaced only by a longer prefix", () => {
  const tail = tailWith(tailWith([], typed("a", "NEW")), typed("b", "x"));
  const first = decideOffer({ tail, shapes: [shape], open: null, origin: H, now: 1000 }).replace;
  assert.equal(decideOffer({ tail, shapes: [shape], open: first, origin: H, now: 2000 }).replace, null);
  const longer = tailWith(tail, { triple: [H, "save", "click"], value: null, secret: false, at: 3 });
  assert.equal(decideOffer({ tail: longer, shapes: [shape], open: first, origin: H, now: 3000 }).replace.k, 3);
});

test("a tail that walks away ends the open offer as diverged", () => {
  // A RUN of gestures that advance nothing, not one of them: the match passes
  // over a gesture the shape does not want, because an operator mid-job reads
  // the mail again and clicks a column header. `K_STRAY` is where noise
  // becomes somebody doing something else.
  const tail = tailWith(tailWith([], typed("a", "NEW")), typed("b", "x"));
  const first = decideOffer({ tail, shapes: [shape], open: null, origin: H, now: 1000 }).replace;

  let away = tailWith(tail, typed("elsewhere", "y"));
  assert.equal(
    decideOffer({ tail: away, shapes: [shape], open: first, origin: H, now: 2000 }).end,
    null,
    "one stray gesture withdrew an offer somebody was answering",
  );

  for (let more = 0; more < K_STRAY; more += 1) away = tailWith(away, typed("elsewhere", "y"));
  assert.equal(
    decideOffer({ tail: away, shapes: [shape], open: first, origin: H, now: 3000 }).end,
    "diverged",
  );
});

test("a concrete rig offer outranks an arrival nudge", () => {
  const tail = tailWith(tailWith([], typed("a", "NEW")), typed("b", "x"));
  const open = { id: "n_1", source: "backend", state: "open" };
  const { replace, end } = decideOffer({ tail, shapes: [shape], open, origin: H, now: 1000 });
  assert.equal(end, null);
  assert.equal(replace.source, "rig");
});
