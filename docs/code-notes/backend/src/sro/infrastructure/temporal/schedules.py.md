# Notes for `backend/src/sro/infrastructure/temporal/schedules.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/temporal/schedules.py`](../../../../../../../backend/src/sro/infrastructure/temporal/schedules.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/temporal/schedules.py#L1): Docstring

> Temporal Schedules: the clock this system does not keep itself.
>
> A cron loop in a process fires nothing while that process is down and twice
> while two are up, and both of those are a warehouse write. Temporal already
> answers those questions, and the deployment already runs it.
>
> The schedule id is derived from the trigger id, which is what makes creating one
> twice idempotent -- the same trigger scheduled again is one schedule, not two
> runs of the same task at the same moment against the same records.

## `TemporalScheduler._connect`, [line 67](../../../../../../../backend/src/sro/infrastructure/temporal/schedules.py#L67): Docstring

> Connected on first use, not at boot: a Temporal outage must not stop
> the API from serving reads. Same reason as the durable adapter.

## `TemporalScheduler.schedule`, [line 45](../../../../../../../backend/src/sro/infrastructure/temporal/schedules.py#L45): Comment

Code: `id=f"fire-{trigger.id.value}",`

> Derived, so a firing is traceable to the trigger that caused it
> without a lookup.

## `TemporalScheduler.schedule`, [line 53](../../../../../../../backend/src/sro/infrastructure/temporal/schedules.py#L53): Comment

Code: `handle = client.get_schedule_handle(schedule_id(trigger.id))`

> Idempotent by id: an update replaces the spec rather than adding
> a second schedule for the same trigger.

## `TemporalScheduler.unschedule`, [line 65](../../../../../../../backend/src/sro/infrastructure/temporal/schedules.py#L65): Comment

Code: `logger.debug("no schedule for trigger %s to remove", trigger_id)`

> Already gone. Deleting what is not there is the success this port
> promises, because a failed teardown must be safe to repeat.
