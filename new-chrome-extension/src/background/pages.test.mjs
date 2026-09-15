// Self-check for "is this tab already on the screen the task was taught on".
//
// A skill taught by clicking names no URL on any step, so a run used to be
// performable only by an operator who had already navigated to the right screen
// themselves. The version now records where the demonstration began and the run
// opens it -- which makes this comparison the thing that decides whether a tab
// is opened at all, and a wrong answer either opens a tab over and over mid-run
// or drives a page that is not the one the skill was taught on.
//
// Run with `node src/background/pages.test.mjs`.

import assert from "node:assert";

import { opensFor, samePage } from "./commands.js";

const WORK_AREAS =
  "https://wms.example/portal?siteId=SG&subsite=----#wm.config/wm.config.work.work.areas////";
const WAREHOUSE =
  "https://wms.example/portal?siteId=SG&subsite=----#wm.config/wm.config.warehouse.warehouse////";

// The same screen reached in a different session. The query carries a site code
// and whatever else the portal put there; none of it is what makes this page
// the Work Areas page.
assert.equal(samePage(WORK_AREAS, "https://wms.example/portal?siteId=US#wm.config/wm.config.work.work.areas////"), true);

// The fragment is the screen. In an application that routes on it, ignoring it
// would call every page of the WMS the same page -- which is exactly the state
// this was built to end.
assert.equal(samePage(WORK_AREAS, WAREHOUSE), false);

// Trailing slashes are the router's punctuation, not a different screen.
assert.equal(samePage(WORK_AREAS, "https://wms.example/portal#wm.config/wm.config.work.work.areas"), true);

// A different host is never the same screen, whatever the path says.
assert.equal(samePage(WORK_AREAS, WORK_AREAS.replace("wms.example", "other.example")), false);

// A tab with no URL yet, and a skill that recorded no screen. Neither is a
// match, so neither silently passes for one.
assert.equal(samePage(undefined, WORK_AREAS), false);
assert.equal(samePage(WORK_AREAS, undefined), false);
assert.equal(samePage("chrome://newtab", WORK_AREAS), false);

// -- and which step's page a run may open a tab at --------------------------
//
// Measured on the deployment, 2026-09-15. `starts_on` was computed once, for
// the step a run begins at, and then sent with EVERY step -- so step 2 of a
// job that crosses from a mail to a warehouse went out with `origin` naming
// the warehouse and `starts_on` naming the operator's mail. The caller found
// their warehouse tab, threw it away because it was not on that page, opened
// the mail, and clicked a warehouse control there: `not_actionable: the page
// did not answer`.

const MAIL = "https://mail.example/mail/u/0/#inbox/ABC";

// The step's own system. This is what `starts_on` is for: open a tab here.
assert.equal(opensFor({ origin: "https://wms.example", starts_on: WORK_AREAS }), WORK_AREAS);

// Another system's page never takes the tab, however it got into the payload.
assert.equal(opensFor({ origin: "https://wms.example", starts_on: MAIL }), null);

// A step that names no origin keeps the old behaviour: the recorder saw no
// url and the extension resolves it.
assert.equal(opensFor({ origin: null, starts_on: MAIL }), MAIL);

// Nothing to open is not somewhere to open.
assert.equal(opensFor({ origin: "https://wms.example" }), null);
assert.equal(opensFor({ origin: "https://wms.example", starts_on: "" }), null);
assert.equal(opensFor(undefined), null);

console.log("pages.test.mjs: ok");
