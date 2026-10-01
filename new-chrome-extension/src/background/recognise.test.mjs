// recognise.test.mjs
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  K_MISSED,
  K_OFFER_AFTER,
  K_STRAY,
  K_TAIL,
  K_TAIL_TTL_S,
  chosen,
  covered,
  diverged,
  match,
  resting,
  tailWith,
  valuesFrom,
} from "./recognise.js";
import { page } from "../panel/nudge.js";
import { screenOf } from "./shape.generated.js";

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
  assert.equal(match(tail, shapes), null);
  assert.equal(K_OFFER_AFTER, 2);
});

test("two gestures offer the job whose prefix they are, with the values typed so far", () => {
  let tail = tailWith([], typed("wm.workAreas.code", "NEWTESTS"));
  tail = tailWith(tail, typed("wm.workAreas.desc", "north dock"));
  const offer = match(tail, shapes);
  assert.equal(offer.workflowId, "wfl_wa");
  assert.equal(offer.title, "Create Work Area");
  assert.equal(offer.k, 2);
  assert.deepEqual(offer.values, { workArea: "NEWTESTS", description: "north dock" });
  assert.deepEqual(offer.missing, []);
});

test("a job as short as the offer threshold is never matched at all", () => {
  // The other end of `shape_of`'s refusal to SERVE one. An offer has to leave
  // something to finish, so k stops at `length - 1` -- and a two-position
  // shape therefore has no k at or above `K_OFFER_AFTER`. The backend served
  // one until 2026-09-14, off by one against this loop; both sides are pinned
  // now, because a rule that lives on two sides of a wire is a rule that
  // drifts on one of them.
  const twoSteps = { ...workArea, id: "wfl_short", shape: workArea.shape.slice(0, K_OFFER_AFTER) };
  let tail = tailWith([], typed("wm.workAreas.code", "NEWTESTS"));
  tail = tailWith(tail, typed("wm.workAreas.desc", "north dock"));

  assert.equal(match(tail, [twoSteps]), null);
  // And the walk carrying on does not rescue it: the whole of a shape is never
  // a prefix anybody is offered.
  const whole = tailWith(tail, { triple: [H, "button|Save", "click"], at: 1 });
  assert.equal(match(whole, [twoSteps]), null);
});

test("a shared first step resolves to whichever job the second step names", () => {
  let tail = tailWith([], typed("wm.workAreas.code", "NEWTESTS"));
  tail = tailWith(tail, typed("wm.ops.code", "PICK"));
  assert.equal(match(tail, shapes).workflowId, "wfl_op");
});

test("a shape on another origin is never matched", () => {
  // The tail's own triples carry the origin, so a job on another system is
  // refused by `endsWith` and needs no filter of its own. This used to pass
  // `{ origin: "https://elsewhere" }` beside a tail whose every gesture was on
  // `H`, which is a state no browser can be in -- and it was the only thing
  // holding up a filter that silently un-offered every cross-system job.
  let tail = tailWith([], { triple: ["https://elsewhere", "wm.workAreas.code", "type"], value: "A", secret: false, at: 1 });
  tail = tailWith(tail, { triple: ["https://elsewhere", "wm.workAreas.desc", "type"], value: "b", secret: false, at: 2 });
  assert.equal(match(tail, shapes), null);
});

test("a job is still offered after the operator has crossed to its second system", () => {
  // `Create Warehouse Equipment Type DDD` -- one gesture in the mail, then
  // twelve on the WMS -- was never offered at all, and the job beside it was
  // offered only during its opening run of mail gestures. Both were mined from
  // real demonstrations; the matcher, not the miner, was losing them.
  const MAIL = "https://mail.example";
  const spanning = {
    id: "wfl_span", title: "Create Equipment Type", held_runs: 2,
    shape: [[MAIL, "name|the brief", "click"], [H, "addButton", "click"], [H, "wm.equip.code", "type"]],
    parameters: [{ name: "equipment", at: 2 }],
  };
  let tail = tailWith([], { triple: [MAIL, "name|the brief", "click"], value: "", secret: false, at: 1 });
  assert.equal(match(tail, [spanning]), null, "one gesture is not yet an offer");
  tail = tailWith(tail, { triple: [H, "addButton", "click"], value: "", secret: false, at: 2 });
  assert.equal(match(tail, [spanning])?.k, 2, "the offer lands on the far system");
});

