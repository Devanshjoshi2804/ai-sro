"""`counsel` and `record_offer` -- the callers that make plan 1's rules and
plan 2's queries true.

Ported from `new_agent_arch/tests/test_offers.py`. The rules themselves are
covered in `tests/unit/domain/rig/test_offers.py` against hand-built rows;
what is here is everything those two halves each left for the other, and it
is exactly the set of promises neither can keep alone:

* the window is `K_WINDOW` rows and the resting window is `K_ENOUGH` rows,
* an arrival nudge is neither kind of evidence and does not take up room in
  either window,
* a tie on `at` is broken by arrival,
* an offer gets an id of its own, a fate the protocol has, and a clock no
  later than the rig's.

Four of these carry the names the rig gave them, because plan 1 and plan 2
both deferred them by name.

Two of the rig's own plants are deliberately not reproduced as written: they
are satisfied by the bug they were meant to catch, and the comments below say
which and why.
"""

from datetime import UTC, datetime, timedelta

import pytest

from sro.application.skill.counsel import counsel
from sro.application.skill.record_offer import record_offer
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.skill.offers import (
    K_ENOUGH,
    K_OFFER_AFTER,
    K_QUIET_HOURS,
    K_WINDOW,
    Counsel,
    Offer,
)
from tests.unit.fakes import FakeUnitOfWork

TENANT = TenantId("acme")
OTHER = TenantId("other-corp")
DEVICE = DeviceId("dev_1")
SECOND = DeviceId("dev_2")
WORKFLOW = "wfl_1"

DAY = 11
"""February 2025, and deliberately not today or any day this will plausibly
run on.

Every rule under test here turns on a clock -- the window's order, the day a
refusal rests a job for, the cap `record_offer` holds a browser to -- and a
fixture dated on the day it was written lets a use case that ignores its
`now` and reads `datetime.now(UTC)` agree with it by the calendar. Task 5 of
this plan shipped exactly that: 8 of 8 green on the day, 4 of 8 red the next
morning."""


def _when(hour: int, *, day: int = DAY) -> datetime:
    return datetime(2025, 2, day, hour, tzinfo=UTC)


def _at(hour: int, *, day: int = DAY) -> str:
    return _when(hour, day=day).isoformat()


LATER = _when(23, day=28)
"""The rig's clock while the fixtures are being planted: after every `at`
below, so `clamped` keeps what the browser said and only the tests that are
about clamping see it bite."""


async def _offer(
    uow: FakeUnitOfWork,
    fate: str,
    *,
    k: int = 2,
    hour: int = 10,
    device: DeviceId = DEVICE,
    tenant: TenantId = TENANT,
    workflow: str = WORKFLOW,
) -> Offer:
    return await record_offer(
        uow,
        tenant_id=tenant,
        workflow_id=workflow,
        device_id=device,
        k=k,
        fate=fate,
        run_id=None,
        at=_at(hour),
        now=LATER,
    )


async def _counsel(
    uow: FakeUnitOfWork,
    *,
    device: DeviceId | None = DEVICE,
    now: datetime | None = None,
    tenant: TenantId = TENANT,
    workflow: str = WORKFLOW,
) -> Counsel:
    return await counsel(
        uow,
        tenant_id=tenant,
        workflow_id=workflow,
        device_id=device,
        now=now or _when(23),
    )


async def _stored(uow: FakeUnitOfWork) -> tuple[Offer, ...]:
    """Every offer this tenant's browsers were shown, read back through the
    audit query rather than off the fake's list."""
    return await uow.offers.since(TENANT, since=_at(0, day=1))


# --------------------------------------------------------------------------
# record_offer


