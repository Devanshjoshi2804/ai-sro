"""The day's cap: what a tenant's model calls may cost before the rig stops.

Ported from the rig's ``over_cap`` in ``new_agent_arch/src/rig/api.py``. The
spend itself is not handed to the rule as a number -- it is put into the same
repositories the rest of the system writes to and summed back out by
``FakeSpendRepository``, so a day that reads as $5.00 here is a day something
actually billed $5.00.
"""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from sro.application.intent.spend import over_cap, spent_today
from sro.config import Settings
from sro.domain.chat.reading import ChatReading
from sro.domain.shared.identifiers import TenantId
from sro.domain.shared.prices import DaySpend
from tests.unit.fakes import FakeUnitOfWork

TENANT = TenantId("acme")
NOW = datetime(2025, 3, 4, 12, 0, tzinfo=UTC)
"""Deliberately not today, and not any day this will plausibly run on.

Dated on the day it was written, every test here passed against a `spent_today`
that ignored its `now` entirely and asked the repository `datetime.now(tz=UTC)`
-- the two agreed by the calendar. The one property the parameter exists for
was pinned for a day and unpinned from the next morning.
"""


async def _billed(*chats: ChatReading) -> FakeUnitOfWork:
    """A day with these calls on it. The chat door is one of the four billable
    tables and the cheapest to write, and the rule reads the sum, not the
    table."""
    uow = FakeUnitOfWork()
    for chat in chats:
        await uow.chats.record(chat)
    return uow


def _chat(chat_id: str, *, cost_usd: float = 0.0, unpriced: bool = False) -> ChatReading:
    return ChatReading(
        id=chat_id,
        tenant=TENANT.value,
        at=NOW.replace(hour=10).isoformat(),
        cost_usd=cost_usd,
        unpriced=unpriced,
    )


async def test_a_day_under_the_cap_goes_on_asking() -> None:
    uow = await _billed(_chat("cha_1", cost_usd=4.99))

    assert await over_cap(uow, TENANT, now=NOW, cap_usd=5.0) is None


async def test_the_day_that_spent_exactly_the_cap_has_spent_it() -> None:
    """The boundary, which no real day lands on by accident and every wrong
    implementation lands on the far side of. A cap is the amount that MAY be
    spent: `>=` and `>` differ on exactly this input, and under `>` a cap of
    zero -- the switch that turns the asking off -- would not stop anything.
    """
    uow = await _billed(_chat("cha_1", cost_usd=5.0))

    reason = await over_cap(uow, TENANT, now=NOW, cap_usd=5.0)

    assert reason is not None
    assert "$5.0000 of $5.00" in reason


async def test_a_day_over_the_cap_says_how_much_of_what() -> None:
    """The sentence is what a 429 carries, so it names both numbers: a reader
    has to be able to tell a cap that wants raising from a cap that is
    working."""
    uow = await _billed(_chat("cha_1", cost_usd=3.0), _chat("cha_2", cost_usd=4.0))

    reason = await over_cap(uow, TENANT, now=NOW, cap_usd=5.0)

    assert reason is not None
    assert "$7.0000 of $5.00" in reason
    assert "0 unpriced call(s)" in reason


class _RefusesToBeAsked:
    """A spend repository that fails if anything asks it what today cost."""

    async def today(self, tenant_id: TenantId, *, now: datetime) -> DaySpend:
        raise AssertionError("a cap that is not a cap must not pay for the query")


async def test_a_negative_cap_is_no_cap_at_all() -> None:
    """What a deliberate one-off measurement sets. Nothing stops it -- not the
    dollars, and not an unpriced call either, because the point of the run is
    to find out what a thing costs.

    And it is answered before the repository is touched, which is a claim the
    module docstring makes and only this repository holds it to: with the
    guard moved below the `await` every other test here still passed.
    """
    uow = await _billed(_chat("cha_1", cost_usd=500.0, unpriced=True))
    uow.spend = _RefusesToBeAsked()

    assert await over_cap(uow, TENANT, now=NOW, cap_usd=-1.0) is None


async def test_a_cap_of_zero_stops_the_asking_before_anything_is_spent() -> None:
    """Zero is the off switch, and it has to hold on a day that has not billed
    a cent -- which is the only day it will ever be read on."""
    uow = await _billed()

    reason = await over_cap(uow, TENANT, now=NOW, cap_usd=0.0)

    assert reason is not None
    assert "$0.0000 of $0.00" in reason


async def test_a_day_whose_cost_cannot_be_trusted_is_not_a_cheap_day() -> None:
    """A model name the price table never knew about records $0.0000 with
    ``unpriced`` set. Summed on cost_usd alone the day reads free while it
    spends -- the run that proved this architecture billed $1.12 and every row
    said free -- so the blind count stops the day, and the reason says so
    rather than reporting a total that is not one.
    """
    uow = await _billed(_chat("cha_1", cost_usd=0.0, unpriced=True))

    reason = await over_cap(uow, TENANT, now=NOW, cap_usd=5.0)

    assert reason is not None
    assert "1 unpriced call(s)" in reason


