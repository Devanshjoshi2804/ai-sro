// What this browser knows between service-worker lifetimes.
//
// MV3 evicts the worker while it is idle, so nothing here may live in a module
// variable: every read goes to chrome.storage. `local` rather than `session`
// because `session` is cleared when Chrome restarts, and an operator who has to
// paste a credential every morning is an operator who turns the extension off.

// Which deployment this build belongs to. `make gen-deployment` writes that
// file; the default in the tree is a developer's own stack. A default, not a
// lock -- `sign-in` still takes whatever url was typed, so one build can be
// pointed elsewhere without regenerating anything.
//
// Imported as well as re-exported: `export ... from` would not bind the names
// here, and `apiUrl()` and `consoleUrl()` below read them.
import {
  DEFAULT_API_URL,
  DEFAULT_CONSOLE_URL,
} from "./deployment.generated.js";

export { DEFAULT_API_URL, DEFAULT_CONSOLE_URL };

const KEYS = {
  token: "sro.token",
  deviceId: "sro.deviceId",
  deviceSecret: "sro.deviceSecret",
  apiUrl: "sro.apiUrl",
  consoleUrl: "sro.consoleUrl",
  policy: "sro.policy",
  grants: "sro.grants",
  watches: "sro.watches",
  offers: "sro.offers",
  nudges: "sro.nudges",
  tails: "sro.tails",
  watched: "sro.watched",
  alwaysWatch: "sro.alwaysWatch",
  paused: "sro.paused",
  serverPaused: "sro.serverPaused",
  lastBeat: "sro.lastBeat",
  lastError: "sro.lastError",
  mailLooked: "sro.mailLooked",
  awaitingMail: "sro.awaitingMail",
  queueEpoch: "sro.queueEpoch",
  pendingBatch: "sro.pendingBatch",
  shotTimes: "sro.shotTimes",
  treeTimes: "sro.treeTimes",
  finishedRun: "sro.finishedRun",
  question: "sro.question",
  activeRun: "sro.activeRun",
  answer: "sro.answer",
  arrivals: "sro.arrivals",
  arrived: "sro.arrived",
  nearMisses: "sro.nearMisses",
  said: "sro.said",
  repaired: "sro.repaired",
};

// Whichever deployment this build belongs to. `make gen-deployment` writes it;
// the default in the tree is a developer's own stack. It is a *default*, not a
// lock: `sign-in` still takes whatever url was typed, so one build can be
// pointed somewhere else without regenerating anything.

/** Keys this extension used to write and no longer does.
 *
 * The rig's URL, the tenant's rig bearer and the rig's last refusal. They were
 * in `KEYS`, so `forget()` took them at sign-out; dropped from `KEYS` they
 * would sit in `chrome.storage.local` forever on every browser that ever had a
 * rig configured -- including the tenant's bearer, which is a credential this
 * extension no longer has any door to use. Removed once on update rather than
 * left for a sign-out that may never come; see `service-worker.js`'s
 * `onInstalled`. */
export const RETIRED_KEYS = ["sro.rigUrl", "sro.rigToken", "sro.rigRefusal"];

async function read(key, fallback = null) {
  const held = await chrome.storage.local.get(key);
  return key in held ? held[key] : fallback;
}

async function write(key, value) {
  await chrome.storage.local.set({ [key]: value });
}

