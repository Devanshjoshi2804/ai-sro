// "You have done this here before. Shall I?"
//
// Said the moment an operator lands on the page a known task starts on, which
// is the one moment it is worth saying: they are about to do the thing.
//
// The rule that matters is not when it fires but when it stops. A prompt that
// outlives the task it offered is a prompt that was ignored, and a product that
// nags is one whose notifications get switched off in week two. So a nudge ends
// three ways, whichever comes first:
//
//   1. They answer it.
//   2. They do the task themselves -- the first write on that host says so, and
//      nothing more needs to be said.
//   3. Ninety seconds, or they navigate away.
//
// Nothing here is stored on the server. A nudge lives about a minute and a half
// and a conversation full of them is noise; only an answer produces anything
// durable, and what it produces is a run. That is also why this is browser-held
// rather than a message: the thread is the record of what was decided, and a
// prompt nobody answered decided nothing.
//
// Pure over an injected clock, which is what makes ninety seconds a test rather
// than a wait.

/** Long enough to read and decide, short enough not to outlive the task.
 *
 * The tasks this fires on take about 36 and 161 seconds where they were
 * measured. A prompt still on screen after the work is done is the failure this
 * number exists to avoid.
 */
export const LIFETIME_MS = 90_000;

/** When an offer that came from a mail stops asking QUIETLY: the end of their day.
 *
 * The ninety seconds above are the arrival rule, and they are right for it --
 * it fires the moment somebody lands on the page, so the work is either
 * happening now or it is not. A mail is the opposite: it arrives while they
 * are on the floor, and a card that expired before they next looked at the
 * panel would be a request nobody ever sees.
 *
 * A day rather than for ever in the sense that matters: after it the card stops
 * being today's news and becomes one of the ones they missed -- counted,
 * still there, still pressable. A request nobody has answered has not stopped
 * being a request, and a panel that swept it would be one that loses work.
 */
export function endOfDay(now) {
  const midnight = new Date(now);
  midnight.setHours(24, 0, 0, 0);
  return midnight.getTime();
}

/** Host and path, no query -- the same shape the miner records `starts_on` in.
 *
 * Without the query, because that is where a warehouse system puts session ids
 * and timestamps: a page addressed with one is never the same page twice.
 */
export function page(url) {
  try {
    const parsed = new URL(url);
    return `${parsed.host}${parsed.pathname}`.replace(/\/$/, "");
  } catch {
    return "";
  }
}

/**
 * The task worth offering here, or `null`.
 *
 * `visit` identifies this navigation, not this page: asking once per visit
 * means an operator who comes back in the afternoon is asked again, and one who
 * is standing on the page is asked once.
 */
export function shouldFire({ url, visit, candidates, nudges, muted, performing, now }) {
  // The browser is already being driven. Offering to drive it again is the
  // panel talking over itself.
  if (performing) return null;

  const here = page(url);
  if (!here) return null;
  if (muted[here] && muted[here] > now) return null;
  // One at a time, anywhere. Two open at once is a queue, and a queue of
  // prompts is the thing this design exists to not be.
  if (nudges.some((nudge) => nudge.state === "open")) return null;
  if (nudges.some((nudge) => nudge.startsOn === here && nudge.visit === visit)) return null;

  return (
    candidates.find(
      (candidate) =>
        candidate.starts_on === here &&
        // Proven enough to offer: taught by somebody, done often enough to be
        // a habit, or -- for a job the rig serves -- already run and held.
        (candidate.source === "rig" || candidate.skill_id || candidate.times_seen >= 3),
    ) || null
  );
}

