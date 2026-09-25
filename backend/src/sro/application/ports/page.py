from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from sro.domain.execution.lanes import SeenCall
from sro.domain.observation.gesture import AfterState
from sro.domain.skill.signing_in import PageSignals


@dataclass(frozen=True, slots=True)
class SessionRef:
    context_id: str
    cdp_url: str


@dataclass(frozen=True, slots=True)
class PageAnswer:
    ok: bool
    matched_by: str | None = None
    candidates: int = 0
    detail: str = ""
    error_kind: str | None = None
    state: AfterState | None = None
    pin: str | None = None
    repaired: bool = False


class PageGone(Exception):
    code = "page_gone"


class PageUnsettled(Exception):
    code = "page_unsettled"


class PageDriver(Protocol):
    async def act(
        self, session: SessionRef, target_id: str, payload: Mapping[str, object]
    ) -> PageAnswer: ...

    async def mark(self, session: SessionRef, target_id: str) -> int: ...

    async def calls_since(
        self, session: SessionRef, target_id: str, mark: int
    ) -> tuple[SeenCall, ...]: ...

    async def wait_for_call(
        self,
        session: SessionRef,
        target_id: str,
        *,
        method: str,
        shape: str,
        since: int,
        deadline_s: float,
    ) -> bool: ...

    async def wait_for(
        self, session: SessionRef, target_id: str, payload: Mapping[str, object], deadline_s: float
    ) -> bool: ...

    async def signals(self, session: SessionRef, target_id: str) -> PageSignals: ...

    async def open_tab(self, session: SessionRef, url: str) -> str: ...

    async def close_tab(self, session: SessionRef, target_id: str) -> None: ...

    async def goto(self, session: SessionRef, target_id: str, url: str) -> None: ...

    async def url_of(self, session: SessionRef, target_id: str) -> str: ...

    async def storage_state(self, session: SessionRef) -> str: ...

    async def restore_state(self, session: SessionRef, state: str) -> None: ...

    async def forget(self, session: SessionRef) -> None: ...

    async def aclose(self) -> None: ...
