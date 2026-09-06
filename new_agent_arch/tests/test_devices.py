import asyncio
import json
from pathlib import Path
from typing import Any

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


def test_a_browser_approves_only_the_run_it_is_driving(tmp_path: Path) -> None:
    from rig.runner import Approvals
    from rig.runs import Run, RunStep, save_run

    store = _store(tmp_path)
    client = _client(store)
    other = issue(store, "dev_other")
    save_run(
        store,
        Run(
            id="run_theirs",
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
    Approvals.register("run_theirs")
    try:
        got = client.post(
            "/v1/runs/run_theirs/approve", headers={"Authorization": f"Bearer {other}"}
        )
        assert got.status_code == 403
        assert "run_theirs" in Approvals.waiting(), "the wait was not released"
        assert store.query("SELECT 1 FROM approvals") == []
    finally:
        Approvals.forget("run_theirs")


def test_the_tenants_purse_and_the_other_browsers_days_are_not_a_devices(tmp_path: Path) -> None:
    store = _store(tmp_path)
    client = _client(store)
    device = {"Authorization": f"Bearer {issue(store, 'dev_1')}"}
    for method, path in (
        ("post", "/v1/mine"),
        ("post", "/v1/chat"),
        ("get", "/v1/audit"),
        ("get", "/v1/gestures?stream=s"),
        ("get", "/v1/streams"),
        ("get", "/v1/spend"),
        ("get", "/v1/workflows/wfl_x/evidence"),
    ):
        kwargs: dict[str, Any] = {"json": {}} if method == "post" else {}
        got = getattr(client, method)(path, headers=device, **kwargs)
        assert got.status_code == 403, f"{method} {path} let a device in: {got.status_code}"
    # Its own doors stay open.
    assert client.get("/v1/devices", headers=device).status_code == 200
    assert client.get("/v1/shapes", headers=device).status_code == 200


def test_an_empty_tenant_token_admits_nobody(tmp_path: Path) -> None:
    store = _store(tmp_path)
    client = TestClient(
        build_app(store=store, asker=FakeAsker(), token="", tenant="acme", read_on_ingest=False)
    )
    assert client.get("/v1/devices").status_code == 401
    assert client.get("/v1/devices", headers={"Authorization": "Bearer "}).status_code == 401


def test_revoking_a_browser_takes_it_offline_at_once(tmp_path: Path) -> None:
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
        got = client.post("/v1/devices/dev_1/revoke", headers={"Authorization": f"Bearer {TOKEN}"})
        assert got.json()["revoked"] is True
        assert app.state.channel.online() == [], "revoked reads as offline, not as connected"


def test_a_browser_with_a_token_of_its_own_reads_its_own_rest_whatever_it_asks_for(
    tmp_path: Path,
) -> None:
    from datetime import UTC, datetime

    from rig.api import save_batch
    from rig.offers import record_offer
    from rig.wire import Batch
    from rig.workflows import Step, Workflow, save_workflow
    from tests.fixtures import BATCH

    store = _store(tmp_path)
    save_batch(store, Batch.model_validate(BATCH), "acme")
    ids = [r["id"] for r in store.query("SELECT id FROM gestures ORDER BY at")]
    save_workflow(
        store,
        Workflow(
            id="wfl_1",
            tenant="acme",
            title="t",
            narrative="n",
            systems=["http://127.0.0.1:63319"],
            steps=[
                Step(order=0, says="a", system=None, cites=[ids[0]]),
                Step(order=1, says="b", system=None, cites=[ids[-1]]),
            ],
            parameters=[],
        ),
    )
    for _ in range(3):
        record_offer(
            store,
            tenant="acme",
            workflow_id="wfl_1",
            k=2,
            fate="dismissed",
            run_id=None,
            device_id="dev_real",
            at=datetime.now(UTC).isoformat(),
        )
    client = _client(store)
    real = {"Authorization": f"Bearer {issue(store, 'dev_real')}"}
    other = {"Authorization": f"Bearer {issue(store, 'dev_other')}"}
    [as_real] = client.get("/v1/shapes?device_id=dev_other", headers=real).json()["shapes"]
    [as_other] = client.get("/v1/shapes?device_id=dev_real", headers=other).json()["shapes"]
    [tenant_says] = client.get(
        "/v1/shapes?device_id=dev_real", headers={"Authorization": f"Bearer {TOKEN}"}
    ).json()["shapes"]
    assert as_real["quiet_until"], "the token names the browser, not the query"
    assert as_other["quiet_until"] is None, "another browser cannot borrow the rest"
    assert tenant_says["quiet_until"], "the tenant's bearer may ask on any browser's behalf"
