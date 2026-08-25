// A durable queue of captured events, in IndexedDB.
//
// Not chrome.storage: that is quota-limited and meant for settings, not a
// growing log of everything an operator does in a day. MV3 evicts this
// service worker while it is idle, so nothing held only in a module
// variable survives to the next alarm -- IndexedDB is the one thing here
// that does.

import { state } from "./state.js";

const DB_NAME = "sro-observation-queue";
const DB_VERSION = 2;
const STORE = "events";

/** Screenshots whose batch has already been accepted, waiting for their own
 * upload. They leave the event row they were captured on the moment that
 * batch lands: the events are stored by then, and holding accepted evidence
 * in the queue to retry one picture would re-send the whole batch with it.
 *
 * Keyed by the batch and frame they belong to rather than by a counter, so a
 * flush that stages the same batch twice -- a reply lost after the events
 * were stored -- overwrites its own row instead of queueing a second copy of
 * the same picture. */
const SHOTS = "shots";

let opening = null;

function open() {
  if (!opening) {
    opening = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      let freshlyCreated = false;
      request.onupgradeneeded = (event) => {
        // `oldVersion === 0` is the store being created -- a first install, or
        // a database that was deleted or evicted underneath us. Either way the
        // autoIncrement counter restarts at 1, which the next row this worker
        // hands out will reuse. A version *upgrade* is not that: the rows and
        // the counter are still there, and rotating the epoch under them would
        // re-mint an id for a batch already in flight.
        freshlyCreated = event.oldVersion === 0;
        const db = request.result;
        if (!db.objectStoreNames.contains(STORE)) {
          db.createObjectStore(STORE, { keyPath: "id", autoIncrement: true });
        }
        if (!db.objectStoreNames.contains(SHOTS))
          db.createObjectStore(SHOTS, { keyPath: "id" });
      };
      request.onsuccess = () => {
        const db = request.result;
        // A connection can be closed underneath us -- another context asking
        // for a version change, or the browser reclaiming storage. Dropping
        // the cached promise means the next call opens a live one instead of
        // reusing a handle whose every transaction throws.
        db.onversionchange = () => {
          db.close();
          opening = null;
        };
        db.onclose = () => {
          opening = null;
        };
        if (!freshlyCreated) {
          resolve(db);
          return;
        }
        // Done here, before the promise resolves and before any caller can
        // read or write a row against the new counter -- not as a flag read
        // later by upload.js. A module boolean read at flush time missed the
        // eviction whenever the queue was empty when it happened: MV3 evicts
        // this worker after ~30s idle, `flush` returns before ever checking
        // the flag when there is nothing queued, and the next wake-up opens
        // the now-existing store with no onupgradeneeded to have set it.
        // Rotating here instead means it happens exactly once, synchronously
        // with the recreation, and is persisted before it can be missed.
        Promise.all([state.newQueueEpoch(), state.setPendingBatch(null)]).then(
          () => resolve(db),
          reject,
        );
      };
      request.onerror = () => {
        // Never leave a rejected promise cached: it would be handed to every
        // later call for the rest of this worker's life, so one transient
        // failure would look like a permanently broken queue.
        opening = null;
        reject(request.error);
      };
      request.onblocked = () => {
        opening = null;
        reject(
          new Error("the observation queue could not be opened; it is blocked"),
        );
      };
    });
  }
  return opening;
}

/** Settles the promise however the transaction ends -- including `abort`,
 * which is how a quota failure arrives and which used to leave the caller
 * waiting on a promise that never resolved. */
function settle(tx, resolve, reject, value) {
  tx.oncomplete = () => resolve(value);
  tx.onerror = () => reject(tx.error);
  tx.onabort = () =>
    reject(tx.error || new Error("the queue transaction was aborted"));
}

/** Bytes, not characters. `String.length` counts UTF-16 units, so every
 * non-ASCII payload -- a warehouse in any non-English locale, or the
 * «redacted» marker itself -- under-reported its own size, and both the batch
 * cap and the heartbeat's `queued_bytes` were wrong by that much. */
