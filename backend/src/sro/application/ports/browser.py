from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

from sro.domain.shared.identifiers import BrowserSessionId


@dataclass(frozen=True, slots=True)
class BrowserSession:
    id: BrowserSessionId
    live_view_url: str

    debugger_url: str


class BrowserProvider(Protocol):
    async def open(self, *, start_url: str | None = None) -> BrowserSession: ...

    async def close(self, session_id: BrowserSessionId) -> None: ...

    async def navigate(self, session_id: BrowserSessionId, url: str) -> None: ...

    async def session_cookies(
        self, session_id: BrowserSessionId
    ) -> tuple[dict[str, object], ...]: ...

    async def forget_everything(self, session_id: BrowserSessionId) -> None: ...

    async def restore(
        self, session_id: BrowserSessionId, cookies: list[dict[str, object]]
    ) -> None: ...

    async def session_headers(self, session_id: BrowserSessionId, url: str) -> dict[str, str]: ...

    async def live_sessions(self) -> tuple[BrowserSessionId, ...]: ...

    async def debugger_url(self, session_id: BrowserSessionId) -> str: ...

    async def live_view_url(self, session_id: BrowserSessionId) -> str | None: ...

    def frames(self, session_id: BrowserSessionId) -> AsyncIterator[bytes]: ...


class BrowserUnavailable(Exception):
    code = "browser_unavailable"
