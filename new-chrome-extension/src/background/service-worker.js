// Registration, heartbeat, and the truthful badge.
//
// Nothing here holds state in a module variable: MV3 evicts this worker while
// it is idle and every wake-up starts from storage.

import { api, ApiError } from "./api.js";
import { alsoWatch, alwaysWatched, hostOf } from "./always.js";
import { questionIn } from "./asking.js";
import { waitBeforeLooking } from "./looking.js";
import * as channel from "./channel.js";
import {
  abort,
  isDriving,
  noteDriven,
  performing,
  RUN_QUIET_MS,
} from "./commands.js";
import { MAX_SAID, narrate, said } from "./said.js";
import { serially } from "./serially.js";
import * as queue from "./queue.js";
import { redactUrl } from "../content/sensitivity.module.js";
import {
  allowsHost,
  applyPolicy,
  applyWatches,
  hostMatches,
  injectInto,
  injectIntoWatched,
  unregister,
} from "./scripts.js";
import {
  LIFETIME_MS,
  endOfDay,
  fire,
  onCall,
  page as pageOf,
  shouldFire,
  sweep,
} from "../panel/nudge.js";
import { decideOffer } from "./offering.js";
import { chosen, resting, tailWith } from "./recognise.js";
import { tripleOf } from "./shape.generated.js";
import { hideNudge, showNudge } from "./showing.js";
import { capture } from "./shots.js";
import { noteFinished } from "./finishing.js";
import {
  activeRunAge,
  afterRunWrong,
  capturing,
  finishedRun,
  RETIRED_KEYS,
  state,
} from "./state.js";
import {
  release as releaseTree,
  releaseAll,
  takeTree,
  takeTreeSoon,
} from "./trees.js";
import { flush } from "./upload.js";

const BEAT = "sro-heartbeat";
const FLUSH = "sro-flush";
const EVERY_MINUTES = 1;

const VERSION = chrome.runtime.getManifest().version;

// The toolbar button opens the panel rather than a popup: everything this
// extension has to say is about the tab you are looking at, and a popup closes
// the moment you look at it.
void chrome.sidePanel
  ?.setPanelBehavior({ openPanelOnActionClick: true })
  .catch(() => {});

/** Everything the rig settings wrote, taken off this browser -- one of the
 * three is the tenant's bearer, and a credential nothing can spend any more is
 * one nothing should still hold.
 *
 * On both hooks rather than only `onInstalled`, and not awaited on either. MV3
 * tears this worker down at any await point with no lock and no rollback, so a
 * removal that ran only on the update that shipped it would be lost for good on
 * a browser evicted mid-call -- `onInstalled` does not fire again until the
 * next update, which may never come. Removing a key that is not there is free,
 * so the cheap fix is a second occasion rather than a ledger: every browser
 * launch tries again until one of them lands. Harmless on a fresh install,
 * where there is nothing to remove. */
const dropRetired = () => void chrome.storage.local.remove(RETIRED_KEYS);

chrome.runtime.onInstalled.addListener(() => {
  dropRetired();
  chrome.alarms.create(BEAT, { periodInMinutes: EVERY_MINUTES });
  chrome.alarms.create(FLUSH, { periodInMinutes: EVERY_MINUTES });
  void settle();
});

chrome.runtime.onStartup.addListener(() => {
  dropRetired();
  chrome.alarms.create(BEAT, { periodInMinutes: EVERY_MINUTES });
  chrome.alarms.create(FLUSH, { periodInMinutes: EVERY_MINUTES });
  void settle();
});

/** A new version, held until there is a gap to land it in.
 *
 * An extension update is not free to whoever is mid-task when it lands. The
 * worker is torn down and rebuilt, so a run this browser is driving stops
 * between two steps -- a half-made record in a warehouse -- and a
 * demonstration being recorded loses its `chrome.debugger` attachment, which
 * means the banner goes, the events stop, and the recording is never sealed.
 * Neither is recoverable afterwards, and neither is anything the operator did
 * wrong.
 *
 * Registering this listener is what buys the choice: with one attached Chrome
 * holds the update instead of installing it at the first opportunity, and
 * `chrome.runtime.reload()` is how this worker says "now is a good moment".
 *
 * What is deliberately NOT gated on: a page with a half-filled form. An update
 * does not reload anybody's tab -- the form is still there afterwards. What it
 * does is leave every open tab recording half of what it sees, and the repair
 * for THAT already asks the page whether it is holding anything before
 * reloading it. Gating here as well would be the same question asked twice,
 * and the second one would hold an update back for a form nothing is going to
 * disturb.
 *
 * The version lives in a module variable, which MV3 evicts -- and that is the
 * correct place for it. A worker that has been evicted is a browser with
 * nothing in flight, which is exactly when Chrome installs a held update on
 * its own. Losing this is the update landing in the gap by another route.
 */
let updateWaiting = null;

chrome.runtime.onUpdateAvailable?.addListener((details) => {
  updateWaiting = details?.version || "a new version";
  void landTheUpdate();
});

/** Install it, if nothing would be lost by restarting right now.
 *
 * Returns whether it went. Nothing after `chrome.runtime.reload()` runs.
 */
async function landTheUpdate() {
  if (!updateWaiting) return false;
  // A run is a form being filled in a warehouse, a step at a time.
  if ((await state.activeRun())?.runId) return false;
  // Said before the restart, not after: there is no after.
  await narrate(
    `version ${updateWaiting} was installed while nothing was in flight`,
  );
  // Asked for once. Nothing below this line runs in a browser that restarts,
  // and a browser that somehow does not is one Chrome installs the held
  // update in anyway the moment this worker next idles -- which is the
  // fallback this whole arrangement is a refinement of, not a race with it.
  updateWaiting = null;
  chrome.runtime.reload();
  return true;
}

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === BEAT) {
    void beat();
    // And a held update, once a minute, because the gap it is waiting for is
    // the end of a run or the end of a demonstration -- and hooking both of
    // those in every place they can end is a list that the next one to be
    // added will not be on.
    void landTheUpdate();
    // The one trigger that does not need the panel open. A run performed and
    // then left alone -- the ordinary case, not the exception -- goes quiet in
    // a worker that idles out long before an operator comes back to look, and
    // `commands.js`'s own `latest` dies with it. This alarm fires on its own
    // schedule regardless, off the storage-backed mirror `perform()` writes,
    // which is the only thing here that survives that eviction.
    void checkFinishing();
    // And the same for a rig run: the timer chain dies with the worker, so
    // without this a run parked on an approval across an eviction would never
    // be asked about again. Self-guarding -- it returns at once unless the
    // active run is the rig's.
    void pollRigRun();
    // A prompt that outlives the task it offered is a prompt that was ignored.
    // On the beat rather than a timer of its own: this worker is evicted
    // between events, and a `setTimeout` for ninety seconds is one the platform
    // is free to never run.
    void sweepNudges();
    // And the conversation, for a question nobody has answered.
    //
    // A run that could not find a value writes one into this operator's own
    // thread and ends. The panel used to walk them to it off the FINISHED RUN,
    // which is one slot: on 2026-09-17 a later run took that slot ninety
    // seconds after the question was written, and the question sat unanswered
    // for the rest of the morning. The thread cannot be swept, and this is
    // where it is read -- on the beat, so it is found while the panel is shut.
    void lookForAQuestion();
    // And the mailbox, for the jobs it is asking for.
    //
    // Here rather than on the panel's own tick, which is where it started: a
    // request that arrived while the panel was closed is exactly the one
    // somebody needs to find waiting when they open it, and a look that only
    // runs while somebody is watching cannot produce one. The beat is a minute
    // and so is the look's own throttle, so this asks about as often as it
    // acts.
    void lookInTheMail();
  }
  if (alarm.name === FLUSH) void flushQueue();
  // Every wake-up re-dials. Chrome evicts this worker while it is idle and the
  // socket goes with it, so without this a quiet browser is an unreachable one
  // until the operator happens to click something.
  void channel.settle();
});

// Page lifecycle, straight from the platform -- no content script needed for
// this, and nothing rides on a page having one registered at all.
// ponytail: main frame only; add per-iframe navigation if a miner needs it.
chrome.webNavigation.onCommitted.addListener((d) => {
  if (d.frameId !== 0) return;
  // A fresh document gets a fresh patch and a handshake at `document_start`,
  // which is the only moment one can safely happen -- so whatever was wrong
  // with the last document is not wrong with this one.
  halfDeaf.delete(d.tabId);
  // Except when this document IS the repair.
  //
  // `chrome.tabs.reload` commits like any other navigation, so the reload the
  // worker performed arrived here and forgot the claim it had just made. The
  // fresh page reported the same half-installed recorder to a worker that had
  // never heard of it, which reloaded it, which committed, which forgot --
  // the loop this guard exists to stop, driven by the guard itself. Measured
  // on the deployment 2026-09-20: two tabs, twenty-three reloads, one minute.
  //
  // `reload` covers the operator pressing it too, which costs that tab its
  // repair for a page it is already on. That is the conservative side: a
  // repair not offered goes on the card and waits to be asked, and a repair
  // offered forever is a browser nobody can use.
  if (d.transitionType !== "reload") void forgetRepaired(d.tabId);
  // A system the operator watches everywhere is watched here too, whoever
  // opened this tab -- them, a link, or a run opening one for itself. On the
  // deployment, 2026-09-17, a run drove a tab it had opened while the panel
  // said "not watched", and nothing it did was evidence.
  void watchIfAlways(d.tabId, d.url);
  void pageEvent("navigated", d.tabId, d.url, d.timeStamp);
  // `navigationId` is not in this event, so the visit is the tab and the moment
  // it committed. Same property either way: one nudge per navigation rather
  // than one per page for ever.
  void considerNudge(d.tabId, d.url, `${d.tabId}:${d.timeStamp}`);
  // And the rule the operator made by standing here. Same visit id, so a rule
  // fires once per navigation rather than once per page for ever, and the
  // nudge for this page is superseded by the run it starts.
  void considerArrival(d.tabId, d.url, `${d.tabId}:${d.timeStamp}`);
});
chrome.webNavigation.onCompleted.addListener((d) => {
  if (d.frameId === 0) void pageEvent("loaded", d.tabId, d.url, d.timeStamp);
});
chrome.webNavigation.onCreatedNavigationTarget.addListener((d) => {
  void popupEvent(d);
});

// -- offering to do the one they are about to do -----------------------------

/** Cached per host, because a navigation happens far more often than a task is
 * mined. Five minutes is well inside the quarter-hour sweep that changes it. */
const CANDIDATES_FRESH_MS = 300_000;
const knownHere = new Map();

async function candidatesFor(host) {
  // The rig's jobs, and nothing else.
  //
  // This used to be the rig's jobs plus the mining pipeline's candidates,
  // which offered to TEACH a skill from recordings. That is not the system
  // this browser drives: an operator pressed one of those offers for work the
  // rig already held as a seven-step job and got "the doings differ too much
  // for me to be sure". That pipeline has since been removed from the
  // backend as well.
  const held = knownHere.get(host);
  if (held && Date.now() - held.at < CANDIDATES_FRESH_MS) return held.list;
  const proven = rigArrivals(await shapesFor(), host);
  knownHere.set(host, { at: Date.now(), list: proven });
  return proven;
}

/** The rig's jobs that start on this host, as arrival candidates.
 *
 * `k: 0` and nothing typed, because arriving somewhere is not doing anything:
 * every parameter is still missing, which is exactly what makes this the weaker
 * of the two offers and the one a prefix match replaces.
 */
function rigArrivals(shapes, host) {
  return shapes
    .filter(
      (shape) =>
        shape.starts_on && shape.starts_on.split("/")[0].split(":")[0] === host,
    )
    .filter((shape) => !resting(shape))
    .map((shape) => {
      const names = (shape.parameters || []).map((p) => p.name);
      return {
        id: shape.id,
        title: shape.title,
        starts_on: shape.starts_on,
        source: "rig",
        workflow_id: shape.id,
        k: 0,
        values: {},
        missing: names,
        parameters: names,
        // What pressing it would write, so the card can say it before the
        // press. Served with the shape, which is where the evidence is read.
        writes: shape.writes || [],
      };
    });
}

/** Whether to say "you have done this here before", and saying it.
 *
 * Fired here rather than in the panel because the panel may be closed, which is
 * exactly when this matters: the operator is looking at the page, about to do
 * the work themselves.
 */
async function considerNudge(tabId, url, visit) {
  try {
    if (!(await isWatched(tabId))) return;
    const host = hostOf(url || "");
    if (!host) return;
    // Asked before the lock is taken, because it can be a call to the backend
    // and the gesture path queues behind the same lock. Everything after this
    // is arithmetic over storage.
    const candidates = await candidatesFor(host);
    const busy = performing();
    // Read, decide and write as one. Two navigations landing together each read
    // a list without the other's nudge in it and each wrote it back, and the
    // second write took the first nudge with it.
    const candidate = await serially(async () => {
      const now = Date.now();
      // Anything the operator has walked away from ends here, before anything
      // new is offered: leaving the page is one of the three ways a nudge ends.
      const before = await state.nudges();
      const swept = sweep(before, { url, now, tabId });
      reportEndings(before, swept);
      const fired = shouldFire({
        url,
        visit,
        candidates,
        nudges: swept,
        performing: busy,
      });
      if (!fired) {
        await state.setNudges(swept.slice(0, MAX_NUDGES));
        return null;
      }
      await state.setNudges(
        [fire(fired, now, { tabId, visit }), ...swept].slice(0, MAX_NUDGES),
      );
      return fired;
    });
    if (candidate) await showNudge(tabId, candidate.title);
  } catch {
    // A tab that closed mid-navigation, or a browser with no credential yet.
    // Nothing offered is the safe answer and the quiet one.
  }
}

/** The rule this operator made by standing on this page: fire it, once.
 *
 * The other half of the wire. `considerNudge` above offers -- "you have done
 * this here before, want me to?" -- and this one acts, because somebody
 * already answered that question in advance. The two are deliberately separate
 * functions over the same navigation: an offer is a question and a rule is an
 * instruction, and a single path that did both would make the difference a
 * flag.
 *
 * What it will not do, in the order it refuses:
 *
 * - While this browser is paused, or the tenant has paused it. A rule is not
 *   an exception to the badge saying nothing is happening.
 * - While a run is already performing here. Two runs in one window is the
 *   panel driving over itself.
 * - Twice for one navigation. The visit id is the tab and the moment it
 *   committed, kept in storage because this worker is evicted between events
 *   and a forgotten fire is indistinguishable to the operator from a second
 *   one they never asked for.
 *
 * The page is matched HERE and again by the backend against the rule's own
 * page. This side has to match, because it is the only thing that knows where
 * its operator is; the other side has to, because a browser that got it wrong
 * would start a live run on a page nobody chose.
 */
async function considerArrival(tabId, url, visit) {
  try {
    const [deviceId, paused, serverPaused] = await Promise.all([
      state.deviceId(),
      state.paused(),
      state.serverPaused(),
    ]);
    if (!deviceId || paused || serverPaused) return;
    if (performing() || parkedRigRun(await state.activeRun())) return;

    const here = rulePage(url);
    if (!here) return;
    const rules = (await state.arrivals()).filter((rule) => rule.page === here);
    if (!rules.length) return;

    const fired = await serially(async () => {
      const already = await state.arrived();
      if (already.includes(visit)) return null;
      // Written before the call, not after. The call takes a round trip, and a
      // second navigation event for the same commit -- which Chrome does emit
      // -- would otherwise find nothing written and fire again.
      await state.setArrived(
        [visit, ...already].slice(0, MOST_ARRIVALS_REMEMBERED),
      );
      return rules[0];
    });
    if (!fired) return;

    const started = await api.arrivalFire(deviceId, fired.id, url);
    // Said where the panel can draw it. A run that started because of a
    // standing rule looks, from the operator's side, like their browser
    // deciding to do something -- and the one thing that must never be true is
    // that they cannot see why.
    //
    // Only where a run actually started. A fire that stopped to ask answers
    // with a `confirmation_id` and a NULL run id, and one the backend skipped
    // answers with neither -- and this wrote the null straight into the active
    // run, where `pollRigRun` then asked the backend about a run called "null"
    // once a second, forever: 191 of those 404s are in one evening's log. The
    // card the operator should have seen is the confirmation, which
    // `waitingOnSomebody` already fetches.
    if (started?.run_id) {
      await state.setActiveRun({
        runId: started.run_id,
        at: Date.now(),
        source: "rig",
      });
    }
  } catch (error) {
    // A tab that closed mid-navigation, a rule the backend has since disabled,
    // a browser with no credential. Said out loud rather than swallowed: a
    // rule that silently stopped firing is the worst of the three.
    await state.setLastError(`a page rule did not fire: ${error}`);
  }
}

/** How many navigations back this browser remembers firing on. Ten is far more
 * than the handful of tabs anybody has open, and the visit id carries the
 * moment it happened, so an old one can never come back and match. */
const MOST_ARRIVALS_REMEMBERED = 10;

/** The page a RULE is about, which is `page()` plus two narrower rules.
 *
 * Not a second parser: `nudge.js`'s `page()` is the one that says what a page
 * is here, and this is the same string under the two conditions a standing
 * rule adds. Lowercased, because `domain/trigger/arrival.py` stores rules
 * lowercase so the two sides of the wire compare one spelling -- done at the
 * comparison rather than inside `page()`, which the nudge path matches against
 * `starts_on` strings the miner wrote in whatever case the page used. And http
 * or https only: `chrome://settings` parses, and the browser's own pages are
 * not a system, carry no session, and are the one place an extension has no
 * business driving anything.
 */
function rulePage(url) {
  try {
    if (!/^https?:$/.test(new URL(url).protocol)) return "";
  } catch {
    return "";
  }
  return pageOf(url).toLowerCase();
}

