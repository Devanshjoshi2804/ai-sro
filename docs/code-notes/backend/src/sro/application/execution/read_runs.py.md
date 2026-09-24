# Notes for `backend/src/sro/application/execution/read_runs.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/read_runs.py`](../../../../../../../backend/src/sro/application/execution/read_runs.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/read_runs.py#L1): Docstring

> Read runs, and ask one to stop. The audit trail is only useful if it can be
> looked at, and a run in somebody's own browser is only watchable if they can
> also interrupt it.

## module, [line 42](../../../../../../../backend/src/sro/application/execution/read_runs.py#L42): Note on the line above

Code: `NOT_IN_A_BROWSER_HERE = "that run is not being performed in a browser this process is driving"`

> Said by both stop buttons, so it is said once.
>
> `StopRun` below and `AbortWorkflowRun` in `workflow_runs.py` refuse the same
> thing for the same reason -- a run nothing in this process is driving cannot be
> stopped by this process -- and the two aggregates are the only difference
> between them. Two literals is how the console ends up with two sentences for
> one refusal, and a person told two different things about the same button reads
> it as two different failures.

## `CannotStop`, [line 38](../../../../../../../backend/src/sro/application/execution/read_runs.py#L38): Docstring

> This run is not one this process can stop.
>
> A `Conflict` rather than a plain domain error: the request is well formed
> and the run is real, it is just not in a state anybody can stop it from --
> which is 409, and is what tells a console to re-read the run rather than to
> change what it asked for.

## `StopRun`, [line 45](../../../../../../../backend/src/sro/application/execution/read_runs.py#L45): Docstring

> Ask a run being performed here to end at its next step.
>
> Only a run in somebody's own browser: that one is being driven by a task in
> this process, and the intention to stop is held in this process. A durable
> run belongs to the worker and would go on regardless -- answering "stopped"
> for it would be the console reporting something that did not happen, which
> is worse on this screen than not offering the button at all.

## `StopRun.execute`, [line 58](../../../../../../../backend/src/sro/application/execution/read_runs.py#L58): Comment (debt)

Code: `return run`

> ponytail: in-process only. A device run and its socket live in one
> worker, so stopping must land there too -- sticky-route by device_id
> if this is ever run with more than one.
