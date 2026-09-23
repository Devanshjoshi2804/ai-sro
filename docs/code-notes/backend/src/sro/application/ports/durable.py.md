# Notes for `backend/src/sro/application/ports/durable.py`

Comments and docstrings moved out of [`backend/src/sro/application/ports/durable.py`](../../../../../../../backend/src/sro/application/ports/durable.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/ports/durable.py#L1): Docstring

> Work that must survive a process dying.
>
> Two very different needs behind one port:
>
> - **Induction** is a computation whose inputs are already durable. Running it
>   through a workflow buys retries and a history to look at when it fails, not
>   correctness.
> - **The session deadline** is the opposite: nothing else in the system will ever
>   notice that an operator walked away, so if this is not durable the recording
>   stays open forever.

## `DurableExecution.execute_skill`, [line 21](../../../../../../../backend/src/sro/application/ports/durable.py#L21): Docstring

> Perform a skill durably and wait for it to finish.
>
> Durable for a different reason again: a run touches a live warehouse one
> step at a time, and a process that dies halfway must be resumable
> without repeating the step that may already have landed.

## `DurableExecution.watch_recording`, [line 34](../../../../../../../backend/src/sro/application/ports/durable.py#L34): Docstring

> Start the deadline that reaps this demonstration if it is abandoned.
>
> Returns whether the watch was actually started. Best effort by contract:
> the recording is already durable by the time this is called, so a
> scheduler outage must cost a deadline, never the demonstration.

## `DurableExecution.recording_finished`, [line 43](../../../../../../../backend/src/sro/application/ports/durable.py#L43): Docstring

> Tell the deadline it is no longer needed. Never raises.