/** Ends the ones that ran out, wherever the operator has got to.
 *
 * Called on the beat rather than by a timer of its own: a service worker is
 * evicted between events, and a `setTimeout` for ninety seconds is one the
 * platform is free to never run. The pill in the page removes itself for the
 * same reason.
 */
async function sweepNudges() {
  return serially(async () => {
    const held = await state.nudges();
    if (!held.length) return;
    const open = held.filter((nudge) => nudge.state === "open");
    // `null`, not `""`: the beat is not looking at any one tab, and an empty url
    // read as a page says every operator has walked away from every offer.
    const swept = sweep(held, { url: null, now: Date.now() });
    await state.setNudges(swept);
    reportEndings(held, swept);
    // A card that has just gone quiet is one more waiting, and the beat is the
    // only thing that notices the day turning over.
    await badge();
    for (const nudge of open) {
      if (swept.find((each) => each.id === nudge.id)?.state !== "open") {
        void hideNudge(nudge.tabId);
      }
    }
  });
}

/** How many prompts are worth keeping to draw the day. */
const MAX_NUDGES = 20;

/** A write the operator's own browser made, against what was being offered. */
async function didItThemselves(message) {
  return serially(async () => {
    const held = await state.nudges();
    if (!held.some((nudge) => nudge.state === "open")) return;
    const after = onCall(
      held,
      { url: message.url, method: message.method },
      Date.now(),
    );
    if (after === held) return;
    await state.setNudges(after);
    reportEndings(held, after);
    for (const nudge of held) {
      if (
        nudge.state === "open" &&
        after.find((each) => each.id === nudge.id)?.state !== "open"
      ) {
        void hideNudge(nudge.tabId);
      }
    }
  });
}

// -- offering to finish the job they have just started ------------------------
//
// The nudge above asks from the address alone: "you have done this here
// before". This asks from the work itself. Two gestures into a job the rig has
// proved, the shape says which job it is and what has already been typed into
// it, so what lands is "finish this" -- with the values the operator has
// already given -- rather than "start something like it".
//
// On the gesture path, which is the hot one, so everything here is arithmetic
// over a five-minute cache and nothing on it may throw.

let shapesHeld = { at: 0, list: [] };
async function shapesFor() {
  if (Date.now() - shapesHeld.at < CANDIDATES_FRESH_MS) return shapesHeld.list;
  // A rig that answers something other than a list of shapes -- a proxy's
  // error page, an older rig -- is a rig with nothing to offer, not a throw
  // that would silence the arrival nudge too (`candidatesFor` awaits this
  // outside its own try).
  // Named, so the rig can mark the jobs this browser has been refusing.
  const answered = await api.shapes(await state.deviceId());
  // The older shape of this answer was a bare list. Both are read, so a worker
  // that has not been restarted after a backend deploy keeps offering.
  const served = Array.isArray(answered) ? answered : answered?.shapes;
  canFind = Array.isArray(answered) ? canFind : Boolean(answered?.canFind);
  const usable = Array.isArray(served)
    ? served.filter((shape) => shape && Array.isArray(shape.shape) && shape.id)
    : [];
  const list = usable.map((shape) => ({
    ...shape,
    // The rig records `starts_on` as the tab's whole URL. Everything that
    // compares one -- `shouldFire`, `mute`, the muted map -- speaks the nudge's
    // host-and-path, and a page addressed with a session id is never the same
    // page twice. Normalised once, here, so no consumer has to remember to.
    starts_on: pageOf(shape.starts_on || ""),
  }));
  // Only a non-empty answer is stamped, for the reason `candidatesFor` does not
  // cache a failed one: an empty list is a rig with nothing proved yet, and
  // holding it for five minutes means the first job it proves is invisible for
  // five more. `at: 0` is older than any window, so the next gesture asks again.
  shapesHeld = { at: list.length ? Date.now() : 0, list };
  return list;
}

/** Whether a run can go and find a value nobody typed, as this deployment last
 * said. Held beside the shapes because it arrives with them, and read by both
 * card paths -- the one a sentence makes and the one a prefix match makes.
 *
 * False until the first answer, which is the safe way round: a card that asks
 * for a value the run could have found costs a person ten seconds, and one
 * that promises to find a value on a deployment with no mailbox costs them a
 * run that stops at the first step. */
let canFind = false;

function originOf(url) {
  try {
    return new URL(url).origin;
  } catch {
    return null;
  }
}

/** One sentence, turned into the same offer a recognised walk makes.
 *
 * The card, the values, the box for anything missing and the press are all the
 * recogniser's already -- `offeringToFinish` draws this shape and
 * `start-rig-run` starts it. What was missing was the sentence: `/v1/chat`
 * reads an utterance against the tenant's jobs and had no caller in this
 * extension at all, so typing "create a work area called APITEST1" in the
 * panel said something to the thread and nothing else.
 *
 * `k: 0`, because nothing has been done yet: the card asks "want me to do it?"
 * rather than "want me to finish it?". The title comes off the served shapes
 * rather than the reading, which answers an id.
 *
 * Nothing here WRITES anything. An instruction is a request for an offer, and
 * the press on the card is still the authorisation -- the same rule that holds
 * for an offer the browser made off somebody's own gestures. A question is a
 * different thing and is answered on the spot: a read writes nothing, and
 * making somebody press a button before they are told what the answer is would
 * be a card that says "shall I go and look?" and nothing else.
 */
/** The job the thread's own reply placed this sentence as, if it placed one.
 *
 * The last thing the assistant said, and only the last: a thread is a
 * conversation, and the offer on screen is about the sentence just typed.
 */
function jobInTheReply(thread) {
  const messages = thread?.messages || [];
  for (const message of [...messages].reverse()) {
    if (message.speaker !== "assistant") continue;
    const decision = message.decision || {};
    return decision.kind === "job" && decision.workflow_id ? decision : null;
  }
  return null;
}

/** Whether that reply is a question the conversation is still waiting on.
 *
 * A sentence typed under a standing question has already been read -- against
 * the question, which is the only reading of it that is about anything. When
 * it was not the answer, the thread says so and asks again, and reading those
 * same words a second time against the rig's jobs is a reading of a sentence
 * that was never about a job.
 *
 * Measured on the deployment 2026-09-19, thread thr_163bf91b: the operator was
 * asked "Create a Client. Address takes 40 characters. What should it be?",
 * typed `testing for new purpose`, and got back both halves at once -- the
 * conversation correctly saying "I am still waiting on this one", and an open
 * offer to create a WAREHOUSE EQUIPMENT TYPE named after their sentence.
 */
function stillAsking(thread) {
  for (const message of [...(thread?.messages || [])].reverse()) {
    if (message.speaker !== "assistant") continue;
    const decision = message.decision || {};
    return decision.kind === "needs_values" && Boolean(decision.workflow_id);
  }
  return false;
}

/** Start a job that was already said yes to, as soon as the last answer lands.
 *
 * The run went looking for values nobody typed, came back short of one, and
 * ended -- and what it could not find became a question in the operator's own
 * thread. They answered it. The alternative to this function is drawing them
 * another card with another "Yes, do it" on it, for the job they already
 * pressed yes on and have just spent three answers finishing.
 *
 * `resume` is the door's word for that, and it is the door's to give: this
 * browser must not decide that a press was implied. `watched` rides along
 * because the two ways of doing the job are not interchangeable -- somebody
 * sitting in the panel answering questions is somebody watching, and a run
 * that replayed the call in front of them would finish with the page never
 * having moved.
 */
async function resumeTheJob(placed) {
  try {
    const started = await api.rigStart({
      workflow_id: placed.workflow_id,
      values: placed.values || {},
      items: Array.isArray(placed.items) ? placed.items : [],
      device_id: await state.deviceId(),
      live: true,
      allow_focus: true,
      matched: 0,
      // Where the run that asked the question had got to.
      //
      // Without it this starts at step 0 and re-walks everything the first run
      // performed: on `Create a Customer Type` it re-opens the mail,
      // re-navigates, presses Add again and re-types both fields, to arrive
      // back at the box it stopped in front of. `matched` stays 0 because that
      // counts GESTURES a browser tail matched and this is a step, and sending
      // one as the other is the defect that marked steps done nobody had done.
      from_step: Number.isInteger(placed.from_step) ? placed.from_step : 0,
      // Which outside conversation this run answers to, carried by the door
      // through every question. Without it a run started by an ANSWER is
      // findable by nobody while one started by a PRESS is findable by a
      // reply -- and which of the two happened is not something the person who
      // sent the request can see.
      mail_thread: placed.mail_thread || "",
      watched: placed.watched !== false,
    });
    await state.setActiveRun({
      runId: started.id,
      at: Date.now(),
      source: "rig",
    });
    // And say so where the decision was made. The thread holds the request,
    // the question and the answer; without this it stops one line short of
    // what came of them, and the run is only visible on the other pane.
    //
    // After the run is claimed and never before: a message naming a run that
    // failed to start is a thread saying something happened that did not.
    // Failing to SAY it is not failing to run it, so this cannot take the run
    // down with it.
    try {
      await api.runStarted({ run_id: started.id, title: placed.title || "" });
    } catch (error) {
      console.warn("[sro] the run started and the thread was not told", error);
    }
    void pollRigRun();
    return started.id;
  } catch (error) {
    // Said in the console and nowhere else on purpose. The thread already
    // says the job is running; a second card apologising for it is the panel
    // narrating its own plumbing, and the run's own row is where a failure to
    // start shows up.
    console.warn("[sro] the answered job could not be started", error);
    return null;
  }
}

/** A card for a job a mail asked for.
 *
 * Held here and never said into the thread, which is the rule this surface
 * already keeps: the thread is the record of what was DECIDED, and a prompt
 * nobody answered decided nothing. A conversation that filled up with "a mail
 * asks for X" would be the panel keeping history of questions instead of
 * answers -- and history is what the console is for.
 *
 * It ends three ways: they press it, they do the job themselves (the first
 * write on that host says so), or they dismiss it. What it does NOT end on is
 * time or a page -- it was never about a page they were standing on, and a
 * request nobody has answered has not stopped being a request. At the end of
 * the day it goes quiet instead, counted among the ones they missed.
 */
async function offerFromMail(offer) {
  // The answer came. Nothing is waiting on a mailbox any more, and a panel
  // still saying so under the card that answered it is a panel arguing with
  // itself. Cleared on the offer rather than on the reply being read, because
  // the offer is the thing this browser can actually see arrive.
  const awaiting = await state.awaitingMail();
  if (
    awaiting &&
    (!awaiting.thread || awaiting.thread === (offer.thread || ""))
  ) {
    await state.setAwaitingMail(null);
    await narrate(`no longer waiting on ${awaiting.to}: an offer arrived`);
  }
  // A run the answer already started. There is nothing here to offer.
  //
  // The operator pressed Yes on this request; that press is what sent the mail
  // asking for what was missing, and the reply filled the one blank the press
  // could not. A card beside the run that answer started is this panel
  // offering to do what it is doing.
  //
  // AFTER the wait is let go, not before: the answer that started the run is
  // exactly the answer that ends the waiting, and an early return above would
  // leave the panel saying it was still waiting for a reply that had arrived
  // and already been acted on.
  if (offer.started) {
    await narrate(
      `${offer.title || offer.workflow_id} is running on the answer that came back`,
    );
    return;
  }
  const shape = (await shapesFor()).find((one) => one.id === offer.workflow_id);
  const now = Date.now();
  const made = fire(
    {
      // The message, so two looks that somehow saw the same mail are one card.
      id: `mail_${offer.message}`,
      title: offer.title || shape?.title || offer.workflow_id,
      starts_on: shape?.starts_on || "",
      source: "rig",
      workflow_id: offer.workflow_id,
      k: 0,
      values: offer.values || {},
      items: [],
      missing: offer.missing || [],
      thread: offer.thread || "",
      subject: offer.subject || "",
      too_long: offer.too_long || {},
      // What the request asked for that this job cannot write. Carried so the
      // card can say it before the press rather than the run saying it after
      // -- after the press is after the record.
      unasked: offer.unasked || [],
      // What it could ALSO set, which nothing has to answer.
      //
      // On the card because a mail that supplied everything required produces
      // no question, and the question is where these are otherwise offered --
      // so for somebody who works out of their mailbox, an optional field
      // could never be set at all.
      offers: offer.offers || [],
      can_find: true,
      parameters: (shape?.parameters || []).map((one) => one.name),
      writes: shape?.writes || [],
      expires_at: endOfDay(now),
      keeps: true,
    },
    now,
  );
  const kept = await serially(async () => {
    const held = await state.nudges();
    if (held.some((one) => one.candidateId === made.candidateId))
      return "already held";
    // One request, one card, however many mails it arrives in.
    //
    // A request and its "Confirmed - please create the customer type in WMS as
    // discussed" are two MESSAGES, and the claim that stops a mail being read
    // twice is per message id -- so each was read, each understood as the same
    // job, and each offered. Seen on the deployment 2026-09-18: two identical
    // `Create a Customer Type — GV2` cards for one request, and pressing both
    // would try to make the record twice.
    //
    // The conversation is what identifies a request, which is why this is the
    // thread and not the values: a follow-up that corrects the code is still
    // the same request, and two people asking for the same code on separate
    // threads are two.
    //
    // Only against an OPEN one. An offer that was answered, dismissed or swept
    // has had its say, and a genuinely new request on that thread a week later
    // deserves its own card.
    if (
      made.mailThread &&
      held.some(
        (one) =>
          one.state === "open" &&
          one.workflowId === made.workflowId &&
          one.mailThread === made.mailThread,
      )
    )
      return "the same request is already on a card";
    await state.setNudges([made, ...held].slice(0, MAX_NUDGES));
    return "";
  });
  // Every way this can end, said out loud -- including the two that end it
  // quietly. An offer the backend made and this browser did not keep is the
  // failure nobody could see, and "already held" and "kept" were the same
  // silence as each other and as a throw.
  await narrate(
    kept
      ? `mail offer ${made.candidateId} not kept: ${kept}`
      : `mail offer ${made.candidateId} kept for ${made.workflowId} (${Object.keys(made.values || {}).length} value(s), ${(made.missing || []).length} missing)`,
  );
  // The icon says how many are waiting where the operator is not looking at
  // the panel, which is most of the day.
  await badge();
}

/** The offer, from a reading somebody else already paid for. */
async function offerFromJob(placed, tabId) {
  if (tabId === null) return;
  const shape = (await shapesFor()).find(
    (one) => one.id === placed.workflow_id,
  );
  const made = fire(
    {
      id: placed.workflow_id,
      title: placed.title || shape?.title || placed.workflow_id,
      starts_on: shape?.starts_on || "",
      source: "rig",
      workflow_id: placed.workflow_id,
      k: 0,
      values: placed.values || {},
      items: Array.isArray(placed.items) ? placed.items : [],
      missing: placed.missing || [],
      // What the door said, where it said anything; what the deployment last
      // told this browser otherwise. The two agree -- both are the same
      // container property -- and the fallback is for an older backend.
      can_find:
        placed.can_find === undefined ? canFind : Boolean(placed.can_find),
      parameters: (shape?.parameters || []).map((one) => one.name),
      writes: shape?.writes || [],
    },
    Date.now(),
  );
  await serially(async () => {
    const held = await state.nudges();
    // One open offer at a time: a sentence supersedes whatever was offered.
    const rest = held.map((one) =>
      one.state === "open"
        ? { ...one, state: "expired", endedAt: Date.now() }
        : one,
    );
    await state.setNudges([{ ...made, tabId }, ...rest].slice(0, MAX_NUDGES));
  });
}

async function offerFromWords(text, tabId) {
  if (!text || tabId === null) return;
  try {
    const said = await api.ask(text);
    // A question, not an instruction. It has already been looked up -- a read
    // writes nothing, and waiting for a press before answering a question is
    // the shortcut this was built to avoid -- so what is left is to put the
    // answer where the panel draws it.
    if (said?.kind === "lookup") {
      await state.setAnswer({
        said: text,
        tabId,
        askedAt: Date.now(),
        ...said.lookup,
      });
      return;
    }
    const read = said?.job;
    if (!read?.workflow_id) return;
    const shape = (await shapesFor()).find(
      (one) => one.id === read.workflow_id,
    );
    const made = fire(
      {
        id: read.workflow_id,
        title: shape?.title || read.workflow_id,
        starts_on: shape?.starts_on || "",
        source: "rig",
        workflow_id: read.workflow_id,
        k: 0,
        values: read.values || {},
        // Several things in one sentence: "add these three equipment types" is
        // one job done three times. The card says how many before anybody
        // presses it, and the press carries them.
        items: Array.isArray(read.items) ? read.items : [],
        missing: read.missing || [],
        parameters: (shape?.parameters || []).map((one) => one.name),
      },
      Date.now(),
    );
    await serially(async () => {
      const held = await state.nudges();
      // One open offer at a time, which is the queue this design exists to not
      // be: a sentence supersedes whatever the browser was offering.
      const rest = held.map((one) =>
        one.state === "open"
          ? { ...one, state: "expired", endedAt: Date.now() }
          : one,
      );
      await state.setNudges([{ ...made, tabId }, ...rest].slice(0, MAX_NUDGES));
    });
  } catch (error) {
    // Said out loud, not swallowed.
    //
    // A sentence about nothing is the ordinary case and says nothing back --
    // the thread already has what they said. A door that REFUSED is a
    // different thing, and this catch hid one for a whole evening: every
    // sentence an operator typed got a 404 from `/v1/ask`, the panel offered
    // nothing, and there was no way from the panel to tell "I did not
    // understand you" from "I could not ask".
    //
    // `lastError` is what the strip already draws when something is wrong, so
    // this needs no new surface: the operator sees that the door refused and
    // the log says which.
    if (error instanceof ApiError) {
      await state.setLastError(
        `the panel could not ask about that: ${error.message}`,
      );
    }
  }
}

