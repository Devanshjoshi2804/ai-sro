# Notes for `backend/src/sro/application/observation/demonstrate.py`

Comments and docstrings moved out of [`backend/src/sro/application/observation/demonstrate.py`](../../../../../../../backend/src/sro/application/observation/demonstrate.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/observation/demonstrate.py#L1): Docstring

> A demonstration performed in the operator's own browser, turned into frames.
>
> The server-side path drives a browser through CDP and assembles frames as they
> happen. This one cannot: the evidence arrives afterwards, in teaching-mode
> observation batches, minutes of it at a time and out of the process that will
> read it.
>
> So the frames are assembled once, when the demonstration is sealed, from every
> batch that named it. Not per upload: a click and the call it caused routinely
> land in different batches, and a frame split across that seam is a step that
> lost its evidence -- which is a skill that replays a click and never checks what
> it did.

## `NothingDemonstrated`, [line 19](../../../../../../../backend/src/sro/application/observation/demonstrate.py#L19): Docstring

> The operator was asked to show the system a task and nothing usable
> arrived. Said out loud rather than sealing an empty recording, which
> induction would later refuse in a place much further from the operator.

## `_events_in`, [line 69](../../../../../../../backend/src/sro/application/observation/demonstrate.py#L69): Docstring

> One upload's NDJSON, as the events the assembler folds.
>
> Anything that will not decode is skipped rather than raised: these bytes
> were screened at ingest against the shapes the protocol declares, so a line
> that fails here is a version of the extension this deployment has not seen,
> and losing one event is better than losing the demonstration.

## `_at`, [line 119](../../../../../../../backend/src/sro/application/observation/demonstrate.py#L119): Docstring

> The recorder's float seconds since the epoch.

## `AssembleDemonstration.execute`, [line 39](../../../../../../../backend/src/sro/application/observation/demonstrate.py#L39): Comment

Code: `return Assembled(recording_id=recording_id, frames=len(recording.frames), batches=0)`

> Already assembled. Sealing is two calls -- assemble, then
> finish -- and anything that retries the second after the first
> succeeded would append every frame a second time, giving the
> skill each step twice. `append_frame` does not dedupe and
> should not: a demonstration really can do the same thing
> twice, and only this knows the difference.

## `AssembleDemonstration.execute`, [line 47](../../../../../../../backend/src/sro/application/observation/demonstrate.py#L47): Comment

Code: `continue`

> One unreadable upload does not lose the demonstration. The
> frames it held are missing from the result, which is visible
> at review, rather than the whole thing failing to seal.
