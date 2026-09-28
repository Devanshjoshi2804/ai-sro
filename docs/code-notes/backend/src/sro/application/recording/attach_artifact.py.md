# Notes for `backend/src/sro/application/recording/attach_artifact.py`

Comments and docstrings moved out of [`backend/src/sro/application/recording/attach_artifact.py`](../../../../../../../backend/src/sro/application/recording/attach_artifact.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/recording/attach_artifact.py#L1): Docstring

> Store a capture artifact and attach it to the recording.

## `_place`, [line 21](../../../../../../../backend/src/sro/application/recording/attach_artifact.py#L21): Docstring

> Offsets into the audio become points on the recording's clock.

## `artifact_key`, [line 34](../../../../../../../backend/src/sro/application/recording/attach_artifact.py#L34): Docstring

> Object-store key. Tenant-first so bucket policies can scope per tenant.

## `AttachArtifact.execute`, [line 60](../../../../../../../backend/src/sro/application/recording/attach_artifact.py#L60): Docstring

> ``recorded_from`` is when the microphone started, which is the only
> thing that turns a transcript's offsets into times a frame can be
> matched against.

## `AttachArtifact.execute`, [line 91](../../../../../../../backend/src/sro/application/recording/attach_artifact.py#L91): Note on the block below

Code: `try:`

> A transcription that yields nothing usable is logged and leaves the
> recording with its audio and no transcript. The audio blob is already
> written above, so letting the raise through would lose the artifact the
> operator just uploaded; attaching an empty transcript would claim silence.

## `AttachArtifact.record_stored_blob`, [line 134](../../../../../../../backend/src/sro/application/recording/attach_artifact.py#L134): Docstring

> Attach a blob the capture adapter already wrote.
>
> Screenshots and oversized payloads are stored as they are captured --
> holding them in memory until the recording ends would defeat the point.
> This records their existence without moving the bytes again.
