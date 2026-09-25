# Notes for `backend/src/sro/infrastructure/temporal/activities.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/temporal/activities.py`](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L1): Docstring

> Activities: the effectful half. Everything that touches the world lives here.
>
> Arguments and returns are plain dataclasses because Temporal serialises them.
> Domain objects stay behind the use case, so a change to an aggregate never
> invalidates a workflow history.

## `StartRunRequest`, [line 38](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L38): Note on the line above

Code: `run_id: str = ""`

> Chosen before the workflow starts, so whoever asked can watch it.

## `StepResult`, [line 60](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L60): Note on the line above

Code: `mutating: bool`

> Whether this step changed the target system. The workflow uses it to
> decide that a failure must not be retried.

## `StepResult`, [line 62](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L62): Note on the line above

Code: `more: bool = False`

> Whether the run has another position to perform.
>
> Asked rather than counted, because a skill with a loop does not know how
> many steps it has until the system says how many things there are -- and a
> workflow that counted up front would stop after the first line of a
> twelve-line order.

## `TriggerRequest`, [line 67](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L67): Note on the line above

Code: `trigger_id: str`

> The whole request. A schedule has no caller, so the tenant and the
> principal come off the trigger itself rather than being carried here where
> they could disagree with it.

## `Activities`, [line 77](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L77): Docstring

> Bound to a container so the worker owns exactly one set of adapters.

## `Activities.fire_trigger`, [line 123](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L123): Docstring

> No context argument: a schedule has no caller, and the tenant comes
> off the trigger.

## module, [line 16](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L16): Comment

Code: `from sro.container import Container`

> Type-only: the composition root builds the activities, so importing it at
> runtime would make anything that schedules work import every adapter.

## `RunActivities.step`, [line 156](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L156): Note

Code: `steps, beating = self._container.run_steps(), self._container.run_steps()`

> Two instances: the beat runs while the step does, and one unit of work
> cannot be entered twice at once.

## `RunActivities.step`, [line 164](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L164): Note

Code: `except Exception:`

> A beat that fails once (the database away for a moment) never abandons
> the step mid-write: it is logged and the loop goes on; a lease that is
> truly lost shows up as `PageGone` in the step itself.

## `RunActivities.step`, [line 167](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L167): Note

Code: `except asyncio.CancelledError:`

> A stop: the step sees it at its lane's next check, finishes its current
> action and records itself stopped before the cancellation goes on (§7.4).