async function considerOffer(tabId, gesture) {
  try {
    if (tabId === null || !(await isWatched(tabId))) return;
    // The browser is already being driven. Offering to drive it again is the
    // panel talking over itself -- and the gestures would be the run's own.
    // `parkedRigRun` too: a run waiting on somebody to approve a write has sent
    // no command for however long they have been thinking about it, and the
    // gestures arriving meanwhile are them doing that step by hand. Offering
    // to start a second run over it is the worst moment this panel has.
    if (performing() || parkedRigRun(await state.activeRun())) return;
    const origin = originOf(gesture.url);
    if (!origin) return;
    // Asked before the tail is written: a browser with no rig has nothing to
    // match against, and a storage write per keystroke to feed nothing is a
    // cost paid by every operator who never configured one.
    const shapes = await shapesFor();
    if (!shapes.length) return;
    const tails = await state.tails();
    const tail = tailWith(tails[tabId] || [], {
      triple: tripleOf({
        system: origin,
        target: gesture.target,
        kind: gesture.kind,
      }),
      // A credential field contributes the fact that it was typed and nothing
      // else: the shape still matches, and the offer simply has one more
      // parameter it has to ask for.
      //
      // A click falls back to what it clicked ON. The WMS's dropdown is an
      // ExtJS combo: clicking the field opens a floating list and the operator
      // clicks a row of it, so the choice is carried by the row's text and by
      // no `value` anywhere. Without this the offer for a job whose parameter
      // is a dropdown draws an empty box for it however plainly the operator
      // just picked it. Only positions a served shape indexes are ever read
      // (`valuesFrom`), and a shape indexes one only where the miner matched
      // that text against a value the job was seen taking -- so "Save" never
      // becomes anybody's answer.
      value: gesture.secret ? null : (gesture.value ?? chosen(gesture)),
      secret: Boolean(gesture.secret || gesture.target?.secret),
      at: gesture.at,
    });
    await state.setTails({ ...tails, [tabId]: tail });
    const now = Date.now();
    // Everything that reads the nudges and writes them back goes through the
    // one lock. Two gestures fifty milliseconds apart both read a list with no
    // offer in it and both wrote one, and the second write took the first
    // offer's record with it -- so the operator saw two pills and the rig was
    // told about one offer that no longer existed.
    await serially(async () => {
      const held = await state.nudges();
      const open =
        held.find((n) => n.state === "open" && n.tabId === tabId) || null;
      // The screen the work is happening on, so a job that begins on another
      // screen of the same application is not offered here. See
      // `elsewhereInTheSameApp`.
      const { replace, end } = decideOffer({
        tail,
        shapes,
        open,
        origin,
        page: gesture.url || null,
        now,
      });
      if (end && open) return endOffer(open, end, held);
      if (!replace) return;
      // A longer prefix is the same offer knowing more, not a second one. The
      // id and the moment it was made stay put -- so nothing ended, nothing is
      // reported, and the ledger has one offer that got further rather than a
      // dismissal every time the operator typed the next field.
      const made =
        open && open.source === "rig" && open.state === "open"
          ? { ...open, ...replace, id: open.id, at: open.at, tabId, canFind }
          : { ...replace, tabId, canFind };
      // The one it supersedes stops being open: two open at once is the queue
      // this design exists to not be. On an upgrade that is the same record,
      // and `made` puts it straight back with what it has just learned. A
      // backend nudge is a different record, and it is not thrown away either
      // -- it ends as `expired`, so the day it drew still holds every offer
      // that was ever made rather than quietly losing the ones a prefix match
      // happened to land on top of.
      const rest = held.flatMap((n) => {
        if (n.id !== open?.id) return [n];
        if (n.id === made.id) return [];
        void hideNudge(n.tabId);
        return [{ ...n, state: "expired", endedAt: now }];
      });
      // Kept offers first, and outside the trim. A request read out of a mail
      // is waiting on a person; the prefix offers this path makes are what
      // somebody is doing right now, and twenty of those must not be able to
      // push a request off the end of the list. Nothing is lost by a busy
      // morning.
      const waiting = [made, ...rest].filter(
        (n) => n.keeps && n.state === "open",
      );
      const others = [made, ...rest].filter(
        (n) => !(n.keeps && n.state === "open"),
      );
      await state.setNudges([...waiting, ...others.slice(0, MAX_NUDGES)]);
      // The title alone: `paintNudge` wraps whatever it is given in "do ...?",
      // so a sentence renders as a question about a question.
      //
      // And only when the panel is not already up. The pill does one thing --
      // open the panel -- so beside an open one it is a button that cannot do
      // anything, which is what it looked like: pressed, and nothing happened.
      // `watching` is the panel's own port, so this is a fact rather than a
      // guess. One window is assumed: a panel open in another window still
      // suppresses the pill here, which is the rarer wrong answer of the two.
      if (!watching.size) await showNudge(tabId, made.title);
    });
  } catch {
    // A tab that closed, a rig that is down. Nothing offered is the quiet
    // answer, and this runs on every keystroke: it may never cost a gesture.
  }
}

/** A tab that closed took its tail with it. Chrome hands the id out again, and
 * a tail left under it would make the next tab's first gesture look like the
 * middle of a job somebody did in a window that is gone. */
function forgetTail(tabId) {
  return serially(async () => {
    const tails = await state.tails();
    if (!(tabId in tails)) return;
    delete tails[tabId];
    await state.setTails(tails);
  });
}

async function endOffer(nudge, fate, held) {
  await state.setNudges(
    held.map((n) => (n.id === nudge.id ? { ...n, state: fate } : n)),
  );
  void hideNudge(nudge.tabId);
  void report(nudge, fate);
}

/** How an offer ended, told to the rig.
 *
 * Every fate, not just the ones that became runs: whether recognising a job
 * early was worth doing is a question only the dismissals and the walk-aways
 * can answer.
 */
async function report(nudge, fate, runId = null) {
  if (nudge.source !== "rig" || !nudge.workflowId) return;
  try {
    void api.reportOffer({
      workflow_id: nudge.workflowId,
      k: nudge.k || 0,
      fate,
      run_id: runId,
      device_id: await state.deviceId(),
      at: new Date().toISOString(),
    });
  } catch {
    // Called with `void` from every ending. A rejection here is an unhandled
    // one, and what would be lost is a record of something that already
    // happened.
  }
}

/** Every offer that has just stopped being open, reported by how it stopped. */
function reportEndings(before, after) {
  for (const was of before) {
    if (was.state !== "open" || was.source !== "rig") continue;
    const now = after.find((each) => each.id === was.id);
    if (!now || now.state === "open") continue;
    void report(was, now.state === "by-hand" ? "did_it" : "expired");
  }
}

// -- which tabs are being watched --------------------------------------------
//
// The operator points at a tab and says "the work is in here". Nothing else
// decides it: not the tenant's host list (which cannot tell a warehouse tab
// from a console tab on the same host), and not any rule this file could
// invent about which origins are "ours". A watched tab is watched entirely --
// every frame, every call it makes, wherever it navigates.

async function watchedTabs() {
  const watched = await state.watched();
  // A tab id is only meaningful while the tab exists. Chrome hands the same
  // ids out again after a restart, so a stale entry is not merely useless --
  // it is a watch on whatever tab inherits the number.
  const alive = await Promise.all(
    watched.map(async (entry) => {
      try {
        const tab = await chrome.tabs.get(entry.tabId);
        // Where it is NOW, beside the host the watch was granted for.
        //
        // `host` is written once, when the watch is made, and is what the
        // grant was asked about -- so it has to stay that, or closing the tab
        // would revoke a grant for a host it never left. It is not where the
        // tab is: a watched tab is watched wherever it navigates, and the
        // panel read `host` and told an operator standing on a Keycloak
        // sign-in page that everything they did on `blueyonderalphaus.
        // b2clogin.com` was evidence. Measured on the deployment 2026-09-20.
        return { ...entry, on: hostOf(tab.url || "") };
      } catch {
        return null;
      }
    }),
  );
  const kept = alive.filter(Boolean);
  // Tidying is never allowed to fail a capture. Storage can reject -- a full
  // disk, a quota -- and a gesture lost because the housekeeping beside it
  // threw is the same bug as a gesture lost to a failed screenshot.
  if (kept.length !== watched.length)
    // Without the derived half: `on` is read off the live tab every time this
    // is called, and a copy of it in storage is a second answer that goes
    // stale the moment the tab moves -- which is the defect this adds `on` to
    // fix.
    await state
      .setWatched(kept.map(({ on: _on, ...kept_ }) => kept_))
      .catch(() => {});
  return kept;
}

/** Hosts this operator granted, minus the ones that have run out.
 *
 * Expiry is applied here as well as on the server, and for the same reason it
 * is applied there rather than swept: a grant that has run out must stop
 * admitting the moment it does. A browser that kept queueing against an
 * expired one would fill the queue with events the backend then refuses.
 */
async function grantedHosts() {
  const grants = await state.grants();
  const now = Date.now();
  return grants
    .filter((grant) => Date.parse(grant.expires_at || "") > now)
    .map((grant) => grant.host);
}

/** Whether this URL may be recorded, the operator's own grants included.
 *
 * `allowsHost` takes the grants as its third argument and defaults it to none,
 * which is right for a pure function and wrong for every caller in this file:
 * each one is deciding about a live browser where the operator may have pressed
 * "watch this host anyway". Three of them forgot, so pressing that button
 * produced gestures and calls and had every one of them dropped here as an
 * excluded host -- a surface claiming to observe, and no evidence.
 *
 * So the grants stop being an argument anybody can leave off.
 */
async function admits(url, policy) {
  return allowsHost(url, policy, await grantedHosts());
}

/** Put the recorder into this tab, the operator's own grants included.
 *
 * `injectInto` defaults its grants the same way, and both call sites here
 * forgot them -- so on a granted host the gate above would have admitted
 * evidence that was never produced, because nothing was ever injected.
 */
async function injectHere(tabId, url) {
  return injectInto(tabId, url, await state.policy(), await grantedHosts());
}

async function isWatched(tabId) {
  if (tabId === null || tabId === undefined) return false;
  return (await watchedTabs()).some((entry) => entry.tabId === tabId);
}

function watch(tabId, url) {
  return serially(async () => {
    const watched = await watchedTabs();
    if (watched.some((entry) => entry.tabId === tabId)) return watched;
    let host = "";
    try {
      host = new URL(url).hostname;
    } catch {
      host = "";
    }
    // Pressing "watch" on a page the tenant excludes by default is the
    // operator saying it may be watched after all. Asked of the server before
    // the tab is recorded as watched, because the server is what actually
    // admits the evidence: a browser that recorded the watch and failed to get
    // the grant would show a watching panel over a queue being thrown away.
    if (host && (await isExcluded(host))) await grant(host);

    const next = [{ tabId, host, since: Date.now() }, ...watched];
    await state.setWatched(next);
    return next;
  });
}

/** Watch this tab, if its system is one the operator watches everywhere.
 *
 * The same `watch` a press calls, and the same injection: a tab that is
 * watched but never injected into is a panel saying "watching" over a page
 * producing nothing. Silent when the host is not on the list -- that is the
 * ordinary case and the panel still offers.
 */
async function watchIfAlways(tabId, url) {
  if (!alwaysWatched(url, await state.alwaysWatch())) return false;
  if (await isWatched(tabId)) return true;
  await watch(tabId, url);
  await injectHere(tabId, url);
  await badge();
  return true;
}

/** Whether the tenant's policy excludes this host by default. */
async function isExcluded(host) {
  const policy = await state.policy();
  return (policy?.exclude_hosts || []).some((pattern) =>
    hostMatches(host, pattern),
  );
}

/** Ask the server to watch this host too, and remember what it answered.
 *
 * The server's list is the one that counts and it caps the duration, so what
 * comes back is stored rather than what was asked for.
 */
async function grant(host) {
  const deviceId = await state.deviceId();
  if (!deviceId) return;
  try {
    const answer = await api.grantHost(deviceId, host);
    await state.setGrants(answer.grants || []);
  } catch (error) {
    // Said out loud rather than swallowed: the panel will claim to be watching
    // a tab whose evidence the backend is about to refuse, and the operator
    // has no other way to find that out.
    await state.setLastError(
      error instanceof ApiError ? error.message : String(error),
    );
  }
}

/** Give the host back, so a closed tab does not leave a mailbox observed. */
async function ungrant(host) {
  const deviceId = await state.deviceId();
  if (!deviceId || !host) return;
  // Only when no other watched tab is still on it: two mail tabs and closing
  // one is not the operator withdrawing anything.
  const watched = await watchedTabs();
  if (watched.some((entry) => entry.host === host)) return;
  try {
    const answer = await api.revokeHost(deviceId, host);
    await state.setGrants(answer.grants || []);
  } catch {
    // The grant expires on its own, so a revoke that could not be delivered
    // costs a window rather than leaving the page observed forever.
  }
}

function unwatch(tabId) {
  return serially(async () => {
    const watched = await watchedTabs();
    const leaving = watched.find((entry) => entry.tabId === tabId);
    const next = watched.filter((entry) => entry.tabId !== tabId);
    // A tab nobody was watching closes all day long. Writing the same list
    // back for each one is how a watch set meanwhile gets overwritten.
    if (next.length !== watched.length) await state.setWatched(next);
    // Stop watching, stop debugging. An operator who pressed "stop watching"
    // and was left with the banner up would have every reason to disbelieve
    // the panel about anything else it says.
    if (next.length !== watched.length) await releaseTree(tabId);
    // And stop remembering what was typed there. A tail kept across "stop
    // watching" and "watch" again could complete a prefix from yesterday's
    // job with values nobody is looking at. Inline rather than `forgetTail`,
    // which takes the same lock this block already holds.
    const tails = await state.tails();
    if (tabId in tails) {
      const { [tabId]: _gone, ...kept } = tails;
      await state.setTails(kept);
    }
    if (leaving?.host && (await isExcluded(leaving.host)))
      await ungrant(leaving.host);
    return next;
  });
}

chrome.tabs.onRemoved.addListener((tabId) => {
  halfDeaf.delete(tabId);
  void forgetRepaired(tabId);
  void forgetTail(tabId);
  void releaseTree(tabId);
  void unwatch(tabId);
});

/** A popup is two hosts, so it is two policy checks.
 *
 * `pageEvent` below tests the host being opened. The opener was never tested
 * at all, so an excluded page could spawn a popup and have it recorded --
 * ADR 008 says an excluded page produces nothing, and a popup it opened is
 * something. */
async function popupEvent(d) {
  let opener;
  try {
    opener = await chrome.tabs.get(d.sourceTabId);
  } catch {
    // The opener is gone already, so there is no host left to judge it by,
    // and a popup that cannot be attributed is not evidence of anything.
    return;
  }
  const policy = await state.policy();
  if (!(await admits(opener.url, policy))) return;
  // A window the watched application opened is part of the same piece of work
  // -- a picker, an SSO round trip, a print preview. The operator pointed at
  // the task, not at a tab id, so the watch follows it.
  if (await isWatched(d.sourceTabId)) await watch(d.tabId, d.url);
  // The new tab's id, not the opener's: `url` is the new tab's, and the two
  // together used to name one tab while describing another's page.
  await pageEvent("popup_opened", d.tabId, d.url, d.timeStamp, d.sourceTabId);
}

async function pageEvent(page_kind, tab_id, url, timeStamp, opener_tab_id = null) {
  try {
    const [policy, allowed, watching] = await Promise.all([
      state.policy(),
      capturing(),
      isWatched(tab_id),
    ]);
    if (!allowed.on || !watching || !(await admits(url, policy))) return;
    await queue.enqueue({
      kind: "page",
      at: new Date(timeStamp).toISOString(),
      page_kind,
      // Every stored URL goes through this. An SSO or magic-link callback
      // carries a live credential in its query, `webNavigation` fires for it
      // with no content script involved, and the backend redacts bodies and
      // headers but never URLs -- so if this does not do it, nothing does.
      url: redactUrl(url),
      detail: null,
      tab_id,
      opener_tab_id,
    });
  } catch (error) {
    // A full or broken queue is the one failure that must not be silent:
    // capture stopping quietly looks exactly like an operator with nothing
    // to do, and nobody finds out for weeks.
    await state.setLastError(`could not queue a page event: ${String(error)}`);
  }
}

/** What the tenant's policy allows this request to keep.
 *
 * Both of these are delivered on every heartbeat and neither was being read,
 * so a tenant that had switched response bodies off still had them uploaded,
 * and `max_body_bytes` bounded nothing at all. */
function underPolicy(request, policy) {
  if (!request?.request_body && !request?.response_body) return request;
  const limit = policy?.max_body_bytes ?? Infinity;

  const allowed = (body, keep) => {
    if (!body) return body;
    if (!keep)
      return {
        ...body,
        text: null,
        size_bytes: 0,
        redacted_fields: ["«not captured»"],
      };
    if ((body.size_bytes ?? 0) > limit) {
      return {
        ...body,
        text: null,
        size_bytes: 0,
        redacted_fields: ["«dropped: larger than the tenant's max_body_bytes»"],
      };
    }
    return body;
  };

  return {
    ...request,
    request_body: allowed(request.request_body, true),
    response_body: allowed(
      request.response_body,
      policy?.capture_response_bodies !== false,
    ),
  };
}

/** Tabs whose page-realm patch outlived the extension that installed it.
 *
 * Their gestures still arrive; their calls are emitted and dropped. Cleared on
 * navigation, because a fresh document gets a fresh patch and a handshake at
 * `document_start`, which is the only moment one can safely happen.
 */
const halfDeaf = new Set();

