"""A target's attributes survive the door a browser writes through (F5).

Everything that decides from HTML structure reads ``target.attributes``: the
menu-opening rule for a sign-out (``aria-haspopup``), the replayer's attribute
locator (``name``, ``autocomplete``, ``type``), and the identity-field rule
(``autocomplete="username"``, ``type="email"``). QA found them empty on stored
gestures, so this posts what the recorder really sends through the real route
and reads the gesture back out of the repository the miner reads.

The two gestures are the generated recorder's own output, captured from
Chromium on a sign-in form (an email box and a password box), with only the
page address moved onto a host the tenant observes.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from httpx import ASGITransport

from sro.application.context import RequestContext
from sro.application.observation.policy import SetObservationPolicy
from sro.domain.observation.device import AgentDevice
from sro.domain.observation.gesture import Gesture
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.shared.identifiers import DeviceId, PrincipalId
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for

LENA = DeviceId("dev-lena-laptop")
HERS = "the-secret-lena-s-browser-was-minted"
CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
PAGE = "https://wms.acme.com/signin"

EMAIL: dict[str, Any] = {
    "kind": "type",
    "target": {
        "tag": "input",
        "role": "textbox",
        "name": "Email or phone",
        "secret": False,
        "text": None,
        "testId": None,
        "required": None,
        "cssPath": "input#identifierId",
        "xpath": "/html/body[1]/form[1]/input[1]",
        "bounds": {"x": 8, "y": 8, "width": 185, "height": 21},
        "attributes": {
            "id": "identifierId",
            "type": "email",
            "name": "identifier",
            "autocomplete": "username",
            "aria-haspopup": "true",
            "aria-label": "Email or phone",
        },
        "component": None,
        "landmarks": [],
    },
    "value": "clerk@acme.test",
    "secret": False,
    "modifiers": [],
    "ref": "dufqku1unx9.2",
    "prior": {"value": None, "visible": True, "enabled": True},
    "prior_of": "dufqku1unx9.1",
    "outlines": [],
    "frame_path": [],
    "at": 1772355630.229,
    "url": PAGE,
}

PASSWORD: dict[str, Any] = {
    "kind": "type",
    "target": {
        "tag": "input",
        "role": "textbox",
        "name": None,
        "secret": True,
        "text": None,
        "testId": None,
        "required": None,
        "cssPath": "html > body > form > input:nth-of-type(2)",
        "xpath": "/html/body[1]/form[1]/input[2]",
        "bounds": {"x": 193, "y": 8, "width": 185, "height": 21},
        "attributes": {
            "type": "password",
            "name": "Passwd",
            "autocomplete": "current-password",
            "aria-label": "Enter your password",
        },
        "component": None,
        "landmarks": [],
    },
    "value": None,
    "secret": True,
    "modifiers": [],
    "ref": "dufqku1unx9.4",
    "prior": {"value": None, "visible": True, "enabled": True},
    "prior_of": "dufqku1unx9.3",
    "outlines": [],
    "frame_path": [],
    "at": 1772355630.252,
    "url": PAGE,
}


def _batch(batch_id: str, *gestures: dict[str, Any]) -> dict[str, Any]:
    return {
        "batch_id": batch_id,
        "device_id": LENA.value,
        "started_at": "2026-03-01T09:00:00Z",
        "ended_at": "2026-03-01T09:01:00Z",
        "mode": "passive",
        "events": [
            {
                "kind": "gesture",
                "gesture": gesture,
                "tab_id": 7,
                "frame_url": PAGE,
                "page_url": PAGE,
            }
            for gesture in gestures
        ],
    }


@pytest.fixture
async def uow() -> AsyncIterator[FakeUnitOfWork]:
    unit = FakeUnitOfWork()
    unit.devices.rows[LENA.value] = AgentDevice(
        id=LENA,
        tenant_id=f.TENANT,
        principal_id=PrincipalId("lena@acme.test"),
        label="laptop",
        extension_version="0.1.0",
        registered_at=f.at(0),
        last_seen_at=f.at(0),
        secret=HERS,
    )
    await SetObservationPolicy(unit).execute(CTX, policy=ObservationPolicy().enabled())
    yield unit


@pytest.fixture
async def client(uow: FakeUnitOfWork) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    container = _FakeContainer(uow)
    app.dependency_overrides[get_container] = lambda: container
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_for()}", "X-Device-Secret": HERS},
    ) as http:
        yield http


async def _stored(uow: FakeUnitOfWork) -> dict[str, Gesture]:
    kept = await uow.gestures.gestures_for(f.TENANT, ids=None)
    return {
        str(gesture.action.target.css_path): gesture
        for gesture in kept
        if gesture.action.target is not None
    }


async def test_an_identity_field_is_stored_with_the_attributes_it_was_recorded_with(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    response = await client.post("/v1/observations", json=_batch("bat-signin", EMAIL, PASSWORD))

    assert response.status_code == 202, response.text
    stored = await _stored(uow)
    email = stored["input#identifierId"].action.target
    assert email is not None
    assert email.attributes["autocomplete"] == "username"
    assert email.attributes["type"] == "email"
    assert email.attributes["aria-haspopup"] == "true"
    password = stored["html > body > form > input:nth-of-type(2)"].action.target
    assert password is not None
    assert password.attributes["type"] == "password"
    assert password.attributes["autocomplete"] == "current-password"


async def test_a_credential_field_s_value_attribute_never_comes_back(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """The recorder omits it; the store drops it again whoever sent it.

    ``observe.js`` relays any ``sro:gesture`` a page dispatches, so a payload
    that carries a secret field's ``value`` is one a page can produce even
    though the recorder never does. The storage-side policy is what answers
    for it, and it is the half this door owns.
    """
    leaked = {
        **PASSWORD,
        "target": {
            **PASSWORD["target"],
            "attributes": {**PASSWORD["target"]["attributes"], "value": "hunter2"},
        },
    }

    response = await client.post("/v1/observations", json=_batch("bat-leak", leaked))

    assert response.status_code == 202, response.text
    stored = await _stored(uow)
    target = stored["html > body > form > input:nth-of-type(2)"].action.target
    assert target is not None
    assert "value" not in target.attributes
    assert target.attributes["autocomplete"] == "current-password"
    assert "hunter2" not in repr(stored)
