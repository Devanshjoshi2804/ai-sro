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
from sro.domain.execution.run import Medium
from sro.domain.shared.identifiers import DeviceId, RecordingId, SkillId
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.track_record import REQUIRED_CLEAN_RUNS, TrackRecord
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
    to. The default step's `UiPlan` carries no locator, so the UI medium this
    call always drives ends every run in a clean SKIPPED disposition rather
    than an exception -- there is nothing for `_perform_in_ui` to find."""
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

    run = await _runner(uow, clock).execute(
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
    # Always the operator's own tab, never a silent HTTP replay: ADR 014's
    # whole argument for treating a preview as a review rests on the operator
    # having read the screen the run acts on, which only holds if the run
    # actually drives that screen.
    assert run.medium is Medium.UI


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
    """A version one rung below the ceiling, with a clean streak already at
    `REQUIRED_CLEAN_RUNS` -- exactly the record `earn` would act on -- still
    stops at ASSISTED. Distinct from "already running": here the press *does*
    promote (SHADOW has never been reviewed by a press before), and the
    version it produces has every number `earn` looks at already satisfied.
    The rungs above assisted are earned by runs, not by presses -- `earn` is a
    separate mechanism this call never invokes."""
    uow = FakeUnitOfWork()
    before = f.at(700)
    await _skill_at(
        uow,
        PromotionStage.SHADOW,
        at=before,
        track_record=replace(TrackRecord(), clean_streak=REQUIRED_CLEAN_RUNS),
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
    # It did move -- unlike the already-assisted case above -- just not past
    # where a press is allowed to put it.
    assert version.promoted_at == f.at(2000)


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
    `acknowledging_fixed_values=True`. Kept as an accepted residual risk, the
    same way ADR 014 already accepts that a preview does not show which steps
    write: `run.wrong_because` plus `DEMOTE_AFTER_FAILURES` is the backstop for
    both gaps, not a claim that the operator already read these particular
    values. Without the flag this is exactly the version `promote` refuses --
    one demonstration, one write -- which is the commonest shape a freshly
    induced skill has. See `RunFromPreview` and ADR 014's amended
    "Consequences" for the full argument."""
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


async def test_the_run_is_pinned_to_the_version_this_press_promoted() -> None:
    """A second induction landing between this call's own promotion committing
    and the run resolving which version to perform must not run the new one
    instead. `RunFromPreview.begin` reads `version.version` before releasing
    its own unit of work and passes it explicitly, so `ExecuteSkill` never asks
    "the latest version" a second time and gets a different answer."""
    uow = FakeUnitOfWork()
    skill = f.skill(versions=0)
    skill.add_version(f.skill_version())  # v1, RECORDED
    await uow.skills.add(skill)

    calls = 0
    real_get = uow.skills.get

    async def racing_get(tenant_id: object, skill_id: object) -> object:
        nonlocal calls
        calls += 1
        got = await real_get(tenant_id, skill_id)  # type: ignore[misc]
        if calls == 2:
            # The race: a second demonstration lands and is appended right
            # after this call's own promotion has already committed v1 to
            # ASSISTED, before `ExecuteSkill` has resolved which version to
            # start -- this is the second `skills.get`, inside `StartRun`.
            got.add_version(f.skill_version(version=2))
        return got

    uow.skills.get = racing_get  # type: ignore[method-assign]
    clock = FakeClock(f.at(1000))

    run = await _runner(uow, clock).execute(
        OPERATOR,
        skill_id=SkillId("skill-1"),
        parameters={"shipment_id": "555"},
        device_id=DEVICE,
        intent="",
    )

    assert run.skill_version == 1
