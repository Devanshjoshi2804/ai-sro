from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import logging
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Any

from playwright.async_api import BrowserContext, CDPSession, Frame, Page, async_playwright
from playwright.async_api import Playwright as PlaywrightDriver

from sro.application.capture.decode import (
    CdpPayload,
    epoch_to_datetime,
    to_ax_graph,
    to_console_message,
    to_cookies,
    to_headers,
    to_initiator,
    to_input_action,
    to_page_event,
    to_timing,
)
from sro.application.capture.events import CaptureEvent, InputEvent, RequestEvent, SnapshotEvent
from sro.application.ports.blob import BlobStore
from sro.config import get_settings
from sro.domain.recording.artifact import ArtifactKind
from sro.domain.recording.network import Body, CapturedRequest, Cookie, RedirectHop
from sro.domain.recording.redaction import REDACTED, redact_body
from sro.domain.recording.sensitivity import SECRET_TOKENS
from sro.domain.recording.state import ConsoleMessage, PageEvent
from sro.infrastructure.steel.video import Recorded, ScreencastRecorder

logger = logging.getLogger(__name__)

_RECORDER_JS = Path(__file__).with_name("recorder.js")


_READERS_START = "  const readers = "
_READERS_END = "\n  })();\n"


def _page_readers() -> str:
    source = Path(get_settings().page_code_path).read_text(encoding="utf-8")
    start = source.find(_READERS_START + "(() => {")
    end = source.find(_READERS_END, start)
    if start == -1 or end == -1:
        raise RuntimeError("page-code.js has no readers block to share with the recorder")
    return source[start + len(_READERS_START) : end + len(_READERS_END) - 2]


def _recorder_script() -> str:
    source = _RECORDER_JS.read_text(encoding="utf-8")
    if "__SECRET_WORDS__" not in source:
        raise RuntimeError("recorder.js has no place to put the credential word list")
    if "__PAGE_READERS__" not in source:
        raise RuntimeError("recorder.js has no place to put page-code.js's readers")
    return source.replace("__SECRET_WORDS__", json.dumps(sorted(SECRET_TOKENS))).replace(
        "__PAGE_READERS__", _page_readers()
    )


@dataclass(frozen=True, slots=True)
class PendingArtifact:
    kind: ArtifactKind
    uri: str
    content_type: str
    size_bytes: int
    captured_at: datetime
    frame_index: int | None = None
    label: str | None = None


@dataclass(frozen=True, slots=True)
class CaptureBatch:
    events: list[CaptureEvent]
    artifacts: list[PendingArtifact]
    console: list[ConsoleMessage]
    page_events: list[PageEvent]


@dataclass
class _PendingRequest:
    request_id: str
    method: str
    url: str
    resource_type: str
    started_at: datetime
    request_headers: dict[str, str]
    request_body: Body | None
    initiator: Any
    redirect_chain: list[RedirectHop] = field(default_factory=list)
    status: int | None = None
    status_text: str | None = None
    response_headers: dict[str, str] = field(default_factory=dict)
    cookies_set: tuple[Any, ...] = ()
    timing: Any = None
    protocol: str | None = None
    remote_address: str | None = None
    from_cache: bool = False
    mime_type: str | None = None


