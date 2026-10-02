from __future__ import annotations

import asyncio
import contextlib
import itertools
import json
from collections import deque
from collections.abc import Awaitable, Callable, Collection, Mapping, Sequence
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

from sro.application.ports.http import HttpResponse
from sro.application.ports.page import PageAnswer, PageGone, PageUnsettled, SessionRef
from sro.application.ports.vision import Screen
from sro.domain.execution.lanes import SeenCall
from sro.domain.observation.gesture import AfterState
from sro.domain.observation.trim import path_shape
from sro.domain.recording.events import ActionKind
from sro.domain.recording.sensitivity import K_TOKENS, classify_header
from sro.domain.shared.hosts import belongs_to, origin_of
from sro.domain.skill.signing_in import PageSignals, a_navigation
from sro.infrastructure.steel.capture import addressed
from sro.infrastructure.steel.client import cdp_origin, websocket_debugger_url

K_ATTACH_TIMEOUT_S = 10
K_ACTION_TIMEOUT_S = 15
K_CALL_BODY_CHARS = 4096
K_CALL_TYPES = frozenset({"fetch", "xhr"})
K_NO_DOCUMENT = frozenset({204, 205})
K_SCROLL_PX = 400
K_REQUESTS_KEPT = 200
K_ALIVE_RESERVE_S = 0.25
K_APPEAR_S = 15
K_APPEAR_POLL_S = 0.25
_CONTEXT_DESTROYED = "Execution context was destroyed"
_NOT_DRAWN_YET = frozenset({"control_not_found", "frame_not_found"})
_BROWSER_OWNS = frozenset({"cookie", "host", "origin", "referer", "content-length", "connection"})
_SEND = """async (c) => {
  const stop = new AbortController();
  const timer = setTimeout(() => stop.abort(), c.ms);
  try {
    const r = await fetch(c.url, {method: c.method, headers: c.headers, body: c.body ?? undefined,
      credentials: "include", signal: stop.signal});
    const headers = {};
    r.headers.forEach((value, name) => { headers[name] = value; });
    return {status: r.status, headers, text: await r.text(), redirected: r.redirected, url: r.url};
  } finally { clearTimeout(timer); }
}"""

_SIGNALS = "() => globalThis.sroPage.signals()"
_HIT_TEST = "([x, y]) => globalThis.sroPage.hitTest(x, y)"
_VIEWPORT = "() => ({width: innerWidth, height: innerHeight})"

_SEED_STORAGE = """(items) => {
  for (const { name, value } of items) {
    if (localStorage.getItem(name) === null) localStorage.setItem(name, value);
  }
}"""

T = TypeVar("T")

type _Key = tuple[str, str]


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
class _Sent:
    at: int
    own_frame: bool
    body: str | None
    content_type: str | None


@dataclass
class _Calls:
    first: int
    numbered: dict[Request, _Sent] = field(default_factory=dict)
    seen: list[tuple[int, SeenCall]] = field(default_factory=list)
    acted: Frame | None = None
    changed: asyncio.Event = field(default_factory=asyncio.Event)
    reading: set[asyncio.Task[None]] = field(default_factory=set)


