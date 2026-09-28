// Registration, heartbeat, and the truthful badge.
//
// Nothing here holds state in a module variable: MV3 evicts this worker while
// it is idle and every wake-up starts from storage.

import { api, ApiError } from "./api.js";
import { alsoWatch, alwaysWatched, hostOf } from "./always.js";
import { questionIn } from "./asking.js";
import { waitBeforeLooking } from "./looking.js";
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
import { capture } from "./shots.js";
import { noteFinished } from "./finishing.js";
import {
  activeRunAge,
  capturing,
  finishedRun,
  RETIRED_KEYS,
  state,
} from "./state.js";
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

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === BEAT) {
    void beat();
    // The one trigger that does not need the panel open. A run watched and
    // then left alone -- the ordinary case, not the exception -- ends while
    // this worker is idled out, and this alarm fires on its own schedule
    // regardless, off the storage-backed record of the run being watched.
    void checkFinishing();
    // And the picture of that run: the timer chain dies with the worker, so
    // without this a run parked on an approval across an eviction would never
    // be asked about again. Self-guarding -- it returns at once when no run
    // is being watched.
    void pollRigRun();
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
  // opened this tab -- them or a link.
  //
  // And nothing else happens on arriving. This browser records; it never
  // starts a run because of where its operator is. A page rule that did was
  // how a job ran because somebody opened their mail (QA, 2026-09-28).
  void watchIfAlways(d.tabId, d.url);
  void pageEvent("navigated", d.tabId, d.url, d.timeStamp);
});
chrome.webNavigation.onCompleted.addListener((d) => {
  if (d.frameId === 0) void pageEvent("loaded", d.tabId, d.url, d.timeStamp);
});
chrome.webNavigation.onCreatedNavigationTarget.addListener((d) => {
  void popupEvent(d);
});

// -- what the conversation said, as this browser watches it ------------------
//
// This browser starts nothing. The backend starts every run -- a yes in the
// conversation, the last answer to a question, a mail it acts on -- and Steel
// runs it. What is left here is watching: the run a reply names, the question
// a thread is still holding open, and what a mail look came back with.

/** The job the thread's own reply placed this sentence as, if it placed one.
 *
 * The last thing the assistant said, and only the last: a thread is a
 * conversation, and the reply on screen is about the sentence just typed.
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
 * same words a second time as a question for the systems is a reading of a
 * sentence that was never about one.
 *
 * Measured on the deployment 2026-09-19, thread thr_163bf91b: the operator was
 * asked "Create a Client. Address takes 40 characters. What should it be?",
 * typed `testing for new purpose`, and got back both halves at once.
 */
function stillAsking(thread) {
  for (const message of [...(thread?.messages || [])].reverse()) {
    if (message.speaker !== "assistant") continue;
    const decision = message.decision || {};
    return decision.kind === "needs_values" && Boolean(decision.workflow_id);
  }
  return false;
}

/** What a mail look found for one request, said and nothing more.
 *
 * The backend acts on a mail itself: it starts the run, or asks in the
 * conversation, and says which. A card here with its own Yes was a second
 * engine behind a first one -- so this browser only lets go of the wait the
 * answer ended, and says what the backend did.
 */
async function heardFromMail(offer) {
  // The answer came. Nothing is waiting on a mailbox any more, and a panel
  // still saying so under the reply that answered it is a panel arguing with
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
  const named = offer.title || offer.workflow_id;
  // Every way this can end, said out loud -- including the one where the
  // backend did neither. That one is not this browser's to act on, and a
  // request nobody can see is the failure this line exists to make visible.
  await narrate(
    offer.started
      ? `${named} is running on the answer that came back`
      : offer.asked
        ? `${named} is asked in the conversation`
        : `mail offer for ${named} was neither started nor asked by the backend`,
  );
}

