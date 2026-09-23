# Notes for `backend/src/sro/application/recording/finish_recording.py`

Comments and docstrings moved out of [`backend/src/sro/application/recording/finish_recording.py`](../../../../../../../backend/src/sro/application/recording/finish_recording.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/recording/finish_recording.py#L1): Docstring

> End a demonstration: sealed if it produced evidence, abandoned if not.

## `UnnamedDemonstration`, [line 16](../../../../../../../backend/src/sro/application/recording/finish_recording.py#L16): Docstring

> Nothing the demonstration did says what task it was.
>
> Recoverable by the operator naming it, so it is a 422 with an instruction
> rather than a failure of capture.

## `FinishRecording.seal`, [line 32](../../../../../../../backend/src/sro/application/recording/finish_recording.py#L32): Docstring

> Seal, naming the task from the evidence unless the caller named it.
>
> A caller-supplied key is for the second run of a pair and for the rare
> demonstration that asked the server nothing; the first run names itself.

## `FinishRecording._finish`, [line 80](../../../../../../../backend/src/sro/application/recording/finish_recording.py#L80): Comment

Code: `with suppress(BrowserUnavailable):`

> Best effort: the recording is already durable, and a provider
> outage must not turn a good demonstration into a failed request.
> The RecordingWorkflow reaper collects anything left behind.
