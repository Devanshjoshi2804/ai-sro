"""A control moved, several verified runs found it anyway, and the skill adopts it.

Escalation already carried each run: the UI rung found the button by a locator
the demonstration did not lead with, and the task got done. What did not happen
is the skill changing -- so every later run re-discovered the same drift, paid
the same escalation, and could never be `CLEAN` again. A skill that heals by
escalating works forever and can never again run unattended.

What decides is the store, not the run that triggers the look. One escalation is
a slow page, a race, a modal that was still closing; `SETTLED` verified runs
agreeing is a control that moved. The store was already built for exactly this
-- evidence accumulates there and outranks arrival order -- and reading it is
what keeps one bad afternoon from rewriting a skill.
"""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import ExecuteSkill, ExecutionRequest
from sro.application.knowledge.learn_from_run import LearnFromRun
from sro.application.knowledge.open_questions import AskAbout
from sro.application.knowledge.record_claim import RecordClaims
from sro.application.skill.repair_drift import REPAIR, SETTLED, RepairDrift
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
from sro.domain.shared.errors import Conflict
from sro.domain.skill.assertion import Assertion, AssertionKind
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
SYSTEM = f.objective().target_system

TAUGHT = ControlLocator(strategy=LocatorStrategy.COMPONENT, query=Template("button#closeWave"))
FALLBACK = ControlLocator(strategy=LocatorStrategy.CSS_PATH, query=Template("div > button"))


def _version(
    *, number: int = 1, locators: tuple[ControlLocator, ...] = (TAUGHT, FALLBACK)
) -> SkillVersion:
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
                    locators=locators,
                ),
                assertions=(
                    Assertion(kind=AssertionKind.UI_TEXT_VISIBLE, expected=Template("Wave closed")),
                ),
            ),
        ),
    )


def _skill(version: SkillVersion, stage: PromotionStage = PromotionStage.ASSISTED) -> Skill:
    skill = f.skill(versions=0)
    skill.add_version(version)
    version.stage = stage
    version.track_record = TrackRecord(clean_streak=7, clean_runs=7)
    return skill


