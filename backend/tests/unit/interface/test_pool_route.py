"""The carryover pool, over the wire.

Ported from `new_agent_arch/src/rig/api.py:794`. The pool's own rules -- the
two clocks, both caps, what re-entering does to an entry's age -- belong to
`tests/integration/test_evidence_repositories.py`, which proves them against
real Postgres. What is here is everything between those two reads and the
wire: that the retired entries are a SECOND list rather than the live one, that
each of them carries why, that the live ones come back oldest first, and who is
allowed to ask.

Nothing here is dated today. Every plant is `f.at(...)` -- March 2026, six
months from the wall clock -- so a route that reached for a clock of its own
rather than serving what the store holds cannot agree with these assertions by
the calendar.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from httpx import ASGITransport

from sro.domain.observation.pool import RETIRED_PASSES, RETIRED_STALE, PoolEntry
from sro.domain.shared.identifiers import DeviceId
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for

LAPTOP = DeviceId("dev-1")
HERS = "the-secret-the-laptop-was-minted"

FIRST = f.at(0).isoformat()
SECOND = f.at(100).isoformat()
THIRD = f.at(200).isoformat()


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


def _plant(
    uow: FakeUnitOfWork,
    gesture_id: str,
    *,
    at: str,
    age: int = 0,
    waited: int = 0,
    reason: str = "",
    tenant: str = "acme",
) -> None:
    """One entry, straight into the store.

    Through the rows rather than through `add_unclaimed` and seven calls to
    `age`, for the reason `test_spend_and_audit_reads.py` plants intent rows
    directly: the repository takes its instants off its own clock, so there is
    no other way to put an entry in at a chosen moment with a chosen age -- and
    which cap retired something is exactly what this door is opened to report.

    `reason != ""` IS retirement, here as everywhere: the boolean the row also
    carries is written from the same decision and is never the record's own
    answer.
    """
    entry = PoolEntry(
        gesture_id=gesture_id,
        tenant=tenant,
        age=age,
        entered_at=at,
        reason=reason,
        waited=waited,
    )
    uow.pool.rows[(tenant, gesture_id)] = entry
    if reason:
        uow.pool.retired_ids.add((tenant, gesture_id))


@pytest.fixture
async def pooled(uow: FakeUnitOfWork) -> None:
    """Three live entries and two retired ones, in one tenant.

    The live three go in NEWEST first, so reading them back in the order the
    store was written in is a failure rather than a coincidence -- this plan
    has twice shipped a route that re-ordered a list and passed its whole suite
    because the wanted answer happened to be insertion order.

    Two retired, under the two different caps, because a route that reported
    one reason for everything agrees with a single-entry test.
    """
    _plant(uow, "ges_3", at=THIRD, age=3, waited=1)
    _plant(uow, "ges_2", at=SECOND, age=2, waited=4)
    _plant(uow, "ges_1", at=FIRST, age=1, waited=6)

    _plant(uow, "ges_old", at=FIRST, age=7, waited=2, reason=RETIRED_PASSES)
    _plant(uow, "ges_stale", at=SECOND, age=1, waited=9, reason=RETIRED_STALE)


# --- the two lists --------------------------------------------------------


async def test_a_retired_entry_is_on_its_own_list_and_says_which_cap_took_it(
    client: httpx.AsyncClient, pooled: None
) -> None:
    """The whole reason this door was opened. `retired` is the record
    `pool.py` says must exist, and nothing over the wire could read it: a pass
    whose window quietly stopped carrying yesterday's tail looked exactly like
    one that had nothing left to carry.

    The reason is what makes the two lists different -- an entry is retired
    exactly when it has one -- so a `retired` list served out of `waiting`,
    or served with the reason blanked, is not this list at all.
    """
    body = (await client.get("/v1/pool")).json()

    assert [entry["gesture_id"] for entry in body["retired"]] == ["ges_old", "ges_stale"]
    assert [entry["reason"] for entry in body["retired"]] == [RETIRED_PASSES, RETIRED_STALE]
    # And not on the live list, which is the other half of "two reads": a route
    # answering one read twice satisfies every assertion above.
    assert "ges_old" not in [entry["gesture_id"] for entry in body["waiting"]]
    assert "ges_stale" not in [entry["gesture_id"] for entry in body["waiting"]]


async def test_a_retired_row_comes_back_whole(client: httpx.AsyncClient, pooled: None) -> None:
    """Every field at a value nothing defaults to, and the two clocks at
    DIFFERENT values: `age` counts readings this entry was shown, `waited`
    counts passes it was passed over, and a model that read one into both is
    right about half of every row."""
    body = (await client.get("/v1/pool")).json()

    assert body["retired"][0] == {
        "gesture_id": "ges_old",
        "age": 7,
        "waited": 2,
        "entered_at": FIRST,
        "reason": RETIRED_PASSES,
    }


async def test_the_live_entries_come_back_oldest_first(
    client: httpx.AsyncClient, pooled: None
) -> None:
    """The order the next pass will draw them in, and the order the repository
    promises. Three rows and not two: two agree with a route that reversed the
    list as readily as with one that did not."""
    body = (await client.get("/v1/pool")).json()

    assert [entry["gesture_id"] for entry in body["waiting"]] == ["ges_1", "ges_2", "ges_3"]
    assert [entry["entered_at"] for entry in body["waiting"]] == [FIRST, SECOND, THIRD]


async def test_a_live_row_carries_both_clocks_and_no_reason(
    client: httpx.AsyncClient, pooled: None
) -> None:
    """`reason` is empty while an entry is live, and empty is not absent:
    there is no `retired` field on either list, so the reason IS the flag and
    a reader that concatenates the two can still tell them apart."""
    body = (await client.get("/v1/pool")).json()

    assert body["waiting"][0] == {
        "gesture_id": "ges_1",
        "age": 1,
        "waited": 6,
        "entered_at": FIRST,
        "reason": "",
    }


async def test_reading_the_pool_does_not_move_it(client: httpx.AsyncClient, pooled: None) -> None:
    """`age` is the pass's to call, once per pass. A door that aged what it
    looked at would retire evidence for being read about -- and would do it
    silently, since the second read is the one that looks wrong."""
    once = (await client.get("/v1/pool")).json()
    twice = (await client.get("/v1/pool")).json()

    assert once == twice
    assert [entry["age"] for entry in twice["waiting"]] == [1, 2, 3]
    assert len(twice["retired"]) == 2


async def test_an_empty_pool_is_two_empty_lists_and_not_two_absent_keys(
    client: httpx.AsyncClient,
) -> None:
    answered = await client.get("/v1/pool")

    assert answered.status_code == 200
    assert answered.json() == {"waiting": [], "retired": []}


# --- whose pool it is -----------------------------------------------------


async def test_another_tenants_credential_reads_its_own_nothing(
    container: _FakeContainer, uow: FakeUnitOfWork, pooled: None
) -> None:
    """Keyed by tenant, which is the whole mechanism the pool exists for: one
    operator's Blue Yonder half meets another operator's SAP half because they
    share a tenant, and never because they share a server.

    Two tenants, because a route that dropped the tenant -- or hardcoded
    `acme` -- passes every other assertion in this file. The rival has a pool
    of its own, so what is proved is that this read is scoped and not that it
    is empty.
    """
    _plant(uow, "ges_theirs", at=FIRST, tenant="rival")
    _plant(uow, "ges_theirs_old", at=FIRST, tenant="rival", reason=RETIRED_STALE)

    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_for(tenant='rival')}"},
    ) as rival:
        body = (await rival.get("/v1/pool")).json()

    assert [entry["gesture_id"] for entry in body["waiting"]] == ["ges_theirs"]
    assert [entry["gesture_id"] for entry in body["retired"]] == ["ges_theirs_old"]


async def test_no_credential_is_refused_before_anything_is_read(
    client: httpx.AsyncClient, pooled: None
) -> None:
    """And the same door answers with a credential, in the same test: a 401
    asserted alone passes against a route nobody registered."""
    refused = await client.get("/v1/pool", headers={"Authorization": ""})
    served = await client.get("/v1/pool")

    assert refused.status_code == 401
    assert served.status_code == 200
    assert served.json()["waiting"], "the refusal is not this route being absent"


async def test_a_browser_carrying_its_own_secret_is_still_served(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, pooled: None
) -> None:
    """The credential and nothing else, which is what the rig's `authorised`
    meant on this route.

    Not `TenantOnly`. The extension sends `X-Device-Secret` on every request it
    makes, and `asking_device` answers a secret with no `?device_id=` with a
    404 -- so a tenant-only pool would be 404 for the one caller that has a
    pool to read about. Nothing here is per browser: the pool is keyed by
    tenant, and this is the same answer either way.

    Both reads in one test, so what is pinned is that the header changes
    nothing rather than that some request somewhere succeeds.
    """
    await uow.devices.add(f.device(id=LAPTOP, secret=HERS))

    with_header = await client.get("/v1/pool", headers={"X-Device-Secret": HERS})
    named = await client.get(
        "/v1/pool", params={"device_id": LAPTOP.value}, headers={"X-Device-Secret": HERS}
    )
    plain = await client.get("/v1/pool")

    assert with_header.status_code == named.status_code == 200
    assert with_header.json() == named.json() == plain.json()
    assert plain.json()["waiting"], "the plant never reached the store"
