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
from sro.infrastructure.agent.sockets import DeviceSockets
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
    assert outcome.detail == "gone"


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
