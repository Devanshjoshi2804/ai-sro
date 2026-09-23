# Notes for `backend/src/sro/application/recording/ingest_capture_events.py`

Comments and docstrings moved out of [`backend/src/sro/application/recording/ingest_capture_events.py`](../../../../../../../backend/src/sro/application/recording/ingest_capture_events.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/recording/ingest_capture_events.py#L1): Docstring

> Fold a batch of capture events into a live recording.

## `IngestResult`, [line 16](../../../../../../../backend/src/sro/application/recording/ingest_capture_events.py#L16): Note on the line above

Code: `absorbed_requests: int`

> Calls attached to the previous action because they finished after a drain.

## `IngestResult`, [line 18](../../../../../../../backend/src/sro/application/recording/ingest_capture_events.py#L18): Note on the line above

Code: `orphaned_requests: int`

> Calls with no action to attach to at all: page-load noise.

## `IngestCaptureEvents`, [line 21](../../../../../../../backend/src/sro/application/recording/ingest_capture_events.py#L21): Docstring

> Append-only, so a retried batch duplicates rather than corrupts.
>
> Duplication is visible in the review UI; a rewritten frame would not be.

## `IngestCaptureEvents.execute`, [line 36](../../../../../../../backend/src/sro/application/recording/ingest_capture_events.py#L36): Comment

Code: `absorbed = recording.absorb_late_evidence(requests=assembled.unattached_requests)`

> Absorb before appending: unattached traffic precedes this batch's
> actions, so it belongs to the frame that was already the last one.
