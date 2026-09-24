"""Spec §5.6, enforced where the evidence is stored and not only where it is taken.

A browser decides first, so the values never leave it. The backend decides
again: a browser can be old, broken, or not ours, and a rule that runs only in
the client is one the client can be made not to run. So an event the browser
MARKED as sign-in, and an event the backend DETECTS as one -- a gesture on a
password or one-time-code field, anything on a tab inside an OAuth/OIDC flow,
and anything else on the same page as either -- is stored structure-only: what
was acted on, the URLs and each call's method, URL and status stay; typed
values, bodies, trees and screenshots do not.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from sro.application.context import RequestContext
from sro.application.observation.artifacts import StoreObservationArtifact
from sro.application.observation.ingest import IngestObservation
from sro.application.observation.policy import SetObservationPolicy
from sro.application.observation.redact import redact_events
from sro.application.observation.register import RegisterDevice
from sro.domain.observation.batch import CaptureMode
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.recording.artifact import ArtifactKind
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import BatchId, DeviceId
from tests import factories as f
from tests.unit.fakes import FakeBlobStore, FakeClock, FakeIdFactory, FakeUnitOfWork

ACME = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)

APP = "https://wms.example"
IDP = "https://login.idp.example"
AUTHORIZE = f"{IDP}/authorize?client_id=app&response_type=code&redirect_uri={APP}/callback&state=s1"
CODE = "135791"
PASSWORD = "hunter2-not-real"  # noqa: S105 -- the thing under test


def _gesture(
    kind: str, *, url: str, value: str | None = None, **target: object
) -> dict[str, object]:
    return {
        "kind": "gesture",
        "tab_id": 7,
        "page_url": url,
        "frame_url": url,
        "gesture": {
            "kind": kind,
            "at": 1787654321.0,
            "url": url,
            "value": value,
            "target": {"tag": "input", "cssPath": "form > input", **target},
        },
    }


def _page(url: str) -> dict[str, object]:
    return {
        "kind": "page",
        "page_kind": "navigated",
        "at": "2026-03-01T09:00:00Z",
        "url": url,
        "tab_id": 7,
    }


def _request(url: str, frame: str) -> dict[str, object]:
    return {
        "kind": "request",
        "tab_id": 7,
        "frame_url": frame,
        "request": {
            "request_id": "r1",
            "method": "POST",
            "url": url,
            "started_at": "2026-03-01T09:00:01Z",
            "status": 200,
            "request_body": {"text": json.dumps({"otc": CODE}), "size_bytes": 14},
            "response_body": {"text": json.dumps({"session": "S3SSION"}), "size_bytes": 20},
        },
    }


def _snapshot(url: str) -> dict[str, object]:
    return {
        "kind": "snapshot",
        "tab_id": 7,
        "url": url,
        "taken_at": "2026-03-01T09:00:02Z",
        "snapshot": {"nodes": [{"nodeId": "1", "name": {"value": f"Verify {CODE}"}}]},
    }


def test_a_tab_inside_an_oauth_flow_is_stored_structure_only() -> None:
    otc = f"{IDP}/otc"
    stored = redact_events(
        [
            _page(AUTHORIZE),
            _page(otc),
            _gesture(
                "type", url=otc, value=CODE, name="Code", attributes={"name": "otc", "type": "tel"}
            ),
            _gesture("click", url=otc, name=f"Verify {CODE}", text=f"Verify {CODE}"),
            _request(f"{IDP}/verify", otc),
            _snapshot(otc),
            _page(f"{APP}/callback?code=AUTHCODE&state=s1"),
            _gesture("type", url=f"{APP}/orders", value="ACME-4471", name="Client"),
        ]
    )

    signed_in = stored[:6]
    assert all(event["sign_in"] is True for event in signed_in)
    text = json.dumps(signed_in)
    for value in (CODE, "S3SSION"):
        assert value not in text
    assert stored[2]["gesture"]["value"] is None
    assert stored[4]["request"]["request_body"] is None
    assert stored[4]["request"]["response_body"] is None
    assert stored[5]["snapshot"] == {}
    # What was acted on and where stays: the sign-in chain is learned from it.
    assert stored[2]["gesture"]["target"]["attributes"] == {"name": "otc", "type": "tel"}
    assert stored[3]["gesture"]["target"]["cssPath"] == "form > input"
    assert stored[4]["request"]["method"] == "POST"
    assert stored[4]["request"]["status"] == 200
    assert stored[1]["url"] == otc
    # And the app on the other side of the flow is watched like any page.
    assert "sign_in" not in stored[6]
    assert stored[7]["gesture"]["value"] == "ACME-4471"


def test_a_page_holding_a_password_field_is_stored_structure_only() -> None:
    page = f"{APP}/sign-in"
    stored = redact_events(
        [
            _gesture("type", url=page, value="operator", name="Username"),
            _gesture("type", url=page, value=PASSWORD, attributes={"type": "password"}),
            _snapshot(page),
            _request(f"{APP}/login", page),
        ]
    )

    assert [event.get("sign_in") for event in stored] == [True, True, True, True]
    text = json.dumps(stored)
    for value in ("operator", PASSWORD, CODE, "S3SSION"):
        assert value not in text


def test_an_event_the_browser_marked_is_believed() -> None:
    marked = {**_gesture("type", url=f"{APP}/pin", value="4242"), "sign_in": True}

    stored = redact_events([marked])

    assert stored[0]["gesture"]["value"] is None


async def _ingested(
    uow: FakeUnitOfWork, blobs: FakeBlobStore, events: list[dict[str, object]]
) -> str:
    await SetObservationPolicy(uow).execute(ACME, policy=ObservationPolicy().enabled())
    registered = await RegisterDevice(uow, FakeClock(), FakeIdFactory()).execute(
        ACME, label="laptop", extension_version="0.1.0"
    )
    device_id = registered.device_id.value
    await IngestObservation(uow, blobs, FakeClock()).execute(
        ACME,
        device_id=DeviceId(device_id),
        secret=uow.devices.rows[device_id].secret,
        batch_id=BatchId("bat_sign_in"),
        started_at=datetime(2026, 3, 1, 9, 0, tzinfo=UTC),
        ended_at=datetime(2026, 3, 1, 9, 5, tzinfo=UTC),
        mode=CaptureMode.PASSIVE,
        events=events,
    )
    return device_id


async def _upload_picture(
    uow: FakeUnitOfWork, blobs: FakeBlobStore, device_id: str, frame_index: int
) -> str:
    stored = await StoreObservationArtifact(uow, blobs, FakeClock()).execute(
        ACME,
        device_id=DeviceId(device_id),
        secret=uow.devices.rows[device_id].secret,
        batch_id=BatchId("bat_sign_in"),
        kind=ArtifactKind.SCREENSHOT,
        data=b"png-bytes",
        content_type="image/png",
        frame_index=frame_index,
    )
    return stored.uri


async def test_a_picture_of_a_sign_in_gesture_is_refused() -> None:
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    device_id = await _ingested(
        uow,
        blobs,
        [
            _gesture("type", url=f"{APP}/orders", value="ACME-4471", name="Client"),
            _gesture("type", url=f"{APP}/sign-in", value=PASSWORD, attributes={"type": "password"}),
        ],
    )

    assert await _upload_picture(uow, blobs, device_id, 0)
    with pytest.raises(InvariantViolation):
        await _upload_picture(uow, blobs, device_id, 1)
    assert not [key for key in blobs.objects if key.endswith("00001.png")]


def test_a_tree_of_the_callback_page_keeps_its_url_but_not_the_code_in_it() -> None:
    """Found by the real-Chrome proof: the app page the flow returns to is not
    a sign-in page, and Chrome writes the page's own URL into the tree's root
    -- `?code=` and all."""
    callback = f"{APP}/callback?code=AUTHCODE&state=s1"
    tree = {
        "kind": "snapshot",
        "tab_id": 7,
        "url": f"{APP}/callback",
        "taken_at": "2026-03-01T09:00:02Z",
        "snapshot": {
            "nodes": [
                {
                    "nodeId": "1",
                    "role": {"value": "RootWebArea"},
                    "properties": [{"name": "url", "value": {"type": "string", "value": callback}}],
                }
            ]
        },
    }

    stored = redact_events([tree])

    assert "AUTHCODE" not in json.dumps(stored)
    assert "callback?code=" in json.dumps(stored)


def test_steel_s_tree_keeps_no_code_in_a_url_either() -> None:
    from sro.application.capture.decode import to_ax_graph

    graph = to_ax_graph(
        {
            "nodes": [
                {
                    "nodeId": "1",
                    "role": {"value": "RootWebArea"},
                    "properties": [
                        {
                            "name": "url",
                            "value": {"value": f"{APP}/callback?code=AUTHCODE&state=s1"},
                        }
                    ],
                }
            ]
        },
        url=f"{APP}/callback?code=AUTHCODE&state=s1",
        taken_at=datetime(2026, 3, 1, 9, 0, tzinfo=UTC),
    )

    assert "AUTHCODE" not in repr(graph)
