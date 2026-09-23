# Notes for `backend/src/sro/application/ports/dispatch.py`

Comments and docstrings moved out of [`backend/src/sro/application/ports/dispatch.py`](../../../../../../../backend/src/sro/application/ports/dispatch.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/ports/dispatch.py#L1): Docstring

> Starting a run in a process that is not this one.
>
> There is exactly one reason this exists: the channel to an operator's browser is
> held by whichever process the extension connected to, and the scheduler's worker
> is not that process. A run bound to a device is therefore asked for rather than
> performed here.
>
> Deliberately the same authority a person has -- start this taught skill, with
> these values -- and not "send this browser a command". An interface that could
> say the latter would be a way to drive somebody's signed-in session anywhere,
> which no taught skill can do.

## `DispatchFailed`, [line 36](../../../../../../../backend/src/sro/application/ports/dispatch.py#L36): Docstring

> The other process refused or could not be reached.

## `RunDispatcher.start`, [line 12](../../../../../../../backend/src/sro/application/ports/dispatch.py#L12): Docstring

> Ask whoever holds that browser to run this, and answer with the run.
>
> ``may_take_focus`` travels with it because the process that holds the
> socket is not the process that read the trigger, and whether an
> operator's screen may be taken is the trigger's decision rather than
> either process's.

## `RunDispatcher.start_job`, [line 25](../../../../../../../backend/src/sro/application/ports/dispatch.py#L25): Docstring

> The same, for a mined job rather than a taught skill.
>
> Separate from `start` rather than a flag on it, because the two are
> different authorities. `start` says "run this taught skill, with these
> values"; this says "replay this recording of somebody's own work in
> this browser". Live is not a parameter: a dry run of a scheduled job
> sends nothing and verifies nothing, and what keeps a live one safe is
> the ladder the run itself climbs.
