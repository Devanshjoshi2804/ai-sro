/**
 * Every string an operator reads off these five pages, and nothing else.
 *
 * Pure on purpose, which is the one property the rig's own page argued for:
 * "A pure function so it can be run against hostile and awkward input rather
 * than only ever existing inside a fetch." Nothing here fetches, and nothing
 * here touches React.
 */

/** A run, a step, or anything else carrying a bill. */
export function money(thing: { cost_usd: number; unpriced: boolean }): string {
  // Three states and not two. A call billed on a model missing from the price
  // table records $0.0000 with `unpriced` set; drawing that as $0.0000 is a
  // bill the page invented.
  return thing.unpriced ? "unpriced" : `$${thing.cost_usd.toFixed(4)}`;
}

/** One line of what has become of a mined job. */
export function became(runs: {
  total: number;
  held: number;
  stale: number;
  earned: boolean;
}): string {
  if (!runs.total) return "never run";
  const parts = [`${runs.total} run${runs.total === 1 ? "" : "s"}`, `${runs.held} held`];
  if (runs.earned) parts.push("writes unasked");
  if (runs.stale) parts.push(`${runs.stale} step${runs.stale === 1 ? "" : "s"} matched weakly`);
  return parts.join(" · ");
}

/**
 * The day against its cap.
 *
 * `overCap` is separate from the text because it drives a colour, and because
 * an unpriced day is over the cap however small its total reads: a day whose
 * cost cannot be established is not a cheap day.
 */
export function spendLine(s: {
  cost_usd: number;
  unpriced: number;
  cap_usd: number;
}): { text: string; overCap: boolean } {
  // A negative cap is how this deployment says "no cap"; `>= cap` would then
  // be true for every day and paint a green deployment permanently red.
  const capped = s.cap_usd >= 0;
  const overCap = capped && (s.unpriced > 0 || s.cost_usd >= s.cap_usd);
  const head = capped
    ? `$${s.cost_usd.toFixed(4)} of $${s.cap_usd.toFixed(2)} today`
    : `$${s.cost_usd.toFixed(4)} spent today`;
  // Omitted at zero rather than written as "0 unpriced": the clause exists to
  // be alarming, and one that is always there is not.
  return { text: s.unpriced ? `${head} · ${s.unpriced} unpriced` : head, overCap };
}

/**
 * A timestamp as the record holds it: the rig's UTC, seconds kept, the `T`
 * spent on a space. Deliberately not localised — this is what the row says.
 */
export function when(t: string | null | undefined): string {
  return String(t ?? "").slice(0, 19).replace("T", " ");
}

/** Midnight today in the reader's OWN zone, shaped for `<input type="datetime-local">`. */
export function startOfToday(now: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T00:00`;
}

/** A run's outcome as a card says it: dry runs are marked, live ones are not. */
export function outcomeLabel(run: { outcome: string; live: boolean }): string {
  return run.live ? run.outcome : `${run.outcome} (dry)`;
}
