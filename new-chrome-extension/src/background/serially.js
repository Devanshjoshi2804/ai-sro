// One change to storage at a time.
//
// Lifted out of `service-worker.js` unchanged, so a module the worker imports
// can take the same lock without importing the worker. Its own argument, kept
// whole:
//
// Read-modify-write over `chrome.storage` has no transaction: a tab closing
// while another is being watched read the old list and wrote it back, and the
// new watch vanished. That failure is invisible -- capture simply produces
// nothing -- so it is worth the four lines.
//
// One chain for every list this worker keeps, rather than one per list. They
// are all short writes to the same store, contention between two of them is
// rare, and a lock per list is a set of locks somebody has to remember to take
// the right one of.

let changes = Promise.resolve();

export function serially(job) {
  const next = changes.then(job, job);
  changes = next.then(
    () => {},
    () => {},
  );
  return next;
}
