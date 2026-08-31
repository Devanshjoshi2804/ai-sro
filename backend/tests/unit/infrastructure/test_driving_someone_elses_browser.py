"""What comes back from an operator's browser, turned into what execution reads.

The point of these: a browser that closed must not look like a control that
moved. One is a laptop; the other is a skill drifting from the system it was
taught on, and counting the first as the second demotes a skill for somebody
going to lunch.
"""

from __future__ import annotations

import asyncio
import base64
import json

import pytest

from sro.application.ports.http import TargetUnreachable
from sro.application.ports.ui import ResolvedLocator, UiUnavailable
from sro.domain.recording.events import ActionKind
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.skill.locator import LocatorStrategy
from sro.infrastructure.agent.drivers import RemoteAgents
from sro.infrastructure.agent.sockets import (
    DEFAULT_TIMEOUT,
    MAX_BUSY_WAIT,
    DeviceSockets,
)
from tests.unit.infrastructure.test_the_channel_to_a_browser import FakeSocket

ACME = TenantId("acme")
LAPTOP = DeviceId("dev-1")

CLICK = (
    ResolvedLocator(strategy=LocatorStrategy.COMPONENT, query="panel#clients button#save"),
    ResolvedLocator(strategy=LocatorStrategy.TEXT, query="Save"),
)


def _wired() -> tuple[RemoteAgents, DeviceSockets, FakeSocket]:
    sockets, socket = DeviceSockets(timeout_s=0.05), FakeSocket()
    sockets.attach(ACME, LAPTOP, socket)
    return RemoteAgents(sockets), sockets, socket


async def _reply(sockets: DeviceSockets, socket: FakeSocket, **fields: object) -> None:
    command = await socket.arrived.get()
    sockets.deliver(json.dumps({"command_id": command["command_id"], **fields}))


async def test_a_gesture_reports_which_locator_actually_worked() -> None:
    agents, sockets, socket = _wired()

    performing = asyncio.create_task(
        agents.ui(ACME, LAPTOP).perform(action=ActionKind.CLICK, locators=CLICK)
    )
    await _reply(
        sockets,
        socket,
        ok=True,
        result={"performed": True, "matched_by": "text", "candidates": 2},
    )
    outcome = await performing

    # Fell through to the weakest locator and matched two controls: the step
    # worked and the recipe is about to break, and both are on the record.
    assert outcome.performed is True
    assert outcome.matched_by is LocatorStrategy.TEXT
    assert outcome.candidates == 2
    assert socket.sent[0]["payload"]["locators"][0]["strategy"] == "component"


async def test_an_unknown_locator_strategy_loses_a_field_not_the_whole_outcome() -> None:
    # The extension is a different build than this deployment's own code.
    # A `matched_by` outside the five known strategies used to raise
    # ValueError uncaught, 500ing a device-bound run instead of just losing
    # this one diagnostic field.
    agents, sockets, socket = _wired()

    performing = asyncio.create_task(
        agents.ui(ACME, LAPTOP).perform(action=ActionKind.CLICK, locators=CLICK)
    )
    await _reply(
        sockets,
        socket,
        ok=True,
        result={"performed": True, "matched_by": "some-future-strategy", "candidates": 1},
    )
    outcome = await performing

    assert outcome.performed is True
    assert outcome.matched_by is None


async def test_a_control_that_moved_is_a_failed_gesture_not_a_missing_browser() -> None:
    agents, sockets, socket = _wired()

    performing = asyncio.create_task(
        agents.ui(ACME, LAPTOP).perform(action=ActionKind.CLICK, locators=CLICK)
    )
    await _reply(sockets, socket, ok=False, error={"kind": "control_not_found", "detail": "gone"})
    outcome = await performing

    assert outcome.performed is False
    # The kind rides along with the sentence. It used to be dropped whenever
    # both were sent, which left the one machine-readable half on the floor.
    assert outcome.detail == "control_not_found: gone"


