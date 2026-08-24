// A durable queue of captured events, in IndexedDB.
//
// Not chrome.storage: that is quota-limited and meant for settings, not a
// growing log of everything an operator does in a day. MV3 evicts this
// service worker while it is idle, so nothing held only in a module
// variable survives to the next alarm -- IndexedDB is the one thing here
// that does.

const DB_NAME = "sro-observation-queue";
const DB_VERSION = 1;
const STORE = "events";

let opening = null;

function open() {
  if (!opening) {
    opening = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = () => {
        request.result.createObjectStore(STORE, { keyPath: "id", autoIncrement: true });
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }
  return opening;
}

/** Add one protocol-shaped event to the tail of the queue. */
export async function enqueue(event) {
  const db = await open();
  const size = JSON.stringify(event).length;
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).add({ queuedAt: Date.now(), size, event });
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
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
    const cursorRequest = db.transaction(STORE, "readonly").objectStore(STORE).openCursor();
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
  });
}

/** Remove rows once the backend has accepted them -- never before. */
export async function remove(ids) {
  if (!ids.length) return;
  const db = await open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    const store = tx.objectStore(STORE);
    for (const id of ids) store.delete(id);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
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
    const cursorRequest = db.transaction(STORE, "readonly").objectStore(STORE).openCursor();
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
  });
}
