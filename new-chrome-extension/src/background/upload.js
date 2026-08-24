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
 * the backend's idempotence is keyed on this id, and the oldest row's own
 * key stays the same across retries because nothing is removed from the
 * queue until a batch actually lands.
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

/** Drains what fits into one batch and uploads it. Returns how many events
 * actually went, or an `error` when the attempt did not land at all. */
export async function flush(deviceId) {
  if (!deviceId) return { uploaded: 0 };

  const rows = await queue.peek(MAX_EVENTS);
  if (!rows.length) return { uploaded: 0 };

  let bytes = 0;
  const kept = [];
  for (const row of rows) {
    // At least one event always goes, even past the byte cap -- a single
    // oversized event must not queue forever behind a limit it alone exceeds.
    if (kept.length && bytes + row.size > MAX_BYTES) break;
    kept.push(row);
    bytes += row.size;
  }

  const epoch = await state.queueEpoch();
  const startedAt = kept[0].queuedAt;
  // A clock that steps backwards -- an NTP correction mid-queue -- would
  // otherwise produce a batch that ended before it started, which the domain
  // refuses outright. That refusal is permanent, so the batch would have sat
  // at the head of the queue being re-sent and re-refused forever.
  const endedAt = Math.max(kept[kept.length - 1].queuedAt, startedAt);

  const body = {
    batch_id: batchIdFor(deviceId, epoch, kept[0].id),
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
      return {
        uploaded: 0,
        dropped: kept.length,
        error: `the backend refused ${kept.length} events permanently (${error.status}): ${error.message}`,
      };
    }
    return { uploaded: 0, error: error instanceof ApiError ? error.message : String(error) };
  }

  await queue.remove(kept.map((row) => row.id));
  const remaining = await queue.count();
  return { uploaded: kept.length, remaining };
}
