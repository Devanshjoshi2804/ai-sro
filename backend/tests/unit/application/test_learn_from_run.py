"""What a run teaches the store, and what it is not allowed to teach it."""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.knowledge.learn_from_run import LearnFromRun
from sro.application.knowledge.record_claim import RecordClaims
from sro.domain.execution.run import (
    Medium,
    Run,
    RunId,
    RunStatus,
    StepDisposition,
    StepOutcome,
)
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel
from sro.domain.recording.events import ActionKind
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.locator import ControlLocator, LocatorStrategy
from sro.domain.skill.plan import Template, UiPlan
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import SkillVersion
from tests import factories as f
from tests.unit.fakes import FakeClock, FakeEmbedder, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)


def _run(*outcomes: StepOutcome, finished: bool = True) -> Run:
    run = Run(
        id=RunId("run-1"),
        tenant_id=f.TENANT,
        skill_id=SkillId("skill-1"),
        skill_version=1,
        stage=PromotionStage.ASSISTED,
        parameters={},
        requested_by=f.OPERATOR,
        started_at=f.at(0),
        authorized_by=f.OPERATOR,
    )
    for outcome in outcomes:
        run.record(outcome)
    if finished:
        run.finish(f.at(60))
    return run


def _outcome(**overrides: object) -> StepOutcome:
    defaults: dict[str, object] = {
        "index": 0,
        "medium": Medium.NETWORK,
        "disposition": StepDisposition.PERFORMED,
        "intent": "adjust the count",
        "method": "PUT",
        "url": "https://wms.test/data/WM/wm/inventory/adjust?siteId=SG",
        "status_code": 200,
    }
    return StepOutcome(**{**defaults, **overrides})


async def _learn(run: Run, uow: FakeUnitOfWork) -> None:
    record = RecordClaims(uow, FakeClock(), FakeIdFactory(), FakeEmbedder())
    await LearnFromRun(record).execute(CTX, run=run, system="blue_yonder")


async def test_a_verified_call_becomes_something_the_store_knows() -> None:
    uow = FakeUnitOfWork()

    await _learn(_run(_outcome()), uow)

    entry = await uow.knowledge.current(
        f.TENANT,
        system="blue_yonder",
        kind=EntryKind.STATUS,
        key="PUT /data/WM/wm/inventory/adjust",
    )
    assert entry is not None
    assert entry.body["status"] == 200
    assert entry.source == "run-1", "the claim cites the run that proved it"
    assert entry.evidence is EvidenceLevel.REPRODUCED, (
        "the call was made and checked; nothing was created, read back and deleted"
    )


async def test_a_withheld_shadow_write_teaches_nothing() -> None:
    """It was built and never sent. Its status is unknown, not good."""
    uow = FakeUnitOfWork()

    await _learn(_run(_outcome(disposition=StepDisposition.WITHHELD, status_code=None)), uow)

    assert uow.knowledge.rows == {}


async def test_a_step_whose_assertions_failed_teaches_nothing() -> None:
    """The skill and the system disagree. Recording that would teach the store
    the skill's bugs as facts about the WMS."""
    uow = FakeUnitOfWork()

    await _learn(_run(_outcome(assertion_failures=("/data/ok is 'false'",))), uow)

    assert uow.knowledge.rows == {}


async def test_a_run_that_did_not_succeed_teaches_nothing() -> None:
    uow = FakeUnitOfWork()
    run = _run(_outcome(disposition=StepDisposition.FAILED, status_code=500), finished=True)
    assert run.status is RunStatus.FAILED

    await _learn(run, uow)

    assert uow.knowledge.rows == {}


async def test_the_url_is_recorded_without_its_parameters() -> None:
    """The path is the fact; `siteId=SG` is this run's parameter, and keying on
    it would make one endpoint look like a hundred."""
    uow = FakeUnitOfWork()

    await _learn(_run(_outcome()), uow)

    entry = next(iter(uow.knowledge.rows.values()))
    assert "?" not in entry.key
    assert entry.body["path"] == "/data/WM/wm/inventory/adjust"


def _ui_version(*, taught: LocatorStrategy = LocatorStrategy.COMPONENT) -> SkillVersion:
    return f.skill_version(
        steps=(
            f.step(
                index=0,
                network_plan=None,
                ui_plan=UiPlan(
                    action=ActionKind.CLICK,
                    target=f.fingerprint(accessible_name="Close wave"),
                    locators=(
                        ControlLocator(strategy=taught, query=Template("button#closeWave")),
                        ControlLocator(
                            strategy=LocatorStrategy.CSS_PATH, query=Template("div > button")
                        ),
                    ),
                ),
            ),
        ),
        parameters=(),
    )


async def _learn_with(run: Run, uow: FakeUnitOfWork, version: SkillVersion) -> None:
    record = RecordClaims(uow, FakeClock(), FakeIdFactory(), FakeEmbedder())
    await LearnFromRun(record).execute(CTX, run=run, system="blue_yonder", version=version)


