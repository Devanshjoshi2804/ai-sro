"""The browser a demonstration happens in. Backed by Steel; see docs/07-adr/003-steel.md."""

from __future__ import annotations

from collections.abc import AsyncIterator
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

    async def navigate(self, session_id: BrowserSessionId, url: str) -> None:
        """Put the session on a page.

        Steel accepts a start URL when a session is created and does not act on
        it, so opening a browser "at" somewhere is two steps rather than one.
        """
        ...

    async def session_cookies(self, session_id: BrowserSessionId) -> tuple[dict[str, object], ...]:
        """Every cookie the session holds.

        The only place cookie values are read on purpose. They are a bearer
        credential, so the caller puts them in the vault and nowhere else.
        """
        ...

    async def forget_everything(self, session_id: BrowserSessionId) -> None:
        """Empty this browser of whoever used it last.

        Not a nicety. A provider that keeps one browser keeps one cookie jar, so
        a session opened for a second tenant arrived already signed in as the
        first -- the system under test said so, and the connect flow stored that
        session under the new tenant's name. Nobody typed a password and one
        tenant ended up holding another's warehouse session.
        """
        ...

    async def restore(self, session_id: BrowserSessionId, cookies: list[dict[str, object]]) -> None:
        """Put a stored session into a fresh browser, before it navigates.

        A browser sent to the application with nothing in it lands on a login
        page, and everything read from that page belongs to nobody.
        """
        ...

    async def session_headers(self, session_id: BrowserSessionId, url: str) -> dict[str, str]:
        """The headers this session's own application sends, beyond its cookies.

        Some systems authenticate a call with more than a cookie -- Blue Yonder
        signs every request with a ``CSRF-ENCRYPT-TOKEN`` issued at login, held
        in the page rather than in a cookie or in storage. Without it the
        executor is refused while the browser beside it is signed in, which is
        the state a run cannot diagnose for itself.

        Observed from a request the application makes on its own, because that
        is the only place the value appears. Returns only the headers that
        authenticate; nothing about the transport, and never the cookie, which
        is kept separately and refreshed on its own schedule.
        """
        ...

    async def live_sessions(self) -> tuple[BrowserSessionId, ...]:
        """Browsers this deployment has open right now.

        So a login somebody completed in one of them is not lost because
        nothing happened to be watching that window."""
        ...

    async def debugger_url(self, session_id: BrowserSessionId) -> str:
        """Where to attach to this particular browser."""
        ...

    async def live_view_url(self, session_id: BrowserSessionId) -> str | None:
        """Where a human drives this session, asked for after the fact.

        The URL is not stored on the recording: it belongs to the provider, and
        a session that has ended has no live view. ``None`` says exactly that.
        """
        ...

    def frames(self, session_id: BrowserSessionId) -> AsyncIterator[bytes]:
        """This session's screen, as JPEG frames, for as long as it is read.

        Separate from ``live_view_url`` because a provider's own viewer is a web
        page we do not control: self-hosted Steel hands out one URL for the whole
        deployment with no session in it, which shows the wrong browser or none.
        Frames are the same picture with the provider's product taken out of it.
        """
        ...


class BrowserUnavailable(Exception):
    """Provider is down. Not a ``DomainError``: the request was fine, we are not."""

    code = "browser_unavailable"
