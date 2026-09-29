// recognise.js
// Which proven job the operator has just started, decided from the last few
// gestures on the tab. Arithmetic on the shape the rig serves -- no model, no
// waiting for the once-a-minute flush -- so an offer can land on the second
// gesture, not a minute after it.
//
// Only a strict prefix is offered: a tail that already ends with the whole
// shape is a job the operator has finished, and there is nothing left to
// offer. So a two-step job is never offered by prefix -- arriving on its page
// covers that one.
//
// And only a UNIQUE prefix. Two proven jobs that begin with the same gestures
// are, for as long as the tail is that short, the same evidence -- naming one
// of them is a guess dressed as recognition. Nothing is offered until the tail
// separates them, which the next gesture usually does.

import { hostOfPage, page as screen } from "../panel/nudge.js";

// Long enough to hold a whole job: the corpus's jobs run 13 to 35 gestures,
// and a run started from a late step carries only the values the tail still
// holds. Twelve held the end of every job and forgot every value typed at
// its start -- measured 0 of 11 lifted by the end of the doing. Matching
// cost is a handful of string compares per shape per gesture either way.
export const K_TAIL = 40;
export const K_OFFER_AFTER = 2;

const key = (triple) => triple.join(" ");

/** How long a gesture stays in the tail. A prefix typed yesterday is not the
 * start of today's job, and a tail that outlives its session can complete a
 * shape with values nobody is looking at. Seconds, like the recorder's `at`. */
export const K_TAIL_TTL_S = 600;

/** The tail with one more gesture. Scrolls are noise in a prefix and are dropped;
 * anything older than the lifetime falls out first. */
export function tailWith(tail, entry) {
  if (entry.triple[1] === "anon|scroll") return tail;
  const fresh =
    typeof entry.at === "number"
      ? tail.filter((each) => typeof each.at !== "number" || entry.at - each.at <= K_TAIL_TTL_S)
      : tail;
  return [...fresh, entry].slice(-K_TAIL);
}

/** What a gesture with no `value` put into the form: the label of what it
 *  clicked. The WMS's dropdown is an ExtJS combo -- clicking the field opens a
 *  floating list and the operator clicks a row of it, so the choice is carried
 *  by that row's text and by no `value` anywhere. Ten of the forty parameters
 *  declared across both real stores are dropdowns, and each one reached the
 *  offer as an empty box however plainly the operator had just picked it.
 *
 *  Clicks only: a press or a scroll lands on a control whose text is the
 *  page's rather than the operator's answer. What keeps the rest honest is
 *  `valuesFrom`, which reads only the positions a served shape indexes -- and
 *  the miner indexes one only where that label matched a value the job was
 *  seen taking, so the click on Save is never anybody's answer. */
export function chosen(gesture) {
  if (gesture.kind !== "click" || gesture.target?.secret) return null;
  const text = typeof gesture.target?.text === "string" ? gesture.target.text.trim() : "";
  return text || null;
}

/** How far ahead of what it wants next a shape may look, so an operator can
 *  skip a step they did not need.
 *
 *  A recording contains the navigation the person who made it happened to
 *  need. Somebody already ON the customer types screen does not click the tab
 *  to get there, and before this they were not recognised as doing the job at
 *  all: measured on this deployment, 2026-09-15, an operator did `Create a
 *  Customer Type` end to end -- read the mail, pressed Add, typed the code and
 *  the description, saved -- and was never once asked, because the shape's
 *  second entry is a tab click they were already past.
 *
 *  Two, and small on purpose. This is the whole of the looseness: the shape may
 *  jump a couple of entries to meet what the operator actually did, and no
 *  further. */
export const K_MISSED = 2;

/** How much of `shape` the tail covers, and which tail entry answered each
 *  shape entry.
 *
 *  Not `endsWith`. That asked whether the tail's last k entries ARE the
 *  shape's first k, exactly and contiguously, which is true only of an
 *  operator who repeats a recording gesture for gesture. A real one skips the
 *  navigation they are already past and leaves noise behind them -- three
 *  clicks in one mail where the recording has one -- and either of those ended
 *  the match at k=0.
 *
 *  So the shape may skip up to `K_MISSED` entries to meet what came next, and
 *  the tail may carry anything the shape does not want. `at` records which
 *  tail entry answered which shape entry, because nothing downstream may
 *  assume the two line up any more: `valuesFrom` reads the operator's typed
 *  values out of this, and reading them off a position would show somebody
 *  values they never typed and start a run with them.
 *
 *  `ended` is whether the LAST thing the operator did took part: an offer is
 *  about what is happening now, not about a shape a tail brushed past ten
 *  gestures ago. */
