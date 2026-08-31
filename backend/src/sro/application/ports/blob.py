"""Object storage for capture artifacts."""

from __future__ import annotations

from collections.abc import Mapping
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

    async def list_prefix(self, prefix: str) -> Mapping[str, int]:
        """Every URI stored under a key prefix, and how big each one is.

        The read half of ``forget_prefix``. A batch's screenshots have no row
        of their own -- `StoreObservationArtifact` keys them by
        tenant/principal/day/batch instead -- so asking the store is the only
        way to learn which gestures were photographed. Sizes ride along
        because the listing already carries them and an artifact has to record
        one.

        URIs rather than keys, so no caller has to construct one the way only
        the store knows how.
        """
        ...

    async def forget_prefix(self, prefix: str) -> int:
        """Delete everything stored under a key prefix, and say how much went.
        Idempotent, like ``forget``.

        The count is the operator's receipt. "Your evidence is deleted" is a
        promise, and a promise about pictures of somebody's screen is worth
        stating as a number they can check.

        A batch's screenshots have no row of their own to hold a URI --
        `StoreObservationArtifact` keys them by tenant/principal/day/batch
        instead, exactly so a purge can find every frame of one batch without
        having recorded each one. This is the other half of that trade.
        """
        ...