test("the tail drops scrolls, so one in the middle does not break a prefix", () => {
  // Both sides drop them: `shapes.py` filters `anon|scroll` out of a shape
  // before it is served, so the rig's shapes hold none either and the two
  // agree on what a job's gestures are.
  let tail = tailWith([], typed("wm.workAreas.code", "A"));
  tail = tailWith(tail, { triple: [H, "anon|scroll", "scroll"], value: "300", secret: false, at: 2 });
  tail = tailWith(tail, typed("wm.workAreas.desc", "b"));
  assert.equal(match(tail, shapes).k, 2);
});

test("the tail is bounded", () => {
  let tail = [];
  for (let i = 0; i < K_TAIL + 8; i++) tail = tailWith(tail, typed(`c${i}`, "v"));
  assert.equal(tail.length, K_TAIL);
  assert.ok(K_TAIL >= 35, "long enough to hold the longest job in the corpus");
});

test("a secret control contributes no value and the parameter is missing", () => {
  let tail = tailWith([], typed("wm.workAreas.code", null, { secret: true }));
  tail = tailWith(tail, typed("wm.workAreas.desc", "b"));
  const { values, missing } = valuesFrom(tail, workArea, covered(tail, workArea.shape).at);
  assert.deepEqual(values, { description: "b" });
  assert.deepEqual(missing, ["workArea"]);
});

test("a value that is blank is a parameter nobody has answered", () => {
  // A field cleared, or one the gesture read as an empty string. Counted as a
  // value it draws no box on the offer and nothing blocks Yes, so the run
  // starts with a blank where the job needs a word.
  let tail = tailWith([], typed("wm.workAreas.code", ""));
  tail = tailWith(tail, typed("wm.workAreas.desc", "   "));
  const { values, missing } = valuesFrom(tail, workArea, covered(tail, workArea.shape).at);
  assert.deepEqual(values, {});
  assert.deepEqual(missing, ["workArea", "description"]);
});

test("a parameter typed later than the prefix is missing, and one never typed is too", () => {
  const later = { ...workArea, parameters: [{ name: "workArea", at: 0 }, { name: "code", at: 2 }, { name: "never", at: null }] };
  let tail = tailWith([], typed("wm.workAreas.code", "A"));
  tail = tailWith(tail, typed("wm.workAreas.desc", "b"));
  assert.deepEqual(valuesFrom(tail, later, covered(tail, later.shape).at).missing, ["code", "never"]);
});

test("a shape served with offer_after is not offered before it", () => {
  // Alone, so no shared prefix withholds the offer.
  const later = { ...workArea, offer_after: 3 };
  const two = tailWith(tailWith([], typed("wm.workAreas.code", "NEWTESTS")), typed("wm.workAreas.desc", "d"));
  assert.equal(match(two, [later]), null, "offered at 2 against the rig's 3");
  const three = tailWith(two, { triple: [H, "button|Save", "click"], at: 1 });
  // Three gestures is the whole shape; k stops at length - 1, so still nothing.
  assert.equal(match(three, [later]), null);
  const wider = { ...later, shape: [...later.shape, [H, "button|Next", "click"]] };
  assert.equal(match(three, [wider])?.k, 3);
});

test("a job the rig says this browser is resting from is not offered, until then", () => {
  const two = tailWith(tailWith([], typed("wm.workAreas.code", "NEWTESTS")), typed("wm.workAreas.desc", "d"));
  const tomorrow = new Date(Date.now() + 3600_000).toISOString();
  const yesterday = new Date(Date.now() - 3600_000).toISOString();
  assert.equal(resting({ quiet_until: tomorrow }), true);
  assert.equal(resting({ quiet_until: yesterday }), false);
  assert.equal(resting({ quiet_until: null }), false);
  assert.equal(match(two, [{ ...workArea, quiet_until: tomorrow }]), null);
  assert.equal(match(two, [{ ...workArea, quiet_until: yesterday }])?.k, 2);
  // Still on the list: an open offer on it can tell diverging from finishing.
  const offer = { workflowId: "wfl_wa", k: 2 };
  assert.equal(diverged(two, offer, [{ ...workArea, quiet_until: tomorrow }]), false);
});

