"""What verifies a step performed in the interface.

At L1 the demonstration's post-conditions are checked against what the system
answered. At L2 and L3 they were checked against nothing at all: the driver said
"performed" when it found a control and clicked it, and that was the whole of
the verification. A click on the wrong Save, or the right Save on a form the
application refused, was a step that succeeded -- and a succeeding step earns a
version its way up the promotion ladder.

`docs/12` calls verification the control that stands between a model and a live
system, and `vision_step.py` says in as many words that a model may claim a step
is done and the demonstration's assertions are what decide. Nothing decided.
The evidence was there the whole time: `UI_TEXT_VISIBLE` assertions, extracted
at induction from the text that appeared on screen in both demonstrations.
"""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import ExecuteStep, ExecutionRequest, StartRun
from sro.application.ports.ui import UiUnavailable
from sro.application.ports.vision import Screen
from sro.domain.execution.run import Medium, StepDisposition
from sro.domain.recording.events import ActionKind
from sro.domain.skill.assertion import Assertion, AssertionKind
from sro.domain.skill.locator import ControlLocator, LocatorStrategy
from sro.domain.skill.plan import Template, UiPlan
from sro.domain.skill.promotion import PromotionStage
from tests import factories as f
from tests.unit.fakes import (
    FakeClock,
    FakeCredentialVault,
    FakeHttpCaller,
    FakeIdFactory,
    FakeUiDriver,
    FakeUnitOfWork,
)

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)


async def _skill(
    uow: FakeUnitOfWork, *, asserts: tuple[Assertion, ...], network: bool = False
) -> None:
    """One step, demonstrated as a click that made a confirmation appear."""
    version = f.skill_version(
        steps=(
            f.step(
                index=0,
                network_plan=(
                    f.network_plan(url=Template("https://wms.test/api/waves/close"), body=None)
                    if network
                    else None
                ),
                ui_plan=UiPlan(
                    action=ActionKind.CLICK,
                    target=f.fingerprint(accessible_name="Close wave"),
                    locators=(
                        ControlLocator(
                            strategy=LocatorStrategy.ROLE_AND_NAME,
                            query=Template("button|Close wave"),
                        ),
                    ),
                ),
                assertions=asserts,
            ),
        ),
        parameters=(),
    )
    skill = f.skill(versions=0)
    skill.add_version(version)
    for stage in (PromotionStage.SHADOW, PromotionStage.ASSISTED):
        version.promote(stage, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)


async def _run(uow: FakeUnitOfWork, ui: FakeUiDriver) -> StepDisposition:
    run = await StartRun(uow, FakeClock(), FakeIdFactory()).execute(
        CTX,
        ExecutionRequest(
            skill_id=f.skill().id, parameters={}, authorized_by="supervisor", medium=Medium.UI
        ),
    )
    step = ExecuteStep(uow, FakeHttpCaller(), FakeCredentialVault(), ui)
    return await step.execute(CTX, run_id=run.id, index=0)  # type: ignore[return-value]


async def test_a_click_that_did_not_change_the_screen_is_not_a_step_that_worked() -> None:
    uow = FakeUnitOfWork()
    await _skill(
        uow,
        asserts=(Assertion(kind=AssertionKind.UI_TEXT_VISIBLE, expected=Template("Wave closed")),),
    )
    # The control was found and clicked. The confirmation the demonstration
    # produced twice is not on the screen afterwards.
    ui = FakeUiDriver(digest="Close wave: 100,200")

    outcome = await _run(uow, ui)

    assert outcome.disposition is StepDisposition.PERFORMED, "the gesture did land"
    assert outcome.assertion_failures == ("the screen does not show 'Wave closed'",)
    assert not outcome.ok, "a run of this must not count as clean"


async def test_a_click_the_screen_confirms_passes() -> None:
    uow = FakeUnitOfWork()
    await _skill(
        uow,
        asserts=(Assertion(kind=AssertionKind.UI_TEXT_VISIBLE, expected=Template("Wave closed")),),
    )
    ui = FakeUiDriver(digest="Wave closed: 40,80")

    outcome = await _run(uow, ui)

    assert outcome.assertion_failures == ()
    assert outcome.ok


