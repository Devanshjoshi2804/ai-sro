// Registration, heartbeat, and the truthful badge.
//
// Nothing here holds state in a module variable: MV3 evicts this worker while
// it is idle and every wake-up starts from storage.

import { api, ApiError } from "./api.js";
import * as channel from "./channel.js";
import { abort, isDriving, performing } from "./commands.js";
import * as queue from "./queue.js";
import { redactUrl } from "../content/sensitivity.module.js";
import { allowsHost, applyPolicy, applyWatches, hostMatches, injectInto, unregister } from "./scripts.js";
import { capture } from "./shots.js";
import { capturing, state } from "./state.js";
import * as teaching from "./teaching.js";
import { flush } from "./upload.js";

const BEAT = "sro-heartbeat";
const FLUSH = "sro-flush";
const EVERY_MINUTES = 1;

const VERSION = chrome.runtime.getManifest().version;

// The toolbar button opens the panel rather than a popup: everything this
// extension has to say is about the tab you are looking at, and a popup closes
// the moment you look at it.
void chrome.sidePanel?.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create(BEAT, { periodInMinutes: EVERY_MINUTES });
  chrome.alarms.create(FLUSH, { periodInMinutes: EVERY_MINUTES });
  void settle();
});

chrome.runtime.onStartup.addListener(() => {
  chrome.alarms.create(BEAT, { periodInMinutes: EVERY_MINUTES });
  chrome.alarms.create(FLUSH, { periodInMinutes: EVERY_MINUTES });
  void settle();
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === BEAT) void beat();
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
  if (d.frameId === 0) void pageEvent("navigated", d.tabId, d.url, d.timeStamp);
});
chrome.webNavigation.onCompleted.addListener((d) => {
  if (d.frameId === 0) void pageEvent("loaded", d.tabId, d.url, d.timeStamp);
});
chrome.webNavigation.onCreatedNavigationTarget.addListener((d) => {
  void popupEvent(d);
});


// -- which tabs are being watched --------------------------------------------
//
// The operator points at a tab and says "the work is in here". Nothing else
// decides it: not the tenant's host list (which cannot tell a warehouse tab
// from a console tab on the same host), and not any rule this file could
// invent about which origins are "ours". A watched tab is watched entirely --
// every frame, every call it makes, wherever it navigates.

/** Every change to the watched list, one at a time.
 *
 * Read-modify-write over `chrome.storage` has no transaction: a tab closing
 * while another is being watched read the old list and wrote it back, and the
 * new watch vanished. That failure is invisible -- capture simply produces
 * nothing -- so it is worth the four lines.
 */
let changes = Promise.resolve();

function serially(job) {
  const next = changes.then(job, job);
  changes = next.then(
    () => {},
    () => {},
  );
  return next;
}

async function watchedTabs() {
  const watched = await state.watched();
  // A tab id is only meaningful while the tab exists. Chrome hands the same
  // ids out again after a restart, so a stale entry is not merely useless --
  // it is a watch on whatever tab inherits the number.
  const alive = await Promise.all(
    watched.map(async (entry) => {
      try {
        await chrome.tabs.get(entry.tabId);
        return entry;
      } catch {
        return null;
      }
    }),
  );
  const kept = alive.filter(Boolean);
  // Tidying is never allowed to fail a capture. Storage can reject -- a full
  // disk, a quota -- and a gesture lost because the housekeeping beside it
  // threw is the same bug as a gesture lost to a failed screenshot.
  if (kept.length !== watched.length) await state.setWatched(kept).catch(() => {});
  return kept;
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
    const next = [{ tabId, host, since: Date.now() }, ...watched];
    await state.setWatched(next);
    return next;
  });
}

function unwatch(tabId) {
  return serially(async () => {
    const watched = await watchedTabs();
    const next = watched.filter((entry) => entry.tabId !== tabId);
    // A tab nobody was watching closes all day long. Writing the same list
    // back for each one is how a watch set meanwhile gets overwritten.
    if (next.length !== watched.length) await state.setWatched(next);
    return next;
  });
}

