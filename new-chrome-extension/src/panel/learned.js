// What was learned here, and how proven each job is.
//
// Learning is passive: nobody starts a demonstration. What the operator
// repeats on this system is mined into a job, and this card is the one place
// they see that it happened -- which jobs exist for the page in front of them,
// and how proven each is.
//
// Nothing here says a write waits for approval: a Steel run writes on its
// own from its first run (full autonomy). The ladder is how proven a job is
// and nothing else: it exists (learned), has run (ran with you), has held,
// and after `needed` live runs whose every write was verified by what the
// warehouse said, is proven. A job with a hundred held runs and nothing
// verified is not proven, and the count here is the same count the backend's
// verdict reads (`runs.proven`), so the two cannot disagree.
//
// Pure: jobs in, DOM out. What a press means is the caller's.

/** The rungs, in order, and whether a job has reached each. */
const RUNGS = [
  ["Learned", () => true],
  ["Ran with you", (runs) => runs.total > 0],
  ["Held", (runs) => runs.held > 0],
  ["Proven", (runs) => runs.earned],
];

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

/** The jobs offered on this host.
 *
 * Which jobs are real -- no chores, no mail-only doings, no fragments, one
 * copy per title -- is the backend's `offered`, the rule the chat offers by.
 * A backend that does not say is not guessed at: nothing is shown.
 */
export function learnedHere(jobs, host) {
  if (!host) return [];
  const here = host.toLowerCase();
  return (jobs || []).filter(
    (job) => job.offered === true && (job.systems || []).some((system) => hostOf(system) === here),
  );
}

/** One sentence for where a job stands, from counted facts only.
 *
 * A deployment that does not serve the count is not one to guess at: an older
 * backend has no `proven`, and "0 of 3" would be this panel inventing a number
 * about somebody's warehouse. It says what it knows instead. */
export function standing(runs) {
  if (runs.earned) return "Checked against the warehouse. Every write is still read back.";
  if (!runs.total) return "Not run yet.";
  if (!counts(runs)) return "Has run with you.";
  const proven = Math.min(runs.proven, runs.needed);
  return `${proven} of ${runs.needed} runs checked against the warehouse.`;
}

/** Whether this deployment says how far along a job is. */
export function counts(runs) {
  return Number.isFinite(runs?.proven) && Number.isFinite(runs?.needed) && runs.needed > 0;
}

/** The same count, in the few words a one-line row has room for. */
function checkedCount(runs) {
  if (runs.earned) return "proven";
  if (!runs.total) return "not run yet";
  if (!counts(runs)) return "has run";
  return `${Math.min(runs.proven, runs.needed)} of ${runs.needed} runs checked`;
}

/** The rungs, lit where the job stands: every rung it reached is done, and the
 * last one reached is the one it is on -- unless it reached them all. A rung
 * it has not reached is never lit, so "0 of 3 checked" cannot sit under a
 * glowing Proven (QA 2026-09-29): Proven is `earned`, the fact the count
 * beside it reads. */
function ladder(runs) {
  const list = document.createElement("ol");
  list.className = "ladder";
  const reached = RUNGS.map(([, did]) => Boolean(did(runs)));
  const at = reached.lastIndexOf(true);
  const all = reached.every(Boolean);
  RUNGS.forEach(([name], index) => {
    const rung = document.createElement("li");
    rung.className = "rung";
    rung.dataset.state = !reached[index]
      ? "todo"
      : index === at && !all
        ? "now"
        : "done";
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

function button(label, act, className = "quiet") {
  const press = document.createElement("button");
  press.type = "button";
  press.className = className;
  press.textContent = label;
  press.addEventListener("click", () => act(press));
  return press;
}

/** One job, as a line: its title (which opens its ladder), its checked count,
 * and Run it here. The ladder only under the job somebody opened. */
function jobLine(job, { opened, onRun, onReview, onOpen }) {
  const runs = { total: 0, held: 0, earned: false, ...job.runs };
  const isOpen = opened === job.id;
  const one = document.createElement("li");
  one.className = "job";
  one.dataset.workflowId = job.id;

  const line = document.createElement("div");
  line.className = "line";
  const title = button(job.title, () => onOpen?.(isOpen ? null : job.id), "title");
  title.setAttribute("aria-expanded", String(isOpen));
  const count = document.createElement("span");
  count.className = "count";
  count.textContent = checkedCount(runs);
  line.append(title, count, button("Run it here", (press) => onRun?.(job, press)));
  one.append(line);

  if (isOpen) {
    const says = document.createElement("p");
    says.textContent = standing(runs);
    one.append(says, ladder(runs));
    if (!runs.earned && counts(runs)) one.append(checked(runs));
    one.append(button("Review in console ↗", () => onReview?.(job)));
  }
  return one;
}

/**
 * One quiet row, or `null` when nothing was learned for this host.
 *
 * Learned jobs are standing facts, not things happening now, so Home gives
 * them one line (the user, 2026-09-29): "N jobs learned on this page ›".
 * `open` is whether that line is unfolded to a compact line per job, and
 * `opened` which job's ladder is showing -- both this window's, held by the
 * panel. `onToggle(open)`, `onOpen(id | null)`, `onRun(job, button)` and
 * `onReview(job)` are the caller's.
 *
 * Nothing here knows about a run in progress: while one drives this browser
 * the panel does not draw this row at all, the way an offer taken stops
 * being an offer. See `render` in `panel.js`.
 */
export function learned(
  jobs,
  { open = false, opened = null, onToggle, onOpen, onRun, onReview } = {},
) {
  if (!jobs?.length) return null;
  const card = document.createElement("section");
  card.className = "card learned";
  card.dataset.key = "learned";

  const head = button(
    `${jobs.length} ${jobs.length === 1 ? "job" : "jobs"} learned on this page ›`,
    () => onToggle?.(!open),
    "learned-head",
  );
  head.setAttribute("aria-expanded", String(open));
  head.setAttribute("aria-controls", "learned-list");
  card.append(head);

  if (open) {
    const list = document.createElement("ul");
    list.className = "learned-list";
    list.id = "learned-list";
    for (const job of jobs) list.append(jobLine(job, { opened, onRun, onReview, onOpen }));
    card.append(list);
  }
  return card;
}
