// Batching and uploading what queue.js is holding.
//
// Runs on an alarm tick rather than per event: a busy minute of clicking
// would otherwise be a busy minute of requests. Nothing leaves the queue
// until the backend has either accepted it or refused it in a way that will
// not change on the next attempt -- a transient failure is retried whole on
// the following tick, and no separate backoff timer is needed because the
// alarm already paces every attempt the same way.

import { api, ApiError } from "./api.js";
import * as queue from "./queue.js";
import { state } from "./state.js";

const MAX_EVENTS = 500;
const MAX_BYTES = 2 * 1024 * 1024;

/** How many staged screenshots go per tick. The alarm paces the rest, the same
 * way it paces batches. */
const MAX_SHOTS_PER_TICK = 10;

/** A screenshot the backend will not take after this many tries is given up.
 * Without a ceiling, one picture refused in a way that looks transient is
 * retried on every alarm for as long as the browser runs. */
const MAX_SHOT_ATTEMPTS = 3;

/** Statuses worth trying again. Everything else in the 4xx range is the
 * backend saying no for a reason this device cannot fix by waiting: a refusal
 * (409), a batch it cannot parse (422), one too large to accept (413). Those
 * used to be retried every minute forever, and because the refused batch sat
 * at the head of the queue nothing behind it ever drained either. */
const WORTH_RETRYING = new Set([408, 425, 429]);

function isPermanent(status) {
  return status >= 400 && status < 500 && status !== 401 && !WORTH_RETRYING.has(status);
}

/**
 * A batch id derived from the oldest queued row, not a fresh random one.
 *
 * A retry after a lost reply must look like the same batch, not a new one --
 * the backend's idempotence is keyed on this id. Minted once here and then
 * held in `state.pendingBatch` until the batch is accounted for, because the
 * oldest row does *not* reliably stay put: the heartbeat's `trim` runs on its
 * own alarm and can delete the head between two attempts.
 *
 * The epoch is in the id because the row key alone is not unique over time:
 * IndexedDB's autoIncrement counter restarts at 1 whenever the store is
 * recreated (an evicted database, cleared browsing data), so the first batch
 * after that would reuse an id the backend had already stored, be answered
 * `already_had_it`, and have its rows deleted as though they had been saved.
 */
function batchIdFor(deviceId, epoch, firstRowId) {
  return `bat_${deviceId.replace(/^dev_/, "")}_${epoch}_${firstRowId}`;
}

function isoFrom(ms) {
  return new Date(ms).toISOString();
}

/**
 * Both halves of a tick: the events, then the pictures.
 *
 * The pictures drain whether or not there were events this time. Each one is
 * keyed to a batch the backend has already accepted, so it no longer depends
 * on anything still being in the event queue -- which is the point of staging
 * them separately. A failed screenshot upload used to be given up on the spot,
 * because the alternative was holding stored evidence in the queue and
 * re-sending a whole batch to retry one PNG.
 */
export async function flush(deviceId) {
  if (!deviceId) return { uploaded: 0 };

  const batch = await sendBatch(deviceId);
  const shots = await drainShots(deviceId);

  return {
    ...batch,
    screenshots: shots.sent,
    // The events are the more important half, so their trouble is the trouble
    // reported when both halves had some.
    error: batch.error || shots.error,
  };
}

/** Drains what fits into one batch and uploads it. Returns how many events
 * actually went, or an `error` when the attempt did not land at all. */
