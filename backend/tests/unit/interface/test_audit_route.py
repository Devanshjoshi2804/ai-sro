"""The door onto what happened: four lists, one tenant, one bound.

Ported from `new_agent_arch/src/rig/api.py:1366`. The reads and the bound have
their own tests in `tests/unit/application/rig/test_audit.py`; what is here is
everything that can go wrong between the use case's answer and the wire -- the
bound the answer names, the order each of the four lists comes back in, which
run's approval landed on which step, and who is allowed to ask at all.

Over the whole stack down to the in-memory store, through the `client` fixture,
because that is where those break: a use-case test cannot see a router that
sorted a list on the way out, echoed the query string it was handed, or was
never given `tenant_only`.

Nothing here is dated today. Every plant is `f.at(...)` -- March 2026, six
months from the wall clock -- so a route that reached for `datetime.now(UTC)`
instead of the bound it was given answers four empty lists rather than agreeing
with these assertions by the calendar.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime

import httpx
import pytest
from httpx import ASGITransport

from sro.domain.chat.reading import ChatReading
from sro.domain.execution.workflow_run import RunStep, WorkflowRun
from sro.domain.shared.identifiers import DeviceId
from sro.domain.skill.offers import Offer
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for

LAPTOP = DeviceId("dev-1")
DESKTOP = DeviceId("dev-2")
HERS = "the-secret-the-laptop-was-minted"

EARLY = f.at(0)
LATE = f.at(100)
DAWN = f.at(-60).isoformat()
"""Before every plant below, so a read taking this bound returns all of them."""

MIDDAY = f.at(50).isoformat()
"""Between the two instants everything is planted at, in all four tables."""


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def container(uow: FakeUnitOfWork) -> _FakeContainer:
    return _FakeContainer(uow)


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


def _run(run_id: str, *, at: str, tenant: str = "acme") -> WorkflowRun:
    return WorkflowRun(
        id=run_id,
        tenant=tenant,
        workflow_id="wfl-1",
        device_id=LAPTOP.value,
        values={},
        started_by="offer",
        live=True,
        allow_focus=True,
        started_at=at,
        finished_at=at,
        outcome="held",
        steps=[RunStep(order=0, says="save", verdict="held", verdict_by="status")],
    )


def _offer(offer_id: str, *, at: str, tenant: str = "acme") -> Offer:
    return Offer(
        id=offer_id,
        tenant=tenant,
        workflow_id="wfl-1",
        device_id=LAPTOP.value,
        k=2,
        fate="accepted",
        at=at,
    )


def _chat(chat_id: str, *, at: str, tenant: str = "acme") -> ChatReading:
    return ChatReading(id=chat_id, tenant=tenant, at=at, workflow_id="wfl-1", cost_usd=0.01)


@pytest.fixture
async def day(uow: FakeUnitOfWork) -> None:
    """One tenant's morning, planted so the wanted answer is the REVERSE of the
    order the store was written in -- in all four tables at once.

    This plan has now twice shipped a route that re-ordered a list and passed
    its whole suite, because the expected answer happened to be insertion
    order. So the oldest row of each kind goes in first, and the two newest go
    in tied on the instant with the LOWER id first: every one of these four
    lists is newest-first with `(instant, id)` as the tiebreak, which is what
    the store's `ORDER BY ... DESC` gives at these row counts, and reading them
    back in the order they were written is a failure rather than a coincidence.

    The devices are the exception, and deliberately: `since` orders them on
    `registered_at` alone, so two browsers registered in the same instant have
    no order anybody promised and there is nothing here to assert. They are
    planted a hundred seconds apart, oldest first.
    """
    early, late = EARLY.isoformat(), LATE.isoformat()

    await uow.workflow_runs.save(_run("run_1", at=early))
    await uow.workflow_runs.save(_run("run_2", at=late))
    await uow.workflow_runs.save(_run("run_3", at=late))

    await uow.offers.record(_offer("off_1", at=early))
    await uow.offers.record(_offer("off_2", at=late))
    await uow.offers.record(_offer("off_3", at=late))

    await uow.chats.record(_chat("cht_1", at=early))
    await uow.chats.record(_chat("cht_2", at=late))
    await uow.chats.record(_chat("cht_3", at=late))

    await uow.devices.add(f.device(id=LAPTOP, secret=HERS, registered_at=EARLY, last_seen_at=LATE))
    await uow.devices.add(
        f.device(id=DESKTOP, label="desktop", registered_at=LATE, last_seen_at=LATE)
    )


async def _since(client: httpx.AsyncClient, when: str) -> httpx.Response:
    return await client.get("/v1/audit", params={"since": when})


# --- the bound ------------------------------------------------------------


async def test_the_audit_answers_with_the_bound_it_actually_used(
    client: httpx.AsyncClient,
) -> None:
    """A caller that passes a naive time is told, in UTC, what that was taken
    to mean -- which is the whole reason `Audit.since` is handed back rather
    than echoed from the query string.

    Naive on purpose: a route that echoed what it was sent is indistinguishable
    from this one for every caller that already wrote an offset, and those are
    the callers a route is usually tested with.
    """
    answered = await _since(client, "2026-03-04T09:10:00")

    assert answered.status_code == 200
    assert answered.json()["since"] == "2026-03-04T09:10:00+00:00"


async def test_the_audit_needs_a_bound(client: httpx.AsyncClient, day: None) -> None:
    """The rig's "no since means everything" is not ported.

    An unbounded audit over a real tenant is a table scan nobody meant to run,
    and every caller with a reason to be here has a window in hand. A 422 and
    not a default: a route that quietly picked one would answer a question it
    was not asked.
    """
    answered = await client.get("/v1/audit")

    assert answered.status_code == 422


async def test_a_time_nobody_can_read_is_refused_and_not_answered_as_an_empty_day(
    client: httpx.AsyncClient, day: None
) -> None:
    """The rig's rule, kept: on an audit route "nothing happened" is the wrong
    way to fail. There is a whole morning in the store, and a `since` that
    cannot be parsed must not come back looking like a quiet one.
    """
    answered = await client.get("/v1/audit", params={"since": "last tuesday"})

    assert answered.status_code == 422
    assert "since" in answered.text
    # And the morning really is there, so the 422 above is about the time and
    # not about an empty store.
    assert (await _since(client, DAWN)).json()["runs"]


async def test_nothing_before_the_bound_is_in_the_answer(
    client: httpx.AsyncClient, day: None
) -> None:
    """The argument that must reach the use case, checked in all four lists.

    A route that passed its own instant, a literal, or nothing at all returns
    strictly more or strictly less than this -- and "strictly more" is the
    failure that reads as a working audit right up until somebody trusts it to
    say what happened this morning.
    """
    body = (await _since(client, MIDDAY)).json()

    assert [run["id"] for run in body["runs"]] == ["run_3", "run_2"]
    assert [offer["id"] for offer in body["offers"]] == ["off_3", "off_2"]
    assert [chat["id"] for chat in body["chats"]] == ["cht_3", "cht_2"]
    assert [device["device_id"] for device in body["devices"]] == [DESKTOP.value]


# --- the four lists -------------------------------------------------------


async def test_the_runs_come_back_newest_first(client: httpx.AsyncClient, day: None) -> None:
    body = (await _since(client, DAWN)).json()

    assert [run["id"] for run in body["runs"]] == ["run_3", "run_2", "run_1"]


async def test_the_offers_come_back_newest_first(client: httpx.AsyncClient, day: None) -> None:
    body = (await _since(client, DAWN)).json()

    assert [offer["id"] for offer in body["offers"]] == ["off_3", "off_2", "off_1"]


async def test_the_chats_come_back_newest_first(client: httpx.AsyncClient, day: None) -> None:
    body = (await _since(client, DAWN)).json()

    assert [chat["id"] for chat in body["chats"]] == ["cht_3", "cht_2", "cht_1"]


async def test_the_browsers_come_back_newest_first(client: httpx.AsyncClient, day: None) -> None:
    body = (await _since(client, DAWN)).json()

    assert [device["device_id"] for device in body["devices"]] == [DESKTOP.value, LAPTOP.value]
    # And no `online`, which is the one field the roster next door carries and
    # this list must not: a socket held right now is a fact about this second,
    # not about the window that was asked for, and an audit read a week later
    # would report it as though it had been true then.
    assert "online" not in body["devices"][0]


async def test_a_tenant_with_a_quiet_morning_gets_four_empty_lists(
    client: httpx.AsyncClient,
) -> None:
    """Four keys, always, and never a missing one: whoever draws this reads all
    four, and a list that is absent rather than empty is a different bug on
    every screen that renders it."""
    body = (await _since(client, DAWN)).json()

    assert body["runs"] == body["offers"] == body["devices"] == body["chats"] == []


# --- what a row says ------------------------------------------------------


async def test_a_step_says_what_kind_of_thing_was_sent_and_not_what_was_in_it(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """Ported from the rig's `sent.get("kind")`.

    The payload is the warehouse's own data and this list is read by whoever
    holds a tenant credential; what the audit owes them is that a click went
    out, at a time, on a step. A model that serialised `sent` whole would put
    an order number on that screen and nothing would look wrong.
    """
    run = _run("run_1", at=EARLY.isoformat())
    run.steps = [
        RunStep(
            order=0,
            says="save",
            verdict="held",
            verdict_by="status",
            sent={"kind": "click", "selector": "#saveButton", "value": "ACME-4471"},
        )
    ]
    await uow.workflow_runs.save(run)

    answered = await _since(client, DAWN)

    (step,) = answered.json()["runs"][0]["steps"]
    assert step["sent"] == "click"
    assert "ACME-4471" not in answered.text
    assert "saveButton" not in answered.text


async def test_a_step_nobody_planned_a_command_for_says_so(
    client: httpx.AsyncClient, day: None
) -> None:
    """Null rather than the empty string: a step with nothing planned did not
    send a command with no kind."""
    (step,) = (await _since(client, DAWN)).json()["runs"][0]["steps"]

    assert step["sent"] is None


async def test_a_run_nobody_could_price_says_so_beside_its_zero(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """`cost_usd: 0.0` and `unpriced: true` is a run that did not cost nothing
    -- it is one nobody could put a number on. A model that carried the cost
    and dropped the flag would put that run on the spend line as free."""
    run = _run("run_1", at=EARLY.isoformat())
    run.cost_usd, run.unpriced = 0.0, True
    await uow.workflow_runs.save(run)

    (row,) = (await _since(client, DAWN)).json()["runs"]

    assert (row["cost_usd"], row["unpriced"]) == (0.0, True)


async def test_an_approval_lands_on_the_step_a_person_actually_approved(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """Two steps, and only the second approved.

    `AuditedRun` carries approvals beside the run and the wire folds them onto
    their step, which is a join -- and a join with one step in the run agrees
    with itself however it is written. What must never happen is an approval
    appearing against a step nobody tapped for: that is a record saying a
    person let a write out when they did not.
    """
    run = _run("run_1", at=EARLY.isoformat())
    run.steps = [
        RunStep(order=0, says="open", verdict="held", verdict_by="status"),
        RunStep(order=1, says="save", verdict="held", verdict_by="status"),
    ]
    await uow.workflow_runs.save(run)
    await uow.workflow_runs.approve("run_1", 1, at=LATE.isoformat(), device_id=LAPTOP.value)

    steps = (await _since(client, DAWN)).json()["runs"][0]["steps"]

    assert [step["approved_at"] for step in steps] == [None, LATE.isoformat()]
    assert [step["approved_by"] for step in steps] == [None, LAPTOP.value]
    # `order`, not the rig's `ord`, which was its column name: the field is
    # `RunStep.order` here, and it is the key the fold above is done on -- a
    # wire name that disagreed with the domain is how an approval ends up
    # against the wrong step.
    assert [step["order"] for step in steps] == [0, 1]


async def test_one_runs_approval_is_not_shown_against_another_runs_step(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """Both runs have a step at ord 0 and only one of them was approved."""
    await uow.workflow_runs.save(_run("run_1", at=EARLY.isoformat()))
    await uow.workflow_runs.save(_run("run_2", at=LATE.isoformat()))
    await uow.workflow_runs.approve("run_2", 0, at=LATE.isoformat(), device_id=LAPTOP.value)

    approved = {
        run["id"]: run["steps"][0]["approved_at"]
        for run in (await _since(client, DAWN)).json()["runs"]
    }

    assert approved == {"run_2": LATE.isoformat(), "run_1": None}


async def test_a_browsers_row_says_when_its_authority_began_and_ended(
    client: httpx.AsyncClient, client_revoking: None, day: None
) -> None:
    """`revoked_at` is the one fact the runs and the offers cannot carry: a
    browser that acted this morning and was cut off at noon looks, in those two
    lists, exactly like one that is still trusted."""
    body = (await _since(client, DAWN)).json()

    ended = {line["device_id"]: line["revoked_at"] for line in body["devices"]}
    assert ended[DESKTOP.value] is None
    assert ended[LAPTOP.value] is not None
    # `registered_at` is a `datetime` on this model, as it is on the roster
    # next door, so pydantic writes it `...Z` rather than `...+00:00`. Compared
    # as an instant: what matters is that it is the browser's own registration
    # and not some other clock.
    assert datetime.fromisoformat(body["devices"][0]["registered_at"]) == LATE


@pytest.fixture
async def client_revoking(client: httpx.AsyncClient, day: None) -> None:
    await client.post(f"/v1/devices/{LAPTOP.value}/revoke")


# --- who may ask ----------------------------------------------------------


async def test_a_browser_may_not_read_the_tenants_audit(
    client: httpx.AsyncClient, day: None
) -> None:
    """Tenant-only, as in the rig. Every browser's runs, every browser's
    refusals and the tenant's chat bill are not one browser's to read -- and
    naming itself with its own real secret is the only way to reach
    `tenant_only` at all, since a wrong or half-offered secret is refused
    earlier as a 404.
    """
    answered = await client.get(
        "/v1/audit",
        params={"since": DAWN, "device_id": LAPTOP.value},
        headers={"X-Device-Secret": HERS},
    )

    assert answered.status_code == 403
    assert answered.json()["detail"] == "that is the tenant's to do, not a browser's"


async def test_no_credential_is_refused_before_anything_is_read(
    client: httpx.AsyncClient, day: None
) -> None:
    answered = await client.get("/v1/audit", params={"since": DAWN}, headers={"Authorization": ""})

    assert answered.status_code == 401


async def test_another_tenants_credential_reads_its_own_nothing(
    container: _FakeContainer, day: None
) -> None:
    """The tenant comes off the credential and never off a literal. Two
    tenants, because a route that hardcoded `acme` -- or read the tenant off
    anything but `ctx` -- passes every other assertion in this file."""
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_for(tenant='rival')}"},
    ) as rival:
        body = (await rival.get("/v1/audit", params={"since": DAWN})).json()

    assert body["runs"] == body["offers"] == body["devices"] == body["chats"] == []
    assert body["since"] == DAWN