/** Tabs this worker has already reloaded to repair their recording.
 *
 * One attempt each. A reload that did not fix it will not fix it the second
 * time either, and the page says nothing that distinguishes the two -- so a
 * worker that kept trying would keep a tab reloading forever, which is what it
 * did before this existed.
 *
 * Forgotten when the tab goes, beside `halfDeaf`, so a tab id Chrome reuses
 * for something else is not refused a repair it has never had.
 *
 * **In storage, because "ever" is longer than this worker lives.** It was a
 * module Set, and a module Set is emptied every time the worker is evicted --
 * which is every few seconds. So the guard held for one eviction cycle and the
 * loop it exists to stop ran anyway, just with a pause in it.
 *
 * Measured on the deployment 2026-09-20: the console's own page reloaded 68
 * times in four minutes, once every three and a half seconds, each reload
 * reporting the same half-installed recorder to a fresh worker that had never
 * heard of it. The page was unusable and the extension was narrating the
 * repair each time, truthfully.
 *
 * The in-memory Set stays in front of it: the common case is a tab asking
 * twice in one worker's life, and that should not cost a storage read.
 */
const repaired = new Set();

/** Claim this tab's one repair, or say somebody already has it.
 *
 * Asking and claiming in ONE turn, under the lock, and that is the whole
 * point. It used to be `alreadyRepaired` then `markRepaired`, with an await
 * between them -- so every report that arrived before the first one finished
 * reading storage saw an unclaimed tab, and every one of them reloaded it.
 *
 * Which is not a rare race. One page is one tab id and many FRAMES: a page
 * with a dozen iframes reports a half-installed recorder a dozen times in the
 * same turn, from the same `sender.tab.id`. Measured on the deployment
 * 2026-09-20: tab 148284819 reloaded fifteen times and tab 148284734 eight,
 * inside one minute, each reload narrated truthfully by a guard that was
 * doing exactly what it was written to do and could not see the other
 * fourteen.
 *
 * The in-memory Set stays in front of the storage read for the common case --
 * a tab asking twice in one worker's life should not cost one -- but it is
 * now read and written on the same side of the lock as the list.
 */
async function claimRepair(tabId) {
  return serially(async () => {
    if (repaired.has(tabId)) return false;
    const held = await state.repaired();
    if (held.includes(tabId)) {
      // Remembered here too, so the next report in this worker's life is
      // answered without a storage read.
      repaired.add(tabId);
      return false;
    }
    repaired.add(tabId);
    // Bounded: tab ids are reused by Chrome and a list that only grows is a
    // list that refuses a repair to a tab that has never had one. The newest
    // few are the ones a loop would be about.
    await state.setRepaired([...held, tabId].slice(-K_REPAIRED));
    return true;
  });
}

/** Forget a tab that has gone, in both places.
 *
 * Chrome hands the same tab id out again, so a record that outlived the tab
 * refuses a repair to a page that has never had one -- which is the failure
 * the in-memory Set was already careful about, and which persisting it would
 * have made permanent.
 */
async function forgetRepaired(tabId) {
  repaired.delete(tabId);
  await serially(async () => {
    const held = await state.repaired();
    if (held.includes(tabId)) {
      await state.setRepaired(held.filter((one) => one !== tabId));
    }
  });
}

/** How many repaired tabs are remembered. A browser with thirty tabs open,
 * each repaired once, is the most this ever has to hold. */
const K_REPAIRED = 40;

chrome.runtime.onMessage.addListener((message, sender, respond) => {
  // Returning true keeps the channel open for the async answer.
  handle(message, sender).then(respond, (error) =>
    respond({ error: String(error) }),
  );
  return true;
});

