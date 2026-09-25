"""Capture against a live Steel browser.

The mapping functions are unit tested; this proves the part that cannot be:
that CDP actually delivers what the adapter subscribes to, that the injected
recorder reaches the binding, and that a click produces a frame carrying the
call it caused.

Skipped when Steel is not running.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import httpx
import pytest
from playwright.async_api import async_playwright

from sro.application.capture.assemble import assemble_frames
from sro.application.capture.events import InputEvent, RequestEvent
from sro.domain.recording.network import InitiatorKind
from sro.infrastructure.steel.capture import CaptureSession
from sro.infrastructure.steel.client import SteelClient
from tests.unit.fakes import FakeBlobStore

STEEL_URL = "http://localhost:3010"
CDP_URL = "http://localhost:9223"

PAGE = """
<!doctype html>
<title>Release wave</title>
<form onsubmit="return false">
  <label for="wave">Wave</label>
  <input id="wave" name="wave" value="W-1001">
  <button id="release" type="button" onclick="send()">Release</button>
</form>
<script>
  function send() {
    fetch('/api/waves/W-1001/release', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Facility': 'DC01' },
      body: JSON.stringify({ wave: document.getElementById('wave').value }),
    });
  }
</script>
"""


@pytest.fixture
async def steel() -> AsyncIterator[SteelClient]:
    client = SteelClient(STEEL_URL, CDP_URL)
    try:
        if not await client.health():
            pytest.skip("Steel is not running; `make up` first")
    except Exception as exc:
        pytest.skip(f"Steel is not reachable: {exc}")
    async with client:
        yield client


async def test_a_click_becomes_a_frame_carrying_the_call_it_caused(
    steel: SteelClient,
) -> None:
    session = await steel.open()
    capture = CaptureSession(blob_store=FakeBlobStore(), key_prefix="acme/rec-live")

    try:
        await capture.attach(session.debugger_url)
        page = capture.page
        # Served from a real origin rather than set_content: a relative fetch on
        # about:blank has nothing to resolve against, so the call under test
        # would never leave the page.
        await page.route(
            "https://wms.test/",
            lambda route: route.fulfill(status=200, content_type="text/html", body=PAGE),
        )
        await page.route(
            "**/api/waves/**",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body='{"status": "released", "wave_id": "W-1001"}',
            ),
        )
        await page.goto("https://wms.test/")
        await page.click("#release")
        await page.wait_for_timeout(1500)

        batch = capture.drain()
    finally:
        await capture.detach()
        await steel.close(session.id)

    inputs = [e for e in batch.events if isinstance(e, InputEvent)]
    requests = [e for e in batch.events if isinstance(e, RequestEvent)]

    assert inputs, "the injected recorder never reached the binding"
    assert inputs[0].action.target is not None
    assert inputs[0].action.target.css_path
    assert inputs[0].action.target.accessible_name == "Release"

    released = next((r for r in requests if "release" in r.request.url), None)
    assert released is not None, "the POST the click caused was not captured"
    assert released.request.method == "POST"
    assert released.request.request_headers.get("X-Facility") == "DC01"
    assert released.request.initiator is not None
    assert released.request.initiator.kind is InitiatorKind.SCRIPT
    assert released.request.response_text == '{"status": "released", "wave_id": "W-1001"}'

    frames = assemble_frames(list(batch.events))
    assert frames.frames, "events did not assemble into a frame"
    primary = frames.frames[0].primary_request
    assert primary is not None
    assert "release" in primary.url


async def test_a_screenshot_is_written_for_each_gesture(steel: SteelClient) -> None:
    blobs = FakeBlobStore()
    session = await steel.open()
    capture = CaptureSession(blob_store=blobs, key_prefix="acme/rec-shots")

    try:
        await capture.attach(session.debugger_url)
        await capture.page.route(
            "https://wms.test/",
            lambda route: route.fulfill(status=200, content_type="text/html", body=PAGE),
        )
        await capture.page.goto("https://wms.test/")
        await capture.page.click("#release")
        await capture.page.wait_for_timeout(1000)
        batch = capture.drain()
    finally:
        await capture.detach()
        await steel.close(session.id)

    assert batch.artifacts
    assert blobs.objects
    assert all(artifact.size_bytes > 0 for artifact in batch.artifacts)


async def test_capture_does_not_starve_the_operator_s_live_view(steel: SteelClient) -> None:
    """Chrome allows one screencast consumer per page, and the newest one wins.

    Steel's live view is a screencast consumer, so a capture session that starts
    its own screencast silently freezes the browser the operator is driving --
    the teaching session still records, and the human can no longer see what
    they are doing. Video is therefore sampled with screenshots instead.
    """
    session = await steel.open()
    capture = CaptureSession(
        blob_store=FakeBlobStore(), key_prefix="acme/rec-live-view", video=True
    )

    async with async_playwright() as pw:
        viewer_browser = await pw.chromium.connect_over_cdp(session.debugger_url)
        page = viewer_browser.contexts[0].pages[0]
        viewer = await viewer_browser.contexts[0].new_cdp_session(page)
        frames: list[object] = []
        acks: set[asyncio.Task[object]] = set()

        def _on_frame(event: dict[str, object]) -> None:
            # Chrome sends at most one screencast frame ahead of the last ack:
            # without acking, this stand-in viewer stalls after a couple of
            # frames regardless of how long the test waits, which reads as
            # "capture starved the live view" for a reason that has nothing to
            # do with capture.
            frames.append(1)
            task = asyncio.create_task(
                viewer.send("Page.screencastFrameAck", {"sessionId": event["sessionId"]})
            )
            acks.add(task)
            task.add_done_callback(acks.discard)

        viewer.on("Page.screencastFrame", _on_frame)
        await viewer.send("Page.enable")
        await viewer.send("Page.startScreencast", {"format": "jpeg", "quality": 40})

        await page.route(
            "https://wms.test/",
            lambda route: route.fulfill(status=200, content_type="text/html", body=PAGE),
        )
        await page.goto("https://wms.test/")
        await page.wait_for_timeout(600)
        before = len(frames)

        try:
            await capture.attach(session.debugger_url)
            await capture.page.wait_for_timeout(400)
            await page.click("#release")
            await page.wait_for_timeout(1500)
            recorded = capture.stop_video()
        finally:
            await capture.detach()
            await viewer_browser.close()
            await steel.close(session.id)

    assert before > 0, "the stand-in live view never worked, so the test proves nothing"
    assert len(frames) > before, "capture starved the live view of screencast frames"
    assert recorded is not None and recorded.frame_count > 0, "no video was recorded"
    recorded.path.unlink(missing_ok=True)


async def test_a_request_in_flight_when_capture_ends_is_still_recorded(
    steel: SteelClient,
) -> None:
    """The driver disconnecting mid-call must not erase the call.

    This is how a demonstration loses its most important step: the operator
    closes the tab the moment the WMS confirms, and the confirming POST is the
    one the skill is built from.
    """
    session = await steel.open()
    capture = CaptureSession(blob_store=FakeBlobStore(), key_prefix="acme/rec-inflight")

    try:
        await capture.attach(session.debugger_url)
        page = capture.page
        await page.route(
            "https://wms.test/",
            lambda route: route.fulfill(status=200, content_type="text/html", body=PAGE),
        )
        # Never fulfilled: the exchange is still open when capture ends.
        await page.route("**/api/waves/**", lambda route: None)
        await page.goto("https://wms.test/")
        await page.click("#release")
        await page.wait_for_timeout(500)

        capture.flush_incomplete()
        batch = capture.drain()
    finally:
        await capture.detach()
        await steel.close(session.id)

    requests = [e for e in batch.events if isinstance(e, RequestEvent)]
    released = next((r for r in requests if "release" in r.request.url), None)

    assert released is not None, "an unfinished exchange was discarded"
    assert released.request.method == "POST"
    assert released.request.request_headers.get("X-Facility") == "DC01"
    assert released.request.failure_reason == "capture ended before the response completed"


async def test_a_demonstration_is_recorded_as_a_playable_video(steel: SteelClient) -> None:
    """The reviewer watches this. It has to be a real file, not a pile of JPEGs."""
    import av

    session = await steel.open()
    capture = CaptureSession(blob_store=FakeBlobStore(), key_prefix="acme/rec-video")

    try:
        await capture.attach(session.debugger_url)
        page = capture.page
        await page.route(
            "https://wms.test/",
            lambda route: route.fulfill(status=200, content_type="text/html", body=PAGE),
        )
        await page.goto("https://wms.test/")
        # Move the page around so the screencast has something to encode.
        for value in ("W-1", "W-2", "W-3"):
            await page.fill("#wave", value)
            await page.wait_for_timeout(300)
        await page.click("#release")
        await page.wait_for_timeout(800)

        recorded = capture.stop_video()
    finally:
        await capture.detach()
        await steel.close(session.id)

    assert recorded is not None, "no video was produced"
    assert recorded.frame_count > 1
    assert recorded.path.stat().st_size > 0

    with av.open(str(recorded.path)) as container:
        stream = container.streams.video[0]
        assert stream.codec_context.name == "h264"
        assert stream.width > 0 and stream.height > 0
        # Even dimensions, or the file will not decode in a browser.
        assert stream.width % 2 == 0 and stream.height % 2 == 0
        decoded = sum(1 for _ in container.decode(video=0))

    # Not exact parity with frame_count: the screencast changes resolution when
    # the page does, and the encoder resolves that its own way. What matters is
    # that the file plays and covers the demonstration.
    assert 1 < decoded <= recorded.frame_count
    assert recorded.duration_ms > 0
    recorded.path.unlink(missing_ok=True)


LOGIN_PAGE = """
<!doctype html><title>WMS login</title>
<form id="login" onsubmit="return false">
  <input id="user" name="username" value="">
  <input id="pw" type="password" name="password" value="">
  <button id="go" type="button" onclick="send()">Sign in</button>