export const state = {
  token: () => read(KEYS.token, ""),
  setToken: (token) => write(KEYS.token, token),

  deviceId: () => read(KEYS.deviceId, ""),
  setDeviceId: (id) => write(KEYS.deviceId, id),

  /** What this browser proves it is *itself* with, minted at registration.
   *
   * Beside the credential rather than anywhere cleverer, because there is
   * nowhere cleverer: `chrome.storage.local` is the extension's own origin and
   * no page can reach it -- a content script runs in the page's world but with
   * the extension's `chrome.storage`, and nothing here is ever handed to one
   * (`in-page.js` is given locators and gives back values). A page that could
   * read this could already read the credential, and the credential is the
   * larger loss: it is the whole tenant, this is one browser.
   *
   * Goes with everything else at sign-out -- it is in `KEYS`, so `forget()`
   * takes it -- which matters on a shared machine: left behind, it would be
   * the previous operator's device the next one's browser could speak as. */
  deviceSecret: () => read(KEYS.deviceSecret, ""),
  setDeviceSecret: (secret) => write(KEYS.deviceSecret, secret),

  apiUrl: () => read(KEYS.apiUrl, DEFAULT_API_URL),
  setApiUrl: (url) => write(KEYS.apiUrl, url.replace(/\/+$/, "")),

  /** Where the console is, for the panel to frame. A different origin from the
   * backend and not derivable from it -- one is an API, the other is a site,
   * and a deployment may put them anywhere. Empty means the panel shows only
   * what it can do itself, which is most of why it exists. */
  consoleUrl: () => read(KEYS.consoleUrl, DEFAULT_CONSOLE_URL),
  setConsoleUrl: (url) => write(KEYS.consoleUrl, url.replace(/\/+$/, "")),

  /** The tabs the operator asked to be watched, newest first. Each is
   * `{ tabId, host, since }`.
   *
   * Nothing is watched by default and nothing is inferred: what a person is
   * working in is a thing only that person knows, and every rule this system
   * tried to guess it by -- our own origins, the tenant's host list -- was
   * either wrong about a tab or silently right about the wrong one.
   *
   * A tab id, not a host: the operator points at the window in front of them,
   * and it keeps being that window when the application navigates to a
   * different host mid-task, which every SSO flow does. */
  /** Prompts this browser is holding, and the pages the operator said no to.
   *
   * Browser-held on purpose: a nudge lives about ninety seconds, only an answer
   * produces anything durable, and the thread is the record of what was decided
   * rather than of what was asked and ignored. */
  nudges: () => read(KEYS.nudges, []),
  setNudges: (nudges) => write(KEYS.nudges, nudges),

  /** The last question this browser asked of the systems, and what came back.
   *
   * One, not a list: a second question supersedes the first, the way a second
   * nudge does. An answer is worth holding across a worker eviction -- the
   * operator asked it seconds ago and is reading it -- and worth nothing the
   * next morning, which is what `askedAt` lets the panel decide. */
  answer: () => read(KEYS.answer, null),
  setAnswer: (answer) => write(KEYS.answer, answer),

  /** The pages this browser starts a job on, from the backend that keeps them.
   *
   * Held here for the same reason the watches are: the rule is evaluated where
   * the operator is, and a browser on a train should still do what its
   * operator told it to do on the page in front of them. */
  arrivals: () => read(KEYS.arrivals, []),
  setArrivals: (arrivals) => write(KEYS.arrivals, arrivals),

  /** Navigations this browser has already fired a rule on.
   *
   * In storage and not in a module variable, because MV3 evicts this worker
   * between events and a reload of the same page would otherwise start the
   * job again -- the worker having forgotten, not the operator having asked
   * twice. Capped: the visit id carries the moment it happened, so old ones
   * can never come back. */
  arrived: () => read(KEYS.arrived, []),
  setArrived: (visits) => write(KEYS.arrived, visits),

  /** Rules that almost fired, so a miss is not silent.
   *
   * `{ triggerId, terms, at }`, the operator's OWN words and never a word of
   * the mail -- which is what lets a near miss be reported at all (ADR 008).
   * Browser-held like the offers beside them: this is the browser it happened
   * in, and none of it is worth writing down anywhere else. */
  nearMisses: () => read(KEYS.nearMisses, []),
  setNearMisses: (misses) => write(KEYS.nearMisses, misses),

  // What this browser decided, waiting for the next beat to carry it up. In
  // storage rather than in a variable, because the service worker is evicted
  // between beats as a matter of course and the lines worth having are usually
  // the ones written just before it went. See `said.js`.
  said: () => read(KEYS.said, []),
  setSaid: (lines) => write(KEYS.said, lines),

  // Tabs this browser has already reloaded once to repair a half-installed
  // recorder. In storage because the guard is "once per tab, EVER" and the
  // worker holding it is evicted every few seconds. See `service-worker.js`.
  repaired: () => read(KEYS.repaired, []),
  setRepaired: (tabIds) => write(KEYS.repaired, tabIds),

  /** The last few gestures on each watched tab, by tab id.
   *
   * Here rather than in a module variable because MV3 evicts the worker between
   * events: a tail held in memory would be empty again by the second keystroke,
   * which is the exact moment a job becomes recognisable. */
  tails: () => read(KEYS.tails, {}),
  setTails: (tails) => write(KEYS.tails, tails),

  watched: () => read(KEYS.watched, []),
  setWatched: (tabs) => write(KEYS.watched, tabs),

  policy: () => read(KEYS.policy, null),
  setPolicy: (policy) => write(KEYS.policy, policy),

  /** Hosts this operator said may be watched after all, each `{ host,
   * expires_at }`.
   *
   * The tenant's exclusion list is what is observed by default, and webmail is
   * on it deliberately. A grant is the person in front of the screen deciding
   * otherwise about one host for one tab. Mirrored here from the server rather
   * than owned here: the backend refuses an excluded host whatever this says,
   * so the copy exists to keep the browser from queueing what would be thrown
   * away, not to decide anything.
   */
  grants: () => read(KEYS.grants, []),
  setGrants: (grants) => write(KEYS.grants, grants),

  /** The mail rules this browser holds, each `{ id, host, terms, values,
   * sender_at, subject_at }`.
   *
   * The rule, never a match. A watch is evaluated in the page and what it saw
   * is forgotten there; a list of mails this browser recognised would be the
   * one thing `ValueAt` went structural lengths to keep out of storage.
   *
   * Written here rather than kept in the worker because the watch content
   * script reads the change through `chrome.storage.onChanged` -- a page open
   * all day picks up a watch created this morning, and drops the lot when the
   * operator signs out. */
  watches: () => read(KEYS.watches, []),
  setWatches: (watches) => write(KEYS.watches, watches),

  /** The systems this operator has said to watch wherever they open.
   *
   * Hosts, not tabs. A tab id lives for as long as one tab, so a watch keyed
   * on one is a watch that ends when somebody closes a window, follows a link
   * into a new tab, or lets a run open its own -- and every one of those is
   * the same system doing the same work. Measured on the deployment,
   * 2026-09-17: a run drove a Blue Yonder tab it had opened itself while the
   * panel said "not watched", so nothing it did was evidence and the job
   * learnt nothing from having been done.
   */
  alwaysWatch: () => read(KEYS.alwaysWatch, []),
  setAlwaysWatch: (hosts) => write(KEYS.alwaysWatch, hosts),

  /** The mails this browser recognised and has not been answered about yet.
   *
   * This is the one thing here that came out of a mailbox, and this machine is
   * as far as it goes. It is not sent anywhere, and the backend has nowhere to
   * put it if it were: `POST .../matched` stores nothing and answers, which is
   * the whole reason the offer lives here. It goes when the operator presses
   * or dismisses, and `forget()` takes it with everything else at sign-out.
   *
   * In storage rather than the worker's memory for the ordinary reason: MV3
   * evicts the worker between the mail arriving and the operator looking at
   * the panel, and an offer that did not survive that is a mail nobody was
   * ever told about. */
  offers: () => read(KEYS.offers, []),
  setOffers: (offers) => write(KEYS.offers, offers),

  // Two pauses, deliberately separate. This one is the operator's and lives
  // only here; theirs is theirs to hold. The other arrives on a heartbeat and
  // is an administrator's.
  paused: () => read(KEYS.paused, false),
  setPaused: (paused) => write(KEYS.paused, paused),

  serverPaused: () => read(KEYS.serverPaused, false),
  setServerPaused: (paused) => write(KEYS.serverPaused, paused),

  lastBeat: () => read(KEYS.lastBeat, null),
  setLastBeat: (at) => write(KEYS.lastBeat, at),

  lastError: () => read(KEYS.lastError, ""),
  setLastError: (message) => write(KEYS.lastError, message),

  /** When the mailbox was last read for the jobs it asks for, and whether it
   * could be reached. Held here rather than in the panel because the panel is
   * one of several that may ask and is closed most of the day: the throttle
   * belongs to the browser, not to a window of it. */
  mailLooked: () => read(KEYS.mailLooked, null),
  setMailLooked: (looked) => write(KEYS.mailLooked, looked),

  /** The mail this browser has sent and is waiting on an answer to.
   *
   * In storage rather than in a variable for `said`'s reason -- the worker is
   * evicted between beats as a matter of course, and a person who sent a mail
   * five minutes ago is exactly who must still be told it is being watched
   * for. One at a time: the panel asks one question at a time, so there is
   * one outstanding request to wait on.
   */
  awaitingMail: () => read(KEYS.awaitingMail, null),
  setAwaitingMail: (waiting) => write(KEYS.awaitingMail, waiting),

  /** Distinguishes one lifetime of the event queue from the next.
   *
   * Batch ids are minted from IndexedDB row keys, and that counter restarts
   * whenever the store is recreated. Without something that does not restart
   * alongside it, the first batch after an evicted database would collide
   * with one the backend had already stored. */
  async queueEpoch() {
    const held = await read(KEYS.queueEpoch, "");
    if (held) return held;
    return state.newQueueEpoch();
  },
  async newQueueEpoch() {
    const minted = crypto.randomUUID().slice(0, 8);
    await write(KEYS.queueEpoch, minted);
    return minted;
  },

  /** The batch that has been sent at least once and not yet accounted for:
   * its id and the exact rows it named.
   *
   * Both, not just the id. `trim` can delete rows out from under a batch
   * between attempts, and a retry that quietly picked up a different set --
   * or minted a different id over an overlapping one -- is how the same
   * events got stored twice. */
  pendingBatch: () => read(KEYS.pendingBatch, null),
  setPendingBatch: (batch) => write(KEYS.pendingBatch, batch),

  /** When the last minute's screenshots were taken, so the policy's
   * per-minute cap survives this worker being evicted between two clicks --
   * which, at a human's pace, is most pairs of clicks. */
  shotTimes: () => read(KEYS.shotTimes, []),
  setShotTimes: (times) => write(KEYS.shotTimes, times),

  /** When accessibility trees were last taken, for their own per-minute cap.
   * Separate from the screenshots' budget: a tree is a round trip and some
   * JSON, a picture is a PNG, and sharing one counter would have whichever
   * happened first spend the other's allowance. */
  treeTimes: () => read(KEYS.treeTimes, []),
  setTreeTimes: (times) => write(KEYS.treeTimes, times),

  /** The last run this browser finished, and what it made -- `{ id, status,
   * derived, reversal, failure, at, wrongBecause? }`, or null. In storage
   * rather than a module variable for the reason this whole file exists: the
   * worker is evicted between the run finishing and the operator opening the
   * panel to look, and a card that forgot itself between those two moments is
   * a card that never existed as far as the operator is concerned. `status`,
   * `derived`, `reversal` and `failure` are copied in whole from `RunModel`
   * -- see `service-worker.js`'s own note on why they can only be asked for,
   * never computed here. `at` is this browser's own clock, read once when the
   * row is written, and is what `finishedRun()` below measures a lifetime
   * against. `wrongBecause` is set once `panel.js` has already told the
   * backend this run was wrong -- present so a `run-wrong` that already
   * landed is never sent twice (the backend refuses a second one outright),
   * while whatever is still left to do (starting a reversal) stays retryable
   * rather than the whole row being deleted the moment the record lands. */
  finishedRun: () => read(KEYS.finishedRun, null),

  /** The question this operator has not answered, read off their own
   * conversation on the beat. Stored rather than derived on every status: the
   * panel polls twice a second and the thread is a network round trip. */
  question: () => read(KEYS.question, null),
  setQuestion: (question) => write(KEYS.question, question),
  setFinishedRun: (run) => write(KEYS.finishedRun, run),

  /** The run this browser is currently -- or was most recently -- being asked
   * to do something for, and when it was last asked: `{ runId, at }`, or
   * null. The storage-backed mirror of `commands.js`'s own `latest`, written
   * on every run-bearing command; see `perform()` there for why a module
   * variable is not enough on its own. Nothing else `latest` carries belongs
   * here -- this exists only so a worker woken by the heartbeat alarm, with
   * no memory of `latest` at all, can still tell whether the run it was last
   * asked about has gone quiet. */
  activeRun: () => read(KEYS.activeRun, null),
  setActiveRun: (run) => write(KEYS.activeRun, run),

  async forget() {
    await chrome.storage.local.remove(Object.values(KEYS));
  },
};

