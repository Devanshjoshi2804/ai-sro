"""Creating a watch over HTTP, and a browser asking what its own rules are.

A watch is evaluated in the operator's own browser and nowhere else: no mail is
sent here, so the rule has to go there. That makes two things this boundary
owns. The shape the extension posts has to be the shape it already speaks --
locators are the only interesting part, and it resolves them today from the
command channel. And the endpoint that hands the rules back has to hand each
browser only its own, because a rule about one person's mail in another
person's browser is that mail being read by somebody nobody offered it to.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from httpx import ASGITransport

from sro.application.context import RequestContext
from sro.domain.observation.device import AgentDevice
from sro.domain.shared.identifiers import DeviceId, PrincipalId, SkillId, TenantId
from sro.domain.skill.promotion import PromotionStage
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for

LENA = DeviceId("dev-lena-laptop")
SAM = DeviceId("dev-sam-laptop")

WATCH = {
    "host": "mail.acme.test",
    "terms": [
        {"field": "sender", "contains": "dispatch@supplier.test"},
        {"field": "subject", "contains": "Short ship"},
    ],
    "values": [
        {
            "name": "shipment_id",
            # The four fields `in-page.js` already reads off a locator handed
            # down the command channel. A fifth name here would be a second
            # resolver in the extension.
            "where": {
                "strategy": "css_path",
                "query": "span.shipment-ref",
                "within": "div.mail-body",
                "visible_only": True,
            },
        }
    ],
}


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
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_for()}"},
    ) as http:
        yield http


async def _teachable_skill(uow: FakeUnitOfWork) -> SkillId:
    """A skill somebody has rehearsed, taking one value."""
    skill = f.skill(versions=0)
    version = f.skill_version(steps=(f.step(network_plan=f.network_plan(method="GET", body=None)),))
    skill.add_version(version)
    version.promote(PromotionStage.SHADOW, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)
    return skill.id


def _device(
    uow: FakeUnitOfWork,
    device_id: DeviceId,
    *,
    tenant: TenantId = f.TENANT,
    principal: PrincipalId = f.OPERATOR,
) -> None:
    uow.devices.rows[device_id.value] = AgentDevice(  # type: ignore[attr-defined]
        id=device_id,
        tenant_id=tenant,
        principal_id=principal,
        label=device_id.value,
        extension_version="0.1.0",
        registered_at=f.at(0),
        last_seen_at=f.at(0),
    )


async def _create_watch(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, *, device_id: DeviceId
) -> httpx.Response:
    skill_id = await _teachable_skill(uow)
    _device(uow, device_id)
    return await client.post(
        "/v1/triggers",
        json={
            "skill_id": skill_id.value,
            "kind": "watch",
            "watch": WATCH,
            "device_id": device_id.value,
        },
    )


async def test_the_extension_posts_a_watch_in_the_shape_it_already_speaks(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """A locator on the wire is `strategy`, `query`, `within`, `visible_only`.

    The extension resolves exactly those four on every step it is handed today.
    Inventing a fifth shape here would mean a second resolver in the content
    script, which would drift from the first the week after it was written.
    """
    response = await _create_watch(client, uow, device_id=LENA)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["watch"] == WATCH
    # Derived from where the watch reads, never given separately: two lists of
    # the same names are two lists that can disagree.
    assert body["from_message"] == ["shipment_id"]
    assert body["parameters"] == {}


async def test_a_watch_with_nothing_to_match_on_is_refused_rather_than_stored(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """A watch that knew only where to look would fire on every mail that
    arrives, which is the first stage of an autonomous system going off."""
    skill_id = await _teachable_skill(uow)
    _device(uow, LENA)

    response = await client.post(
        "/v1/triggers",
        json={
            "skill_id": skill_id.value,
            "kind": "watch",
            "watch": {**WATCH, "terms": []},
            "device_id": LENA.value,
        },
    )

    assert response.status_code == 422
    assert uow.triggers.rows == {}


async def test_a_browser_is_never_handed_another_devices_watches(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """Lena's mail rules must not reach Sam's browser, same tenant or not.

    Two operators in one tenant have two mailboxes. A watch handed to the wrong
    browser is a rule about somebody's correspondence being applied to mail
    they were never offered -- and the values it reads would be read out of it.
    """
    created = await _create_watch(client, uow, device_id=LENA)
    assert created.status_code == 201, created.text
    _device(uow, SAM)

    hers = await client.get(f"/v1/agents/{LENA.value}/watches")
    his = await client.get(f"/v1/agents/{SAM.value}/watches")

    assert [trigger["id"] for trigger in hers.json()] == [created.json()["id"]]
    assert his.status_code == 200
    assert his.json() == []


async def test_another_tenant_is_refused_the_browser_it_does_not_own(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """A device id that leaked is otherwise somebody else's mail rules.

    The same ownership check the command channel does: a credential proves who
    is asking, never which browser they may ask about.
    """
    await _create_watch(client, uow, device_id=LENA)

    theirs = await client.get(
        f"/v1/agents/{LENA.value}/watches",
        headers={"Authorization": f"Bearer {token_for(tenant='rival')}"},
    )

    assert theirs.status_code == 404


async def test_a_watch_switched_off_is_left_out_rather_than_sent_with_a_flag(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """A browser that had to remember to check a flag is one that one day does not."""
    created = await _create_watch(client, uow, device_id=LENA)
    trigger_id = created.json()["id"]

    paused = await client.patch(
        f"/v1/triggers/{trigger_id}",
        json={"enabled": False, "reason": "she is on leave"},
    )
    assert paused.status_code == 200

    remaining = await client.get(f"/v1/agents/{LENA.value}/watches")

    assert remaining.json() == []


async def test_the_rules_a_browser_holds_carry_no_mail(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """The only text that ever crosses this boundary is the operator's own term.

    Asserted on the whole document rather than on a named field, because the
    field this is guarding against is the one somebody adds next -- a snippet
    for display, a "last matched" excerpt, a preview.
    """
    await _create_watch(client, uow, device_id=LENA)

    watches = (await client.get(f"/v1/agents/{LENA.value}/watches")).json()

    [only] = watches
    text = {term["contains"] for term in only["watch"]["terms"]}
    assert text == {"dispatch@supplier.test", "Short ship"}
    assert all(set(value) == {"name", "where"} for value in only["watch"]["values"])
    assert set(only["watch"]) == {"host", "terms", "values"}


async def test_a_watch_read_back_matches_the_mail_it_was_written_for(
    container: _FakeContainer, uow: FakeUnitOfWork, client: httpx.AsyncClient
) -> None:
    """What the browser reconstructs is the rule, not a description of one."""
    await _create_watch(client, uow, device_id=LENA)
    ctx = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)

    [trigger] = await container.read_triggers().watches(ctx, device_id=LENA)

    assert trigger.watch is not None
    assert trigger.watch.matches(
        "mail.acme.test", sender="dispatch@supplier.test", subject="Short ship on PO 4471"
    )
    assert not trigger.watch.matches(
        "mail.acme.test", sender="hr@acme.test", subject="Short ship on PO 4471"
    )
