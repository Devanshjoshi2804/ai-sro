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
 * which DOOR to ask is on it, and the two doors answer about different things.
 * `source: "rig"` means a mined workflow, at `GET /v1/workflow-runs/{id}`;
 * anything else -- including a record with no `source` at all, which is every
 * row an older worker wrote -- means a taught skill, at `GET /v1/runs/{id}`.
 * The two are separate resources and an id from one is a 404 at the other.
 *
 * **"rig" is a historical name and no longer a separate process.** This
 * comment used to say a run the rig drove was one the backend had never heard
 * of, because the rig was once its own service with its own store. It was
 * folded into the backend, and both kinds of run now live in the same
 * Postgres. The value on the record is left spelled `"rig"` because it is
 * persisted in `state.activeRun()` and written by `commands.js`,
 * `offering.js` and the worker; renaming it would strand whatever is in
 * flight in somebody's browser. Read it as "workflow run".
 *
 * Nothing is decided here past which door. `derived` and `reversal` are
 * computed against the tenant's whole skill library, which only the skill
 * door has, so a workflow run's card says so by having no undo on it rather
 * than by inventing one (see `panel.js`'s `finished()`).
 */
export async function noteFinished(active) {
  // ponytail: `state.activeRun()` is one slot for one run -- see the note above
  // `checkFinishing()` in `service-worker.js` for the ceiling that shares.
  // Not rig-versus-backend: both are this backend. Workflow run versus skill
  // run, two resources behind two doors. The spelling is the persisted one.
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
      // What it went looking for and could not find. The question about each
      // of these is already in the operator's thread -- the backend wrote it
      // as the run closed -- and this is what tells the panel to take them
      // there rather than leave them reading "The run stopped".
      needs: run.needs || [],
      // What it wrote, so the card can name the record rather than only
      // reporting the machinery that made it.
      //
      // This projection is a SUBSET of the run and that is deliberate -- a
      // stored copy of every field would be a second, staler run row in
      // browser storage. It is also the third place today a wire broke one
      // layer from where it was checked: `WorkflowRunModel` carries `values`,
      // and nothing carried it this far, so a card built to name the record
      // named nothing and looked exactly like a card that had not been
      // changed.
      values: run.values || {},
      gathered: run.gathered || {},
      watched: Boolean(run.watched),
      at: Date.now(),
    });
  } catch (error) {
    // A backend -- or a rig -- this browser cannot reach right now is not a
    // reason to show a stale or invented card. `state.activeRun()` is left as
    // it was, so the next trigger tries again.
    //
    // Except a door that answered: there is no such run. A run this browser
    // has an id for and the backend does not is a run that was never written
    // or has been retained away, so that answer will not change however long
    // this browser goes on asking -- once every poll and every heartbeat for
    // the hour it takes to age out. Nothing to show for it,
    // so nothing is shown; asking is what stops.
    if (source === "rig" && error?.status === 404) await forget(active.runId);
    return;
  }
  await forget(active.runId);
}

/** Stop asking about this run. Cleared only once there is a confirmed answer
 * for it -- or none there will ever be -- never on a failure to reach the
 * process driving it: guarded by id so a slow answer for a run this browser
 * has since moved past does not erase what the *next* run left behind. */
async function forget(runId) {
  const now = await state.activeRun();
  if (now?.runId === runId) await state.setActiveRun(null);
}
