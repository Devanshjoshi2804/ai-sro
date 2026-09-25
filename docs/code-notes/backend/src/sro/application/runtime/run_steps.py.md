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

## `RunSteps.beat`, [line 203](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L203): Note

Code: `if progress.lease and not await self._broker.beat(ctx, progress.lease, holder=run_id):`

> A beat the lease no longer answers is a lost lease: the lost-page path.

## `RunSteps._keep_tab`, [line 244](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L244): Note

Code: `except BaseException:`

> A tab this attempt opened but could not record is closed at once; a retry
> would open another, and nothing would ever release the first.

## `RunSteps._sending`, [line 287](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L287): Note

Code: `if again and wrote == "sending":`

> The same lane run again after a re-sign-in (X8) marks the write it already
> marked; any other mark means another attempt got there first, and this one
> sends nothing.

## `RunSteps._settled`, [line 294](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L294): Note

Code: `async def _settled(`

> Settling an `unknown` write is this class's job (X8): a read-back first,
> signed in afresh when the result says the session expired; nothing to read
> back means a person is asked and the mark stays in doubt.

## `RunSteps._advance`, [line 340](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L340): Note

Code: `progress.step, progress.asking = index + 1, {}`

> A step that settles after asking withdraws its own question: the held row
> follows the unclear one, and D5 takes an answer to a withdrawn question as
> already answered.

## `RunSteps._ask`, [line 356](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L356): Note

Code: `async def _ask(`

> Every question is also a step row (`failed`, or `unclear` for a write
> nobody can confirm) with the question as its reason, so the console shows
> where and why the run stopped. Asked from prepare and acquire too, at the
> step the run stands on.

## `RunSteps._write`, [line 429](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L429): Note

Code: `ctx.tenant_id, run.id, now, was=run.progress`

> A compare-and-set: progress is written only over the progress this attempt
> loaded. Temporal can start a retry while the attempt it gave up on still
> runs (a missed heartbeat, a partition); whichever writes second finds it
> changed and stops with `Superseded`, so one write is never sent twice and
> a step is never skipped.

## `RunSteps._run`, [line 444](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L444): Note

Code: `raise Stopped(f"run {run_id} is not known")`

> A run this tenant does not hold is a stop: nothing more may be done for it,
> and retrying cannot bring it back.

## `RunSteps.finish`, [line 171](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L171): Note

Code: `last = {one.of_step: one.verdict for one in sorted(run.steps, key=lambda s: s.order)}`

> Judged by each step's last row: an `unclear` a read-back later settled as
> `held` is history, not the step's result.

## `RunSteps._write`, [line 422](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L422): Note

Code: `if (index is not None and loaded.step != index) or (`

> The one guard every step write passes, beside the compare-and-set: an
> attempt only records a step's result or question while the run still
> stands on that step, and a question only while the step is not done. A
> zombie whose lane fails after the retry already held the step asks nothing
> and adds no row.

## `RunSteps.stopped`, [line 181](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L181): Note

Code: `async def stopped(self, ctx: RequestContext, run_id: str) -> None:`

> The one place a stopped run is recorded `aborted`: the workflow calls it
> after the operator's cancel, and `acquire` calls it when the stop arrived
> while it was signing in. A run the step already closed (a lane raised
> `Stopped`, or it held) is left as it is.