async def test_an_offer_is_recorded_under_an_id_of_its_own() -> None:
    uow = FakeUnitOfWork()

    offer = await record_offer(
        uow,
        tenant_id=TENANT,
        workflow_id=WORKFLOW,
        device_id=DEVICE,
        k=3,
        fate="accepted",
        run_id="run_1",
        at=_at(10),
        now=LATER,
    )

    # Sixteen bytes of randomness, hex: the shape every other id in the
    # backend has, and enough of it that two offers made in the same second
    # cannot collide.
    assert offer.id.startswith("off_") and len(offer.id) == 36
    assert int(offer.id[4:], 16) >= 0
    assert offer == Offer(
        id=offer.id,
        tenant="acme",
        workflow_id=WORKFLOW,
        device_id="dev_1",
        k=3,
        fate="accepted",
        at=_at(10),
        run_id="run_1",
    )
    assert await _stored(uow) == (offer,)
    assert uow.commits == 1, "an offer nobody committed is an offer nobody made"

    # An id of its OWN: a second offer of the same job in the same second is a
    # second row, not an overwrite of the first.
    twin = await _offer(uow, "accepted", k=3)
    assert twin.id != offer.id
    assert {one.id for one in await _stored(uow)} == {offer.id, twin.id}


async def test_a_fate_the_protocol_does_not_have_is_refused_and_never_stored() -> None:
    """The last belt behind the route's own check. The `fate` column has no
    CHECK constraint, so if this does not refuse the word, nothing does -- and
    the refusal names the word, because a caller told only "bad fate" has to
    guess."""
    uow = FakeUnitOfWork()

    with pytest.raises(ValueError, match="ignored"):
        await _offer(uow, "ignored")

    assert await _stored(uow) == (), "refused before the row exists, not after"
    assert uow.commits == 0


async def test_a_browser_a_year_fast_does_not_own_the_window() -> None:
    """`counsel` rests a job for a day after the last refusal, measured from
    the clock on the row. Left as the browser wrote it, a machine set to 2099
    would rest the job it refused until 2099 -- on every browser's behalf, for
    as long as the row sits in the window."""
    uow = FakeUnitOfWork()
    now = _when(10)

    for _ in range(K_ENOUGH):
        await record_offer(
            uow,
            tenant_id=TENANT,
            workflow_id=WORKFLOW,
            device_id=DEVICE,
            k=2,
            fate="dismissed",
            run_id=None,
            at="2099-01-01T00:00:00Z",
            now=now,
        )

    assert [one.at for one in await _stored(uow)] == [now.isoformat()] * K_ENOUGH
    resting = await _counsel(uow, now=now)
    assert resting.quiet_until == (now + timedelta(hours=K_QUIET_HOURS)).isoformat(), (
        "a day from the rig's own now, not from the browser's"
    )


async def test_a_browser_behind_the_rig_keeps_its_own_reading() -> None:
    """The clamp is a ceiling, not a replacement: an offer answered an hour
    ago was answered an hour ago, and the rest it earns is measured from
    then."""
    uow = FakeUnitOfWork()

    for hour in (10, 11, 12):
        await _offer(uow, "dismissed", hour=hour)

    assert [one.at for one in await _stored(uow)] == [_at(12), _at(11), _at(10)]
    resting = await _counsel(uow, now=_when(13))
    assert resting.quiet_until == (_when(12) + timedelta(hours=K_QUIET_HOURS)).isoformat()


# --------------------------------------------------------------------------
# counsel


async def test_a_job_nobody_has_answered_is_offered_at_the_default() -> None:
    uow = FakeUnitOfWork()
    advice = await _counsel(uow)
    assert advice == Counsel(K_OFFER_AFTER, None)
    assert uow.commits == 0, "counsel reads; the caller owns the session"
    assert advice.as_json() == {
        "offer_after": K_OFFER_AFTER,
        "later": False,
        "quiet_until": None,
    }