test("a job already finished is not offered back", () => {
  let tail = tailWith([], typed("wm.workAreas.code", "A"));
  tail = tailWith(tail, typed("wm.workAreas.desc", "b"));
  assert.equal(match(tail, shapes).k, 2);
  tail = tailWith(tail, { triple: [H, "button|Save", "click"], value: null, secret: false, at: 3 });
  assert.equal(match(tail, shapes), null);
});

// Gone: "the job held more often wins a tie on the same prefix". A tie on `k`
// cannot be constructed any more, and never could be. Two shapes matching at
// the same k both end the tail with their own first k triples, so those k
// triples are the same triples -- the tie the `held_runs` order was breaking
// was always a shared prefix, which is now no offer at all. The two tests
// below are what replaced it.

test("a prefix two jobs share offers neither", () => {
  const cancel = { ...workArea, id: "wfl_cancel", title: "Cancel Work Area", held_runs: 9,
    shape: [...workArea.shape.slice(0, 2), [H, "button|Cancel", "click"]] };
  const archive = { ...workArea, id: "wfl_archive", title: "Archive Work Area", held_runs: 0,
    shape: [...workArea.shape.slice(0, 2), [H, "button|Archive", "click"]] };
  let tail = tailWith([], typed("wm.workAreas.code", "A"));
  tail = tailWith(tail, typed("wm.workAreas.desc", "b"));
  assert.equal(match(tail, [workArea, cancel, archive]), null);
  assert.equal(match(tail, [archive, cancel, workArea]), null, "served order decided it");
});

test("the gesture that separates them is the gesture that offers", () => {
  const cancel = { ...workArea, id: "wfl_cancel", title: "Cancel Work Area",
    shape: [...workArea.shape.slice(0, 2), [H, "button|Cancel", "click"], [H, "button|Yes", "click"]] };
  const archive = { ...workArea, id: "wfl_archive", title: "Archive Work Area",
    shape: [...workArea.shape.slice(0, 2), [H, "button|Archive", "click"], [H, "button|Yes", "click"]] };
  const three = [workArea, cancel, archive];
  let tail = tailWith([], typed("wm.workAreas.code", "A"));
  tail = tailWith(tail, typed("wm.workAreas.desc", "b"));
  tail = tailWith(tail, { triple: [H, "button|Cancel", "click"], value: null, secret: false, at: 3 });
  const offer = match(tail, three);
  assert.equal(offer.workflowId, "wfl_cancel");
  assert.equal(offer.k, 3);
});

test("walking away ends the offer, but carrying it further and a stray do not", () => {
  // The match passes over a gesture the shape does not want, so one of them is
  // no longer divergence -- an operator mid-job reads the mail again, clicks a
  // column header, and on the real trace exactly one such gesture sits between
  // typing the code and clicking the description. What ends the offer is a RUN
  // of them: `K_STRAY` in a row that advance none of the job.
  let tail = tailWith([], typed("wm.workAreas.code", "A"));
  tail = tailWith(tail, typed("wm.workAreas.desc", "b"));
  const offer = match(tail, shapes);
  assert.equal(diverged(tail, offer, shapes), false);
  const save = { triple: [H, "button|Save", "click"], value: null, secret: false, at: 3 };
  assert.equal(
    diverged(tailWith(tail, save), offer, shapes),
    false,
    "advancing the job is not diverging from it",
  );

  const elsewhere = typed("somewhere.else", "x");
  let strayed = tailWith(tail, elsewhere);
  assert.equal(diverged(strayed, offer, shapes), false, "one stray gesture withdrew the offer");

  for (let more = 0; more < K_STRAY; more += 1) strayed = tailWith(strayed, elsewhere);
  assert.equal(diverged(strayed, offer, shapes), true, "the operator has gone elsewhere");
});

test("a gesture older than the tail's lifetime is not the start of today's job", () => {
  let tail = tailWith([], { triple: [H, "wm.workAreas.code", "type"], value: "OLD", secret: false, at: 1000 });
  tail = tailWith(tail, { triple: [H, "wm.workAreas.desc", "type"], value: "b", secret: false, at: 1000 + K_TAIL_TTL_S + 1 });
  assert.equal(tail.length, 1, "yesterday's gesture fell out");
  assert.equal(match(tail, shapes), null, "one fresh gesture is not a prefix");
});

