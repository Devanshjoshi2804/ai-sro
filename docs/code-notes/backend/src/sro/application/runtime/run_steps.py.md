# Notes for `backend/src/sro/application/runtime/run_steps.py`

Comments and docstrings moved out of [`backend/src/sro/application/runtime/run_steps.py`](../../../../../../../backend/src/sro/application/runtime/run_steps.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `RunSteps`, [line 51](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L51): Class

> A Steel run's activities (spec §7.2): prepare, acquire, one step per call,
> finish, release, beat. Each loads the run and its `progress` afresh, so a
> Temporal retry of any of them is safe: `progress` guards every write. It is
> written only through `record_progress` (D1); `save` carries the steps and
> the outcome. None of them acts on a run that is no longer `running`. A code
> change here is live only after the worker restarts (AGENTS.md).

## `RunSteps.step`, [line 117](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L117): Note

Code: `if progress.in_doubt(step.order):`

> A write marked `sending` (or settled `unknown`) by an earlier attempt is
> never sent again by any path: a retried step runs no lane, it settles the
> write by the API lane's read-back -- signed in afresh when the mark says the
> session had expired, credited to the lane that sent it -- else it asks.

## `RunSteps.step`, [line 139](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L139): Note

Code: `except (NeedsAPerson, AccountBusy, PageGone) as why:`

> The executor raises these carrying the lanes it tried; what they taught is
> learned before anything else. A person is asked; a busy account (another
> run's sign-in is parked on a person) and a lost page are raised again for
> the activity to retry. `Superseded` is raised untouched: another attempt
> holds the run.

## `RunSteps.step`, [line 165](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L165): Note

Code: `await self._teach.learn(ctx, workflow, by_id, step, tried, run_id=run_id, values=values)`

> Taught after the step is recorded, so a teaching failure never turns a
> write proven done back into one in doubt.

## `RunSteps.finish`, [line 168](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L168): Note

Code: `async def finish(self, ctx: RequestContext, run_id: str) -> str:`

> Runs on every path out of the workflow, so a run is never left `running`:
> `held` only when every step was reached and each is held or withheld;
> an outcome already set (a stop's `aborted`) is kept.

## `RunSteps.beat`, [line 193](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L193): Note

Code: `if progress.lease and not await self._broker.beat(ctx, progress.lease, holder=run_id):`

> A beat the lease no longer answers is a lost lease: the lost-page path.

## `RunSteps._keep_tab`, [line 234](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L234): Note

Code: `except BaseException:`

> A tab this attempt opened but could not record is closed at once; a retry
> would open another, and nothing would ever release the first.

## `RunSteps._sending`, [line 277](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L277): Note

Code: `if again and wrote == "sending":`

> The same lane run again after a re-sign-in (X8) marks the write it already
> marked; any other mark means another attempt got there first, and this one
> sends nothing.

## `RunSteps._settled`, [line 284](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L284): Note

Code: `async def _settled(`

> Settling an `unknown` write is this class's job (X8): a read-back first,
> signed in afresh when the result says the session expired; nothing to read
> back means a person is asked and the mark stays in doubt.

## `RunSteps._advance`, [line 319](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L319): Note

Code: `if progress.step != index:`

> The step index moves only from the index this attempt acted on to the next
> one; an attempt that finds it moved lost the run and records nothing.

## `RunSteps._ask`, [line 346](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L346): Note

Code: `async def _ask(`

> Every question is also a step row (`failed`, or `unclear` for a write
> nobody can confirm) with the question as its reason, so the console shows
> where and why the run stopped. Asked from prepare and acquire too, at the
> step the run stands on.

## `RunSteps._write`, [line 415](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L415): Note

Code: `ctx.tenant_id, run.id, now, was=run.progress`

> A compare-and-set: progress is written only over the progress this attempt
> loaded. Temporal can start a retry while the attempt it gave up on still
> runs (a missed heartbeat, a partition); whichever writes second finds it
> changed and stops with `Superseded`, so one write is never sent twice and
> a step is never skipped.

## `RunSteps._run`, [line 430](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L430): Note

Code: `raise Stopped(f"run {run_id} is not known")`

> A run this tenant does not hold is a stop: nothing more may be done for it,
> and retrying cannot bring it back.