export function fire(candidate, now, { tabId = null, visit = "" } = {}) {
  return {
    id: `n_${now}_${candidate.id}`,
    // When this one stops asking, where the ninety seconds are the wrong
    // clock, and whether walking off the page ends it. Both are about an
    // offer that did NOT come from an arrival: a mail arrives while the
    // operator is on the floor, so it was never tied to a page they were
    // standing on and there is no page for them to leave. Absent -- every
    // arrival nudge -- and the rules below are exactly what they were.
    expiresAt: candidate.expires_at || null,
    // An offer that is KEPT rather than swept. A mail is not about where the
    // operator is standing: it arrived while they were on the floor, so
    // leaving a page says nothing about it, and running out of time does not
    // mean the request went away -- it means nobody has looked yet. So it goes
    // quiet instead of ending: still open, still pressable, and flagged as one
    // they missed so the panel can say how many are waiting.
    //
    // Absent -- every arrival nudge -- and the two rules below are exactly
    // what they were: ninety seconds, or they navigate away.
    keeps: Boolean(candidate.keeps),
    at: new Date(now).toISOString(),
    candidateId: candidate.id,
    skillId: candidate.skill_id || null,
    title: candidate.title,
    startsOn: candidate.starts_on,
    tabId,
    visit,
    state: "open",
    // Who recognised this, and -- when it was the rig, from the shape of what
    // the operator has just done -- everything it would take to finish the job
    // from where they have got to. An arrival nudge has reached no step and
    // knows nothing typed, which is what `k: 0` and an empty `values` say.
    source: candidate.source || "backend",
    workflowId: candidate.workflow_id || null,
    k: candidate.k || 0,
    values: candidate.values || {},
    missing: candidate.missing || [],
    // Whether a run can go and find what nobody typed. The deployment's
    // answer, not this browser's: the connector is a deployment's and a panel
    // cannot know whether this one has a mailbox it may read.
    canFind: Boolean(candidate.can_find),
    // What this job's own boxes will not hold, by name, and what they hold
    // instead. Learnt by an earlier run that typed a value and watched the
    // browser silently keep a prefix of it, so the card can say so BEFORE the
    // press rather than the run saying so in the middle of a form.
    // The mail conversation this offer was read out of, where it was read out
    // of one. Sent back when the job starts, so a run that comes up short can
    // be found again by a reply to that mail.
    mailThread: candidate.thread || "",
    tooLong: candidate.too_long || {},
    parameters: candidate.parameters || [],
  };
}

/**
 * A call the operator's own browser just made.
 *
 * A write on the host this nudge is about means they did the task themselves
 * while it was asking. Nothing is said about that -- they did the thing, and a
 * panel congratulating them on it is a panel nobody wants open. A read is not
 * the task: looking something up is most of what anybody does on a page.
 */
export function onCall(nudges, { url, method }, now) {
  const host = page(url).split("/")[0];
  const mutating = /^(POST|PUT|PATCH|DELETE)$/i.test(method || "");
  if (!mutating || !host) return nudges;
  return nudges.map((nudge) =>
    nudge.state === "open" && nudge.startsOn.split("/")[0] === host
      ? { ...nudge, state: "by-hand", endedAt: now }
      : nudge,
  );
}

/** Time, and leaving. Both end an open nudge; neither touches one that ended.
 *
 * A `null` url means "wherever they are, this is only about the clock". The
 * beat sweeps that way: it is not looking at any one tab, and `""` is not an
 * answer to where the operator is -- read as a page it says everybody has
 * walked away, which ended every open nudge on the next beat and reported the
 * lot as expired while they were still standing on the page.
 */
export function sweep(nudges, { url, now, tabId }) {
  const here = url === null || url === undefined ? null : page(url);
  return nudges.map((nudge) => {
    if (nudge.state !== "open") return nudge;
    const old = nudge.expiresAt
      ? now >= nudge.expiresAt
      : now - Date.parse(nudge.at) >= LIFETIME_MS;
    // Kept: it goes quiet and stays askable. The one thing that changes is
    // that the panel can now say "three arrived while you were away", which is
    // the difference between a request nobody has answered and one nobody was
    // ever shown.
    if (nudge.keeps) return old && !nudge.missed ? { ...nudge, missed: true } : nudge;
    // Leaving the page is a fact about one tab. A navigation in tab B says
    // nothing about the offer open in tab A, so when the caller names the tab
    // only that tab's nudges can have left; a caller without one (the older
    // shape) keeps the whole-list reading.
    const thisTab = tabId === undefined || nudge.tabId == null || nudge.tabId === tabId;
    const left = here !== null && thisTab && here !== nudge.startsOn;
    return old || left ? { ...nudge, state: "expired", endedAt: now } : nudge;
  });
}

/**
 * "Not for this page", until the end of the day.
 *
 * A day rather than for ever: the page may matter to them next week even if it
 * did not this afternoon, and a permanent no taken from one press is a decision
 * nobody knew they were making.
 */
export function mute(muted, startsOn, now) {
  const midnight = new Date(now);
  midnight.setHours(24, 0, 0, 0);
  return { ...muted, [startsOn]: midnight.getTime() };
}
