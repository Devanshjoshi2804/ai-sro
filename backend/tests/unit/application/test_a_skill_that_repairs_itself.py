"""A control moved, a verified run found it anyway, and the skill adopts that.

Escalation already carried the run: the UI rung found the button by a locator
the demonstration did not lead with, and the task got done. What did not happen
is the skill changing -- so every later run re-discovered the same drift, paid
the same escalation, and could never be `CLEAN` again. A skill that heals by
escalating works forever and can never again run unattended.
"""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import ExecuteSkill, ExecutionRequest
from sro.application.knowledge.open_questions import AskAbout
from sro.application.knowledge.record_claim import RecordClaims
from sro.application.skill.repair_drift import RepairDrift
from sro.domain.execution.run import (
    Medium,
    Run,
    RunId,
    RunStatus,
    StepDisposition,
    StepOutcome,
)
from sro.domain.knowledge.entry import EntryKind
from sro.domain.recording.events import ActionKind
from sro.domain.skill.locator import ControlLocator, LocatorStrategy
from sro.domain.skill.plan import Template, UiPlan
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import Skill, SkillVersion
from sro.domain.skill.track_record import TrackRecord
from tests import factories as f
from tests.unit.fakes import (
    FakeClock,
    FakeCredentialVault,
    FakeEmbedder,
    FakeHttpCaller,
    FakeIdFactory,
    FakeUiDriver,
    FakeUnitOfWork,
)

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)

TAUGHT = ControlLocator(strategy=LocatorStrategy.COMPONENT, query=Template("button#closeWave"))
FALLBACK = ControlLocator(strategy=LocatorStrategy.CSS_PATH, query=Template("div > button"))


def _version(*, number: int = 1) -> SkillVersion:
    """Two steps: a call, then a click. Only the click can drift."""
    return f.skill_version(
        version=number,
        steps=(
            f.step(index=0, ui_plan=None),
            f.step(
                index=1,
                intent="close the wave",
                network_plan=None,
                ui_plan=UiPlan(
                    action=ActionKind.CLICK,
                    target=f.fingerprint(accessible_name="Close wave"),
                    locators=(TAUGHT, FALLBACK),
                ),
            ),
        ),
    )


def _skill(version: SkillVersion) -> Skill:
    skill = f.skill(versions=0)
    skill.add_version(version)
    version.stage = PromotionStage.ASSISTED
    version.track_record = TrackRecord(clean_streak=7, clean_runs=7)
    return skill


def _run(*outcomes: StepOutcome, version: int = 1) -> Run:
    run = Run(
        id=RunId("run-1"),
        tenant_id=f.TENANT,
        skill_id=f.skill().id,
        skill_version=version,
        stage=PromotionStage.ASSISTED,
        parameters={},
        requested_by=f.OPERATOR,
        started_at=f.at(0),
        authorized_by=f.OPERATOR,
    )
    for outcome in outcomes:
        run.record(outcome)
    run.finish(f.at(60))
    return run


def _call() -> StepOutcome:
    return StepOutcome(
        index=0,
        medium=Medium.NETWORK,
        disposition=StepDisposition.PERFORMED,
        intent="release the wave",
        method="POST",
        url="https://wms.test/api/waves/1/release",
        status_code=200,
    )


def _click(**overrides: object) -> StepOutcome:
    defaults: dict[str, object] = {
        "index": 1,
        "medium": Medium.UI,
        "disposition": StepDisposition.PERFORMED,
        "intent": "close the wave",
        "matched_by": LocatorStrategy.CSS_PATH.value,
    }
    return StepOutcome(**{**defaults, **overrides})  # type: ignore[arg-type]


async def _repair(run: Run, skill: Skill) -> tuple[int | None, FakeUnitOfWork]:
    uow = FakeUnitOfWork()
    await uow.skills.add(skill)
    ask = AskAbout(uow, RecordClaims(uow, FakeClock(), FakeIdFactory(), FakeEmbedder()))
    return await RepairDrift(uow, FakeClock(), ask).execute(CTX, run=run), uow


async def test_a_locator_that_drifted_becomes_a_new_version() -> None:
    version = _version()
    skill = _skill(version)

    number, _ = await _repair(_run(_call(), _click()), skill)

    assert number == 2
    plan = skill.version(2).steps[1].ui_plan
    assert plan is not None
    assert plan.locators[0] is FALLBACK, "the plan now names the locator that worked"
    assert plan.locators[1] is TAUGHT, (
        "and keeps the one it was taught with behind it: a screen that changes "
        "back is not a screen this skill should be taught twice"
    )


async def test_every_other_step_comes_out_byte_identical() -> None:
    """A repair is the old version with one plan replaced, never a re-induction."""
    version = _version()
    skill = _skill(version)

    await _repair(_run(_call(), _click()), skill)

    assert skill.version(2).steps[0] is version.steps[0]
    assert skill.version(2).parameters == version.parameters
    assert skill.version(2).steps[1].intent == version.steps[1].intent
    old = version.steps[1].ui_plan
    new = skill.version(2).steps[1].ui_plan
    assert old is not None and new is not None
    assert (new.action, new.target, new.value) == (old.action, old.target, old.value)


async def test_the_version_it_repaired_is_left_exactly_where_it_was() -> None:
    """Nothing is edited in place, so a repair that was wrong is undone by
    promoting the older version again."""
    version = _version()
    skill = _skill(version)

    await _repair(_run(_call(), _click()), skill)

    plan = version.steps[1].ui_plan
    assert plan is not None
    assert plan.locators == (TAUGHT, FALLBACK)
    assert version.stage is PromotionStage.ASSISTED