async function handle(message, sender) {
  switch (message?.kind) {
    case "content-ready":
      return { ok: true };
    case "calls-not-recordable": {
      // A tab whose page-realm patch outlived the extension that installed it.
      // It is still emitting and nothing can accept what it emits, and the tab
      // cannot be repaired from here -- the patch lives in the page's own realm,
      // where the handshake that made it trustworthy can only happen before any
      // page script exists.
      //
      // Reloading somebody's page out from under them is not this worker's
      // call to make -- unless the page has nothing to lose, which is the one
      // case where it is nobody's loss and everybody's gain.
      //
      // The rule stands where it matters. A page holding typed text, a ticked
      // box, or its own beforeunload warning is a page somebody is working in,
      // and the half-filled form is exactly the state this system spends its
      // care protecting: it goes on the card and waits to be asked. A page
      // holding none of those is repaired where it stands, because asking
      // somebody to press a button to fix a fault they did not cause -- every
      // time an extension update lands -- is a tax for no benefit.
      //
      // The page decides which it is, because only the page can see it.
      //
      // And nothing is reloaded at all while a run is in flight. Which tab a
      // run is driving is held inside `commands.js` and not readable here, so
      // the answer is the conservative one rather than the precise one: a run
      // is a form being filled somewhere, and being wrong about where would
      // reload the page out from under it mid-step.
      const deafTab = sender?.tab?.id ?? -1;
      const running = Boolean((await state.activeRun())?.runId);
      // Once per tab, ever.
      //
      // The reload is a repair and a repair that did not work is not worth
      // repeating: the fresh page reports the same fault a second later, and
      // the worker reloads it again. Measured on the deployment 2026-09-18 --
      // one tab reloaded fourteen times in a row, which is a browser nobody
      // can use and a page nobody can read.
      //
      // Why the second one fails at all is not knowable from here: the patch
      // installs at `document_start` and whether it won that race is exactly
      // what the tab is reporting it cannot tell. So this does not try to be
      // clever about the cause -- it tries once, and if the tab is still deaf
      // it goes on the card and waits to be asked, which is where it was
      // before any of this.
      if (
        message.holding === false &&
        deafTab >= 0 &&
        !running &&
        (await claimRepair(deafTab))
      ) {
        try {
          await chrome.tabs.reload(deafTab);
          await narrate(
            `tab ${deafTab} was recording half and was reloaded -- nothing typed in it`,
          );
          halfDeaf.delete(deafTab);
          return { ok: true, reloaded: true };
        } catch (error) {
          // A tab that will not reload is a tab to say something about, which
          // is what the card below is for.
          console.warn("[sro] a half-deaf tab could not be reloaded", error);
        }
      }
      // Recorded rather than acted on: saying that the tab records gestures
      // and no calls is this worker's call to make, because the alternative is
      // a demonstration that quietly asserts nothing about the system it
      // changes.
      halfDeaf.add(deafTab);
      return { ok: true };
    }
    case "gesture":
    case "request": {
      // Every captured event is judged here, at the one point they all pass
      // through, rather than by whether a content script happens to be
      // running. Withdrawing a registration only stops *future* injections:
      // a tab that was already open keeps its scripts, keeps its patched
      // `fetch`, and keeps sending. Gating only on registration meant an
      // operator who hit pause -- or a host that had just been excluded --
      // went on being recorded for as long as the tab stayed open.
      const [policy, allowed, watching] = await Promise.all([
        state.policy(),
        capturing(),
        isWatched(sender?.tab?.id ?? null),
      ]);
      const frameUrl = message.frameUrl;
      if (!allowed.on) return { ok: false, dropped: allowed.because };
      // The operator's own answer to "which tab is the work in". Everything in
      // a watched tab is evidence and nothing outside one is -- no host list
      // decides it, which is why a console polling its own backend all day
      // never became 97% of a day's capture again.
      if (!watching)
        return { ok: false, dropped: "this tab is not being watched" };
      if (!(await admits(frameUrl, policy))) {
        return { ok: false, dropped: "excluded host" };
      }
      // A tab this extension is driving for a run is not an operator working.
      // Kept out of the evidence plane entirely: a replay's clicks and the
      // calls they set off, mined as though somebody had done them, is the
      // system learning a task from a robot imitating a person -- and then
      // offering it back as something worth automating.
      if (isDriving(sender?.tab?.id ?? null)) {
        // Dropped from the evidence plane, and kept for the length of the run
        // in a bounded map the run can ask about: a step that just posted a
        // form is verified by what the server answered rather than by
        // photographing the page and asking a model what it looks like.
        if (message.kind === "request")
          noteDriven(sender?.tab?.id ?? null, message.request);
        return { ok: false, dropped: "this browser is performing a run" };
      }
      // Somebody is working in here. Said out loud on the channel so a command
      // queues instead of landing mid-keystroke -- only for gestures, because
      // a page's background traffic is not a person at a keyboard.
      if (message.kind === "gesture") {
        channel.operatorIsWorking();
        // And the same gesture, read the other way: is this the start of a job
        // the backend has already proved? Never awaited -- recognising a job may
        // not hold up recording one.
        void considerOffer(sender?.tab?.id ?? null, message.gesture);
      }
      // They did the task themselves while it was being offered. One of the
      // three ways a nudge ends, and the one that needs saying least: they did
      // the thing, and a panel congratulating them on it is a panel nobody
      // wants open.
      if (message.kind === "request") void didItThemselves(message);
      // tab_id comes from the sender, not the content script -- a frame has
      // no chrome.tabs access of its own to ask for it.
      const tab_id = sender?.tab?.id ?? null;
      // The tab's own URL, which is not the frame's. A gesture inside a portal
      // that hosts its screens in an iframe reports the frame's src, and a run
      // told to open that would load the frame's document on its own, outside
      // the shell that gives it its session and its chrome. What a run has to
      // reproduce is the address an operator would type.
      const page_url = redactUrl(sender?.tab?.url);
      // Same rule as page events, at the same one point: a gesture carries the
      // page's own `location.href` and every event carries the frame it
      // happened in, and either can be the callback URL with the token in it.

      if (message.kind === "gesture") {
        // Taken before the row is written so the picture and the gesture are
        // one row: nothing to key together afterwards, and nothing left
        // orphaned when the queue is cleared for a change of credential.
        // `capture` decides for itself whether a picture is allowed at all --
        // the tenant's policy, its per-minute cap, and the host of the whole
        // document the gesture's frame sits in, which is what a photograph
        // actually shows.
        // Never allowed to fail the gesture. `capture` can reject -- a
        // chrome.storage read, a data URL that will not decode -- and an
        // exception here would leave the queue untouched, so the one event
        // this system refuses to drop would be lost to a failed picture of it.
        const shot = await capture(tab_id, policy).catch(() => null);
        await queue.enqueue(
          {
            kind: "gesture",
            gesture: {
              ...message.gesture,
              url: redactUrl(message.gesture?.url),
            },
            tab_id,
            frame_url: redactUrl(frameUrl),
            page_url,
          },
          shot,
        );

        // The screen the operator was looking at when they decided to act,
        // for whatever induction later builds a locator from. Taken before
        // the click, not after: a step that navigates would otherwise carry
        // the destination page, and induction would build that step's
        // locator from a page where the control it clicked does not exist.
        const before = takeTree(tab_id);
        if (before) await queue.enqueue(before, null);
        void takeTreeSoon(tab_id, page_url, policy).catch(() => null);
        return { ok: true, screenshot: Boolean(shot) };
      }
      await queue.enqueue({
        kind: "request",
        request: {
          ...underPolicy(message.request, policy),
          url: redactUrl(message.request?.url),
        },
        tab_id,
        frame_url: redactUrl(frameUrl),
      });
      return { ok: true };
    }
    case "sign-in":
      // Everything the last credential left behind goes first, before the new
      // one is written. Doing it after a successful `register` left a window
      // where the new token was live and the old queue was still on disk: if
      // `register` threw -- offline, a 500 -- capture stayed on with the old
      // device id, and the next FLUSH alarm uploaded one operator's events
      // under the other's credential, into the other's tenant. That is the
      // exact thing the sign-out path below clears the queue to prevent.
      await unregister();
      channel.close();
      await queue.clear();
      await state.newQueueEpoch();
      // A batch minted for the last operator names their epoch and their
      // rows; left standing, the first flush under the new credential would
      // retry it as itself and send the new operator's queue under the old
      // operator's batch id.
      await state.setPendingBatch(null);
      // A shared warehouse machine is the ordinary case, not the exception:
      // the last operator's run stays offerable for an hour (`state.js`'s
      // `finishedRun`), so without this the next operator to sign in within
      // that hour would see somebody else's card and an "Undo that" that
      // 403s -- this run was not performed for them.
      await state.setFinishedRun(null);
      await state.setActiveRun(null);
      await state.setDeviceId("");
      await state.setDeviceSecret("");
      await state.setPolicy(null);
      await state.setApiUrl(message.apiUrl);
      await state.setConsoleUrl(message.consoleUrl || "");
      await state.setToken(message.token);
      // Capture is off until the registration lands, and the badge says so.
      await badge();
      return register(message.label);
    case "sign-out":
      await unregister();
      // Before the credential goes: a socket authenticated as the operator
      // who is leaving must not still be open for the next one.
      channel.close();
      // Before the credential goes, so nothing captured under it can be
      // uploaded under the next one. What this browser recorded for one
      // operator must not arrive in another operator's tenant because they
      // shared a machine.
      await queue.clear();
      await state.newQueueEpoch();
      await state.forget();
      await badge();
      return { ok: true };
    case "set-paused":
      await state.setPaused(Boolean(message.paused));
      return settle();
    case "send-draft": {
      // The one press in this system that writes to somebody outside it.
      //
      // The worker holds the credential and nothing else: which words go out
      // is the backend's to decide, from the draft it put in the thread. This
      // carries the operator's yes and two ids.
      try {
        const answered = await api.sendTheDraft({
          thread_id: message.threadId,
          message_id: message.messageId,
        });
        await narrate(
          answered.sent_to
            ? `asked ${answered.sent_to} about ${message.messageId}`
            : `nothing was sent for ${message.messageId}`,
        );
        // What the panel draws a live wait from. Only where a mail actually
        // went: "waiting for a reply" under a mail that was never sent is the
        // panel telling somebody a story about itself.
        if (answered.sent_to) {
          await state.setAwaitingMail({
            to: answered.sent_to,
            at: Date.now(),
            thread: message.mailThread || "",
          });
          await narrate(`waiting on a reply from ${answered.sent_to}`);
        }
        return { ok: true, sent_to: answered.sent_to || "" };
      } catch (error) {
        return { ok: false, error: error.problem?.detail || error.message };
      }
    }
    case "forget-run":
      // The operator has read what the run made. The card is a result, not a
      // record: the run itself is on the backend for as long as the tenant
      // keeps it, and this clears only the copy this panel draws.
      //
      // Their press and nothing else. It used to go when the hour ran out or
      // when the next run started, so a card somebody had not looked at yet
      // could vanish, and one they had finished with sat there for an hour.
      await state.setFinishedRun(null);
      return status();
    case "clear-error":
      // The panel's dismiss. `lastError` is the last one, not a live one, so
      // it outlives whatever fixed it; without this the amber stays until the
      // next call happens to succeed and clear it as a side effect.
      await state.setLastError("");
      return status();
    case "reconnect":
      // The panel's answer to "this browser cannot be reached". The channel
      // redials itself on the minute alarm anyway, so this buys impatience
      // rather than correctness -- but a card that states a fault and offers
      // nothing to do about it sends the operator to the options page to
      // toggle something at random.
      await state.setLastError("");
      void channel.settle();
      return status();
    case "flush":
      // Upload now rather than on the next tick, and all of it: "it went" has
      // to mean the queue is empty. No screen sends this any more; the
      // real-Chrome suite and `make fixtures` drain through it.
      return drain();
    case "run":
      // The panel says what a run driving this browser is doing. The worker
      // holds the credential, so it does the asking.
      //
      // Two doors, because there are two kinds of run and their ids live in
      // different tables: a skill run at `/v1/runs`, a mined job's run at
      // `/v1/workflow-runs`. The panel asked the first about both, so every
      // rig run 404'd -- 308 of those in one evening across eleven run ids --
      // and the card an operator watches while their own browser is being
      // driven never learned the job's name or how far through it was. The
      // panel says which kind it is asking about; it is the only thing that
      // knows, because it is what the worker told it.
      //
      // A rig run is already being polled once a second by `pollRigRun`, and
      // the panel asked for it again on every one of its own refreshes -- two
      // fetchers on one row, about two `GET /v1/workflow-runs/{id}` a second
      // for the length of a run. The picture the worker is already holding is
      // the same answer, so it is handed over when it is fresh enough to be
      // the one the poll would have returned.
      if (
        message.source === "rig" &&
        rigRunShown?.id === message.runId &&
        Date.now() - rigShownAt < K_RUN_POLL_MS
      )
        return rigRunShown;
      if (message.source !== "rig") return api.run(message.runId);
      // And what it fetches becomes the held picture, so the poll a moment
      // later has nothing to ask for either. One row, one reader.
      rigRunShown = await api.rigRun(message.runId);
      rigShownAt = Date.now();
      return rigRunShown;
    case "skill":
      return api.skill(message.skillId);
    case "summary":
      return api.summary(message.days);
    case "what-this-browser-said": {
      // What is waiting to go up on the next beat, for the operator standing
      // in front of the browser that refused. Read only: the heartbeat still
      // takes them, and a panel that emptied the buffer to draw it would cost
      // the deployment the same lines.
      return await said();
    }
    case "keep-secret": {
      // Straight through to the backend and gone. Not held here even for the
      // length of this function longer than it takes to send: a worker that
      // kept a password in a variable is a worker whose crash dump has one.
      try {
        const kept = await api.keepSecret({
          system: message.system,
          field: message.field,
          value: message.value,
        });
        return { ok: true, key: kept.key };
      } catch (error) {
        return { ok: false, error: error.problem?.detail || error.message };
      }
    }
    case "hold-secret-once": {
      // The same one-way trip as `keep-secret`, to the door that keeps
      // nothing: the deployment holds it for the next step that types it and
      // forgets it after.
      try {
        const held = await api.holdSecretOnce({
          system: message.system,
          field: message.field,
          value: message.value,
          runId: message.runId,
        });
        return { ok: true, key: held.key, until: held.until };
      } catch (error) {
        return { ok: false, error: error.problem?.detail || error.message };
      }
    }
    case "answer-waiting": {
      // The press on a card a rule left waiting. Here rather than in the panel
      // because the credential lives in this worker, and the backend takes the
      // name off it: an unattended write happens because somebody said so, and
      // the somebody is whoever is holding this browser.
      try {
        const answered =
          message.answer === "approve"
            ? await api.approveWaiting(message.confirmationId)
            : await api.declineWaiting(message.confirmationId);
        if (answered.run_id) {
          // So the panel draws the run it just started, rather than waiting
          // for the first command to arrive and tell it.
          await state.setActiveRun({
            runId: answered.run_id,
            at: Date.now(),
            source: "rig",
          });
        }
        return { ok: true, ...answered };
      } catch (error) {
        return { ok: false, error: error.problem?.detail || error.message };
      }
    }
    case "do-this-here": {
      // "Do this here", from the card that just offered the job. The rule is
      // written on the backend -- a trigger, with the operator's credential
      // behind it -- and this worker is where that credential lives.
      //
      // The page comes from the OFFER and not from whichever tab the panel is
      // docked beside. The offer is about a page the miner recorded the job
      // starting on, and a rule made about the tab somebody happened to have
      // in front of them is a rule about the wrong page that fires forever.
      const nudge = (await state.nudges()).find(
        (n) => n.id === message.nudgeId,
      );
      if (!nudge || !nudge.workflowId)
        return { ok: false, error: "no such offer" };
      const page = rulePage(`https://${nudge.startsOn || ""}`);
      if (!page) return { ok: false, error: "that offer does not name a page" };
      try {
        const made = await api.makeArrival({
          workflow_id: nudge.workflowId,
          device_id: await state.deviceId(),
          page,
          values: nudge.values || {},
        });
        // Read back rather than assumed: the rule is only in force once this
        // browser holds it, and the next navigation is what reads this list.
        await refreshArrivals();
        return { ok: true, trigger_id: made.id, page };
      } catch (error) {
        return { ok: false, error: error.problem?.detail || error.message };
      }
    }
    case "ask-about-offer": {
      // The same yes, for an offer that cannot simply run: something is
      // missing, or something it holds will not fit the box it goes in. The
      // question goes into the operator's own conversation and the existing
      // answering path takes it from there -- one question, one answer, and
      // when the last one lands the job starts on this press.
      //
      // The press ends the offer, and the first version of this was wrong to
      // say otherwise.
      //
      // It reasoned that the offer had been "taken up" rather than accepted
      // and that the RUN would end it -- and then nothing ever did. The card
      // stayed open and pressable through the question, the answer and the
      // 201, so each further press stacked another identical question in the
      // thread: three of them on the deployment 2026-09-18, for one request.
      //
      // A press is a yes. What it buys is a question rather than a run, and
      // from that moment the THREAD holds the state -- which is the rule this
      // whole surface keeps, and the reason nothing is lost by ending the card:
      // somebody who walks away mid-answer comes back to the question, in
      // their conversation, with everything established still on it.
      //
      // Claimed under the same lock and before the call, for `start-rig-run`'s
      // reasons: between a check outside it and the POST sits a network call,
      // and anything reading the list meanwhile would find the offer open and
      // end it a second time.
      const claimed = await serially(async () => {
        const held = await state.nudges();
        const one = held.find((n) => n.id === message.nudgeId);
        if (!one || one.source !== "rig") return { error: "no such offer" };
        if (one.state !== "open")
          return { error: "this offer has already ended" };
        await state.setNudges(
          held.map((n) =>
            n.id === one.id
              ? { ...n, state: "accepted", endedAt: Date.now() }
              : n,
          ),
        );
        return { nudge: one };
      });
      if (claimed.error) return { ok: false, error: claimed.error };
      const found = claimed.nudge;
      try {
        const asked = await api.askAboutOffer({
          workflow_id: found.workflowId,
          title: found.title || "",
          values: found.values || {},
          missing: found.missing || [],
          items: Array.isArray(found.items) ? found.items : [],
          // What the offer was told each box holds. Sent back rather than
          // looked up again: a run that learned a limit in between would
          // change the question under somebody already reading it.
          limits: found.tooLong || {},
          // The mail this was read out of, so the run the ANSWER starts
          // answers to it -- the same as one this press starts directly. The
          // two doors disagreeing about that is invisible to a person and
          // costs them the reply that would have finished the job.
          mail_thread: found.mailThread || "",
          about: found.mailSubject || "",
          watched: true,
        });
        await narrate(
          `asked about ${found.candidateId} in the conversation: ${asked.asked || "nothing to ask"}`,
        );
        return { ok: true, asked: asked.asked || "" };
      } catch (error) {
        // Nothing was asked, so nothing was decided: the offer goes back to
        // being theirs to answer. The same rule `start-rig-run` keeps when a
        // run refuses to start -- a failed press is not an ending.
        await serially(async () => {
          const now = await state.nudges();
          await state.setNudges(
            now.map((n) =>
              n.id === found.id ? { ...n, state: "open", endedAt: null } : n,
            ),
          );
        });
        return { ok: false, error: error.problem?.detail || error.message };
      }
    }
    case "retry-rig-run":
    case "undo-rig-run": {
      // Run a mined job with values the panel already holds: the job that
      // takes back what a run made, or the job that stopped for a reason that
      // had nothing to do with it and is worth one more press.
      //
      // One case for both, because they are the same act -- an ordinary rig
      // run of an ordinary mined job -- and the only difference is which run
      // it names.
      //
      // An ordinary rig run of an ordinary mined job, and deliberately not a
      // special path: the delete goes through the same ladder, the same write
      // gate and the same belts as anything else, and an undo that skipped
      // them would be the one write in this system nobody checked.
      //
      // Its own case rather than `start-rig-run`, which finds and claims an
      // OFFER -- there is no offer behind an undo, and passing a nudge id that
      // does not exist would be refused for the wrong reason.
      if (!message.workflowId || !message.values)
        return { ok: false, error: "an undo with nothing to undo" };
      try {
        const run = await api.rigStart({
          workflow_id: message.workflowId,
          device_id: await state.deviceId(),
          values: message.values,
          // The things a repeating job was asked to do, where there were any.
          // A retry of a job that was making three records has to make the
          // same three.
          items: Array.isArray(message.items) ? message.items : [],
          live: true,
          allow_focus: true,
          watched: true,
          // Which run this takes back. The backend refuses a second undo of
          // the same run, which is what a double press in two panels is.
          undoes_run: message.undoesRun || "",
          // And the conversation the request came out of, so a retry that
          // comes up short can still be answered by a reply to that mail.
          mail_thread: message.mailThread || "",
        });
        await narrate(
          message.undoesRun
            ? `taking back what ${message.workflowId} made: run ${run.id}`
            : `trying ${message.workflowId} again: run ${run.id}`,
        );
        await state.setActiveRun({
          runId: run.id,
          at: Date.now(),
          source: "rig",
        });
        return { ok: true, run_id: run.id };
      } catch (error) {
        return { ok: false, error: error.problem?.detail || error.message };
      }
    }
    case "start-rig-run": {
      // Yes, on an offer the rig made. The press is in the panel, where
      // somebody can read what it says; the run is started here, because the
      // rig's credential lives in this worker and nowhere a page can reach.
      // Found, checked and claimed under one lock. The check-then-act has to
      // be one step: with the lookup outside the lock, an ending that landed
      // in the gap -- a sweep, a drop from a second panel window -- would have
      // reported its fate and then been overwritten to `accepted` here, which
      // is two fates for one offer and a live run behind a refusal. Only while
      // it is still asking: an offer that was dropped, swept or already taken
      // has reported its fate, and starting a run off it would report a second
      // one -- so this refuses, and reports nothing. The panel disables the
      // card on the first press; this is the guard that holds when the panel
      // is an older copy or a second window.
      const claimed = await serially(async () => {
        const held = await state.nudges();
        const found = held.find((n) => n.id === message.nudgeId);
        if (!found || found.source !== "rig") return { error: "no such offer" };
        if (found.state !== "open")
          return { error: "this offer has already ended" };
        // Claimed before the POST, not after. Between the two sits a network
        // call that can take a second, and anything else reading the list
        // meanwhile would find the offer still `open` and end it.
        await state.setNudges(
          held.map((n) =>
            n.id === found.id
              ? { ...n, state: "accepted", endedAt: Date.now() }
              : n,
          ),
        );
        return { nudge: found };
      });
      if (claimed.error) return { ok: false, error: claimed.error };
      const nudge = claimed.nudge;
      // What the operator typed into the panel wins over what the prefix read
      // off the page: they are looking at both, and the panel is the later word.
      const values = { ...(nudge.values || {}), ...(message.values || {}) };
      // The things the sentence named, as they were read. What the operator
      // typed into the card fills the gaps in the job's shared values, not in
      // one thing's -- there is one box per parameter on the card and three
      // things behind it, so a typed value that overwrote each thing's own
      // would make three identical records.
      const items = Array.isArray(nudge.items) ? nudge.items : [];
      let started;
      try {
        // No `started_by`. The backend reads who authorised the press off the
        // credential it arrived on; a body field saying so is a signature
        // nobody checked, written into the row an audit reads first.
        started = await api.rigStart({
          workflow_id: nudge.workflowId,
          values,
          items,
          device_id: await state.deviceId(),
          // `matched`, not `from_step`. `k` is how many SHAPE ENTRIES the tail
          // matched and an entry is one cited gesture, so a step of four
          // gestures is four of them -- 19 entries over 6 steps on the first
          // real job this system mined. Sent as `from_step` it marked steps
          // done that nobody had done, and above the step count the press came
          // back refused. The backend has the steps behind the shape and does
          // the conversion there.
          live: true,
          allow_focus: true,
          matched: nudge.k || 0,
          // Somebody is looking at this. The press came from an open panel, so
          // the run does the job ON THE SCREEN -- it types into the form and
          // presses Save -- instead of replaying the call the demonstration
          // made. Both end with one record; only one of them is something the
          // person watching can see happen. A trigger firing at three in the
          // morning never comes through here, and is left to replay.
          watched: true,
          // The mail this request came out of, where it came out of one.
          //
          // An id, never a word of anybody's mail. It buys the run an address:
          // one that comes up short can be found again by a REPLY to that
          // mail, because the person who knows the missing value is usually
          // whoever sent the request -- and they do not have this panel open.
          // Empty for every press that was not a mail offer.
          mail_thread: nudge.mailThread || "",
        });
      } catch (error) {
        // No run was started, so nothing was accepted. The offer goes back to
        // being the operator's to answer, and no fate is reported -- a failed
        // press is not an ending.
        await serially(async () => {
          const now = await state.nudges();
          await state.setNudges(
            now.map((n) =>
              n.id === nudge.id ? { ...n, state: "open", endedAt: null } : n,
            ),
          );
        });
        return { ok: false, error: error.problem?.detail || error.message };
      }
      // `started.id`, not `started.run_id`: `POST /v1/workflow-runs` answers
      // 201 with the whole `WorkflowRunModel`, where the rig answered 202 and
      // `{"run_id": ...}`. Read as `run_id` this is `undefined`, and the panel
      // draws a run with no id it can ever poll or approve.
      await state.setActiveRun({
        runId: started.id,
        at: Date.now(),
        source: "rig",
      });
      // From here the panel draws the run itself, a row per step as it lands.
      // Beside the record that says a rig run is active, because that record is
      // the whole of what `pollRigRun` reads. Not awaited: the press answers as
      // soon as the run exists, and the first picture of it is a moment behind
      // that either way.
      void pollRigRun();
      void hideNudge(nudge.tabId);
      void report(nudge, "accepted", started.id);
      // One fewer waiting, on the icon as well as in the panel.
      void badge();
      return { ok: true, run_id: started.id };
    }
    case "drop-nudges": {
      // Many at once, in ONE pass over the list.
      //
      // A backlog can be a month deep -- the panel groups it by day for
      // exactly that -- and clearing it one `drop-nudge` at a time would be
      // thirty-four read-modify-writes of a single storage key. `serially`
      // would order them, and each would still re-read, re-map and re-write
      // the whole list; the lock is the thing that makes that correct rather
      // than cheap. One pass is both.
      //
      // Reported one by one, because a fate is per offer: a job dismissed
      // thirty times is a job not worth offering, and a single "34 dropped"
      // says nothing about which.
      const wanted = new Set(message.nudgeIds || []);
      if (!wanted.size) return { ok: true, dropped: 0 };
      return serially(async () => {
        const held = await state.nudges();
        // Only the ones still open. Answering and dropping are two paths to
        // the same place, and the first one out of `open` is the one that
        // ends it.
        const going = held.filter(
          (one) => wanted.has(one.id) && one.state === "open",
        );
        if (!going.length) return { ok: true, dropped: 0 };
        const gone = new Set(going.map((one) => one.id));
        const at = Date.now();
        await state.setNudges(
          held.map((one) =>
            gone.has(one.id)
              ? { ...one, state: "dismissed", endedAt: at }
              : one,
          ),
        );
        void badge();
        for (const one of going) {
          void hideNudge(one.tabId);
          void report(one, "dismissed");
        }
        return { ok: true, dropped: going.length };
      });
    }
    case "drop-nudge": {
      // "No thanks", from the panel. An offer taken off the screen unanswered
      // is one that was refused, and saying so is the whole point of reporting
      // fates: a job that is always dismissed is a job not worth offering.
      return serially(async () => {
        const held = await state.nudges();
        const nudge = held.find((n) => n.id === message.nudgeId);
        // Only while it is still open. Answering and dropping are two paths to
        // the same place, and the first one out of `open` is the one that ends
        // it -- so an offer reports its fate once however many arrive.
        if (!nudge || nudge.state !== "open") return { ok: true };
        await state.setNudges(
          held.map((n) =>
            n.id === nudge.id
              ? { ...n, state: "dismissed", endedAt: Date.now() }
              : n,
          ),
        );
        void badge();
        void hideNudge(nudge.tabId);
        void report(nudge, "dismissed");
        return { ok: true };
      });
    }
    case "open-panel":
      // From the pill in the page. Opening it is all it does: the offer is in
      // the panel with its two answers, and pressing one there is what
      // authorises anything.
      if (sender?.tab?.id !== undefined)
        await chrome.sidePanel.open({ tabId: sender.tab.id });
      return { ok: true };
    // `candidates`, `teach-candidate`, `teach-together`, `answer-join`,
    // `dismiss-candidate` and `resolve-intent` were here, and are not any
    // more: every one of them served the mining pipeline's offer -- a card
    // that proposed teaching a skill from recordings, and a box that resolved
    // a sentence against the skills it had taught. This deployment runs the
    // rig, whose jobs come with their steps already. `nudge-answer`,
    // `never-watch-site`, `revise-run`, `say-to-run`, `look-in-the-mail` and
    // `panel-open` went the same way: nothing sent them.
    case "thread":
      return api.currentThread();
    case "new-thread":
      // A conversation somebody deliberately started. `current` answers with
      // the newest, so nothing else has to be told which one to draw.
      return api.newThread();
    case "run-workflow": {
      // "Run it here", off the learned-job card. By id, never by title: the
      // tenant holds three jobs called "Log in to Keycloak", and a sentence
      // naming one of them comes back as a question about which was meant.
      // A job short of a required value parks and asks in the conversation,
      // which is where that question belongs.
      if (!message.workflowId)
        return { ok: false, error: "no job to run" };
      try {
        const run = await api.rigStart({
          workflow_id: message.workflowId,
          device_id: await state.deviceId(),
          values: message.values || {},
          items: [],
          live: true,
          allow_focus: true,
          watched: true,
        });
        // The same record `start-rig-run` writes, field for field: `at` is
        // what `parkedRigRun` reads back as the run's `since`, and a record
        // written with a different name for it is a run card with no elapsed
        // time on it.
        await state.setActiveRun({
          runId: run.id,
          at: Date.now(),
          source: "rig",
        });
        void pollRigRun();
        return { ok: true, run_id: run.id, runId: run.id };
      } catch (error) {
        return { ok: false, error: error.problem?.detail || error.message };
      }
    }
    case "learned-jobs":
      // The jobs mined for this tenant, for the card that says what was
      // learned on the page beside the panel. The panel filters by host.
      return { jobs: await api.workflows(await state.deviceId()) };
    case "recent-runs": {
      // The rows, with each job's own title put back on them. The backend
      // answers `workflow_id` and this browser is already holding the shapes
      // -- a list reading "wfl_3f2a — done" tells nobody what was done.
      const runs = await api.rigRuns(message.limit || 12);
      const titles = new Map(
        (await shapesFor()).map((shape) => [shape.id, shape.title]),
      );
      return runs.map((run) => ({
        ...run,
        title: titles.get(run.workflow_id) || run.workflow_id,
      }));
    }
    case "thread-say": {
      const said = await api.say(message.threadId, message.text);
      // What the thread is waiting on NOW, off the reply that just changed it.
      //
      // `lookForAQuestion` is the only other writer and it runs on the minute
      // beat, so until this line the panel drew the old question for up to a
      // minute after it stopped standing. Measured on the deployment
      // 2026-09-22 at 01:24: the operator typed `no`, the door answered
      // "Dropped Create a Customer Type", and the question they had just
      // dropped was still sitting under it -- a job that no longer existed
      // asking for a value. The reply already carries the whole thread, so
      // this costs no request.
      await holdTheQuestion(said);
      // The reply already read the sentence against this tenant's jobs, so the
      // offer is built from what came back rather than from a second reading
      // of the same words. That second reading was a second model call per
      // sentence, and the two could disagree.
      const placed = jobInTheReply(said);
      // The last answer to a question this job asked starts it. They pressed
      // yes before any of the questions; asking for the same permission a
      // second time is how a panel teaches somebody to stop reading it.
      if (placed?.resume) void resumeTheJob(placed);
      else if (placed) void offerFromJob(placed, message.tabId ?? null);
      // And a sentence the thread is still holding a question open for is not
      // an unread sentence. `offerFromWords` is for the case where the door
      // read it and placed no job at all.
      else if (!stillAsking(said))
        void offerFromWords(message.text, message.tabId ?? null);
      return said;
    }
    case "run-skill":
      // The press. `from-preview`, not the ordinary run endpoint -- the
      // operator read the preview this promotes on, in this browser, and a
      // run started anywhere else would not be the run they read.
      // `message.version` is the version the panel drew the preview from, and
      // is sent rather than left to the backend: what the operator read has to
      // be what runs, and "the newest one" is a different version the moment
      // anything re-teaches or repairs the skill between the read and the
      // press.
      return api.runFromPreview(
        message.skillId,
        message.parameters,
        message.deviceId,
        message.intent,
        message.version,
      );
    case "panel-console":
      // Where the console is, and nothing else. The token used to go with it,
      // for a console framed inside the panel; that frame is gone, and the
      // token no longer leaves this worker for the panel at all.
      return { consoleUrl: await state.consoleUrl() };
    case "approve-rig-run": {
      // The press on the awaiting row. It comes here rather than going to the
      // rig from the panel for the same reason `start-rig-run` does: the rig's
      // bearer lives in this worker and in nothing a page can reach.
      //
      // And only for the run this browser is actually driving. The panel draws
      // Approve off a status read that can be a couple of seconds old, so a
      // card left standing after the run ended -- or a second window showing a
      // run that has since been superseded -- could otherwise authorise a live
      // write in somebody's warehouse against a run nobody here is watching.
      if (message.runId !== (await state.activeRun())?.runId) {
        return {
          ok: false,
          error: "that run is not the one this browser is driving",
        };
      }
      try {
        return await api.rigApprove(message.runId, await state.deviceId());
      } catch (error) {
        return { ok: false, error: error.problem?.detail || error.message };
      }
    }
    case "abort-run": {
      // Both halves, in this order. `abort` is local and immediate: every
      // later command for this run is refused here, so nothing else reaches
      // the page whatever the network does next. But the run is driven from
      // the backend, and until this told it so it went on stepping -- asking
      // for command after command that this browser refused -- which is a
      // Stop button that stops the browser and not the run.
      const here_ = abort(message.runId);
      try {
        // Whoever is driving it is who has to be told. A run the rig started
        // is a run the backend has never heard of, and `POST /runs/{id}/stop`
        // there would answer 404 while the rig went on stepping -- a Stop
        // button that stops the browser and not the run, which is the one
        // thing a stop control must never be. Read off the same mirrored
        // `source` `noteFinished` reads; a record with no source is a backend
        // run. ponytail: `state.activeRun()` is one slot, so a rig run and a
        // backend run in flight at once would answer for each other here --
        // the same ceiling `commands.js`'s `latest` already has, widened
        // together or not at all.
        const active = await state.activeRun();
        if (active?.runId === message.runId && active.source === "rig") {
          await api.rigAbort(message.runId);
        } else {
          await api.stopRun(message.runId);
        }
      } catch (error) {
        // Only what is worth showing anybody reaches here: `api.stopRun`
        // swallows the 409 the backend answers when there was nothing left to
        // stop -- a run that has just finished, or a second press -- because
        // that is an ordinary race and not a fault. What is left is a backend
        // this browser could not reach at all, which means a run still
        // stepping somewhere with nobody having been told to stop it, and the
        // operator who just pressed Stop is the one person who needs to know.
        return { ok: true, aborted: here_, error: error.message };
      }
      return { ok: true, aborted: here_ };
    }
    case "run-wrong": {
      // "Undo that" and "it's wrong" both land here first, before whichever of
      // them goes on to start a reversal run -- see `panel.js`'s `undoRun` and
      // `wasWrong`. The record is what counts against the skill and is sent
      // regardless of what happens next.
      const result = await api.runWrong(message.runId, message.because);
      const held = await state.finishedRun();
      // Keyed on which button was pressed (`message.keepForRetry`, set only by
      // `undoRun`), not on whether this run happens to have a reversal -- see
      // `afterRunWrong` in `state.js` for why keying on `reversal` alone was
      // wrong: it kept "Undo that" alive after "It's wrong -- I'll fix it",
      // which would reverse the operator's own hand-made correction.
      if (held?.id === message.runId) {
        await state.setFinishedRun(
          afterRunWrong(held, message.because, Boolean(message.keepForRetry)),
        );
      }
      return result;
    }
    case "purge": {
      // The device's own queue first, and unconditionally. What is still
      // sitting here has not reached the server, so deleting it there and
      // leaving it here would have the next flush upload the hour the operator
      // just asked to be rid of.
      const hours = Number(message.hours) || 1;
      const since = new Date(Date.now() - hours * 3600_000).toISOString();
      await queue.clear();
      await state.newQueueEpoch();
      // A batch already sent once is named by the epoch that has just been
      // rotated; without clearing it the next flush would retry rows that no
      // longer exist under an id from before the purge.
      await state.setPendingBatch(null);
      // The tails too. They are the same gestures, held per tab to recognise a
      // job from: an operator who asks for the last hour to be forgotten has
      // not asked for the last hour of it to go on being matched against.
      await state.setTails({});
      const gone = await api.forget(since);
      await state.setLastError("");
      return gone;
    }
    case "watch-tab": {
      const tabId = message.tabId ?? sender?.tab?.id ?? null;
      if (tabId === null) return { error: "no tab to watch" };
      let url = message.url || "";
      if (!url) {
        try {
          url = (await chrome.tabs.get(tabId)).url || "";
        } catch {
          return { error: "that tab is gone" };
        }
      }
      const watched = await watch(tabId, url);
      // Into the tab as it stands, not on its next navigation. An operator who
      // presses this in the middle of a job should not have to reload the page
      // and lose the form they were halfway through.
      await injectHere(tabId, url);
      return { watched };
    }
    case "always-watch": {
      // "Watch this site, wherever it opens." Said once about a system rather
      // than once per tab, because a tab id lives for as long as one tab and
      // the work does not.
      const tabId = message.tabId ?? sender?.tab?.id ?? null;
      let url = message.url || "";
      if (!url && tabId !== null) {
        url = (await chrome.tabs.get(tabId).catch(() => ({}))).url || "";
      }
      const host = hostOf(url);
      if (!host) return { error: "that is not a page this can watch" };
      await state.setAlwaysWatch(alsoWatch(host, await state.alwaysWatch()));
      // And this tab now, not on its next navigation: an operator who says it
      // while looking at the page means this page.
      if (tabId !== null) await watchIfAlways(tabId, url);
      // Every other tab already open on it, for the same reason -- saying it
      // about a system and having four of its tabs stay blind is the defect
      // this replaces, one layer along.
      for (const tab of await chrome.tabs.query({ url: `*://${host}/*` })) {
        if (tab.id !== tabId) await watchIfAlways(tab.id, tab.url || "");
      }
      return { always: await state.alwaysWatch() };
    }
    case "unwatch-tab": {
      const tabId = message.tabId ?? sender?.tab?.id ?? null;
      if (tabId === null) return { error: "no tab to stop watching" };
      return { watched: await unwatch(tabId) };
    }
    case "watches": {
      // Only the rules for the host the asking frame is on. A page never
      // learns that this operator watches anything anywhere else, and the
      // host rule is the extension's one copy of it rather than a second one
      // in a content script.
      const host = hostOf(sender?.url || "");
      const held = await state.watches();
      return {
        watches: host
          ? held.filter((watch) => hostMatches(host, watch.host))
          : [],
      };
    }
    case "watch-matched": {
      // The one place a value read out of somebody's mail leaves this
      // machine, so the checks are here rather than only in the page: the
      // watch has to be one this browser holds, the frame has to be on that
      // watch's host, and what goes is the names the watch declared and
      // nothing else. A page that made this message up gets nowhere.
      const deviceId = await state.deviceId();
      const host = hostOf(sender?.url || "");
      const watch = (await state.watches()).find(
        (each) => each.id === message.triggerId,
      );
      if (!deviceId || !watch || !hostMatches(host, watch.host)) {
        return { error: "no such watch" };
      }
      const values = {};
      for (const declared of watch.values || []) {
        const given = message.values?.[declared.name];
        if (typeof given === "string" && given)
          values[declared.name] = given.slice(0, MAX_VALUE);
      }
      // One identity per match, found before it is minted. `watch.js` reports
      // per frame, so a mail sitting open reports itself repeatedly; the id is
      // what tells the server those are one match and not four, and minting a
      // fresh one each time would have the conversation repeat itself once a
      // frame. Reusing the held offer's id makes the second report a no-op at
      // both ends.
      if (watch.asks) {
        // A question, not a job. What leaves the machine is the same shape as
        // any other matched value -- read now, sent as a parameter, never
        // written down -- and what comes back is an answer rather than an
        // offer to run something. Nothing is held: a question already answered
        // has nothing left to press.
        const question = values[QUESTION];
        if (!question)
          return {
            error: "this mail has no question where the watch says one is",
          };
        const answer = await api.lookup(question);
        await state.setAnswer({
          said: question,
          tabId: sender?.tab?.id ?? null,
          askedAt: Date.now(),
          ...answer,
        });
        return { ok: true, asked: true };
      }
      const offerId =
        (await sameOfferAs(watch, values))?.id || crypto.randomUUID();
      const offer = await api.watchMatched(deviceId, watch.id, values, offerId);
      await hold(watch, values, offer, offerId);
      return { ok: true, offer };
    }
    case "watch-nearly": {
      // A rule that almost fired. Held and shown, never acted on: what makes
      // it a near miss is that the operator's rule did not match, and a system
      // that acted on nearly would be deciding that their words meant
      // something they did not write.
      //
      // The same ownership check the match path makes, for a smaller reason --
      // nothing here starts anything -- but a page that made this message up
      // should still get nowhere.
      const host = hostOf(sender?.url || "");
      const watch = (await state.watches()).find(
        (each) => each.id === message.triggerId,
      );
      if (!watch || !hostMatches(host, watch.host))
        return { error: "no such watch" };
      // The terms are the watch's own, read from the rule this worker holds
      // rather than from the message: a page that sent a different string
      // would otherwise put its own text on the panel.
      const mine = new Set(
        (watch.terms || []).map((term) => String(term.contains)),
      );
      const terms = (message.terms || [])
        .map(String)
        .filter((term) => mine.has(term));
      if (!terms.length) return { ok: true };
      await serially(async () => {
        const held = await state.nearMisses();
        const fresh = [
          { triggerId: watch.id, terms, at: Date.now() },
          // One line per rule: a mailbox open all morning would otherwise say
          // the same thing forty times.
          ...held.filter((one) => one.triggerId !== watch.id),
        ];
        await state.setNearMisses(fresh.slice(0, MOST_NEAR_MISSES));
      });
      return { ok: true };
    }
    case "watch-fire": {
      // The press. The values go up again because nothing was kept: this
      // browser is the only place they exist, which is the whole shape of a
      // watch. From there it is an ordinary fire -- the trigger reads only the
      // names it declared, and a run whose required inputs are empty is
      // skipped with the reason legible rather than started.
      const deviceId = await state.deviceId();
      const offers = await state.offers();
      const offer = offers.find((each) => each.id === message.offerId);
      if (!deviceId || !offer) return { error: "that offer is gone" };
      // What the operator saw on the card, not what the mail happened to fill.
      // The two are the same until they change one, and when they do it is the
      // change that has to reach the warehouse -- a press that silently ran the
      // mail's value would be the panel showing one thing and doing another.
      // Values only, and only names the offer already carries: a body assembled
      // in a panel is not a way to reach a name the watch never declared.
      const chosen = { ...offer.read };
      for (const [name, value] of Object.entries(message.values || {})) {
        if (name in chosen || (offer.missing || []).includes(name))
          chosen[name] = String(value);
      }
      const fired = await api.watchFire(deviceId, offer.triggerId, chosen);
      // Kept when nothing started, so the card can say why. A laptop that was
      // closed is the ordinary one of these, and it is worth pressing again.
      await state.setOffers(
        fired.run_id
          ? offers.filter((each) => each.id !== offer.id)
          : offers.map((each) =>
              each.id === offer.id ? { ...each, skipped: fired.skipped } : each,
            ),
      );
      return fired;
    }
    case "drop-offer": {
      // ponytail: an ignored offer is evidence about whether the watch is any
      // good, and this records nothing -- it drops it here and the control
      // plane never hears. The taken half is already history (the trigger's
      // `last_fired_at` and the run under it); the ignored half needs somewhere
      // to count it and a definition of ignored that tells a person saying no
      // apart from a laptop that was asleep. A counter on the trigger and one
      // endpoint, the day somebody reviews watches.
      const offers = await state.offers();
      await state.setOffers(
        offers.filter((each) => each.id !== message.offerId),
      );
      return { ok: true };
    }
    case "status":
      return status(sender);
    default:
      return { error: `no such message: ${message?.kind}` };
  }
}

