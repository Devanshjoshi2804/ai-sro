# Notes for `backend/src/sro/infrastructure/transcription/gemini.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/transcription/gemini.py`](../../../../../../../backend/src/sro/infrastructure/transcription/gemini.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/transcription/gemini.py#L1): Docstring

> Narration to timed segments, through Gemini.
>
> The audio leaves the deployment, so this adapter is bound only when a key is
> configured and transcription is switched on. See docs/12-execution-and-agents.md
> on egress: capture stays in the customer's infrastructure, sending does not.

## `GeminiTranscriber`, [line 36](../../../../../../../backend/src/sro/infrastructure/transcription/gemini.py#L36): Docstring

> The SDK is imported here rather than at module scope.
>
> A deployment that never sends anything to a hosted model should not load a
> hosted model's client to boot, and the composition root imports this module
> either way.

## `_parse`, [line 66](../../../../../../../backend/src/sro/infrastructure/transcription/gemini.py#L66): Docstring

> Model output is data crossing a trust boundary; a bad shape is silence.
>
> A demonstration is still perfectly usable without narration, so a malformed
> response must not fail the upload the operator is waiting on.
