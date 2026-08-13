"""Control of a live capture session.

The session itself is a socket bound to one process, so it cannot be modelled as
a repository or a workflow. What the interface layer needs from it is only this:
start collecting for a recording, and stop collecting for a recording.
"""

from __future__ import annotations

from typing import Protocol

from sro.application.context import RequestContext
from sro.domain.shared.identifiers import RecordingId


class CaptureController(Protocol):
    async def start(
        self, ctx: RequestContext, *, recording_id: RecordingId, debugger_url: str
    ) -> None: ...

    async def stop(self, ctx: RequestContext, *, recording_id: RecordingId) -> None:
        """Flush what is buffered, then release the session. Idempotent."""
        ...

    async def stop_all(self) -> None:
        """Shutdown. Sessions outlive requests, so something has to end them."""
        ...