export function covered(tail, shape) {
  const at = new Map();
  let want = 0;
  let matched = 0;
  let skipped = 0;
  let ended = false;
  let straying = 0;
  for (let j = 0; j < tail.length && want < shape.length; j++) {
    const here = key(tail[j].triple);
    if (matched > 0) straying += 1;
    ended = false;
    if (here === key(shape[want])) {
      at.set(want, j);
      want += 1;
      matched += 1;
      ended = true;
      straying = 0;
      continue;
    }
    // What the shape wants a little further on. The entries in between are
    // ones this operator did not need -- a navigation to a screen they were
    // already on is the case this exists for.
    const last = Math.min(want + K_MISSED, shape.length - 1);
    for (let ahead = want + 1; ahead <= last; ahead += 1) {
      if (key(shape[ahead]) !== here) continue;
      at.set(ahead, j);
      skipped += ahead - want;
      want = ahead + 1;
      matched += 1;
      ended = true;
      straying = 0;
      break;
    }
    // Anything else is the operator's own business and is passed over.
  }
  return { k: want, matched, skipped, ended, straying, at };
}

/** How many gestures in a row may advance nothing before an open offer is
 *  taken to be one the operator walked away from.
 *
 *  Noise is not divergence. An operator mid-job reads the mail again, clicks a
 *  column header, scrolls a list -- measured on the real trace, one such
 *  gesture sits between typing the code and clicking the description -- and
 *  before this the match ended at the first of them. But an offer that never
 *  withdraws is one still on screen while somebody does something else, so a
 *  RUN of them ends it.
 *
 *  Three. The nudge expires by itself in ninety seconds either way, which is
 *  what makes it safe to be generous here rather than strict. */
export const K_STRAY = 3;

/** Values typed so far for the parameters the prefix has reached. */
export function valuesFrom(tail, shape, at) {
  const values = {};
  const missing = [];
  for (const p of shape.parameters || []) {
    // `p.at` is an index into the SHAPE, and `at` says which tail entry
    // answered it. It used to be `tail[tail.length - k + p.at]`, which is the
    // same thing only while the two line up one for one -- and they no longer
    // do, because a match may skip a shape entry and pass over a tail one. Off
    // a position it would read somebody else's gesture and offer a value
    // nobody typed.
    const found = p.at === null || p.at === undefined ? undefined : at.get(p.at);
    const entry = found === undefined ? null : tail[found];
    // Blank is not a value. A field cleared, or one the gesture read as an
    // empty string, is a parameter nobody has answered yet -- counting it as
    // answered draws no box for it on the offer and lets the run start with
    // nothing in it.
    const said = entry && !entry.secret && entry.value != null ? String(entry.value).trim() : "";
    if (said) values[p.name] = entry.value;
    else missing.push(p.name);
  }
  return { values, missing };
}

/**
 * Whether the rig said this browser refused the job three times running and
 * is not to be asked again yet. The shape is still served -- the list stays
 * whole, and an open offer on the job can still tell diverging from
 * finishing -- so the declining happens here, and in the arrival nudge.
 */
export function resting(shape, now = Date.now()) {
  return Boolean(shape.quiet_until) && Date.parse(shape.quiet_until) > now;
}

/** The one job this tail is a prefix of, or null.
 *
 * There was an origin filter here -- a shape was skipped unless its FIRST step
 * was on the system the current gesture is on -- and on a job that stays on one
 * system it costs nothing, because every gesture has that origin. On a job that
 * spans two it is fatal: the operator reads the mail, moves to the WMS, and
 * from that gesture onward the shape whose first step is the mail is skipped on
 * every comparison. `Create Warehouse Equipment Type DDD` -- one mail gesture,
 * then twelve on the WMS -- was NEVER offered, and the customer-type job beside
 * it was only ever offered during its opening run of mail gestures.
 *
 * The filter was redundant as well as wrong. `endsWith` compares whole triples,
 * origin included, so the current gesture's origin is already required to equal
 * `shape.shape[k - 1][0]` -- the step the tail's last gesture aligns to. The
 * filter tested `shape.shape[0][0]` instead, which is the same index only when
 * k is 1, and k is never 1: it stops at `offer_after`, whose floor is 2.
 */