chrome.tabs.onRemoved.addListener((tabId) => {
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
  if (!allowsHost(opener.url, policy)) return;
  // A window the watched application opened is part of the same piece of work
  // -- a picker, an SSO round trip, a print preview. The operator pointed at
  // the task, not at a tab id, so the watch follows it.
  if (await isWatched(d.sourceTabId)) await watch(d.tabId, d.url);
  // The new tab's id, not the opener's: `url` is the new tab's, and the two
  // together used to name one tab while describing another's page.
  await pageEvent("popup_opened", d.tabId, d.url, d.timeStamp);
}

async function pageEvent(page_kind, tab_id, url, timeStamp) {
  try {
    const [policy, allowed, watching] = await Promise.all([
      state.policy(),
      capturing(),
      isWatched(tab_id),
    ]);
    if (!allowed.on || !watching || !allowsHost(url, policy)) return;
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
    if (!keep) return { ...body, text: null, size_bytes: 0, redacted_fields: ["«not captured»"] };
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
    response_body: allowed(request.response_body, policy?.capture_response_bodies !== false),
  };
}

chrome.runtime.onMessage.addListener((message, sender, respond) => {
  // Returning true keeps the channel open for the async answer.
  handle(message, sender).then(respond, (error) => respond({ error: String(error) }));
  return true;
});

async function handle(message, sender) {
  switch (message?.kind) {
    case "content-ready":
      return { ok: true };
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
      if (!watching) return { ok: false, dropped: "this tab is not being watched" };
      if (!allowsHost(frameUrl, policy)) {
        return { ok: false, dropped: "excluded host" };
      }
      // A tab this extension is driving for a run is not an operator working.
      // Kept out of the evidence plane entirely: a replay's clicks and the
      // calls they set off, mined as though somebody had done them, is the
      // system learning a task from a robot imitating a person -- and then
      // offering it back as something worth automating.
      if (isDriving(sender?.tab?.id ?? null)) {
        return { ok: false, dropped: "this browser is performing a run" };
      }
      // Somebody is working in here. Said out loud on the channel so a command
      // queues instead of landing mid-keystroke -- only for gestures, because
      // a page's background traffic is not a person at a keyboard.
      if (message.kind === "gesture") channel.operatorIsWorking();
      // tab_id comes from the sender, not the content script -- a frame has
      // no chrome.tabs access of its own to ask for it.
      const tab_id = sender?.tab?.id ?? null;
      // Same rule as page events, at the same one point: a gesture carries the
      // page's own `location.href` and every event carries the frame it
      // happened in, and either can be the callback URL with the token in it.
      const demonstrating = await teaching.current();
      const recordingId =
        demonstrating && demonstrating.tabId === tab_id ? demonstrating.recordingId : null;

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
            gesture: { ...message.gesture, url: redactUrl(message.gesture?.url) },
            tab_id,
            frame_url: redactUrl(frameUrl),
          },
          shot,
          recordingId,
        );

        if (recordingId) {
          // The tree taken *before* this gesture, enqueued after it: the
          // assembler attaches a snapshot to the frame of the gesture before
          // it, and that frame's locator is built from the tree. A tree taken
          // after the click describes the page the click produced -- for a
          // step that navigates, a page where the control it clicked does not
          // exist at all.
          const before = teaching.takeSnapshot();
          if (before) await queue.enqueue(before, null, recordingId);
          // And one for whatever they do next.
          void teaching.snapshot(tab_id, redactUrl(frameUrl)).catch(() => null);
        }
        return { ok: true, screenshot: Boolean(shot) };
      }
      await queue.enqueue(
        {
          kind: "request",
          request: {
            ...underPolicy(message.request, policy),
            url: redactUrl(message.request?.url),
          },
          tab_id,
          frame_url: redactUrl(frameUrl),
        },
        null,
        recordingId,
      );
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
      await state.setDeviceId("");
      await state.setPolicy(null);
      await state.setApiUrl(message.apiUrl);
      await state.setConsoleUrl(message.consoleUrl || "");
      await state.setToken(message.token);
      // Capture is off until the registration lands, and the badge says so.
      await badge();
      return register(message.label);
    case "sign-out":
      await teaching.stop();
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
    case "flush":
      // Upload now rather than on the next tick, and all of it: the options
      // page offers this so an operator about to close the laptop can watch the
      // queue go, and "it went" has to mean the queue is empty.
      return drain();
    case "teach-start": {
      // Everything captured so far goes up as ordinary work before the
      // demonstration starts, so no batch straddles the moment it began.
      await flushQueue();
      const deviceId = await state.deviceId();
      // Named by the caller where the caller knows: the side panel is docked
      // beside the tab being taught and can say which it is. Where nobody says
      // -- the options page, which cannot be the tab you mean -- fall back to
      // the last ordinary page the operator was on.
      const tab = message.tabId
        ? await chrome.tabs.get(message.tabId).catch(() => null)
        : (await chrome.tabs.query({ windowType: "normal" }))
            .filter((each) => /^https?:/.test(each.url || ""))
            .sort((a, b) => (b.lastAccessed || 0) - (a.lastAccessed || 0))[0];
      if (!tab?.id || !/^https?:/.test(tab.url || "")) {
        return { error: "open the system you want to teach in a tab first" };
      }
      // Pressing "teach" in a tab is the same sentence as "watch this tab",
      // said more strongly. An operator who demonstrates in an unwatched tab
      // and gets an empty recording learns nothing except not to trust this.
      await watch(tab.id, tab.url);
      await injectInto(tab.id, tab.url, await state.policy());
      const started = await api.startRecording(deviceId, message.label || tab.title || null);
      try {
        await teaching.start(started.recording_id, tab.id);
        // The first "before": the screen as it was when the operator pressed
        // start, which is what the first gesture will be judged against.
        await teaching.snapshot(tab.id, tab.url).catch(() => null);
      } catch (error) {
        // Chrome refuses a second debugger on a tab, so DevTools being open is
        // enough to land here. Without this the recording stays open on the
        // server with nothing on this device that could ever seal it -- an
        // empty demonstration nobody can finish or find.
        await api.finishRecording(started.recording_id).catch(() => {});
        return {
          error:
            `${error}. If DevTools is open on that tab, close it: Chrome allows ` +
            "one debugger at a time.",
        };
      }
      return { ok: true, teaching: await teaching.current() };
    }
    case "teach-stop": {
      const was = await teaching.stop();
      if (!was) return { ok: true, was: null };
      // *All* of the demonstration's evidence goes up before anything is
      // sealed. One flush is one batch -- 500 events or 2MB -- and a teaching
      // batch carries an accessibility tree per gesture, so a demonstration of
      // any length is several. Sealing after the first one left the rest in
      // the queue, and the next tick met a sealed recording: the backend
      // refuses that permanently, and a permanent refusal deletes the rows.
      // The back half of the demonstration disappeared without a word.
      if (message.discard) {
        // Nothing more is uploaded: what is queued belongs to a demonstration
        // the operator has just said they did not mean. The recording is
        // abandoned rather than deleted, because it is still evidence of what
        // happened in this browser -- it is simply never induced from.
        await queue.clear();
        await api.finishRecording(was.recordingId, "the operator discarded it");
        return { ok: true, was, summary: null, discarded: true };
      }
      const sent = await drain();
      if (sent.error) {
        return { error: `not sealed, because the last of it did not upload: ${sent.error}` };
      }
      const summary = await api.finishRecording(was.recordingId);
      return { ok: true, was, summary };
    }
    case "run":
      // The panel says what a run driving this browser is doing. The worker
      // holds the credential, so it does the asking.
      return api.run(message.runId);
    case "skill":
      return api.skill(message.skillId);
    case "candidates":
      // Read here rather than in the panel so the credential stays in the
      // worker: an extension page holding a token is one more place it can be
      // read from, and the panel has no need of it.
      return api.candidates(message.host);
    case "teach-candidate":
      return api.teachCandidate(message.id);
    case "teach-together":
      return api.teachTogether(message.id, message.otherId);
    case "answer-join":
      return api.answerJoin(message.id, message.otherId, message.joinKind, message.answer);
    case "dismiss-candidate":
      return api.dismissCandidate(message.id, message.reason);
    case "panel-console":
      // The one place the token deliberately leaves the worker: the console
      // this browser frames cannot see the credential in its own tab, because
      // Chrome partitions storage for framed contexts, so the panel has to hand
      // it across. It goes to the configured origin and nowhere else.
      return { consoleUrl: await state.consoleUrl(), token: await state.token() };
    case "abort-run":
      // Answered even when there was nothing to stop: the panel asking twice,
      // or asking about a run that has just finished, is not an error worth
      // showing anybody.
      return { ok: true, aborted: abort(message.runId) };
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
      await injectInto(tabId, url, await state.policy());
      return { watched };
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
      return { watches: host ? held.filter((watch) => hostMatches(host, watch.host)) : [] };
    }
    case "watch-matched": {
      // The one place a value read out of somebody's mail leaves this
      // machine, so the checks are here rather than only in the page: the
      // watch has to be one this browser holds, the frame has to be on that
      // watch's host, and what goes is the names the watch declared and
      // nothing else. A page that made this message up gets nowhere.
      const deviceId = await state.deviceId();
      const host = hostOf(sender?.url || "");
      const watch = (await state.watches()).find((each) => each.id === message.triggerId);
      if (!deviceId || !watch || !hostMatches(host, watch.host)) {
        return { error: "no such watch" };
      }
      const values = {};
      for (const declared of watch.values || []) {
        const given = message.values?.[declared.name];
        if (typeof given === "string" && given) values[declared.name] = given.slice(0, MAX_VALUE);
      }
      const offer = await api.watchMatched(deviceId, watch.id, values);
      await hold(watch, values, offer);
      return { ok: true, offer };
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
      const fired = await api.watchFire(deviceId, offer.triggerId, offer.read);
      // Kept when nothing started, so the card can say why. A laptop that was
      // closed is the ordinary one of these, and it is worth pressing again.
      await state.setOffers(
        fired.run_id
          ? offers.filter((each) => each.id !== offer.id)
          : offers.map((each) => (each.id === offer.id ? { ...each, skipped: fired.skipped } : each)),
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
      await state.setOffers(offers.filter((each) => each.id !== message.offerId));
      return { ok: true };
    }
    case "status":
      return status();
    default:
      return { error: `no such message: ${message?.kind}` };
  }
}