const sizeOf = (event) =>
  new TextEncoder().encode(JSON.stringify(event)).length;

/**
 * Add one protocol-shaped event to the tail of the queue, with the screenshot
 * that illustrates it when there is one.
 *
 * The screenshot rides on the row rather than in the event: it is not an event
 * kind the protocol has, it is uploaded to a different endpoint, and keeping it
 * beside its gesture is what lets `flush` name the frame it belongs to without
 * a second store to keep in step. `size` stays the size of the event alone --
 * it is what bounds a batch's JSON, which the picture is not part of.
 *
 * `recordingId` marks a row as part of a demonstration rather than ordinary
 * work. A batch is one or the other and never both: the backend refuses a
 * teaching batch that names no demonstration and a passive one that names one,
 * and it is right to -- evidence nobody can attribute is indistinguishable
 * from a morning's browsing.
 */
export async function enqueue(event, shot = null, recordingId = null) {
  const db = await open();
  const size = sizeOf(event);
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    const request = tx
      .objectStore(STORE)
      .add({ queuedAt: Date.now(), size, event, shot, recordingId });
    let id;
    // The row's own key, answered once the transaction has actually committed:
    // it is how a picture is fetched back out of the row at flush time without
    // anything having carried its bytes around in the meantime.
    request.onsuccess = () => {
      id = request.result;
    };
    tx.oncomplete = () => resolve(id);
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error || new Error("the queue transaction was aborted"));
  });
}

/**
 * The oldest `limit` rows, in insertion order, left in place. autoIncrement
 * keys only ever grow, so a cursor from the start of the store is already
 * oldest-first -- exactly what "flush what has waited longest" needs, with
 * no separate sort.
 */
export async function peek(limit) {
  const db = await open();
  return new Promise((resolve, reject) => {
    const rows = [];
    const tx = db.transaction(STORE, "readonly");
    const cursorRequest = tx.objectStore(STORE).openCursor();
    cursorRequest.onsuccess = () => {
      const cursor = cursorRequest.result;
      if (!cursor || rows.length >= limit) {
        resolve(rows);
        return;
      }
      rows.push({
        id: cursor.value.id,
        queuedAt: cursor.value.queuedAt,
        size: cursor.value.size,
        event: cursor.value.event,
        recordingId: cursor.value.recordingId || null,
        // What the picture is, never the picture. A batch of 500 rows each
        // carrying a megabyte of PNG is half a gigabyte in a service worker
        // that only needed 2MB of JSON -- and the bytes are read back a row at
        // a time by `stageShots` for the handful that are actually staged.
        shot: cursor.value.shot
          ? { mime: cursor.value.shot.mime, size: cursor.value.shot.size }
          : null,
      });
      cursor.continue();
    };
    cursorRequest.onerror = () => reject(cursorRequest.error);
    tx.onabort = () =>
      reject(tx.error || new Error("the queue transaction was aborted"));
  });
}

/** Remove rows once the backend has accepted them -- or once they have been
 * refused in a way that will not change. Never before one or the other. */
export async function remove(ids) {
  if (!ids.length) return;
  const db = await open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    const store = tx.objectStore(STORE);
    for (const id of ids) store.delete(id);
    settle(tx, resolve, reject);
  });
}

/** Empty the queue, pictures included. Used when the credential changes: what
 * one operator's browser captured must never be uploaded under the next
 * operator's identity, into the next operator's tenant. A staged screenshot is
 * the most literal form of that -- it is a photograph of the last operator's
 * screen -- so it goes with everything else. */
export async function clear() {
  const db = await open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction([STORE, SHOTS], "readwrite");
    tx.objectStore(STORE).clear();
    tx.objectStore(SHOTS).clear();
    settle(tx, resolve, reject);
  });
}