/** A sentence the conversation placed as no job, looked up as a question.
 *
 * A read writes nothing, and waiting for a press before answering a question
 * is the shortcut this was built to avoid -- so what is left is to put the
 * answer where the panel draws it. An instruction is not read here at all:
 * the conversation already decided about it, and starting anything is the
 * backend's.
 */
async function lookUp(text, tabId) {
  if (!text || tabId === null) return;
  try {
    const said = await api.ask(text);
    if (said?.kind !== "lookup") return;
    await state.setAnswer({
      said: text,
      tabId,
      askedAt: Date.now(),
      ...said.lookup,
    });
  } catch (error) {
    // Said out loud, not swallowed.
    //
    // A sentence about nothing is the ordinary case and says nothing back --
    // the thread already has what they said. A door that REFUSED is a
    // different thing, and this catch once hid one for a whole evening: every
    // sentence an operator typed got a 404 from `/v1/ask`, and there was no
    // way from the panel to tell "I did not understand you" from "I could not
    // ask". `lastError` is what the strip already draws.
    if (error instanceof ApiError) {
      await state.setLastError(
        `the panel could not ask about that: ${error.message}`,
      );
    }
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
    if (leaving?.host && (await isExcluded(leaving.host)))
      await ungrant(leaving.host);
    return next;
  });
}

