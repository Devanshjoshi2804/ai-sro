"""The day's bill, and whether it can be trusted.

Ported from `new_agent_arch/src/rig/api.py:663`. The sum itself is plan 2's --
`tests/unit/application/rig/test_spend.py` proves which four tables it comes
out of and where midnight is -- so what is here is everything between that
answer and the wire: that the blind count survives the trip, that the cap is
reported beside the spend, that the day is asked about on the container's
clock, and who is allowed to ask at all.

Nothing here is dated today. Every plant is `f.at(...)` -- March 2026, six
months from the wall clock -- and the container's clock stands at `f.T0`, so a
route that reached for `datetime.now(UTC)` answers $0.00 and zero unpriced
rather than agreeing with these assertions by the calendar. One plant is at
23:00 the night before, which is inside the last twenty-four hours and outside
today: "since midnight UTC" and "in the last day" are different windows and
this is where they differ.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from httpx import ASGITransport

from sro.config import Settings
from sro.domain.chat.reading import ChatReading
from sro.domain.execution.workflow_run import RunStep, WorkflowRun
from sro.domain.shared.identifiers import DeviceId
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests import factories as f
from tests.unit.fakes import FakeClock, FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for

LAPTOP = DeviceId("dev-1")
HERS = "the-secret-the-laptop-was-minted"

CAP = 25.0
"""Deliberately not `Settings().daily_usd_cap`. A route that answered with the
production default -- or with any literal -- passes a cap test written against
the default, and this endpoint exists to say how close today is to the cap
THIS deployment configured."""

LAST_NIGHT = f.at(-10 * 3600)
"""2026-02-28T23:00Z: yesterday, and ten hours before the clock this container
holds. Inside a twenty-four-hour window and outside today's."""


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def container(uow: FakeUnitOfWork) -> _FakeContainer:
    built = _FakeContainer(uow)
    built.settings = Settings(daily_usd_cap=CAP)
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


def _chat(chat_id: str, *, at: str, cost_usd: float = 0.0, unpriced: bool = False) -> ChatReading:
    return ChatReading(id=chat_id, tenant="acme", at=at, cost_usd=cost_usd, unpriced=unpriced)


