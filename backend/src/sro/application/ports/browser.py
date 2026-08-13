"""The browser a demonstration happens in. Backed by Steel; see docs/07-adr/003-steel.md."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sro.domain.shared.identifiers import BrowserSessionId


@dataclass(frozen=True, slots=True)
class BrowserSession:
    id: BrowserSessionId
    live_view_url: str
    """Where a human points their browser to drive this session."""

    debugger_url: str
    """CDP endpoint for the capture adapter. Never sent to a client."""


class BrowserProvider(Protocol):
    async def open(self, *, start_url: str | None = None) -> BrowserSession: ...

    async def close(self, session_id: BrowserSessionId) -> None:
        """Idempotent -- crash recovery calls this on sessions already gone."""
        ...

    async def live_view_url(self, session_id: BrowserSessionId) -> str | None:
        """Where a human drives this session, asked for after the fact.

        The URL is not stored on the recording: it belongs to the provider, and
        a session that has ended has no live view. ``None`` says exactly that.
        """
        ...


class BrowserUnavailable(Exception):
    """Provider is down. Not a ``DomainError``: the request was fine, we are not."""