async def test_a_step_with_nothing_visible_to_check_costs_no_photograph() -> None:
    """A step whose evidence is a response body proves nothing on screen, and
    photographing somebody's browser for nothing is a cost and an intrusion."""
    uow = FakeUnitOfWork()
    await _skill(
        uow,
        asserts=(Assertion(kind=AssertionKind.HTTP_STATUS, expected=Template("200")),),
    )
    ui = FakeUiDriver()

    outcome = await _run(uow, ui)

    assert ui.captures == 0
    assert outcome.ok


async def test_what_this_rung_cannot_check_is_said_rather_than_assumed() -> None:
    """A response body is not visible from a browser. Counting it as satisfied
    is how a run in the interface convinces itself it produced a result nobody
    saw -- the same reasoning the network rung already applies in reverse."""
    uow = FakeUnitOfWork()
    await _skill(
        uow,
        asserts=(
            Assertion(kind=AssertionKind.UI_TEXT_VISIBLE, expected=Template("Wave closed")),
            Assertion(kind=AssertionKind.HTTP_STATUS, expected=Template("200")),
        ),
    )
    ui = FakeUiDriver(digest="Wave closed")

    outcome = await _run(uow, ui)

    assert outcome.ok, "an unreadable post-condition is not a failed task"
    assert "not checkable from the interface: http_status" in (outcome.detail or "")


async def test_a_screen_that_cannot_be_read_does_not_fail_the_step() -> None:
    """The gesture landed. Calling the task wrong because a capture failed would
    be inventing a failure, which is the opposite of what verification is for --
    and it is said in the step's own words so nobody reads it as verified."""
    uow = FakeUnitOfWork()
    await _skill(
        uow,
        asserts=(Assertion(kind=AssertionKind.UI_TEXT_VISIBLE, expected=Template("Wave closed")),),
    )

    class _Blind(FakeUiDriver):
        async def capture(self) -> Screen:
            raise UiUnavailable("the tab was closed")

    outcome = await _run(uow, _Blind())

    assert outcome.disposition is StepDisposition.PERFORMED
    assert outcome.assertion_failures == ()
    assert "could not be read" in (outcome.detail or "")


async def test_what_a_model_clicked_is_checked_against_the_screen_too() -> None:
    """The rung whose own docstring promised this.

    L3 is a model looking at a screenshot and choosing a coordinate. It may say
    a step is done -- and `vision_step.py` says the demonstration's assertions
    are what decide. Nothing decided, so the least predictable rung in the
    system was also the only one whose success nobody checked.
    """
    from sro.application.execution.vision_step import PerformWithVision
    from sro.application.ports.vision import ProposedGesture
    from tests.unit.fakes import FakeVisionDriver

    uow = FakeUnitOfWork()
    await _skill(
        uow,
        asserts=(Assertion(kind=AssertionKind.UI_TEXT_VISIBLE, expected=Template("Wave closed")),),
        network=True,
    )
    http = FakeHttpCaller()
    http.answer(status_code=404, text="{}")
    # The recorded control is gone, so L2 cannot act and L3 is asked to look.
    ui = FakeUiDriver(digest="Close wave: 100,200")
    ui.will_not_find()
    model = FakeVisionDriver(
        ProposedGesture(action=ActionKind.CLICK, x=120, y=340, reasoning="the button moved")
    )
    vision = PerformWithVision(ui, model, FakeClock(), egress_enabled=True, model="fake-vision")

    run = await StartRun(uow, FakeClock(), FakeIdFactory()).execute(
        CTX,
        ExecutionRequest(skill_id=f.skill().id, parameters={}, authorized_by="supervisor"),
    )
    step = ExecuteStep(uow, http, FakeCredentialVault(), ui, vision)
    outcome = await step.execute(CTX, run_id=run.id, index=0)

    assert outcome.medium is Medium.VISION
    assert outcome.disposition is StepDisposition.PERFORMED, "the model did click something"
    # And it clicked something that did not close the wave.
    assert outcome.assertion_failures == ("the screen does not show 'Wave closed'",)
    assert not outcome.ok
