"""Repositories against real Postgres."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.domain.shared.errors import NotFound
from sro.domain.shared.identifiers import RecordingId, SkillId, TenantId
from sro.domain.skill.promotion import PromotionStage
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
