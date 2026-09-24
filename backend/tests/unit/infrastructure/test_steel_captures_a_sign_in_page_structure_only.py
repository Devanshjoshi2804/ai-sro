"""Spec §5.6 holds for Steel's own capture too, by the same rule.

An operator can demonstrate a sign-in in a Steel recording. The page-side
recorder is the one the extension runs, so it already marks a gesture on a
page holding a password or one-time-code field; the tab's OAuth/OIDC flow is
followed here with the same `SignInFlow` the backend's ingest uses. On a
sign-in page nothing typed, no tree, no screenshot, no video frame and no body
is kept -- only what was acted on and each call's method, URL and status.
"""

from __future__ import annotations

import json
from typing import Any

from sro.application.capture.events import InputEvent, RequestEvent, SnapshotEvent
from sro.infrastructure.steel.capture import CaptureSession
from tests.unit.fakes import FakeBlobStore

AUTHORIZE = (
    "https://login.idp.example/authorize?client_id=app&response_type=code"
    "&redirect_uri=https%3A%2F%2Fwms.example%2Fcallback&state=s1"
)


class _Cdp:
    def __init__(self) -> None:
        self.asked: list[str] = []

    async def send(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.asked.append(method)
        if method == "Accessibility.getFullAXTree":
            return {"nodes": [{"nodeId": "1", "role": {"value": "textbox"}}]}
        if method == "Network.getResponseBody":
            return {"body": json.dumps({"session": "S3SSION"}), "base64Encoded": False}
        if method == "Page.captureScreenshot":
            return {"data": "aGVsbG8="}
        return {}


class _Page:
    def __init__(self) -> None:
        self.shots = 0

    async def screenshot(self, **_: object) -> bytes:
        self.shots += 1
        return b"png"


class _Video:
    def __init__(self) -> None:
        self.frames = 0

    def add_frame(self, data: bytes, *, at_ms: float) -> None:
        self.frames += 1


def _session() -> tuple[CaptureSession, _Cdp, _Page]:
    session = CaptureSession(blob_store=FakeBlobStore(), key_prefix="acme/rec-1", video=False)
    cdp, page = _Cdp(), _Page()
    session._cdp = cdp  # type: ignore[assignment]
    session._page = page  # type: ignore[assignment]
    session._main_frame = "MAIN"
    return session, cdp, page


def _gesture(value: str, **extra: object) -> str:
    return json.dumps(
        {
            "kind": "type",
            "value": value,
            "target": {"tag": "input", "cssPath": "form > input"},
            "at": 1787654321.0,
            "url": "https://x/",
            **extra,
        }
    )


def _navigation(url: str, *, method: str = "GET", post: str | None = None) -> dict[str, Any]:
    request: dict[str, Any] = {"url": url, "method": method, "headers": {}}
    if post is not None:
        request["postData"] = post
    return {
        "requestId": url,
        "type": "Document",
        "frameId": "MAIN",
        "wallTime": 1787654321.0,
        "request": request,
    }


async def test_a_gesture_the_recorder_marked_keeps_no_value_no_tree_and_no_picture() -> None:
    session, cdp, page = _session()

    await session._on_gesture(None, _gesture("hunter2", sign_in=True))

    events = session.drain().events
    assert [type(event) for event in events] == [InputEvent]
    assert isinstance(events[0], InputEvent)
    assert events[0].action.value is None
    assert "Accessibility.getFullAXTree" not in cdp.asked
    assert page.shots == 0


async def test_inside_an_oauth_flow_nothing_typed_and_no_body_is_kept() -> None:
    session, _, page = _session()
    session._on_request(_navigation(AUTHORIZE))

    await session._on_gesture(None, _gesture("135791"))
    session._on_request(
        _navigation("https://login.idp.example/otc", method="POST", post="otc=135791")
    )
    await session._finish({"requestId": "https://login.idp.example/otc"})
    await session._video_frame(video := _Video())

    events = session.drain().events
    typed = [event for event in events if isinstance(event, InputEvent)]
    calls = [event for event in events if isinstance(event, RequestEvent)]
    assert typed[0].action.value is None
    assert not [event for event in events if isinstance(event, SnapshotEvent)]
    assert page.shots == 0
    assert video.frames == 0
    posted = next(call for call in calls if call.request.method == "POST")
    assert posted.request.request_body is None
    assert posted.request.response_body is None
    assert "135791" not in repr(events)


async def test_the_app_on_the_other_side_of_the_flow_is_captured_as_before() -> None:
    session, _, page = _session()
    session._on_request(_navigation(AUTHORIZE))
    session._on_request(_navigation("https://wms.example/callback?code=c&state=s1"))

    await session._on_gesture(None, _gesture("ACME-4471"))
    await session._video_frame(video := _Video())

    typed = [event for event in session.drain().events if isinstance(event, InputEvent)]
    assert typed[0].action.value == "ACME-4471"
    assert page.shots == 1
    assert video.frames == 1
