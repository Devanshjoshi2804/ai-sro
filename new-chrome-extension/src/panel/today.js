// The day so far, in three numbers.
//
// This is the one line in the product a person repeats to somebody else, so
// every number in it is measured rather than estimated. They come off
// `GET /v1/analytics/summary`, which counts rows an operator can open: runs
// that succeeded, and the time their own doings of those tasks took. Nothing
// here computes a figure of its own, and there is no confidence, no percentage
// and no projection.
//
// Absent rather than zeroed on a day with nothing in it. "0 done · 0 offers ·
// 0 min saved" is a scoreboard of failure on a product that has not been given
// anything to do yet, and it would be the first thing a new operator read.

/**
 * The line, or `null` when there is nothing yet to say.
 *
 * `summary` is the analytics answer; `openOffers` is how many offers in today's
 * thread nobody has answered, which the panel counts from the thread it already
 * holds rather than asking for a second time.
 */
export function today(summary, openOffers = 0) {
  const done = summary?.doing?.runs || 0;
  const minutes = summary?.doing?.minutes_saved || 0;
  if (!done && !openOffers && !minutes) return null;

  const line = document.createElement("div");
  line.className = "today";
  for (const text of [counted(done, "done"), counted(openOffers, "offer"), saved(minutes)]) {
    const cell = document.createElement("span");
    cell.textContent = text;
    line.append(cell);
  }
  return line;
}

/** "3 done", "1 offer", "2 offers". `done` is already past tense in both. */
function counted(count, word) {
  const plural = word === "done" ? word : `${word}s`;
  return `${count} ${count === 1 ? word : plural}`;
}

/** Minutes, or seconds below a minute and a half.
 *
 * "0 min saved" after a run that took thirty seconds off somebody's day reads
 * as nothing having happened, which is the opposite of true.
 */
function saved(minutes) {
  const seconds = Math.round(minutes * 60);
  return seconds >= 90 ? `${Math.round(minutes)} min saved` : `${seconds} s saved`;
}
