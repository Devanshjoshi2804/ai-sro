"""A target's attributes, posted through the real route, read back from Postgres (F5).

The unit twin posts the same batch into the fake store. What only a database
can answer is the last hop: the gesture is written as ``TypeAdapter(Action)``
JSONB by ``evidence._gesture_to_row`` and read back by ``_row_to_gesture``, and
an attribute that dies in that round trip dies silently for every reader of
the evidence plane.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.application.observation.policy import SetObservationPolicy
from sro.application.ports.repositories import UnitOfWork
from sro.domain.observation.device import AgentDevice
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.shared.identifiers import PrincipalId
from sro.infrastructure.db.repositories import SqlUnitOfWork
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork
from tests.unit.interface.test_a_target_keeps_its_attributes import (
    CTX,
    EMAIL,
    HERS,
    LENA,
    PASSWORD,
    _batch,
)
from tests.unit.interface.test_http import _FakeContainer, token_for


class _RealSessionContainer(_FakeContainer):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        super().__init__(FakeUnitOfWork())

    def unit_of_work(self) -> UnitOfWork:
        return SqlUnitOfWork(self._session_factory)


@pytest.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[httpx.AsyncClient]:
    async with SqlUnitOfWork(session_factory) as uow:
        await uow.devices.add(
            AgentDevice(
                id=LENA,
                tenant_id=f.TENANT,
                principal_id=PrincipalId("lena@acme.test"),
                label="laptop",
                extension_version="0.1.0",
                registered_at=f.at(0),
                last_seen_at=f.at(0),
                secret=HERS,
            )
        )
        await uow.commit()
    await SetObservationPolicy(SqlUnitOfWork(session_factory)).execute(
        CTX, policy=ObservationPolicy().enabled()
    )
    app = create_app()
    container = _RealSessionContainer(session_factory)
    app.dependency_overrides[get_container] = lambda: container
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_for()}", "X-Device-Secret": HERS},
    ) as http:
        yield http


async def test_a_posted_gesture_comes_back_from_postgres_with_its_attributes(
    client: httpx.AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    leaked = {
        **PASSWORD,
        "target": {
            **PASSWORD["target"],
            "attributes": {**PASSWORD["target"]["attributes"], "value": "hunter2"},
        },
    }

    response = await client.post("/v1/observations", json=_batch("bat-signin", EMAIL, leaked))

    assert response.status_code == 202, response.text
    async with SqlUnitOfWork(session_factory) as uow:
        kept = await uow.gestures.gestures_for(f.TENANT, ids=None)
    targets = {
        gesture.action.target.css_path: gesture.action.target
        for gesture in kept
        if gesture.action.target is not None
    }
    email = targets["input#identifierId"]
    assert email.attributes["autocomplete"] == "username"
    assert email.attributes["type"] == "email"
    assert email.attributes["aria-haspopup"] == "true"
    password = targets["html > body > form > input:nth-of-type(2)"]
    assert password.attributes["autocomplete"] == "current-password"
    assert "value" not in password.attributes
    assert "hunter2" not in repr(kept)
