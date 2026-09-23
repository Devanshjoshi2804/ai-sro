# Notes for `backend/src/sro/application/ports/schedule.py`

Comments and docstrings moved out of [`backend/src/sro/application/ports/schedule.py`](../../../../../../../backend/src/sro/application/ports/schedule.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/ports/schedule.py#L1): Docstring

> Handing a clock to somebody else.
>
> The system has no timer of its own for this on purpose. A cron loop in a process
> fires nothing while the process is down and fires twice when two are up, and
> both of those are a warehouse write. What this port asks for is a scheduler that
> already answers those questions.

## `SchedulerUnavailable`, [line 15](../../../../../../../backend/src/sro/application/ports/schedule.py#L15): Docstring

> No scheduler. Not a ``DomainError``: the trigger was fine.
>
> Raised rather than storing a trigger that will never fire, which is worse
> than refusing to store it -- somebody would believe the task was covered.

## `Scheduler.schedule`, [line 10](../../../../../../../backend/src/sro/application/ports/schedule.py#L10): Docstring

> Create or replace the schedule for this trigger.
>
> Idempotent on the trigger's id: the same trigger scheduled twice is one
> schedule, because the alternative is two runs of the same task at the
> same moment against the same records.

## `Scheduler.unschedule`, [line 12](../../../../../../../backend/src/sro/application/ports/schedule.py#L12): Docstring

> Idempotent: a schedule that is already gone is success.
>
> By id rather than by trigger, because the caller that most needs this is
> a schedule that outlived the trigger it was for -- there is no trigger
> left to pass.
