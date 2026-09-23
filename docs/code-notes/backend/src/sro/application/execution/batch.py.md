# Notes for `backend/src/sro/application/execution/batch.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/batch.py`](../../../../../../../backend/src/sro/application/execution/batch.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/batch.py#L1): Docstring

> Doing the same taught task to several things at once.
>
> A batch is not a new kind of execution. It is N runs of one skill version, each
> with its own idempotency keys, its own audit record and its own verification --
> so one item failing tells you nothing about the others, and the failure names
> which item it was.
>
> Two rules that keep a batch from being the worst thing in the system:
>
> - **The operator confirms the table, not the sentence.** What the model read out
>   of "these six SKUs" is shown as parameter sets before anything is sent, and
>   that confirmation is the authorisation each assisted run records.
> - **It stops on a system that is failing.** The circuit breaker is checked per
>   run, so a batch against a WMS that started answering 500 stops after the third
>   rather than sending the remaining forty.

## `BatchResult`, [line 30](../../../../../../../backend/src/sro/application/execution/batch.py#L30): Note on the line above

Code: `stopped_early: str | None = None`

> Why the rest were not attempted. Present when a limit stopped the batch,
> absent when everything was tried.

## `RunBatch.execute`, [line 66](../../../../../../../backend/src/sro/application/execution/batch.py#L66): Comment

Code: `done.append(Item(parameters=parameters, refused=str(refusal)))`

> A safety limit, not this item's fault. Everything after it
> would hit the same wall, so the batch stops and says so.

## `RunBatch.execute`, [line 69](../../../../../../../backend/src/sro/application/execution/batch.py#L69): Comment

Code: `done.append(Item(parameters=parameters, refused=str(refusal)))`

> This item cannot run -- a missing value, usually. The others
> still can, so the batch carries on.
