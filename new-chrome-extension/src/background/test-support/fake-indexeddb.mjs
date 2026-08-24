// Just enough of IndexedDB to exercise queue.js outside a browser: single
// store, keyPath + autoIncrement, add/delete/clear/count/openCursor with
// cursor update and delete. Not a general IndexedDB implementation -- do not
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
    const id = this._table.nextId++;
    this._table.rows.set(id, { ...row, id });
    req._succeed(id);
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
    const ids = [...table.rows.keys()].sort((a, b) => a - b);
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
  constructor(table) {
    this._table = table;
    this.oncomplete = null;
    this.onerror = null;
    this.onabort = null;
    // One turn later than the cursor callbacks, so a sweep finishes before
    // the transaction reports completion.
    microtask(() => microtask(() => microtask(() => this.oncomplete?.())));
  }
  objectStore() {
    return new FakeStore(this._table);
  }
}

class FakeDB {
  constructor() {
    this._table = { rows: new Map(), nextId: 1 };
    this.onversionchange = null;
    this.onclose = null;
  }
  createObjectStore() {
    return new FakeStore(this._table);
  }
  transaction() {
    return new FakeTransaction(this._table);
  }
}

export function fakeIndexedDB() {
  return {
    open() {
      const req = new FakeRequest();
      const db = new FakeDB();
      microtask(() => {
        req.result = db;
        req.onupgradeneeded?.();
        req.onsuccess?.();
      });
      return req;
    },
  };
}