async function sendBatch(deviceId) {
  const rows = await queue.peek(MAX_EVENTS);
  if (!rows.length) return { uploaded: 0 };

  // A store recreated under us rotates the epoch and clears any pending batch
  // itself, inside queue.js's open() and before this call could see a row --
  // so by the time `pendingBatch` is read below, a stale one from before the
  // eviction cannot still be here.
  const pending = await state.pendingBatch();
  let kept;
  let batchId;

  if (pending) {
    // Sent once already: it goes back as itself. Rows that `trim` removed in
    // the meantime are simply absent -- what must not change is the id, or the
    // survivors would be stored a second time under a new one.
    const byId = new Map(rows.map((row) => [row.id, row]));
    kept = pending.ids.map((id) => byId.get(id)).filter(Boolean);
    batchId = pending.batch_id;
    if (!kept.length) {
      await state.setPendingBatch(null);
      return { uploaded: 0 };
    }
  } else {
    kept = [];
    let bytes = 0;
    for (const row of rows) {
      // At least one event always goes, even past the byte cap -- a single
      // oversized event must not queue forever behind a limit it alone exceeds.
      if (kept.length && bytes + row.size > MAX_BYTES) break;
      kept.push(row);
      bytes += row.size;
    }
    const epoch = await state.queueEpoch();
    batchId = batchIdFor(deviceId, epoch, kept[0].id);
    // Written before the attempt, not after: a reply that never arrives is
    // exactly the case this exists for.
    await state.setPendingBatch({ batch_id: batchId, ids: kept.map((row) => row.id) });
  }

  const startedAt = kept[0].queuedAt;
  // A clock that steps backwards -- an NTP correction mid-queue -- would
  // otherwise produce a batch that ended before it started, which the domain
  // refuses outright. That refusal is permanent, so the batch would have sat
  // at the head of the queue being re-sent and re-refused forever.
  const endedAt = Math.max(kept[kept.length - 1].queuedAt, startedAt);

  const body = {
    batch_id: batchId,
    device_id: deviceId,
    started_at: isoFrom(startedAt),
    ended_at: isoFrom(endedAt),
    mode: "passive",
    recording_id: null,
    events: kept.map((row) => row.event),
  };

  try {
    await api.observations(body);
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) throw error;
    if (error instanceof ApiError && isPermanent(error.status)) {
      // Dropped, not retried. Said out loud rather than swallowed: evidence
      // being discarded is exactly the kind of thing that must not be quiet.
      await queue.remove(kept.map((row) => row.id));
      await state.setPendingBatch(null);
      return {
        uploaded: 0,
        dropped: kept.length,
        error: `the backend refused ${kept.length} events permanently (${error.status}): ${error.message}`,
      };
    }
    return { uploaded: 0, error: error instanceof ApiError ? error.message : String(error) };
  }

  // Before the rows go, and only now that the events are stored: a picture is
  // keyed by the batch it belongs to, so one staged against a batch the
  // backend never accepted is a picture nobody could find.
  await queue.stageShots(batchId, framesOf(kept));

  await queue.remove(kept.map((row) => row.id));
  await state.setPendingBatch(null);
  const remaining = await queue.count();
  return { uploaded: kept.length, remaining };
}

/**
 * Which rows of this batch carry a picture, and which frame each one
 * illustrates: the index of its gesture in this batch, counting gestures from
 * zero.
 *
 * The counter walks every gesture, not only the photographed ones, so a
 * gesture that went without a picture -- over the per-minute cap, a background
 * tab, trimmed for the byte budget -- does not shift every later frame onto
 * the wrong gesture. A retry indexes the same way it did the first time:
 * `trim` strips a picture but never drops the gesture row it hangs on, so the
 * gestures a re-sent batch names are the gestures it named before.
 */
function framesOf(kept) {
  const staged = [];
  let frameIndex = -1;
  for (const row of kept) {
    if (row.event?.kind !== "gesture") continue;
    frameIndex += 1;
    // `row.shot` is the picture's description, not its bytes: the queue hands
    // those to nobody, and `stageShots` reads them a row at a time.
    if (row.shot) staged.push({ rowId: row.id, frameIndex });
  }
  return staged;
}

/**
 * Upload staged screenshots, oldest first, and stop at the first sign the
 * backend is not taking them.
 *
 * Stopping rather than working through the rest: they all go to the same
 * endpoint that just refused, and a tick that tried ten in a row would spend
 * ten requests learning the same thing. The alarm brings the next attempt.
 */
async function drainShots(deviceId) {
  const rows = await queue.peekShots(MAX_SHOTS_PER_TICK);
  if (!rows.length) return { sent: 0 };

  let sent = 0;
  for (const row of rows) {
    const form = new FormData();
    form.append("device_id", deviceId);
    form.append("batch_id", row.batchId);
    form.append("kind", "screenshot");
    form.append("frame_index", String(row.frameIndex));
    form.append(
      "file",
      new Blob([row.bytes], { type: row.mime }),
      `${String(row.frameIndex).padStart(5, "0")}.png`,
    );

    try {
      await api.artifact(form);
      await queue.removeShots([row.id]);
      sent += 1;
      continue;
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) throw error;

      if (error instanceof ApiError && isPermanent(error.status)) {
        // The same rule the batch follows: a refusal that will not change on
        // the next attempt is a refusal, and the picture is dropped rather
        // than retried forever. Said out loud, because evidence being
        // discarded must not be quiet.
        await queue.removeShots([row.id]);
        return {
          sent,
          error: `the backend refused a screenshot permanently (${error.status}): ${error.message}`,
        };
      }

      const why = error instanceof ApiError ? error.message : String(error);
      const attempts = await queue.noteShotAttempt(row.id);
      if (attempts >= MAX_SHOT_ATTEMPTS) {
        await queue.removeShots([row.id]);
        return { sent, error: `a screenshot was given up after ${attempts} attempts: ${why}` };
      }
      return { sent, error: `a screenshot did not upload, attempt ${attempts}: ${why}` };
    }
  }

  return { sent };
}
