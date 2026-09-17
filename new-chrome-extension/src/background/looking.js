// How long to wait before reading the mailbox again.
//
// Two facts used to be one. "The mailbox could not be reached" is the answer a
// deployment with no mail connector gives to every look it will ever be asked
// for -- there is nothing to reach, and asking a minute later is a call that
// can only say the same thing, so it waits ten minutes. A call that FAILED is
// a different fact with the same shape: the backend was restarting, the wifi
// hopped, the laptop lid was shut. Nothing about the mailbox is known.
//
// Measured on the deployment, 2026-09-17: a deploy restarted the API under a
// look, the browser recorded "could not be reached", and the mail look went
// quiet for ten minutes on a browser whose mailbox was perfectly reachable --
// while two mails asking for a job sat unread. Heartbeats every minute the
// whole time, so nothing looked wrong.
//
// So the record says which happened, and only the deployment's own answer
// buys the long wait.

/** The ordinary cadence: a mail that arrived this second is worth a card
 * within a minute, and a search against somebody's mailbox every five seconds
 * is a browser hammering a mail provider all day for nothing. */
export const LOOK_EVERY_MS = 60_000;

/** After the deployment itself says there is no mailbox to read. Ten minutes
 * rather than never: a grant authorised while the panel is open should start
 * working without a reload. */
export const LOOK_AGAIN_AFTER_MS = 600_000;

/**
 * How long this browser should leave it, given the last look.
 *
 * `reached: false` alone is not enough, and that is the whole of this
 * function: it wants `answered: true` beside it -- the backend replied, and
 * what it replied was that the mailbox could not be read. A look that never
 * got an answer knows nothing and waits the ordinary minute.
 *
 * A record with no `answered` at all is one written before this existed, and
 * is read as the short wait. That is deliberate: every browser parked by the
 * old rule un-parks itself on its next beat rather than serving out ten
 * minutes for an outage that ended before it noticed.
 */
export function waitBeforeLooking(last) {
  return last?.reached === false && last?.answered === true
    ? LOOK_AGAIN_AFTER_MS
    : LOOK_EVERY_MS;
}
