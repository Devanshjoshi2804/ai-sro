"""CDP payloads to domain objects.

Pure functions: dict in, domain object out. No browser, no I/O, so the parsing of
every CDP shape is testable in milliseconds -- which matters because these shapes
are the part most likely to shift under a Chrome upgrade.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sro.domain.recording.axgraph import AxGraph
from sro.domain.recording.element import Bounds, ElementFingerprint
from sro.domain.recording.events import ActionKind, InputAction
from sro.domain.recording.network import (
    Cookie,
    Initiator,
    InitiatorKind,
    ResourceTiming,
    StackFrame,
)
from sro.domain.recording.state import (
    BrowserState,
    ConsoleLevel,
    ConsoleMessage,
    PageEvent,
    PageEventKind,
)

CdpPayload = dict[str, Any]

_AX_STATE_PROPERTIES = frozenset(
    {
        "disabled",
        "checked",
        "expanded",
        "selected",
        "focused",
        "required",
        "invalid",
        "busy",
        "readonly",
        "pressed",
    }
)

_CONSOLE_LEVELS = {
    "log": ConsoleLevel.LOG,
    "info": ConsoleLevel.INFO,
    "warning": ConsoleLevel.WARNING,
    "warn": ConsoleLevel.WARNING,
    "error": ConsoleLevel.ERROR,
    "debug": ConsoleLevel.DEBUG,
    "verbose": ConsoleLevel.DEBUG,
}

_INITIATOR_KINDS = {
    "parser": InitiatorKind.PARSER,
    "script": InitiatorKind.SCRIPT,
    "preload": InitiatorKind.PRELOAD,
    "SignedExchange": InitiatorKind.SIGNED_EXCHANGE,
    "signedExchange": InitiatorKind.SIGNED_EXCHANGE,
    "redirect": InitiatorKind.REDIRECT,
}

_PAGE_EVENT_KINDS = {
    "Page.frameNavigated": PageEventKind.NAVIGATED,
    "Page.loadEventFired": PageEventKind.LOADED,
    "Page.javascriptDialogOpening": PageEventKind.DIALOG_OPENED,
    "Page.javascriptDialogClosed": PageEventKind.DIALOG_HANDLED,
    "Page.downloadWillBegin": PageEventKind.DOWNLOAD_STARTED,
    "Page.frameAttached": PageEventKind.FRAME_ATTACHED,
    "Page.frameDetached": PageEventKind.FRAME_DETACHED,
    "Page.windowOpen": PageEventKind.POPUP_OPENED,
}


def epoch_to_datetime(seconds: float) -> datetime:
    """CDP wall-clock timestamps are Unix seconds as a float."""
    return datetime.fromtimestamp(seconds, tz=UTC)


def to_headers(raw: CdpPayload | None) -> dict[str, str]:
    """Every header, verbatim. Nothing filtered -- see docs/11-capture-completeness.md."""
    if not raw:
        return {}
    return {str(key): str(value) for key, value in raw.items()}


def to_initiator(raw: CdpPayload | None) -> Initiator | None:
    """The 'why' of a request: what caused the browser to make it."""
    if not raw:
        return None

    stack_frames: list[StackFrame] = []
    stack = raw.get("stack")
    if isinstance(stack, dict):
        for frame in stack.get("callFrames", []):
            stack_frames.append(
                StackFrame(
                    function=str(frame.get("functionName") or "<anonymous>"),
                    url=str(frame.get("url") or ""),
                    line=int(frame.get("lineNumber") or 0),
                    column=int(frame.get("columnNumber") or 0),
                )
            )

    line = raw.get("lineNumber")
    return Initiator(
        kind=_INITIATOR_KINDS.get(str(raw.get("type")), InitiatorKind.OTHER),
        url=str(raw["url"]) if raw.get("url") else None,
        line=int(line) if line is not None else None,
        stack=tuple(stack_frames),
        parent_request_id=str(raw["requestId"]) if raw.get("requestId") else None,
    )


def to_timing(raw: CdpPayload | None) -> ResourceTiming | None:
    """CDP timings are offsets in milliseconds from ``requestTime``.

    Negative offsets mean the phase did not happen -- a reused connection has no
    DNS or TLS -- so they collapse to ``None`` rather than to a bogus zero.
    """
    if not raw:
        return None

    def span(start_key: str, end_key: str) -> float | None:
        start, end = raw.get(start_key), raw.get(end_key)
        if start is None or end is None or start < 0 or end < 0:
            return None
        return float(end) - float(start)

    send = span("sendStart", "sendEnd")
    receive_end = raw.get("receiveHeadersEnd")
    send_end = raw.get("sendEnd")
    wait = (
        float(receive_end) - float(send_end)
        if receive_end is not None and send_end is not None and receive_end >= 0 and send_end >= 0
        else None
    )

    return ResourceTiming(
        dns_ms=span("dnsStart", "dnsEnd"),
        connect_ms=span("connectStart", "connectEnd"),
        tls_ms=span("sslStart", "sslEnd"),
        send_ms=send,
        wait_ms=wait,
    )


def to_cookies(raw: list[CdpPayload] | None) -> tuple[Cookie, ...]:
    """All cookie attributes, including the ones that decide replayability."""
    if not raw:
        return ()
    cookies = []
    for entry in raw:
        expires = entry.get("expires")
        cookies.append(
            Cookie(
                name=str(entry.get("name", "")),
                value=str(entry.get("value", "")),
                domain=str(entry.get("domain", "")),
                path=str(entry.get("path", "/")),
                secure=bool(entry.get("secure", False)),
                http_only=bool(entry.get("httpOnly", False)),
                same_site=str(entry["sameSite"]) if entry.get("sameSite") else None,
                expires=(
                    epoch_to_datetime(float(expires))
                    if expires is not None and float(expires) > 0
                    else None
                ),
                session=bool(entry.get("session", expires is None)),
            )
        )
    return tuple(cookies)


def to_ax_graph(
    payload: CdpPayload, *, url: str, taken_at: datetime, frame_url: str | None = None
) -> AxGraph:
    """``Accessibility.getFullAXTree`` to a graph with its edges intact.

    Ignored nodes are kept: an element becoming ignored is itself a state change,
    and dropping them would break the parent chain for everything beneath.
    """
    nodes: list[ElementFingerprint] = []
    root_id: str | None = None

    for raw in payload.get("nodes", []):
        node_id = str(raw.get("nodeId")) if raw.get("nodeId") is not None else None
        parent_id = str(raw["parentId"]) if raw.get("parentId") is not None else None
        if parent_id is None and root_id is None and node_id is not None:
            root_id = node_id

        properties = {
            str(p.get("name")): p.get("value", {}).get("value")
            for p in raw.get("properties", [])
            if isinstance(p, dict)
        }
        states = frozenset(
            name
            for name, value in properties.items()
            if name in _AX_STATE_PROPERTIES and value not in (False, "false", None)
        )

        role = _ax_value(raw.get("role"))
        name = _ax_value(raw.get("name"))
        description = _ax_value(raw.get("description"))
        value = _ax_value(raw.get("value"))

        if not any((role, name, description, value, node_id)):
            continue

        nodes.append(
            ElementFingerprint(
                node_id=node_id,
                parent_id=parent_id,
                child_ids=tuple(str(child) for child in raw.get("childIds", [])),
                role=role,
                accessible_name=name,
                description=description,
                value=value,
                states=states,
                attributes={
                    key: str(val)
                    for key, val in properties.items()
                    if key not in _AX_STATE_PROPERTIES and val is not None
                },
            )
        )

    return AxGraph(
        taken_at=taken_at, url=url, frame_url=frame_url, nodes=tuple(nodes), root_id=root_id
    )


def _ax_value(raw: CdpPayload | None) -> str | None:
    if not raw:
        return None
    value = raw.get("value")
    return str(value) if value not in (None, "") else None


def to_console_message(payload: CdpPayload, *, at: datetime) -> ConsoleMessage:
    """``Runtime.consoleAPICalled``. A logged validation failure is a branch reason."""
    args = payload.get("args", [])
    text = " ".join(
        str(arg.get("value", arg.get("description", ""))) for arg in args if isinstance(arg, dict)
    )
    stack_frames = tuple(
        StackFrame(
            function=str(frame.get("functionName") or "<anonymous>"),
            url=str(frame.get("url") or ""),
            line=int(frame.get("lineNumber") or 0),
            column=int(frame.get("columnNumber") or 0),
        )
        for frame in (payload.get("stackTrace") or {}).get("callFrames", [])
    )
    return ConsoleMessage(
        at=at,
        level=_CONSOLE_LEVELS.get(str(payload.get("type")), ConsoleLevel.LOG),
        text=text,
        source="console-api",
        url=stack_frames[0].url if stack_frames else None,
        stack=stack_frames,
    )


def to_page_event(method: str, payload: CdpPayload, *, at: datetime) -> PageEvent | None:
    kind = _PAGE_EVENT_KINDS.get(method)
    if kind is None:
        return None

    frame = payload.get("frame") or {}
    url = payload.get("url") or frame.get("url")
    detail = (
        payload.get("message")
        or payload.get("suggestedFilename")
        or payload.get("frameId")
        or payload.get("windowName")
    )
    return PageEvent(
        at=at,
        kind=kind,
        url=str(url) if url else None,
        detail=str(detail) if detail else None,
    )


def to_browser_state(
    *,
    at: datetime,
    origin: str,
    cookies: list[CdpPayload] | None,
    local_storage: CdpPayload | None,
    session_storage: CdpPayload | None,
) -> BrowserState:
    return BrowserState(
        taken_at=at,
        origin=origin,
        cookies=to_cookies(cookies),
        local_storage={str(k): str(v) for k, v in (local_storage or {}).items()},
        session_storage={str(k): str(v) for k, v in (session_storage or {}).items()},
    )


def to_input_action(payload: CdpPayload) -> InputAction:
    """A record emitted by the injected page recorder.

    The element description here is DOM-side and deliberately shallow: roles and
    accessible names come from the AX tree taken at the same instant, which is
    authoritative. This carries the selectors the AX tree cannot give.
    """
    target = payload.get("target")
    fingerprint = _to_dom_fingerprint(target) if target else None
    secret = bool(payload.get("secret"))
    return InputAction(
        kind=ActionKind(str(payload.get("kind", "click"))),
        target=fingerprint,
        # Belt and braces: the page already dropped it, and a page is not a
        # trustworthy place to enforce this.
        value=(
            None
            if secret
            else (str(payload["value"]) if payload.get("value") is not None else None)
        ),
        secret=secret,
        modifiers=frozenset(str(m) for m in payload.get("modifiers", [])),
    )


def _to_dom_fingerprint(raw: CdpPayload) -> ElementFingerprint:
    box = raw.get("bounds") or {}
    return ElementFingerprint(
        role=str(raw["role"]) if raw.get("role") else None,
        accessible_name=str(raw["name"]) if raw.get("name") else None,
        text=str(raw["text"]) if raw.get("text") else None,
        test_id=str(raw["testId"]) if raw.get("testId") else None,
        css_path=str(raw["cssPath"]) if raw.get("cssPath") else None,
        xpath=str(raw["xpath"]) if raw.get("xpath") else None,
        tag=str(raw["tag"]) if raw.get("tag") else None,
        bounds=(
            Bounds(
                x=float(box.get("x", 0)),
                y=float(box.get("y", 0)),
                width=float(box.get("width", 0)),
                height=float(box.get("height", 0)),
            )
            if box
            else None
        ),
        attributes={str(k): str(v) for k, v in (raw.get("attributes") or {}).items()},
    )
