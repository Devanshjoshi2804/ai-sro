// How a run this browser was driving ended, and which process to ask.
//
// Lifted out of `service-worker.js` -- where `checkFinishing()` still lives and
// still decides *when* to ask -- for one reason: that file registers chrome
// listeners the moment it is imported and cannot be loaded in plain node at
// all, so the branch below had no self-check. See `finishing.test.mjs`.

import { api } from "./api.js";
import { state } from "./state.js";

/**
 * Ask whoever drove this run how it ended, and keep the answer for the panel.
 *
 * `active` is the whole `state.activeRun()` record rather than its id, because
 * which process to ask is on it. A run the rig drove is a run the backend has
 * never heard of -- the id is the rig's own -- so asking the backend about it
 * would answer 404 forever and store nothing.
 *
 * A record with no `source` is a backend run: every row an older worker wrote
 * has none, and reading a missing field as "rig" would send all of them to a
 * rig that may not even be configured.
 *
 * Nothing is decided here past that. `derived` and `reversal` are computed
 * against the tenant's whole skill library and only ever copied from the
 * backend's own record; the rig has neither, and a rig run's card says so by
 * having no undo on it rather than by inventing one (see `panel.js`'s
 * `finished()`).
 */
export async function noteFinished(active) {
  const source = active.source === "rig" ? "rig" : "backend";
  try {
    const run = source === "rig" ? await api.rigRun(active.runId) : await api.run(active.runId);
    // The one status both vocabularies share, and it means the same thing in
    // each: the quiet window landed between two of the run's own steps rather
    // than after its last one. Nothing is stored and `state.activeRun()` is
    // left as it was, so the next trigger asks again.
    if (run.status === "running") return;
    await state.setFinishedRun({
      id: run.id,
      source,
      status: run.status,
      // The rig's card draws these; the backend's draws the skill's plan and
      // leaves them empty. Both are copied rather than merged, so neither
      // shape has to know about the other.
      steps: run.steps || [],
      withheld: run.withheld || [],
      derived: run.derived || {},
      reversal: run.reversal || null,
      failure: run.failure || null,
      // Copied from the run's own record, not only written by the press that
      // set it. A run called wrong in the console, or by a press whose row
      // this browser has since rebuilt, came back here with `wrongBecause`
      // unset -- so the card went on offering "It's wrong" for a run the
      // backend refuses to hear it about a second time, and `undoRun` sent a
      // `run-wrong` guaranteed to fail.
      wrongBecause: run.wrong_because || null,
      at: Date.now(),
    });
  } catch {
    // A backend -- or a rig -- this browser cannot reach right now is not a
    // reason to show a stale or invented card. `state.activeRun()` is left as
    // it was, so the next trigger tries again.
    return;
  }
  // Resolved -- stop asking about this run. Cleared only once there is a
  // confirmed, terminal answer to show for it, never on a failure to reach the
  // backend: guarded by id so a slow answer for a run this browser has since
  // moved past does not erase what the *next* run left behind instead.
  const now = await state.activeRun();
  if (now?.runId === active.runId) await state.setActiveRun(null);
}
