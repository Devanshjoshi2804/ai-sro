"""Making a rule by standing somewhere, and a browser firing it when it lands.

The wire that was missing. This system could recognise a job and could drive a
browser through one, and nothing joined them: a run began because a person
pressed, a console started it, or a clock fired. An operator watching their own
browser be driven through a login asked why it could not do that by itself.

Three things this boundary owns, and the third is the one that matters. The
rule is a page and never a url. A browser is handed only its own rules, for a
sharper reason than a watch has -- a watch in the wrong browser reads somebody's
mail, an arrival in the wrong browser DRIVES it. And the fire is checked here
against the rule's own page as well as in the browser, because a browser that
got it wrong, or a request that never came from one, would otherwise start a
live run in somebody's window on a page nobody chose.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from httpx import ASGITransport

from sro.domain.observation.device import AgentDevice
from sro.domain.shared.identifiers import DeviceId, PrincipalId, TenantId
from sro.domain.skill.workflow import Step, Workflow
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for

LENA = DeviceId("dev-lena-laptop")
SAM = DeviceId("dev-sam-laptop")

WMS = "bf56-kms-wms-web-np2.jdadelivers.com"
# The screen, fragment route and all: Blue Yonder routes on the fragment.
THE_PAGE = f"{WMS}/portal/page#wm.config.partners.suppliers"
ON_IT = f"https://{WMS}/portal/page?siteId=SG#wm.config.partners.suppliers////"


def _proving(device_id: DeviceId) -> dict[str, str]:
    return {"X-Device-Secret": f"secret-for-{device_id.value}"}


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def container(uow: FakeUnitOfWork) -> _FakeContainer:
    return _FakeContainer(uow)


@pytest.fixture
async def client(
    uow: FakeUnitOfWork, container: _FakeContainer
) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_for()}"},
    ) as http:
        yield http


def _device(
    uow: FakeUnitOfWork,
    device_id: DeviceId,
    *,
    tenant: TenantId = f.TENANT,
    principal: PrincipalId = f.OPERATOR,
) -> None:
    uow.devices.rows[device_id.value] = AgentDevice(
        id=device_id,
        tenant_id=tenant,
        principal_id=principal,
        label=device_id.value,
        extension_version="0.1.0",
        registered_at=f.at(0),
        last_seen_at=f.at(0),
        secret=f"secret-for-{device_id.value}",
    )


async def _job(uow: FakeUnitOfWork, *, workflow_id: str = "wfl_1") -> None:
    await uow.workflows.save(
        Workflow(
            id=workflow_id,
            tenant=f.TENANT.value,
            title="create an equipment type",
            narrative="the operator created an equipment type",
            steps=[
                Step(order=n, says=f"step {n}", system=None, cites=[f"ges-{n}"]) for n in range(2)
            ],
            parameters=[],
        )
    )


def _asked(**over: object) -> dict[str, object]:
    body: dict[str, object] = {
        "workflow_id": "wfl_1",
        "kind": "arrival",
        "arrival": {"page": THE_PAGE},
        "device_id": LENA.value,
        "authorized_by": True,
        "parameters": {},
    }
    body.update(over)
    return body


async def _rule(client: httpx.AsyncClient, uow: FakeUnitOfWork, **over: object) -> str:
    _device(uow, LENA)
    await _job(uow)
    made = await client.post("/v1/triggers", json=_asked(**over))
    assert made.status_code == 201, made.text
    return str(made.json()["id"])


# --- making one ------------------------------------------------------------


async def test_a_page_becomes_a_rule_that_runs_a_job(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    _device(uow, LENA)
    await _job(uow)

    made = await client.post("/v1/triggers", json=_asked())

    assert made.status_code == 201, made.text
    assert made.json()["arrival"] == {"page": THE_PAGE}
    assert made.json()["kind"] == "arrival"
    # A standing authority to drive a browser through real work. The write
    # still asks: `requires_confirmation` is what makes the fire a card.
    assert made.json()["writes"] is True
    assert made.json()["requires_confirmation"] is True


async def test_a_rule_with_no_page_is_refused_with_a_sentence(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    _device(uow, LENA)
    await _job(uow)

    refused = await client.post("/v1/triggers", json=_asked(arrival=None))

    # 409 and a sentence, as every other `TriggerRefused` is: the request is
    # well formed and the thing it asks for is not a trigger that could work.
    assert refused.status_code == 409, refused.text
    assert "needs the page it fires on" in refused.text


async def test_a_url_somebody_pasted_is_refused_rather_than_trimmed(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """The rule and the page it was made from have to be one string. Trimmed
    here, they would be two that somebody has to keep in step."""
    _device(uow, LENA)
    await _job(uow)

    refused = await client.post("/v1/triggers", json=_asked(arrival={"page": ON_IT}))

    assert refused.status_code == 422, refused.text


async def test_a_rule_with_no_browser_sees_nobody_arrive(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    await _job(uow)

    refused = await client.post("/v1/triggers", json=_asked(device_id=None))

    assert refused.status_code == 409, refused.text
    assert "browser" in refused.text


# --- reading them back -----------------------------------------------------


async def test_a_browser_is_handed_only_its_own_rules(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """Sharper than the same rule for a watch. A watch in the wrong browser
    reads somebody's mail; an arrival in the wrong browser drives it."""
    await _rule(client, uow)
    _device(uow, SAM, principal=PrincipalId("sam"))

    hers = await client.get(f"/v1/agents/{LENA.value}/arrivals", headers=_proving(LENA))
    his = await client.get(f"/v1/agents/{SAM.value}/arrivals", headers=_proving(SAM))

    assert [one["arrival"]["page"] for one in hers.json()] == [THE_PAGE]
    assert his.json() == []


async def test_a_browser_that_cannot_prove_it_is_itself_is_handed_nothing(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    await _rule(client, uow)

    asked = await client.get(
        f"/v1/agents/{LENA.value}/arrivals", headers={"X-Device-Secret": "not-hers"}
    )

    assert asked.status_code == 404, asked.text


# --- firing one ------------------------------------------------------------


async def test_arriving_on_the_page_starts_the_job_with_no_press(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """No press, and that is the kind. A person already pressed once, when they
    made the rule."""
    trigger_id = await _rule(client, uow)

    fired = await client.post(
        f"/v1/agents/{LENA.value}/arrivals/{trigger_id}/fire",
        json={"url": ON_IT},
        headers=_proving(LENA),
    )

    assert fired.status_code == 202, fired.text
    assert fired.json()["trigger_id"] == trigger_id


async def test_a_page_the_rule_is_not_about_starts_nothing(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """Checked here as well as in the browser. A browser that got the rule
    wrong -- or a request that never came from one -- would otherwise start a
    live run in somebody's window on a page nobody chose."""
    trigger_id = await _rule(client, uow)

    fired = await client.post(
        f"/v1/agents/{LENA.value}/arrivals/{trigger_id}/fire",
        json={"url": f"https://{WMS}/portal/page/suppliers"},
        headers=_proving(LENA),
    )

    assert fired.status_code == 404, fired.text


async def test_another_browser_cannot_fire_this_ones_rule(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    trigger_id = await _rule(client, uow)
    _device(uow, SAM, principal=PrincipalId("sam"))

    fired = await client.post(
        f"/v1/agents/{SAM.value}/arrivals/{trigger_id}/fire",
        json={"url": ON_IT},
        headers=_proving(SAM),
    )

    assert fired.status_code == 404, fired.text
