"""The press that runs a skill for the first time.

`_check_runnable` refuses a RECORDED version because nobody has reviewed it.
After the preview somebody has -- so this promotes and runs in one call, because
two calls race and a version promoted by a press that then failed to start is a
version at assisted because somebody clicked once and walked away.
"""

from __future__ import annotations

from dataclasses import replace

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import ExecuteSkill
from sro.application.execution.run_from_preview import RunFromPreview
from sro.domain.shared.identifiers import DeviceId, RecordingId, SkillId
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.track_record import TrackRecord
from tests import factories as f
from tests.unit.fakes import (
    FakeClock,
    FakeCredentialVault,
    FakeHttpCaller,
    FakeIdFactory,
    FakeUnitOfWork,
)

OPERATOR = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
DEVICE = DeviceId("dev-1")


def _runner(uow: FakeUnitOfWork, clock: FakeClock) -> RunFromPreview:
    """Same shape as `_executor` in test_execute_skill.py: a fake uow, http and
    vault behind an `ExecuteSkill`, with no agent driver -- the run this call
    triggers has nowhere live to go, and none of these tests is about whether
    it lands. They are about what happens to the version before it is asked
    to."""
    executor = ExecuteSkill(uow, FakeHttpCaller(), FakeCredentialVault(), clock, FakeIdFactory())
    return RunFromPreview(uow, clock, executor)


async def _skill_at(
    uow: FakeUnitOfWork,
    stage: PromotionStage,
    *,
    at: object,
    recordings: int = 2,
    track_record: TrackRecord = TrackRecord(),
) -> None:
    """A skill with one version at `stage`, promoted one rung at a time as a
    reviewer would -- following `_skill` in test_execute_skill.py."""
    version = f.skill_version(
        provenance=f.provenance(
            recording_ids=tuple(RecordingId(f"rec-{n}") for n in range(1, recordings + 1))
        ),
        track_record=track_record,
    )
    skill = f.skill(versions=0)
    skill.add_version(version)
    current = PromotionStage.RECORDED
    while current is not stage:
        current = current.next_stage()
        version.promote(current, at, f.OPERATOR, acknowledging_fixed_values=True)
    await uow.skills.add(skill)


async def test_the_press_promotes_a_recorded_version_and_runs_it() -> None:
    uow = FakeUnitOfWork()
    skill = f.skill(versions=0)
    skill.add_version(f.skill_version())  # RECORDED, the default stage
    await uow.skills.add(skill)
    clock = FakeClock(f.at(1000))

    await _runner(uow, clock).execute(
        OPERATOR,
        skill_id=SkillId("skill-1"),
        parameters={"shipment_id": "555"},
        device_id=DEVICE,
        intent="create work operation NDPCK, north dock picking",
    )

    version = (await uow.skills.get(f.TENANT, SkillId("skill-1"))).latest
    assert version.stage is PromotionStage.ASSISTED
    assert version.promoted_from == "preview"
    assert version.promoted_by == f.OPERATOR


async def test_a_version_already_running_is_not_promoted_again() -> None:
    """A press on the fifth run is not a fifth promotion. Only a version that
    cannot run yet is moved, and only as far as it needs to go."""
    uow = FakeUnitOfWork()
    before = f.at(700)
    await _skill_at(uow, PromotionStage.ASSISTED, at=before)
    clock = FakeClock(f.at(2000))

    await _runner(uow, clock).execute(
        OPERATOR,
        skill_id=SkillId("skill-1"),
        parameters={"shipment_id": "555"},
        device_id=DEVICE,
        intent="create work operation NDPCK, north dock picking",
    )

    version = (await uow.skills.get(f.TENANT, SkillId("skill-1"))).latest
    assert version.stage is PromotionStage.ASSISTED
    assert version.promoted_at == before


async def test_the_press_never_reaches_past_assisted() -> None:
    """Even pressed on an assisted version with ten clean runs behind it. The
    rungs above are earned by runs, not by presses."""
    uow = FakeUnitOfWork()
    await _skill_at(
        uow,
        PromotionStage.ASSISTED,
        at=f.at(700),
        track_record=replace(TrackRecord(), clean_streak=10),
    )
    clock = FakeClock(f.at(2000))

    await _runner(uow, clock).execute(
        OPERATOR,
        skill_id=SkillId("skill-1"),
        parameters={"shipment_id": "555"},
        device_id=DEVICE,
        intent="create work operation NDPCK, north dock picking",
    )

    version = (await uow.skills.get(f.TENANT, SkillId("skill-1"))).latest
    assert version.stage is PromotionStage.ASSISTED


async def test_the_sentence_they_typed_is_on_the_run() -> None:
    """`Run.intent` is the audit answer to "why did this happen". A run started
    from a sentence records the sentence; there is no second store for it."""
    uow = FakeUnitOfWork()
    skill = f.skill(versions=0)
    skill.add_version(f.skill_version())
    await uow.skills.add(skill)
    clock = FakeClock(f.at(1000))

    run = await _runner(uow, clock).execute(
        OPERATOR,
        skill_id=SkillId("skill-1"),
        parameters={"shipment_id": "555"},
        device_id=DEVICE,
        intent="create work operation NDPCK, north dock picking",
    )

    assert run.intent == "create work operation NDPCK, north dock picking"


async def test_a_write_from_one_demonstration_still_reaches_assisted() -> None:
    """Pins the task 5 ruling: a preview promotion passes
    `acknowledging_fixed_values=True`, because the same press already trusted
    with "this version may act for real" (the jump to ASSISTED) has already
    been trusted with the strictly narrower "and these particular values are
    what it sends". Without the flag this is exactly the version `promote`
    refuses -- one demonstration, one write -- which is the commonest shape a
    freshly induced skill has. See `RunFromPreview` for the full argument."""
    uow = FakeUnitOfWork()
    skill = f.skill(versions=0)
    skill.add_version(
        f.skill_version(provenance=f.provenance(recording_ids=(RecordingId("rec-1"),)))
    )
    await uow.skills.add(skill)
    clock = FakeClock(f.at(1000))

    await _runner(uow, clock).execute(
        OPERATOR,
        skill_id=SkillId("skill-1"),
        parameters={"shipment_id": "555"},
        device_id=DEVICE,
        intent="create work operation NDPCK, north dock picking",
    )

    version = (await uow.skills.get(f.TENANT, SkillId("skill-1"))).latest
    assert version.stage is PromotionStage.ASSISTED
