// When something happened, and what the day it happened on is called.
//
// All that is left of the pane of requests waiting on the operator, which went
// with the offers this browser used to make and start itself: the backend asks
// in the conversation now. The recent-tasks list and the watching card still
// read a time and name a day, and these are the one reading of both.

/** When something happened, in milliseconds, from either shape it is held in.
 *
 * What this browser stores is often an ISO STRING, and everything that once
 * reached for one read `Number(at)`, which is `NaN` -- so a list dated every
 * row to the first of January 1970 and "newest first" sorted nothing at all,
 * because `NaN - NaN` is not an order. The unit tests passed: they were
 * written with numbers, which is the one shape the real thing never uses.
 */
export function when(at) {
  if (typeof at === "number") return Number.isFinite(at) ? at : 0;
  const parsed = Date.parse(String(at ?? ""));
  return Number.isFinite(parsed) ? parsed : 0;
}

/** What a day is called at the top of its group. */
export function dayNamed(at, now = Date.now()) {
  const was = new Date(when(at));
  const today = new Date(now);
  const midnight = (d) =>
    new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const days = Math.round((midnight(today) - midnight(was)) / 86400000);
  if (days <= 0) return "Today";
  if (days === 1) return "Yesterday";
  // Past a week the weekday stops being a date anybody can place: "Tuesday"
  // is this week's Tuesday to everybody who reads it.
  if (days < 7) return was.toLocaleDateString(undefined, { weekday: "long" });
  return was.toLocaleDateString(undefined, { day: "numeric", month: "short" });
}
