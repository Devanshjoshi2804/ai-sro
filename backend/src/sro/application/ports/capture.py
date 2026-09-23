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

    async def stop(self, ctx: RequestContext, *, recording_id: RecordingId) -> None: ...

    async def snapshot_cookies(self, recording_id: RecordingId) -> list[dict[str, object]]: ...

    async def stop_all(self) -> None: ...