chrome.tabs.onRemoved.addListener((tabId) => {
  halfDeaf.delete(tabId);
  void forgetRepaired(tabId);
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
      const deafTab = sender?.tab?.id ?? -1;
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
      await queue.clear();
      await state.newQueueEpoch();
      // A batch minted for the last operator names their epoch and their
      // rows; left standing, the first flush under the new credential would
      // retry it as itself and send the new operator's queue under the old
      // operator's batch id.
      await state.setPendingBatch(null);
      // A shared warehouse machine is the ordinary case, not the exception:
      // the last operator's run card stays for an hour (`state.js`'s
      // `finishedRun`), so without this the next operator to sign in within
      // that hour would see somebody else's run.
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
    case "flush":
      // Upload now rather than on the next tick, and all of it: "it went" has
      // to mean the queue is empty. No screen sends this any more; the
      // real-Chrome suite and `make fixtures` drain through it.
      return drain();
    case "run":
      // The panel says what the run it is watching is doing. The worker
      // holds the credential, so it does the asking.
      //
      // Two doors, because there are two kinds of run and their ids live in
      // different tables: a skill run at `/v1/runs`, a mined job's run at
      // `/v1/workflow-runs`. The panel asked the first about both, so every
      // rig run 404'd -- 308 of those in one evening across eleven run ids --
      // and the card an operator watches never learned the job's name or how
      // far through it was. The panel says which kind it is asking about; it
      // is the only thing that knows, because it is what the worker told it.
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
          // So the panel draws the run the backend just started.
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
    // `candidates`, `teach-candidate`, `teach-together`, `answer-join`,
    // `dismiss-candidate` and `resolve-intent` were here, and are not any
    // more: every one of them served the mining pipeline's offer -- a card
    // that proposed teaching a skill from recordings, and a box that resolved
    // a sentence against the skills it had taught. This deployment runs the
    // rig, whose jobs come with their steps already. `nudge-answer`,
    // `never-watch-site`, `revise-run`, `say-to-run`, `look-in-the-mail` and
    // `panel-open` went the same way: nothing sent them.
    //
    // And every message that started or drove a run from this browser --
    // `start-rig-run`, `retry-rig-run`, `undo-rig-run`, `run-workflow`,
    // `run-skill`, `ask-about-offer`, `do-this-here`, the offer drops, and
    // `reconnect` for the command channel. One engine: the backend starts
    // every run and Steel runs it. A press that should start one is a yes in
    // the conversation, and this browser only carries the sentence.
    case "thread": {
      const thread = await api.currentThread();
      void watchTheRunIn(thread);
      return thread;
    }
    case "new-thread":
      // A conversation somebody deliberately started. `current` answers with
      // the newest, so nothing else has to be told which one to draw.
      return api.newThread();
    case "learned-jobs":
      // The jobs mined for this tenant, for the card that says what was
      // learned on the page beside the panel. The panel filters by host.
      return { jobs: await api.workflows(await state.deviceId()) };
    case "recent-runs": {
      // The rows, with each job's own title put back on them. The backend
      // answers `workflow_id`, and the jobs it has learned carry the titles --
      // a list reading "wfl_3f2a — done" tells nobody what was done.
      const [runs, jobs] = await Promise.all([
        api.rigRuns(message.limit || 12),
        api.workflows(await state.deviceId()),
      ]);
      const titles = new Map(jobs.map((job) => [job.id, job.title]));
      return runs.map((run) => ({
        ...run,
        title: titles.get(run.workflow_id) || run.workflow_id,
      }));
    }
    case "thread-say": {
      const said = await api.say(
        message.threadId,
        message.text,
        message.answering,
      );
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
      // The reply already read the sentence against this tenant's jobs.
      const placed = jobInTheReply(said);
      // A yes, or the last answer to a question, and the backend has already
      // started the run -- from every door, the console and a mail as well as
      // this panel -- and named it here. This browser watches it. A job placed
      // and not started is the conversation's to ask about, in the thread;
      // nothing here offers or starts it.
      if (placed?.run_id) {
        await state.setActiveRun({
          runId: placed.run_id,
          at: Date.now(),
          source: "rig",
        });
        void pollRigRun();
      }
      // And a sentence the thread is still holding a question open for is not
      // an unread sentence. `lookUp` is for the case where the door read it
      // and placed no job at all.
      else if (!placed && !stillAsking(said))
        void lookUp(message.text, message.tabId ?? null);
      // A yes that lost the race to another panel is told only that the
      // question closed; the run it lost to is further up the same thread.
      void watchTheRunIn(said);
      return said;
    }
    case "panel-console":
      // Where the console is, and nothing else. The token used to go with it,
      // for a console framed inside the panel; that frame is gone, and the
      // token no longer leaves this worker for the panel at all.
      return { consoleUrl: await state.consoleUrl() };
    case "approve-rig-run": {
      // The press on the awaiting row. It comes here rather than going to the
      // backend from the panel because the bearer lives in this worker and in
      // nothing a page can reach.
      //
      // And only for the run this panel is actually watching. The panel draws
      // Approve off a status read that can be a couple of seconds old, so a
      // card left standing after the run ended -- or a second window showing a
      // run that has since been superseded -- could otherwise authorise a live
      // write in somebody's warehouse against a run nobody here is watching.
      if (message.runId !== (await state.activeRun())?.runId) {
        return {
          ok: false,
          error: "that run is not the one this panel is watching",
        };
      }
      try {
        return await api.rigApprove(message.runId, await state.deviceId());
      } catch (error) {
        return { ok: false, error: error.problem?.detail || error.message };
      }
    }
    case "abort-run": {
      // The run is driven by the backend, so the backend is what is told.
      try {
        // Through the door that holds it. A workflow run's id is a 404 at
        // `POST /runs/{id}/stop` -- a Stop button that stops nothing, which is
        // the one thing a stop control must never be. Read off the same
        // mirrored `source` `noteFinished` reads; a record with no source is a
        // skill run. ponytail: `state.activeRun()` is one slot, so two runs
        // watched at once would answer for each other here.
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
        return { ok: true, error: error.message };
      }
      return { ok: true };
    }
    case "run-wrong": {
      // "It's wrong -- I'll fix it". The record is what counts against the
      // skill; from that press on the operator's own hands are the
      // correction, and the card ends.
      const result = await api.runWrong(message.runId, message.because);
      const held = await state.finishedRun();
      if (held?.id === message.runId) await state.setFinishedRun(null);
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
    // Heard one at a time, and a failure to hear one is NOT a failure to
    // reach the mailbox: a throw here caught by the handler below would mark
    // the mailbox unreachable and say nothing.
    let kept = 0;
    if (looked?.offered?.length || looked?.read)
      await narrate(
        `looked in the mail -- ${looked?.read || 0} read, ${(looked?.offered || []).length} offered`,
      );
    for (const offer of looked?.offered || []) {
      try {
        await heardFromMail(offer);
        kept += 1;
      } catch (error) {
        await narrate(`mail offer not heard: ${error}`);
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

/** The newest run the conversation names, whoever's yes started it. */
function runNamedIn(thread) {
  for (const message of [...(thread?.messages || [])].reverse()) {
    if (message.speaker !== "assistant") continue;
    if (message.decision?.run_id) return message.decision.run_id;
  }
  return null;
}

/** Runs already looked at once, so a thread whose newest run ended long ago
 * costs one read per worker, not one a minute. */
const lookedAtRuns = new Set();

/** Watch the run the backend started from a yes said anywhere -- the console,
 * another panel, a mail -- the way this panel watches its own.
 *
 * Only while nothing else is being watched, and only a run still going: a
 * finished run's card is `finishedRun`'s, and adopting it again would bring
 * back a card the operator already saw end. */
async function watchTheRunIn(thread) {
  const runId = runNamedIn(thread);
  if (!runId || lookedAtRuns.has(runId) || (await state.activeRun())) return;
  lookedAtRuns.add(runId);
  if ((await state.finishedRun())?.runId === runId) return;
  let run;
  try {
    run = await api.rigRun(runId);
  } catch {
    lookedAtRuns.delete(runId);
    return;
  }
  if (run.status !== "running" || (await state.activeRun())) return;
  await state.setActiveRun({ runId, at: Date.now(), source: "rig" });
  void pollRigRun();
}

async function lookForAQuestion() {
  try {
    const thread = await api.currentThread();
    void watchTheRunIn(thread);
    await holdTheQuestion(thread);
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
  // same device -- same watches, same row in the device list -- now holding a
  // secret. The operator sees a minute of "still here" and nothing else.
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
  await settle();
}

/** Make the browser match what is stored: scripts registered and the badge
 * honest. */
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
  await badge();
  return status();
}

/** The icon, which has four characters to say the most important true thing:
 * whether this browser is recording. The operator cannot discover it any other
 * way and may want to stop it this second. */
async function badge() {
  const allowed = await capturing();
  await chrome.action.setBadgeText({ text: allowed.on ? "REC" : "" });
  await chrome.action.setBadgeBackgroundColor({
    color: allowed.on ? "#b91c1c" : "#6b7280",
  });
  const how = allowed.on ? "observing" : `not observing (${allowed.because})`;
  await chrome.action.setTitle({ title: `AI-SRO — ${how}` });
}

async function status(sender = null) {
  // A content script asking (it has a tab) gets none of the panel's halves:
  // what came back from a question, a mailbox or a rule is one tab's business
  // text, and a page has no card to draw it on.
  const fromPage = Boolean(sender?.tab);
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
  // The run this panel is watching, the only record that says it exists.
  const active = await state.activeRun();
  // The panel is open and looking. Kicking here is what restarts a chain
  // whose first tick failed. Guarded against piling up by `pollingRig`; not
  // awaited, for the same reason `checkFinishing` is not.
  if (active) void pollRigRun();
  const shown = watchedRun(active);
  return {
    capturing: allowed.on,
    because: allowed.because,
    // A question this operator has not answered, off their own conversation.
    // Drawn in the column that cannot be swept, because that is the whole
    // point: the run that asked it is long gone and the question is not.
    question: await state.question(),
    // Which kind of run it is, off the same mirrored record the `abort-run`
    // case and `finishing.js` read -- so the panel's "details" link and its
    // Stop agree without a second answer to the question. Missing means a
    // skill run, as everywhere else.
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
    // What the last run this panel watched made -- held long past the run
    // itself, unlike `performing` above, because an operator coming back to
    // look is what this is measured against rather than the run going quiet.
    // See `state.js`'s `finishedRun` for why an hour.
    finished: await finishedRun(),
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
    // this is the backend's record and any browser or console may answer it
    // -- a stale copy would draw a card somebody already said yes to in the
    // other window.
    waiting: fromPage ? undefined : await waitingOnSomebody(),
    // The last question this browser asked of the systems and what came back.
    // Only for the panel: what came back is one tab's business text.
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
  try {
    return (await api.waiting()) || [];
  } catch {
    return [];
  }
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
 * Keep asking the backend what the run this panel is watching is doing.
 *
 * Nothing pushes. The backend performs a step, judges the reading and moves
 * on -- and none of that reaches the panel unless something here asks. So the
 * panel showed "A run is performing here" and nothing else until the run
 * ended, which is the whole of what somebody watching a live warehouse wants
 * to see.
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
    // A run recorded under another source is still asked about once: a
    // workflow run the panel cannot picture is a card with no steps and no
    // Approve. Asking costs one 404 for a run that is not a workflow run,
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
    // `status()` kicks on every panel read, and each of those was a fetch of
    // its own on top of the timer below.
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
          `the run this panel is watching could not be read: ${error}`,
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

/** The run this panel is watching, while the backend says it is running.
 *
 * Read off the poll's own picture, so it is the backend saying the run is
 * still running rather than this browser assuming it -- which is what keeps
 * the card, and its Approve, on screen for the whole five minutes a write can
 * wait on a person. `rigRunShown` having this run's id at all is already
 * proof the workflow-run door answered about it.
 */
function watchedRun(active) {
  // Both halves named, because `undefined === undefined` is true: with no run
  // active and no picture held, the loose comparison passed and the next line
  // read `.status` off null.
  if (!active?.runId || !rigRunShown) return null;
  return rigRunShown.id === active.runId && rigRunShown.status === "running"
    ? { runId: active.runId, kind: "rig", since: active.at }
    : null;
}

// On worker start, because Chrome evicts this worker between events and a run
// started before that eviction is still running in the warehouse. Costs
// nothing where there is no rig run: the first line reads one key and returns.
void pollRigRun();

/** How long after a run is first watched before anybody asks whether it
 * ended. Short enough that a finished run's card arrives while somebody is
 * still looking, long enough that a run just started is not asked about on
 * every status read. */
const RUN_QUIET_MS = 30_000;

/**
 * Ask the backend whether the run this panel is watching has finished, and
 * keep what it made for the card.
 *
 * Run off two triggers, deliberately: the panel's own status poll, for an
 * operator watching right now, and the `sro-heartbeat` alarm, which fires on
 * its own schedule whether the panel is open or not. Both read
 * `state.activeRun()`, which survives this worker being evicted -- the
 * *ordinary* case for a run left to finish with the panel closed.
 *
 * Never decided locally past the timing itself. `RunModel.derived` is what
 * the run read back -- not something this browser has the material to
 * produce, so it is only ever copied from what `GET /v1/runs/{run_id}`
 * answers.
 *
 * `run.status === "running"` means the run has not ended yet -- nothing is
 * stored, and
 * `state.activeRun()` is left as it was so the next trigger asks again. Any
 * other status is confirmed either way: `derived` may be empty, and the card
 * says so itself rather than this deciding not to show one at all (see
 * `panel.js`'s `finished()`).
 *
 * *Which* door is asked is `noteFinished`'s in `finishing.js`, and the whole
 * record is handed over rather than its id, because the `source` that decides
 * is on it.
 *
 * ponytail: a second run watched before this one is confirmed overwrites
 * `state.activeRun()`'s single slot and the first run's card is lost. Widen
 * to a small history if back-to-back runs turn out to be ordinary.
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
    // a run that went quiet yesterday and write a brand-new hour of a card
    // for it -- exactly the staleness `FINISHED_RUN_MS` exists to keep
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