/**
 * Move the pictures of a batch that has just been accepted into the shot
 * store, keyed by the frame each one illustrates.
 *
 * Named by row id rather than handed the bytes: the caller has never held
 * them. Each picture is read out of the event row and written to the shot
 * store inside one transaction, so only the row being moved is in memory.
 *
 * `put`, not `add`: the key is the batch and the frame, so staging the same
 * batch twice replaces the row rather than doubling it.
 */
export async function stageShots(batchId, frames) {
  if (!frames.length) return;
  const db = await open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction([STORE, SHOTS], "readwrite");
    const events = tx.objectStore(STORE);
    const shots = tx.objectStore(SHOTS);
    for (const { rowId, frameIndex } of frames) {
      const request = events.get(rowId);
      request.onsuccess = () => {
        const shot = request.result?.shot;
        // Gone since the batch was sent -- `trim` strips a picture off a row
        // that is still queued -- and a frame with no picture is simply a
        // gesture that went unillustrated.
        if (!shot?.bytes) return;
        shots.put({
          id: `${batchId}:${frameIndex}`,
          batchId,
          frameIndex,
          stagedAt: Date.now(),
          attempts: 0,
          mime: shot.mime,
          size: shot.size,
          bytes: shot.bytes,
        });
      };
    }
    settle(tx, resolve, reject);
  });
}

/** The oldest `limit` staged screenshots, left in place. */
export async function peekShots(limit) {
  const db = await open();
  return new Promise((resolve, reject) => {
    const rows = [];
    const tx = db.transaction(SHOTS, "readonly");
    const cursorRequest = tx.objectStore(SHOTS).openCursor();
    cursorRequest.onsuccess = () => {
      const cursor = cursorRequest.result;
      if (!cursor || rows.length >= limit) {
        resolve(rows.sort((a, b) => a.stagedAt - b.stagedAt).slice(0, limit));
        return;
      }
      rows.push(cursor.value);
      cursor.continue();
    };
    cursorRequest.onerror = () => reject(cursorRequest.error);
    tx.onabort = () =>
      reject(tx.error || new Error("the queue transaction was aborted"));
  });
}

/** Remove staged screenshots -- uploaded, refused for good, or given up. */
export async function removeShots(ids) {
  if (!ids.length) return;
  const db = await open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(SHOTS, "readwrite");
    const store = tx.objectStore(SHOTS);
    for (const id of ids) store.delete(id);
    settle(tx, resolve, reject);
  });
}

/** Count one failed attempt against a staged screenshot and answer with the
 * total, which is what decides when to stop trying. */
export async function noteShotAttempt(id) {
  const db = await open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(SHOTS, "readwrite");
    const store = tx.objectStore(SHOTS);
    const request = store.get(id);
    let attempts = 0;
    request.onsuccess = () => {
      const row = request.result;
      if (!row) return;
      attempts = (row.attempts || 0) + 1;
      store.put({ ...row, attempts });
    };
    request.onerror = () => reject(request.error);
    settle(tx, resolve, reject, undefined);
    tx.oncomplete = () => resolve(attempts);
  });
}

