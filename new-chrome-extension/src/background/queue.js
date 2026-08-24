// A durable queue of captured events, in IndexedDB.
//
// Not chrome.storage: that is quota-limited and meant for settings, not a
// growing log of everything an operator does in a day. MV3 evicts this
// service worker while it is idle, so nothing held only in a module
// variable survives to the next alarm -- IndexedDB is the one thing here
// that does.

import { state } from "./state.js";

const DB_NAME = "sro-observation-queue";
const DB_VERSION = 1;
const STORE = "events";

let opening = null;

function open() {
  if (!opening) {
    opening = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      let freshlyCreated = false;
      request.onupgradeneeded = () => {
        // Fires when the store is created -- a first install, or a database
        // that was deleted or evicted underneath us. Either way the
        // autoIncrement counter restarts at 1, which the next row this
        // worker hands out will reuse.
        freshlyCreated = true;
        request.result.createObjectStore(STORE, { keyPath: "id", autoIncrement: true });
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
        reject(new Error("the observation queue could not be opened; it is blocked"));
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
  tx.onabort = () => reject(tx.error || new Error("the queue transaction was aborted"));
}

/** Bytes, not characters. `String.length` counts UTF-16 units, so every
 * non-ASCII payload -- a warehouse in any non-English locale, or the
 * «redacted» marker itself -- under-reported its own size, and both the batch
 * cap and the heartbeat's `queued_bytes` were wrong by that much. */
const sizeOf = (event) => new TextEncoder().encode(JSON.stringify(event)).length;

/** Add one protocol-shaped event to the tail of the queue. */
export async function enqueue(event) {
  const db = await open();
  const size = sizeOf(event);
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).add({ queuedAt: Date.now(), size, event });
    settle(tx, resolve, reject);
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
      });
      cursor.continue();
    };
    cursorRequest.onerror = () => reject(cursorRequest.error);
    tx.onabort = () => reject(tx.error || new Error("the queue transaction was aborted"));
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

/** Empty the queue. Used when the credential changes: what one operator's
 * browser captured must never be uploaded under the next operator's identity,
 * into the next operator's tenant. */
export async function clear() {
  const db = await open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).clear();
    settle(tx, resolve, reject);
  });
}

export async function count() {
  const db = await open();
  return new Promise((resolve, reject) => {
    const request = db.transaction(STORE, "readonly").objectStore(STORE).count();
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

/** Summed from each row's own recorded size -- a fresh scan every heartbeat,
 * not a running total kept in a second place that could drift from it. */
export async function totalBytes() {
  const db = await open();
  return new Promise((resolve, reject) => {
    let total = 0;
    const tx = db.transaction(STORE, "readonly");
    const cursorRequest = tx.objectStore(STORE).openCursor();
    cursorRequest.onsuccess = () => {
      const cursor = cursorRequest.result;
      if (!cursor) {
        resolve(total);
        return;
      }
      total += cursor.value.size || 0;
      cursor.continue();
    };
    cursorRequest.onerror = () => reject(cursorRequest.error);
    tx.onabort = () => reject(tx.error || new Error("the queue transaction was aborted"));
  });
}

/**
 * Bring the queue back under `maxBytes`, giving up the least valuable thing
 * first. Returns what it did.
 *
 * The order is the one the design settled on before any of this was written:
 * response bodies go, then whole non-gesture events, and a gesture is never
 * dropped. A gesture is the record that the operator did something at all --
 * lose it and the task did not happen as far as any miner can tell, whereas
 * losing a response body only costs some of the detail about how it went.
 *
 * Without this the queue grew without limit whenever the backend was
 * unreachable or capture was paused, until IndexedDB refused a write and
 * capture died silently with a full database.
 */
export async function trim(maxBytes) {
  let total = await totalBytes();
  if (total <= maxBytes) return { strippedBodies: 0, droppedEvents: 0, bytes: total };

  const db = await open();
  let strippedBodies = 0;
  let droppedEvents = 0;

  const sweep = (shouldAct, act) =>
    new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      const cursorRequest = tx.objectStore(STORE).openCursor();
      cursorRequest.onsuccess = () => {
        const cursor = cursorRequest.result;
        if (!cursor || total <= maxBytes) {
          resolve();
          return;
        }
        const row = cursor.value;
        if (shouldAct(row)) {
          const before = row.size || 0;
          const after = act(cursor, row);
          total -= before - after;
        }
        cursor.continue();
      };
      cursorRequest.onerror = () => reject(cursorRequest.error);
      tx.onabort = () => reject(tx.error || new Error("the queue transaction was aborted"));
    });

  // First pass: the response body of a request event, oldest first.
  await sweep(
    (row) => row.event?.kind === "request" && row.event.request?.response_body?.text,
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

  // Second pass: whole events, but never a gesture.
  if (total > maxBytes) {
    await sweep(
      (row) => row.event?.kind !== "gesture",
      (cursor) => {
        cursor.delete();
        droppedEvents += 1;
        return 0;
      },
    );
  }

  return { strippedBodies, droppedEvents, bytes: total };
}
