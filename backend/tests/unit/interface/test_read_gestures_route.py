"""`POST /v1/gestures/read`: who may ask, what it costs them, and what comes back.

The door itself is proved in `tests/unit/application/rig/test_read_gesture.py`
(the `ReadGestures` section). What is here is the wire: that a deployment with
no model answers 503 rather than a quiet empty pass, that a tenant over its cap
answers 429, that the count reaches the response body, and that a browser's
secret does not open the tenant's purse -- the same shape `test_mine_route.py`
proves for `POST /v1/mine`, scaled to a door that answers a bare count.

Nothing is dated today. The container's clock stands six months from any wall
clock this runs against, so a route that reached for `datetime.now(UTC)` bills
a different day than the one asserted here.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from httpx import ASGITransport

from sro.config import Settings
from sro.domain.chat.reading import ChatReading
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.shared.prices import Answer
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests import factories as f
from tests.unit.domain.rig.conftest import gestures as _gestures
from tests.unit.fakes import FakeAsker, FakeClock, FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for

TENANT = TenantId("acme")
LAPTOP = DeviceId("dev-1")
HERS = "the-secret-the-laptop-was-minted"

NOW = datetime(2025, 2, 11, 23, 0, tzinfo=UTC)
CAP = 5.0

MODEL = "gemini-3.1-flash-preview"
"""Deliberately not the shipped `gemini_read_model`, so a route wired to a
literal -- or to the wrong one of the model settings -- fails rather than
agreeing with the default."""


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def container(uow: FakeUnitOfWork) -> _FakeContainer:
    built = _FakeContainer(uow)
    built.settings = Settings(daily_usd_cap=CAP, gemini_read_model=MODEL, _env_file=None)
    built.clock = FakeClock(NOW)
    return built


@pytest.fixture
async def client(container: _FakeContainer) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_for()}"},
    ) as http:
        yield http


@pytest.fixture
async def day(uow: FakeUnitOfWork) -> list[str]:
    found = _gestures(TENANT.value)
    await uow.gestures.add_gestures(tuple(found))
    return [g.id for g in sorted(found, key=lambda g: (g.at, g.id))]


def _answer() -> Answer:
    return Answer(
        data={"act": "typed a client code", "why": "the field is labelled Client Code"},
        cost_usd=0.001,
    )


def test_this_containers_clock_is_nowhere_near_the_wall_clock() -> None:
    assert abs(datetime.now(UTC) - NOW) > timedelta(days=2)


# --- the two refusals -------------------------------------------------------


async def test_a_deployment_with_no_model_says_so_rather_than_reading_nothing(
    client: httpx.AsyncClient, day: list[str]
) -> None:
    answered = await client.post("/v1/gestures/read")

    assert answered.status_code == 503
    assert "gemini_api_key" in answered.text
    assert "interpretation_enabled" in answered.text


async def test_a_tenant_over_its_cap_is_told_to_come_back_later(
    container: _FakeContainer, client: httpx.AsyncClient, uow: FakeUnitOfWork, day: list[str]
) -> None:
    container.asker = FakeAsker(*(_answer() for _ in day))
    await uow.chats.record(
        ChatReading(
            id="cht_1", tenant=TENANT.value, at=NOW.replace(hour=10).isoformat(), cost_usd=5.01
        )
    )

    answered = await client.post("/v1/gestures/read")

    assert answered.status_code == 429
    body = answered.json()
    assert body["type"] == "https://ai-sro.dev/problems/over_cap"
    assert "$5.0100 of $5.00" in body["detail"]
    assert await uow.gestures.intents_for(TENANT) == (), "the refusal read something anyway"


# --- what comes back --------------------------------------------------------


async def test_every_unread_gesture_is_read_and_the_count_reaches_the_wire(
    container: _FakeContainer, client: httpx.AsyncClient, day: list[str]
) -> None:
    container.asker = FakeAsker(*(_answer() for _ in day))

    answered = await client.post("/v1/gestures/read")

    assert answered.status_code == 200, answered.text
    assert answered.json() == {"read": len(day)}


async def test_the_model_asked_is_the_one_this_deployment_configured(
    container: _FakeContainer, client: httpx.AsyncClient, day: list[str]
) -> None:
    asked = FakeAsker(*(_answer() for _ in day))
    container.asker = asked

    await client.post("/v1/gestures/read")

    assert [one["model"] for one in asked.asked] == [MODEL] * len(day)


# --- whose tenant, whose clock -----------------------------------------------


async def test_the_tenant_read_is_the_one_on_the_credential(
    container: _FakeContainer, uow: FakeUnitOfWork, day: list[str]
) -> None:
    container.asker = FakeAsker(*(_answer() for _ in day))
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_for(tenant='rival')}"},
    ) as rival:
        body = (await rival.post("/v1/gestures/read")).json()

    assert body == {"read": 0}
    assert await uow.gestures.intents_for(TENANT) == ()


# --- who may ask -------------------------------------------------------------


async def test_a_browser_may_not_spend_the_tenants_model_budget(
    container: _FakeContainer, client: httpx.AsyncClient, uow: FakeUnitOfWork, day: list[str]
) -> None:
    container.asker = FakeAsker(*(_answer() for _ in day))
    await uow.devices.add(f.device(id=LAPTOP, secret=HERS))

    answered = await client.post(
        "/v1/gestures/read",
        params={"device_id": LAPTOP.value},
        headers={"X-Device-Secret": HERS},
    )

    assert answered.status_code == 403
    assert answered.json()["detail"] == "that is the tenant's to do, not a browser's"
    assert (await client.post("/v1/gestures/read")).status_code == 200


async def test_no_credential_is_refused_before_anything_is_read(
    client: httpx.AsyncClient, day: list[str]
) -> None:
    answered = await client.post("/v1/gestures/read", headers={"Authorization": ""})

    assert answered.status_code == 401
