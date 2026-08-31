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

import { samePage } from "./commands.js";

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

console.log("pages.test.mjs: ok");
