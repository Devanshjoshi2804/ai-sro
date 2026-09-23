from __future__ import annotations

from dataclasses import dataclass

from sro.application.ports.browser import BrowserProvider, BrowserUnavailable


@dataclass(frozen=True, slots=True)
class OpenBrowser:
    session_id: str
    live_view_url: str | None


class WatchBrowsers:
    def __init__(self, browser: BrowserProvider) -> None:
        self._browser = browser

    async def all_in_deployment(self) -> tuple[OpenBrowser, ...]:
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
