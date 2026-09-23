# Notes for `backend/src/sro/domain/observation/batch.py`

Comments and docstrings moved out of [`backend/src/sro/domain/observation/batch.py`](../../../../../../../backend/src/sro/domain/observation/batch.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/observation/batch.py#L1): Docstring

> What one upload from one device was, and where its evidence went.

## `CaptureMode`, [line 12](../../../../../../../backend/src/sro/domain/observation/batch.py#L12): Note on the line above

Code: `PASSIVE = "passive"`

> Nobody said "watch this". The stream an operator's ordinary day produces.

## `CaptureMode`, [line 14](../../../../../../../backend/src/sro/domain/observation/batch.py#L14): Note on the line above

Code: `TEACHING = "teaching"`

> An operator asked to be recorded, with the debugger attached. Richer
> evidence, and the tier a candidate falls back to when passive evidence is
> too thin to induce from.

## `check_times`, [line 29](../../../../../../../backend/src/sro/domain/observation/batch.py#L29): Docstring

> The two rules about a batch's clock, asked before the evidence is
> written as well as when the row is built.
>
> `ObservationBatch.__post_init__` is the authority and it runs LAST: ingest
> writes the NDJSON object first and constructs the row after it, so an
> upload whose envelope carried an offset-less time answered 422 with the
> object already in the store. The transaction rolls back; the object does
> not, and no row points at it -- so neither a purge nor the retention sweep
> will ever reach it. Asked here too, before the write, so the refusal costs
> nothing but the refusal.

## `ObservationBatch`, [line 42](../../../../../../../backend/src/sro/domain/observation/batch.py#L42): Docstring

> The row. The events themselves are one object in the blob store.
>
> A day of capture is millions of events and none of them is queried by id --
> they are read whole, by a miner, over a window. Putting them in a column
> would make the row that says "this arrived" as expensive to read as the
> evidence it points at.
>
> Not `observation.gesture.GestureBatch`, which is the miner's own tally of an
> upload whose gestures were stored row by row. Separate tables, and one
> upload can be described by both.

## `ObservationBatch`, [line 56](../../../../../../../backend/src/sro/domain/observation/batch.py#L56): Note on the line above

Code: `recording_id: RecordingId | None = None`

> The demonstration this batch is part of, for teaching capture.
>
> A teaching batch without one is evidence nobody can attribute: the operator
> was asked to show the system a task, and what came back cannot be told from
> an ordinary morning's browsing. A passive batch with one would be the
> opposite mistake -- ordinary work filed as a deliberate demonstration.