/** Whether anything may be captured right now, and why not when it may not. */
export async function capturing() {
  const [token, deviceId, policy, paused, serverPaused] = await Promise.all([
    state.token(),
    state.deviceId(),
    state.policy(),
    state.paused(),
    state.serverPaused(),
  ]);
  if (!token) return { on: false, because: "no credential" };
  if (!deviceId) return { on: false, because: "not registered" };
  if (paused) return { on: false, because: "paused here" };
  if (serverPaused) return { on: false, because: "paused by an administrator" };
  if (!policy?.capture_enabled)
    return { on: false, because: "not enabled for this tenant" };
  return { on: true, because: "" };
}

/** How long the last finished run stays offerable, and why an hour rather
 * than the thirty seconds `performing()` uses to call a run quiet.
 *
 * That thirty seconds answers a different question -- "is this still
 * happening" -- and is right to be short: a stale "running" card is a lie
 * about the present. This is "can this still be taken back", and has to be
 * measured against the operator, not the run: they may not open the panel
 * again until after a break, and a card that vanished while they were away
 * would be silence pretending to mean "it was fine" when nobody ever looked.
 *
 * An hour is chosen as the defensible middle of an operator's day: long
 * enough to survive an ordinary break -- a delivery to unload, a meeting, a
 * late lunch -- short enough that the offer does not outlive the shift it was
 * made in. Past that point an undo is not "take this back", it is "reverse
 * work whatever came after it may already depend on", and the honest answer
 * is the same silence a run nobody ever touched gets: judged as it stands.
 */