/** Whether this job's own screen is one the operator has left.
 *
 * **Every screen of this application shares its controls.** ExtJS names them
 * by component: `tabItem` is every tab, `addButton` every Add, `ok` every
 * confirm -- so the opening of "add a supplier" is, to a shape, the opening of
 * "add a client", "add an area" or "add a customer type". Nothing in a triple
 * tells them apart.
 *
 * Measured on the deployment 2026-09-20. The operator created three clients on
 * `#wm.config/wm.config.partners.clients` -- Partners tab, Add, fill, Save --
 * and was offered `Initiate Add Supplier`, whose shape opens `tabItem`, `ok`,
 * `addButton` and whose every gesture was recorded on the suppliers screen.
 * The offer was right about the gestures and wrong about the job.
 *
 * So a job is not offered while the operator is somewhere else in the same
 * application. `starts_on` is the url of the first gesture the job's first
 * step cites -- the screen it begins on -- and `page()` names both the way this
 * application addresses a screen: host and path and the fragment's route,
 * without the query, because the WMS routes on the fragment and puts a site
 * code in the query.
 *
 * Only within one application. A job that reads a request in a mailbox and
 * does it in the warehouse begins on a different origin from the one it is
 * recognised on, and that is this system's whole purpose rather than a
 * mismatch -- so a `starts_on` elsewhere says nothing here and is left alone.
 *
 * ponytail: the screen, not the control. Two jobs that genuinely begin on one
 * screen -- add a client and delete a client -- are still told apart only by
 * their triples, and on this platform those may not tell them apart at all.
 * The upgrade is to require an offer to rest on at least one control that is
 * not common currency across the tenant's jobs, which needs the whole shape
 * list to judge one shape and is a bigger change than the failure warrants.
 */
function elsewhereInTheSameApp(shape, url) {
  // `page()` reads a served URL and a worker-held screen alike; either one
  // missing is nothing to compare.
  const here = screen(url || "");
  const start = screen(shape.starts_on || "");
  if (!here || !start) return false;
  return hostOfPage(here) === hostOfPage(start) && here !== start;
}

export function match(tail, shapes, page = null) {
  let best = null;
  let shared = false;
  for (const shape of shapes) {
    if (!shape.shape?.length || resting(shape)) continue;
    if (elsewhereInTheSameApp(shape, page)) continue;
    // The rig may say a job is offered later than the default: its earlier
    // offers kept diverging at the default.
    const after = shape.offer_after ?? K_OFFER_AFTER;
    const reach = covered(tail, shape.shape);
    // `matched` and not `k`: `k` is how far INTO the shape the operator has
    // got and counts the entries a skip stepped over, which are entries they
    // never performed. What earns an offer is what they actually did.
    if (reach.matched < after) continue;
    // An offer is about the gesture that just happened. A tail that brushed
    // past this shape and then went elsewhere is not somebody starting it.
    if (!reach.ended) continue;
    // A strict prefix, as before: a tail that reached the end of the shape is
    // a job the operator finished, and there is nothing left to offer.
    if (reach.k >= shape.shape.length) continue;
    if (!best || reach.matched > best.matched) {
      best = {
        workflowId: shape.id,
        title: shape.title,
        k: reach.k,
        matched: reach.matched,
        at: reach.at,
        shape,
      };
      shared = false;
    } else if (reach.matched === best.matched) shared = true;
  }
  // Two shapes that matched the same number of the operator's gestures were
  // answered by the same gestures: the evidence is shared and the tail holds
  // nothing that says which job it is. Offer neither. More matched is not a
  // tie -- a shape that got further has been separated from the rest by the
  // very gestures that took it there.
  if (!best || shared) return null;
  const { values, missing } = valuesFrom(tail, best.shape, best.at);
  // The recorder times of the first and last gesture this match used. A Steel
  // takeover reads the operator's own uploads in this span, and nothing older:
  // a save from an earlier doing of the same job is not this one's.
  const used = [...best.at.values()];
  return {
    workflowId: best.workflowId,
    title: best.title,
    k: best.k,
    since: tail[Math.min(...used)].at,
    through: tail[Math.max(...used)].at,
    values,
    missing,
    parameters: (best.shape.parameters || []).map((p) => p.name),
  };
}

/**
 * Whether the tail has left the job's path. Carrying the job further is not
 * divergence: any prefix of the shape at least as long as the offer's still
 * counts as on the path, up to and including the whole of it.
 */
export function diverged(tail, offer, shapes) {
  const shape = shapes.find((s) => s.id === offer.workflowId);
  if (!shape) return true;
  // Carrying the job further is not divergence, so the test is whether the
  // tail still covers at least as much of the shape as the offer was made on.
  // Asked through `covered` rather than `endsWith` for the reason the offer
  // is: an operator who skipped a step they were already past has not left
  // the job, and calling that divergence withdrew the offer they were in the
  // middle of answering.
  const reach = covered(tail, shape.shape);
  // Backwards is impossible -- a tail only grows -- so what ends an offer is
  // the operator going quiet on this job: `K_STRAY` gestures in a row that
  // advanced none of it. A single stray one is the noise the match now passes
  // over on purpose, and calling that divergence withdrew the offer somebody
  // was in the middle of answering.
  return reach.k < offer.k || reach.straying > K_STRAY;
}
