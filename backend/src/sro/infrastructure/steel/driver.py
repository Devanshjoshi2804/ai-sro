from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar
from urllib.parse import urlsplit

import httpx
from playwright.async_api import Browser, CDPSession, Page, Playwright, Route, async_playwright
from playwright.async_api import Error as PlaywrightError

from sro.application.ports.page import PageGone, SessionRef
from sro.infrastructure.steel.capture import addressed
from sro.infrastructure.steel.client import cdp_origin, websocket_debugger_url

K_ATTACH_TIMEOUT_S = 10
K_ACTION_TIMEOUT_S = 15

_SEED_STORAGE = """(items) => {
  for (const { name, value } of items) {
    if (localStorage.getItem(name) === null) localStorage.setItem(name, value);
  }
}"""

T = TypeVar("T")


@dataclass
class _Link:
    cdp_url: str
    authority: str
    browser: Browser
    raw: CDPSession
    pages: dict[str, Page] = field(default_factory=dict)
    owners: dict[str, str] = field(default_factory=dict)
    waiting: dict[str, asyncio.Future[Page]] = field(default_factory=dict)


class SteelDriver:
    def __init__(self, page_code_path: str) -> None:
        self._page_code = Path(page_code_path).read_text(encoding="utf-8")
        self._playwright: Playwright | None = None
        self._locks: dict[str, asyncio.Lock] = {}
        self._locks_guard = asyncio.Lock()
        self._links: dict[str, _Link] = {}
        self._listeners: dict[tuple[str, str], list[tuple[str, Callable[..., Any]]]] = {}

    async def _lock_for(self, cdp_url: str) -> asyncio.Lock:
        async with self._locks_guard:
            found = self._locks.get(cdp_url)
            if found is None:
                found = self._locks[cdp_url] = asyncio.Lock()
            return found

    async def _link(self, cdp_url: str) -> _Link:
        lock = await self._lock_for(cdp_url)
        async with lock:
            link = self._links.get(cdp_url)
            if link is not None and link.browser.is_connected():
                return link
            self._links.pop(cdp_url, None)
            if self._playwright is None:
                self._playwright = await async_playwright().start()
            try:
                async with httpx.AsyncClient(timeout=K_ATTACH_TIMEOUT_S) as client:
                    authority = await cdp_origin(cdp_url)
                    endpoint = await websocket_debugger_url(cdp_url, client)
                browser = await self._playwright.chromium.connect_over_cdp(
                    endpoint, timeout=K_ATTACH_TIMEOUT_S * 1000
                )
                link = _Link(cdp_url, authority, browser, await browser.new_browser_cdp_session())
            except (httpx.HTTPError, PlaywrightError) as why:
                raise PageGone(f"could not attach to the browser at {cdp_url}: {why}") from why
            for stale_url, stale in list(self._links.items()):
                if stale_url != cdp_url and stale.authority == authority:
                    del self._links[stale_url]
                    self._locks.pop(stale_url, None)
                    with contextlib.suppress(PlaywrightError):
                        await stale.browser.close()
            context = browser.contexts[0]
            already = list(context.pages)
            context.on("page", lambda page: self._arrived(link, page))
            for page in already:
                await self._arrived(link, page)
            self._links[cdp_url] = link
            return link

    async def _arrived(self, link: _Link, page: Page) -> None:
        try:
            cdp = await page.context.new_cdp_session(page)
            try:
                info = (await cdp.send("Target.getTargetInfo"))["targetInfo"]
            finally:
                await cdp.detach()
        except PlaywrightError:
            return
        target_id, owner = str(info["targetId"]), str(info.get("browserContextId", ""))

        def gone(_: Page) -> None:
            link.pages.pop(target_id, None)
            link.owners.pop(target_id, None)

        page.once("close", gone)
        link.owners[target_id] = owner
        for event, handler in self._listeners.get((link.cdp_url, owner), []):
            page.on(event, handler)  # type: ignore[call-overload]

        try:
            await page.add_init_script(script=self._page_code)
            for frame in page.frames:
                with contextlib.suppress(PlaywrightError):
                    await frame.evaluate(self._page_code)
        except PlaywrightError:
            link.owners.pop(target_id, None)
            return

        link.pages[target_id] = page
        waiter = link.waiting.pop(target_id, None)
        if waiter is not None and not waiter.done():
            waiter.set_result(page)

    async def _send(self, link: _Link, method: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            return await link.raw.send(method, params)
        except PlaywrightError as why:
            raise PageGone(f"{method} failed: {why}") from why

    async def _context(self, session: SessionRef) -> _Link:
        link = await self._link(session.cdp_url)
        found = await self._send(link, "Target.getBrowserContexts", {})
        if session.context_id not in found["browserContextIds"]:
            raise PageGone(f"context {session.context_id} is not open in this browser")
        return link

    async def _page(self, session: SessionRef, target_id: str) -> Page:
        link = await self._context(session)
        page = link.pages.get(target_id)
        if page is None or page.is_closed() or link.owners.get(target_id) != session.context_id:
            raise PageGone(f"tab {target_id} is not open in context {session.context_id}")
        return page

    async def _target_alive(self, session: SessionRef, target_id: str) -> bool:
        link = self._links.get(session.cdp_url)
        if link is None:
            return False
        try:
            await self._send(link, "Target.getTargetInfo", {"targetId": target_id})
        except PageGone:
            return False
        return True

    async def _call(
        self, session: SessionRef, target_id: str, page: Page, action: Callable[[], Awaitable[T]]
    ) -> T:
        try:
            return await action()
        except PlaywrightError as why:
            if page.is_closed() or not await self._target_alive(session, target_id):
                raise PageGone(
                    f"tab {target_id} in context {session.context_id} is gone: {why}"
                ) from why
            raise

    async def open_tab(self, session: SessionRef, url: str) -> str:
        link = await self._context(session)
        made = await self._send(
            link,
            "Target.createTarget",
            {"url": "about:blank", "browserContextId": session.context_id},
        )
        target_id = str(made["targetId"])
        page = link.pages.get(target_id)
        if page is None:
            waiter: asyncio.Future[Page] = asyncio.get_running_loop().create_future()
            link.waiting[target_id] = waiter
            try:
                page = await asyncio.wait_for(waiter, K_ATTACH_TIMEOUT_S)
            except TimeoutError:
                link.waiting.pop(target_id, None)
                with contextlib.suppress(PageGone):
                    await self._send(link, "Target.closeTarget", {"targetId": target_id})
                raise PageGone(
                    f"tab {target_id} did not attach within {K_ATTACH_TIMEOUT_S} s"
                ) from None
        try:
            await self._call(
                session,
                target_id,
                page,
                lambda: page.goto(
                    url, wait_until="domcontentloaded", timeout=K_ACTION_TIMEOUT_S * 1000
                ),
            )
        except PageGone:
            with contextlib.suppress(PageGone):
                await self._send(link, "Target.closeTarget", {"targetId": target_id})
            raise
        return target_id

    async def close_tab(self, session: SessionRef, target_id: str) -> None:
        page = await self._page(session, target_id)
        await self._call(session, target_id, page, page.close)

    async def goto(self, session: SessionRef, target_id: str, url: str) -> None:
        page = await self._page(session, target_id)
        await self._call(
            session,
            target_id,
            page,
            lambda: page.goto(
                url, wait_until="domcontentloaded", timeout=K_ACTION_TIMEOUT_S * 1000
            ),
        )

    async def url_of(self, session: SessionRef, target_id: str) -> str:
        return (await self._page(session, target_id)).url

    async def evaluate(self, session: SessionRef, target_id: str, expression: str) -> object:
        page = await self._page(session, target_id)
        return await self._call(session, target_id, page, lambda: page.evaluate(expression))

    async def on(self, session: SessionRef, event: str, handler: Callable[..., Any]) -> None:
        link = await self._context(session)
        key = (session.cdp_url, session.context_id)
        self._listeners.setdefault(key, []).append((event, handler))
        for target_id, page in list(link.pages.items()):
            if link.owners.get(target_id) == session.context_id:
                page.on(event, handler)  # type: ignore[call-overload]

    async def storage_state(self, session: SessionRef) -> str:
        link = await self._context(session)
        found = await self._send(
            link, "Storage.getCookies", {"browserContextId": session.context_id}
        )

        origins: dict[str, list[dict[str, str]]] = {}
        for target_id, page in list(link.pages.items()):
            if link.owners.get(target_id) != session.context_id:
                continue
            try:
                items = await page.evaluate("Object.entries(localStorage)")
            except PlaywrightError:
                continue
            if items:
                parts = urlsplit(page.url)
                origins[f"{parts.scheme}://{parts.netloc}"] = [
                    {"name": name, "value": value} for name, value in items
                ]

        return json.dumps(
            {
                "cookies": found["cookies"],
                "origins": [
                    {"origin": origin, "localStorage": items} for origin, items in origins.items()
                ],
            }
        )

    async def restore_state(self, session: SessionRef, state: str) -> None:
        saved = json.loads(state)
        link = await self._context(session)
        if cookies := [addressed(c) for c in saved.get("cookies", [])]:
            await self._send(
                link,
                "Storage.setCookies",
                {"cookies": cookies, "browserContextId": session.context_id},
            )

        kept = [one for one in saved.get("origins", []) if one.get("localStorage")]
        if not kept:
            return
        target_id = await self.open_tab(session, "about:blank")
        page = link.pages[target_id]

        async def blank(route: Route) -> None:
            await route.fulfill(body="<html></html>", content_type="text/html")

        try:
            await page.route("**/*", blank)
            for one in kept:
                await page.goto(one["origin"], wait_until="domcontentloaded")
                await page.evaluate(_SEED_STORAGE, one["localStorage"])
        except PlaywrightError as why:
            raise PageGone(f"could not restore storage in {session.context_id}: {why}") from why
        finally:
            with contextlib.suppress(PlaywrightError):
                await page.close()

    async def forget(self, session: SessionRef) -> None:
        key = (session.cdp_url, session.context_id)
        handlers = self._listeners.pop(key, [])
        link = self._links.get(session.cdp_url)
        if link is None or not handlers:
            return
        for event, handler in handlers:
            for target_id, page in list(link.pages.items()):
                if link.owners.get(target_id) == session.context_id:
                    page.remove_listener(event, handler)

    async def aclose(self) -> None:
        links, self._links = self._links, {}
        for link in links.values():
            with contextlib.suppress(PlaywrightError):
                await link.browser.close()
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None