async def test_the_repaired_version_starts_at_the_bottom_with_no_record() -> None:
    """Surviving one run is not ten clean ones."""
    version = _version()
    skill = _skill(version)

    await _repair(_run(_call(), _click()), skill)

    fresh = skill.version(2)
    assert fresh.track_record == TrackRecord(), "none of the old one's streak"
    assert fresh.stage.rung < version.stage.rung
    assert fresh.stage is PromotionStage.SHADOW, (
        "the rung a freshly taught version reaches: runnable, and nothing it "
        "sends leaves the process"
    )
    assert fresh is skill.runnable, "and it is what the next run is offered"


async def test_the_new_version_names_the_run_that_proved_it() -> None:
    """A skill that quietly rewrites itself is one nobody can trust."""
    skill = _skill(_version())

    await _repair(_run(_call(), _click()), skill)

    note = skill.version(2).provenance.note
    assert "run-1" in note
    assert "css_path" in note and "component" in note


async def test_a_run_that_failed_its_assertions_repairs_nothing() -> None:
    """It proves the skill and the system disagree, not which one is wrong.

    The click itself was clean and did drift. The run around it was not: an
    earlier step did not produce what the demonstration produced, so this run
    establishes nothing about where the system's controls are now.
    """
    skill = _skill(_version())
    run = _run(
        StepOutcome(
            index=0,
            medium=Medium.NETWORK,
            disposition=StepDisposition.PERFORMED,
            intent="release the wave",
            method="POST",
            url="https://wms.test/api/waves/1/release",
            status_code=200,
            assertion_failures=("/data/released is 'false'",),
        ),
        _click(),
    )
    assert run.status is RunStatus.FAILED

    number, _ = await _repair(run, skill)

    assert number is None
    assert len(skill.versions) == 1


async def test_a_control_found_where_it_was_taught_repairs_nothing() -> None:
    skill = _skill(_version())

    number, _ = await _repair(
        _run(_call(), _click(matched_by=LocatorStrategy.COMPONENT.value)), skill
    )

    assert number is None
    assert len(skill.versions) == 1


async def test_a_control_only_a_model_could_find_becomes_a_question() -> None:
    """At the UI rung the application's own structure found the control. At the
    vision rung a model read pixels and chose, and letting that write the skill
    is a model marking its own homework."""
    skill = _skill(_version())

    number, uow = await _repair(
        _run(_call(), _click(medium=Medium.VISION, matched_by="vision")), skill
    )

    assert number is None, "no version"
    assert len(skill.versions) == 1
    question = next(e for e in uow.knowledge.rows.values() if e.kind is EntryKind.QUESTION)
    assert "vision" in str(question.body["question"])
    assert "run-1" in str(question.body["because"])


async def test_a_repair_of_a_version_somebody_has_since_replaced_is_refused() -> None:
    """A later demonstration is later evidence than this run, and a repair of
    the older version would be appended in front of it."""
    old = _version()
    skill = _skill(old)
    skill.add_version(_version(number=2))

    number, _ = await _repair(_run(_call(), _click(), version=1), skill)

    assert number is None
    assert len(skill.versions) == 2


async def test_the_repaired_version_no_longer_drifts() -> None:
    """The repair is self-limiting: the next run matches what it was taught."""
    skill = _skill(_version())
    await _repair(_run(_call(), _click()), skill)
    skill.version(2).stage = PromotionStage.ASSISTED

    number, _ = await _repair(_run(_call(), _click(), version=2), skill)

    assert number is None
    assert len(skill.versions) == 2


async def test_a_real_run_that_escalated_leaves_a_repaired_version_behind() -> None:
    """The seam, end to end: the call 404s, the browser finishes the step by a
    locator the demonstration did not lead with, and closing the run adopts it.

    Worth its own test because everything above proves the use case is right and
    none of it proves anything is calling it.
    """
    uow = FakeUnitOfWork()
    version = f.skill_version(
        steps=(
            f.step(
                index=0,
                ui_plan=UiPlan(
                    action=ActionKind.CLICK,
                    target=f.fingerprint(accessible_name="Finish"),
                    locators=(TAUGHT, ControlLocator(LocatorStrategy.TEXT, Template("Finish"))),
                ),
            ),
        )
    )
    skill = f.skill(versions=0)
    skill.add_version(version)
    for stage in (PromotionStage.SHADOW, PromotionStage.ASSISTED):
        version.promote(stage, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)

    http, ui = FakeHttpCaller(), FakeUiDriver()
    http.answer(status_code=404, text='{"message": "Not Found"}')
    ui.will_find(LocatorStrategy.TEXT)
    ask = AskAbout(uow, RecordClaims(uow, FakeClock(), FakeIdFactory(), FakeEmbedder()))

    run = await ExecuteSkill(
        uow,
        http,
        FakeCredentialVault(),
        FakeClock(),
        FakeIdFactory(),
        ui,
        repair=RepairDrift(uow, FakeClock(), ask),
    ).execute(
        CTX,
        ExecutionRequest(
            skill_id=skill.id, parameters={"shipment_id": "555"}, authorized_by="supervisor"
        ),
    )

    assert run.status is RunStatus.SUCCEEDED
    assert run.steps[0].matched_by == LocatorStrategy.TEXT.value
    plan = skill.version(2).steps[0].ui_plan
    assert plan is not None
    assert plan.locators[0].strategy is LocatorStrategy.TEXT
