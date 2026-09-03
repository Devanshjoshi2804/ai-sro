"""Creating a watch over HTTP, and a browser asking what its own rules are.

A watch is evaluated in the operator's own browser and nowhere else: no mail is
sent here, so the rule has to go there. That makes two things this boundary
owns. The shape the extension posts has to be the shape it already speaks --
locators are the only interesting part, and it resolves them today from the
command channel. And the endpoint that hands the rules back has to hand each
browser only its own, because a rule about one person's mail in another
person's browser is that mail being read by somebody nobody offered it to.

The third thing is the way back in: a browser saying one matched. It carries
values and nothing else, it may only speak for its own watches, and what it
gets is an offer -- the values the task would run with -- rather than a run.
"""

from __future__ import annotations

import json
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


def _proving(device_id: DeviceId) -> dict[str, str]:
    """The secret that browser was minted at registration.

    Every device-scoped path takes one: the tenant credential the client
    already carries says which tenant is asking and can never say which
    browser, and one of these paths starts a run in a live warehouse.
    """
    return {"X-Device-Secret": f"secret-for-{device_id.value}"}


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
    # Where the two headers are on this operator's mail client, marked in the
    # same act as the value above. Nothing about a mail is derivable: the
    # browser has to be told which node is the sender, or it is guessing.
    "sender_at": {
        "strategy": "css_path",
        "query": "span.from-address",
        "within": None,
        "visible_only": True,
    },
    "subject_at": {
        "strategy": "css_path",
        "query": "h1.subject",
        "within": None,
        "visible_only": True,
    },
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
        secret=f"secret-for-{device_id.value}",
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

    hers = await client.get(f"/v1/agents/{LENA.value}/watches", headers=_proving(LENA))
    his = await client.get(f"/v1/agents/{SAM.value}/watches", headers=_proving(SAM))

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
        headers={
            "Authorization": f"Bearer {token_for(tenant='rival')}",
            **_proving(LENA),
        },
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

    remaining = await client.get(f"/v1/agents/{LENA.value}/watches", headers=_proving(LENA))

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

    watches = (await client.get(f"/v1/agents/{LENA.value}/watches", headers=_proving(LENA))).json()

    [only] = watches
    text = {term["contains"] for term in only["watch"]["terms"]}
    assert text == {"dispatch@supplier.test", "Short ship"}
    assert all(set(value) == {"name", "where"} for value in only["watch"]["values"])
    assert set(only["watch"]) == {"host", "terms", "values", "sender_at", "subject_at"}
    # The two marks are locators and nothing else -- the same four fields a
    # value's `where` carries. A sender is read where one of these points and
    # compared in the browser; what a mail actually said is not here, and there
    # is no field on this shape it could arrive in.
    assert all(
        set(only["watch"][mark]) == {"strategy", "query", "within", "visible_only"}
        for mark in ("sender_at", "subject_at")
    )


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


def _without_instance(response: httpx.Response) -> dict[str, object]:
    problem: dict[str, object] = response.json()
    return {"status": response.status_code, **{k: v for k, v in problem.items() if k != "instance"}}