// -- pushing the state, rather than being asked for it every two seconds -----

/** The panels connected to this worker right now.
 *
 * A `Set` and not one port: two windows can each have the panel open, and both
 * are looking at the same browser.
 */
const watching = new Set();

/** The last finished run, re-read from the backend once per worker life.
 *
 * The row is a SNAPSHOT: `finishing.js` stores what the run looked like the
 * moment it ended, and the card is drawn from that for an hour. What the
 * backend says about a finished run can change afterwards -- whether it can be
 * taken back, whether it can be pressed again -- and twice on 2026-09-19 an
 * operator sat in front of a card that offered neither, on a run the deployment
 * would by then have offered both for.
 *
 * Once, and only for a row this worker did not write itself: a re-read on
 * every status poll is a call a second, and a row written by the worker that
 * is still running is as fresh as the backend was when it landed.
 */
let refreshed = null;

async function freshlyFinished() {
  const held = await finishedRun();
  if (!held?.id || held.source !== "rig" || refreshed === held.id) return held;
  refreshed = held.id;
  try {
    const now = await api.rigRun(held.id);
    if (!now) return held;
    await state.setFinishedRun({ ...held, ...now, at: held.at });
    return await finishedRun();
  } catch {
    // A backend this browser cannot reach right now is not a reason to drop a
    // card somebody is looking at.
    return held;
  }
}

/** How long to wait before pushing, so a burst of writes is one redraw.
 *
 * Every state change goes through `chrome.storage`, and a single gesture can
 * write three keys. Pushing per key would redraw the panel three times and
 * take the cursor out of whatever somebody was typing twice for nothing.
 */
const SETTLE_PUSH_MS = 120;
let pushing = null;

// `?.` for the same reason `chrome.sidePanel?.` above has it: this module is
// loaded by node in the self-checks, where `chrome` is whatever the test
// needed and nothing more.
chrome.runtime.onConnect?.addListener((port) => {
  if (port.name !== "panel") return;
  watching.add(port);
  // Lazily, the way the reconnect guidance says: nothing here retries, and a
  // port that has gone is simply dropped. The panel reopens it on its own next
  // beat, which is also what happens after this worker is evicted -- the
  // connection dies with it and the panel notices.
  port.onDisconnect.addListener(() => watching.delete(port));
  void pushStatus();
});

/** Every panel told what this worker now knows.
 *
 * `postMessage` on a port whose other end has gone throws SYNCHRONOUSLY rather
 * than reporting through `onDisconnect`, which is the one sharp edge of this
 * API -- so every send is guarded and a port that throws is dropped.
 */
async function pushStatus() {
  if (!watching.size) return;
  const now = await status(null);
  for (const port of [...watching]) {
    try {
      port.postMessage({ kind: "status", status: now });
    } catch {
      watching.delete(port);
    }
  }
}

// What "something changed" means, without a call site having to remember to
// say so. Everything the panel draws is mirrored into `chrome.storage` --
// deliberately, because this worker is evicted between commands -- so the
// storage event is the one signal that cannot be forgotten when a new piece of
// state is added next month.
chrome.storage.onChanged?.addListener(() => {
  if (!watching.size) return;
  clearTimeout(pushing);
  pushing = setTimeout(() => void pushStatus(), SETTLE_PUSH_MS);
});

/** How many offers this browser holds: enough that the morning's mail is still
 * there after lunch, few enough that a watch somebody wrote badly cannot fill
 * the disk with what it read. */
/* How often the mailbox is read, and how long a look that found nothing to
   read waits, are `looking.js`'s -- the rule needed a test of its own after it
   parked a browser for ten minutes over a two-second restart. */

/** Read the operator's recent mail, at most this often.
 *
 * The throttle is here and not in the panel: the panel is closed most of the
 * day and there may be more than one of them, so a window's own timer is not a
 * statement about how often this browser reads a mailbox.
 *
 * Nothing is returned to the panel to draw. What a look produces is an offer in
 * the operator's own thread, and the panel is already polling that -- so the
 * card arrives the way every other message does, and this call has no second
 * path to keep working.
 */
/** Whether the mailbox is being read RIGHT NOW, and when the last read ended.
 *
 * In memory and not in storage, unlike everything else about the look: this is
 * true for the two seconds a fetch is out, and a flag that outlived the worker
 * that set it would have the panel animating a call nobody is making.
 */
let readingTheMail = null;

