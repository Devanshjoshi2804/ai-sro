"""The day's bill, and what the audit is assembled from.

Against real Postgres, because all of it is queries. The rules are the rig's
``spent_today`` and ``SPENT_IN`` in ``new_agent_arch/src/rig/api.py`` -- four
tables that can be billed, each with its own clock column and its own idea of
what a blind row is -- and the audit route's own selects a hundred lines below
them.

Two things are proved here that a fake cannot prove. The midnight boundary is
a ``timestamptz`` comparison rather than the rig's text one, so it is checked a
second either side of it; and every tenant filter is checked against another
tenant's rows planted in the same tables, because a spend sum that reads the
whole database is a cap on somebody else's day.

``intents.created_at`` is the server's clock, taken inside ``save_intent``, so
the intent rows here are planted as rows: there is no other way to put a
reading a second before midnight.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.domain.chat.reading import ChatReading
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.observation.device import AgentDevice
from sro.domain.observation.mining import MiningPass
from sro.domain.shared.identifiers import DeviceId, PrincipalId, TenantId
from sro.domain.skill.offers import Offer, new_offer_id
from sro.infrastructure.db.models import IntentRow
from sro.infrastructure.db.repositories import SqlUnitOfWork

TENANT = TenantId("acme")
OTHER_TENANT = TenantId("other-corp")
DEVICE = DeviceId("dev_1")

NOW = datetime(2026, 9, 7, 1, 0, tzinfo=UTC)
"""Within an offset of midnight, deliberately.

``today`` reads a naive ``now`` as UTC before truncating to midnight, so a
wrong reading of it only moves the day boundary when the offset carries the
clock across a date line. At 09:30 no real zone does, and
``test_a_now_with_no_zone_is_read_as_utc`` passed against an implementation
that read the server's local time instead. At 01:00 it does not."""
MIDNIGHT = datetime(2026, 9, 7, tzinfo=UTC)
JUST_TODAY = MIDNIGHT
JUST_YESTERDAY = MIDNIGHT - timedelta(seconds=1)


def _intent_row(*, tenant: str, created_at: datetime, cost: float, **overrides: Any) -> IntentRow:
    fields: dict[str, Any] = {
        "gesture_id": f"ges_{tenant}_{created_at.isoformat()}_{cost}",
        "tenant_id": tenant,
        "cost_usd": cost,
        "unpriced": False,
        "created_at": created_at,
        "values_seen": [],
        "error": None,
    }
    fields.update(overrides)
    return IntentRow(**fields)


def _pass(*, tenant: str = TENANT.value, at: datetime, cost: float, **overrides: Any) -> MiningPass:
    fields: dict[str, Any] = {
        "id": f"pas_{tenant}_{at.isoformat()}_{cost}",
        "tenant": tenant,
        "started_at": at.isoformat(),
        "cost_usd": cost,
    }
    fields.update(overrides)
    return MiningPass(**fields)


def _run(*, tenant: str = TENANT.value, at: datetime, cost: float, **overrides: Any) -> WorkflowRun:
    fields: dict[str, Any] = {
        "id": f"run_{tenant}_{at.isoformat()}_{cost}",
        "tenant": tenant,
        "workflow_id": "wfl_1",
        "device_id": DEVICE.value,
        "values": {},
        "started_by": "operator",
        "live": False,
        "allow_focus": False,
        "started_at": at.isoformat(),
        "cost_usd": cost,
    }
    fields.update(overrides)
    return WorkflowRun(**fields)


def _chat(
    *, tenant: str = TENANT.value, at: datetime, cost: float, **overrides: Any
) -> ChatReading:
    fields: dict[str, Any] = {
        "id": f"cht_{tenant}_{at.isoformat()}_{cost}",
        "tenant": tenant,
        "at": at.isoformat(),
        "cost_usd": cost,
    }
    fields.update(overrides)
    return ChatReading(**fields)


