# Notes for `backend/src/sro/domain/recording/narration.py`

Comments and docstrings moved out of [`backend/src/sro/domain/recording/narration.py`](../../../../../../../backend/src/sro/domain/recording/narration.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/recording/narration.py#L1): Docstring

> What the operator said while they worked, on the same clock as the frames.

## `NarrationSegment`, [line 10](../../../../../../../backend/src/sro/domain/recording/narration.py#L10): Docstring

> One utterance, placed in absolute time.
>
> Absolute rather than an offset into the audio: a segment is only useful once
> it can be lined up against the action frames, and the audio's own clock
> starts whenever the microphone did.

## `NarrationSegment.overlaps`, [line 23](../../../../../../../backend/src/sro/domain/recording/narration.py#L23): Docstring

> Whether this was said during a window, the last of which is open.
>
> Half-open at both ends: an utterance that finishes exactly as the next
> action begins belongs to the action it was describing, not to the one
> that had not happened yet. Closed-ended, every sentence spoken at a step
> boundary landed on two steps.