const FINISHED_RUN_MS = 60 * 60_000;

/** The last run this browser finished, or null once it has aged out of being
 * offerable. Pruned lazily, on read, the same way an expired offer or a stale
 * `lastError` would be if this codebase kept those on a clock -- there is no
 * alarm dedicated to this, because the only thing that reads it is a panel
 * that is, by definition, open and asking right now.
 */
export async function finishedRun() {
  const held = await state.finishedRun();
  if (!held) return null;
  if (Date.now() - held.at > FINISHED_RUN_MS) {
    await state.setFinishedRun(null);
    return null;
  }
  return held;
}

/** What to do with `state.activeRun()`, given how long ago it was last
 * touched: `"wait"` (too recent to mean anything -- the run may just be
 * between two of its own steps), `"confirm"` (quiet long enough to be worth
 * asking the backend about), or `"stale"` (quiet for longer than a
 * `finishedRun` is ever allowed to stay offerable, so there is no point
 * asking -- the answer would be thrown away the moment it landed).
 *
 * Round 2 review: `state.activeRun()` surviving a worker eviction was the
 * whole point of storage-backing it, but nothing originally bounded how old
 * a survivor could be. Close the laptop before `RUN_QUIET_MS` lands and
 * reopen it a day later, and the first heartbeat after `onStartup` would
 * confirm a run that went quiet yesterday and write a brand-new hour of
 * "Undo that" for it -- exactly the staleness `FINISHED_RUN_MS` exists to
 * keep a *stored* `finishedRun` from having. An `activeRun` older than that
 * limit has already missed the same window, so `"stale"` is answered without
 * ever asking the backend.
 *
 * Pure and exported on its own so this boundary has a self-check that needs
 * neither `chrome.*` nor a real wait to run it -- `now` and `quietMs` are
 * passed in rather than read from `Date.now()` and `commands.js`'s
 * `RUN_QUIET_MS` directly for exactly that reason.
 */