async def test_the_resting_rule_reads_exactly_the_newest_three() -> None:
    """`counsel_over` rests on `len(newest) == K_ENOUGH` -- exactly three, not
    at least three -- so the equality only says "the browser's newest three"
    if this caller cut the list to three. A fourth refusal behind them must
    change nothing: uncut, four refused rows fail the equality and a job three
    refusals deep would quietly stop resting the moment a fourth arrived."""
    uow = FakeUnitOfWork()
    await _offer(uow, "dismissed", hour=10)
    await _offer(uow, "did_it", hour=11)
    assert (await _counsel(uow, now=_when(12))).quiet_until is None, (
        "a single dismissal is a mood and two running is not yet an answer"
    )

    await _offer(uow, "dismissed", hour=12)
    await _offer(uow, "dismissed", hour=13)
    resting = await _counsel(uow, now=_when(14))
    assert resting.quiet_until == (_when(13) + timedelta(hours=K_QUIET_HOURS)).isoformat(), (
        "a day from the last refusal"
    )
    assert resting.as_json()["later"] is False
    # A rest, not a retirement, and a whole day of one: both edges to the
    # hour, because asserting only the far one leaves a rest of any shorter
    # length reading as correct. The far edge is the day exactly, which also
    # pins `until > now` rather than `>=`: the hour it comes back round is the
    # hour the job is offered again.
    assert (await _counsel(uow, now=_when(12, day=DAY + 1))).quiet_until is not None, "23h, not yet"
    assert (await _counsel(uow, now=_when(13, day=DAY + 1))).quiet_until is None, "the day passed"

    # A rest is per browser, per job, per tenant -- and a caller naming no
    # browser has nobody to rest.
    assert (await _counsel(uow, device=SECOND, now=_when(14))).quiet_until is None
    assert (await _counsel(uow, device=None, now=_when(14))).quiet_until is None
    assert (await _counsel(uow, workflow="wfl_2", now=_when(14))).quiet_until is None
    assert (await _counsel(uow, tenant=OTHER, now=_when(14))).quiet_until is None


async def test_an_offer_the_operator_did_not_refuse_breaks_the_run() -> None:
    uow = FakeUnitOfWork()
    for hour, fate in ((10, "dismissed"), (11, "dismissed"), (12, "expired"), (13, "dismissed")):
        await _offer(uow, fate, hour=hour)
    assert (await _counsel(uow, now=_when(14))).quiet_until is None

    for hour, fate in ((14, "accepted"), (15, "dismissed"), (16, "dismissed")):
        await _offer(uow, fate, hour=hour)
    assert (await _counsel(uow, now=_when(17))).quiet_until is None


async def test_offers_that_keep_diverging_move_the_job_past_where_they_diverged() -> None:
    uow = FakeUnitOfWork()
    for hour in range(10, 10 + K_ENOUGH - 1):
        await _offer(uow, "diverged", k=2, hour=hour)
    assert (await _counsel(uow)).offer_after == K_OFFER_AFTER, "two offers are not enough to read"

    # Every browser's offers count towards the threshold: recognition is a
    # property of the job, not of who was asked.
    await _offer(uow, "diverged", k=3, hour=13, device=SECOND)
    later = await _counsel(uow)
    assert later.offer_after == 4, "one past the deepest k that diverged"
    assert later.as_json()["later"] is True

    # Half or more: three diverged of six still moves it ...
    for hour in range(14, 17):
        await _offer(uow, "accepted", k=4, hour=hour)
    assert (await _counsel(uow)).offer_after == 4
    # ... and three of seven does not.
    await _offer(uow, "accepted", k=4, hour=17)
    assert (await _counsel(uow)).offer_after == K_OFFER_AFTER


