"""Commands sent to an operator's browser, and the answers that come back.

The socket itself is a list here. What is under test is the correlation: one
command, one answer, matched by an id this side mints -- and what happens when
the answer never arrives, arrives late, or is for a browser belonging to
somebody else.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from sro.application.ports.agent import DeviceUnreachable
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.infrastructure.agent.sockets import DeviceSockets

ACME, OTHER = TenantId("acme"), TenantId("other-corp")
LAPTOP = DeviceId("dev-1")


class FakeSocket:
    """A browser that writes down what it was told, and answers when a test
    says so. The queue is what lets a test wait for a command without polling."""

    def __init__(self, *, breaks: bool = False) -> None:
        self.sent: list[dict[str, object]] = []
        self.arrived: asyncio.Queue[dict[str, object]] = asyncio.Queue()
        self.breaks = breaks

    async def send_text(self, text: str) -> None:
        if self.breaks:
            raise ConnectionResetError("the browser went away mid-send")
        command = json.loads(text)
        self.sent.append(command)
        self.arrived.put_nowait(command)


async def _answer(sockets: DeviceSockets, socket: FakeSocket, **fields: object) -> None:
    """Reply to the next command this browser is sent."""
    command = await socket.arrived.get()
    sockets.deliver(json.dumps({"command_id": command["command_id"], **fields}))


async def test_a_command_and_its_answer_are_matched_by_the_id_we_minted() -> None:
    sockets, socket = DeviceSockets(), FakeSocket()
    sockets.attach(ACME, LAPTOP, socket)

    sending = asyncio.create_task(
        sockets.send(ACME, LAPTOP, kind="ui.perform", payload={"action": "click"})
    )
    await _answer(sockets, socket, ok=True, result={"performed": True})
    answer = await sending

    assert answer.ok is True
    assert answer.result["performed"] is True
    assert socket.sent[0]["kind"] == "ui.perform"
    assert str(socket.sent[0]["command_id"]).startswith("cmd_")


async def test_a_browser_that_is_not_connected_is_not_a_browser_that_refuses() -> None:
    with pytest.raises(DeviceUnreachable):
        await DeviceSockets().send(ACME, LAPTOP, kind="ui.url", payload={})


async def test_another_tenants_device_is_not_there_rather_than_forbidden() -> None:
    sockets = DeviceSockets()
    sockets.attach(ACME, LAPTOP, FakeSocket())

    with pytest.raises(DeviceUnreachable):
        await sockets.send(OTHER, LAPTOP, kind="ui.url", payload={})

    assert sockets.online(OTHER) == ()
    assert sockets.online(ACME) == (LAPTOP,)


async def test_a_browser_that_never_answers_times_out_rather_than_hanging() -> None:
    sockets, socket = DeviceSockets(timeout_s=0.01), FakeSocket()
    sockets.attach(ACME, LAPTOP, socket)

    answer = await sockets.send(ACME, LAPTOP, kind="ui.perform", payload={})

    assert answer.ok is False
    assert answer.error_kind == "timeout"


async def test_an_answer_that_arrives_after_the_timeout_is_dropped() -> None:
    # The run has already recorded that step as failed. A late success would
    # make it succeed underneath a record that says otherwise.
    sockets, socket = DeviceSockets(timeout_s=0.01), FakeSocket()
    sockets.attach(ACME, LAPTOP, socket)

    await sockets.send(ACME, LAPTOP, kind="ui.perform", payload={})
    stale = await socket.arrived.get()
    sockets.deliver(json.dumps({"command_id": stale["command_id"], "ok": True}))

    second = asyncio.create_task(sockets.send(ACME, LAPTOP, kind="ui.perform", payload={}))
    await _answer(sockets, socket, ok=True, result={"performed": True})
    assert (await second).result["performed"] is True


async def test_a_reconnect_replaces_the_socket_and_a_late_close_does_not_unregister_it() -> None:
    sockets, first, second = DeviceSockets(), FakeSocket(), FakeSocket()
    sockets.attach(ACME, LAPTOP, first)
    sockets.attach(ACME, LAPTOP, second)

    sockets.detach(ACME, LAPTOP, first)

    assert sockets.online(ACME) == (LAPTOP,)


async def test_a_socket_that_breaks_while_sending_is_unreachable() -> None:
    sockets = DeviceSockets()
    sockets.attach(ACME, LAPTOP, FakeSocket(breaks=True))

    with pytest.raises(DeviceUnreachable):
        await sockets.send(ACME, LAPTOP, kind="ui.perform", payload={})


async def test_nonsense_from_a_browser_does_not_take_the_channel_down() -> None:
    sockets = DeviceSockets()

    sockets.deliver("not json at all")
    sockets.deliver(json.dumps(["a list"]))
    sockets.deliver(json.dumps({"command_id": "cmd_nobody_waited_for", "ok": True}))


async def test_a_busy_browser_has_its_command_held_back() -> None:
    """A replay landing mid-keystroke is a run and a person fighting over one
    form. The browser says it is busy; the command waits."""
    sockets, socket = DeviceSockets(timeout_s=1.0), FakeSocket()
    sockets.attach(ACME, LAPTOP, socket)
    sockets.deliver(json.dumps({"kind": "busy", "for_ms": 200}), ACME, LAPTOP)

    started = asyncio.get_running_loop().time()
    sending = asyncio.create_task(
        sockets.send(ACME, LAPTOP, kind="ui.url", payload={}, timeout_s=1.0)
    )
    await _answer(sockets, socket, ok=True, result={"url": "https://wms.example/"})
    answer = await sending

    assert answer.ok, "the command was dropped rather than delayed"
    assert asyncio.get_running_loop().time() - started >= 0.15, (
        "the command went straight out while the operator was typing"
    )


async def test_busy_may_delay_a_command_but_never_veto_it() -> None:
    """Bounded by half the command's own deadline. A device that could hold
    work back indefinitely is a device deciding whether work happens at all --
    and a browser that says it is busy and then closes its laptop would be
    exactly that."""
    sockets, socket = DeviceSockets(timeout_s=1.0), FakeSocket()
    sockets.attach(ACME, LAPTOP, socket)
    sockets.deliver(json.dumps({"kind": "busy", "for_ms": 30_000}), ACME, LAPTOP)

    started = asyncio.get_running_loop().time()
    sending = asyncio.create_task(
        sockets.send(ACME, LAPTOP, kind="ui.url", payload={}, timeout_s=0.4)
    )
    await _answer(sockets, socket, ok=True, result={"url": "https://wms.example/"})
    assert (await sending).ok

    waited = asyncio.get_running_loop().time() - started
    assert 0.15 <= waited < 0.35, f"waited {waited:.2f}s, which is not half of a 0.4s deadline"


async def test_a_browser_cannot_say_it_is_some_other_device() -> None:
    """The device a message is about comes from the router, which authenticated
    it, and never from the message. Otherwise one operator's browser could
    silence another's by claiming to be busy on its behalf."""
    sockets, socket = DeviceSockets(timeout_s=1.0), FakeSocket()
    sockets.attach(ACME, LAPTOP, socket)
    # No tenant or device named: an unsolicited message arriving through a path
    # that cannot say who sent it changes nothing.
    sockets.deliver(json.dumps({"kind": "busy", "for_ms": 30_000, "device_id": "dev-1"}))

    started = asyncio.get_running_loop().time()
    sending = asyncio.create_task(
        sockets.send(ACME, LAPTOP, kind="ui.url", payload={}, timeout_s=1.0)
    )
    await _answer(sockets, socket, ok=True, result={"url": "https://wms.example/"})
    assert (await sending).ok
    assert asyncio.get_running_loop().time() - started < 0.1, "an unattributed message was believed"
