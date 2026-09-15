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
from sro.domain.shared.errors import Conflict
from sro.domain.shared.identifiers import DeviceId
from sro.domain.skill.offers import Offer
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for

LAPTOP = DeviceId("dev-1")
DESKTOP = DeviceId("dev-2")
TABLET = DeviceId("dev-3")
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

    The devices were the exception until `since` broke its tie too. Three of
    them now, planted like the other three kinds: oldest first, then two tied
    on `registered_at` with the LOWER id written first. A read ordering on
    `registered_at` alone is a stable sort, so it hands those two back in the
    order they were written -- which is the answer this fixture is built to
    disagree with.
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
    await uow.devices.add(
        f.device(id=TABLET, label="tablet", registered_at=LATE, last_seen_at=LATE)
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
    # The same instant, said with an offset. `_bound` converts it and the rule
    # has its own test one layer down -- but the ROUTE is what hands the use
    # case its `datetime`, and a route that stripped the tzinfo on the way in
    # passes every naive and every `+00:00` assertion in this file. A bound
    # quietly shifted by five and a half hours does not fail; it returns an
    # audit that starts elsewhere and looks exactly like one that does not.
    shifted = await _since(client, "2026-03-04T14:40:00+05:30")
    assert shifted.json()["since"] == "2026-03-04T09:10:00+00:00"


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
    assert [device["device_id"] for device in body["devices"]] == [TABLET.value, DESKTOP.value]


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
    """Newest first, and two browsers registered in the same instant come back
    in a stable order rather than in whichever one the read happened to find.

    `since` ordered on `registered_at` alone while the audit's other three
    reads all broke their tie -- so the one list assembled from browsers was
    the one an audit read twice could report two different ways, and a reader
    diffing two audits saw a change nobody made. `(registered_at, id)`
    descending, as `workflow_runs.since` and `chats.since` already are.
    """
    body = (await _since(client, DAWN)).json()

    assert [device["device_id"] for device in body["devices"]] == [
        TABLET.value,
        DESKTOP.value,
        LAPTOP.value,
    ]
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
#
# One test per list, each asserting a fully-populated planted row round-trips
# WHOLE. Every field on these four models was otherwise free to come back blank
# -- `AuditOfferModel.of` could hand out `k=0, fate=""` and the suite stayed
# green -- because the tests above read one key each and the plants left most
# of the rest at their defaults, which is what a blanked field looks like.


async def test_a_run_row_says_what_happened(client: httpx.AsyncClient, uow: FakeUnitOfWork) -> None:
    run = _run("run_1", at=EARLY.isoformat())
    run.started_by, run.live, run.outcome = "chat", True, "stopped"
    run.cost_usd, run.unpriced = 0.37, False
    run.steps = [
        RunStep(
            order=0,
            says="save",
            verdict="failed",
            verdict_by="model",
            reason="the page moved under it",
            sent={"kind": "click"},
            matched_by="role",
            stale=True,
        )
    ]
    await uow.workflow_runs.save(run)

    (row,) = (await _since(client, DAWN)).json()["runs"]

    assert row == {
        "id": "run_1",
        "workflow_id": "wfl-1",
        "device_id": LAPTOP.value,
        "started_by": "chat",
        "live": True,
        "started_at": EARLY.isoformat(),
        "finished_at": EARLY.isoformat(),
        "outcome": "stopped",
        "cost_usd": 0.37,
        "unpriced": False,
        "steps": [
            {
                "order": 0,
                # Where in the run, which step of the job, and which thing on
                # the list -- the last two being the same step and no list at
                # all for a job that does one thing once.
                "of_step": 0,
                "item": None,
                "says": "save",
                "verdict": "failed",
                "verdict_by": "model",
                # Why, in the verifier's own words: the most audit-worthy
                # thing on the row when a step did not hold.
                "reason": "the page moved under it",
                "sent": "click",
                "matched_by": "role",
                "stale": True,
                "approved_at": None,
                "approved_by": None,
            }
        ],
    }


async def test_an_offer_row_says_what_was_offered_and_what_became_of_it(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """The desktop's offer, not the laptop's: every other plant in this file
    names the laptop, so a model reading the wrong browser onto the row would
    be indistinguishable from a right one."""
    await uow.offers.record(
        Offer(
            id="off_1",
            tenant="acme",
            workflow_id="wfl-2",
            device_id=DESKTOP.value,
            k=4,
            fate="diverged",
            at=EARLY.isoformat(),
            run_id="run_1",
        )
    )

    (row,) = (await _since(client, DAWN)).json()["offers"]

    assert row == {
        "id": "off_1",
        "workflow_id": "wfl-2",
        "device_id": DESKTOP.value,
        "k": 4,
        "fate": "diverged",
        "run_id": "run_1",
        "at": EARLY.isoformat(),
    }


async def test_a_chat_row_says_what_the_door_cost(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """Two readings, because the two that matter cannot be one row: a reading
    that named a job and was billed for it, and one that failed and could not
    be priced. A single row leaves whichever of `unpriced` and `error` it did
    not carry agreeing with a model that dropped it."""
    await uow.chats.record(
        ChatReading(
            id="cht_1",
            tenant="acme",
            at=EARLY.isoformat(),
            workflow_id="wfl-2",
            cost_usd=0.11,
            unpriced=False,
        )
    )
    await uow.chats.record(
        ChatReading(
            id="cht_2",
            tenant="acme",
            at=LATE.isoformat(),
            unpriced=True,
            error="the model would not answer",
        )
    )

    billed, unpriced = reversed((await _since(client, DAWN)).json()["chats"])

    assert billed == {
        "id": "cht_1",
        "workflow_id": "wfl-2",
        "cost_usd": 0.11,
        "unpriced": False,
        "error": None,
        "at": EARLY.isoformat(),
    }
    assert unpriced == {
        "id": "cht_2",
        # No job: the door read a sentence and could not say which job it meant.
        "workflow_id": None,
        "cost_usd": 0.0,
        "unpriced": True,
        "error": "the model would not answer",
        "at": LATE.isoformat(),
    }


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
    and dropped the flag would put that run on the spend line as free.

    Two runs, and the second is the half this test was missing: with only the
    unpriced one, `cost_usd` hardcoded to `0.0` in the model agreed with the
    assertion, because the fixture's cost WAS zero. Only the flag was ever
    guarded, and the sentence above describes both.
    """
    unpriced = _run("run_1", at=EARLY.isoformat())
    unpriced.cost_usd, unpriced.unpriced = 0.0, True
    await uow.workflow_runs.save(unpriced)
    billed = _run("run_2", at=LATE.isoformat())
    billed.cost_usd, billed.unpriced = 0.37, False
    await uow.workflow_runs.save(billed)

    priced = {
        row["id"]: (row["cost_usd"], row["unpriced"])
        for row in (await _since(client, DAWN)).json()["runs"]
    }

    assert priced == {"run_1": (0.0, True), "run_2": (0.37, False)}


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

    rows = {line["device_id"]: line for line in body["devices"]}
    assert rows[DESKTOP.value]["revoked_at"] is None
    assert rows[LAPTOP.value]["revoked_at"] is not None
    # `registered_at` is a `datetime` on this model, as it is on the roster
    # next door, so pydantic writes it `...Z` rather than `...+00:00`. Compared
    # as an instant: what matters is that it is the browser's own registration
    # and not some other clock.
    #
    # The laptop is the one that can say so. It registered EARLY and was last
    # seen LATE, so a model reading `last_seen_at` into this field is wrong
    # here and right for the desktop, whose two clocks are the same instant.
    assert datetime.fromisoformat(rows[LAPTOP.value]["registered_at"]) == EARLY
    assert datetime.fromisoformat(rows[DESKTOP.value]["registered_at"]) == LATE
    # And nothing else on the row: three fields, and a browser's authority is
    # the whole of what this list is for.
    assert rows[DESKTOP.value] == {
        "device_id": DESKTOP.value,
        "registered_at": "2026-03-01T09:01:40Z",
        "revoked_at": None,
    }


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


# --- what happens when a read underneath refuses ----------------------------


async def test_a_domain_error_beneath_this_door_comes_back_as_a_problem(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, day: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The comment at the top of `routers/audit.py` -- "nothing here catches a
    domain error: `sro.interface.http.errors` maps them once, for every route"
    -- with a test that fails when it stops being true.

    It had none in either file that carries it. `ReadAudit` reads four
    collections in a row, so a route that grew a `try/except DomainError` and
    answered four empty lists would report a quiet morning for a tenant whose
    history could not be read -- the one failure an audit must never be able
    to produce, and one that looks exactly like the truth on every screen that
    draws it.

    Raised at the repository rather than stubbed at the route's own call, so
    what is proved is that a refusal travels the whole way up: `since` on the
    browsers, through the use case, past the router, to the handler.

    The healthy read is taken first, through the same door, so what the 409
    proves is the mapping rather than a route that answers 409 to everything.
    """
    healthy = await _since(client, DAWN)

    async def refuse(*_: object, **__: object) -> tuple[object, ...]:
        raise Conflict("the browsers could not be read")

    monkeypatch.setattr(uow.devices, "since", refuse)
    answered = await _since(client, DAWN)

    assert healthy.status_code == 200
    assert healthy.json()["devices"], "the plant never reached the store"
    assert answered.status_code == 409
    assert answered.headers["content-type"].startswith("application/problem+json")
    # Named, not `.../problems/error`: `problem.type` is how a console tells
    # one refusal from another.
    assert answered.json() == {
        "type": "https://ai-sro.dev/problems/conflict",
        "title": "Conflict",
        "status": 409,
        "detail": "the browsers could not be read",
        "instance": "/v1/audit",
    }