async def test_an_arrival_nudge_is_not_evidence_either_way() -> None:
    """Arrival nudges are recorded at k = 0 -- "you have been here before",
    nothing typed. They are not a recognition that diverged and not an offer
    anyone turned down, and they must not take up room in either window: a
    window of ten that a run of nudges could fill is not a window of ten
    offers.

    The rig planted six nudges and asserted the default came back. That plant
    cannot fail on the threshold at all -- `max(k) + 1` over k = 0 rows is 1,
    which never beats `K_OFFER_AFTER` -- so the assertion it made was already
    true. This plants a flood of ten nudges over three real diverged offers,
    where counting nudges is the difference between a moved threshold and an
    unmoved one, and where the newest nudges are refusals so counting them is
    the difference between a rested job and an offered one.
    """
    uow = FakeUnitOfWork()
    for hour in (8, 9, 10):
        await _offer(uow, "diverged", k=3, hour=hour)
    for hour in range(11, 18):
        await _offer(uow, "expired", k=0, hour=hour)
    for hour in (18, 19, 20):
        await _offer(uow, "dismissed", k=0, hour=hour)

    advice = await _counsel(uow, now=_when(21))
    assert advice.offer_after == 4, (
        "ten nudges do not push three real diverged offers out of the window"
    )
    assert advice.quiet_until is None, "three nudges nobody clicked away are not three refusals"

    # Still offers that were made, though: the panel's tally counts them, and
    # that is the difference between the window and the tally.
    assert dict(await uow.offers.fates(TENANT, WORKFLOW)) == {
        "diverged": 3,
        "expired": 7,
        "dismissed": 3,
    }


async def test_only_the_newest_ten_offers_are_read() -> None:
    """`K_WINDOW` is the caller's, and the rule is meaningless over the wrong
    one: "half or more diverged" of ten and of fourteen are different
    questions about the same day.

    The rig's plant -- three diverged in the morning, ten accepted after them
    -- is the second assertion here, and on its own it pins nothing: three
    diverged of thirteen is under half, so an uncut window answers it exactly
    as a window of ten does. The first plant is built so that ten is the only
    limit that answers 4: five diverged of the newest ten is half, five of
    eleven or more is not, and any limit under ten cuts into the run of
    accepted offers above them and finds no divergence at all.
    """
    uow = FakeUnitOfWork()
    for hour in range(5, 9):
        await _offer(uow, "accepted", k=3, hour=hour)
    for hour in range(9, 14):
        await _offer(uow, "diverged", k=3, hour=hour)
    for hour in range(14, 19):
        await _offer(uow, "accepted", k=3, hour=hour)

    assert (await _counsel(uow, now=_when(20))).offer_after == 4, (
        "five diverged of the newest ten is half; of all fourteen it is not"
    )

    theirs = FakeUnitOfWork()
    for hour in range(3):
        await _offer(theirs, "diverged", k=2, hour=hour)
    for hour in range(3, 3 + K_WINDOW):
        await _offer(theirs, "accepted", k=2, hour=hour)
    assert (await _counsel(theirs, now=_when(23))).offer_after == K_OFFER_AFTER, (
        "three diverged offers from the morning are outside the window of ten"
    )


async def test_offers_in_the_same_second_are_read_in_the_order_they_arrived() -> None:
    """Several offers of one job routinely carry the same second, because the
    extension sends whole-second instants. Which three of them are "the newest
    three" is then decided by arrival alone, and that decides whether the
    browser is rested.

    Both plants below are laid in the order that DISAGREES with the answer
    asserted, because a reader that ignored arrival entirely and returned the
    rows in the order they went in would be flattered by the other order. Six
    rows, not three: with three the set is the same either way and only the
    order inside it changes, which the resting rule cannot see.
    """
    uow = FakeUnitOfWork()
    for _ in range(5):
        await _offer(uow, "dismissed", hour=10)
    await _offer(uow, "accepted", hour=10)
    assert (await _counsel(uow, now=_when(11))).quiet_until is None, (
        "the last to arrive was accepted, so the newest three are not three refusals"
    )

    theirs = FakeUnitOfWork()
    await _offer(theirs, "accepted", hour=10)
    for _ in range(5):
        await _offer(theirs, "dismissed", hour=10)
    assert (await _counsel(theirs, now=_when(11))).quiet_until is not None, (
        "the accepted offer arrived first, so it sorts out of the newest three"
    )