export async function count() {
  const db = await open();
  return new Promise((resolve, reject) => {
    const request = db
      .transaction(STORE, "readonly")
      .objectStore(STORE)
      .count();
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

/** Summed from each row's own recorded size, screenshots included -- a fresh
 * scan every heartbeat, not a running total kept in a second place that could
 * drift from it.
 *
 * The pictures are counted because they are most of the bytes: a device whose
 * budget only ever measured the JSON would have reported a nearly empty queue
 * while holding a hundred megabytes of PNG. */
export async function totalBytes() {
  const [events, shots] = await Promise.all([sumOf(STORE), sumOf(SHOTS)]);
  return events + shots;
}

async function sumOf(store) {
  const db = await open();
  return new Promise((resolve, reject) => {
    let total = 0;
    const tx = db.transaction(store, "readonly");
    const cursorRequest = tx.objectStore(store).openCursor();
    cursorRequest.onsuccess = () => {
      const cursor = cursorRequest.result;
      if (!cursor) {
        resolve(total);
        return;
      }
      total += (cursor.value.size || 0) + (cursor.value.shot?.size || 0);
      cursor.continue();
    };
    cursorRequest.onerror = () => reject(cursorRequest.error);
    tx.onabort = () =>
      reject(tx.error || new Error("the queue transaction was aborted"));
  });
}

/**
 * Bring the queue back under `maxBytes`, giving up the least valuable thing
 * first. Returns what it did.
 *
 * The order is the one the design settled on before any of this was written,
 * with screenshots added at the front of it: staged pictures go, then the
 * pictures still riding on an unsent gesture, then response bodies, then whole
 * non-gesture events, and a gesture is never dropped. A gesture is the record
 * that the operator did something at all -- lose it and the task did not
 * happen as far as any miner can tell. A screenshot is the other end of that
 * scale: it is the largest thing here and it only illustrates a gesture that
 * is being kept anyway.
 *
 * Staged before unstaged because a staged picture's gesture is already stored
 * on the server -- giving it up costs the illustration and nothing else --
 * whereas one still on a queued row has yet to travel, and travels for free
 * with the batch that carries the gesture it belongs to.
 *
 * Without this the queue grew without limit whenever the backend was
 * unreachable or capture was paused, until IndexedDB refused a write and
 * capture died silently with a full database.
 */
export async function trim(maxBytes) {
  let total = await totalBytes();
  if (total <= maxBytes) {
    return {
      droppedShots: 0,
      strippedShots: 0,
      strippedBodies: 0,
      droppedEvents: 0,
      bytes: total,
    };
  }

  const db = await open();
  let droppedShots = 0;
  let strippedShots = 0;
  let strippedBodies = 0;
  let droppedEvents = 0;

  const sweep = (store, shouldAct, act) =>
    new Promise((resolve, reject) => {
      const tx = db.transaction(store, "readwrite");
      const cursorRequest = tx.objectStore(store).openCursor();
      cursorRequest.onsuccess = () => {
        const cursor = cursorRequest.result;
        if (!cursor || total <= maxBytes) {
          resolve();
          return;
        }
        const row = cursor.value;
        if (shouldAct(row)) {
          const before = (row.size || 0) + (row.shot?.size || 0);
          const after = act(cursor, row);
          total -= before - after;
        }
        cursor.continue();
      };
      cursorRequest.onerror = () => reject(cursorRequest.error);
      tx.onabort = () =>
        reject(tx.error || new Error("the queue transaction was aborted"));
    });

  // First pass: the staged screenshots. In key order, which is batch order --
  // near enough to oldest-first, and nothing here needs it to be exact.
  await sweep(
    SHOTS,
    () => true,
    (cursor) => {
      cursor.delete();
      droppedShots += 1;
      return 0;
    },
  );

  // Second pass: the screenshots still riding on a queued gesture.
  if (total > maxBytes) {
    await sweep(
      STORE,
      (row) => row.shot,
      (cursor, row) => {
        cursor.update({ ...row, shot: null });
        strippedShots += 1;
        return row.size || 0;
      },
    );
  }

  // Third pass: the response body of a request event, oldest first.
  if (total > maxBytes) {
    await sweep(
      STORE,
      (row) =>
        row.event?.kind === "request" && row.event.request?.response_body?.text,
      (cursor, row) => {
        const event = row.event;
        event.request.response_body = {
          ...event.request.response_body,
          text: null,
          size_bytes: 0,
          redacted_fields: ["«dropped: the device was over its byte budget»"],
        };
        const size = sizeOf(event);
        cursor.update({ ...row, event, size });
        strippedBodies += 1;
        return size;
      },
    );
  }

  // Fourth pass: whole events, but never a gesture.
  if (total > maxBytes) {
    await sweep(
      STORE,
      (row) => row.event?.kind !== "gesture",
      (cursor) => {
        cursor.delete();
        droppedEvents += 1;
        return 0;
      },
    );
  }

  return {
    droppedShots,
    strippedShots,
    strippedBodies,
    droppedEvents,
    bytes: total,
  };
}