def _run(*outcomes: StepOutcome, version: int = 1, run_id: str = "run-1") -> Run:
    run = Run(
        id=RunId(run_id),
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


def _run_at(stage: PromotionStage) -> Run:
    """A run of the repaired version, only to ask whether its rung sends."""
    return Run(
        id=RunId("run-2"),
        tenant_id=f.TENANT,
        skill_id=f.skill().id,
        skill_version=2,
        stage=stage,
        parameters={},
        requested_by=f.OPERATOR,
        started_at=f.at(0),
        authorized_by=f.OPERATOR,
    )


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


class _Witnessed:
    """A store, and the runs whose evidence has been written into it.

    The claims are written by `LearnFromRun` rather than assembled here: what a
    repair reads is what the learner writes, and a test that spelled the rows
    out itself would go on passing after the two stopped agreeing.
    """

    def __init__(self, skill: Skill) -> None:
        self.uow = FakeUnitOfWork()
        self.skill = skill
        self.clock = FakeClock()
        # One id factory for the life of the store: a fresh one per run would
        # hand out `kb-1` again and each run would overwrite the last.
        self.ids = FakeIdFactory()
        self.learn = LearnFromRun(RecordClaims(self.uow, self.clock, self.ids, FakeEmbedder()))
        self.ask = AskAbout(self.uow, RecordClaims(self.uow, self.clock, self.ids, FakeEmbedder()))
        self.runs = 0

    async def ready(self) -> _Witnessed:
        await self.uow.skills.add(self.skill)
        return self

    async def saw(self, *outcomes: StepOutcome, version: int = 1) -> Run:
        """One more verified run, taught to the store the way every run is."""
        self.runs += 1
        run = _run(*outcomes, version=version, run_id=f"run-{self.runs}")
        await self.learn.execute(CTX, run=run, system=SYSTEM, version=self.skill.version(version))
        return run

    async def repair(self, run: Run) -> int | None:
        return await RepairDrift(self.uow, self.clock, self.ask).execute(CTX, run=run)

    async def after(self, runs: int, *outcomes: StepOutcome, version: int = 1) -> int | None:
        """`runs` runs that all saw the same thing, then the repair they earn."""
        for _ in range(runs):
            run = await self.saw(*outcomes, version=version)
        return await self.repair(run)


async def _settled(skill: Skill, *outcomes: StepOutcome, runs: int = SETTLED) -> _Witnessed:
    """A skill whose store already holds `runs` runs agreeing about the click."""
    store = await _Witnessed(skill).ready()
    await store.after(runs, *(outcomes or (_call(), _click())))
    return store


async def test_a_locator_the_store_has_settled_on_becomes_a_new_version() -> None:
    version = _version()
    skill = _skill(version)
    store = await _Witnessed(skill).ready()

    number = await store.after(SETTLED, _call(), _click())

    assert number == 2
    plan = skill.version(2).steps[1].ui_plan
    assert plan is not None
    assert plan.locators[0] is FALLBACK, "the plan now names the locator that worked"
    assert plan.locators[1] is TAUGHT, (
        "and keeps the one it was taught with behind it: a screen that changes "
        "back is not a screen this skill should be taught twice"
    )


async def test_one_run_that_escalated_is_not_a_reason_to_rewrite_a_skill() -> None:
    """The whole correction, in one test.

    A single escalation is a page that had not settled, a modal still closing, a
    race between a render and a click. Rewriting the skill on it means a bad
    afternoon rewrites the skill -- and every count in this system has said
    three since the day it started counting.
    """
    skill = _skill(_version())
    store = await _Witnessed(skill).ready()

    assert await store.after(1, _call(), _click()) is None, "once is noise"
    assert await store.after(1, _call(), _click()) is None, "twice is a coincidence"
    assert await store.after(1, _call(), _click()) == 2, "three times is a control that moved"


async def test_a_flaky_iteration_cannot_outvote_eleven_clean_ones() -> None:
    """Twelve times round the loop, eleven found as taught and one fell back --
    three runs in a row. The odd one out is a race every time, and a rule that
    reads one outcome would have adopted the fallback three times over."""
    skill = _skill(_version())
    store = await _Witnessed(skill).ready()
    clicks = [
        _click(
            index=i + 1,
            plan_step=1,
            iteration=i,
            matched_by=(
                LocatorStrategy.CSS_PATH.value if i == 2 else LocatorStrategy.COMPONENT.value
            ),
        )
        for i in range(12)
    ]

    number = await store.after(SETTLED, _call(), *clicks)

    assert number is None
    assert len(skill.versions) == 1


async def test_a_step_nothing_checked_never_settles_anything() -> None:
    """A skill that asserts nothing repaired itself: nothing failed because
    nothing looked, the run came out SUCCEEDED, and the fallback that a `div >
    button` happened to resolve went to the front of the plan.

    Three such runs are three times as much of nothing.
    """
    skill = _skill(_version())
    store = await _Witnessed(skill).ready()

    number = await store.after(SETTLED, _call(), _click(unchecked=("the step asserts nothing",)))

    assert number is None
    assert len(skill.versions) == 1


async def test_a_strategy_this_step_carries_twice_is_a_question_not_a_guess() -> None:
    """The evidence names a strategy; the plan holds two locators of it.

    Which one the driver used is exactly what nobody recorded, and promoting the
    first of them puts a destructive control ahead of the one that worked. So it
    is asked rather than guessed at.
    """
    danger = ControlLocator(
        strategy=LocatorStrategy.CSS_PATH, query=Template("#panelA > button.danger")
    )
    close = ControlLocator(
        strategy=LocatorStrategy.CSS_PATH, query=Template("#panelB > button.close")
    )
    skill = _skill(_version(locators=(TAUGHT, danger, close)))
    store = await _Witnessed(skill).ready()

    number = await store.after(SETTLED, _call(), _click())

    assert number is None, "no version, and in particular not one leading with the danger"
    assert len(skill.versions) == 1
    question = next(e for e in store.uow.knowledge.rows.values() if e.kind is EntryKind.QUESTION)
    assert "does not say which control that is" in str(question.body["question"])


async def test_a_control_only_a_model_could_find_becomes_a_question() -> None:
    """At the UI rung the application's own structure found the control. At the
    vision rung a model read pixels and chose, and letting that write the skill
    is a model marking its own homework."""
    skill = _skill(_version())
    store = await _Witnessed(skill).ready()

    number = await store.after(SETTLED, _call(), _click(medium=Medium.VISION, matched_by="vision"))

    assert number is None, "no version"
    assert len(skill.versions) == 1
    question = next(e for e in store.uow.knowledge.rows.values() if e.kind is EntryKind.QUESTION)
    assert "vision" in str(question.body["question"])
    assert "run-3" in str(question.body["because"])


async def test_every_other_step_comes_out_byte_identical() -> None:
    """A repair is the old version with one plan replaced, never a re-induction."""
    version = _version()
    skill = _skill(version)

    await _settled(skill)

    assert skill.version(2).steps[0] is version.steps[0]
    assert skill.version(2).parameters == version.parameters
    assert skill.version(2).steps[1].intent == version.steps[1].intent
    assert skill.version(2).steps[1].assertions == version.steps[1].assertions
    assert skill.version(2).steps[1].when == version.steps[1].when
    old = version.steps[1].ui_plan
    new = skill.version(2).steps[1].ui_plan
    assert old is not None and new is not None
    assert (new.action, new.target, new.value) == (old.action, old.target, old.value)


async def test_the_version_it_repaired_is_left_exactly_where_it_was() -> None:
    """Nothing is edited in place, so a repair that was wrong is undone by
    promoting the older version again."""
    version = _version()
    skill = _skill(version)

    await _settled(skill)

    plan = version.steps[1].ui_plan
    assert plan is not None
    assert plan.locators == (TAUGHT, FALLBACK)
    assert version.stage is PromotionStage.ASSISTED


async def test_a_repair_keeps_doing_the_work_it_was_already_trusted_with() -> None:
    """`Skill.runnable` serves the repaired version immediately, so dropping it
    a rung would stop the operator's Tuesday task from creating anything."""
    skill = _skill(_version())

    await _settled(skill)

    fresh = skill.version(2)
    assert fresh is skill.runnable, "it is what the next run is offered"
    assert fresh.stage is PromotionStage.ASSISTED, (
        "the rung it was already trusted at: a human still presses, and what "
        "they press on differs by one locator several verified runs proved"
    )
    assert _run_at(fresh.stage).performs_writes, "so the work still happens"
    assert fresh.promoted_by is not None, "and the rung names who gave it"


async def test_the_repaired_version_starts_with_no_record() -> None:
    """Three agreeing runs are not ten clean ones, and unattended is exactly
    where a bad repair would go unnoticed."""
    skill = _skill(_version())

    await _settled(skill)

    assert skill.version(2).track_record == TrackRecord(), "none of the old one's streak"


async def test_a_repair_of_an_unattended_version_asks_for_a_human_again() -> None:
    """The one rung a repair may not inherit. Nobody has watched this version
    run, and unattended is where that would go unnoticed -- so it re-earns the
    right to act unwatched from the empty record, ten clean runs away."""
    skill = _skill(_version(), stage=PromotionStage.AUTONOMOUS)

    await _settled(skill)

    fresh = skill.version(2)
    assert fresh.stage is PromotionStage.ASSISTED
    assert fresh is skill.runnable
    assert _run_at(fresh.stage).performs_writes, "the work continues; somebody watches it"


async def test_a_repair_of_a_rehearsing_version_goes_on_rehearsing() -> None:
    """Inheriting the stage cuts both ways: nothing is sent at SHADOW, and a
    repair is not a reason to start sending."""
    skill = _skill(_version(), stage=PromotionStage.SHADOW)

    await _settled(skill)

    fresh = skill.version(2)
    assert fresh.stage is PromotionStage.SHADOW
    assert fresh is skill.runnable
    assert not _run_at(fresh.stage).performs_writes


async def test_the_new_version_says_the_system_wrote_it_and_which_run_closed_it() -> None:
    """A skill that quietly rewrites itself is one nobody can trust -- and a
    version whose author reads as the operator who happened to press the last
    run is exactly that, with a name on it to make it look reviewed."""
    skill = _skill(_version())

    await _settled(skill)

    provenance = skill.version(2).provenance
    assert provenance.repaired_from == "run-3", "in a field, not only in the prose"
    assert provenance.induced_by == REPAIR, "nobody induced this"
    assert provenance.recording_ids == skill.version(1).provenance.recording_ids, (
        "the demonstrations every value it sends still came from"
    )
    assert "run-3" in provenance.note and "3 verified runs" in provenance.note


async def test_a_repair_that_lost_the_race_is_dropped_rather_than_forced() -> None:
    """Two runs finishing together, or a demonstration landing mid-decision.

    Whoever committed first wrote a version this one never saw, and writing over
    it would lose a repair with a green log to show for it. The store still says
    the control drifted, so the next run adopts it.
    """
    skill = _skill(_version())
    store = await _Witnessed(skill).ready()
    for _ in range(SETTLED):
        run = await store.saw(_call(), _click())
    store.uow.commit_raises = Conflict("skill-1 was written by somebody else")

    assert await store.repair(run) is None


async def test_a_run_that_failed_its_assertions_repairs_nothing() -> None:
    """It proves the skill and the system disagree, not which one is wrong.

    The click itself was clean and did drift. The run around it was not: an
    earlier step did not produce what the demonstration produced, so this run
    establishes nothing about where the system's controls are now -- and is not
    even a reason to go and look at what the store says.
    """
    skill = _skill(_version())
    store = await _Witnessed(skill).ready()
    for _ in range(SETTLED):
        await store.saw(_call(), _click())
    broken = _run(
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
        run_id="run-9",
    )
    assert broken.status is RunStatus.FAILED

    assert await store.repair(broken) is None
    assert len(skill.versions) == 1


async def test_a_control_found_where_it_was_taught_repairs_nothing() -> None:
    skill = _skill(_version())
    store = await _Witnessed(skill).ready()

    number = await store.after(SETTLED, _call(), _click(matched_by=LocatorStrategy.COMPONENT.value))

    assert number is None
    assert len(skill.versions) == 1


async def test_a_repair_of_a_version_somebody_has_since_replaced_is_refused() -> None:
    """A later demonstration is later evidence than any of these runs, and a
    repair of the older version would be appended in front of it."""
    skill = _skill(_version())
    store = await _Witnessed(skill).ready()
    for _ in range(SETTLED):
        run = await store.saw(_call(), _click())
    skill.add_version(_version(number=2))

    assert await store.repair(run) is None
    assert len(skill.versions) == 2


async def test_a_settled_drift_is_adopted_once_not_once_per_run() -> None:
    """Thirteen versions from twelve alternating runs was the shape of this bug.

    The repair is self-limiting because the evidence is: the new version leads
    with the locator that worked, so what later runs write down is a control
    found where it was taught.
    """
    skill = _skill(_version())
    store = await _Witnessed(skill).ready()
    await store.after(SETTLED, _call(), _click())
    assert len(skill.versions) == 2

    for _ in range(SETTLED * 2):
        run = await store.saw(_call(), _click(), version=2)
        assert await store.repair(run) is None

    assert len(skill.versions) == 2


async def test_three_real_runs_that_escalated_leave_a_repaired_version_behind() -> None:
    """The seam, end to end: the call 404s, the browser finishes the step by a
    locator the demonstration did not lead with, the screen confirms it, and the
    third run's evidence closes the case.

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
                assertions=(
                    Assertion(kind=AssertionKind.UI_TEXT_VISIBLE, expected=Template("Finish")),
                ),
            ),
        )
    )
    skill = f.skill(versions=0)
    skill.add_version(version)
    for stage in (PromotionStage.SHADOW, PromotionStage.ASSISTED):
        version.promote(stage, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)

    clock, ids = FakeClock(), FakeIdFactory()
    http, ui = FakeHttpCaller(), FakeUiDriver()
    record = RecordClaims(uow, clock, ids, FakeEmbedder())
    execute = ExecuteSkill(
        uow,
        http,
        FakeCredentialVault(),
        clock,
        ids,
        ui,
        learn=LearnFromRun(record),
        repair=RepairDrift(uow, clock, AskAbout(uow, record)),
    )

    for _ in range(SETTLED):
        http.answer(status_code=404, text='{"message": "Not Found"}')
        ui.will_find(LocatorStrategy.TEXT)
        run = await execute.execute(
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
