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
