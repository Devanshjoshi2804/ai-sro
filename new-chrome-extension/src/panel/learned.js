// What was learned here, and how far each job is toward doing it alone.
//
// Learning is passive: nobody starts a demonstration. What the operator
// repeats on this system is mined into a job, and this card is the one place
// they see that it happened -- which jobs exist for the page in front of them,
// and where each stands on the way to writing without asking.
//
// The way is the rig's own and nothing else: a job exists (learned), has run
// (ran with you), has held, and after `needed` live runs whose every write was
// verified by what the warehouse said, writes on its own. A job with a hundred
// held runs and nothing verified has earned nothing, and the count here is the
// same count the backend's verdict reads (`runs.proven`), so the two cannot
// disagree.
//
// Pure: jobs in, DOM out. What a press means is the caller's.

/** The rungs, in order, and whether a job has reached each. */
const RUNGS = [
  ["Learned", () => true],
  ["Ran with you", (runs) => runs.total > 0],
  ["Held", (runs) => runs.held > 0],
  ["On its own", (runs) => runs.earned],
];

/** How many learned jobs one card lists. The rest are in the console. */
export const K_SHOWN = 3;

/** The host a mined job's `systems` entry names.
 *
 * They are stored as whole origins -- `https://bf56-kms-wms-web-np2.jdadelivers.com`
 * -- and the tab beside the panel is a bare hostname. Compared as they are,
 * nothing ever matched and this card never appeared on any system the tenant
 * has. Older rows hold a bare host, so both shapes are read.
 */
export function hostOf(system) {
  const said = String(system || "").trim();
  if (!said) return "";
  try {
    return new URL(said.includes("://") ? said : `https://${said}`).hostname.toLowerCase();
  } catch {
    return said.toLowerCase();
  }
}

/** The jobs whose systems include this host, one per job.
 *
 * Mining produces more than one workflow for the same work -- the deployment
 * holds three called "Log in to Keycloak" and three called "Reply to Email" --
 * and a card listing each of them asks the operator to choose between things
 * that have the same name and no visible difference. The one that has run
 * most, and among equals the one furthest along, is the one a press should
 * start; the rest are in the console where their ids are readable.
 */
export function learnedHere(jobs, host) {
  if (!host) return [];
  const here = host.toLowerCase();
  const mine = (jobs || []).filter((job) =>
    (job.systems || []).some((system) => hostOf(system) === here),
  );
  const byName = new Map();
  for (const job of mine) {
    const name = String(job.title || "").trim().toLowerCase();
    const seen = byName.get(name);
    if (!seen || furtherOn(job, seen)) byName.set(name, job);
  }
  return [...byName.values()];
}

/** Whether `job` is the one to offer over `than`.
 *
 * A step that types a credential first, then run more, then proved more, then
 * earned. Never the newest -- a job mined this morning and never run is not
 * the one a press should start.
 *
 * The credential comes first because the alternative is a sign-in that cannot
 * sign in. Two readings of one login differ by whether the operator typed
 * their password or the browser filled it: the one where nobody typed has no
 * step for it, and on a machine that does not fill it in, it presses Sign In
 * with the field empty. The one that has run MORE is often that one, because
 * it is the one that runs on a browser where autofill does the work.
 */
function furtherOn(job, than) {
  const rank = ({ runs = {}, types_a_credential: credential = false }) => [
    credential ? 1 : 0,
    runs.total || 0,
    runs.proven || 0,
    runs.earned ? 1 : 0,
  ];
  const mine = rank(job);
  const theirs = rank(than);
  // Compared as numbers, place by place. Joined into a string, "10,0,0" sorts
  // below "9,0,0" and the job with ten runs loses to the one with nine.
  for (let i = 0; i < mine.length; i += 1) {
    if (mine[i] !== theirs[i]) return mine[i] > theirs[i];
  }
  return false;
}

/** One sentence for where a job stands, from counted facts only.
 *
 * A deployment that does not serve the count is not one to guess at: an older
 * backend has no `proven`, and "0 of 3" would be this panel inventing a number
 * about somebody's warehouse. It says what it knows instead. */
export function standing(runs) {
  if (runs.earned) return "Writes on its own now. Every write is still read back.";
  if (!runs.total) return "Not run yet. Its writes ask you first.";
  if (!counts(runs)) return "Its writes ask you first.";
  const needed = runs.needed;
  const proven = Math.min(runs.proven, needed);
  return (
    `${proven} of ${needed} runs checked against the warehouse.` +
    " Its writes ask you first until then."
  );
}

/** Whether this deployment says how far along a job is. */
export function counts(runs) {
  return Number.isFinite(runs?.proven) && Number.isFinite(runs?.needed) && runs.needed > 0;
}

function ladder(runs) {
  const list = document.createElement("ol");
  list.className = "ladder";
  const reached = RUNGS.map(([, did]) => Boolean(did(runs)));
  // The rung being worked toward is the first not yet reached.
  const next = reached.indexOf(false);
  RUNGS.forEach(([name], index) => {
    const rung = document.createElement("li");
    rung.className = "rung";
    rung.dataset.state = reached[index] ? "done" : index === next ? "now" : "todo";
    rung.textContent = name;
    list.append(rung);
  });
  return list;
}

function checked(runs) {
  const needed = runs.needed;
  const proven = Math.min(runs.proven, needed);
  const bar = document.createElement("div");
  bar.className = "clean";
  bar.setAttribute("aria-label", `${proven} of ${needed} checked runs`);
  for (let i = 0; i < needed; i += 1) {
    const segment = document.createElement("i");
    if (i < proven) segment.dataset.on = "true";
    bar.append(segment);
  }
  return bar;
}

/**
 * The card, or `null` when nothing was learned for this host.
 *
 * `onReview(job)` for the console. Nothing here runs a job: a job is run by
 * asking for it in the conversation, and the backend starts it.
 *
 * Nothing here knows about a run in progress: while one is watched the panel
 * does not draw this card at all. See `render` in `panel.js`.
 */
export function learned(jobs, { onReview } = {}) {
  if (!jobs?.length) return null;
  const card = document.createElement("section");
  card.className = "card learned";
  card.dataset.key = "learned";
  // Ember while something here has not earned its writes yet, because that is
  // the thing worth the operator's attention; quiet once all of it has.
  if (jobs.some((job) => !job.runs?.earned)) card.dataset.tone = "live";

  const eyebrow = document.createElement("p");
  eyebrow.className = "eyebrow";
  eyebrow.textContent = "Learned from what you do here";
  card.append(eyebrow);

  jobs.slice(0, K_SHOWN).forEach((job) => {
    const runs = { total: 0, held: 0, earned: false, ...job.runs };
    const one = document.createElement("div");
    one.className = "job";
    one.dataset.workflowId = job.id;

    const title = document.createElement("h3");
    title.textContent = job.title;
    const says = document.createElement("p");
    says.textContent = standing(runs);
    one.append(title, says, ladder(runs));
    if (!runs.earned && counts(runs)) one.append(checked(runs));

    const row = document.createElement("div");
    row.className = "row";
    const review = document.createElement("button");
    review.type = "button";
    review.className = "quiet";
    review.textContent = "Review in console ↗";
    review.addEventListener("click", () => onReview?.(job));
    row.append(review);
    one.append(row);
    card.append(one);
  });

  if (jobs.length > K_SHOWN) {
    const more = document.createElement("p");
    more.className = "note";
    more.textContent = `${jobs.length - K_SHOWN} more learned here, in the console.`;
    card.append(more);
  }
  return card;
}