// -- the operator who was already on the screen --------------------------------
//
// Measured on the deployment, 2026-09-15. An operator did `Create a Customer
// Type` end to end -- read the mail, pressed Add, typed the code and the
// description, saved -- and was never once asked to finish it.
//
// A recording carries the navigation the person who made it happened to need.
// This operator was already on the customer types screen, having just deleted
// some there, so they never clicked the tab the recording has as its second
// entry. `endsWith` wanted the tail's last k to BE the shape's first k, so it
// failed at every k and the job the system exists to offer went unoffered
// while the operator did the whole of it by hand.


test("an operator already on the screen is still doing the job", () => {
  const shape = {
    id: "wfl_ct",
    title: "Create a Customer Type",
    shape: [
      ["https://mail.example", "anon|click", "click"],
      [H, "tabItem", "click"],
      [H, "addButton", "click"],
      [H, "customertype-customerType", "click"],
      [H, "customertype-customerType", "type"],
      [H, "saveButton", "click"],
    ],
    parameters: [{ name: "Customer Type", at: 4 }],
  };
  const click = (system, id) => ({ triple: [system, id, "click"], value: null, at: 1 });

  // The mail, and then straight to Add: the tab click is the one they were
  // already past.
  let tail = tailWith([], click("https://mail.example", "anon|click"));
  tail = tailWith(tail, click(H, "addButton"));
  const found = match(tail, [shape]);

  assert.ok(found, "the operator skipped a step they were already past");
  assert.equal(found.title, "Create a Customer Type");
  assert.equal(covered(tail, shape.shape).skipped, 1, "the tab click, and nothing else");
});


test("what the operator typed is read off the gestures that answered, not off a position", () => {
  // The alignment, which is the whole reason the match has to carry one. Once
  // a shape entry can be skipped and a tail entry passed over, the two no
  // longer line up -- and `valuesFrom` read `tail[tail.length - k + at]`. Off a
  // position it shows somebody a value they never typed and starts a run with
  // it.
  const shape = {
    id: "wfl_ct",
    title: "Create a Customer Type",
    shape: [
      ["https://mail.example", "anon|click", "click"],
      [H, "tabItem", "click"],
      [H, "addButton", "click"],
      [H, "customertype-customerType", "type"],
      [H, "saveButton", "click"],
    ],
    parameters: [{ name: "Customer Type", at: 3 }],
  };
  let tail = tailWith([], { triple: ["https://mail.example", "anon|click", "click"], at: 1 });
  // Two more reads of the same mail: noise the shape does not want.
  tail = tailWith(tail, { triple: ["https://mail.example", "anon|click", "click"], at: 2 });
  tail = tailWith(tail, { triple: ["https://mail.example", "anon|click", "click"], at: 3 });
  tail = tailWith(tail, { triple: [H, "addButton", "click"], value: null, at: 4 });
  tail = tailWith(tail, { triple: [H, "customertype-customerType", "type"], value: "GDD", at: 5 });

  const found = match(tail, [shape]);

  assert.ok(found);
  assert.deepEqual(found.values, { "Customer Type": "GDD" });
  assert.deepEqual(found.missing, []);
});


test("the shape may only look a little way ahead", () => {
  // `K_MISSED` is the whole of the looseness. A tail that lands three entries
  // further on has not skipped a step, it is doing something else.
  const shape = {
    id: "wfl_far",
    title: "Far",
    shape: [[H, "a", "click"], [H, "b", "click"], [H, "c", "click"], [H, "d", "click"], [H, "e", "click"]],
    parameters: [],
  };
  const at = (id, n) => ({ triple: [H, id, "click"], value: null, at: n });

  let near = tailWith([], at("a", 1));
  near = tailWith(near, at("d", 2));
  assert.ok(match(near, [shape]), `two ahead is a skipped step (K_MISSED is ${K_MISSED})`);

  let far = tailWith([], at("a", 1));
  far = tailWith(far, at("e", 2));
  assert.equal(match(far, [shape]), null, "four ahead is not this job");
});