export async function lookInTheMail() {
  const last = await state.mailLooked();
  const since = Date.now() - (last?.at || 0);
  const wait = waitBeforeLooking(last);
  if (last && since < wait) return { ok: true, skipped: "looked recently" };
  // Written BEFORE the call, so a look that takes a while does not have four
  // more started on top of it by the ticks that land while it is out.
  await state.setMailLooked({ at: Date.now(), reached: true, answered: true });
  readingTheMail = Date.now();
  try {
    const looked = await api.fromTheMail();
    // `answered`, beside `reached`: the deployment replied, so whatever it
    // said about the mailbox is a fact about the mailbox. That is what buys
    // the long wait -- see `looking.js`.
    await state.setMailLooked({
      at: Date.now(),
      reached: !String(looked?.why || "").includes("could not be reached"),
      answered: true,
    });
    // Kept one at a time, and a failure to keep one is NOT a failure to reach
    // the mailbox.
    //
    // This loop used to sit bare inside the try below, so a throw anywhere in
    // `offerFromMail` was caught by a handler written for a connector that is
    // not there: the look reported `ok`, marked the mailbox unreachable, and
    // said nothing. The offer was gone for good -- the backend claims a
    // message id BEFORE it reads it, so a mail whose offer is lost here is a
    // mail nothing will ever read again -- and the operator saw an empty
    // panel with no error in it.
    //
    // Measured on the deployment, 2026-09-17 at 19:38: the backend offered
    // `Create a Customer Type` from a mail, and no card ever appeared.
    let kept = 0;
    if (looked?.offered?.length || looked?.read)
      await narrate(
        `looked in the mail -- ${looked?.read || 0} read, ${(looked?.offered || []).length} offered`,
      );
    for (const offer of looked?.offered || []) {
      try {
        await offerFromMail(offer);
        kept += 1;
      } catch (error) {
        // Worth a red line, unlike a mailbox that could not be reached: the
        // mail WAS read, the job WAS recognised, and the request has now been
        // dropped by this browser and cannot arrive again.
        await state.setLastError(
          `a request read from your mail was lost before it could be offered: ${error}`,
        );
        await narrate(`mail offer lost: ${error}`);
      }
    }
    readingTheMail = null;
    return {
      ok: true,
      offered: kept,
      read: looked?.read || 0,
    };
  } catch (error) {
    readingTheMail = null;
    // A door that is not there yet, a backend being restarted, a browser with
    // no credential. None of them is worth a red line in the panel: the look is
    // a background convenience and the operator can always type the request.
    // Nothing was answered, so nothing is known about the mailbox: a backend
    // restarting, a wifi hop, a lid shut mid-call. It waits the ordinary
    // minute rather than the ten a deployment with no connector gets.
    await state.setMailLooked({
      at: Date.now(),
      reached: false,
      answered: false,
    });
    return {
      ok: true,
      skipped: error instanceof ApiError ? error.message : String(error),
    };
  }
}

const MAX_OFFERS = 20;

/** Keep an offer where the panel can find it.
 *
 * With the one thing the panel needs that the offer does not carry: what the
 * task is called. Read once, here, rather than by a panel polling for it every
 * two seconds -- and a name that could not be read leaves the card naming the
 * skill's id, which is uglier and still true.
 *
 * The watch's own terms travel with it, because they are what the card says
 * the mail was recognised by. They are the operator's own words and are
 * already in this browser; the sender and the subject that actually decided it
 * were read in the frame and forgotten there, and the mail is on the screen
 * the panel is docked beside.
 */
/** The offer already held for this match, if this mail has been seen before.
 *
 * The same mail seen again -- open in a second tab, or the page reloaded.
 * `watch.js` offers once per frame; this is the frame after that one.
 */
async function sameOfferAs(watch, read) {
  const held = await state.offers();
  return held.find(
    (each) =>
      each.triggerId === watch.id &&
      JSON.stringify(each.read) === JSON.stringify(read),
  );
}

async function hold(watch, read, offer, offerId) {
  const held = await state.offers();
  if (await sameOfferAs(watch, read)) return;
  // The name comes back with the offer now, because a watch may name a mined
  // job and there is no `/v1/skills/{id}` for one. The fetch stays as the
  // fallback for a backend that predates the field.
  const named =
    offer.title ||
    (await api.skill(offer.skill_id).catch(() => null))?.name ||
    "";
  await state.setOffers(
    [
      {
        id: offerId,
        at: Date.now(),
        triggerId: watch.id,
        skillId: offer.skill_id,
        workflowId: offer.workflow_id || null,
        skill: named,
        host: watch.host,
        terms: watch.terms || [],
        // What this browser read out of the mail, and what the task would run
        // with -- the trigger's own values under the mail's. Both, because
        // which is which is what somebody deciding needs to see.
        read,
        values: offer.values || {},
        missing: offer.missing || [],
        // Whether what the mail did not say stops the press. The deployment's
        // answer: a run that can read the operator's mailbox goes and looks
        // for the rest, and a card that refused to start would be asking for
        // what the run already knows how to find.
        canFind: Boolean(offer.can_find),
      },
      ...held,
    ].slice(0, MAX_OFFERS),
  );
}

/** What one value read out of a mail may be, mirroring the domain's `MAX_TERM`.
 * An order number is short; a hundred kilobytes under a parameter name is a
 * mail body that arrived through a sloppy mark. `watch.js` caps it where it is
 * read and this caps it where it would leave. */
const MAX_VALUE = 200;

/** How many almost-fired rules this browser remembers. One per rule, and
 * nobody has twenty mail rules; what this bounds is a browser left open for a
 * week. */
const MOST_NEAR_MISSES = 5;

/** The value name that makes a watch a question rather than a job, mirroring
 * the domain's `watch.QUESTION`. The same cap above applies to it: a question
 * somebody wrote in a mail is a sentence, and a hundred kilobytes under this
 * name is a mail body that arrived through a sloppy mark. */
const QUESTION = "question";

/* `hostOf` is `always.js`'s: the same question, and that one answers "" for a
   url that is not a page rather than naming the host of a `chrome://` one. */

/** The mail rules this browser holds, from the backend that keeps them.
 *
 * The rule only, and only the parts a page needs to evaluate one. A failure
 * leaves the last list standing: a backend that cannot be reached is not a
 * watch being withdrawn, and an operator whose laptop is on a train should
 * still be offered the mail in front of them.
 */
/** The page rules this browser holds, from the backend that keeps them.
 *
 * Exported, alone in this file, so `page-rules.test.mjs` can drive the one
 * thing that was missing on a real browser: the list was fetched when the
 * browser registered and at no other time, so a rule made anywhere else never
 * arrived. The heartbeat calls this beside `refreshWatches` now.
 *
 * Beside `refreshWatches` and refreshed with it. A failure leaves the last
 * list standing for the same reason: a backend that cannot be reached is not
 * an operator withdrawing a rule.
 */
export async function refreshArrivals() {
  const deviceId = await state.deviceId();
  if (!deviceId) return state.setArrivals([]);
  try {
    const triggers = await api.arrivals(deviceId);
    await state.setArrivals(
      (triggers || [])
        .filter((trigger) => trigger.arrival?.page)
        .map((trigger) => ({ id: trigger.id, page: trigger.arrival.page })),
    );
  } catch (error) {
    await state.setLastError(
      error instanceof ApiError ? error.message : String(error),
    );
  }
}

async function refreshWatches() {
  const deviceId = await state.deviceId();
  if (!deviceId) return state.setWatches([]);
  try {
    const triggers = await api.watches(deviceId);
    await state.setWatches(
      (triggers || [])
        .filter((trigger) => trigger.watch)
        // `asks` travels with the rule because the page evaluates the rule:
        // a watch that asks reads a question out of the mail and is answered,
        // where every other one becomes an offer to run something. The flag
        // rides on the watch rather than being looked up per match, so a
        // browser holding a stale list still knows which kind it holds.
        .map((trigger) => ({
          id: trigger.id,
          asks: Boolean(trigger.asks),
          ...trigger.watch,
        })),
    );
  } catch (error) {
    await state.setLastError(
      error instanceof ApiError ? error.message : String(error),
    );
  }
}

/** The hosts a watch script may run on: the ones with a watch, and only while
 * this browser is doing anything at all.
 *
 * Not gated on `capturing()`, deliberately. A watch is not observation -- it
 * reads a mail and forgets it, and the tenant's capture switch is about the
 * evidence plane. It *is* gated on both pauses, because those mean this
 * browser is quiet, and a script of ours running in a mailbox while the
 * operator believes everything is paused is the badge lying.
 */
async function watchHosts() {
  const [deviceId, paused, serverPaused, watches] = await Promise.all([
    state.deviceId(),
    state.paused(),
    state.serverPaused(),
    state.watches(),
  ]);
  if (!deviceId || paused || serverPaused) return [];
  return watches.map((watch) => watch.host);
}

/** How many batches one drain will send before giving the alarm its turn back.
 * A demonstration is minutes of work, not hours; a queue that still is not
 * empty after this many is a queue with a problem, and the alarm will carry on
 * with it. */
const MOST_BATCHES = 50;

/** Upload until there is nothing left, rather than one batch's worth.
 *
 * Only the paths that need emptiness use this -- sealing a demonstration, and
 * the operator asking to flush before closing the laptop. The alarm stays one
 * batch a tick, which is what paces a busy day.
 */
async function drain() {
  let last = { uploaded: 0 };
  for (let batch = 0; batch < MOST_BATCHES; batch += 1) {
    last = await flushQueue();
    if (last.error || !last.uploaded || !last.remaining) return last;
  }
  return last;
}

async function flushQueue() {
  const deviceId = await state.deviceId();
  const allowed = await capturing();
  if (!deviceId || !allowed.on)
    return { uploaded: 0, because: allowed.because || "not registered" };
  try {
    const result = await flush(deviceId);
    if (result.error) await state.setLastError(result.error);
    else if (result.uploaded || result.screenshots)
      await state.setLastError("");
    return result;
  } catch (error) {
    // A 401 already dropped the token in api.js; settle() reflects that as
    // "no credential" on the next status read rather than repeating it here.
    const message = error instanceof ApiError ? error.message : String(error);
    await state.setLastError(message);
    return { uploaded: 0, error: message };
  }
}

/** Register this browser profile, then apply whatever policy came back. */
async function register(label) {
  // The queue was cleared and the epoch rotated by the `sign-in` case before
  // this was reached, so there is nothing of a previous operator's left to
  // guard against here -- and nothing that survives this call failing.
  const registered = await api.register(label || defaultLabel(), VERSION);
  await state.setDeviceId(registered.device_id);
  // After the id, so a worker evicted between the two leaves a device that
  // re-registers on its next beat rather than one that has no id and has to be
  // signed in again. Registration is idempotent on the label and hands the
  // secret back every time, so doing it twice costs a request.
  await state.setDeviceSecret(registered.device_secret || "");
  await state.setPolicy(registered.policy);
  await state.setLastError("");
  // Before `settle`, which is what registers the script that evaluates them.
  await refreshWatches();
  await refreshArrivals();
  await settle();
  return status();
}

/** Read this operator's conversation for a question waiting on them.
 *
 * Kept on the worker rather than computed in `status()`: the panel polls that
 * twice a second and the thread is a network round trip. Failure is silence --
 * a browser that cannot reach the backend has nothing to say about questions,
 * and a banner drawn from a stale read would be worse than none.
 */
/** Hold what this thread is waiting on, or nothing.
 *
 * Written only when it changes, because every write wakes the panel's storage
 * listener and redraws the column.
 */
async function holdTheQuestion(thread) {
  const waiting = questionIn(thread);
  const held = await state.question();
  if ((held?.id || null) !== (waiting?.id || null)) await state.setQuestion(waiting);
  return waiting;
}

async function lookForAQuestion() {
  try {
    await holdTheQuestion(await api.currentThread());
  } catch {
    // Offline, or a backend that has no threads. Leave whatever is held: a
    // question does not stop waiting because a poll failed.
  }
}

async function beat() {
  const deviceId = await state.deviceId();
  if (!deviceId) return;

  // A browser registered before devices had secrets has an id and nothing to
  // prove it with, and every device-scoped call refuses it. Registering again
  // is the whole migration: idempotent on the label, so it comes back as the
  // same device -- same watches, same command channel, same row in the device
  // list -- now holding a secret. The operator sees a minute of "still here"
  // and nothing else.
  if (!(await state.deviceSecret())) {
    try {
      await register();
    } catch (error) {
      await state.setLastError(
        error instanceof ApiError ? error.message : String(error),
      );
      return;
    }
  }

  try {
    const policy = await state.policy();
    // The budget is checked here because this tick already pays for a full
    // scan of the store. Enforcing it per event would mean that scan on every
    // click. The backend does not check it at all -- `ingest.py` says so in as
    // many words -- so if this does not hold the line, nothing does.
    const budget = policy?.daily_budget_bytes;
    if (budget) {
      const trimmed = await queue.trim(budget);
      if (
        trimmed.droppedShots ||
        trimmed.strippedShots ||
        trimmed.strippedBodies ||
        trimmed.droppedEvents
      ) {
        await state.setLastError(
          `over the device's byte budget: dropped ${trimmed.droppedEvents} events, ` +
            `${trimmed.strippedBodies} response bodies and ` +
            `${trimmed.droppedShots + trimmed.strippedShots} screenshots`,
        );
      }
    }
    const [queuedEvents, queuedBytes] = await Promise.all([
      queue.count(),
      queue.totalBytes(),
    ]);
    // Taken before the call and put back if it fails, so a beat that does not
    // land does not eat the lines it was carrying.
    const said = await serially(async () => {
      const held = await state.said();
      if (held.length) await state.setSaid([]);
      return held;
    });
    let answer;
    try {
      answer = await api.heartbeat(deviceId, {
        queued_events: queuedEvents,
        queued_bytes: queuedBytes,
        policy_version: policy?.version ?? null,
        said,
      });
    } catch (error) {
      if (said.length) {
        await serially(async () => {
          const held = await state.said();
          await state.setSaid([...said, ...held].slice(-MAX_SAID));
        });
      }
      throw error;
    }
    if (answer.policy) await state.setPolicy(answer.policy);
    await state.setServerPaused(Boolean(answer.pause));
    await state.setLastBeat(new Date().toISOString());
    await state.setLastError("");
  } catch (error) {
    // A heartbeat that cannot reach the backend is not a reason to stop
    // capturing -- the queue is what capture is for. It is a reason to say so.
    await state.setLastError(
      error instanceof ApiError ? error.message : String(error),
    );
  }
  // A watch created in the console this morning reaches the browser here. The
  // heartbeat is already the tick that asks what changed, and a mail rule is
  // not urgent to the minute.
  await refreshWatches();
  // And a page rule, which needs this more than a watch does: a watch made
  // anywhere else still waits for a mail, but an arrival made in the console
  // -- or by anything other than this browser's own "Always, here" -- would
  // never reach the one process that evaluates it, and would look to its
  // operator like a rule that simply does not work.
  await refreshArrivals();
  await settle();
}

/** Make the browser match what is stored: scripts registered, badge honest,
 * and the command channel open or closed to match the credential. */
async function settle() {
  const [policy, allowed, granted] = await Promise.all([
    state.policy(),
    capturing(),
    grantedHosts(),
  ]);
  await applyPolicy(policy, { ...allowed, granted });
  // After `applyPolicy` and by its own id: the watch script must survive a
  // policy change, and `applyPolicy` withdrawing all three ids is how the
  // watching would stop the first time a heartbeat carried a new policy.
  await applyWatches(await watchHosts());
  // Every worker start, because a reload is one and there is no way to tell it
  // from an ordinary wake-up. Without this a tab open across a reload records
  // nothing while the panel goes on saying it is watched.
  await injectIntoWatched(await watchedTabs(), policy, granted);
  // A tenant that has just switched trees off gets the banner taken down now,
  // not at the next tab close. Nothing re-attaches until a gesture asks.
  if (!policy?.capture_snapshots) await releaseAll();
  await channel.settle();
  await badge();
  return status();
}

/** The icon, which has four characters to say the most important true thing.
 *
 * Two facts want it. Recording is one the operator cannot discover any other
 * way and may want to stop this second; requests waiting is one they can find
 * by opening the panel, and which loses nothing by being found a minute later.
 * So recording wins the badge, always, and a count never takes it -- a badge
 * that flipped between `REC` and `3` would be a badge that says neither
 * reliably, which is the whole reason this rule is written down rather than
 * decided twice.
 *
 * The count is never invisible, though: it goes in the title either way, which
 * is what a hover and every screen reader read off an icon.
 */
async function badge() {
  const allowed = await capturing();
  // Every request still unanswered, not only the ones that have gone quiet.
  // The icon is read by somebody who is NOT looking at the panel, so the
  // question it answers is "is there work waiting for me" -- and a mail that
  // arrived ten minutes ago is as much work as one from yesterday. Which of
  // them is today's news and which is in the banner is the panel's business,
  // not the icon's.
  const waiting = (await state.nudges()).filter(
    (nudge) => nudge.state === "open" && nudge.keeps,
  ).length;
  const counted = waiting
    ? `${waiting} request${waiting === 1 ? "" : "s"} waiting`
    : "";
  await chrome.action.setBadgeText({
    text: allowed.on ? "REC" : waiting ? String(Math.min(waiting, 99)) : "",
  });
  await chrome.action.setBadgeBackgroundColor({
    // `--warn`, the state colour the waiting banner uses, and never the accent:
    // `brand.css` says state colours are not the accent, and an icon is the
    // one place in this product where that rule is hardest to come back from.
    color: allowed.on ? "#b91c1c" : waiting ? "#b45309" : "#6b7280",
  });
  const how = allowed.on ? "observing" : `not observing (${allowed.because})`;
  await chrome.action.setTitle({
    title: `AI-SRO — ${how}${counted ? ` · ${counted}` : ""}`,
  });
}