async def test_a_reported_match_offers_rather_than_running(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """The operator presses once. Recognising a mail is not that press.

    A watch that started a run the moment a mail arrived would be an autonomous
    system that nobody opted into, on the strength of a substring somebody
    typed once -- so what comes back is the offer, and the browser holds it
    until a person acts on it.
    """
    created = await _create_watch(client, uow, device_id=LENA)
    trigger_id = created.json()["id"]

    matched = await client.post(
        f"/v1/agents/{LENA.value}/watches/{trigger_id}/matched",
        json={"shipment_id": "SH-4471"},
        headers=_proving(LENA),
    )

    assert matched.status_code == 200, matched.text
    assert matched.json() == {
        "trigger_id": trigger_id,
        "skill_id": created.json()["skill_id"],
        "values": {"shipment_id": "SH-4471"},
        "missing": [],
    }
    # Nothing started, and nothing was written down: the values came out of
    # somebody's mail and this is the boundary that keeps them out of storage.
    assert container.dispatcher.asked == []
    assert uow.runs.rows == {}


async def test_a_browser_cannot_report_a_match_on_a_watch_that_is_not_its_own(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """Sam's browser reporting on Lena's watch reads exactly like a watch that
    never existed. Telling the two apart would confirm the id is real
    somewhere, which is the whole of what a leaked id is worth.
    """
    created = await _create_watch(client, uow, device_id=LENA)
    trigger_id = created.json()["id"]
    _device(uow, SAM)

    someone_elses = await client.post(
        f"/v1/agents/{SAM.value}/watches/{trigger_id}/matched",
        json={"shipment_id": "SH-4471"},
        headers=_proving(SAM),
    )
    invented = await client.post(
        f"/v1/agents/{SAM.value}/watches/trg-nothing-like-this/matched",
        json={"shipment_id": "SH-4471"},
        headers=_proving(SAM),
    )

    assert someone_elses.status_code == 404
    # `instance` is the path that was asked for and so differs by construction.
    # Everything a caller could read a difference out of -- the status, the
    # code, the sentence -- is one answer.
    assert _without_instance(someone_elses) == _without_instance(invented)
    assert container.dispatcher.asked == []


async def test_another_tenant_cannot_report_a_match_on_a_browser_it_does_not_own(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """The same ownership check the command channel and the rules endpoint do:
    a credential proves who is asking, never which browser they may ask about."""
    created = await _create_watch(client, uow, device_id=LENA)

    theirs = await client.post(
        f"/v1/agents/{LENA.value}/watches/{created.json()['id']}/matched",
        json={"shipment_id": "SH-4471"},
        headers={"Authorization": f"Bearer {token_for(tenant='rival')}", **_proving(LENA)},
    )

    assert theirs.status_code == 404


async def test_a_value_the_watch_never_declared_is_dropped_rather_than_refused(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """A name the watch was never pointed at could name the facility a
    warehouse read runs against, so it does not survive. It is dropped and not
    refused for the reason an inbound relay's extra field is: a rule that has
    worked for a year must not start failing because something upstream added a
    line to its payload.
    """
    created = await _create_watch(client, uow, device_id=LENA)

    matched = await client.post(
        f"/v1/agents/{LENA.value}/watches/{created.json()['id']}/matched",
        json={"shipment_id": "SH-4471", "facility": "another-warehouse", "subject": "Short ship"},
        headers=_proving(LENA),
    )

    assert matched.status_code == 200, matched.text
    assert matched.json()["values"] == {"shipment_id": "SH-4471"}


async def test_a_match_on_a_watch_that_was_switched_off_does_nothing(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """A browser holds its rules and a paused watch is one it should already
    have dropped. Reporting one anyway is the stale copy, not a second way in.
    """
    created = await _create_watch(client, uow, device_id=LENA)
    trigger_id = created.json()["id"]
    paused = await client.patch(
        f"/v1/triggers/{trigger_id}",
        json={"enabled": False, "reason": "she is on leave"},
    )
    assert paused.status_code == 200

    matched = await client.post(
        f"/v1/agents/{LENA.value}/watches/{trigger_id}/matched",
        json={"shipment_id": "SH-4471"},
        headers=_proving(LENA),
    )

    assert matched.status_code == 404
    assert container.dispatcher.asked == []
    assert uow.runs.rows == {}


async def test_an_offer_says_what_the_mail_did_not_say(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """A mail that matched the rule and named no shipment.

    Every mailbox produces some of these -- an autoreply, a thread with the
    number only in an attachment. `FireTrigger` already skips a fire whose
    required inputs are empty, so pressing one produces nothing; the offer says
    so first, because a card that turns out to do nothing is worse than a card
    that says why it cannot.
    """
    created = await _create_watch(client, uow, device_id=LENA)

    matched = await client.post(
        f"/v1/agents/{LENA.value}/watches/{created.json()['id']}/matched",
        json={},
        headers=_proving(LENA),
    )

    assert matched.status_code == 200, matched.text
    assert matched.json()["values"] == {}
    assert matched.json()["missing"] == ["shipment_id"]
    assert container.dispatcher.asked == []


async def test_the_press_runs_with_the_values_the_mail_gave(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """The operator pressed once, and a run started with what they were shown.

    The values travel again rather than being looked up: nothing was written
    down at the match, so the browser that holds the offer is the only place
    they exist. What the run gets is the trigger's own reading of them -- the
    names it declared, and nothing a page invented.
    """
    created = await _create_watch(client, uow, device_id=LENA)

    fired = await client.post(
        f"/v1/agents/{LENA.value}/watches/{created.json()['id']}/fire",
        json={"shipment_id": "SH-4471", "facility": "another-warehouse"},
        headers=_proving(LENA),
    )

    assert fired.status_code == 202, fired.text
    assert fired.json()["run_id"] is not None
    assert fired.json()["skipped"] is None
    assert container.dispatcher.with_values == [{"shipment_id": "SH-4471"}]


async def test_a_press_whose_required_value_is_missing_starts_nothing(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """The press goes through `FireTrigger` like everything else, so the skip
    is the skip that already existed -- reachable, legible, and not routed
    around by a path that had the values in its hand."""
    created = await _create_watch(client, uow, device_id=LENA)

    fired = await client.post(
        f"/v1/agents/{LENA.value}/watches/{created.json()['id']}/fire",
        json={},
        headers=_proving(LENA),
    )

    assert fired.status_code == 202, fired.text
    assert fired.json()["run_id"] is None
    assert fired.json()["skipped"] == "nothing said shipment_id"
    assert container.dispatcher.asked == []


async def test_a_browser_cannot_press_a_watch_that_is_not_its_own(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """The press is a way to start a run, so it is exactly as narrow as the
    report: this tenant's, this device's, enabled, and a watch."""
    created = await _create_watch(client, uow, device_id=LENA)
    trigger_id = created.json()["id"]
    _device(uow, SAM)

    someone_elses = await client.post(
        f"/v1/agents/{SAM.value}/watches/{trigger_id}/fire",
        json={"shipment_id": "SH-4471"},
        headers=_proving(SAM),
    )
    another_tenants = await client.post(
        f"/v1/agents/{LENA.value}/watches/{trigger_id}/fire",
        json={"shipment_id": "SH-4471"},
        headers={"Authorization": f"Bearer {token_for(tenant='rival')}", **_proving(LENA)},
    )

    assert someone_elses.status_code == 404
    assert another_tenants.status_code == 404
    assert container.dispatcher.asked == []
    assert uow.runs.rows == {}


async def test_a_press_on_a_watch_that_was_switched_off_does_nothing(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """An offer outlives the watch it came from: it is held in a browser, and
    the operator may press it tomorrow. A watch switched off in the meantime is
    one the press finds nothing for."""
    created = await _create_watch(client, uow, device_id=LENA)
    trigger_id = created.json()["id"]
    paused = await client.patch(
        f"/v1/triggers/{trigger_id}", json={"enabled": False, "reason": "she is on leave"}
    )
    assert paused.status_code == 200

    fired = await client.post(
        f"/v1/agents/{LENA.value}/watches/{trigger_id}/fire",
        json={"shipment_id": "SH-4471"},
        headers=_proving(LENA),
    )

    assert fired.status_code == 404
    assert container.dispatcher.asked == []


async def test_a_match_is_said_in_the_thread_once_and_carries_names_not_values(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """The operator has to see that a mail matched somewhere that survives the
    panel closing, and the values it matched on must not follow it there.

    `ValueAt` exists so what a watch reads out of somebody's mail stays in the
    browser that read it. A thread is stored, so the message says which names
    were read and leaves the values where they are -- the browser still holds
    them, and the press that starts a run carries them then.
    """
    created = await _create_watch(client, uow, device_id=LENA)
    trigger_id = created.json()["id"]

    for _ in range(2):
        answered = await client.post(
            f"/v1/agents/{LENA.value}/watches/{trigger_id}/matched?offer=off_1",
            json={"shipment_id": "SH-4471"},
            headers=_proving(LENA),
        )
        assert answered.status_code == 200, answered.text

    thread = (await client.get("/v1/threads/current")).json()
    matches = [m for m in thread["messages"] if (m["decision"] or {}).get("kind") == "mail_match"]
    assert len(matches) == 1, "the same offer was said into the thread twice"
    assert matches[0]["decision"]["read"] == ["shipment_id"]
    assert matches[0]["decision"]["offer_id"] == "off_1"
    assert "SH-4471" not in json.dumps(thread), "a value read from a mail was written down"


async def test_a_match_nobody_gave_an_offer_id_for_says_nothing(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """An older extension posts a match with no offer id. It still gets its
    offer back; what it cannot do is have it written once, because there is
    nothing to recognise the second post by -- and a conversation that repeats
    itself is one nobody reads."""
    created = await _create_watch(client, uow, device_id=LENA)
    trigger_id = created.json()["id"]

    answered = await client.post(
        f"/v1/agents/{LENA.value}/watches/{trigger_id}/matched",
        json={"shipment_id": "SH-4471"},
        headers=_proving(LENA),
    )

    assert answered.status_code == 200, answered.text
    thread = (await client.get("/v1/threads/current")).json()
    assert [
        m for m in thread["messages"] if (m["decision"] or {}).get("kind") == "mail_match"
    ] == []
