import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from rig.api import build_app
from rig.channel import Answer, DeviceChannel, DeviceUnreachable, FakeChannel
from rig.models import FakeAsker
from rig.store import Store

TOKEN = "test-token"


class _Socket:
    """A list, which is all the channel needs a socket to be."""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_text(self, text: str) -> None:
        self.sent.append(json.loads(text))


async def test_a_command_is_answered_once_by_id() -> None:
    channel = DeviceChannel(deadline_s=1.0)
    socket = _Socket()
    channel.attach("dev_1", socket)

    task = asyncio.create_task(
        channel.send("dev_1", kind="ui.url", payload={"origin": "https://a"})
    )
    await asyncio.sleep(0)
    envelope = socket.sent[0]
    assert envelope["kind"] == "ui.url"
    assert envelope["payload"] == {"origin": "https://a"}
    assert envelope["deadline_ms"] == 1000
    channel.deliver(
        json.dumps(
            {"command_id": envelope["command_id"], "ok": True, "result": {"url": "https://a/x"}}
        ),
        "dev_1",
    )

    answer = await task
    assert answer.ok and answer.result == {"url": "https://a/x"}


async def test_an_error_keeps_its_kind_and_detail() -> None:
    channel = DeviceChannel(deadline_s=1.0)
    socket = _Socket()
    channel.attach("dev_1", socket)
    task = asyncio.create_task(channel.send("dev_1", kind="ui.perform", payload={}))
    await asyncio.sleep(0)
    cid = socket.sent[0]["command_id"]
    channel.deliver(
        json.dumps(
            {
                "command_id": cid,
                "ok": False,
                "error": {"kind": "control_not_found", "detail": "no visible match"},
            }
        ),
        "dev_1",
    )

    answer = await task
    assert not answer.ok
    assert answer.error_kind == "control_not_found"
    assert answer.detail == "control_not_found: no visible match"


async def test_no_answer_by_the_deadline_is_a_timeout_not_a_hang() -> None:
    channel = DeviceChannel(deadline_s=0.05)
    channel.attach("dev_1", _Socket())

    answer = await channel.send("dev_1", kind="ui.url", payload={})

    assert not answer.ok and answer.error_kind == "timeout"


async def test_a_late_answer_is_dropped_not_applied() -> None:
    """A run that recorded the step as failed must not have it succeed underneath."""
    channel = DeviceChannel(deadline_s=0.05)
    socket = _Socket()
    channel.attach("dev_1", socket)
    await channel.send("dev_1", kind="ui.url", payload={})
    cid = socket.sent[0]["command_id"]

    channel.deliver(
        json.dumps({"command_id": cid, "ok": True, "result": {}}), "dev_1"
    )  # must not raise


async def test_a_device_with_no_socket_is_unreachable() -> None:
    channel = DeviceChannel()
    with pytest.raises(DeviceUnreachable):
        await channel.send("dev_nobody", kind="ui.url", payload={})


async def test_busy_holds_a_command_but_cannot_veto_it() -> None:
    """A device asking for politeness must not be able to stop the work."""
    channel = DeviceChannel(deadline_s=0.2)
    socket = _Socket()
    channel.attach("dev_1", socket)
    channel.deliver(json.dumps({"kind": "busy", "for_ms": 60_000}), "dev_1")

    loop = asyncio.get_running_loop()
    started = loop.time()
    task = asyncio.create_task(channel.send("dev_1", kind="ui.url", payload={}))
    await asyncio.sleep(0.15)
    assert socket.sent, "sent within half the deadline, however long the device asked for"
    assert loop.time() - started < 0.2
    channel.deliver(
        json.dumps({"command_id": socket.sent[0]["command_id"], "ok": True, "result": {}}), "dev_1"
    )
    await task


async def test_a_reconnect_replaces_the_socket_and_a_stale_detach_does_not() -> None:
    channel = DeviceChannel()
    old, new = _Socket(), _Socket()
    channel.attach("dev_1", old)
    channel.attach("dev_1", new)
    channel.detach("dev_1", old)

    assert channel.online() == ["dev_1"], "the live socket survived the stale close"


async def test_unsolicited_messages_are_dropped_on_the_floor() -> None:
    channel = DeviceChannel()
    channel.attach("dev_1", _Socket())
    for raw in ('{"kind":"hello","tabs":3}', '{"kind":"ping"}', "not json", "[]"):
        channel.deliver(raw, "dev_1")  # nothing to assert but that nothing raised


def test_the_route_accepts_the_bearer_subprotocol_and_refuses_the_rest(tmp_path) -> None:
    store = Store(tmp_path / "rig.db")
    store.migrate()
    app = build_app(
        store=store, asker=FakeAsker(), token=TOKEN, tenant="acme", read_on_ingest=False
    )
    client = TestClient(app)

    with client.websocket_connect(
        "/v1/agents/dev_1/commands", subprotocols=["bearer", TOKEN]
    ) as ws:
        ws.send_text(json.dumps({"kind": "hello", "extension_version": "0.1.0", "tabs": 1}))
        assert app.state.channel.online() == ["dev_1"]
    assert app.state.channel.online() == []

    # Starlette raises its own disconnect on a refused handshake, hence B017.
    with (
        pytest.raises(Exception),  # noqa: B017
        client.websocket_connect("/v1/agents/dev_1/commands", subprotocols=["bearer", "wrong"]),
    ):
        pass


async def test_the_fake_channel_answers_by_kind_and_remembers_what_was_sent() -> None:
    fake = FakeChannel({"ui.url": [Answer(ok=True, result={"url": "https://a/x"})]})

    answer = await fake.send("dev_test", kind="ui.url", payload={"origin": "https://a"})

    assert answer.result == {"url": "https://a/x"}
    assert fake.sent[0]["kind"] == "ui.url"
    unscripted = await fake.send("dev_test", kind="screenshot", payload={})
    assert not unscripted.ok and unscripted.error_kind == "not_actionable"


async def test_an_explicit_deadline_is_honoured_and_a_non_positive_one_never_ships() -> None:
    """`deadline_s or self._deadline` could not say 0, and shipped a negative."""
    channel = DeviceChannel(deadline_s=1.0)
    socket = _Socket()
    channel.attach("dev_1", socket)

    task = asyncio.create_task(channel.send("dev_1", kind="ui.url", payload={}))
    await asyncio.sleep(0)
    assert socket.sent[0]["deadline_ms"] == 1000, "None means the channel's own deadline"
    channel.deliver(
        json.dumps({"command_id": socket.sent[0]["command_id"], "ok": True, "result": {}}), "dev_1"
    )
    await task

    short = asyncio.create_task(channel.send("dev_1", kind="ui.url", payload={}, deadline_s=0.05))
    await asyncio.sleep(0)
    assert socket.sent[1]["deadline_ms"] == 50
    channel.deliver(
        json.dumps({"command_id": socket.sent[1]["command_id"], "ok": True, "result": {}}), "dev_1"
    )
    await short

    answer = await channel.send("dev_1", kind="ui.url", payload={}, deadline_s=0)

    assert not answer.ok and answer.error_kind == "timeout"
    assert len(socket.sent) == 2, "nothing went on the wire for a deadline it could not meet"
