# Notes for `backend/src/sro/infrastructure/temporal/activities.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/temporal/activities.py`](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L1): Docstring

> Activities: the effectful half. Everything that touches the world lives here.
>
> Arguments and returns are plain dataclasses because Temporal serialises them.
> Domain objects stay behind the use case, so a change to an aggregate never
> invalidates a workflow history.

## `StartRunRequest`, [line 32](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L32): Note on the line above

Code: `run_id: str = ""`

> Chosen before the workflow starts, so whoever asked can watch it.

## `StepResult`, [line 54](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L54): Note on the line above

Code: `mutating: bool`

> Whether this step changed the target system. The workflow uses it to
> decide that a failure must not be retried.

## `StepResult`, [line 56](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L56): Note on the line above

Code: `more: bool = False`

> Whether the run has another position to perform.
>
> Asked rather than counted, because a skill with a loop does not know how
> many steps it has until the system says how many things there are -- and a
> workflow that counted up front would stop after the first line of a
> twelve-line order.

## `TriggerRequest`, [line 61](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L61): Note on the line above

Code: `trigger_id: str`

> The whole request. A schedule has no caller, so the tenant and the
> principal come off the trigger itself rather than being carried here where
> they could disagree with it.

## `Activities`, [line 71](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L71): Docstring

> Bound to a container so the worker owns exactly one set of adapters.

## `Activities.fire_trigger`, [line 117](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L117): Docstring

> No context argument: a schedule has no caller, and the tenant comes
> off the trigger.

## module, [line 12](../../../../../../../backend/src/sro/infrastructure/temporal/activities.py#L12): Comment

Code: `from sro.container import Container`

> Type-only: the composition root builds the activities, so importing it at
> runtime would make anything that schedules work import every adapter.
