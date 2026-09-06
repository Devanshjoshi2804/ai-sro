import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from rig.api import build_app
from rig.devices import PREFIX, holder, issue, revoke
from rig.models import FakeAsker
from rig.store import Store

TOKEN = "tenant-secret"


def _store(tmp_path: Path) -> Store:
    store = Store(tmp_path / "rig.db")
    store.migrate()
    return store


def _client(store: Store) -> TestClient:
    return TestClient(
        build_app(store=store, asker=FakeAsker(), token=TOKEN, tenant="acme", read_on_ingest=False)
    )


def test_a_token_is_issued_held_as_a_hash_and_revocable(tmp_path: Path) -> None:
    store = _store(tmp_path)
    token = issue(store, "dev_1")
    assert token.startswith(PREFIX) and len(token) == len(PREFIX) + 48
    assert holder(store, token) == "dev_1"
    stored = store.query("SELECT token_hash FROM device_tokens")[0]["token_hash"]
    assert token not in stored and len(stored) == 64, "the store holds a hash, never the token"
    assert holder(store, "dev_nope") is None and holder(store, TOKEN) is None
    assert revoke(store, "dev_1") is True and revoke(store, "dev_1") is False
    assert holder(store, token) is None, "a revoked token belongs to nobody"


def test_a_fresh_issue_retires_the_earlier_token(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = issue(store, "dev_1")
    second = issue(store, "dev_1")
    assert holder(store, first) is None and holder(store, second) == "dev_1"


def test_the_tenant_registers_a_browser_and_the_browser_then_speaks_for_itself(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    client = _client(store)
    tenant = {"Authorization": f"Bearer {TOKEN}"}

    got = client.post("/v1/devices/register", json={"device_id": "dev_1"}, headers=tenant)
    assert got.status_code == 201 and got.json()["device_id"] == "dev_1"
    device = {"Authorization": f"Bearer {got.json()['token']}"}

    assert client.get("/v1/devices", headers=device).status_code == 200
    assert (
        client.get("/v1/devices", headers={"Authorization": "Bearer dev_forged"}).status_code == 401
    )
    # A device does not register or revoke browsers, itself included.
    assert (
        client.post("/v1/devices/register", json={"device_id": "dev_2"}, headers=device).status_code
        == 403
    )
    assert client.post("/v1/devices/dev_1/revoke", headers=device).status_code == 403
    assert client.post("/v1/devices/register", json={}, headers=tenant).status_code == 400

    assert client.post("/v1/devices/dev_1/revoke", headers=tenant).json()["revoked"] is True
    assert client.get("/v1/devices", headers=device).status_code == 401, "revoked means refused"


def test_a_devices_token_opens_its_own_socket_and_no_other(tmp_path: Path) -> None:
    store = _store(tmp_path)
    app = build_app(
        store=store, asker=FakeAsker(), token=TOKEN, tenant="acme", read_on_ingest=False
    )
    client = TestClient(app)
    token = issue(store, "dev_1")

    with client.websocket_connect(
        "/v1/agents/dev_1/commands", subprotocols=["bearer", token]
    ) as ws:
        ws.send_text(json.dumps({"kind": "hello", "extension_version": "0.1.0", "tabs": 1}))
        assert app.state.channel.online() == ["dev_1"]

    # Starlette raises its own disconnect on a refused handshake, hence B017.
    with (
        pytest.raises(Exception),  # noqa: B017
        client.websocket_connect("/v1/agents/dev_2/commands", subprotocols=["bearer", token]),
    ):
        pass
    # The tenant's bearer still opens any device's socket.
    with client.websocket_connect("/v1/agents/dev_2/commands", subprotocols=["bearer", TOKEN]):
        pass


def test_an_approval_by_a_registered_browser_names_that_browser_whatever_the_body_says(
    tmp_path: Path,
) -> None:
    from rig.runner import Approvals
    from rig.runs import Run, RunStep, save_run

    store = _store(tmp_path)
    client = _client(store)
    token = issue(store, "dev_real")
    save_run(
        store,
        Run(
            id="run_by",
            tenant="acme",
            workflow_id="wfl_1",
            device_id="dev_real",
            values={},
            started_by="offer",
            live=True,
            allow_focus=True,
            started_at="2026-09-06T10:00:00+00:00",
            finished_at=None,
            outcome="running",
            steps=[RunStep(order=0, says="save", verdict="awaiting", verdict_by="none")],
        ),
    )
    loop = asyncio.new_event_loop()
    try:
        task = loop.create_task(Approvals.wait_for("run_by", timeout=5))
        loop.run_until_complete(asyncio.sleep(0))
        got = client.post(
            "/v1/runs/run_by/approve",
            json={"device_id": "dev_liar"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert loop.run_until_complete(task) is True
    finally:
        loop.close()
    assert got.status_code == 200
    assert store.query("SELECT device_id FROM approvals")[0]["device_id"] == "dev_real"
