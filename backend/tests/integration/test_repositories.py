"""Repositories against real Postgres."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.domain.observation.batch import CaptureMode, ObservationBatch, RejectedEvent
from sro.domain.observation.device import AgentDevice
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.shared.errors import Conflict, NotFound
from sro.domain.shared.identifiers import (
    BatchId,
    BrowserSessionId,
    DeviceId,
    PrincipalId,
    RecordingId,
    SkillId,
    TenantId,
    TriggerId,
)
from sro.domain.skill.promotion import PromotionStage
from sro.domain.trigger.trigger import Trigger, TriggerKind
from sro.infrastructure.db.repositories import SqlUnitOfWork
from tests import factories as f

OTHER_TENANT = TenantId("other-corp")


class TestRecordings:
    async def test_a_recording_survives_the_round_trip_with_its_frames(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        recording = f.recording(frames=0)
        recording.append_frame(f.frame(requests=(f.request(),)))

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.recordings.add(recording)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            loaded = await uow.recordings.get(recording.tenant_id, recording.id)

        assert len(loaded.frames) == 1
        request = loaded.frames[0].requests[0]
        assert request.request_headers["Authorization"] == "Bearer live-token"
        assert request.initiator is not None

    async def test_another_tenant_cannot_read_it(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        recording = f.recording()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.recordings.add(recording)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            with pytest.raises(NotFound):
                await uow.recordings.get(OTHER_TENANT, recording.id)

    async def test_leaving_the_block_without_committing_writes_nothing(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        recording = f.recording(id=RecordingId("rec-rollback"))

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.recordings.add(recording)

        async with SqlUnitOfWork(session_factory) as uow:
            with pytest.raises(NotFound):
                await uow.recordings.get(recording.tenant_id, recording.id)

    async def test_listing_filters_by_objective(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        wanted = f.recording(id=RecordingId("rec-a"))
        other = f.recording(
            id=RecordingId("rec-b"), objective_key=f.objective(objective_type="count_cycle")
        )

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.recordings.add(wanted)
            await uow.recordings.add(other)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            found = await uow.recordings.list_for_tenant(
                wanted.tenant_id, objective_key=wanted.objective_key
            )

        assert [r.id for r in found] == [wanted.id]


class TestSkills:
    async def test_versions_and_provenance_round_trip(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        skill = f.skill()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.skills.add(skill)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            loaded = await uow.skills.get(skill.tenant_id, skill.id)

        assert loaded.latest.version == skill.latest.version
        assert loaded.latest.provenance.recording_ids == skill.latest.provenance.recording_ids
        assert loaded.latest.steps[0].intent == skill.latest.steps[0].intent

    async def test_find_by_objective_returns_none_rather_than_raising(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.skills.find_by_objective(TenantId("acme"), f.objective()) is None

    async def test_promotion_persists(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        skill = f.skill(id=SkillId("skill-promote"))

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.skills.add(skill)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            loaded = await uow.skills.get(skill.tenant_id, skill.id)
            loaded.latest.promote(PromotionStage.SHADOW, f.at(600), f.OPERATOR)
            await uow.skills.save(loaded)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            again = await uow.skills.get(skill.tenant_id, skill.id)

        assert again.latest.stage.value == "shadow"


class TestBrowserOwnership:
    """The claims that say whose a browser is, in SQL.

    The fakes enforce isolation structurally -- they cannot answer a question
    the wrong way -- so a missing `WHERE tenant_id` is invisible to every unit
    test in the suite. This is the only place that clause is really exercised.
    """

    async def test_a_claim_is_visible_only_to_the_tenant_that_made_it(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.browser_sessions.claim(
                f.TENANT, BrowserSessionId("sess-1"), f.OPERATOR, f.at(10)
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.browser_sessions.held_by(f.TENANT) == (BrowserSessionId("sess-1"),)
            assert await uow.browser_sessions.held_by(OTHER_TENANT) == ()

    async def test_one_browser_cannot_be_claimed_twice(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The primary key is the security property: a second claim means the
        provider handed one browser to two callers, and that must fail rather
        than transfer it."""
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.browser_sessions.claim(
                f.TENANT, BrowserSessionId("sess-2"), f.OPERATOR, f.at(10)
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            with pytest.raises(Conflict):
                await uow.browser_sessions.claim(
                    OTHER_TENANT, BrowserSessionId("sess-2"), f.OPERATOR, f.at(20)
                )

    async def test_the_sweep_sees_every_claim_and_no_tenant(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.browser_sessions.claim(
                f.TENANT, BrowserSessionId("sess-3"), f.OPERATOR, f.at(10)
            )
            await uow.browser_sessions.claim(
                OTHER_TENANT, BrowserSessionId("sess-4"), f.OPERATOR, f.at(20)
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            held = await uow.browser_sessions.all_held()
            await uow.browser_sessions.release(BrowserSessionId("sess-3"))
            await uow.commit()

        assert {str(session_id) for session_id, _ in held} == {"sess-3", "sess-4"}
        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.browser_sessions.held_by(f.TENANT) == ()


class TestObservation:
    """The tables the extension writes into, against real SQL.

    The fakes filter by tenant structurally, so they cannot tell a missing
    ``WHERE tenant_id`` from a present one. This is the only place that can.
    """

    async def test_a_device_is_visible_only_to_the_tenant_it_belongs_to(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        device = _device()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.devices.add(device)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert (await uow.devices.get(device.tenant_id, device.id)).label == "laptop"
            with pytest.raises(NotFound):
                await uow.devices.get(OTHER_TENANT, device.id)
            assert await uow.devices.list_for_tenant(OTHER_TENANT) == ()

    async def test_one_operator_cannot_register_the_same_label_twice(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.devices.add(_device(device_id="dev-1"))
            await uow.commit()

        with pytest.raises(IntegrityError):
            async with SqlUnitOfWork(session_factory) as uow:
                await uow.devices.add(_device(device_id="dev-2"))
                await uow.commit()

    async def test_a_batch_id_the_extension_reused_is_refused_rather_than_doubled(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.observations.add(_batch())
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            with pytest.raises(Conflict):
                await uow.observations.add(_batch())

    async def test_a_window_finds_a_batch_that_began_before_it(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        # Overlap, not containment: a batch that started at 08:58 and ended at
        # 09:03 holds events the 09:00 window asked for.
        batch = _batch(
            started_at=datetime(2026, 3, 1, 8, 58, tzinfo=UTC),
            ended_at=datetime(2026, 3, 1, 9, 3, tzinfo=UTC),
        )

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.observations.add(batch)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            found = await uow.observations.between(
                batch.tenant_id, since=datetime(2026, 3, 1, 9, 0, tzinfo=UTC)
            )
            theirs = await uow.observations.between(
                OTHER_TENANT, since=datetime(2026, 3, 1, 9, 0, tzinfo=UTC)
            )

        assert [one.id for one in found] == [batch.id]
        assert theirs == ()

    async def test_a_purge_leaves_another_tenants_rows_where_they_were(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        mine, theirs = _batch(), _batch(batch_id="bat-2", tenant_id=OTHER_TENANT)

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.observations.add(mine)
            await uow.observations.add(theirs)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.observations.forget(mine.tenant_id, (mine.id, theirs.id))
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.observations.get(mine.tenant_id, mine.id) is None
            assert await uow.observations.get(OTHER_TENANT, theirs.id) is not None

    async def test_a_policy_round_trips_and_stays_the_tenants_own(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        policy = ObservationPolicy().enabled().excluding(("payroll.acme.com",))

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.observation_policies.save(TenantId("acme"), policy)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            stored = await uow.observation_policies.get(TenantId("acme"))
            assert await uow.observation_policies.get(OTHER_TENANT) is None

        assert stored is not None
        assert stored.capture_enabled is True
        assert stored.exclude_hosts == ("payroll.acme.com",)
        assert stored.version == policy.version


def _device(*, device_id: str = "dev-1") -> AgentDevice:
    at = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)
    return AgentDevice(
        id=DeviceId(device_id),
        tenant_id=TenantId("acme"),
        principal_id=PrincipalId("devansh"),
        label="laptop",
        extension_version="0.1.0",
        registered_at=at,
        last_seen_at=at,
    )


def _batch(
    *,
    batch_id: str = "bat-1",
    tenant_id: TenantId = TenantId("acme"),
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
) -> ObservationBatch:
    at = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)
    return ObservationBatch(
        id=BatchId(batch_id),
        tenant_id=tenant_id,
        device_id=DeviceId("dev-1"),
        principal_id=PrincipalId("devansh"),
        mode=CaptureMode.PASSIVE,
        started_at=started_at or at,
        ended_at=ended_at or at,
        received_at=at,
        uri="s3://sro-artifacts/acme/devansh/2026-03-01/bat-1.ndjson",
        event_count=3,
        byte_count=512,
        rejected=(RejectedEvent(index=1, reason="an event kind nobody declared"),),
    )


class TestTriggers:
    async def test_a_trigger_round_trips_and_stays_the_tenants_own(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        trigger = _trigger()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.triggers.add(trigger)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            loaded = await uow.triggers.get(trigger.tenant_id, trigger.id)
            with pytest.raises(NotFound):
                await uow.triggers.get(OTHER_TENANT, trigger.id)
            assert await uow.triggers.list_for_tenant(OTHER_TENANT) == ()

        assert loaded.cron == "0 7 * * 1-5"
        assert loaded.parameters == {"facility": "SG"}
        assert loaded.authorized_by == PrincipalId("devansh")
        assert loaded.writes is True

    async def test_a_schedule_finds_its_trigger_without_being_told_the_tenant(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        # The one tenant-blind read in the system: a schedule fires with an id
        # and nothing else, and what comes back carries its own tenant.
        trigger = _trigger()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.triggers.add(trigger)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            found = await uow.triggers.find(trigger.id)
            missing = await uow.triggers.find(TriggerId("trg-nobody"))

        assert found is not None
        assert found.tenant_id == trigger.tenant_id
        assert missing is None


def _trigger() -> Trigger:
    return Trigger(
        id=TriggerId("trg-1"),
        tenant_id=TenantId("acme"),
        skill_id=SkillId("skill-1"),
        kind=TriggerKind.SCHEDULE,
        created_by=PrincipalId("devansh"),
        created_at=datetime(2026, 3, 1, 9, 0, tzinfo=UTC),
        parameters={"facility": "SG"},
        cron="0 7 * * 1-5",
        timezone="Asia/Kolkata",
        writes=True,
        authorized_by=PrincipalId("devansh"),
        requires_confirmation=False,
    )