@dataclass
class _Tab:
    visited: list[str] | None
    owner: str = ""
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
        self._requests: dict[_Key, deque[tuple[int, str, dict[str, str]]]] = {}
        self._floors: dict[_Key, int] = {}
        self._seen: dict[_Key, asyncio.Event] = {}
        self._reading: set[asyncio.Task[None]] = set()
        self._seq = itertools.count(1)

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
            browser.on("disconnected", lambda _: self._wake_all(cdp_url))
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

        tab = self._tabs[page] = _Tab([] if whole else None, owner=owner)
        tab.settled.set()
        key = (link.cdp_url, owner)

        def gone(_: Page) -> None:
            link.pages.pop(target_id, None)
            link.owners.pop(target_id, None)
            self._tabs.pop(page, None)
            tab.pending.clear()
            tab.settled.set()
            self._wake(key)

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
        page.on("request", lambda request: self._saw(key, request))
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
        making = asyncio.ensure_future(
            self._send(
                link,
                "Target.createTarget",
                {"url": "about:blank", "browserContextId": session.context_id},
            )
        )
        try:
            made = await asyncio.shield(making)
        except asyncio.CancelledError:
            with contextlib.suppress(PageGone):
                late = await asyncio.shield(making)
                await asyncio.shield(
                    self._send(link, "Target.closeTarget", {"targetId": str(late["targetId"])})
                )
            raise
        target_id = str(made["targetId"])
        try:
            page = link.pages.get(target_id)
            if page is None:
                waiter: asyncio.Future[Page] = asyncio.get_running_loop().create_future()
                link.waiting[target_id] = waiter
                try:
                    page = await asyncio.wait_for(waiter, K_ATTACH_TIMEOUT_S)
                except TimeoutError:
                    raise PageGone(
                        f"tab {target_id} did not attach within {K_ATTACH_TIMEOUT_S} s"
                    ) from None
                finally:
                    link.waiting.pop(target_id, None)
            loaded = page
            await self._call(
                session,
                target_id,
                loaded,
                lambda: loaded.goto(
                    url, wait_until="domcontentloaded", timeout=K_ACTION_TIMEOUT_S * 1000
                ),
            )
        except BaseException:
            with contextlib.suppress(PageGone):
                await asyncio.shield(
                    self._send(link, "Target.closeTarget", {"targetId": target_id})
                )
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

    async def send(
        self,
        session: SessionRef,
        target_id: str,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: str | None = None,
        timeout_s: float = 30.0,
    ) -> HttpResponse:
        """A call made by the page itself: its cookies, its origin and whatever
        the site's edge (Cloudflare, on Blue Yonder) granted the browser go with
        it. The same call from the worker's own client was answered 302/404."""
        page = await self._page(session, target_id)
        got = await self._call(
            session,
            target_id,
            page,
            lambda: page.evaluate(
                _SEND,
                {
                    "method": method,
                    "url": url,
                    "headers": {k: v for k, v in headers.items() if k.lower() not in _BROWSER_OWNS},
                    "body": body,
                    "ms": int(timeout_s * 1000),
                },
            ),
        )
        answered = dict(got.get("headers") or {})
        if got.get("redirected"):
            answered.setdefault("location", str(got.get("url") or ""))
        return HttpResponse(int(got.get("status") or 0), answered, str(got.get("text") or ""))

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
        self._listen(await self._context(session), session, event, handler)

    def _listen(
        self, link: _Link, session: SessionRef, event: str, handler: Callable[..., Any]
    ) -> None:
        key = (session.cdp_url, session.context_id)
        self._listeners.setdefault(key, []).append((event, handler))
        for target_id, page in list(link.pages.items()):
            if link.owners.get(target_id) == session.context_id:
                page.on(event, handler)  # type: ignore[call-overload]

    def _log(self, page: Page) -> _Calls:
        log = self._calls.get(page)
        if log is None:
            log = self._calls[page] = _Calls(first=next(self._seq))

            def closed(_: Page) -> None:
                self._calls.pop(page, None)
                log.changed.set()

            page.once("close", closed)
        return log

    def _sent(self, request: Request) -> None:
        if request.resource_type not in K_CALL_TYPES:
            return
        try:
            page = request.frame.page
            own_frame = request.frame is self._log(page).acted
            content_type = request.headers.get("content-type")
            body = request.post_data
        except PlaywrightError:
            return
        self._log(page).numbered[request] = _Sent(next(self._seq), own_frame, body, content_type)

    def _wake(self, key: _Key) -> None:
        seen = self._seen.get(key)
        if seen is not None:
            seen.set()

    def _wake_all(self, cdp_url: str) -> None:
        for key in [key for key in self._seen if key[0] == cdp_url]:
            self._wake(key)

    def _saw(self, key: _Key, request: Request) -> None:
        reading = asyncio.get_running_loop().create_task(self._keep(key, next(self._seq), request))
        self._reading.add(reading)
        reading.add_done_callback(self._reading.discard)

    async def _keep(self, key: _Key, at: int, request: Request) -> None:
        try:
            headers = await request.all_headers()
        except PlaywrightError:
            return
        kept = {
            name.lower(): value
            for name, value in headers.items()
            if name.lower() != "cookie" and classify_header(name) in K_TOKENS
        }
        if kept:
            log = self._requests.setdefault(key, deque(maxlen=K_REQUESTS_KEPT))
            log.append((at, origin_of(request.url), kept))
            self._wake(key)

    def _heard(self, response: Response) -> None:
        request = response.request
        try:
            log = self._calls.get(request.frame.page)
        except PlaywrightError:
            return
        sent = None if log is None else log.numbered.get(request)
        if log is None or sent is None:
            return
        reading = asyncio.get_running_loop().create_task(self._record(log, sent, response))
        log.reading.add(reading)
        reading.add_done_callback(log.reading.discard)

    async def _record(self, log: _Calls, sent: _Sent, response: Response) -> None:
        body = None
        if 200 <= response.status < 300:
            with contextlib.suppress(PlaywrightError):
                body = (await response.text())[:K_CALL_BODY_CHARS]
        call = SeenCall(
            response.request.method,
            response.url,
            response.status,
            body,
            sent.body,
            sent.content_type,
            sent.own_frame,
        )
        log.seen.append((sent.at, call))
        log.numbered.pop(response.request, None)
        log.changed.set()

    async def _frame(self, page: Page, payload: Mapping[str, object]) -> tuple[Frame | None, str]:
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
                    return None, "frame_not_found"
            return frame, ""
        holding = []
        for frame in page.frames:
            with contextlib.suppress(PlaywrightError):
                found = await frame.evaluate("p => globalThis.sroPage.resolve(p)", dict(payload))
                if found and found.get("found"):
                    holding.append((frame, found.get("strategy")))
        picked = best_frame(holding)
        if picked is not None:
            return picked, ""
        return (None, "frame_ambiguous") if holding else (page.main_frame, "")

    async def act(
        self, session: SessionRef, target_id: str, payload: Mapping[str, object]
    ) -> PageAnswer:
        loop = asyncio.get_running_loop()
        until = loop.time() + K_APPEAR_S
        while True:
            answer = await self._act_once(session, target_id, payload)
            if answer.error_kind not in _NOT_DRAWN_YET or loop.time() >= until:
                return answer
            await asyncio.sleep(K_APPEAR_POLL_S)

    async def _act_once(
        self, session: SessionRef, target_id: str, payload: Mapping[str, object]
    ) -> PageAnswer:
        page = await self._page(session, target_id)
        frame, kind = await self._frame(page, payload)
        if frame is None:
            detail = (
                "more than one frame matched, ambiguously"
                if kind == "frame_ambiguous"
                else "the recorded frame is no longer on the page"
            )
            return PageAnswer(ok=False, detail=detail, error_kind=kind)
        self._log(page).acted = frame
        tab = self._tabs.get(page)
        loads = tab.loads if tab is not None else 0

        async def acted() -> Any:
            try:
                return await frame.evaluate("p => globalThis.sroPage.act(p)", dict(payload))
            except PlaywrightError as why:
                # the action itself navigated the page: it is done, so wait for the new page
                if (
                    tab is None
                    or _CONTEXT_DESTROYED not in str(why)
                    or (tab.loads == loads and tab.settled.is_set())
                ):
                    raise
                async with asyncio.timeout(K_ACTION_TIMEOUT_S):
                    await tab.settled.wait()
                return {"ok": True}

        got = await self._call(session, target_id, page, acted)
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

    async def resolve(
        self, session: SessionRef, target_id: str, payload: Mapping[str, object]
    ) -> PageAnswer:
        page = await self._page(session, target_id)
        frame, kind = await self._frame(page, payload)
        if frame is None:
            return PageAnswer(ok=False, error_kind=kind)
        got = await self._call(
            session,
            target_id,
            page,
            lambda: frame.evaluate("p => globalThis.sroPage.resolve(p)", dict(payload)),
        )
        return PageAnswer(
            ok=bool(got.get("found")),
            matched_by=got.get("strategy"),
            candidates=int(got.get("candidates") or 0),
            held=got.get("held"),
        )

    async def outline(
        self,
        session: SessionRef,
        target_id: str,
        frame_path: Sequence[Mapping[str, object]] | None,
    ) -> Mapping[str, object] | None:
        page = await self._page(session, target_id)
        frame, _ = await self._frame(page, {"frame_path": list(frame_path or [])})
        if frame is None:
            return None
        got = await self._call(
            session, target_id, page, lambda: frame.evaluate("() => globalThis.sroPage.outline()")
        )
        return got if isinstance(got, dict) else None

    async def screenshot(self, session: SessionRef, target_id: str) -> Screen:
        page = await self._page(session, target_id)

        async def take() -> Screen:
            size = page.viewport_size or await page.evaluate(_VIEWPORT)
            image = await page.screenshot(
                type="png", scale="css", timeout=K_ACTION_TIMEOUT_S * 1000
            )
            return Screen(image, "image/png", int(size["width"]), int(size["height"]))

        return await self._call(session, target_id, page, take)

    async def hit_test(
        self, session: SessionRef, target_id: str, x: int, y: int
    ) -> Mapping[str, object] | None:
        page = await self._page(session, target_id)
        found = await self._call(
            session, target_id, page, lambda: page.main_frame.evaluate(_HIT_TEST, [x, y])
        )
        return dict(found) if found else None

    async def point(
        self,
        session: SessionRef,
        target_id: str,
        action: ActionKind,
        x: int,
        y: int,
        value: str | None,
        frame_path: Sequence[Mapping[str, object]] | None,
    ) -> None:
        page = await self._page(session, target_id)
        frame, _ = await self._frame(page, {"frame_path": list(frame_path or [])})
        self._log(page).acted = frame

        async def gesture() -> None:
            await page.mouse.move(x, y)
            if action in (ActionKind.CLICK, ActionKind.TYPE):
                await page.mouse.click(x, y)
            if action is ActionKind.TYPE:
                await page.keyboard.type(value or "")
            elif action is ActionKind.PRESS:
                await page.keyboard.press(value or "Enter")
            elif action is ActionKind.SCROLL:
                digits = value is not None and value.lstrip("-").isdigit()
                await page.mouse.wheel(0, int(value) if digits and value else K_SCROLL_PX)

        await self._call(session, target_id, page, gesture)

    async def mark(self, session: SessionRef, target_id: str) -> int:
        page = await self._page(session, target_id)
        if ("request", self._sent) not in self._listeners.get(
            (session.cdp_url, session.context_id), []
        ):
            link = self._links.get(session.cdp_url)
            if link is None:
                raise PageGone(f"the connection for context {session.context_id} is gone")
            self._listen(link, session, "request", self._sent)
            self._listen(link, session, "response", self._heard)
        self._log(page).acted = None
        return next(self._seq)

    async def calls_since(
        self, session: SessionRef, target_id: str, mark: int
    ) -> tuple[SeenCall, ...]:
        log = self._calls.get(await self._page(session, target_id))
        if log is None or log.first > mark:
            return ()
        pending = [
            (
                sent.at,
                SeenCall(
                    request.method,
                    request.url,
                    None,
                    None,
                    sent.body,
                    sent.content_type,
                    sent.own_frame,
                ),
            )
            for request, sent in log.numbered.items()
        ]
        return tuple(
            call for at, call in sorted([*log.seen, *pending], key=lambda one: one[0]) if at > mark
        )

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

        if log.first > since:
            return False

        def arrived() -> bool:
            return any(
                at > since and call.method.upper() == wanted and path_shape(call.url) == shape
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
        recorded, _ = (
            await self._frame(page, payload)
            if isinstance(payload.get("frame_path"), list)
            else (self._log(page).acted or page.main_frame, "")
        )
        if recorded is None:
            return False
        frame = recorded
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

    async def forget_headers_before(self, session: SessionRef, mark: int) -> None:
        key = (session.cdp_url, session.context_id)
        self._floors[key] = max(mark, self._floors.get(key, 0))

    async def headers_for(
        self,
        session: SessionRef,
        origin: str,
        deadline_s: float,
        *,
        since: int = 0,
        needs: Collection[str] = (),
    ) -> dict[str, str]:
        key = (session.cdp_url, session.context_id)
        since = max(since, self._floors.get(key, 0))
        wanted = origin_of(origin)
        seen = self._seen.setdefault(key, asyncio.Event())

        def merged() -> dict[str, str]:
            found: dict[str, str] = {}
            for at, where, kept in sorted(self._requests.get(key, ()), key=lambda one: one[0]):
                if at > since and where == wanted:
                    found.update(kept)
            return found

        until = asyncio.get_running_loop().time() + deadline_s
        try:
            async with asyncio.timeout_at(until - K_ALIVE_RESERVE_S):
                await self._context(session)
                while True:
                    found = merged()
                    if all(name in found for name in needs):
                        return found
                    await seen.wait()
                    seen.clear()
                    await self._context(session)
        except TimeoutError:
            pass
        with contextlib.suppress(TimeoutError):
            async with asyncio.timeout_at(until):
                await self._context(session)
        return merged()

    async def cookies_for(self, session: SessionRef, url: str) -> str:
        link = await self._context(session)
        found = await self._send(
            link, "Storage.getCookies", {"browserContextId": session.context_id}
        )
        return "; ".join(
            f"{cookie['name']}={cookie['value']}"
            for cookie in found["cookies"]
            if belongs_to(cookie, url)
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

    async def forget_calls(self, session: SessionRef, target_id: str) -> None:
        self._calls.pop(await self._page(session, target_id), None)

    async def forget(self, session: SessionRef) -> None:
        key = (session.cdp_url, session.context_id)
        self._requests.pop(key, None)
        self._floors.pop(key, None)
        seen = self._seen.pop(key, None)
        if seen is not None:
            seen.set()
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


def best_frame[F](found: Sequence[tuple[F, object]]) -> F | None:
    strict = [frame for frame, strategy in found if strategy != "repair"]
    pool = strict or [frame for frame, _ in found]
    return pool[0] if len(pool) == 1 else None
