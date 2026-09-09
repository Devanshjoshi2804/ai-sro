"""`POST /v1/mine`: who may ask, what it costs them, and what comes back.

The pass itself is proved in `tests/unit/application/rig/test_mine_pass.py`.
What is here is the wire: that a deployment with no model answers 503 rather
than a quiet empty pass, that a tenant over its cap answers 429, that every
figure the pass measured survives the trip -- `learned_parameters` above all,
which had no column at all until migration 0041 -- and that a browser's secret
does not open the tenant's purse.

Nothing is dated today. The container's clock stands in February 2025, six
months from any wall clock this runs against, so a route that reached for
`datetime.now(UTC)` bills a different day than the one asserted here.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from httpx import ASGITransport

from sro.config import Settings
from sro.domain.chat.reading import ChatReading
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.shared.prices import Answer
from sro.infrastructure.db.codec import when
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests import factories as f
from tests.unit.domain.rig.conftest import gestures as _gestures
from tests.unit.fakes import FakeAsker, FakeClock, FakeGestureRepository, FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for

TENANT = TenantId("acme")
HOST = "http://127.0.0.1:63319"
LAPTOP = DeviceId("dev-1")
HERS = "the-secret-the-laptop-was-minted"

NOW = datetime(2025, 2, 11, 23, 0, tzinfo=UTC)
CAP = 5.0

MODEL = "gemini-3.1-flash-preview"
"""Deliberately not the shipped `gemini_mine_model`, so a route wired to a
literal -- or to the wrong one of the three model settings Task 1 added --
fails rather than agreeing with the default."""


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def container(uow: FakeUnitOfWork) -> _FakeContainer:
    built = _FakeContainer(uow)
    built.settings = Settings(daily_usd_cap=CAP, gemini_mine_model=MODEL, _env_file=None)
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


def _proposal(cites: list[str], **over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "title": "create a work operation",
        "narrative": "the operator created a work operation",
        "systems": [HOST],
        "steps": [{"order": 0, "cites": cites, "says": "do it", "system": HOST, "parameters": []}],
        "parameters": [],
        "same_as": None,
        "unproven": [],
    }
    return {**base, **over}


def _answer(*proposals: dict[str, object], **over: object) -> Answer:
    return Answer(data={"workflows": list(proposals)}, cost_usd=0.01, **over)  # type: ignore[arg-type]


def _fat_day(count: int) -> list[Gesture]:
    """A day bigger than one window, built from the fixture's own rows.

    The gesture carrying calls is the fat one -- `as_evidence` caps each item
    at `K_MAX_GESTURE_TOKENS`, so bulk comes from repeating its calls rather
    than from a long string, which `trim` would clip. All identical and all
    weak in the same way, so `pack` fills to the budget and the remainder is
    the budget's decision rather than a strength tie nobody planted.
    """
    writing = next(g for g in _gestures(TENANT.value) if g.requests)
    fat = replace(writing, requests=tuple(list(writing.requests) * 10))
    return [replace(fat, id=f"ges_fat_{i:03d}", at=1000.0 + i) for i in range(count)]


def _rows(uow: FakeUnitOfWork) -> dict[str, Gesture]:
    assert isinstance(uow.gestures, FakeGestureRepository)
    return uow.gestures.rows


def test_this_containers_clock_is_nowhere_near_the_wall_clock() -> None:
    assert abs(datetime.now(UTC) - NOW) > timedelta(days=2)


# --- the two refusals -------------------------------------------------------


async def test_a_deployment_with_no_model_says_so_rather_than_mining_nothing(
    client: httpx.AsyncClient, day: list[str]
) -> None:
    """503, not a 200 describing an empty pass. `_FakeContainer.asker` is
    `None`, which is what a deployment with no key has, and a miner with
    nothing to ask that ran and found nothing reads exactly like a quiet day.
    """
    answered = await client.post("/v1/mine")

    assert answered.status_code == 503
    assert "gemini_api_key" in answered.text
    assert "interpretation_enabled" in answered.text


async def test_a_tenant_over_its_cap_is_told_to_come_back_later(
    container: _FakeContainer, client: httpx.AsyncClient, uow: FakeUnitOfWork, day: list[str]
) -> None:
    """429 and not 402 or 403: nothing about the request is wrong and it will
    be accepted tomorrow. The body names both numbers, so whoever reads it
    knows whether to raise the cap or to go and find the unpriced call."""
    container.asker = FakeAsker(_answer(_proposal(day[:2])))
    await uow.chats.record(
        ChatReading(
            id="cht_1", tenant=TENANT.value, at=NOW.replace(hour=10).isoformat(), cost_usd=5.01
        )
    )

    answered = await client.post("/v1/mine")

    assert answered.status_code == 429
    body = answered.json()
    assert body["type"] == "https://ai-sro.dev/problems/over_cap"
    assert "$5.0100 of $5.00" in body["detail"]
    assert await uow.workflows.passes(TENANT) == (), "the refusal billed a row of its own"


async def test_the_cap_the_door_judges_against_is_the_configured_one(
    container: _FakeContainer, client: httpx.AsyncClient, uow: FakeUnitOfWork, day: list[str]
) -> None:
    """Asked twice, against two caps. One cap proves only that the route does
    not answer the other number; the answer having to move is what no literal
    can do."""
    container.asker = FakeAsker(_answer(_proposal(day[:2])))
    await uow.chats.record(
        ChatReading(
            id="cht_1", tenant=TENANT.value, at=NOW.replace(hour=10).isoformat(), cost_usd=5.01
        )
    )
    assert (await client.post("/v1/mine")).status_code == 429

    container.settings = Settings(daily_usd_cap=50.0, gemini_mine_model=MODEL, _env_file=None)

    assert (await client.post("/v1/mine")).status_code == 200


# --- what comes back --------------------------------------------------------


async def test_every_figure_the_pass_measured_reaches_the_wire(
    container: _FakeContainer, client: httpx.AsyncClient, day: list[str]
) -> None:
    """One proposal kept, one refused, so `proposed`, `kept` and the two lists
    are four different answers rather than the same one four times.

    `thought_tokens` is inside `out_tokens` and is reported beside it anyway:
    140 and 40, not 180, so a body that added them fails here.
    """
    container.asker = FakeAsker(
        _answer(
            _proposal(day[:2]),
            _proposal(["ges_invented"]),
            in_tokens=900,
            out_tokens=140,
            thought_tokens=40,
        )
    )

    answered = await client.post("/v1/mine")

    assert answered.status_code == 200, answered.text
    body = answered.json()
    assert body["pass_id"].startswith("pas_")
    assert body["error"] is None
    assert (body["proposed"], body["kept"], body["learned_parameters"]) == (2, 1, 0)
    assert (body["window_size"], body["left_out"], body["lost_pool"]) == (len(day), 0, [])
    assert body["rejections"] == [
        {
            "workflow_title": "create a work operation",
            "reason": body["rejections"][0]["reason"],
            "detail": body["rejections"][0]["detail"],
        }
    ]
    assert body["rejections"][0]["reason"]
    assert [one["kind"] for one in body["resolutions"]] == ["new"]
    assert body["resolutions"][0]["workflow_id"] is None
    assert body["resolutions"][0]["contains"] is False
    # Three different numbers and the verdict beside them, so a body that
    # crossed two of them -- `gini` answered as `coverage`, which is the shape
    # of the mistake a nested model invites -- fails rather than passing on a
    # key set that is still correct.
    assert body["coverage"] == pytest.approx(
        {"coverage": 2 / 7, "skew": 1.0, "gini": 0.8, "lopsided": True}
    )
    assert (body["in_tokens"], body["out_tokens"], body["thought_tokens"]) == (900, 140, 40)
    assert (body["cost_usd"], body["unpriced"]) == (0.01, False)


async def test_the_bill_is_not_rounded_on_the_way_out(
    container: _FakeContainer, client: httpx.AsyncClient, day: list[str]
) -> None:
    """A deliberate divergence from the rig, which rounded to six places in the
    route. Rounding for display is the reader's job; a bill rounded on the way
    out cannot be summed against the `mining_passes` row it came from -- and
    `/v1/spend`, which does round, sums the raw figure."""
    container.asker = FakeAsker(
        Answer(data={"workflows": [_proposal(day[:2])]}, cost_usd=0.0123456789)
    )

    assert (await client.post("/v1/mine")).json()["cost_usd"] == 0.0123456789


async def test_a_pass_that_learnt_something_says_so_on_the_wire(
    container: _FakeContainer, client: httpx.AsyncClient, uow: FakeUnitOfWork, day: list[str]
) -> None:
    """The field with the shortest history and the most to lose: until 0041
    every pass computed it and the persistence layer discarded it. A body that
    dropped it would leave a pass that recognised nothing new and widened two
    parameters reading as a wasted call.

    Two doings, because one cannot tell a parameter from a constant -- so the
    number is earned rather than planted, and `kept == 0` beside it is the
    whole point.
    """
    original = [_rows(uow)[gesture_id] for gesture_id in day]
    container.asker = FakeAsker(_answer(_proposal(day)))
    first = (await client.post("/v1/mine")).json()
    assert first["learned_parameters"] == 0
    # And the other side of `lopsided`: this proposal cites the whole window,
    # so the verdict is False here and True in the test above. A field wired to
    # a constant satisfies one of the two and never both.
    assert first["coverage"] == pytest.approx(
        {"coverage": 1.0, "skew": 1 / 7, "gini": 0.3, "lopsided": False}
    )

    again = [
        replace(
            row,
            id=f"{row.id}_again",
            at=row.at + 10_000.0,
            action=(
                replace(row.action, value="SOMETHING-ELSE")
                if row.action.kind == "type" and row.action.value
                else row.action
            ),
        )
        for row in original
    ]
    await uow.gestures.add_gestures(tuple(again))
    container.asker = FakeAsker(_answer(_proposal([row.id for row in again])))

    body = (await client.post("/v1/mine")).json()

    assert body["kept"] == 0
    assert body["learned_parameters"] >= 1


async def test_the_model_asked_is_the_one_this_deployment_configured(
    container: _FakeContainer, client: httpx.AsyncClient, day: list[str]
) -> None:
    """Three model settings landed together in Task 1 and the mining one is
    the only one this door may spend on."""
    asked = FakeAsker(_answer(_proposal(day[:2])))
    container.asker = asked

    await client.post("/v1/mine")

    assert [one["model"] for one in asked.asked] == [MODEL]


async def test_a_pass_whose_model_call_failed_is_not_answered_as_a_quiet_day(
    container: _FakeContainer, client: httpx.AsyncClient, day: list[str]
) -> None:
    """`error` and `unpriced` both carry something other than their default.

    Not hypothetical. `mining_passes` on the real store already holds a pass
    from 2026-09-08 that billed $1.9984 and returned nothing --
    `error='truncated: the answer hit the 65536 output-token ceiling after 2610
    tokens'`. Replayed through a route that answered `error: null`, that $2.00
    failure is indistinguishable from a morning nobody worked, which is the
    exact thing the field's docstring exists to prevent.

    `unpriced` is the same fact on the billing side: a model name the price
    table never knew about records $0.0000 with the flag set, and a wire that
    hardcoded `false` reports an honestly cheap day while the tenant spends.
    """
    container.asker = FakeAsker(
        Answer(
            data={"workflows": []},
            error="truncated: the answer hit the 65536 output-token ceiling",
            unpriced=True,
        )
    )

    body = (await client.post("/v1/mine")).json()

    assert body["error"] == "truncated: the answer hit the 65536 output-token ceiling"
    assert body["unpriced"] is True
    # And the two zeroes beside them, which are what the failure looks like
    # from the outside and why `error` has to be the thing that tells them
    # apart from a quiet day.
    assert (body["proposed"], body["kept"]) == (0, 0)


async def test_evidence_the_pass_could_not_read_is_counted_and_never_inferred(
    container: _FakeContainer, client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """`left_out` and `lost_pool` are two different kinds of unread evidence
    and neither is derivable from `window_size`.

    Ninety-five gestures fat enough that the window budget stops at
    eighty-five: the ten that did not fit are offered again next pass. One
    pooled id whose gesture row is gone is a different thing entirely -- no
    pass can ever read it, and it is named rather than quietly missing from a
    count that came out smaller than expected.

    Both numbers are DERIVED -- 85 and 10 fall out of `K_WINDOW_TOKENS` minus
    the prompt overhead, not out of a fixture -- so a wire that answered zero,
    or that answered `window_size` for either of them, fails here.
    """
    fat = _fat_day(95)
    await uow.gestures.add_gestures(tuple(fat))
    await uow.pool.add_unclaimed(TENANT, window_ids=("ges_vanished",), claimed=frozenset())
    container.asker = FakeAsker(_answer())

    body = (await client.post("/v1/mine")).json()

    assert body["window_size"] == 85
    assert body["left_out"] == 10
    assert body["lost_pool"] == ["ges_vanished"]


# --- whose day, and whose clock ---------------------------------------------


async def test_the_tenant_mined_is_the_one_on_the_credential(
    container: _FakeContainer, uow: FakeUnitOfWork, day: list[str]
) -> None:
    """Two tenants, because a route that hardcoded `acme` -- or read the tenant
    off anything but `ctx` -- passes every other assertion in this file. The
    rival's day is empty, so it reads an empty window and keeps nothing."""
    container.asker = FakeAsker(_answer(_proposal(day[:2])))
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_for(tenant='rival')}"},
    ) as rival:
        body = (await rival.post("/v1/mine")).json()

    assert (body["window_size"], body["kept"]) == (0, 0)
    assert await uow.workflows.passes(TENANT) == ()
    assert [one.tenant for one in await uow.workflows.passes(TenantId("rival"))] == ["rival"]


