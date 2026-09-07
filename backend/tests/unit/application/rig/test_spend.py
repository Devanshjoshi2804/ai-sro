"""The day's cap: what a tenant's model calls may cost before the rig stops.

Ported from the rig's ``over_cap`` in ``new_agent_arch/src/rig/api.py``. The
spend itself is not handed to the rule as a number -- it is put into the same
repositories the rest of the system writes to and summed back out by
``FakeSpendRepository``, so a day that reads as $5.00 here is a day something
actually billed $5.00.
"""

from datetime import UTC, datetime

from sro.application.intent.spend import over_cap, spent_today
from sro.domain.chat.reading import ChatReading
from sro.domain.shared.identifiers import TenantId
from tests.unit.fakes import FakeUnitOfWork

TENANT = TenantId("acme")
NOW = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)


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


async def test_a_negative_cap_is_no_cap_at_all() -> None:
    """What a deliberate one-off measurement sets. Nothing stops it -- not the
    dollars, and not an unpriced call either, because the point of the run is
    to find out what a thing costs."""
    uow = await _billed(_chat("cha_1", cost_usd=500.0, unpriced=True))

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
