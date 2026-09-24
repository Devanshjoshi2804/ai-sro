from __future__ import annotations

import asyncio
import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.async_api import Browser, BrowserContext, Frame, Page, Playwright, async_playwright
from playwright.async_api import Error as PlaywrightError

from sro.application.ports.page import PageGone, SessionRef
from sro.infrastructure.steel.capture import _addressed

K_ATTACH_TIMEOUT_S = 10

_KEEP_STORAGE = """(() => {
  const saved = %s;
  for (const { name, value } of saved[location.origin] || []) {
    if (localStorage.getItem(name) === null) localStorage.setItem(name, value);
  }
})();"""


class SteelDriver:
    def __init__(self, page_code_path: str) -> None:
        self._page_code = Path(page_code_path)
        self._playwright: Playwright | None = None
        self._lock = asyncio.Lock()
        self._browsers: dict[str, Browser] = {}
        self._pages: dict[str, dict[str, Page]] = {}
        self._pending_state: dict[str, str] = {}

    async def _connect(self, cdp_url: str) -> Browser:
        async with self._lock:
            browser = self._browsers.get(cdp_url)
            if browser is not None and browser.is_connected():
                return browser
            if self._playwright is None:
                self._playwright = await async_playwright().start()
            browser = await self._playwright.chromium.connect_over_cdp(cdp_url)
            self._browsers[cdp_url] = browser
            return browser

    async def _default_context(self, browser: Browser) -> BrowserContext:
        return browser.contexts[0] if browser.contexts else await browser.new_context()

    async def _scoped(self, browser: Browser, sid: str) -> str | None:
        raw = await browser.new_browser_cdp_session()
        try:
            context_ids = (await raw.send("Target.getBrowserContexts"))["browserContextIds"]
        finally:
            await raw.detach()
        if not context_ids:
            return None
        if sid not in context_ids:
            raise PageGone(f"context {sid} no longer exists in this container")
        return sid

    async def _target_of(self, page: Page) -> str:
        cdp = await page.context.new_cdp_session(page)
        try:
            info = await cdp.send("Target.getTargetInfo")
        finally:
            await cdp.detach()
        return str(info["targetInfo"]["targetId"])

    async def _install(self, frame: Frame) -> None:
        try:
            await frame.evaluate(self._page_code.read_text(encoding="utf-8"))
        except PlaywrightError:
            return None

    async def _attached(self, context: BrowserContext, target_id: str) -> Page:
        for page in context.pages:
            if not page.is_closed() and await self._target_of(page) == target_id:
                return page
        loop = asyncio.get_running_loop()
        deadline = loop.time() + K_ATTACH_TIMEOUT_S
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise PageGone(f"target {target_id} did not attach in time")
            page = await context.wait_for_event("page", timeout=remaining * 1000)
            if await self._target_of(page) == target_id:
                return page

    async def _page(self, session: SessionRef, target_id: str) -> Page:
        sid = session.steel_session_id
        cached = self._pages.get(sid, {}).get(target_id)
        if cached is not None and not cached.is_closed():
            return cached
        browser = await self._connect(session.cdp_url)
        context = await self._default_context(browser)
        for page in context.pages:
            if not page.is_closed() and await self._target_of(page) == target_id:
                self._pages.setdefault(sid, {})[target_id] = page
                return page
        raise PageGone(f"tab {target_id} is not open in session {sid}")

    async def open_tab(self, session: SessionRef, url: str) -> str:
        sid = session.steel_session_id
        browser = await self._connect(session.cdp_url)
        scoped = await self._scoped(browser, sid)

        raw = await browser.new_browser_cdp_session()
        try:
            payload: dict[str, object] = {"url": "about:blank"}
            if scoped is not None:
                payload["browserContextId"] = scoped
            made = await raw.send("Target.createTarget", payload)
        finally:
            await raw.detach()
        target_id = str(made["targetId"])

        context = await self._default_context(browser)
        page = await self._attached(context, target_id)
        await page.add_init_script(path=str(self._page_code))
        if (pending := self._pending_state.get(sid)) is not None:
            await page.add_init_script(script=pending)
        await self._install(page.main_frame)
        await page.goto(url, wait_until="domcontentloaded")

        self._pages.setdefault(sid, {})[target_id] = page
        return target_id

    async def close_tab(self, session: SessionRef, target_id: str) -> None:
        page = await self._page(session, target_id)
        await page.close()
        self._pages.get(session.steel_session_id, {}).pop(target_id, None)

    async def goto(self, session: SessionRef, target_id: str, url: str) -> None:
        await (await self._page(session, target_id)).goto(url, wait_until="domcontentloaded")

    async def url_of(self, session: SessionRef, target_id: str) -> str:
        return (await self._page(session, target_id)).url

    async def evaluate(self, session: SessionRef, target_id: str, expression: str) -> object:
        return await (await self._page(session, target_id)).evaluate(expression)

    async def storage_state(self, session: SessionRef) -> str:
        sid = session.steel_session_id
        browser = await self._connect(session.cdp_url)
        scoped = await self._scoped(browser, sid)

        raw = await browser.new_browser_cdp_session()
        try:
            payload: dict[str, object] = {"browserContextId": scoped} if scoped is not None else {}
            cookies = (await raw.send("Storage.getCookies", payload))["cookies"]
        finally:
            await raw.detach()

        origins: dict[str, list[dict[str, str]]] = {}
        for page in self._pages.get(sid, {}).values():
            if page.is_closed():
                continue
            try:
                items = await page.evaluate("Object.entries(localStorage)")
            except PlaywrightError:
                continue
            if not items:
                continue
            parts = urlsplit(page.url)
            origins[f"{parts.scheme}://{parts.netloc}"] = [
                {"name": name, "value": value} for name, value in items
            ]

        return json.dumps(
            {
                "cookies": cookies,
                "origins": [
                    {"origin": origin, "localStorage": items} for origin, items in origins.items()
                ],
            }
        )

    async def restore_state(self, session: SessionRef, state: str) -> None:
        saved = json.loads(state)
        sid = session.steel_session_id
        browser = await self._connect(session.cdp_url)
        scoped = await self._scoped(browser, sid)

        cookies = [_addressed(c) for c in saved.get("cookies", [])]
        if cookies:
            raw = await browser.new_browser_cdp_session()
            try:
                payload: dict[str, object] = {"cookies": cookies}
                if scoped is not None:
                    payload["browserContextId"] = scoped
                await raw.send("Storage.setCookies", payload)
            finally:
                await raw.detach()

        kept = {
            one["origin"]: one["localStorage"]
            for one in saved.get("origins", [])
            if one.get("localStorage")
        }
        if kept:
            self._pending_state[sid] = _KEEP_STORAGE % json.dumps(kept)

    async def forget(self, session: SessionRef) -> None:
        sid = session.steel_session_id
        self._pages.pop(sid, None)
        self._pending_state.pop(sid, None)