/** How many offers this browser holds: enough that the morning's mail is still
 * there after lunch, few enough that a watch somebody wrote badly cannot fill
 * the disk with what it read. */
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
async function hold(watch, read, offer) {
  const held = await state.offers();
  // The same mail seen again -- open in a second tab, or the page reloaded.
  // `watch.js` offers once per frame; this is the frame after that one.
  const same = (each) =>
    each.triggerId === watch.id && JSON.stringify(each.read) === JSON.stringify(read);
  if (held.some(same)) return;
  const skill = await api.skill(offer.skill_id).catch(() => null);
  await state.setOffers(
    [
      {
        id: crypto.randomUUID(),
        at: Date.now(),
        triggerId: watch.id,
        skillId: offer.skill_id,
        skill: skill?.name || "",
        host: watch.host,
        terms: watch.terms || [],
        // What this browser read out of the mail, and what the task would run
        // with -- the trigger's own values under the mail's. Both, because
        // which is which is what somebody deciding needs to see.
        read,
        values: offer.values || {},
        missing: offer.missing || [],
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

function hostOf(url) {
  try {
    return new URL(url).hostname;
  } catch {
    return "";
  }
}

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
        .map((trigger) => ({ id: trigger.id, ...trigger.watch })),
    );
  } catch (error) {
    await state.setLastError(error instanceof ApiError ? error.message : String(error));
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
  if (!deviceId || !allowed.on) return { uploaded: 0, because: allowed.because || "not registered" };
  try {
    const result = await flush(deviceId);
    if (result.error) await state.setLastError(result.error);
    else if (result.uploaded || result.screenshots) await state.setLastError("");
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
  await state.setPolicy(registered.policy);
  await state.setLastError("");
  // Before `settle`, which is what registers the script that evaluates them.
  await refreshWatches();
  await settle();
  return status();
}

async function beat() {
  const deviceId = await state.deviceId();
  if (!deviceId) return;

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
    const [queuedEvents, queuedBytes] = await Promise.all([queue.count(), queue.totalBytes()]);
    const answer = await api.heartbeat(deviceId, {
      queued_events: queuedEvents,
      queued_bytes: queuedBytes,
      policy_version: policy?.version ?? null,
    });
    if (answer.policy) await state.setPolicy(answer.policy);
    await state.setServerPaused(Boolean(answer.pause));
    await state.setLastBeat(new Date().toISOString());
    await state.setLastError("");
  } catch (error) {
    // A heartbeat that cannot reach the backend is not a reason to stop
    // capturing -- the queue is what capture is for. It is a reason to say so.
    await state.setLastError(error instanceof ApiError ? error.message : String(error));
  }
  // A watch created in the console this morning reaches the browser here. The
  // heartbeat is already the tick that asks what changed, and a mail rule is
  // not urgent to the minute.
  await refreshWatches();
  await settle();
}

/** Make the browser match what is stored: scripts registered, badge honest,
 * and the command channel open or closed to match the credential. */
async function settle() {
  const [policy, allowed] = await Promise.all([state.policy(), capturing()]);
  await applyPolicy(policy, allowed);
  // After `applyPolicy` and by its own id: the watch script must survive a
  // policy change, and `applyPolicy` withdrawing all three ids is how the
  // watching would stop the first time a heartbeat carried a new policy.
  await applyWatches(await watchHosts());
  await channel.settle();
  await badge();
  return status();
}

async function badge() {
  const allowed = await capturing();
  await chrome.action.setBadgeText({ text: allowed.on ? "REC" : "" });
  await chrome.action.setBadgeBackgroundColor({ color: allowed.on ? "#b91c1c" : "#6b7280" });
  await chrome.action.setTitle({
    title: allowed.on ? "AI-SRO — observing" : `AI-SRO — not observing (${allowed.because})`,
  });
}

async function status() {
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
  ] =
    await Promise.all([
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
  return {
    capturing: allowed.on,
    because: allowed.because,
    channel: channel.status(),
    // What has been seen but not yet sent. The panel shows it while teaching,
    // because a demonstration that is recording nothing looks exactly like one
    // that is recording everything, and the operator finds out at the end.
    queued: await queue.count(),
    teaching: await state.teaching(),
    performing: performing(),
    deviceId,
    policy,
    apiUrl,
    consoleUrl,
    paused,
    serverPaused,
    lastBeat,
    lastError,
    watched: await watchedTabs(),
    // The mails this browser recognised and nobody has answered yet. Held
    // here and nowhere else -- the panel is the same browser that read them.
    offers: await state.offers(),
    version: VERSION,
  };
}

function defaultLabel() {
  // Enough to tell one browser from another in the device list, and nothing
  // about the person: the credential already says who they are.
  const platform = navigator.userAgent.match(/\((.*?)[;)]/)?.[1] || "browser";
  return `${platform} · Chrome`;
}