export function activeRunAge(active, now, quietMs) {
  if (!active) return "wait";
  const quietFor = now - active.at;
  if (quietFor < quietMs) return "wait";
  if (quietFor > FINISHED_RUN_MS) return "stale";
  return "confirm";
}

/** What a finished-run row should become once `POST /runs/{id}/wrong` has
 * been accepted for it -- kept, amended, or dropped entirely. Pure and
 * exported on its own, separate from the two `chrome.storage` calls around
 * it in `service-worker.js`'s `run-wrong` case, so the one decision that
 * matters here has exactly one place to be right and a self-check that does
 * not need `chrome.*` to run it.
 *
 * Round 2 review: this used to be keyed on whether `held.reversal` existed,
 * on the theory that a run with nothing to undo has nothing left to do once
 * it is called wrong. That is true for "It's wrong -- I'll fix it", but that
 * button is offered on *every* succeeded run regardless of whether one also
 * has a reversal (see `panel.js`'s `finished()`), and keying on `reversal`
 * alone kept the row -- and "Undo that" -- alive for an hour after an
 * operator pressed "I'll fix it" on a run that happened to have one too.
 * Pressing "Undo that" then would reverse the very correction the card had
 * just told them to make by hand and asked us to learn from: worse than the
 * wrong record it replaces, because it destroys the evidence the operator
 * was just asked to produce, right after telling them the matter was closed.
 *
 * So this is keyed on which button was pressed, carried as `keepForRetry` --
 * true only from `panel.js`'s `undoRun`, which still has a second step left
 * after this one (starting the reversal, which can fail on its own) and
 * needs the row to retry it. `wasWrong` never sets it, whether or not the run
 * it is answering for happens to have a reversal: from that press on, the
 * operator's own hands are the correction, and the card ends.
 */
export function afterRunWrong(held, because, keepForRetry) {
  return keepForRetry ? { ...held, wrongBecause: because } : null;
}