async function status(sender = null) {
  // A content script asking (it has a tab) gets the nudges without the values
  // typed into them: those are one tab's business text and the page-side pill
  // needs only titles and states. The panel (no tab) draws the card and gets
  // them whole.
  const fromPage = Boolean(sender?.tab);
  const nudgesShown = (await state.nudges()).map((nudge) =>
    fromPage && nudge.values ? { ...nudge, values: undefined } : nudge,
  );
  const [
    allowed,
    deviceId,
    policy,
    apiUrl,
    consoleUrl,
    paused,
    serverPaused,
    lastBeat,
    lastError,
  ] = await Promise.all([
    capturing(),
    state.deviceId(),
    state.policy(),
    state.apiUrl(),
    state.consoleUrl(),
    state.paused(),
    state.serverPaused(),
    state.lastBeat(),
    state.lastError(),
  ]);
  // Not awaited: the panel polls this every two seconds and a card about a run
  // that already finished should not make every one of those polls wait on a
  // network round trip. See `checkFinishing()` -- also run off the heartbeat
  // alarm below, which is what notices a run finishing while the panel is
  // closed, and is the trigger that actually matters for most runs.
  void checkFinishing();
  const live = performing();
  // Read whether or not a command is in flight: a rig run parked on an
  // approval is one that has sent nothing for minutes, and `active` is the
  // only record that says it exists at all.
  const active = await state.activeRun();
  // The panel is open and looking. Kicking here as well as from
  // `start-rig-run` is what covers every other way a rig run becomes the
  // active one -- `commands.js` writes `source: "rig"` for every command that
  // arrives on the rig's channel, whoever started the run -- and what restarts
  // a chain whose first tick failed. Guarded against piling up by
  // `pollingRig`; not awaited, for the same reason `checkFinishing` is not.
  // Whatever it says it came from: `pollRigRun` is what finds out, and a run
  // this browser is driving with no picture beside it is a card with no steps
  // and no Approve.
  if (active) void pollRigRun();
  const shown = live || parkedRigRun(active);
  return {
    capturing: allowed.on,
    because: allowed.because,
    channel: channel.status(),
    // Why it is not dialling, when it is not. See `channel.why`.
    channelWhy: channel.why(),
    // A question this operator has not answered, off their own conversation.
    // Drawn in the column that cannot be swept, because that is the whole
    // point: the run that asked it is long gone and the question is not.
    question: await state.question(),
    // Which process is driving it, put beside what `commands.js` reports.
    // `latest` there holds the source but `performing()` does not carry it,
    // and this is the same mirrored record the `abort-run` case and
    // `finishing.js` read -- so the panel's "details" link and its Stop agree
    // on who is driving without a second answer to the question. Missing means
    // backend, as everywhere else.
    performing: shown && {
      ...shown,
      source: (active?.runId === shown.runId && active.source) || "backend",
      // The rig's own record of it, for the card that draws a row per step.
      // Only for a rig run, and only the run being drawn: a backend run's
      // steps come from its skill, and a picture left over from the previous
      // rig run would draw somebody else's writes under this one's title.
      run: rigRunShown?.id === shown.runId ? rigRunShown : undefined,
      // What the run says it is doing when it has no step to show for it --
      // reading the mailbox for the values nobody typed. Off the row rather
      // than mirrored here: the browser cannot know it, and "Step 0" is what
      // the card said instead for three and a half minutes.
      doing: rigRunShown?.id === shown.runId ? rigRunShown?.doing || "" : "",
    },
    // What the last run this browser finished made, and how to take it back --
    // held long past this run itself, unlike `performing` above, because an
    // operator coming back to look is what this is measured against rather
    // than the run going quiet. See `state.js`'s `finishedRun` for why an hour.
    finished: await freshlyFinished(),
    deviceId,
    policy,
    apiUrl,
    consoleUrl,
    paused,
    serverPaused,
    lastBeat,
    lastError,
    watched: await watchedTabs(),
    // Tabs whose page-realm patch outlived the extension that installed it.
    //
    // They record gestures and no calls. Said out loud because it is otherwise
    // invisible on both sides -- the panel says watching, the console shows
    // uploads arriving, and only the shape of the evidence gives it away, days
    // later, as a skill that checks nothing. An operator lost two
    // demonstrations to exactly that.
    deaf: [...halfDeaf],
    // The mails this browser recognised and nobody has answered yet. Held
    // here and nowhere else -- the panel is the same browser that read them.
    offers: await state.offers(),
    // What this browser is waiting on from a mailbox, and whether it is
    // reading one at this instant.
    //
    // A mail went out over the operator's name and the answer arrives by a
    // background poll they cannot see. What that looked like was a sentence --
    // "I will carry on when they reply" -- and then, for as long as it took,
    // a panel doing nothing. This is the same fact said continuously: who is
    // being waited on, when the mailbox was last read, and whether it is
    // being read now.
    mail: fromPage
      ? undefined
      : {
          awaiting: await state.awaitingMail(),
          looking: readingTheMail !== null,
          lookedAt: (await state.mailLooked())?.at || 0,
        },
    // And the rules that almost fired. Only for the panel, like the answer
    // below: the page-side pill has no room for it, and a rule that misses in
    // silence is the failure an operator cannot see.
    nearMisses: fromPage ? undefined : await state.nearMisses(),
    // Fires waiting on a person. Asked for here rather than held, because
    // unlike a nudge this is the backend's record and any browser or console
    // may answer it -- a stale copy would draw a card somebody already said
    // yes to in the other window.
    waiting: fromPage ? undefined : await waitingOnSomebody(),
    // What was offered on the page in front of them, and what came of it. Held
    // here for the same reason the offers are: this is the browser it happened
    // in, and none of it is worth writing down.
    nudges: nudgesShown,
    // The last question this browser asked of the systems and what came back.
    // Only for the panel: the page-side pill has no room for an answer, and
    // what came back is one tab's business text -- the same rule the nudge
    // values above are held under.
    answer: fromPage ? undefined : await state.answer(),
    version: VERSION,
  };
}

/** What is waiting on a person right now, or nothing.
 *
 * Never throws: the panel polls this every two seconds, and a backend that is
 * briefly unreachable is not a reason for the whole status to fail -- the
 * panel would go blank over a card that may not even exist.
 */
async function waitingOnSomebody() {
  if (!(await state.token())) return [];
  let cards;
  try {
    cards = await api.waiting();
  } catch {
    return [];
  }
  // Whether the page each card is about is still open somewhere in this
  // browser.
  //
  // An operator signed in, the job's own run took the tab off the login page,
  // and the card that fired on arriving there was still sitting in the panel.
  // Pressing it started a run that had nowhere to go: "no tab is open on
  // keycloak-...", a red cross, and eighteen seconds of a model working it
  // out. The card was asking about a page nobody is on any more.
  //
  // Matched by the rule that made it -- the card carries `trigger_id` and this
  // browser already holds every arrival rule and the page it watches -- so no
  // card grows a field the backend has to learn to send.
  const rules = await state.arrivals();
  const open = new Set(
    (await chrome.tabs.query({}))
      .map((tab) => rulePage(tab.url || ""))
      .filter(Boolean),
  );
  return (cards || []).map((card) => {
    const page = rules.find((rule) => rule.id === card.trigger_id)?.page || "";
    // A card from anything but an arrival rule has no page to be away from,
    // and is answerable wherever its operator happens to be.
    return { ...card, page, still_there: !page || open.has(page) };
  });
}

/** Guards `checkFinishing()` against running twice at once within this
 * worker's own lifetime -- not storage-backed, and does not need to be: a
 * fresh worker starts with this false, which is exactly correct, since
 * nothing it would be guarding against is in flight yet either. Without it,
 * two status polls landing within the same couple of seconds -- the panel's
 * own two-second cadence makes this ordinary, not rare -- would both see the
 * same quiet run in `state.activeRun()` and both fire `GET /v1/runs/{id}`:
 * harmless against a healthy backend, unbounded against a slow or
 * unreachable one. */
let checkingFinish = false;

/** How often the panel's picture of a live rig run is refreshed.
 *
 * A second, because the rig steps in about that and a row that appears four
 * seconds after the click reads as a panel that has stopped working. Only
 * while a run is actually running -- see `pollRigRun`, which stops rather than
 * ticking against a rig nobody is using.
 *
 * ponytail: the panel re-reads `status()` every two seconds, so a picture
 * refreshed faster than that is never seen any sooner. Kept at a second
 * anyway, because the two cadences are unsynchronised -- a step landing just
 * after a poll is on screen within one panel read either way -- and worth
 * revisiting only if the rig's `/v1/runs/{id}` ever gets expensive.
 */
const K_RUN_POLL_MS = 1000;

/** When `rigRunShown` was last read from the backend. What tells a kick from
 * a poll: everything that wants the picture gets the one already held if it
 * is younger than the cadence above. */
let rigShownAt = 0;

/** The rig's own record of the run happening now, as the panel's card wants
 * it. Module scope, so it dies with the worker -- which is correct: a fresh
 * worker has no picture yet and asks for one. */
let rigRunShown = null;
let rigPoll = null;
/** One ask at a time. `status()` and the heartbeat both kick this, and the
 * panel polls status every two seconds -- without this, a slow or unreachable
 * rig would collect one in-flight request per poll on top of the timer's own.
 * The same guard, for the same reason, as `checkingFinish` above. */
let pollingRig = false;

/** Run ids that came back 404 from the workflow-run door.
 *
 * A skill run's id is not a workflow run's, and asking after one every two
 * seconds for the length of the run is a request per tick that can only ever
 * 404. Module-scope and unbounded is fine: it holds at most the ids this
 * worker has seen since it started, and the worker is evicted between runs. */
const notWorkflowRuns = new Set();

/**
 * Keep asking the rig what the run it is driving is doing.
 *
 * Nothing pushes. The rig performs a step, waits on this browser to carry it
 * out, judges the reading and moves on -- and none of that reaches the panel
 * unless something here asks. So the panel showed "A run is performing here"
 * and nothing else until the run ended, which is the whole of what somebody
 * watching a live warehouse wants to see.
 *
 * A failed ask keeps the last picture rather than blanking the card: the rig
 * being briefly unreachable is not the run having no steps, and drawing it as
 * one would be worse than a picture that is a second old.
 */
async function pollRigRun() {
  if (pollingRig) return;
  pollingRig = true;
  try {
    const active = await state.activeRun();
    if (!active) {
      rigRunShown = null;
      return;
    }
    // `source !== "rig"` used to return here, and that gate cost an operator a
    // live run: the panel drew "a run is performing here" with no steps and no
    // Approve, while the console showed the same run parked on a person. Every
    // command the backend sends carries `source`, but an extension build older
    // than that field falls back to this channel's own name -- and the panel
    // is then structurally unable to draw the one control the run is waiting
    // on. Asking anyway costs one 404 for a run that is not a workflow run,
    // which the catch below already handles.
    if (
      active.source &&
      active.source !== "rig" &&
      rigRunShown?.id !== active.runId
    ) {
      // Still worth asking once. What is not worth doing is asking every two
      // seconds forever about an id that is not a workflow run at all, so a
      // miss is remembered.
      if (notWorkflowRuns.has(active.runId)) {
        rigRunShown = null;
        return;
      }
    }
    // A picture of some other run is worse than none: it would draw one run's
    // writes under another's title, and `status()` would hand the panel a card
    // for a run that is not the one happening.
    if (rigRunShown && rigRunShown.id !== active.runId) rigRunShown = null;
    // Not oftener than the poll's own cadence, however many things kick it.
    // `status()` kicks on every panel read and `commands.js` on every step,
    // and each of those was a fetch of its own on top of the timer below.
    if (rigRunShown?.id === active.runId && Date.now() - rigShownAt < K_RUN_POLL_MS) {
      clearTimeout(rigPoll);
      rigPoll = setTimeout(() => void pollRigRun(), K_RUN_POLL_MS);
      rigPoll?.unref?.();
      return;
    }
    try {
      rigRunShown = await api.rigRun(active.runId);
      rigShownAt = Date.now();
      notWorkflowRuns.delete(active.runId);
    } catch (error) {
      // Keep the last picture; the next tick asks again. A 404 is different in
      // kind from a network blip: this id is not a workflow run, and asking
      // again every two seconds answers nothing.
      if (error?.status === 404) notWorkflowRuns.add(active.runId);
      // Said out loud, where this used to swallow everything. A panel drawing
      // a run with no steps because the ask failed looks exactly like a run
      // that has no steps, and the operator has nothing to go on.
      else
        await state.setLastError(
          `the run this browser is driving could not be read: ${error}`,
        );
    }
    // Only a successful answer saying the run has ended stops the timer. A
    // failed ask does not: a rig that is briefly unreachable while a run is
    // parked on an approval would otherwise leave the panel with a card that
    // never updates again and an Approve nothing is behind.
    if (!rigRunShown || rigRunShown.status === "running") {
      clearTimeout(rigPoll);
      rigPoll = setTimeout(() => void pollRigRun(), K_RUN_POLL_MS);
      // Nothing in Chrome: `setTimeout` there returns a number and this is a
      // no-op. In node -- which is where this file's own tests run it -- a
      // pending timer holds the process open, and this one reschedules itself
      // for as long as a run is going, so `node --test` sat on the suite for
      // 404 seconds waiting for an event loop that would never drain. A timer
      // that keeps a poll going is not a reason to keep a process alive.
      rigPoll?.unref?.();
    }
  } finally {
    pollingRig = false;
  }
}

/** A rig run that is happening but has sent this browser nothing lately.
 *
 * `commands.js`'s `performing()` expires thirty seconds after the last command,
 * which is right for a run being stepped and wrong for one parked on an
 * approval: a write can wait five minutes for a person, and for four and a half
 * of them the panel would have shown no run, no steps and no Approve -- the
 * control the run is actually waiting on. Read off the poll's own picture, so
 * it is the rig saying the run is still running rather than this browser
 * assuming it.
 */
function parkedRigRun(active) {
  // Read off the poll's own picture and not off `source`. The word travels on
  // the command envelope, so a browser that has not been reloaded since the
  // backend started sending it never sees one -- and this is the function that
  // keeps the card, and its Approve, on screen for the whole five minutes a
  // write can wait on a person. `rigRunShown` having this run's id at all is
  // already proof the workflow-run door answered about it.
  // Both halves named, because `undefined === undefined` is true: with no run
  // active and no picture held, the loose comparison passed and the next line
  // read `.status` off null. Every offer this browser would have made died in
  // the caller's catch, silently, for as long as that shape stood.
  if (!active?.runId || !rigRunShown) return null;
  return rigRunShown.id === active.runId && rigRunShown.status === "running"
    ? { runId: active.runId, kind: "rig", since: active.at }
    : null;
}

// On worker start, because Chrome evicts this worker between events and a run
// started before that eviction is still running in the warehouse. Costs
// nothing where there is no rig run: the first line reads one key and returns.
void pollRigRun();

/**
 * Ask the backend whether the run this browser was last asked to do
 * something for has gone quiet long enough, and actually finished, to be
 * worth noting.
 *
 * Run off two triggers, deliberately: the panel's own status poll, for an
 * operator watching right now, and the `sro-heartbeat` alarm, which fires on
 * its own schedule whether the panel is open or not. Both read
 * `state.activeRun()` rather than `commands.js`'s own `latest` -- that module
 * variable dies with this worker the moment it idles out, which is the
 * *ordinary* case for a run performed with the panel closed: an operator ran
 * a task and moved on. A check that only ever worked off `latest` would only
 * ever fire for the one person who least needs to be told, because they are
 * already staring at the screen.
 *
 * Never decided locally past the timing itself. `RunModel.derived` is what
 * the run read back and `RunModel.reversal` is computed against the tenant's
 * whole skill library -- neither is something this browser has the material
 * to produce, so both are only ever copied from what `GET /v1/runs/{run_id}`
 * answers (`api.run`, already used elsewhere in this file for the same run's
 * own record).
 *
 * `run.status === "running"` means the quiet window landed between two of the
 * run's own steps, not after its last one -- nothing is stored, and
 * `state.activeRun()` is left as it was so the next trigger asks again. Any
 * other status -- succeeded or failed, the only two terminal ones this domain
 * has -- is confirmed either way: `derived` may be empty and `reversal` may
 * be null or, for a run that did not succeed, is always null (the backend
 * never computes an undo for one), and the card says so itself rather than
 * this deciding not to show one at all (see `panel.js`'s `finished()`).
 *
 * *Which* process is asked is `noteFinished`'s in `finishing.js` -- a run the
 * rig drove is a run the backend has never heard of -- and the whole record is
 * handed over rather than its id, because the `source` that decides is on it.
 *
 * ponytail: a second run starting in this browser before this one is
 * confirmed overwrites `state.activeRun()`'s single slot and the first run's
 * confirmation is lost -- it simply never gets checked. `latest` in
 * `commands.js` already only tracks one run at a time, so this is the same
 * ceiling, not a new one; widen both together to a small history if
 * back-to-back runs from one browser turns out to be ordinary rather than
 * rare.
 */
async function checkFinishing() {
  if (checkingFinish) return;
  const active = await state.activeRun();
  const decision = activeRunAge(active, Date.now(), RUN_QUIET_MS);
  if (decision === "wait") return;
  if (decision === "stale") {
    // Round 1 review missed this: `state.activeRun()` now survives a worker
    // eviction, which is the whole point, but nothing bounded how *old* the
    // survivor could be. Close the laptop before this check lands and reopen
    // it a day later, and the first heartbeat after `onStartup` would confirm
    // a run that went quiet yesterday and write a brand-new hour of "Undo
    // that" for it -- exactly the staleness `FINISHED_RUN_MS` exists to keep
    // a *stored* `finishedRun` from having. Dropped here, unconfirmed, rather
    // than asked about and written anyway. See `activeRunAge` in `state.js`.
    await state.setActiveRun(null);
    return;
  }
  checkingFinish = true;
  try {
    await noteFinished(active);
  } finally {
    checkingFinish = false;
  }
}

function defaultLabel() {
  // Enough to tell one browser from another in the device list, and nothing
  // about the person: the credential already says who they are.
  const platform = navigator.userAgent.match(/\((.*?)[;)]/)?.[1] || "browser";
  return `${platform} · Chrome`;
}
