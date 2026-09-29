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

import { screenOf } from "../background/shape.generated.js";

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

/** The screen, without its scheme: `screenOf` -- the generated twin of the
 * backend's `screen_of`, which keys a job's steps and serves `starts_on` -- with
 * `https://` read into anything that has none and dropped from what comes out.
 *
 * One definition, so the page a nudge, a rule and the recogniser compare is
 * the screen the backend keyed: host and path, no query (where a warehouse
 * system puts session ids and timestamps), and the fragment's route, because
 * Blue Yonder routes on the fragment and without it every config screen was
 * `.../portal` (QA 2026-09-29). Idempotent, so `page(page(x))` is `page(x)`.
 */
export function page(url) {
  const said = String(url || "");
  return screenOf(said.includes("://") ? said : `https://${said}`).replace(/^[^:]*:\/\//, "");
}

/** The host a `page()` names. */
export const hostOfPage = (screen) => screen.split(/[/#]/)[0];

/**
 * The task worth offering here, or `null`.
 *
 * `visit` identifies this navigation, not this page: asking once per visit
 * means an operator who comes back in the afternoon is asked again, and one who
 * is standing on the page is asked once.
 */
export function shouldFire({ url, visit, candidates, nudges }) {
  const here = page(url);
  if (!here) return null;
  // One at a time, anywhere. Two open at once is a queue, and a queue of
  // prompts is the thing this design exists to not be.
  if (nudges.some((nudge) => nudge.state === "open")) return null;
  if (nudges.some((nudge) => nudge.startsOn === here && nudge.visit === visit)) return null;

  const offerable = candidates.filter(
    (candidate) =>
      candidate.starts_on === here &&
      // Proven enough to offer: taught by somebody, done often enough to be
      // a habit, or -- for a job the rig serves -- already run and held.
      (candidate.source === "rig" || candidate.skill_id || candidate.times_seen >= 3),
  );
  // A rule is the operator saying which job this page is for.
  const rule = offerable.find((candidate) => candidate.rule);
  if (rule) return rule;
  // Otherwise the address has to name one job. Two that start here are the
  // tie `match` refuses: offering either is a guess, and on QA 2026-09-29 the
  // guess was Delete for somebody pressing Add. The gestures decide instead.
  const jobs = new Set(offerable.map((candidate) => candidate.workflow_id || candidate.id));
  return jobs.size === 1 ? offerable[0] : null;
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
    // The span of the operator's own gestures the match used, so a Steel run
    // that takes the job over reads only this doing's uploads. Null for an
    // offer that was not made from gestures.
    since: candidate.since ?? null,
    through: candidate.through ?? null,
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
    // The offer's own name where it already has one: the reply's question or
    // the mail's key. A press sends it, so a card and a yes are one run.
    offer: candidate.offer || "",
    // What the request was called, so a conversation about it can name which.
    mailSubject: candidate.subject || "",
    tooLong: candidate.too_long || {},
    // What the request asked for that this job has no parameter for.
    //
    // Mapped here since 2026-09-22 and not before: the worker has passed it
    // for as long as the card has drawn it, and this function -- which is what
    // turns an offer into the card -- dropped it in between. So "This job
    // cannot set Department" has been rendering for every offer except the
    // one kind that can carry it, and the renderer's own test passed because
    // it builds its nudge by hand.
    unasked: candidate.unasked || [],
    // And what it could ALSO set, which nothing has to answer. On the card
    // because a mail supplying everything required produces no question, and
    // the question is the only other place these are offered.
    offers: candidate.offers || [],
    // Who the operator sent this request to, when it was somebody else.
    sentTo: candidate.sent_to || [],
    parameters: candidate.parameters || [],
    // What pressing this would WRITE, read off the job's own evidence: one
    // entry per writing step, `{does, record, on}`. The card names the values
    // it holds and what it cannot take; without this it never names the act,
    // and "yes" is a press against something nobody described.
    writes: candidate.writes || [],
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
  const host = hostOfPage(page(url));
  const mutating = /^(POST|PUT|PATCH|DELETE)$/i.test(method || "");
  if (!mutating || !host) return nudges;
  return nudges.map((nudge) =>
    nudge.state === "open" && hostOfPage(page(nudge.startsOn)) === host
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
export const KEPT_MS = 24 * 60 * 60 * 1000;
/** How long a request nobody answered stays on the panel.

 * A day, measured from when it arrived rather than from the end of that day:
 * a mail at 23:50 would otherwise get ten minutes. Long enough that anything
 * arriving while somebody was on the floor is still there when they come back,
 * short enough that a Monday morning panel is about Monday.
 */

export function sweep(nudges, { url, now, tabId }) {
  const here = url === null || url === undefined ? null : page(url);
  return nudges.map((nudge) => {
    if (nudge.state !== "open") return nudge;
    const old = nudge.expiresAt
      ? now >= nudge.expiresAt
      : now - Date.parse(nudge.at) >= LIFETIME_MS;
    // Kept: it goes quiet and stays askable, for a day. The quiet is what lets
    // the panel say "three arrived while you were away", which is the
    // difference between a request nobody has answered and one nobody was ever
    // shown.
    //
    // And then it goes. `keeps` was written to mean "a request nobody answered
    // has not stopped being a request", which is true for an afternoon and not
    // for a week: measured on the deployment 2026-09-18, thirteen cards stacked
    // in one panel, six of them from the day before, and the only thing between
    // an operator and an unbounded column was pressing No thanks on each.
    //
    // Nobody acts on Tuesday's card on Thursday. The request is still in the
    // mail if it mattered, and the mail is where somebody would go looking --
    // so what a stale card costs is the panel's credibility, and what letting
    // it go costs is nothing.
    if (nudge.keeps) {
      if (!old) return nudge;
      const dead = now - Date.parse(nudge.at) >= KEPT_MS;
      if (dead) return { ...nudge, state: "expired", endedAt: now };
      return nudge.missed ? nudge : { ...nudge, missed: true };
    }
    // Leaving the page is a fact about one tab. A navigation in tab B says
    // nothing about the offer open in tab A, so when the caller names the tab
    // only that tab's nudges can have left; a caller without one (the older
    // shape) keeps the whole-list reading.
    const thisTab = tabId === undefined || nudge.tabId == null || nudge.tabId === tabId;
    const left = here !== null && thisTab && here !== nudge.startsOn;
    return old || left ? { ...nudge, state: "expired", endedAt: now } : nudge;
  });
}
