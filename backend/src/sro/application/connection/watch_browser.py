"""Where to watch, when this system is driving a browser.

The system signs itself in, replays a screen and pursues a goal in a browser
nobody can see. That is the right default for something running at 3am and the
wrong one for a person waiting: "it did not finish" is a sentence, and a window
they can watch is evidence. Every provider we use has a live view already --
this only says which sessions are open and where to look at them.
"""

from __future__ import annotations

from dataclasses import dataclass

from sro.application.ports.browser import BrowserProvider, BrowserUnavailable


@dataclass(frozen=True, slots=True)
class OpenBrowser:
    session_id: str
    live_view_url: str | None
    """``None`` when the provider has no viewer for it. Still worth reporting:
    a session nobody can watch is still a session holding the only slot."""


class WatchBrowsers:
    def __init__(self, browser: BrowserProvider) -> None:
        self._browser = browser

    async def execute(self) -> tuple[OpenBrowser, ...]:
        """Every browser open right now. Empty when the provider is down --
        which is a fact about the provider, not something to raise over."""
        try:
            sessions = await self._browser.live_sessions()
        except BrowserUnavailable:
            return ()

        watching: list[OpenBrowser] = []
        for session_id in sessions:
            try:
                url = await self._browser.live_view_url(session_id)
            except BrowserUnavailable:
                url = None
            watching.append(OpenBrowser(session_id=str(session_id), live_view_url=url))
        return tuple(watching)
