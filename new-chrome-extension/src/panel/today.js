// The last 24 hours, in two numbers.
//
// This is the one line in the product a person repeats to somebody else, so
// every number in it is measured rather than estimated. They come off
// `GET /v1/analytics/summary`, which counts rows an operator can open. Nothing
// here computes a figure of its own, and there is no confidence, no percentage
// and no projection.
//
// Absent rather than zeroed on a day with nothing in it. "0 done · 0 offers"
// is a scoreboard of failure on a product that has not been given
// anything to do yet, and it would be the first thing a new operator read.

/**
 * The line, or `null` when there is nothing yet to say.
 *
 * `summary` is the analytics answer for the last 24 hours; `openOffers` is how
 * many offer cards Home drew, which the panel counts where it draws them.
 */
export function today(summary, openOffers = 0) {
  const done = summary?.doing?.runs || 0;
  if (!done && !openOffers) return null;

  const line = document.createElement("div");
  line.className = "today";
  for (const text of [counted(done, "done"), counted(openOffers, "offer")]) {
    // The number large and in mono, the word under it: a count that changes
    // while somebody watches has to read as a count.
    const [number, ...word] = text.split(" ");
    const cell = document.createElement("span");
    const big = document.createElement("b");
    big.textContent = number;
    const label = document.createElement("span");
    label.textContent = word.join(" ");
    cell.append(big, label);
    line.append(cell);
  }
  return line;
}

/** "3 done", "1 offer", "2 offers". `done` is already past tense in both. */
function counted(count, word) {
  const plural = word === "done" ? word : `${word}s`;
  return `${count} ${count === 1 ? word : plural}`;
}