class CaptureSession:
    def __init__(
        self,
        *,
        blob_store: BlobStore,
        key_prefix: str,
        inline_body_limit_bytes: int = 256 * 1024,
        screenshot_per_gesture: bool = True,
        video: bool = True,
        video_fps: int = 2,
        redact_secrets: bool = True,
    ) -> None:
        self._blobs = blob_store
        self._prefix = key_prefix.rstrip("/")
        self._inline_limit = inline_body_limit_bytes
        self._screenshot = screenshot_per_gesture
        self._video_fps = video_fps
        self._redact_secrets = redact_secrets
        self._recorder = ScreencastRecorder() if video else None

        self._events: list[CaptureEvent] = []
        self._artifacts: list[PendingArtifact] = []
        self._console: list[ConsoleMessage] = []
        self._page_events: list[PageEvent] = []
        self._pending: dict[str, _PendingRequest] = {}
        self._tasks: set[asyncio.Task[None]] = set()
        self._gesture_count = 0
        self._recorder_source = ""

        self._driver: PlaywrightDriver | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._cdp: CDPSession | None = None

    async def attach(self, debugger_url: str) -> None:
        self._driver = await async_playwright().start()
        browser = await self._driver.chromium.connect_over_cdp(debugger_url)
        self._context = browser.contexts[0] if browser.contexts else await browser.new_context()
        self._page = (
            self._context.pages[0] if self._context.pages else await self._context.new_page()
        )

        await self._install_recorder()
        await self._enable_domains()

    async def _install_recorder(self) -> None:
        context, page = self._require_context(), self._require_page()
        self._recorder_source = _recorder_script()

        await context.expose_binding("__sroRecord", self._on_gesture)
        await context.add_init_script(self._recorder_source)
        page.on("domcontentloaded", lambda _: self._spawn(self._reinstall_recorder()))
        page.on("framenavigated", lambda frame: self._spawn(self._install_in(frame)))
        page.on("frameattached", lambda frame: self._spawn(self._install_in(frame)))
        await self._reinstall_recorder()

    async def _reinstall_recorder(self) -> None:
        page = self._page
        if page is None:
            return
        for frame in page.frames:
            await self._install_in(frame)

    async def _install_in(self, frame: Frame) -> None:
        try:
            await frame.evaluate(self._recorder_source)
        except Exception:
            logger.debug("no recorder in frame %s", frame.url[:80], exc_info=True)

    async def _enable_domains(self) -> None:
        cdp = await self._require_context().new_cdp_session(self._require_page())
        self._cdp = cdp
        for domain in ("Network", "Page", "Runtime", "DOM", "Accessibility"):
            await cdp.send(f"{domain}.enable")

        cdp.on("Network.requestWillBeSent", self._on_request)
        cdp.on("Network.requestWillBeSentExtraInfo", self._on_request_extra)
        cdp.on("Network.responseReceived", self._on_response)
        cdp.on("Network.responseReceivedExtraInfo", self._on_response_extra)
        cdp.on("Network.loadingFinished", lambda payload: self._spawn(self._finish(payload)))
        cdp.on("Network.loadingFailed", self._on_failed)
        cdp.on("Runtime.consoleAPICalled", self._on_console)
        if self._recorder is not None:
            self._spawn(self._video_loop())
        for method in (
            "Page.frameNavigated",
            "Page.loadEventFired",
            "Page.javascriptDialogOpening",
            "Page.javascriptDialogClosed",
            "Page.downloadWillBegin",
            "Page.frameAttached",
            "Page.frameDetached",
            "Page.windowOpen",
        ):
            cdp.on(method, self._page_event_handler(method))

    async def snapshot_cookies(self) -> list[dict[str, Any]]:
        cdp = self._cdp
        if cdp is None:
            return []
        try:
            result = await cdp.send("Network.getAllCookies")
        except Exception:
            logger.warning("could not read the session cookies", exc_info=True)
            return []
        cookies: list[dict[str, Any]] = result.get("cookies", [])
        return cookies

    async def restore_cookies(self, cookies: list[dict[str, Any]]) -> bool:
        cdp = self._cdp
        if cdp is None or not cookies:
            return False
        try:
            await cdp.send("Network.setCookies", {"cookies": [_addressed(c) for c in cookies]})
            stored = {
                (c["domain"], c["name"])
                for c in (await cdp.send("Network.getAllCookies"))["cookies"]
            }
        except Exception:
            logger.warning("could not restore the stored session", exc_info=True)
            return False
        refused = [
            f"{c['domain']}{c['path']}{c['name']}"
            for c in cookies
            if (c["domain"], c["name"]) not in stored
        ]
        if refused:
            logger.warning(
                "the browser refused %d stored cookies: %s", len(refused), ", ".join(refused)
            )
        return len(refused) < len(cookies)

    async def open_at(self, url: str) -> None:
        page = self._page
        if page is None:
            return
        try:
            await page.goto(url, wait_until="domcontentloaded")
        except Exception:
            logger.warning("could not open the session at %s", url, exc_info=True)

    def flush_incomplete(self) -> int:
        stranded = list(self._pending.values())
        self._pending.clear()
        for pending in stranded:
            self._emit(
                pending,
                response_body=None,
                failure_reason=(
                    None
                    if pending.status is not None
                    else "capture ended before the response completed"
                ),
            )
        return len(stranded)

    def drain(self) -> CaptureBatch:
        batch = CaptureBatch(
            events=sorted(self._events, key=lambda event: event.at),
            artifacts=list(self._artifacts),
            console=list(self._console),
            page_events=list(self._page_events),
        )
        self._events.clear()
        self._artifacts.clear()
        self._console.clear()
        self._page_events.clear()
        return batch

    async def detach(self) -> None:
        self.flush_incomplete()
        if self._recorder is not None:
            self._recorder.close()
            self._recorder = None
        for task in list(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        if self._cdp is not None:
            with contextlib.suppress(Exception):
                await self._cdp.detach()
        if self._driver is not None:
            await self._driver.stop()

    async def __aenter__(self) -> CaptureSession:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.detach()

    async def _on_gesture(self, _source: object, raw: str) -> None:
        payload: CdpPayload = json.loads(raw)
        at = epoch_to_datetime(float(payload.get("at", 0)))
        url = str(payload.get("url", ""))
        index = self._gesture_count
        self._gesture_count += 1

        self._events.append(InputEvent(at=at, action=to_input_action(payload)))

        ax = await self._ax_graph(url=url, at=at)
        if ax is not None:
            self._events.append(SnapshotEvent(snapshot=ax))
        if self._screenshot:
            await self._capture_screenshot(index=index, at=at)

    async def _ax_graph(self, *, url: str, at: datetime) -> Any:
        cdp = self._cdp
        if cdp is None:
            return None
        try:
            payload = await cdp.send("Accessibility.getFullAXTree")
        except Exception:
            return None
        return to_ax_graph(payload, url=url, taken_at=at)

    async def _capture_screenshot(self, *, index: int, at: datetime) -> None:
        page = self._page
        if page is None:
            return
        try:
            data = await page.screenshot(type="png")
        except Exception:
            return
        uri = await self._blobs.put(
            f"{self._prefix}/screenshot/{index:05d}.png", data, content_type="image/png"
        )
        self._artifacts.append(
            PendingArtifact(
                kind=ArtifactKind.SCREENSHOT,
                uri=uri,
                content_type="image/png",
                size_bytes=len(data),
                captured_at=at,
                frame_index=index,
            )
        )

    def _on_request(self, payload: CdpPayload) -> None:
        request = payload.get("request", {})
        request_id = str(payload.get("requestId"))

        redirect = payload.get("redirectResponse")
        if redirect and request_id in self._pending:
            self._pending[request_id].redirect_chain.append(
                RedirectHop(
                    url=str(redirect.get("url", "")),
                    status=int(redirect.get("status", 0)),
                    location=to_headers(redirect.get("headers")).get("location"),
                )
            )

        post_data = request.get("postData")
        body = None
        if post_data:
            raw = str(post_data)
            content_type = to_headers(request.get("headers")).get("Content-Type")
            if self._redact_secrets:
                text, redacted = redact_body(raw, content_type=content_type)
            else:
                text, redacted = raw, ()
            body = Body(
                text=text,
                size_bytes=len(text.encode()),
                redacted_fields=redacted,
            )

        self._pending[request_id] = _PendingRequest(
            request_id=request_id,
            method=str(request.get("method", "GET")),
            url=str(request.get("url", "")),
            resource_type=str(payload.get("type", "Other")).lower(),
            started_at=epoch_to_datetime(float(payload.get("wallTime", 0))),
            request_headers=to_headers(request.get("headers")),
            request_body=body,
            initiator=to_initiator(payload.get("initiator")),
            redirect_chain=(
                self._pending[request_id].redirect_chain if request_id in self._pending else []
            ),
        )

    def _on_request_extra(self, payload: CdpPayload) -> None:
        pending = self._pending.get(str(payload.get("requestId")))
        if pending is None:
            return
        pending.request_headers.update(to_headers(payload.get("headers")))

    def _on_response(self, payload: CdpPayload) -> None:
        pending = self._pending.get(str(payload.get("requestId")))
        if pending is None:
            return
        response = payload.get("response", {})
        pending.status = int(response.get("status", 0)) or None
        pending.status_text = str(response.get("statusText") or "") or None
        pending.response_headers.update(to_headers(response.get("headers")))
        pending.timing = to_timing(response.get("timing"))
        pending.protocol = str(response.get("protocol") or "") or None
        pending.remote_address = str(response.get("remoteIPAddress") or "") or None
        pending.from_cache = bool(
            response.get("fromDiskCache") or response.get("fromPrefetchCache")
        )
        pending.mime_type = str(response.get("mimeType") or "") or None

    def _on_response_extra(self, payload: CdpPayload) -> None:
        pending = self._pending.get(str(payload.get("requestId")))
        if pending is None:
            return
        pending.response_headers.update(to_headers(payload.get("headers")))
        pending.cookies_set = self._safe_cookies(
            to_cookies([entry.get("cookie", {}) for entry in payload.get("cookies", [])])
        )

    def _safe_cookies(self, cookies: tuple[Cookie, ...]) -> tuple[Cookie, ...]:
        if not self._redact_secrets:
            return cookies
        return tuple(replace(cookie, value=REDACTED) for cookie in cookies)

    async def _finish(self, payload: CdpPayload) -> None:
        request_id = str(payload.get("requestId"))
        pending = self._pending.pop(request_id, None)
        if pending is None:
            return
        body = await self._response_body(request_id, pending)
        self._emit(pending, response_body=body)

    def _on_failed(self, payload: CdpPayload) -> None:
        pending = self._pending.pop(str(payload.get("requestId")), None)
        if pending is None:
            return
        self._emit(
            pending,
            response_body=None,
            failure_reason=str(payload.get("errorText") or "") or None,
            blocked_reason=str(payload.get("blockedReason") or "") or None,
        )

    async def _response_body(self, request_id: str, pending: _PendingRequest) -> Body | None:
        cdp = self._cdp
        if cdp is None:
            return None
        try:
            result = await cdp.send("Network.getResponseBody", {"requestId": request_id})
        except Exception:
            return None

        text = str(result.get("body", ""))
        base64_encoded = bool(result.get("base64Encoded"))
        raw = base64.b64decode(text) if base64_encoded else text.encode()
        if not raw:
            return None

        redacted: tuple[str, ...] = ()
        if self._redact_secrets:
            readable = _as_text(raw) if base64_encoded else text
            if readable is not None:
                cleaned, redacted = redact_body(readable, content_type=pending.mime_type)
                if redacted:
                    text, raw, base64_encoded = cleaned, cleaned.encode(), False

        if len(raw) <= self._inline_limit:
            return Body(
                text=text,
                size_bytes=len(raw),
                mime_type=pending.mime_type,
                encoding="base64" if base64_encoded else None,
                redacted_fields=redacted,
            )

        uri = await self._blobs.put(
            f"{self._prefix}/payload/{request_id}",
            raw,
            content_type=pending.mime_type or "application/octet-stream",
        )
        return Body(
            blob_uri=uri,
            size_bytes=len(raw),
            mime_type=pending.mime_type,
            encoding="base64" if base64_encoded else None,
            redacted_fields=redacted,
        )

    def _emit(
        self,
        pending: _PendingRequest,
        *,
        response_body: Body | None,
        failure_reason: str | None = None,
        blocked_reason: str | None = None,
    ) -> None:
        self._events.append(
            RequestEvent(
                request=CapturedRequest(
                    request_id=pending.request_id,
                    method=pending.method,
                    url=pending.url,
                    resource_type=pending.resource_type,
                    started_at=pending.started_at,
                    request_headers=pending.request_headers,
                    request_body=pending.request_body,
                    status=pending.status,
                    status_text=pending.status_text,
                    response_headers=pending.response_headers,
                    response_body=response_body,
                    cookies_set=pending.cookies_set,
                    initiator=pending.initiator,
                    redirect_chain=tuple(pending.redirect_chain),
                    timing=pending.timing,
                    protocol=pending.protocol,
                    remote_address=pending.remote_address,
                    from_cache=pending.from_cache,
                    failure_reason=failure_reason,
                    blocked_reason=blocked_reason,
                )
            )
        )

    async def _video_loop(self) -> None:
        interval = 1 / max(self._video_fps, 1)
        while True:
            await asyncio.sleep(interval)
            recorder, cdp = self._recorder, self._cdp
            if recorder is None or cdp is None:
                return
            try:
                shot = await cdp.send(
                    "Page.captureScreenshot",
                    {"format": "jpeg", "quality": 55, "optimizeForSpeed": True},
                )
            except Exception:
                logger.debug("skipped a video frame", exc_info=True)
                continue
            data = shot.get("data")
            if data:
                recorder.add_frame(
                    base64.b64decode(str(data)), at_ms=datetime.now(UTC).timestamp() * 1000
                )

    def stop_video(self) -> Recorded | None:
        recorder, self._recorder = self._recorder, None
        return recorder.close() if recorder is not None else None

    def _on_console(self, payload: CdpPayload) -> None:
        at = epoch_to_datetime(float(payload.get("timestamp", 0)) / 1000)
        self._console.append(to_console_message(payload, at=at))

    def _page_event_handler(self, method: str) -> Any:
        def handle(payload: CdpPayload) -> None:
            event = to_page_event(method, payload, at=datetime.now(UTC))
            if event is not None:
                self._page_events.append(event)

        return handle

    def _spawn(self, coro: Any) -> None:
        task: asyncio.Task[None] = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    @property
    def page(self) -> Page:
        return self._require_page()

    def _require_context(self) -> BrowserContext:
        if self._context is None:
            raise RuntimeError("CaptureSession.attach() has not run")
        return self._context

    def _require_page(self) -> Page:
        if self._page is None:
            raise RuntimeError("CaptureSession.attach() has not run")
        return self._page


def _addressed(cookie: dict[str, Any]) -> dict[str, Any]:
    if cookie.get("url"):
        return cookie
    domain = str(cookie.get("domain", "")).lstrip(".")
    if not domain:
        return cookie
    scheme = "https" if cookie.get("secure", True) else "http"
    return {**cookie, "url": f"{scheme}://{domain}{cookie.get('path', '/')}"}


def _as_text(raw: bytes) -> str | None:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