async def test_the_browser_says_which_kind_of_failure_it_was() -> None:
    """A refusal to steal the operator's screen is not a control it could not find.

    Both arrive as a failed gesture with a sentence attached, and with the kind
    discarded the console had no way to tell a system behaving well from one
    that could not do the work.
    """
    agents, sockets, socket = _wired()

    performing = asyncio.create_task(
        agents.ui(ACME, LAPTOP).perform(action=ActionKind.CLICK, locators=CLICK)
    )
    await _reply(
        sockets,
        socket,
        ok=False,
        error={"kind": "focus_not_permitted", "detail": "the run may not take the screen"},
    )

    # Refusing to take the screen means there was no usable browser for this
    # gesture, so it raises rather than returning a failed one -- and the kind
    # rides in the message, which is the whole point.
    with pytest.raises(UiUnavailable, match="focus_not_permitted"):
        await performing


async def test_a_browser_that_stopped_answering_is_no_browser_at_all() -> None:
    agents, _, _ = _wired()

    with pytest.raises(UiUnavailable):
        await agents.ui(ACME, LAPTOP).perform(action=ActionKind.CLICK, locators=CLICK)


async def test_a_device_with_no_channel_is_unavailable_never_the_server_browser() -> None:
    agents = RemoteAgents(DeviceSockets())

    with pytest.raises(UiUnavailable):
        await agents.ui(ACME, LAPTOP).perform(action=ActionKind.CLICK, locators=CLICK)


async def test_a_call_is_sent_from_the_operators_page_and_its_answer_read_back() -> None:
    agents, sockets, socket = _wired()

    sending = asyncio.create_task(
        agents.http(ACME, LAPTOP).send(
            "POST", "https://wms.acme.test/api/x", headers={"accept": "application/json"}, body="{}"
        )
    )
    await _reply(
        sockets,
        socket,
        ok=True,
        result={"status": 201, "headers": {"content-type": "application/json"}, "body": '{"id":7}'},
    )
    response = await sending

    assert response.succeeded is True
    assert response.status_code == 201
    assert response.text == '{"id":7}'
    assert socket.sent[0]["payload"]["method"] == "POST"


async def test_a_call_whose_answer_never_came_back_is_unreachable_not_a_failure() -> None:
    # The mutation may have arrived. TargetUnreachable is how the executor is
    # told not to retry it without looking.
    agents, _, _ = _wired()

    with pytest.raises(TargetUnreachable):
        await agents.http(ACME, LAPTOP).send(
            "POST", "https://wms.acme.test/x", headers={}, timeout_s=0.05
        )


async def test_a_screen_comes_back_inline_because_it_is_being_looked_at_now() -> None:
    agents, sockets, socket = _wired()

    capturing = asyncio.create_task(agents.ui(ACME, LAPTOP).capture())
    await _reply(
        sockets,
        socket,
        ok=True,
        result={
            "image_base64": base64.b64encode(b"\x89PNG-pretend").decode(),
            "width": 1600,
            "height": 1000,
            "text_digest": "Save: 100,200",
        },
    )
    screen = await capturing

    assert screen.image == b"\x89PNG-pretend"
    assert (screen.width, screen.height) == (1600, 1000)
    assert screen.text_digest == "Save: 100,200"


async def test_binding_a_device_to_a_session_is_the_device_itself() -> None:
    # A device is one browser. There is no second one to point at, and the
    # deployment cannot open one.
    agents, _, _ = _wired()
    driver = agents.ui(ACME, LAPTOP)

    assert driver.for_session("ws://somewhere/else") is driver


async def test_every_command_names_the_system_the_skill_was_taught_on() -> None:
    """An operator's Chrome has a dozen tabs and one of them is the WMS.

    Without being told which, the extension can only drive the frontmost page,
    and a warehouse gesture performed on somebody's email is a real thing that
    happened to a real person. So the origin rides on every command that acts
    on a page, not on the connection: one browser holds one channel and may be
    asked to act for runs against different systems.
    """
    sockets, socket = DeviceSockets(timeout_s=0.05), FakeSocket()
    sockets.attach(ACME, LAPTOP, socket)
    driver = RemoteAgents(sockets).ui(ACME, LAPTOP, "https://wms.example")

    performing = asyncio.create_task(driver.perform(action=ActionKind.CLICK, locators=CLICK))
    await _reply(sockets, socket, ok=True, result={"performed": True})
    await performing

    looking = asyncio.create_task(driver.current_url())
    await _reply(sockets, socket, ok=True, result={"url": "https://wms.example/orders"})
    await looking

    assert [command["payload"]["origin"] for command in socket.sent] == [
        "https://wms.example",
        "https://wms.example",
    ], socket.sent


