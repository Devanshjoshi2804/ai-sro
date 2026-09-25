from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar
from urllib.parse import urlsplit

import httpx
from playwright.async_api import (
    Browser,
    CDPSession,
    Frame,
    Page,
    Playwright,
    Request,
    Response,
    Route,
    async_playwright,
)
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from sro.application.ports.page import PageAnswer, PageGone, PageUnsettled, SessionRef
from sro.domain.execution.lanes import SeenCall
from sro.domain.observation.gesture import AfterState
from sro.domain.observation.trim import path_shape
from sro.domain.skill.signing_in import PageSignals, a_navigation
from sro.infrastructure.steel.capture import addressed
from sro.infrastructure.steel.client import cdp_origin, websocket_debugger_url

K_ATTACH_TIMEOUT_S = 10
K_ACTION_TIMEOUT_S = 15
K_CALL_BODY_CHARS = 4096
K_CALL_TYPES = frozenset({"fetch", "xhr"})
K_NO_DOCUMENT = frozenset({204, 205})

_SIGNALS = "() => globalThis.sroPage.signals()"

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


@dataclass
class _Calls:
    count: int = 0
    seen: list[tuple[int, SeenCall]] = field(default_factory=list)
    changed: asyncio.Event = field(default_factory=asyncio.Event)
    reading: set[asyncio.Task[None]] = field(default_factory=set)


@dataclass
class _Tab:
    visited: list[str] | None
    pending: set[Request] = field(default_factory=set)
    settled: asyncio.Event = field(default_factory=asyncio.Event)
    loads: int = 0

    def settle(self) -> None:
        if not self.pending:
            self.settled.set()


