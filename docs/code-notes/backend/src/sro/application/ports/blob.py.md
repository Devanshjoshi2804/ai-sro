# Notes for `backend/src/sro/application/ports/blob.py`

Comments and docstrings moved out of [`backend/src/sro/application/ports/blob.py`](../../../../../../../backend/src/sro/application/ports/blob.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/ports/blob.py#L1): Docstring

> Object storage for capture artifacts.

## `BlobStore.put`, [line 9](../../../../../../../backend/src/sro/application/ports/blob.py#L9): Docstring

> Store bytes, return the URI to record on the artifact.

## `BlobStore.presigned_url`, [line 11](../../../../../../../backend/src/sro/application/ports/blob.py#L11): Docstring

> Time-limited read URL, so large media never streams through the API.

## `BlobStore.presigned_url_for_uri`, [line 13](../../../../../../../backend/src/sro/application/ports/blob.py#L13): Docstring

> The same, addressed by the URI stored on an artifact.
>
> The store wrote the URI, so the store parses it. ``None`` when the URI
> belongs to somewhere else entirely -- a recording imported from another
> deployment, say.

## `BlobStore.read`, [line 15](../../../../../../../backend/src/sro/application/ports/blob.py#L15): Docstring

> The bytes back. Used by anything that derives a view from evidence
> rather than serving it to a browser -- the miner reads a day of
> observation this way rather than through a presigned URL it would then
> have to fetch over the network to reach itself.

## `BlobStore.forget`, [line 17](../../../../../../../backend/src/sro/application/ports/blob.py#L17): Docstring

> Delete what a URI addresses. Idempotent -- deleting what is not there
> is success, because a purge that fails halfway must be safe to repeat.
>
> A URI from somewhere else is left alone rather than guessed at.

## `BlobStore.list_prefix`, [line 19](../../../../../../../backend/src/sro/application/ports/blob.py#L19): Docstring

> Every URI stored under a key prefix, and how big each one is.
>
> The read half of ``forget_prefix``. A batch's screenshots have no row
> of their own -- `StoreObservationArtifact` keys them by
> tenant/principal/day/batch instead -- so asking the store is the only
> way to learn which gestures were photographed. Sizes ride along
> because the listing already carries them and an artifact has to record
> one.
>
> URIs rather than keys, so no caller has to construct one the way only
> the store knows how.

## `BlobStore.forget_prefix`, [line 21](../../../../../../../backend/src/sro/application/ports/blob.py#L21): Docstring

> Delete everything stored under a key prefix, and say how much went.
> Idempotent, like ``forget``.
>
> The count is the operator's receipt. "Your evidence is deleted" is a
> promise, and a promise about pictures of somebody's screen is worth
> stating as a number they can check.
>
> A batch's screenshots have no row of their own to hold a URI --
> `StoreObservationArtifact` keys them by tenant/principal/day/batch
> instead, exactly so a purge can find every frame of one batch without
> having recorded each one. This is the other half of that trade.