</form>
<script>
function send() {
  fetch('/api/session', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      username: document.getElementById('user').value,
      password: document.getElementById('pw').value,
      facility: 'DC01',
    }),
  });
}
</script>"""


async def test_a_password_never_reaches_the_recording(steel: SteelClient) -> None:
    """The one thing capture does not keep.

    Teaching a WMS task starts with logging in. Everything else in the session
    is evidence; the password is a key to the customer's system, and an evidence
    store holding keys is a credential store nobody agreed to run.
    """
    session = await steel.open()
    capture = CaptureSession(blob_store=FakeBlobStore(), key_prefix="acme/rec-login", video=False)

    try:
        await capture.attach(session.debugger_url)
        page = capture.page
        await page.route(
            "https://wms.test/login",
            lambda route: route.fulfill(status=200, content_type="text/html", body=LOGIN_PAGE),
        )
        await page.route(
            "**/api/session",
            lambda route: route.fulfill(
                status=200, content_type="application/json", body='{"ok": true}'
            ),
        )
        await page.goto("https://wms.test/login")
        await page.fill("#user", "clerk")
        await page.fill("#pw", "hunter2-very-secret")
        await page.click("#go")
        await page.wait_for_timeout(1200)

        capture.flush_incomplete()
        batch = capture.drain()
    finally:
        await capture.detach()
        await steel.close(session.id)

    everything = repr(batch.events)
    assert "hunter2-very-secret" not in everything, "the password reached the evidence plane"
    # The username is ordinary business data and must survive.
    assert "clerk" in everything

    typed = [event for event in batch.events if isinstance(event, InputEvent)]
    secret_inputs = [event for event in typed if event.action.secret]
    assert secret_inputs, "the password field was not recognised as a credential"
    assert all(event.action.value is None for event in secret_inputs)

    login = next(
        (
            event
            for event in batch.events
            if isinstance(event, RequestEvent) and "api/session" in event.request.url
        ),
        None,
    )
    assert login is not None and login.request.request_body is not None
    assert "password" in login.request.request_body.redacted_fields
    assert "clerk" in (login.request.request_body.text or "")


async def test_the_session_api_shape_is_what_the_adapter_expects(steel: SteelClient) -> None:
    session = await steel.open()
    try:
        assert session.live_view_url.startswith(STEEL_URL)
        async with httpx.AsyncClient() as http:
            listed = (await http.get(f"{STEEL_URL}/v1/sessions")).json()
        assert any(row["id"] == session.id.value for row in listed["sessions"])
    finally:
        await steel.close(session.id)

    # Releasing twice must not raise: crash recovery calls close on sessions
    # the provider may already have reaped.
    await steel.close(session.id)
