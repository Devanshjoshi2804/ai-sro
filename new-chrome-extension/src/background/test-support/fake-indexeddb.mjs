// Just enough of IndexedDB to exercise queue.js outside a browser: single
// store, keyPath + autoIncrement, add/delete/count/openCursor. Not a general
// IndexedDB implementation -- do not grow this beyond what queue.js needs.

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
  constructor(rows, index, advance) {
    this.value = rows[index];
    this._rows = rows;
    this._index = index;
    this._advance = advance;
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
  count() {
    const req = new FakeRequest();
    req._succeed(this._table.rows.size);
    return req;
  }
  openCursor() {
    const req = new FakeRequest();
    const rows = [...this._table.rows.values()].sort((a, b) => a.id - b.id);
    const advance = (index) => {
      if (index >= rows.length) {
        req.result = null;
        microtask(() => req.onsuccess?.());
        return;
      }
      req.result = new FakeCursor(rows, index, advance);
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
    microtask(() => this.oncomplete?.());
  }
  objectStore() {
    return new FakeStore(this._table);
  }
}

class FakeDB {
  constructor() {
    this._table = { rows: new Map(), nextId: 1 };
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
