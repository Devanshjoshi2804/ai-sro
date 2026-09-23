# Notes for `backend/src/sro/domain/recording/artifact.py`

Comments and docstrings moved out of [`backend/src/sro/domain/recording/artifact.py`](../../../../../../../backend/src/sro/domain/recording/artifact.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/recording/artifact.py#L1): Docstring

> Capture outputs stored as blobs rather than rows.

## `ArtifactKind`, [line 11](../../../../../../../backend/src/sro/domain/recording/artifact.py#L11): Note on the line above

Code: `RAW_EVENTS = "raw_events"`

> Unabridged CDP stream. Frames are re-derivable from this without re-recording.

## `ArtifactKind`, [line 14](../../../../../../../backend/src/sro/domain/recording/artifact.py#L14): Note on the line above

Code: `SCREENSHOT = "screenshot"`

> Still capture. One per action frame, plus any taken on demand.

## `ArtifactKind`, [line 18](../../../../../../../backend/src/sro/domain/recording/artifact.py#L18): Note on the line above

Code: `PAYLOAD = "payload"`

> A request or response body too large to store inline.

## `MediaArtifact`, [line 30](../../../../../../../backend/src/sro/domain/recording/artifact.py#L30): Note on the line above

Code: `frame_index: int | None = None`

> Set when the artifact belongs to one action frame -- a screenshot, or a
> payload blob referenced by a captured request.