async def test_the_pass_is_stamped_with_the_containers_clock(
    container: _FakeContainer, client: httpx.AsyncClient, uow: FakeUnitOfWork, day: list[str]
) -> None:
    """The route reads no clock. Which day a pass is billed to comes off the
    container's, and every plant here is six months from the wall clock, so a
    route that read one of its own stamps today."""
    container.asker = FakeAsker(_answer(_proposal(day[:2])))

    await client.post("/v1/mine")

    (row,) = await uow.workflows.passes(TENANT)
    assert when(row.started_at) == NOW


# --- who may ask ------------------------------------------------------------


async def test_a_browser_may_not_spend_the_tenants_model_budget(
    container: _FakeContainer, client: httpx.AsyncClient, uow: FakeUnitOfWork, day: list[str]
) -> None:
    """Tenant-only, as in the rig. This is the most expensive call the system
    makes, and naming itself with its own real secret is the only way a browser
    reaches `tenant_only` at all -- a wrong secret is refused earlier as a 404.
    """
    container.asker = FakeAsker(_answer(_proposal(day[:2])))
    await uow.devices.add(f.device(id=LAPTOP, secret=HERS))

    answered = await client.post(
        "/v1/mine",
        params={"device_id": LAPTOP.value},
        headers={"X-Device-Secret": HERS},
    )

    assert answered.status_code == 403
    assert answered.json()["detail"] == "that is the tenant's to do, not a browser's"
    # And the same request without the browser is answered, so the 403 is the
    # refusal and not this route being absent or unroutable.
    assert (await client.post("/v1/mine")).status_code == 200


async def test_no_credential_is_refused_before_anything_is_read(
    client: httpx.AsyncClient, day: list[str]
) -> None:
    answered = await client.post("/v1/mine", headers={"Authorization": ""})

    assert answered.status_code == 401
