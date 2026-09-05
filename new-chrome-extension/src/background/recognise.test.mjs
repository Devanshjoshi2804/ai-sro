// recognise.test.mjs
import assert from "node:assert/strict";
import test from "node:test";
import { K_OFFER_AFTER, K_TAIL, diverged, match, tailWith, valuesFrom } from "./recognise.js";

const H = "https://wms.example";
const workArea = {
  id: "wfl_wa", title: "Create Work Area", held_runs: 2,
  shape: [[H, "wm.workAreas.code", "type"], [H, "wm.workAreas.desc", "type"], [H, "button|Save", "click"]],
  parameters: [{ name: "workArea", at: 0 }, { name: "description", at: 1 }],
};
const operation = {
  id: "wfl_op", title: "Create Work Operation", held_runs: 0,
  shape: [[H, "wm.workAreas.code", "type"], [H, "wm.ops.code", "type"], [H, "button|Save", "click"]],
  parameters: [{ name: "workArea", at: 0 }, { name: "operation", at: 1 }],
};
const shapes = [workArea, operation];
const typed = (identity, value, extra = {}) => ({ triple: [H, identity, "type"], value, secret: false, at: 1, ...extra });

test("one gesture offers nothing", () => {
  const tail = tailWith([], typed("wm.workAreas.code", "NEWTESTS"));
  assert.equal(match(tail, shapes, { origin: H }), null);
  assert.equal(K_OFFER_AFTER, 2);
});

test("two gestures offer the job whose prefix they are, with the values typed so far", () => {
  let tail = tailWith([], typed("wm.workAreas.code", "NEWTESTS"));
  tail = tailWith(tail, typed("wm.workAreas.desc", "north dock"));
  const offer = match(tail, shapes, { origin: H });
  assert.equal(offer.workflowId, "wfl_wa");
  assert.equal(offer.title, "Create Work Area");
  assert.equal(offer.k, 2);
  assert.deepEqual(offer.values, { workArea: "NEWTESTS", description: "north dock" });
  assert.deepEqual(offer.missing, []);
});

test("a shared first step resolves to whichever job the second step names", () => {
  let tail = tailWith([], typed("wm.workAreas.code", "NEWTESTS"));
  tail = tailWith(tail, typed("wm.ops.code", "PICK"));
  assert.equal(match(tail, shapes, { origin: H }).workflowId, "wfl_op");
});

test("a shape on another origin is never matched", () => {
  let tail = tailWith([], typed("wm.workAreas.code", "A"));
  tail = tailWith(tail, typed("wm.workAreas.desc", "b"));
  assert.equal(match(tail, shapes, { origin: "https://elsewhere" }), null);
});

test("scrolls are not part of a shape and do not break a prefix", () => {
  let tail = tailWith([], typed("wm.workAreas.code", "A"));
  tail = tailWith(tail, { triple: [H, "anon|scroll", "scroll"], value: "300", secret: false, at: 2 });
  tail = tailWith(tail, typed("wm.workAreas.desc", "b"));
  assert.equal(match(tail, shapes, { origin: H }).k, 2);
});

test("the tail is bounded", () => {
  let tail = [];
  for (let i = 0; i < 20; i++) tail = tailWith(tail, typed(`c${i}`, "v"));
  assert.equal(tail.length, K_TAIL);
});

test("a secret control contributes no value and the parameter is missing", () => {
  let tail = tailWith([], typed("wm.workAreas.code", null, { secret: true }));
  tail = tailWith(tail, typed("wm.workAreas.desc", "b"));
  const { values, missing } = valuesFrom(tail, workArea, 2);
  assert.deepEqual(values, { description: "b" });
  assert.deepEqual(missing, ["workArea"]);
});

test("a value that is blank is a parameter nobody has answered", () => {
  // A field cleared, or one the gesture read as an empty string. Counted as a
  // value it draws no box on the offer and nothing blocks Yes, so the run
  // starts with a blank where the job needs a word.
  let tail = tailWith([], typed("wm.workAreas.code", ""));
  tail = tailWith(tail, typed("wm.workAreas.desc", "   "));
  const { values, missing } = valuesFrom(tail, workArea, 2);
  assert.deepEqual(values, {});
  assert.deepEqual(missing, ["workArea", "description"]);
});

test("a parameter typed later than the prefix is missing, and one never typed is too", () => {
  const later = { ...workArea, parameters: [{ name: "workArea", at: 0 }, { name: "code", at: 2 }, { name: "never", at: null }] };
  let tail = tailWith([], typed("wm.workAreas.code", "A"));
  tail = tailWith(tail, typed("wm.workAreas.desc", "b"));
  assert.deepEqual(valuesFrom(tail, later, 2).missing, ["code", "never"]);
});

test("a job already finished is not offered back", () => {
  let tail = tailWith([], typed("wm.workAreas.code", "A"));
  tail = tailWith(tail, typed("wm.workAreas.desc", "b"));
  assert.equal(match(tail, shapes, { origin: H }).k, 2);
  tail = tailWith(tail, { triple: [H, "button|Save", "click"], value: null, secret: false, at: 3 });
  assert.equal(match(tail, shapes, { origin: H }), null);
});

test("the job held more often wins a tie on the same prefix", () => {
  const rare = { ...operation, id: "wfl_rare", held_runs: 0, shape: [...workArea.shape.slice(0, 2), [H, "button|Cancel", "click"]] };
  const often = { ...workArea, id: "wfl_often", held_runs: 2 };
  let tail = tailWith([], typed("wm.workAreas.code", "A"));
  tail = tailWith(tail, typed("wm.workAreas.desc", "b"));
  assert.equal(match(tail, [rare, often], { origin: H }).workflowId, "wfl_often");
  assert.equal(match(tail, [often, rare], { origin: H }).workflowId, "wfl_often");
});

test("going another way ends the offer, but carrying it further does not", () => {
  let tail = tailWith([], typed("wm.workAreas.code", "A"));
  tail = tailWith(tail, typed("wm.workAreas.desc", "b"));
  const offer = match(tail, shapes, { origin: H });
  assert.equal(diverged(tail, offer, shapes), false);
  const save = { triple: [H, "button|Save", "click"], value: null, secret: false, at: 3 };
  assert.equal(diverged(tailWith(tail, save), offer, shapes), false, "advancing the job is not diverging from it");
  tail = tailWith(tail, typed("somewhere.else", "x"));
  assert.equal(diverged(tail, offer, shapes), true);
  tail = tailWith(tail, save);
  assert.equal(diverged(tail, offer, shapes), true, "a prefix broken once does not mend");
});