def _run(run_id: str, *, at: str, cost_usd: float = 0.0, unpriced: bool = False) -> WorkflowRun:
    run = WorkflowRun(
        id=run_id,
        tenant="acme",
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
    run.cost_usd, run.unpriced = cost_usd, unpriced
    return run


@pytest.fixture
async def day(uow: FakeUnitOfWork) -> None:
    """One tenant's morning: $1.75 billed and two calls nobody could price.

    Two tables rather than one, and priced and blind rows in each, so the
    answer disagrees with every obvious wrong sum -- $0.25 (one table), $1.50
    (the other), $100.75 (a day that began twenty-four hours ago). Two blind
    rows rather than one, so a count that came back as a flag is a failure
    rather than a coincidence.
    """
    await uow.chats.record(_chat("cht_1", at=f.at(-3600).isoformat(), cost_usd=0.25))
    await uow.chats.record(_chat("cht_2", at=f.at(-1800).isoformat(), unpriced=True))
    await uow.workflow_runs.save(_run("run_1", at=f.at(-2700).isoformat(), cost_usd=1.50))
    await uow.workflow_runs.save(_run("run_2", at=f.at(-900).isoformat(), unpriced=True))

    await uow.chats.record(_chat("cht_old", at=LAST_NIGHT.isoformat(), cost_usd=99.0))
    await uow.workflow_runs.save(_run("run_old", at=LAST_NIGHT.isoformat(), unpriced=True))


async def _spend(client: httpx.AsyncClient) -> httpx.Response:
    return await client.get("/v1/spend")


def test_these_plants_are_nowhere_near_the_wall_clock() -> None:
    """The sentence this file's first paragraph is written on, made to fail.

    Every assertion below tells the container's clock from a real one only
    because `f.T0` is months from today. Move the plants to now -- which is the
    natural thing to do to a test about *today's* spend -- and a route reading
    `datetime.now(UTC)` passes the lot, which is how a clock mutation survives
    a suite that looks thorough.
    """
    assert abs(datetime.now(UTC) - f.T0) > timedelta(days=2)


# --- what the day says ----------------------------------------------------


async def test_the_day_reports_what_it_could_not_price(
    client: httpx.AsyncClient, day: None
) -> None:
    """Two numbers, because one of them cannot be trusted on its own.

    `789d069` and `11782b4` are on main because a call that never returned was
    being recorded as a free one, and plan 3b's final review found the daily
    cap reading `unpriced` on a roll-up that never carried it. A route that
    answered $1.75 and stopped would throw that away at the last step -- and
    $1.75 is exactly what a day with two unreadable bills in it costs, as far
    as anybody looking at the number alone can tell.
    """
    answered = await _spend(client)

    assert answered.status_code == 200
    assert answered.json() == {"cost_usd": 1.75, "unpriced": 2, "cap_usd": CAP}


async def test_a_day_that_could_not_be_priced_at_all_does_not_read_as_a_free_one(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """$0.00 and two unpriced calls. The measurement run that proved this
    architecture billed $1.12 and every row said free, which is this shape
    exactly -- and a wire that carried only `cost_usd` cannot tell it from a
    morning nobody used."""
    await uow.chats.record(_chat("cht_1", at=f.at(-3600).isoformat(), unpriced=True))
    await uow.workflow_runs.save(_run("run_1", at=f.at(-900).isoformat(), unpriced=True))

    body = (await _spend(client)).json()

    assert (body["cost_usd"], body["unpriced"]) == (0.0, 2)


async def test_a_quiet_day_is_zero_and_not_an_absent_field(client: httpx.AsyncClient) -> None:
    """A tenant that has spent nothing gets three numbers, never a missing one:
    whoever draws this line reads all three, and an absent field is a different
    bug on every screen that renders it."""
    assert (await _spend(client)).json() == {"cost_usd": 0.0, "unpriced": 0, "cap_usd": CAP}


async def test_the_total_is_rounded_where_the_rig_rounded_it(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """The rig rounded every dollar figure it answered with to six places, and
    a sum of floats does not: $0.10 and $0.20 reach a console as
    $0.30000000000000004. Six places is a twentieth of a cent -- nothing a cap
    in dollars can notice, and the difference between a bill and a defect
    report."""
    await uow.chats.record(_chat("cht_1", at=f.at(-3600).isoformat(), cost_usd=0.1))
    await uow.chats.record(_chat("cht_2", at=f.at(-1800).isoformat(), cost_usd=0.2))

    assert (await _spend(client)).json()["cost_usd"] == 0.3


# --- the cap --------------------------------------------------------------


async def test_the_cap_is_reported_beside_the_spend(client: httpx.AsyncClient, day: None) -> None:
    """Without it the console has a number and no scale, and "am I about to be
    cut off" is the only question this endpoint is opened to answer."""
    assert (await _spend(client)).json()["cap_usd"] == CAP


async def test_the_cap_reported_is_the_one_this_deployment_configured(
    client: httpx.AsyncClient,
) -> None:
    """The assertion above is worth nothing if `CAP` is what a route with a
    literal in it would have answered anyway. This is the sentence that keeps
    it: the fixture's cap and the shipped default must differ, so the test
    fails the day somebody makes them the same rather than quietly stopping
    guarding anything."""
    assert Settings().daily_usd_cap != CAP


# --- which day, and whose ---------------------------------------------------


async def test_last_nights_bill_is_not_in_todays(client: httpx.AsyncClient, day: None) -> None:
    """Midnight UTC, not twenty-four hours ago.

    $99.00 was billed at 23:00 last night, which a rolling day would count and
    today does not -- and its blind row with it. A route that took the window
    from anywhere but the day's own midnight answers $100.75 and three.
    """
    body = (await _spend(client)).json()

    assert (body["cost_usd"], body["unpriced"]) == (1.75, 2)


async def test_the_day_is_the_one_this_containers_clock_is_standing_in(
    container: _FakeContainer, client: httpx.AsyncClient, day: None
) -> None:
    """Wind the container's clock back into last night and last night's bill
    comes inside the day: $100.75 and three, where the same plants read on this
    container's own clock are $1.75 and two.

    The answer moving with the clock is the assertion. A route that read a
    clock of its own answers $0.00 to both -- every plant here is six months
    from the wall clock -- and a route with a midnight of its own answers the
    same thing twice.
    """
    container.clock = FakeClock(LAST_NIGHT)

    body = (await _spend(client)).json()

    assert (body["cost_usd"], body["unpriced"]) == (100.75, 3)


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
        body = (await rival.get("/v1/spend")).json()

    assert (body["cost_usd"], body["unpriced"]) == (0.0, 0)


# --- who may ask ----------------------------------------------------------


async def test_a_browser_may_not_read_the_tenants_purse(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, day: None
) -> None:
    """Tenant-only, as in the rig. What the tenant is spending on models is not
    one browser's to read -- and naming itself with its own real secret is the
    only way to reach `tenant_only` at all, since a wrong or half-offered
    secret is refused earlier as a 404.
    """
    await uow.devices.add(f.device(id=LAPTOP, secret=HERS))

    answered = await client.get(
        "/v1/spend",
        params={"device_id": LAPTOP.value},
        headers={"X-Device-Secret": HERS},
    )

    assert answered.status_code == 403
    assert answered.json()["detail"] == "that is the tenant's to do, not a browser's"
    # And the same request without the browser is answered, so the 403 above is
    # the refusal and not this route being absent, unroutable, or 404 for a
    # browser nobody registered.
    assert (await _spend(client)).status_code == 200


async def test_no_credential_is_refused_before_anything_is_read(
    client: httpx.AsyncClient, day: None
) -> None:
    answered = await client.get("/v1/spend", headers={"Authorization": ""})

    assert answered.status_code == 401
