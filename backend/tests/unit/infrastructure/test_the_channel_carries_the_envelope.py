"""The ``Channel`` port, over the sockets the API worker already holds.

``test_the_channel_to_a_browser.py`` covers the correlation, the reconnects and
the busy window; this file covers only what the port adds on top of them -- the
deadline it can say, the browser a tenant revoked, and the fact that a mined
workflow's own envelope reaches the wire unreshaped.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping

import pytest

from sro.application.ports.agent import DeviceUnreachable
from sro.application.ports.channel import Channel, Reply
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.infrastructure.agent.channel import SocketChannel
from sro.infrastructure.agent.sockets import DeviceSockets
from tests.unit.fakes import FakeChannel
from tests.unit.infrastructure.test_the_channel_to_a_browser import FakeSocket

ACME = TenantId("acme")
LAPTOP = DeviceId("dev-1")


async def _round_trip(
    channel: Channel,
    sockets: DeviceSockets,
    socket: FakeSocket,
    *,
    kind: str,
    payload: Mapping[str, object],
    run_id: str | None = None,
    deadline_s: float | None = None,
) -> Reply:
    """Send, answer the command the browser was handed, and give back the reply."""
    sending = asyncio.create_task(
        channel.send(ACME, LAPTOP, kind=kind, payload=payload, run_id=run_id, deadline_s=deadline_s)
    )
    command = await socket.arrived.get()
    sockets.deliver(json.dumps({"command_id": command["command_id"], "ok": True, "result": {}}))
    return await sending


async def test_an_explicit_deadline_is_honoured_and_a_non_positive_one_never_ships() -> None:
    """`deadline_s or the default` could not say a short one, and shipped a
    negative as a negative `deadline_ms`."""
    sockets, socket = DeviceSockets(timeout_s=1.0), FakeSocket()
    sockets.attach(ACME, LAPTOP, socket)
    channel = SocketChannel(sockets)

    await _round_trip(channel, sockets, socket, kind="ui.url", payload={})
    assert socket.sent[0]["deadline_ms"] == 1000, "None means the channel's own deadline"

    await _round_trip(channel, sockets, socket, kind="ui.url", payload={}, deadline_s=0.05)
    assert socket.sent[1]["deadline_ms"] == 50

    refused = await channel.send(ACME, LAPTOP, kind="ui.url", payload={}, deadline_s=0)

    assert not refused.ok and refused.error_kind == "timeout"
    assert len(socket.sent) == 2, "nothing went on the wire for a deadline it could not meet"


async def test_the_fake_channel_answers_by_kind_and_remembers_what_was_sent() -> None:
    fake = FakeChannel({"ui.url": [Reply(ok=True, result={"url": "https://a/x"})]})

    answer = await fake.send(ACME, LAPTOP, kind="ui.url", payload={"origin": "https://a"})

    assert answer.result == {"url": "https://a/x"}
    assert fake.sent[0]["kind"] == "ui.url"
    assert fake.sent[0]["payload"] == {"origin": "https://a"}

    unscripted = await fake.send(ACME, LAPTOP, kind="screenshot", payload={})

    assert not unscripted.ok and unscripted.error_kind == "not_actionable"


async def test_a_revoked_browser_is_dropped_and_reads_as_offline() -> None:
    """A tenant revoking a browser's token. One that still read as connected
    would be an audit line nobody could trust."""
    sockets = DeviceSockets()
    sockets.attach(ACME, LAPTOP, FakeSocket())
    channel: Channel = SocketChannel(sockets)
    assert channel.online(ACME) == (LAPTOP,)

    assert channel.drop(ACME, LAPTOP) is True

    assert channel.online(ACME) == ()
    with pytest.raises(DeviceUnreachable):
        await channel.send(ACME, LAPTOP, kind="ui.url", payload={})
    assert channel.drop(ACME, LAPTOP) is False, "a browser can only be revoked once"


async def test_the_channel_port_carries_the_kinds_a_run_sends() -> None:
    """A mined workflow sends the envelope the demonstration recorded, so the
    port reshapes none of it -- not the `origin` on a url, not the `inline` on a
    screenshot, and not the two kinds only a run sends."""
    sockets, socket = DeviceSockets(timeout_s=1.0), FakeSocket()
    sockets.attach(ACME, LAPTOP, socket)
    channel = SocketChannel(sockets)

    envelopes: list[tuple[str, dict[str, object]]] = [
        ("ui.url", {"origin": "https://wms.example"}),
        ("screenshot", {"inline": True, "origin": "https://wms.example", "allow_focus": True}),
        ("ui.perform", {"action": "click", "locators": [{"strategy": "role", "query": "Save"}]}),
        ("ui.perform_at", {"action": "click", "x": 12, "y": 34}),
        ("http.send", {"method": "GET", "url": "https://wms.example/o/1", "headers": {}}),
        ("navigate", {"url": "https://wms.example/orders"}),
        ("abort", {"run_id": "run-7"}),
    ]
    for kind, payload in envelopes:
        await _round_trip(
            channel, sockets, socket, kind=kind, payload=payload, run_id="run-7", deadline_s=0.5
        )

    assert [(sent["kind"], sent["payload"]) for sent in socket.sent] == envelopes
    assert {str(sent["run_id"]) for sent in socket.sent} == {"run-7"}
    assert {int(str(sent["deadline_ms"])) for sent in socket.sent} == {500}
