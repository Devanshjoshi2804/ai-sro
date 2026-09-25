# Notes for `backend/src/sro/application/runtime/run_steps.py`

Comments and docstrings moved out of [`backend/src/sro/application/runtime/run_steps.py`](../../../../../../../backend/src/sro/application/runtime/run_steps.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `RunSteps`, [line 43](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L43): Class

> A Steel run's activities (spec §7.2): prepare, acquire, one step per call,
> finish, release, beat. Each loads the run and its `progress` afresh, so a
> Temporal retry of any of them is safe: `progress` guards every write. It is
> written only through `record_progress` (D1); `save` carries the steps and
> the outcome. A code change here is live only after the worker restarts
> (AGENTS.md).

## `RunSteps.step`, [line 104](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L104): Note

Code: `if progress.in_doubt(step.order):`

> A write marked `sending` (or settled `unknown`) by an earlier attempt is
> never sent again by any path: a retried step runs no lane, it settles the
> write by the API lane's read-back, else it asks. The earlier attempt's
> result is lost with it, so the read-back is not told the session expired.

## `RunSteps.step`, [line 116](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L116): Note

Code: `except (NeedsAPerson, AccountBusy, PageGone) as why:`

> The executor raises these carrying the lanes it tried; what they taught is
> learned before anything else. A person is asked; a busy account (another
> run's sign-in is parked on a person) and a lost page are raised again for
> the activity to retry. `Stopped` and cancellation are never caught here
> beyond recording the stop.

## `RunSteps.finish`, [line 135](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L135): Note

Code: `async def finish(self, ctx: RequestContext, run_id: str) -> str:`

> Runs on every path out of the workflow, so a run is never left `running`:
> `held` only when every step was reached and each is held or withheld;
> an outcome already set (a stop's `aborted`) is kept.

## `RunSteps._settled`, [line 212](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L212): Note

Code: `async def _settled(`

> Settling an `unknown` write is this class's job (X8): a read-back first,
> signed in afresh when the result says the session expired; nothing to read
> back means a person is asked and the mark stays in doubt.

## `RunSteps._stopped`, [line 290](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L290): Note

Code: `async def _stopped(self, ctx: RequestContext, run_id: str, step: Step) -> StepOutcome:`

> A step stopped after its write went out is `unclear`, not `skipped`: the
> write may have landed.

## `RunSteps._run`, [line 321](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L321): Note

Code: `raise Stopped(f"run {run_id} is not known")`

> A run this tenant does not hold (or `record_progress` answering false) is
> a stop: nothing more may be done for it, and retrying cannot bring it back.
