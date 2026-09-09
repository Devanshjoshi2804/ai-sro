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
    exactly that.

    This one fails under heavy contention perhaps once in many full-suite runs,
    and the bound below is NOT the reason. Measured 2026-09-09 on a machine busy
    with the full suite, Docker and a second agent, 60 runs of exactly this
    sequence: min 0.2004, median 0.2015, mean 0.2033, max 0.2342 -- against an
    upper bound of 0.35, so the worst observed run still had 0.116s of slack and
    nothing came near either edge.

    So a failure here means the event loop was starved past 0.115s beyond
    typical, which is a statement about the machine and not about `DeviceSockets`.
    Re-run it before believing it.

    The bound stays as it is, deliberately. `< 0.35` is what enforces the "half
    the deadline" half of this test's own first sentence; widening it to quiet a
    rare flake would delete the guarantee to protect the schedule."""
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


@pytest.mark.parametrize("for_ms", [float("nan"), float("inf"), -5000, "soon", True])
async def test_a_busy_window_that_is_not_a_duration_is_not_believed(for_ms: object) -> None:
    """`json.loads` accepts a bare `NaN`, and it passes every isinstance check
    a duration would. Stored, `asyncio.sleep(nan)` raises -- and because the
    entry was never cleared, every later command to that device raised the same
    way. One malformed frame from one browser took it offline until the process
    restarted, so what arrives here is checked for being a real number rather
    than for having a numeric type.
    """
    sockets, socket = DeviceSockets(timeout_s=1.0), FakeSocket()
    sockets.attach(ACME, LAPTOP, socket)
    sockets.deliver(json.dumps({"kind": "busy", "for_ms": for_ms}), ACME, LAPTOP)

    started = asyncio.get_running_loop().time()
    sending = asyncio.create_task(
        sockets.send(ACME, LAPTOP, kind="ui.url", payload={}, timeout_s=1.0)
    )
    await _answer(sockets, socket, ok=True, result={"url": "https://wms.example/"})
    assert (await sending).ok, "the command did not survive a nonsense busy window"
    assert asyncio.get_running_loop().time() - started < 0.4, (
        "a browser that sent nonsense was believed anyway"
    )


async def test_a_busy_with_no_window_of_its_own_gets_the_documented_default() -> None:
    """Absent is not nonsense: the protocol says a `busy` without `for_ms` asks
    for the default, and the message still means the operator is working."""
    sockets, socket = DeviceSockets(timeout_s=1.0), FakeSocket()
    sockets.attach(ACME, LAPTOP, socket)
    sockets.deliver(json.dumps({"kind": "busy"}), ACME, LAPTOP)

    started = asyncio.get_running_loop().time()
    sending = asyncio.create_task(
        sockets.send(ACME, LAPTOP, kind="ui.url", payload={}, timeout_s=0.4)
    )
    await _answer(sockets, socket, ok=True, result={"url": "https://wms.example/"})
    assert (await sending).ok
    assert asyncio.get_running_loop().time() - started >= 0.15, "the default window was not applied"


async def test_a_browser_that_reconnects_mid_wait_is_sent_the_command_anyway() -> None:
    """The socket is resolved after the busy wait, not before it.

    That wait is seconds long, and a lid or a wifi hop inside it has the
    extension re-dial. Holding the socket from before meant sending down a dead
    one and failing the run as an unreachable device -- against a browser that
    was connected the whole time.
    """
    sockets = DeviceSockets(timeout_s=1.0)
    stale, live = FakeSocket(breaks=True), FakeSocket()
    sockets.attach(ACME, LAPTOP, stale)
    sockets.deliver(json.dumps({"kind": "busy", "for_ms": 150}), ACME, LAPTOP)

    sending = asyncio.create_task(
        sockets.send(ACME, LAPTOP, kind="ui.url", payload={}, timeout_s=1.0)
    )
    await asyncio.sleep(0.05)
    sockets.attach(ACME, LAPTOP, live)  # the browser came back while we waited

    await _answer(sockets, live, ok=True, result={"url": "https://wms.example/"})
    assert (await sending).ok
    assert not stale.sent, "the command went down the socket that had already gone"


async def test_a_browser_that_disconnects_is_not_still_busy() -> None:
    """Otherwise the entry sits in memory for the life of the process, and a
    device that closed its laptop mid-sentence is politely waited on."""
    sockets, socket = DeviceSockets(timeout_s=1.0), FakeSocket()
    sockets.attach(ACME, LAPTOP, socket)
    sockets.deliver(json.dumps({"kind": "busy", "for_ms": 30_000}), ACME, LAPTOP)
    sockets.detach(ACME, LAPTOP, socket)

    back = FakeSocket()
    sockets.attach(ACME, LAPTOP, back)
    started = asyncio.get_running_loop().time()
    sending = asyncio.create_task(
        sockets.send(ACME, LAPTOP, kind="ui.url", payload={}, timeout_s=1.0)
    )
    await _answer(sockets, back, ok=True, result={"url": "https://wms.example/"})
    assert (await sending).ok
    assert asyncio.get_running_loop().time() - started < 0.2, (
        "a browser that had gone away was still being waited on"
    )
