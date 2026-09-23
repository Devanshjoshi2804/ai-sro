# Notes for `backend/src/sro/application/ports/transcription.py`

Comments and docstrings moved out of [`backend/src/sro/application/ports/transcription.py`](../../../../../../../backend/src/sro/application/ports/transcription.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/ports/transcription.py#L1): Docstring

> Optional narration transcription. Default binding is ``NullTranscriber``.

## `TranscribedSegment`, [line 10](../../../../../../../backend/src/sro/application/ports/transcription.py#L10): Docstring

> One utterance, as offsets into the audio.
>
> Offsets rather than timestamps because a transcriber knows only the file it
> was given; the caller owns the clock the microphone started on.

## `Transcriber.available`, [line 22](../../../../../../../backend/src/sro/application/ports/transcription.py#L22): Docstring

> Whether a backend is configured. Absence is a normal deployment,
> so callers branch on this rather than catching.

## `Transcriber.transcribe`, [line 24](../../../../../../../backend/src/sro/application/ports/transcription.py#L24): Docstring

> Timed segments, in any order. An empty result is a silent recording,
> not a failure.