test("a dropdown pick answers with the row it clicked", () => {
  // The WMS's combo is ExtJS: clicking the field opens a floating list and the
  // operator clicks a row of it. The choice is that row's text and there is no
  // `value` anywhere -- ten of the forty parameters across both real stores
  // are this, and each one drew an empty box on the offer.
  const shape = {
    shape: [
      ["https://wms.example", "combo|click", "click"],
      ["https://wms.example", "rpComboBoundList|click", "click"],
    ],
    parameters: [{ name: "External System Name", at: 1 }],
  };
  const tail = [
    { triple: shape.shape[0], value: null, at: 1 },
    { triple: shape.shape[1], value: "ConnectShip (TanData)", at: 2 },
  ];

  const found = valuesFrom(tail, shape, covered(tail, shape.shape).at);

  assert.deepEqual(found.values, { "External System Name": "ConnectShip (TanData)" });
  assert.deepEqual(found.missing, []);
});

test("a click with no value answers with what it clicked on", () => {
  const pick = { kind: "click", target: { text: "  ConnectShip (TanData)  " } };
  assert.equal(chosen(pick), "ConnectShip (TanData)");
});

test("only a click, only a label, and never a struck-out one", () => {
  // A press or a scroll lands on a control whose text is the page's rather
  // than the operator's answer. A credential field contributes the fact that
  // it was typed and nothing else -- the rule the tail already wears.
  assert.equal(chosen({ kind: "press", target: { text: "Search" } }), null);
  assert.equal(chosen({ kind: "click", target: { text: "   " } }), null);
  assert.equal(chosen({ kind: "click", target: {} }), null);
  assert.equal(chosen({ kind: "click" }), null);
  assert.equal(chosen({ kind: "click", target: { text: "hunter2", secret: true } }), null);
});


// --- a job is not offered from another screen of the same application -------

const WMS = "https://bf56-kms-wms-web-np2.jdadelivers.com";
const CLIENTS = `${WMS}/portal?siteId=SG#wm.config/wm.config.partners.clients////`;
const SUPPLIERS = `${WMS}/portal?siteId=SG#wm.config/wm.config.partners.suppliers////`;

// The deployment's own row, 2026-09-20. Every control in its opening is an
// ExtJS component id that every screen of this application shares -- so only
// the screen each triple carries (`screenOf`, as the backend keys it) tells
// the supplier's Add from the client's.
const on = (url, id) => [screenOf(url), id, "click"];
const addSupplier = {
  id: "wfl_supplier",
  title: "Initiate Add Supplier",
  held_runs: 2,
  starts_on: page(SUPPLIERS),
  shape: [
    on(SUPPLIERS, "tabItem"),
    on(SUPPLIERS, "ok"),
    on(SUPPLIERS, "addButton"),
    on(SUPPLIERS, "supplierform-selectitemsdrilldownbutton"),
    on(SUPPLIERS, "adrnam"),
  ],
  parameters: [],
};

/** The worker's tail for tab, OK and Add pressed on `url`. */
const addingSomethingOn = (url) =>
  ["tabItem", "ok", "addButton"].map((id) => ({ triple: on(url, id), value: null }));

test("a job is offered on the screen it was recorded on", () => {
  const found = match(addingSomethingOn(SUPPLIERS), [addSupplier]);

  assert.equal(found?.workflowId, "wfl_supplier");
});

test("and not from another screen of the same application", () => {
  // Measured on the deployment 2026-09-20: the operator created three clients
  // -- Partners tab, Add, fill, Save -- and was offered `Initiate Add
  // Supplier`, because `tabItem`, `ok` and `addButton` are what every screen
  // of this application calls its tab, its confirm and its Add.
  const found = match(addingSomethingOn(CLIENTS), [addSupplier]);

  assert.equal(found, null, "the offer was right about the controls, wrong about the screen");
});

test("the query is not what makes it a different screen", () => {
  // The WMS carries a site code in the query and routes on the fragment.
  const sameScreenOtherSite = `${WMS}/portal?siteId=NL&_dc=123#wm.config/wm.config.partners.suppliers////`;

  const found = match(addingSomethingOn(sameScreenOtherSite), [addSupplier]);

  assert.equal(found?.workflowId, "wfl_supplier");
});

test("a recording that opens on the screen before is offered on the screen its work is on", () => {
  // QA 2026-09-29: `Create a Customer Type` opens with the tab click made on
  // the previous screen, so that screen is its `starts_on`; the operator was
  // already on Customer Types and was never offered it.
  const shape = {
    ...addSupplier,
    starts_on: page(CLIENTS),
    shape: [on(CLIENTS, "tabItem"), ...addSupplier.shape.slice(1)],
  };
  const here = ["ok", "addButton"].map((id) => ({ triple: on(SUPPLIERS, id), value: null }));

  assert.equal(match(here, [shape])?.workflowId, "wfl_supplier");
});