async def test_the_day_is_this_tenants_own() -> None:
    """The cap is per tenant, and a fake that summed the store would read one
    tenant's spending onto another's bill."""
    uow = await _billed(_chat("cha_1", cost_usd=9.0))

    assert await over_cap(uow, TenantId("other-corp"), now=NOW, cap_usd=5.0) is None


async def test_spent_today_reports_the_pair_the_rule_judges() -> None:
    uow = await _billed(_chat("cha_1", cost_usd=1.25), _chat("cha_2", unpriced=True))

    day = await spent_today(uow, TENANT, now=NOW)

    assert (day.cost_usd, day.blind) == (1.25, 1)


async def test_the_day_is_the_utc_day_whatever_zone_the_clock_carries() -> None:
    """Midnight is UTC's, and `now` is only asked what instant it is.

    A clock at 02:00+05:30 is still on the previous UTC day, so the day being
    summed starts at that day's UTC midnight -- twenty and a half hours before
    the caller's own midnight. Read in the machine's local zone instead the
    window slides by its offset, which on a westward host bills yesterday
    evening to today and hands a fresh day a spent cap. Plan 2's repository is
    pinned on this by two integration tests; the fake every unit test here runs
    against was not, and this is the first use case to depend on it.
    """
    clock = datetime(2025, 3, 4, 2, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    assert clock.astimezone(UTC).date() != clock.date(), "the two days must differ"

    uow = FakeUnitOfWork()
    # Inside the UTC day of `clock`, and outside the calendar day it reads as.
    await uow.chats.record(
        ChatReading(id="cha_1", tenant=TENANT.value, at="2025-03-03T10:00:00+00:00", cost_usd=2.0)
    )
    # The UTC day before: outside by nine hours, whatever the caller's offset.
    await uow.chats.record(
        ChatReading(id="cha_2", tenant=TENANT.value, at="2025-03-02T15:00:00+00:00", cost_usd=4.0)
    )

    assert (await spent_today(uow, TENANT, now=clock)).cost_usd == 2.0


# --------------------------------------------------------------------------
# the setting the cap is read from


class TestTheSettingEveryPaidLoopReadsTheCapFrom:
    """`Settings.daily_usd_cap` carries the rig's docstring, and every claim
    in it is a claim about `cap_usd` above -- which the tests above prove
    about the *argument*.

    Between the two sits pydantic, and it can make the docstring false without
    touching either: a `ge=0` on the field leaves "a negative value means no
    cap" unwritable, and a default of zero turns the asking off everywhere,
    with every test above still green. `read_new_gestures`, `mine` and the
    runner all take their `cap_usd` from here, so this is where the two halves
    are tied together.
    """

    async def test_the_default_is_no_cap_and_a_ceiling_is_a_deployment_s_to_set(self) -> None:
        """No ceiling by default, by the owner's instruction (2026-09-16).

        It was five dollars, and the day a tenant reached it every reading,
        every mining pass and every run stopped -- a warehouse whose jobs stop
        at four in the afternoon because a number in a config file ran out. Not
        zero, which refuses every model call there is; negative, which `over_cap`
        already reads as "no cap".

        The machinery is not deleted and the test below still pins that a set
        cap stops a day: what shipped as a ceiling nobody chose is now a
        ceiling a deployment chooses.
        """
        cap = Settings(_env_file=None).daily_usd_cap
        spent = await _billed(_chat("cha_1", cost_usd=500.0, unpriced=True))

        assert cap == -1.0
        assert await over_cap(spent, TENANT, now=NOW, cap_usd=cap) is None
        # And a deployment that sets one still gets one.
        assert await over_cap(spent, TENANT, now=NOW, cap_usd=5.0) is not None

    async def test_a_negative_value_survives_the_setting_and_means_no_cap(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """What a deliberate one-off measurement sets, written where an
        operator sets it: the environment, under the SRO_ prefix."""
        monkeypatch.setenv("SRO_DAILY_USD_CAP", "-1")
        cap = Settings(_env_file=None).daily_usd_cap
        uow = await _billed(_chat("cha_1", cost_usd=500.0, unpriced=True))

        assert cap == -1.0
        assert await over_cap(uow, TENANT, now=NOW, cap_usd=cap) is None

    async def test_zero_survives_the_setting_and_disables_the_asking(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SRO_DAILY_USD_CAP", "0")
        cap = Settings(_env_file=None).daily_usd_cap

        assert cap == 0.0
        assert await over_cap(await _billed(), TENANT, now=NOW, cap_usd=cap) is not None
