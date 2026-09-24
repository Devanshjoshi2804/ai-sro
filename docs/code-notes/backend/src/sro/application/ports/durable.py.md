# Notes for `backend/src/sro/application/ports/durable.py`

Comments and docstrings moved out of [`backend/src/sro/application/ports/durable.py`](../../../../../../../backend/src/sro/application/ports/durable.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/ports/durable.py#L1): Docstring

> Work that must survive a process dying.
>
> A computation whose inputs are already durable. Running it through a
> workflow buys retries and a history to look at when it fails, not
> correctness.

## `DurableExecution.execute_skill`, [line 11](../../../../../../../backend/src/sro/application/ports/durable.py#L11): Docstring

> Perform a skill durably and wait for it to finish.
>
> Durable for a different reason again: a run touches a live warehouse one
> step at a time, and a process that dies halfway must be resumable
> without repeating the step that may already have landed.