class SteelDriver:
    def __init__(self, page_code_path: str) -> None:
        self._page_code = Path(page_code_path).read_text(encoding="utf-8")
        self._playwright: Playwright | None = None
        self._locks: dict[str, asyncio.Lock] = {}
        self._locks_guard = asyncio.Lock()
        self._links: dict[str, _Link] = {}
        self._listeners: dict[tuple[str, str], list[tuple[str, Callable[..., Any]]]] = {}
        self._calls: dict[Page, _Calls] = {}
        self._tabs: dict[Page, _Tab] = {}

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
            context.on("page", lambda page: self._arrived(link, page, whole=True))
            for page in already:
                await self._arrived(link, page, whole=False)
            self._links[cdp_url] = link
            return link

    async def _arrived(self, link: _Link, page: Page, *, whole: bool) -> None:
        try:
            cdp = await page.context.new_cdp_session(page)
            try:
                info = (await cdp.send("Target.getTargetInfo"))["targetInfo"]
            finally:
                await cdp.detach()
        except PlaywrightError:
            return
        target_id, owner = str(info["targetId"]), str(info.get("browserContextId", ""))

        tab = self._tabs[page] = _Tab([] if whole else None)
        tab.settled.set()

        def gone(_: Page) -> None:
            link.pages.pop(target_id, None)
            link.owners.pop(target_id, None)
            self._tabs.pop(page, None)
            tab.pending.clear()
            tab.settled.set()

        page.once("close", gone)
        link.owners[target_id] = owner
        for event, handler in self._listeners.get((link.cdp_url, owner), []):
            page.on(event, handler)  # type: ignore[call-overload]

        def main(request: Request) -> bool:
            return request.is_navigation_request() and request.frame == page.main_frame

        def started(request: Request) -> None:
            if main(request):
                tab.pending.discard(request.redirected_from)
                tab.pending.add(request)
                tab.settled.clear()

        def failed(request: Request) -> None:
            if main(request):
                tab.pending.discard(request)
                tab.settle()

        def navigated(response: Response) -> None:
            if not main(response.request):
                return
            if tab.visited is None:
                tab.visited = []
            tab.visited.append(a_navigation(response.url))
            if response.status in K_NO_DOCUMENT:
                failed(response.request)

        def loaded(_: object) -> None:
            tab.loads += 1
            tab.pending.clear()
            tab.settle()

        page.on("request", started)
        page.on("requestfailed", failed)
        page.on("response", navigated)
        page.on("domcontentloaded", loaded)
        page.on("download", loaded)

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
        except TimeoutError as why:
            if page.is_closed() or not await self._target_alive(session, target_id):
                raise PageGone(
                    f"tab {target_id} in context {session.context_id} is gone: {why}"
                ) from why
            raise PageUnsettled(
                f"tab {target_id} in context {session.context_id} did not settle: {why}"
            ) from why

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

    async def signals(self, session: SessionRef, target_id: str) -> PageSignals:
        page = await self._page(session, target_id)
        tab = self._tabs.get(page)

        async def settled_read() -> dict[str, Any]:
            while True:
                if tab is not None:
                    await tab.settled.wait()
                loads = tab.loads if tab is not None else 0
                try:
                    return dict(await page.main_frame.evaluate(_SIGNALS))
                except PlaywrightError:
                    if tab is None or (tab.loads == loads and tab.settled.is_set()):
                        raise

        async def gather() -> tuple[bool, set[str]]:
            async with asyncio.timeout(K_ACTION_TIMEOUT_S):
                got = await settled_read()
            password = bool(got.get("password"))
            autocomplete = set(got.get("autocomplete") or [])
            for frame in page.frames:
                if frame == page.main_frame:
                    continue
                with contextlib.suppress(PlaywrightError):
                    child = await frame.evaluate(_SIGNALS)
                    password = password or bool(child.get("password"))
                    autocomplete.update(child.get("autocomplete") or [])
            return password, autocomplete

        password, autocomplete = await self._call(session, target_id, page, gather)
        visited = None if tab is None or tab.visited is None else tuple(tab.visited)
        return PageSignals(a_navigation(page.url), visited, password, frozenset(autocomplete))

    async def on(self, session: SessionRef, event: str, handler: Callable[..., Any]) -> None:
        link = await self._context(session)
        key = (session.cdp_url, session.context_id)
        self._listeners.setdefault(key, []).append((event, handler))
        for target_id, page in list(link.pages.items()):
            if link.owners.get(target_id) == session.context_id:
                page.on(event, handler)  # type: ignore[call-overload]

    def _log(self, page: Page) -> _Calls:
        log = self._calls.get(page)
        if log is None:
            log = self._calls[page] = _Calls()

            def closed(_: Page) -> None:
                self._calls.pop(page, None)
                log.changed.set()

            page.once("close", closed)
        return log

    def _heard(self, response: Response) -> None:
        request = response.request
        if request.resource_type not in K_CALL_TYPES:
            return
        try:
            page = request.frame.page
        except PlaywrightError:
            return
        log = self._log(page)
        at, log.count = log.count, log.count + 1
        reading = asyncio.get_running_loop().create_task(self._record(log, at, response))
        log.reading.add(reading)
        reading.add_done_callback(log.reading.discard)

    async def _record(self, log: _Calls, at: int, response: Response) -> None:
        body = None
        if 200 <= response.status < 300:
            with contextlib.suppress(PlaywrightError):
                body = (await response.text())[:K_CALL_BODY_CHARS]
        call = SeenCall(response.request.method, response.url, response.status, body)
        log.seen.append((at, call))
        log.changed.set()

    async def _frame(self, page: Page, payload: Mapping[str, object]) -> Frame:
        hops = payload.get("frame_path")
        if isinstance(hops, list):
            frame = page.main_frame
            for hop in hops:
                children = frame.child_frames
                url, index = hop.get("url"), hop.get("index")
                same = [c for c in children if url and path_shape(c.url) == path_shape(url)]
                if len(same) == 1:
                    frame = same[0]
                elif isinstance(index, int) and 0 <= index < len(children):
                    frame = children[index]
                else:
                    break
            else:
                return frame
        holding = []
        for frame in page.frames:
            with contextlib.suppress(PlaywrightError):
                found = await frame.evaluate("p => globalThis.sroPage.resolve(p)", dict(payload))
                if found and found.get("found"):
                    holding.append(frame)
        return holding[0] if len(holding) == 1 else page.main_frame

    async def act(
        self, session: SessionRef, target_id: str, payload: Mapping[str, object]
    ) -> PageAnswer:
        page = await self._page(session, target_id)
        frame = await self._frame(page, payload)
        got = await self._call(
            session,
            target_id,
            page,
            lambda: frame.evaluate("p => globalThis.sroPage.act(p)", dict(payload)),
        )
        error, state = got.get("error") or {}, got.get("state")
        return PageAnswer(
            ok=bool(got.get("ok")),
            matched_by=got.get("matched_by"),
            candidates=int(got.get("candidates") or 0),
            detail=str(error.get("detail") or ""),
            error_kind=error.get("kind"),
            state=AfterState(**state) if state else None,
            pin=got.get("pin"),
            repaired=bool(got.get("repaired")),
        )

    async def mark(self, session: SessionRef, target_id: str) -> int:
        page = await self._page(session, target_id)
        if ("response", self._heard) not in self._listeners.get(
            (session.cdp_url, session.context_id), []
        ):
            await self.on(session, "response", self._heard)
        return self._log(page).count

    async def calls_since(
        self, session: SessionRef, target_id: str, mark: int
    ) -> tuple[SeenCall, ...]:
        log = self._calls.get(await self._page(session, target_id))
        if log is None:
            return ()
        return tuple(call for at, call in sorted(log.seen, key=lambda one: one[0]) if at >= mark)

    async def wait_for_call(
        self,
        session: SessionRef,
        target_id: str,
        *,
        method: str,
        shape: str,
        since: int,
        deadline_s: float,
    ) -> bool:
        page = await self._page(session, target_id)
        log = self._log(page)
        wanted = method.upper()

        def arrived() -> bool:
            return any(
                at >= since and call.method.upper() == wanted and path_shape(call.url) == shape
                for at, call in log.seen
            )

        gone = PageGone(f"tab {target_id} in context {session.context_id} is gone")
        try:
            async with asyncio.timeout(deadline_s):
                while not arrived():
                    if page.is_closed():
                        raise gone
                    log.changed.clear()
                    await log.changed.wait()
        except TimeoutError:
            if page.is_closed() or not await self._target_alive(session, target_id):
                raise gone from None
            return False
        return True

    async def wait_for(
        self, session: SessionRef, target_id: str, payload: Mapping[str, object], deadline_s: float
    ) -> bool:
        page = await self._page(session, target_id)
        frame = await self._frame(page, payload)
        try:
            await self._call(
                session,
                target_id,
                page,
                lambda: frame.wait_for_function(
                    "p => globalThis.sroPage.holds(p)", arg=dict(payload), timeout=deadline_s * 1000
                ),
            )
        except PlaywrightTimeoutError:
            return False
        return True

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
