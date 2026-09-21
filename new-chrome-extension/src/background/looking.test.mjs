// Self-check for the mail look's throttle.
//
// Run with `node src/background/looking.test.mjs`.

import assert from "node:assert";
import { test } from "node:test";

const { LOOK_AGAIN_AFTER_MS, LOOK_EVERY_MS, waitBeforeLooking } = await import("./looking.js");

test("a look that has never happened goes now", () => {
  assert.equal(waitBeforeLooking(null), LOOK_EVERY_MS);
  assert.equal(waitBeforeLooking(undefined), LOOK_EVERY_MS);
});

test("a look that reached the mailbox goes again in a minute", () => {
  assert.equal(waitBeforeLooking({ at: 1, reached: true, answered: true }), LOOK_EVERY_MS);
});

test("a deployment with no mailbox is left alone for ten minutes", () => {
  // The backend answered, and what it answered was that there is nothing to
  // read. Asking again in a minute is a call that can only say the same thing.
  assert.equal(
    waitBeforeLooking({ at: 1, reached: false, answered: true }),
    LOOK_AGAIN_AFTER_MS,
  );
});

test("a call that never got an answer knows nothing and waits a minute", () => {
  // Measured on the deployment, 2026-09-17: a deploy restarted the API under a
  // look, and the mail look went quiet for ten minutes on a browser whose
  // mailbox was perfectly reachable, while two mails asking for a job sat
  // unread.
  assert.equal(waitBeforeLooking({ at: 1, reached: false, answered: false }), LOOK_EVERY_MS);
});

test("a record written before any of this un-parks itself", () => {
  // Every browser the old rule parked is holding one of these. Reading it as
  // the long wait would have them serve out ten minutes for an outage that
  // ended before they noticed.
  assert.equal(waitBeforeLooking({ at: 1, reached: false }), LOOK_EVERY_MS);
});