test("a match says when the gestures it used began and ended, so a takeover reads only this doing", () => {
  let tail = tailWith([], typed("wm.workAreas.code", "NEWTESTS", { at: 100 }));
  tail = tailWith(tail, { triple: [H, "grid|Customers", "click"], value: null, secret: false, at: 101 });
  tail = tailWith(tail, typed("wm.workAreas.desc", "north dock", { at: 102 }));

  const got = match(tail, [workArea]);

  assert.equal(got.since, 100);
  assert.equal(got.through, 102);
});

// --- part-way through a job, and a second attempt at it ----------------------

const click = (identity, at) => ({ triple: [H, identity, "click"], value: null, secret: false, at });
const long = {
  id: "wfl_long", title: "Add a type", held_runs: 1,
  shape: ["tab", "add", "code", "desc", "dept", "save"].map((one) => [H, one, "click"]),
  parameters: [],
};
const remove = {
  id: "wfl_remove", title: "Remove a type", held_runs: 1,
  shape: ["grid", "delete", "ok", "add", "code", "reset"].map((one) => [H, one, "click"]),
  parameters: [],
};

test("joining a job part-way is offered when a gesture only that job has says which", () => {
  // The form was already open: all the tail holds is the field typed into
  // and the next one, and `desc` is in no other job.
  const got = match([click("code", 1), click("desc", 2)], [long, remove]);

  assert.equal(got?.workflowId, "wfl_long");
});

test("and not on gestures every job on the screen has", () => {
  // `add` then `code` are the opening of one job and the middle of the other.
  // Part-way into `Remove a type` on those is a guess; from the top of `Add a
  // type`, it is the job.
  const got = match([click("add", 1), click("code", 2)], [long, remove]);

  assert.equal(got?.workflowId, "wfl_long", "the middle of Remove tied with the top of Add");
});

test("a second attempt at a job is read as itself, not against where the first got to", () => {
  // QA 2026-09-29: Add, a value, walked off, back, Add again.
  const first = [click("tab", 1), click("add", 2), click("code", 3), click("desc", 4)];
  const away = [click("elsewhere", 5), click("elsewhere", 6)];
  const again = [click("add", 7), click("code", 8)];
  const tail = [...first, ...away, ...again];

  const got = match(tail, [long]);
  assert.equal(got?.workflowId, "wfl_long", "the second attempt was never seen");
  assert.equal(got.since, 7, "matched on the first attempt's gestures");

  const offer = { workflowId: "wfl_long", k: got.k, since: got.since };
  assert.equal(diverged(tail, offer, [long]), false, "the first attempt's leftovers withdrew the offer");
  assert.equal(diverged([...tail, click("desc", 9)], offer, [long]), false);
});

test("editing an existing record is not Create a Transport Equipment Type (real served shapes)", () => {
  // Opus day-end review P: longDescription click, type, saveButton -- what
  // editing a record does -- matched the middle of the transport job's first
  // attempt, k=8. Every triple is screen-keyed, so each is held by one job on
  // its screen; but `longDescription` and `saveButton` are on other screens
  // of the tenant too, and only a gesture rare across ALL served jobs says
  // which job a part-way join is.
  const served = JSON.parse(
    readFileSync(new URL("./test-support/served-shapes-greyorange.json", import.meta.url), "utf8"),
  );
  const screen = served.find((one) => one.title === "Create a Transport Equipment Type").shape[0][0];
  const gestures = (list) =>
    list.map(([identity, kind], at) => ({
      triple: [screen, identity, kind],
      value: kind === "type" ? "x" : null,
      secret: false,
      at,
    }));

  const edit = gestures([["longDescription", "click"], ["longDescription", "type"], ["saveButton", "click"]]);
  assert.equal(match(edit, served), null);
  // Joined part-way on a field only this job has is still offered.
  const rare = gestures([["trailerType", "type"], ["longDescription", "click"]]);
  assert.equal(match(rare, served)?.title, "Create a Transport Equipment Type");
});
