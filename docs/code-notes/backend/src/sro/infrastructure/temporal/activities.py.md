# Notes for `backend/src/sro/infrastructure/temporal/activities.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/temporal/activities.py`](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L1): Docstring

> Activities: the effectful half. Everything that touches the world lives here.
>
> Arguments and returns are plain dataclasses because Temporal serialises them.
> Domain objects stay behind the use case, so a change to an aggregate never
> invalidates a workflow history.

## `StartRunRequest`, [line 40](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L40): Note on the line above

Code: `run_id: str = ""`

> Chosen before the workflow starts, so whoever asked can watch it.

## `StepResult`, [line 62](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L62): Note on the line above

Code: `mutating: bool`

> Whether this step changed the target system. The workflow uses it to
> decide that a failure must not be retried.

## `StepResult`, [line 64](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L64): Note on the line above

Code: `more: bool = False`

> Whether the run has another position to perform.
>
> Asked rather than counted, because a skill with a loop does not know how
> many steps it has until the system says how many things there are -- and a
> workflow that counted up front would stop after the first line of a
> twelve-line order.

## `TriggerRequest`, [line 69](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L69): Note on the line above

Code: `trigger_id: str`

> The whole request. A schedule has no caller, so the tenant and the
> principal come off the trigger itself rather than being carried here where
> they could disagree with it.

## `Activities`, [line 79](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L79): Docstring

> Bound to a container so the worker owns exactly one set of adapters.

## `Activities.fire_trigger`, [line 125](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L125): Docstring

> No context argument: a schedule has no caller, and the tenant comes
> off the trigger.

## module, [line 18](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L18): Comment

Code: `from sro.container import Container`

> Type-only: the composition root builds the activities, so importing it at
> runtime would make anything that schedules work import every adapter.

## `RunActivities._driven`, [line 185](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L185): Note

Code: `beating = self._container.run_steps()`

> A second instance: the beat runs while the work does, and one unit of work
> cannot be entered twice at once.

## `RunActivities._driven`, [line 193](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L193): Note

Code: `except PageGone:`

> The beat found the lease no longer live: the sweeper is about to close the
> context under the step, so the step is abandoned now and the lost page is
> raised for the retry to recover onto a fresh lease, rather than let it act
> on until the context dies mid-write.

## `RunActivities._driven`, [line 196](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L196): Note

Code: `except Exception:`

> Any other beat failure (the database away for a moment) never abandons the
> step: it is logged and the loop goes on.

## `RunActivities._driven`, [line 201](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L201): Note

Code: `if why is not None and why.cancel_requested:`

> Only an operator's stop (the workflow cancelled) sets `stop`: the work
> finishes its current action, records itself stopped (a step) or aborts the
> run once its tab is recorded (acquire), and only then does the cancellation
> go on (§7.4). A timeout, a worker shutdown or a pause is not a stop: the work
> is cancelled where it stands, the run stays `running`, and the retry picks
> it up from `progress` -- a write already marked is only ever read back.
