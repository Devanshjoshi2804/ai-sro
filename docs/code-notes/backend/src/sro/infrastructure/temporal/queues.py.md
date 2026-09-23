# Notes for `backend/src/sro/infrastructure/temporal/queues.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/temporal/queues.py`](../../../../../../../backend/src/sro/infrastructure/temporal/queues.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/temporal/queues.py#L1): Docstring

> Task queue names.
>
> Their own module because both the worker and the client need them, and the
> worker imports the container -- putting them there makes anything that schedules
> work depend on the composition root.
>
> Split by scarcity, not by feature: ``browser`` holds work tied to a browser
> slot, so a slow induction can never starve session reaping.