async def _bill(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    intents: tuple[IntentRow, ...] = (),
    passes: tuple[MiningPass, ...] = (),
    runs: tuple[WorkflowRun, ...] = (),
    chats: tuple[ChatReading, ...] = (),
) -> None:
    if intents:
        # Planted as rows: `created_at` is taken by `save_intent` from the
        # server's own clock, and a reading a second before midnight cannot be
        # written any other way.
        async with session_factory() as session:
            session.add_all(intents)
            await session.commit()
    async with SqlUnitOfWork(session_factory) as uow:
        for mining_pass in passes:
            await uow.workflows.add_pass(mining_pass)
        for run in runs:
            await uow.workflow_runs.save(run)
        for chat in chats:
            await uow.chats.record(chat)
        await uow.commit()


class TestTheDaysSpend:
    async def test_the_day_sums_every_table_that_can_be_billed(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A reading, a mining pass, a run and a chat are the four things that
        cost money. The rig learnt this the expensive way: a cap that summed
        one of them was a cap on a quarter of the bill."""
        await _bill(
            session_factory,
            intents=(_intent_row(tenant=TENANT.value, created_at=NOW, cost=0.01),),
            passes=(_pass(at=NOW, cost=0.02),),
            runs=(_run(at=NOW, cost=0.04),),
            chats=(_chat(at=NOW, cost=0.08),),
        )

        async with SqlUnitOfWork(session_factory) as uow:
            day = await uow.spend.today(TENANT, now=NOW)

        assert (round(day.cost_usd, 6), day.blind) == (0.15, 0)

    async def test_a_row_from_yesterday_is_not_in_todays_day(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Midnight UTC, a second either side, in all four tables. The rig
        compared ISO text against a date string; this is a ``timestamptz``
        comparison, and the boundary is the whole rule."""
        await _bill(
            session_factory,
            intents=(
                _intent_row(tenant=TENANT.value, created_at=JUST_YESTERDAY, cost=1.0),
                _intent_row(tenant=TENANT.value, created_at=JUST_TODAY, cost=0.01),
            ),
            passes=(
                _pass(at=JUST_YESTERDAY, cost=1.0),
                _pass(at=JUST_TODAY, cost=0.02),
            ),
            runs=(
                _run(at=JUST_YESTERDAY, cost=1.0),
                _run(at=JUST_TODAY, cost=0.04),
            ),
            chats=(
                _chat(at=JUST_YESTERDAY, cost=1.0),
                _chat(at=JUST_TODAY, cost=0.08),
            ),
        )

        async with SqlUnitOfWork(session_factory) as uow:
            day = await uow.spend.today(TENANT, now=NOW)

        assert (round(day.cost_usd, 6), day.blind) == (0.15, 0), "midnight itself is today"

    async def test_a_blind_row_is_counted_as_blind_and_still_summed(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A day whose cost cannot be trusted is not a cheap day. Each table
        has its own idea of what blind means: a reading, a pass and a chat that
        errored were never billed at all, so they are unpriced without being
        blind; a run carries no error column, so its blind row is the one that
        billed nothing."""
        await _bill(
            session_factory,
            intents=(
                _intent_row(tenant=TENANT.value, created_at=NOW, cost=0.0, unpriced=True),
                _intent_row(
                    tenant=TENANT.value,
                    created_at=NOW,
                    cost=0.0,
                    unpriced=True,
                    error="503",
                    gesture_id="ges_refused",
                ),
            ),
            passes=(
                _pass(at=NOW, cost=0.02, unpriced=True),
                _pass(at=NOW, cost=0.0, unpriced=True, error="503", id="pas_refused"),
            ),
            runs=(
                _run(at=NOW, cost=0.0, unpriced=True),
                # Billed its other steps and lost one to a 503: unpriced, and
                # not the accident `blind` exists for.
                _run(at=NOW, cost=0.04, unpriced=True, id="run_partly_billed"),
            ),
            chats=(
                _chat(at=NOW, cost=0.08, unpriced=True),
                _chat(at=NOW, cost=0.0, unpriced=True, error="503", id="cht_refused"),
            ),
        )

        async with SqlUnitOfWork(session_factory) as uow:
            day = await uow.spend.today(TENANT, now=NOW)

        assert day.blind == 4, "one per table, and the refusals are not among them"
        assert round(day.cost_usd, 6) == 0.14, "a blind row still spends what it says"

    async def test_another_tenants_spending_is_not_in_this_days(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Every one of the four predicates is tenant-scoped, or one warehouse's
        morning closes another warehouse's day."""
        await _bill(
            session_factory,
            intents=(
                _intent_row(tenant=OTHER_TENANT.value, created_at=NOW, cost=5.0, unpriced=True),
            ),
            passes=(_pass(tenant=OTHER_TENANT.value, at=NOW, cost=5.0, unpriced=True),),
            runs=(_run(tenant=OTHER_TENANT.value, at=NOW, cost=5.0, unpriced=True),),
            chats=(_chat(tenant=OTHER_TENANT.value, at=NOW, cost=5.0, unpriced=True),),
        )
        await _bill(session_factory, chats=(_chat(at=NOW, cost=0.08),))

        async with SqlUnitOfWork(session_factory) as uow:
            mine = await uow.spend.today(TENANT, now=NOW)
            theirs = await uow.spend.today(OTHER_TENANT, now=NOW)

        assert (round(mine.cost_usd, 6), mine.blind) == (0.08, 0)
        # Three of their four rows are blind, not four: the run billed $5.00,
        # and a run that billed is not the accident `unpriced` exists for.
        assert (round(theirs.cost_usd, 6), theirs.blind) == (20.0, 3)

    async def test_a_day_nobody_spent_anything_in_is_zero_rather_than_nothing(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """``SUM`` over no rows is NULL, and a cap that reads NULL as a float
        is a cap that crashes on a quiet morning."""
        async with SqlUnitOfWork(session_factory) as uow:
            day = await uow.spend.today(TENANT, now=NOW)

        assert (day.cost_usd, day.blind) == (0.0, 0)

    async def test_a_now_with_no_zone_is_read_as_utc(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Midnight is UTC's, never the server's. A naive ``now`` read as local
        time moves the boundary by the machine's offset, which on a westward
        host bills yesterday evening to today."""
        await _bill(
            session_factory,
            chats=(_chat(at=JUST_YESTERDAY, cost=1.0), _chat(at=JUST_TODAY, cost=0.08)),
        )

        async with SqlUnitOfWork(session_factory) as uow:
            day = await uow.spend.today(TENANT, now=NOW.replace(tzinfo=None))

        assert round(day.cost_usd, 6) == 0.08


class TestWhatTheAuditReads:
    async def test_the_audit_reads_each_kind_since_a_time_newest_first(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The audit route's four selects: runs, offers, browsers and chats,
        plus the readings this backend keeps that the rig's route did not.
        Newest first, one tenant, from a time."""
        earlier, later = NOW - timedelta(hours=2), NOW
        before = NOW - timedelta(days=2)
        await _bill(
            session_factory,
            intents=(
                _intent_row(tenant=TENANT.value, created_at=before, cost=1.0),
                _intent_row(tenant=TENANT.value, created_at=earlier, cost=0.01),
                _intent_row(tenant=TENANT.value, created_at=later, cost=0.02),
            ),
            runs=(
                _run(at=before, cost=1.0),
                _run(at=earlier, cost=0.04),
                _run(at=later, cost=0.05),
            ),
            chats=(
                _chat(at=before, cost=1.0),
                _chat(at=earlier, cost=0.08),
                _chat(at=later, cost=0.09),
            ),
        )
        async with SqlUnitOfWork(session_factory) as uow:
            for at in (before, earlier, later):
                await uow.offers.record(
                    Offer(
                        id=new_offer_id(),
                        tenant=TENANT.value,
                        workflow_id="wfl_1",
                        device_id=DEVICE.value,
                        k=2,
                        fate="accepted",
                        at=at.isoformat(),
                    )
                )
            for at in (before, earlier, later):
                await uow.devices.add(
                    AgentDevice(
                        id=DeviceId(f"dev_{at.hour}_{at.day}"),
                        tenant_id=TENANT,
                        principal_id=PrincipalId("op_1"),
                        label=f"chrome {at.isoformat()}",
                        extension_version="1.0.0",
                        registered_at=at,
                        last_seen_at=at,
                        secret="s" * 32,
                    )
                )
            await uow.commit()

        since = (NOW - timedelta(days=1)).isoformat()
        async with SqlUnitOfWork(session_factory) as uow:
            runs = await uow.workflow_runs.since(TENANT, since=since)
            offers = await uow.offers.since(TENANT, since=since)
            chats = await uow.chats.since(TENANT, since=since)
            devices = await uow.devices.since(TENANT, since=since)
            intents = await uow.gestures.intents_since(TENANT, since=since)

        assert [run.started_at for run in runs] == [later.isoformat(), earlier.isoformat()]
        assert [offer.at for offer in offers] == [later.isoformat(), earlier.isoformat()]
        assert [chat.at for chat in chats] == [later.isoformat(), earlier.isoformat()]
        assert [device.registered_at for device in devices] == [later, earlier]
        assert [intent.cost_usd for intent in intents] == [0.02, 0.01]

    async def test_a_browser_revoked_since_is_read_even_though_it_registered_before(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """``revoked_at`` is the one fact the runs and offers cannot carry: who
        could act, and until when. A browser registered last month and revoked
        this morning belongs in this morning's audit."""
        long_ago = NOW - timedelta(days=30)
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.devices.add(
                AgentDevice(
                    id=DEVICE,
                    tenant_id=TENANT,
                    principal_id=PrincipalId("op_1"),
                    label="chrome",
                    extension_version="1.0.0",
                    registered_at=long_ago,
                    last_seen_at=long_ago,
                    secret="s" * 32,
                )
            )
            await uow.commit()

        since = (NOW - timedelta(days=1)).isoformat()
        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.devices.since(TENANT, since=since) == ()
            assert await uow.devices.revoke(TENANT, DEVICE, at=NOW.isoformat()) is True
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            revoked = await uow.devices.since(TENANT, since=since)

        assert [device.id for device in revoked] == [DEVICE]
        assert revoked[0].revoked_at == NOW.isoformat()

    async def test_a_since_with_no_zone_is_read_as_utc(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The rig's audit route normalised a zone-less ``since`` to UTC before
        it compared anything. A naive instant read as the server's local time
        moves the window by the machine's offset and quietly drops the hours
        either side of it."""
        await _bill(
            session_factory,
            chats=(
                _chat(at=NOW - timedelta(hours=2), cost=0.01),
                _chat(at=NOW, cost=0.02),
            ),
        )
        cut = NOW - timedelta(hours=1)

        async with SqlUnitOfWork(session_factory) as uow:
            aware = await uow.chats.since(TENANT, since=cut.isoformat())
            naive = await uow.chats.since(TENANT, since=cut.replace(tzinfo=None).isoformat())

        assert [chat.cost_usd for chat in naive] == [chat.cost_usd for chat in aware] == [0.02]

    async def test_another_tenants_history_is_not_in_this_audit(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """One audit, one tenant. The rig's own device select was the exception
        -- it read every tenant's browsers -- and it is not carried across."""
        await _bill(
            session_factory,
            intents=(_intent_row(tenant=OTHER_TENANT.value, created_at=NOW, cost=5.0),),
            runs=(_run(tenant=OTHER_TENANT.value, at=NOW, cost=5.0),),
            chats=(_chat(tenant=OTHER_TENANT.value, at=NOW, cost=5.0),),
        )
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.offers.record(
                Offer(
                    id=new_offer_id(),
                    tenant=OTHER_TENANT.value,
                    workflow_id="wfl_1",
                    device_id=DEVICE.value,
                    k=2,
                    fate="accepted",
                    at=NOW.isoformat(),
                )
            )
            await uow.devices.add(
                AgentDevice(
                    id=DeviceId("dev_theirs"),
                    tenant_id=OTHER_TENANT,
                    principal_id=PrincipalId("op_2"),
                    label="chrome",
                    extension_version="1.0.0",
                    registered_at=NOW,
                    last_seen_at=NOW,
                    secret="s" * 32,
                )
            )
            await uow.commit()

        since = (NOW - timedelta(days=1)).isoformat()
        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.workflow_runs.since(TENANT, since=since) == ()
            assert await uow.offers.since(TENANT, since=since) == ()
            assert await uow.chats.since(TENANT, since=since) == ()
            assert await uow.devices.since(TENANT, since=since) == ()
            assert await uow.gestures.intents_since(TENANT, since=since) == ()
            assert len(await uow.workflow_runs.since(OTHER_TENANT, since=since)) == 1
