# Notes for `backend/src/sro/application/recording/attach_artifact.py`

Comments and docstrings moved out of [`backend/src/sro/application/recording/attach_artifact.py`](../../../../../../../backend/src/sro/application/recording/attach_artifact.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/recording/attach_artifact.py#L1): Docstring

> Store a capture artifact and attach it to the recording.

## `_place`, [line 18](../../../../../../../backend/src/sro/application/recording/attach_artifact.py#L18): Docstring

> Offsets into the audio become points on the recording's clock.

## `artifact_key`, [line 31](../../../../../../../backend/src/sro/application/recording/attach_artifact.py#L31): Docstring

> Object-store key. Tenant-first so bucket policies can scope per tenant.

## `AttachArtifact.execute`, [line 57](../../../../../../../backend/src/sro/application/recording/attach_artifact.py#L57): Docstring

> ``recorded_from`` is when the microphone started, which is the only
> thing that turns a transcript's offsets into times a frame can be
> matched against.

## `AttachArtifact.record_stored_blob`, [line 126](../../../../../../../backend/src/sro/application/recording/attach_artifact.py#L126): Docstring

> Attach a blob the capture adapter already wrote.
>
> Screenshots and oversized payloads are stored as they are captured --
> holding them in memory until the recording ends would defeat the point.
> This records their existence without moving the bytes again.
