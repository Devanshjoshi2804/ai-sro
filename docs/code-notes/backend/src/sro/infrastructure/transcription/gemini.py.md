# Notes for `backend/src/sro/infrastructure/transcription/gemini.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/transcription/gemini.py`](../../../../../../../backend/src/sro/infrastructure/transcription/gemini.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/transcription/gemini.py#L1): Docstring

> Narration to timed segments, through Gemini.
>
> The audio leaves the deployment, so this adapter is bound only when a key is
> configured and transcription is switched on. See docs/12-execution-and-agents.md
> on egress: capture stays in the customer's infrastructure, sending does not.

## `GeminiTranscriber`, [line 14](../../../../../../../backend/src/sro/infrastructure/transcription/gemini.py#L14): Docstring

> Asks through `sro.application.shared.asking.ask`, with the audio as
> `(bytes, mime type)`, so a failure on 3.8-flash is heard once more on
> 3.7-flash and the segments are checked against `TRANSCRIBE`'s schema.
>
> The SDK is still not imported at module scope: `GeminiAsker` imports it
> inside the call. A deployment that never sends anything to a hosted model
> should not load a hosted model's client to boot, and the composition root
> imports this module either way.

## `GeminiTranscriber.transcribe`, [line 31](../../../../../../../backend/src/sro/infrastructure/transcription/gemini.py#L31): Note on the block below

Code: `if answer.data is None:`

> Model output is data crossing a trust boundary; a bad shape is silence --
> `Answer.malformed` is how the caller tells the two `data is None` cases
> apart. `ask`'s schema check sets it when a model answered but the shape
> broke `TRANSCRIBE`'s schema (GC 10): that stays silence, since a
> demonstration is still perfectly usable without narration and a malformed
> response must not fail the upload the operator is waiting on.
>
> A call that failed on both models -- neither model produced anything to
> check against the schema -- is a different failure and is not silence: it
> raises, so an outage on both flash models is never read as "nobody said
> anything."
