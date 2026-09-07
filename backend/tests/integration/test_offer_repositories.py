"""What the extension offered, what a sentence cost, and a browser withdrawn.

Against real Postgres, because these are queries rather than logic. The rules
are the rig's: ``counsel``'s two selects in ``new_agent_arch/src/rig/offers.py``
(the ``k > 0`` filter, ``ORDER BY at DESC, rowid DESC LIMIT ?``, and the
per-device variant), the ``chats`` insert and select in ``rig/api.py``, and
``rig/devices.py``'s ``revoke``. The offer names come from
``new_agent_arch/tests/test_offers.py``; what is proved here is the repository
half of them, with ``counsel_over`` -- already ported and already unit-tested --
reading the window this hands it.

The rig's ``rowid`` tiebreak is an identity column here, and it carries a real
rule: two offers written in the same second come back in the order they
arrived, which is what decides whether a browser's last three were all
refusals.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.domain.chat.reading import ChatReading
from sro.domain.observation.device import AgentDevice
from sro.domain.shared.errors import NotFound
from sro.domain.shared.identifiers import DeviceId, PrincipalId, TenantId
from sro.domain.skill.offers import (
    K_ENOUGH,
    K_OFFER_AFTER,
    K_WINDOW,
    Offer,
    counsel_over,
    new_offer_id,
)
from sro.infrastructure.db.models import ChatRow, OfferRow
from sro.infrastructure.db.repositories import SqlUnitOfWork

TENANT = TenantId("acme")
OTHER_TENANT = TenantId("other-corp")
DEVICE = DeviceId("dev_1")
OTHER_DEVICE = DeviceId("dev_2")


def _at(hour: int, day: int = 6) -> str:
    return datetime(2026, 9, day, hour, tzinfo=UTC).isoformat()


def _offer(**overrides: Any) -> Offer:
    fields: dict[str, Any] = {
        "id": new_offer_id(),
        "tenant": TENANT.value,
        "workflow_id": "wfl_1",
        "device_id": DEVICE.value,
        "k": 2,
        "fate": "dismissed",
        "at": _at(10),
    }
    fields.update(overrides)
    return Offer(**fields)


async def _record(
    session_factory: async_sessionmaker[AsyncSession], *offers: Offer
) -> tuple[Offer, ...]:
    """One at a time, in the order given: arrival order is under test."""
    for offer in offers:
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.offers.record(offer)
            await uow.commit()
    return offers


class TestOffers:
    async def test_an_offer_is_recorded_under_an_id_of_its_own(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Sixteen bytes of randomness, hex -- the shape every other id in the
        backend has, and enough of it that two offers made in the same second
        cannot collide. One offer is one row: nothing here upserts."""
        offer = _offer(k=3, fate="accepted", run_id="run_1")

        assert offer.id.startswith("off_") and len(offer.id) == 36
        assert int(offer.id[4:], 16) >= 0

        await _record(session_factory, offer)

        async with session_factory() as session:
            rows = (
                await session.execute(select(OfferRow.id, OfferRow.fate, OfferRow.run_id))
            ).all()

        assert [tuple(row) for row in rows] == [(offer.id, "accepted", "run_1")]

    async def test_an_arrival_nudge_is_not_evidence_either_way(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """``k = 0`` is "you have been here before", with nothing typed. It is
        not a recognition that diverged and not an offer anyone turned down, so
        the ``k > 0`` filter belongs in the query rather than in the caller."""
        await _record(
            session_factory,
            *(_offer(fate="dismissed", k=0, at=_at(hour)) for hour in (10, 11, 12)),
            *(_offer(fate="diverged", k=0, at=_at(hour)) for hour in (13, 14, 15)),
        )

        async with SqlUnitOfWork(session_factory) as uow:
            window = await uow.offers.newest(TENANT, "wfl_1", limit=K_WINDOW)
            mine = await uow.offers.newest_for_device(TENANT, "wfl_1", DEVICE, limit=K_ENOUGH)

        advice = counsel_over(window, mine, datetime(2026, 9, 6, 16, tzinfo=UTC))
        assert (window, mine) == ((), ())
        assert advice.quiet_until is None and advice.offer_after == K_OFFER_AFTER

    async def test_only_the_newest_ten_offers_are_read(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Older offers were made against a threshold that has since moved, or
        against a page that has. Three diverged offers from the small hours are
        outside a window of ten and must not move the job."""
        await _record(
            session_factory,
            *(_offer(fate="diverged", at=_at(hour)) for hour in range(3)),
            *(_offer(fate="accepted", at=_at(hour)) for hour in range(3, 13)),
        )

        async with SqlUnitOfWork(session_factory) as uow:
            window = await uow.offers.newest(TENANT, "wfl_1", limit=K_WINDOW)

        assert len(window) == K_WINDOW
        assert {row.fate for row in window} == {"accepted"}
        assert [row.at for row in window] == [_at(hour) for hour in range(12, 2, -1)]
        assert counsel_over(window, (), datetime(2026, 9, 6, 14, tzinfo=UTC)).offer_after == (
            K_OFFER_AFTER
        )

    async def test_offers_in_the_same_second_are_read_in_the_order_they_arrived(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The rig broke an ``at`` tie on ``rowid``; the identity column is what
        replaces it. Without the tiebreak Postgres is free to hand back these
        three in any order, and a browser whose newest offer was an acceptance
        would be told to rest on the strength of two older refusals."""
        await _record(
            session_factory,
            _offer(fate="dismissed"),
            _offer(fate="dismissed"),
            _offer(fate="accepted"),
        )
        now = datetime(2026, 9, 6, 11, tzinfo=UTC)

        async with SqlUnitOfWork(session_factory) as uow:
            mine = await uow.offers.newest_for_device(TENANT, "wfl_1", DEVICE, limit=K_ENOUGH)

        assert [row.fate for row in mine] == ["accepted", "dismissed", "dismissed"]
        assert counsel_over((), mine, now).quiet_until is None, "the newest of the three accepted"

        await _record(session_factory, *(_offer(fate="dismissed") for _ in range(3)))

        async with SqlUnitOfWork(session_factory) as uow:
            refused = await uow.offers.newest_for_device(TENANT, "wfl_1", DEVICE, limit=K_ENOUGH)

        assert [row.fate for row in refused] == ["dismissed"] * 3
        assert counsel_over((), refused, now).quiet_until is not None

    async def test_a_rest_is_read_off_the_browser_that_asked_and_no_other(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """One operator's no is not the next operator's. The tenant-wide window
        counts every browser's offers -- recognition is a property of the job --
        but the run of refusals that rests a job is one browser's."""
        await _record(
            session_factory,
            *(_offer(fate="dismissed", at=_at(hour)) for hour in (10, 11, 12)),
            *(
                _offer(fate="accepted", device_id=OTHER_DEVICE.value, at=_at(hour))
                for hour in (13,)
            ),
        )

        async with SqlUnitOfWork(session_factory) as uow:
            theirs = await uow.offers.newest_for_device(
                TENANT, "wfl_1", OTHER_DEVICE, limit=K_ENOUGH
            )
            everyone = await uow.offers.newest(TENANT, "wfl_1", limit=K_WINDOW)

        assert [row.fate for row in theirs] == ["accepted"]
        assert len(everyone) == 4

    async def test_another_tenants_offers_are_not_this_ones_evidence(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Planted so that a query missing the tenant filter answers wrongly
        rather than merely differently: the other tenant's three divergences are
        newer, and would move this job's threshold and count towards its fates."""
        await _record(
            session_factory,
            _offer(fate="accepted", at=_at(10)),
            *(
                _offer(tenant=OTHER_TENANT.value, fate="diverged", k=7, at=_at(hour))
                for hour in (11, 12, 13)
            ),
            _offer(workflow_id="wfl_2", fate="diverged", k=9, at=_at(14)),
        )

        async with SqlUnitOfWork(session_factory) as uow:
            window = await uow.offers.newest(TENANT, "wfl_1", limit=K_WINDOW)
            mine = await uow.offers.newest_for_device(TENANT, "wfl_1", DEVICE, limit=K_ENOUGH)
            counted = await uow.offers.fates(TENANT, "wfl_1")

        assert [row.fate for row in window] == ["accepted"]
        assert [row.fate for row in mine] == ["accepted"]
        assert counted == {"accepted": 1}
        assert counsel_over(window, mine, datetime(2026, 9, 6, 15, tzinfo=UTC)).offer_after == (
            K_OFFER_AFTER
        )

    async def test_every_fate_is_counted_by_name_including_the_nudges(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The panel's tally, not the counsel's window: no ``k > 0`` and no
        limit here, because an arrival nudge is still an offer that was made."""
        await _record(
            session_factory,
            _offer(fate="diverged", at=_at(10)),
            _offer(fate="diverged", at=_at(11)),
            _offer(fate="accepted", at=_at(12)),
            _offer(fate="dismissed", k=0, at=_at(13)),
        )

        async with SqlUnitOfWork(session_factory) as uow:
            counted = await uow.offers.fates(TENANT, "wfl_1")

        assert counted == {"diverged": 2, "accepted": 1, "dismissed": 1}


class TestChats:
    async def test_a_chat_reading_records_what_it_cost_and_never_the_sentence(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The row exists for the cap and the spend line, and neither needs the
        operator's words about their warehouse. The column list is the assertion
        because it is the thing a later change would quietly break."""
        reading = ChatReading(
            id="cht_1",
            tenant=TENANT.value,
            at=_at(10),
            workflow_id="wfl_1",
            in_tokens=900,
            out_tokens=120,
            thought_tokens=30,
            cost_usd=0.0021,
            unpriced=False,
        )
        blind = ChatReading(
            id="cht_2",
            tenant=TENANT.value,
            at=_at(11),
            unpriced=True,
            error="the model refused",
        )
        theirs = ChatReading(id="cht_3", tenant=OTHER_TENANT.value, at=_at(12), cost_usd=99.0)

        async with SqlUnitOfWork(session_factory) as uow:
            for one in (reading, blind, theirs):
                await uow.chats.record(one)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            day = await uow.chats.since(TENANT, since=_at(0))
            afternoon = await uow.chats.since(TENANT, since=_at(11))

        assert {column.name for column in ChatRow.__table__.columns} == {
            "id",
            "tenant_id",
            "workflow_id",
            "in_tokens",
            "out_tokens",
            "thought_tokens",
            "cost_usd",
            "unpriced",
            "error",
            "at",
        }
        # Newest first, this tenant's only, and nothing from before `since`.
        assert day == (blind, reading)
        assert afternoon == (blind,)

    async def test_a_reading_whose_cost_could_not_be_established_is_not_a_free_one(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A call that cost nothing and a call nobody could price are the same
        row without ``unpriced``, and the day's bill is understated silently."""
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.chats.record(
                ChatReading(id="cht_1", tenant=TENANT.value, at=_at(10), unpriced=True)
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            (back,) = await uow.chats.since(TENANT, since=_at(0))

        assert (back.unpriced, back.cost_usd, back.workflow_id) == (True, 0.0, None)


def _device(at: datetime) -> AgentDevice:
    return AgentDevice(
        id=DEVICE,
        tenant_id=TENANT,
        principal_id=PrincipalId("op_1"),
        label="laptop",
        extension_version="0.1.0",
        registered_at=at,
        last_seen_at=at,
        secret="what-this-browser-proves-it-is-itself-with",  # noqa: S106
    )


class TestRevocation:
    async def test_revoking_a_browser_stops_it_speaking_for_itself(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The secret keeps working -- nothing here rewrites it -- and the
        record carries the one fact the auth dependency will read."""
        registered = datetime(2026, 9, 6, 9, tzinfo=UTC)

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.devices.add(_device(registered))
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            live = await uow.devices.get(TENANT, DEVICE)
            taken = await uow.devices.revoke(TENANT, DEVICE, at=_at(10))
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            withdrawn = await uow.devices.get(TENANT, DEVICE)

        assert live.revoked is False and live.revoked_at is None
        assert taken is True
        assert withdrawn.revoked is True and withdrawn.revoked_at == _at(10)
        assert withdrawn.proves_itself("what-this-browser-proves-it-is-itself-with")

    async def test_revoking_twice_is_not_a_second_revocation(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Whether there was a live browser to revoke, and the first answer
        stands: a second call must not move the instant the authority ended."""
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.devices.add(_device(datetime(2026, 9, 6, 9, tzinfo=UTC)))
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            first = await uow.devices.revoke(TENANT, DEVICE, at=_at(10))
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            second = await uow.devices.revoke(TENANT, DEVICE, at=_at(11))
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            withdrawn = await uow.devices.get(TENANT, DEVICE)

        assert (first, second) == (True, False)
        assert withdrawn.revoked_at == _at(10)

    async def test_a_browser_is_not_revoked_by_another_tenant(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.devices.add(_device(datetime(2026, 9, 6, 9, tzinfo=UTC)))
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            try:
                await uow.devices.revoke(OTHER_TENANT, DEVICE, at=_at(10))
                refused = False
            except NotFound:
                refused = True

        async with SqlUnitOfWork(session_factory) as uow:
            still = await uow.devices.get(TENANT, DEVICE)

        assert refused is True
        assert still.revoked is False
