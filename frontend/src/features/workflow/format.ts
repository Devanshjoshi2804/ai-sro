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
 * A timestamp as the record holds it: the rig's UTC, seconds kept, the `T`
 * spent on a space. Deliberately not localised — this is what the row says.
 */
export function when(t: string | null | undefined): string {
  return String(t ?? "")
    .slice(0, 19)
    .replace("T", " ");
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

/** Why a job cannot run, one line per reason, each said once; empty when it can. */
export function whyNotRunnable(
  reasons: { code: string; step: number | null; detail: string }[],
): string[] {
  return [
    ...new Set(
      reasons.map((one) => (one.step === null ? one.detail : `Step ${one.step}: ${one.detail}`)),
    ),
  ];
}
