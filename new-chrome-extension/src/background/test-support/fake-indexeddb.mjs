// Just enough of IndexedDB to exercise queue.js outside a browser: named
// stores, keyPath with or without autoIncrement, add/put/get/delete/clear/
// count/openCursor with cursor update and delete, and an upgrade that reports
// the version it came from. Not a general IndexedDB implementation -- do not
// grow this beyond what queue.js needs.

function microtask(fn) {
  Promise.resolve().then(fn);
}

class FakeRequest {
  constructor() {
    this.onsuccess = null;
    this.onerror = null;
    this.result = undefined;
    this.error = undefined;
  }
  _succeed(result) {
    this.result = result;
    microtask(() => this.onsuccess?.());
  }
}

class FakeCursor {
  constructor(rows, index, table, advance) {
    this.value = rows[index];
    this._table = table;
    this._index = index;
    this._advance = advance;
  }
  update(row) {
    this._table.rows.set(row.id, { ...row });
    return new FakeRequest();
  }
  delete() {
    this._table.rows.delete(this.value.id);
    return new FakeRequest();
  }
  continue() {
    this._advance(this._index + 1);
  }
}

class FakeStore {
  constructor(table) {
    this._table = table;
  }
  add(row) {
    const req = new FakeRequest();
    // A store whose rows name their own key -- the shot store keys by batch
    // and frame -- keeps the key it was given; the event store counts.
    const id = row.id ?? this._table.nextId++;
    this._table.rows.set(id, { ...row, id });
    req._succeed(id);
    return req;
  }
  put(row) {
    return this.add(row);
  }
  get(id) {
    const req = new FakeRequest();
    req._succeed(this._table.rows.get(id));
    return req;
  }
  delete(id) {
    const req = new FakeRequest();
    this._table.rows.delete(id);
    req._succeed(undefined);
    return req;
  }
  clear() {
    const req = new FakeRequest();
    this._table.rows.clear();
    req._succeed(undefined);
    return req;
  }
  count() {
    const req = new FakeRequest();
    req._succeed(this._table.rows.size);
    return req;
  }
  openCursor() {
    const req = new FakeRequest();
    const table = this._table;
    // Snapshot the key order once, then re-read each row as the cursor
    // reaches it -- a row updated or deleted mid-sweep must be seen as it is
    // now, which is exactly what queue.trim() does.
    const ids = [...table.rows.keys()].sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
    const advance = (index) => {
      let at = index;
      while (at < ids.length && !table.rows.has(ids[at])) at += 1;
      if (at >= ids.length) {
        req.result = null;
        microtask(() => req.onsuccess?.());
        return;
      }
      const rows = ids.map((id) => table.rows.get(id));
      req.result = new FakeCursor(rows, at, table, advance);
      microtask(() => req.onsuccess?.());
    };
    advance(0);
    return req;
  }
}

class FakeTransaction {
  constructor(tables) {
    this._tables = tables;
    this.oncomplete = null;
    this.onerror = null;
    this.onabort = null;
    // One turn later than the cursor callbacks, so a sweep finishes before
    // the transaction reports completion.
    microtask(() => microtask(() => microtask(() => this.oncomplete?.())));
  }
  objectStore(name) {
    return new FakeStore(this._tables.get(name));
  }
}

class FakeDB {
  constructor() {
    this._tables = new Map();
    this.objectStoreNames = { contains: (name) => this._tables.has(name) };
    this.onversionchange = null;
    this.onclose = null;
  }
  createObjectStore(name) {
    const table = { rows: new Map(), nextId: 1 };
    this._tables.set(name, table);
    return new FakeStore(table);
  }
  transaction() {
    return new FakeTransaction(this._tables);
  }
}

/**
 * @param {number} startsAt - the version the database is already at, so a test
 * can be an *upgrade* rather than a first install. That difference is the whole
 * reason queue.js reads `oldVersion`: a store being created rotates the queue
 * epoch, and a version bump over live rows must not.
 */
export function fakeIndexedDB(startsAt = 0) {
  let version = startsAt;
  const held = new FakeDB();
  return {
    open(_name, wanted = 1) {
      const req = new FakeRequest();
      microtask(() => {
        req.result = held;
        if (wanted > version) {
          req.onupgradeneeded?.({ oldVersion: version });
          version = wanted;
        }
        req.onsuccess?.();
      });
      return req;
    },
  };
}