async def test_a_skill_with_no_recorded_call_names_no_origin() -> None:
    """A skill taught entirely through the interface has no host to read off,
    and a payload carrying `origin: null` would say something false about a
    browser that should fall back to the page in front of the operator."""
    sockets, socket = DeviceSockets(timeout_s=0.05), FakeSocket()
    sockets.attach(ACME, LAPTOP, socket)
    driver = RemoteAgents(sockets).ui(ACME, LAPTOP)

    performing = asyncio.create_task(driver.perform(action=ActionKind.CLICK, locators=CLICK))
    await _reply(sockets, socket, ok=True, result={"performed": True})
    await performing

    assert "origin" not in socket.sent[0]["payload"], socket.sent[0]


async def test_a_run_that_may_take_the_screen_says_so_and_one_that_may_not_says_nothing() -> None:
    """`allow_focus` is sent only when it is true.

    A payload carrying `allow_focus: false` says exactly what one that omits it
    says, and the omission is the safer default to have in a protocol: a
    browser reading a field it does not understand takes nobody's screen.
    """
    sockets, socket = DeviceSockets(timeout_s=0.05), FakeSocket()
    sockets.attach(ACME, LAPTOP, socket)

    allowed = RemoteAgents(sockets).ui(ACME, LAPTOP, "https://wms.example", True)
    performing = asyncio.create_task(allowed.perform(action=ActionKind.CLICK, locators=CLICK))
    await _reply(sockets, socket, ok=True, result={"performed": True})
    await performing

    refused = RemoteAgents(sockets).ui(ACME, LAPTOP, "https://wms.example")
    performing = asyncio.create_task(refused.perform(action=ActionKind.CLICK, locators=CLICK))
    await _reply(sockets, socket, ok=True, result={"performed": True})
    await performing

    assert socket.sent[0]["payload"]["allow_focus"] is True
    assert "allow_focus" not in socket.sent[1]["payload"], socket.sent[1]


async def test_a_busy_window_that_has_passed_is_not_reported_as_held() -> None:
    """A pause carries its own end, and both readers of it must agree.

    `held_for` and the wait that actually holds commands back read the same
    dict. If one of them thought a lapsed pause was still running, a console
    would show "held" over a run that was moving.
    """
    _, sockets, _ = _wired()

    sockets.deliver(json.dumps({"kind": "busy", "for_ms": 5000}), ACME, LAPTOP)
    held = sockets.held_for(ACME, LAPTOP)
    assert held is not None and held > 0

    # A real window, waited out rather than cancelled: there is no "idle"
    # message, so lapsing is the only way a pause ever ends.
    sockets.deliver(json.dumps({"kind": "busy", "for_ms": 10}), ACME, LAPTOP)
    await asyncio.sleep(0.05)
    assert sockets.held_for(ACME, LAPTOP) is None


async def test_being_held_never_promises_longer_than_the_backend_will_wait() -> None:
    """The window the browser asks for is not the window it gets.

    Commands are held for at most a fraction of their own deadline -- a device
    asking for politeness must not be able to veto the work -- so a countdown
    drawn from the raw request would tell the operator to expect a wait twice as
    long as the one that is going to happen.
    """
    _, sockets, _ = _wired()

    sockets.deliver(json.dumps({"kind": "busy", "for_ms": 60_000}), ACME, LAPTOP)

    held = sockets.held_for(ACME, LAPTOP)
    assert held is not None
    assert held <= DEFAULT_TIMEOUT * MAX_BUSY_WAIT