async def test_a_control_that_has_drifted_to_its_fallback_is_written_down() -> None:
    """It works, and it is one screen change from not working.

    The driver takes the first locator that resolves, so a step whose taught
    locator has rotted keeps passing on its last-resort CSS path and looks
    exactly like a step that is fine. Which one won was on every run and read by
    nobody.
    """
    uow = FakeUnitOfWork()
    run = _run(
        _outcome(
            medium=Medium.UI,
            method=None,
            url=None,
            status_code=None,
            matched_by=LocatorStrategy.CSS_PATH.value,
        )
    )

    await _learn_with(run, uow, _ui_version())

    entry = next(e for e in uow.knowledge.rows.values() if e.kind is EntryKind.SCREEN)
    assert entry.body["drifted"] is True
    assert entry.body["taught_as"] == LocatorStrategy.COMPONENT.value
    assert entry.body["found_by"] == LocatorStrategy.CSS_PATH.value
    assert "not by the component it was taught with" in entry.title


async def test_a_control_only_a_model_could_find_is_the_loudest_of_these() -> None:
    """No locator resolved at all: the step was finished by looking at the
    screen. That is the rung of last resort doing the work of the first."""
    uow = FakeUnitOfWork()
    run = _run(
        _outcome(medium=Medium.VISION, method=None, url=None, status_code=None, matched_by="vision")
    )

    await _learn_with(run, uow, _ui_version())

    entry = next(e for e in uow.knowledge.rows.values() if e.kind is EntryKind.SCREEN)
    assert entry.body["found_by"] == "vision"
    assert entry.body["drifted"] is True


async def test_a_control_found_where_it_was_taught_is_recorded_as_that() -> None:
    uow = FakeUnitOfWork()
    run = _run(
        _outcome(
            medium=Medium.UI,
            method=None,
            url=None,
            status_code=None,
            matched_by=LocatorStrategy.COMPONENT.value,
        )
    )

    await _learn_with(run, uow, _ui_version())

    entry = next(e for e in uow.knowledge.rows.values() if e.kind is EntryKind.SCREEN)
    assert entry.body["drifted"] is False


async def test_a_run_whose_screen_check_failed_teaches_nothing_about_the_control() -> None:
    """Same rule as everywhere else here, and now it has teeth at the interface
    rung: a step that clicked something and did not produce what the
    demonstration produced makes the run fail, and a failed run proves nothing
    about the system -- including nothing about where its controls are."""
    uow = FakeUnitOfWork()
    run = _run(
        _outcome(
            medium=Medium.UI,
            method=None,
            url=None,
            status_code=None,
            matched_by=LocatorStrategy.CSS_PATH.value,
            assertion_failures=("the screen does not show 'Wave closed'",),
        )
    )
    assert run.status is RunStatus.FAILED

    await _learn_with(run, uow, _ui_version())

    assert not uow.knowledge.rows


async def test_a_step_nothing_checked_teaches_nothing_about_the_control() -> None:
    """The clean half of the same rule. A step that failed its assertions is
    refused above; this is the step that had none to fail.

    The run succeeded, because a step with nothing to check cannot fail a check
    -- and where the control was found is exactly what a step nobody verified
    must not be believed about. The gesture landed on something. That the
    something was the right control is what the assertions were for.
    """
    uow = FakeUnitOfWork()
    run = _run(
        _outcome(
            medium=Medium.UI,
            method=None,
            url=None,
            status_code=None,
            matched_by=LocatorStrategy.CSS_PATH.value,
            unchecked=("the step asserts nothing",),
        )
    )
    assert run.status is RunStatus.SUCCEEDED

    await _learn_with(run, uow, _ui_version())

    assert not [e for e in uow.knowledge.rows.values() if e.kind is EntryKind.SCREEN]


async def test_a_run_that_disagrees_with_itself_about_a_control_records_nothing() -> None:
    """Twelve times round the loop, eleven found as taught and one fell back.

    That is a race, a page that had not settled, a modal still closing -- not a
    control that moved. Counting the odd one out as evidence lets a single flaky
    iteration outvote eleven clean ones.
    """
    uow = FakeUnitOfWork()
    clicks = [
        _outcome(
            index=i,
            plan_step=0,
            iteration=i,
            medium=Medium.UI,
            method=None,
            url=None,
            status_code=None,
            matched_by=(
                LocatorStrategy.CSS_PATH.value if i == 2 else LocatorStrategy.COMPONENT.value
            ),
        )
        for i in range(12)
    ]

    await _learn_with(_run(*clicks), uow, _ui_version())

    assert not [e for e in uow.knowledge.rows.values() if e.kind is EntryKind.SCREEN]


async def test_a_loop_that_agreed_every_time_records_one_claim_about_the_control() -> None:
    """One control that moved is one observation, however many times it was
    clicked -- not twelve rows all superseding each other from one run."""
    uow = FakeUnitOfWork()
    clicks = [
        _outcome(
            index=i,
            plan_step=0,
            iteration=i,
            medium=Medium.UI,
            method=None,
            url=None,
            status_code=None,
            matched_by=LocatorStrategy.CSS_PATH.value,
        )
        for i in range(12)
    ]

    await _learn_with(_run(*clicks), uow, _ui_version())

    screens = [e for e in uow.knowledge.rows.values() if e.kind is EntryKind.SCREEN]
    assert len(screens) == 1
    assert screens[0].body["drifted"] is True
