// Self-check for the strip: one line, and when it stops being one.
//
// The panel used to open with a card headed "Not watching this tab" and two
// buttons, on every tab, including the ones nobody would ever watch. A
// permission gate is the first thing an operator met every time they switched
// tabs, and the thing they came for was underneath it.
//
// So the state of the tab beside the panel is a line, and the question worth
// asserting on is which states earn more than a line. That is `needsAPress`,
// and it is exported for exactly this reason: the rule is small, load-bearing,
// and the difference between a panel that is quiet and one that nags.
//
// Run with `node src/panel/strip.test.mjs`.

import assert from "node:assert";

import { asMarkup, install, words } from "./test-support/fake-document.mjs";

install();

const { needsAPress, strip } = await import("./strip.js");

const HERE = { tabId: 1, host: "bf56-kms-wms-web-np2.jdadelivers.com" };
const STEADY = { deviceId: "dev-1", capturing: true, channel: "open", watched: [{ tabId: 1 }] };

const tests = [];
const test = (name, fn) => tests.push([name, fn]);

test("a tab being watched, with nothing to answer, is a line", () => {
  assert.equal(needsAPress(STEADY, HERE), null);
  const drawn = strip(STEADY, HERE, {});
  const chip = drawn.kids.find((kid) => kid.className === "chip");
  assert.equal(chip.dataset.open, "false");
  assert.equal(chip.dataset.state, "observing");
  assert.match(words(chip), /bf56-kms/, "the chip must name the tab it is beside");
  assert.match(words(chip), /watching/);
});

test("a tab nobody is watching is still a line, not a wall", () => {
  // The bug this whole design is answering. Being on a tab that is not evidence
  // is the ordinary case -- a console, a mail tab, anything -- and it is worth
  // one line saying so, never a card with buttons in front of everything else.
  const idle = { ...STEADY, capturing: true, watched: [] };
  assert.equal(needsAPress(idle, HERE), null);
  const chip = strip(idle, HERE, {}).kids.find((kid) => kid.className === "chip");
  assert.equal(chip.dataset.open, "false");
  assert.equal(chip.dataset.state, "idle");
  assert.match(words(chip), /not watched/);
});

test("the four states that have something to press open themselves", () => {
  // Each of these is a thing only the operator can fix, and each of them used
  // to be a grey sentence somewhere with nothing to press.
  assert.equal(needsAPress({ ...STEADY, deviceId: "" }, HERE), "not-connected");
  assert.equal(needsAPress({ ...STEADY, grantExpired: true }, HERE), "grant");
  assert.equal(
    needsAPress({ ...STEADY, channel: "closed", performing: { runId: "run-1" } }, HERE),
    "channel",
  );
  assert.equal(needsAPress({ ...STEADY, excludedHere: true }, HERE), "excluded");

  const drawn = strip({ ...STEADY, grantExpired: true }, HERE, {});
  const chip = drawn.kids.find((kid) => kid.className === "chip");
  assert.equal(chip.dataset.open, "true");
  assert.equal(chip.dataset.why, "grant");
});

test("a closed channel with no run to perform is not worth interrupting anybody for", () => {
  // The channel is closed whenever the worker sleeps, which is most of the day.
  // It matters when something is trying to drive this browser and cannot; on
  // its own it is a line, and saying otherwise would make the panel cry wolf
  // hourly.
  assert.equal(needsAPress({ ...STEADY, channel: "closed" }, HERE), null);
});

test("the housekeeping is under the profile, not under the composer", () => {
  // Pause, purge and settings used to sit in a footer, in the operator's eye
  // line, beside the one control they actually reach for. They are things done
  // rarely and deliberately, which is what a menu is for.
  const pressed = [];
  const drawn = strip(STEADY, HERE, { onMenu: (action) => pressed.push(action) });
  const menu = drawn.kids.find((kid) => kid.className === "menu");

  assert.equal(menu.hidden, true, "the menu is closed until somebody opens it");
  assert.deepEqual(
    menu.kids.map((button) => button.textContent),
    [
      "Pause watching",
      "Delete the last hour",
      "Never watch this site",
      "Settings",
      "Disconnect this browser",
    ],
  );

  menu.kids[1].listeners.click[0]();
  assert.deepEqual(pressed, ["purge"], "the menu decides nothing itself");
  assert.equal(menu.hidden, true, "pressing an item leaves the menu closed behind it");
});

test("a paused browser is offered a way back, in the same place", () => {
  const drawn = strip({ ...STEADY, paused: true }, HERE, {});
  const menu = drawn.kids.find((kid) => kid.className === "menu");
  assert.equal(menu.kids[0].textContent, "Resume watching");
  const chip = drawn.kids.find((kid) => kid.className === "chip");
  assert.equal(chip.dataset.state, "paused");
});

test("a host is shown as text, never as markup", () => {
  // A host comes off a tab the operator opened, which is to say off the open
  // internet. `panel.js` and `ledger.js` hold this line and so does this.
  const drawn = strip(STEADY, { tabId: 1, host: "<img src=x onerror=alert(1)>" }, {});
  assert.deepEqual(asMarkup, []);
  assert.match(words(drawn), /<img src=x onerror=alert\(1\)>/);
});

test("a recording says so, and says how long for", () => {
  const drawn = strip({ ...STEADY, teaching: { elapsed: "1:12" } }, HERE, {});
  const chip = drawn.kids.find((kid) => kid.className === "chip");
  assert.equal(chip.dataset.state, "recording");
  assert.match(words(chip), /1:12/);
});

let failed = 0;
for (const [name, fn] of tests) {
  try {
    await fn();
  } catch (error) {
    failed += 1;
    console.error(`  ✗ ${name}\n    ${error.message}`);
  }
}
if (failed) {
  console.error(`strip.test.mjs: ${failed} failed`);
  process.exit(1);
}
console.log(`strip.test.mjs: ok (${tests.length})`);
