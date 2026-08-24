"""Object storage for capture artifacts."""

from __future__ import annotations

from datetime import timedelta
from typing import Protocol


class BlobStore(Protocol):
    async def put(self, key: str, data: bytes, *, content_type: str) -> str:
        """Store bytes, return the URI to record on the artifact."""
        ...

    async def presigned_url(self, key: str, *, expires_in: timedelta) -> str:
        """Time-limited read URL, so large media never streams through the API."""
        ...

    async def presigned_url_for_uri(self, uri: str, *, expires_in: timedelta) -> str | None:
        """The same, addressed by the URI stored on an artifact.

        The store wrote the URI, so the store parses it. ``None`` when the URI
        belongs to somewhere else entirely -- a recording imported from another
        deployment, say.
        """
        ...

    async def read(self, uri: str) -> bytes:
        """The bytes back. Used by anything that derives a view from evidence
        rather than serving it to a browser -- the miner reads a day of
        observation this way rather than through a presigned URL it would then
        have to fetch over the network to reach itself."""
        ...

    async def forget(self, uri: str) -> None:
        """Delete what a URI addresses. Idempotent -- deleting what is not there
        is success, because a purge that fails halfway must be safe to repeat.

        A URI from somewhere else is left alone rather than guessed at.
        """
        ...

    async def forget_prefix(self, prefix: str) -> None:
        """Delete everything stored under a key prefix. Idempotent, like
        ``forget``.

        A batch's screenshots have no row of their own to hold a URI --
        `StoreObservationArtifact` keys them by tenant/principal/day/batch
        instead, exactly so a purge can find every frame of one batch without
        having recorded each one. This is the other half of that trade.
        """
        ...
