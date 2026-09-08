"""Repositories against real Postgres."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.domain.execution.run import Medium, Run, RunId, StepDisposition, StepOutcome
from sro.domain.observation.batch import CaptureMode, ObservationBatch, RejectedEvent
from sro.domain.observation.candidate import Episode, TaskCandidate
from sro.domain.observation.device import AgentDevice
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.shared.errors import Conflict, NotFound
from sro.domain.shared.identifiers import (
    BatchId,
    BrowserSessionId,
    CandidateId,
    DeviceId,
    RecordingId,
    SkillId,
    TenantId,
    TriggerId,
)
from sro.domain.skill.locator import ControlLocator, LocatorStrategy
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.template import Template
from sro.domain.trigger.trigger import Trigger, TriggerKind
from sro.domain.trigger.watch import Term, TermField, ValueAt, Watch
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

    async def test_two_reviewers_promoting_two_versions_do_not_undo_each_other(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The gap the append check left, and the comment that called it safe.

        `latest_version` only moves when a version is appended, so a promotion
        left it alone and two of them raced. That was called correct on the
        grounds that a stage is one field -- but it is not one field that gets
        written, it is the JSONB document all the versions live in, so the
        second reviewer's save silently undid the first's.
        """
        skill = f.skill(versions=0, id=SkillId("skill-two-rungs"))
        skill.add_version(f.skill_version(version=1))
        skill.add_version(f.skill_version(version=2))

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.skills.add(skill)
            await uow.commit()

        async with (
            SqlUnitOfWork(session_factory) as first,
            SqlUnitOfWork(session_factory) as second,
        ):
            mine = await first.skills.get(skill.tenant_id, skill.id)
            theirs = await second.skills.get(skill.tenant_id, skill.id)
            mine.version(1).promote(PromotionStage.SHADOW, f.at(700), f.OPERATOR)
            theirs.version(2).promote(PromotionStage.SHADOW, f.at(700), f.OPERATOR)

            await first.skills.save(mine)
            await first.commit()

            await second.skills.save(theirs)
            with pytest.raises(Conflict):
                await second.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            again = await uow.skills.get(skill.tenant_id, skill.id)

        # The first reviewer's decision is still there. Without the check it was
        # gone, and the screen showed version 1 back at `recorded` with nothing
        # to say why.
        assert again.version(1).stage is PromotionStage.SHADOW
        assert again.version(2).stage is PromotionStage.RECORDED

    async def test_two_writers_appending_at_once_do_not_lose_one_of_them(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Every version lives in one JSONB document, so both writers read the
        same list, appended to their own copy, and the second overwrote the
        first. Two runs finishing together lost a repair; a repair racing a
        demonstration lost the demonstration. Nothing said so.
        """
        skill = f.skill(id=SkillId("skill-race"))

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.skills.add(skill)
            await uow.commit()

        async with (
            SqlUnitOfWork(session_factory) as first,
            SqlUnitOfWork(session_factory) as second,
        ):
            mine = await first.skills.get(skill.tenant_id, skill.id)
            theirs = await second.skills.get(skill.tenant_id, skill.id)
            mine.add_version(f.skill_version(version=2, summary="mine"))
            theirs.add_version(f.skill_version(version=2, summary="theirs"))

            await first.skills.save(mine)
            await first.commit()

            await second.skills.save(theirs)
            with pytest.raises(Conflict):
                await second.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            again = await uow.skills.get(skill.tenant_id, skill.id)

        assert len(again.versions) == 2
        assert again.latest.summary == "mine", "the write that landed is the one that is there"


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
            stored = await uow.devices.get(device.tenant_id, device.id)
            assert stored.label == "laptop"
            # The one column a device is refused without. A round trip that
            # dropped it would lock every browser out on its next heartbeat.
            assert stored.secret == device.secret
            with pytest.raises(NotFound):
                await uow.devices.get(OTHER_TENANT, device.id)
            assert await uow.devices.list_for_tenant(OTHER_TENANT) == ()

    async def test_one_operator_cannot_register_the_same_label_twice(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.devices.add(_device(device_id="dev-1"))
            await uow.commit()

        # A raced registration finds this as Conflict, not a raw driver
        # exception with no registered handler -- RegisterDevice catches it
        # and comes back as the winner, which needs a classified error to do.
        with pytest.raises(Conflict):
            async with SqlUnitOfWork(session_factory) as uow:
                await uow.devices.add(_device(device_id="dev-2"))
                await uow.commit()

    async def test_a_revoked_browser_is_let_back_in_with_the_secret_it_had(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The un-revoke, against real SQL rather than the fake's dict.

        The fake sets an attribute on an object it is already holding, so it
        cannot tell a `revoked_at = NULL` that reached the column from one that
        did not -- and it cannot see that the secret column was left alone,
        which is the whole reason a restored browser needs no reinstall.
        """
        device = _device()
        ended = f.at(600).isoformat()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.devices.add(device)
            assert await uow.devices.revoke(device.tenant_id, device.id, at=ended) is True
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            # Another tenant pressing at this id moves nothing and is told
            # nothing, as the revoke is.
            with pytest.raises(NotFound):
                await uow.devices.restore(OTHER_TENANT, device.id)
            assert await uow.devices.restore(device.tenant_id, device.id) is True
            # Read back inside the same session: the row this returns is the
            # one just written, which is what the lock and the read-then-set
            # are for.
            assert (await uow.devices.get(device.tenant_id, device.id)).revoked_at is None
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            stored = await uow.devices.get(device.tenant_id, device.id)
            assert stored.revoked_at is None
            assert stored.secret == device.secret
            # Idempotent: a second press moved nothing, so nothing about the
            # row says this browser was ever revoked twice.
            assert await uow.devices.restore(device.tenant_id, device.id) is False

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
        principal_id=f.OPERATOR,
        label="laptop",
        extension_version="0.1.0",
        registered_at=at,
        last_seen_at=at,
        secret="what-this-browser-proves-it-is-itself-with",  # noqa: S106
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
        principal_id=f.OPERATOR,
        mode=CaptureMode.PASSIVE,
        started_at=started_at or at,
        ended_at=ended_at or at,
        received_at=at,
        uri=f"s3://sro-artifacts/{f.TENANT}/{f.OPERATOR}/2026-03-01/bat-1.ndjson",
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
        assert loaded.authorized_by == f.OPERATOR
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

    async def test_a_watch_comes_back_with_its_terms_and_its_places_to_read(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A rule an operator wrote by pointing at one mail, over a laptop reboot.

        Both halves have to survive intact, and they are different halves: the
        terms are the operator's own text and are the only thing that decides
        whether a mail is one of these, while the values are locations and carry
        no text at all. A round trip that lost the terms would leave a trigger
        that fires on every mail that arrives.
        """
        watch = Watch(
            host="mail.example.com",
            terms=(
                Term(field=TermField.SENDER, contains="orders@supplier.test"),
                Term(field=TermField.SUBJECT, contains="Dispatch note"),
            ),
            values=(
                ValueAt(
                    name="order",
                    where=ControlLocator(
                        strategy=LocatorStrategy.CSS_PATH,
                        query=Template("span.order-ref"),
                        within="div.mail-body",
                    ),
                ),
            ),
            sender_at=ControlLocator(
                strategy=LocatorStrategy.CSS_PATH, query=Template("span.from")
            ),
            subject_at=ControlLocator(
                strategy=LocatorStrategy.CSS_PATH, query=Template("h1.subject")
            ),
        )
        trigger = _trigger(
            kind=TriggerKind.WATCH, cron=None, watch=watch, device_id=DeviceId("dev-1")
        )

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.triggers.add(trigger)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            loaded = await uow.triggers.get(trigger.tenant_id, trigger.id)

        assert loaded.watch == watch
        assert loaded.watch is not None
        assert loaded.watch.matches(
            "mail.example.com", sender="orders@supplier.test", subject="Dispatch note 41"
        )
        # Derived from the watch on the way out, not stored twice.
        assert loaded.from_message == ("order",)


def _trigger(
    *,
    kind: TriggerKind = TriggerKind.SCHEDULE,
    cron: str | None = "0 7 * * 1-5",
    watch: Watch | None = None,
    device_id: DeviceId | None = None,
) -> Trigger:
    return Trigger(
        id=TriggerId("trg-1"),
        tenant_id=TenantId("acme"),
        skill_id=SkillId("skill-1"),
        kind=kind,
        created_by=f.OPERATOR,
        created_at=datetime(2026, 3, 1, 9, 0, tzinfo=UTC),
        parameters={"facility": "SG"},
        watch=watch,
        device_id=device_id,
        cron=cron,
        timezone="Asia/Kolkata",
        writes=True,
        authorized_by=f.OPERATOR,
        requires_confirmation=False,
    )


class TestRuns:
    async def test_a_workflow_s_failure_is_found_by_either_system_s_breaker(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The read the circuit breaker does, against real JSONB.

        A run that checked the WMS and wrote to the ERP is stored under the
        system it is keyed by. Asked about the other one, a breaker that matched
        only on that key would answer "nothing has failed here lately" about the
        system the failure actually landed in.
        """
        skill = f.skill()
        version = skill.versions[0]
        run = Run(
            id=RunId("run-cross"),
            tenant_id=f.TENANT,
            skill_id=skill.id,
            skill_version=version.version,
            stage=version.stage,
            parameters={},
            requested_by=f.OPERATOR,
            started_at=datetime(2026, 8, 25, 9, 0, tzinfo=UTC),
            target_system="blue_yonder",
            systems=("blue_yonder", "sap"),
        )
        run.fail(datetime(2026, 8, 25, 9, 5, tzinfo=UTC), "the ERP refused the receipt")

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.skills.add(skill)
            await uow.runs.add(run)
            await uow.commit()

        since = datetime(2026, 8, 25, 8, 0, tzinfo=UTC)
        async with SqlUnitOfWork(session_factory) as uow:
            loaded = await uow.runs.get(f.TENANT, run.id)
            keyed = await uow.runs.finished_since(
                f.TENANT, target_system="blue_yonder", since=since
            )
            touched = await uow.runs.finished_since(f.TENANT, target_system="sap", since=since)
            elsewhere = await uow.runs.finished_since(f.TENANT, target_system="oracle", since=since)

        assert loaded.systems == ("blue_yonder", "sap")
        assert [each.id for each in keyed] == [run.id]
        assert [each.id for each in touched] == [run.id]
        assert elsewhere == (), "a system this run never touched must not see its failure"


class TestLoopingRuns:
    async def test_what_a_loop_is_iterating_over_survives_a_restart(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A run that resumes must do the iterations it started with.

        Re-reading the list on the way back up would act on whatever the
        warehouse says now -- a different task under the same run id, half of it
        already done.
        """
        skill = f.skill()
        version = skill.versions[0]
        run = Run(
            id=RunId("run-loop"),
            tenant_id=f.TENANT,
            skill_id=skill.id,
            skill_version=version.version,
            stage=version.stage,
            parameters={},
            requested_by=f.OPERATOR,
            started_at=datetime(2026, 8, 26, 9, 0, tzinfo=UTC),
        )
        run.will_iterate(1, [{"line_id": "7"}, {"line_id": "8"}])
        for position, (plan_step, iteration, intent) in enumerate(
            ((0, 0, "open the order"), (1, 0, "adjust the line"))
        ):
            run.record(
                StepOutcome(
                    index=position,
                    plan_step=plan_step,
                    iteration=iteration,
                    medium=Medium.NETWORK,
                    disposition=StepDisposition.PERFORMED,
                    intent=intent,
                )
            )

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.skills.add(skill)
            await uow.runs.add(run)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            loaded = await uow.runs.get(f.TENANT, run.id)

        assert loaded.iterations_of(1) == [{"line_id": "7"}, {"line_id": "8"}]
        # And which step of the plan each position was, which is what tells a
        # resumed run that line 7 is already done.
        assert (loaded.steps[1].step_index, loaded.steps[1].iteration) == (1, 0)


class TestCandidates:
    async def test_a_candidate_round_trips_with_its_episodes_and_stays_its_tenants(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        candidate = _candidate()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.candidates.add(candidate)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            loaded = await uow.candidates.get(candidate.tenant_id, candidate.id)
            with pytest.raises(NotFound):
                await uow.candidates.get(OTHER_TENANT, candidate.id)
            assert await uow.candidates.list_for_tenant(OTHER_TENANT) == ()

        assert loaded.times_seen == 2
        assert loaded.episodes[0].gestures == 4
        assert loaded.median_duration_ms == 45_000

    async def test_the_same_task_mined_twice_cannot_become_two_candidates(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        # The unique index is what makes re-running the miner safe.
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.candidates.add(_candidate())
            await uow.commit()

        # A manual mine-now request racing the scheduled sweep onto the same
        # candidate finds this as Conflict, not a raw driver exception no
        # handler in errors.py knows what to do with.
        with pytest.raises(Conflict):
            async with SqlUnitOfWork(session_factory) as uow:
                await uow.candidates.add(_candidate(candidate_id="cnd-2"))
                await uow.commit()

    async def test_only_what_has_happened_often_enough_comes_back(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.candidates.add(_candidate())
            await uow.candidates.add(
                _candidate(candidate_id="cnd-rare", signature="GET api/waves", episodes=1)
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            offered = await uow.candidates.list_for_tenant(TenantId("acme"), seen_at_least=2)

        assert [one.id.value for one in offered] == ["cnd-1"]

    async def test_one_system_at_a_time_for_the_panel_docked_beside_it(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """ "Tasks you keep doing *here*" is a different question from "tasks you
        keep doing", and it is the one the extension's side panel asks of the
        tab it is open next to. Filtering after the fact would let a busy
        morning elsewhere push the answer off the list."""
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.candidates.add(_candidate())
            await uow.candidates.add(
                _candidate(candidate_id="cnd-erp", signature="POST erp/receipts", host="erp.test")
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            here = await uow.candidates.list_for_tenant(TenantId("acme"), host="wms.acme.test")
            # Hosts are stored lowercased by the segmenter, so how the caller
            # happens to spell one must not decide whether their tasks come back.
            shouting = await uow.candidates.list_for_tenant(TenantId("acme"), host="WMS.ACME.TEST")

        assert [one.id.value for one in here] == ["cnd-1"]
        assert [one.id.value for one in shouting] == ["cnd-1"]


def _candidate(
    *,
    candidate_id: str = "cnd-1",
    signature: str = "POST api/suppliers",
    episodes: int = 2,
    host: str = "wms.acme.test",
) -> TaskCandidate:
    at = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)
    return TaskCandidate(
        id=CandidateId(candidate_id),
        tenant_id=TenantId("acme"),
        principal_id=f.OPERATOR,
        signature=signature,
        host=host,
        title="Create suppliers on wms.acme.test",
        episodes=tuple(
            Episode(
                started_at=at + timedelta(hours=hour),
                ended_at=at + timedelta(hours=hour, seconds=45),
                host="wms.acme.test",
                batch_ids=(BatchId(f"bat-{hour}"),),
                gestures=4,
                calls=3,
            )
            for hour in range(episodes)
        ),
    )
