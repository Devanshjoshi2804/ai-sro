from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SessionRef:
    steel_session_id: str
    cdp_url: str


class PageGone(Exception):
    code = "page_gone"


class PageDriver(Protocol):
    async def open_tab(self, session: SessionRef, url: str) -> str: ...

    async def close_tab(self, session: SessionRef, target_id: str) -> None: ...

    async def goto(self, session: SessionRef, target_id: str, url: str) -> None: ...

    async def url_of(self, session: SessionRef, target_id: str) -> str: ...

    async def storage_state(self, session: SessionRef) -> str: ...

    async def restore_state(self, session: SessionRef, state: str) -> None: ...

    async def forget(self, session: SessionRef) -> None: ...
