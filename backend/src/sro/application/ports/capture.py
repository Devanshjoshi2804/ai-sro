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
        self,
        ctx: RequestContext,
        *,
        recording_id: RecordingId,
        debugger_url: str,
        start_url: str | None = None,
        session_cookies: tuple[dict[str, object], ...] = (),
    ) -> None: ...

    async def stop(self, ctx: RequestContext, *, recording_id: RecordingId) -> None:
        """Flush what is buffered, then release the session. Idempotent."""
        ...

    async def snapshot_cookies(self, recording_id: RecordingId) -> list[dict[str, object]]:
        """The live session's cookies, for the vault.

        On this port rather than the browser one because only the capture
        session holds an attached CDP connection to read them through.
        """
        ...

    async def stop_all(self) -> None:
        """Shutdown. Sessions outlive requests, so something has to end them."""
        ...
