// Batching and uploading what queue.js is holding.
//
// Runs on an alarm tick rather than per event: a busy minute of clicking
// would otherwise be a busy minute of requests. Nothing leaves the queue
// until the backend has accepted it -- a failed upload is retried whole on
// the next tick, and no separate backoff timer is needed because the alarm
// already paces every attempt the same way.

import { api, ApiError } from "./api.js";
import * as queue from "./queue.js";

const MAX_EVENTS = 500;
const MAX_BYTES = 2 * 1024 * 1024;

/**
 * A batch_id derived from the oldest queued row, not a fresh random one.
 *
 * A retry after a lost reply must look like the same batch, not a new one --
 * the backend's idempotence is keyed on this id, and the oldest row's own
 * key stays the same across retries because nothing is removed from the
 * queue until a batch actually lands.
 */
function batchIdFor(deviceId, firstRowId) {
  return `bat_${deviceId.replace(/^dev_/, "")}_${firstRowId}`;
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

  const body = {
    batch_id: batchIdFor(deviceId, kept[0].id),
    device_id: deviceId,
    started_at: isoFrom(kept[0].queuedAt),
    ended_at: isoFrom(kept[kept.length - 1].queuedAt),
    mode: "passive",
    recording_id: null,
    events: kept.map((row) => row.event),
  };

  try {
    await api.observations(body);
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) throw error;
    return { uploaded: 0, error: error instanceof ApiError ? error.message : String(error) };
  }

  await queue.remove(kept.map((row) => row.id));
  const remaining = await queue.count();
  return { uploaded: kept.length, remaining };
}
