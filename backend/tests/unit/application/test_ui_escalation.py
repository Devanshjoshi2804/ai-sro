"""L2: when the call no longer works, drive the screen instead.

The escalation is the interesting part, not the clicking. Every test here is
about *when* the browser is allowed to take over, because that decision is the
one that can change a warehouse by accident.
"""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import ExecuteSkill, ExecutionRequest
from sro.domain.execution.run import Medium, Run, RunStatus, StepDisposition
from sro.domain.recording.events import ActionKind
from sro.domain.recording.sensitivity import Sensitivity
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.locator import ControlLocator, LocatorStrategy
from sro.domain.skill.plan import HeaderPlan, UiPlan
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import SkillStep
from sro.domain.skill.template import Template
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
COOKIE_REF = "blue_yonder/SG/cookie"
SCOPED = f"{f.TENANT}/{COOKIE_REF}"

CONFIRM = UiPlan(
    action=ActionKind.CLICK,
    target=f.fingerprint(),
    locators=(
        ControlLocator(
            strategy=LocatorStrategy.COMPONENT,
            query=Template("wm-adjust-window button#finishButton"),
        ),
        ControlLocator(strategy=LocatorStrategy.TEXT, query=Template("Finish")),
    ),
)


def _step() -> SkillStep:
    return f.step(
        index=0,
        ui_plan=CONFIRM,
        network_plan=f.network_plan(
            headers=(
                HeaderPlan(
                    name="cookie", sensitivity=Sensitivity.SESSION, credential_ref=COOKIE_REF
                ),
            )
        ),
    )


async def _run(
    *,
    stage: PromotionStage,
    http: FakeHttpCaller,
    ui: FakeUiDriver,
    authorized: str | None = "supervisor",
) -> Run:
    uow, vault = FakeUnitOfWork(), FakeCredentialVault()
    await vault.store(SCOPED, "session=live")

    version = f.skill_version(steps=(_step(),))
    skill = f.skill(versions=0)
    skill.add_version(version)
    current = PromotionStage.RECORDED
    while current is not stage:
        current = current.next_stage()
        version.promote(current, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)

    executor = ExecuteSkill(uow, http, vault, FakeClock(), FakeIdFactory(), ui)
    return await executor.execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"shipment_id": "555"},
            authorized_by=authorized,
        ),
    )


async def test_a_call_the_system_no_longer_answers_is_finished_on_the_screen() -> None:
    http, ui = FakeHttpCaller(), FakeUiDriver()
    http.answer(status_code=404, text='{"message": "Not Found"}')
    ui.will_find(LocatorStrategy.COMPONENT)

    run = await _run(stage=PromotionStage.ASSISTED, http=http, ui=ui)

    step = run.steps[0]
    assert step.medium is Medium.UI
    assert step.disposition is StepDisposition.PERFORMED
    assert step.escalated_from is Medium.NETWORK
    assert step.matched_by == "component"
    assert run.status is RunStatus.SUCCEEDED
    assert ui.asked[0]["action"] is ActionKind.CLICK


async def test_a_shadow_run_never_touches_the_interface() -> None:
    """A withheld call did not happen. A click on the same screen would have."""
    http, ui = FakeHttpCaller(), FakeUiDriver()
    http.answer(status_code=404, text="{}")

    run = await _run(stage=PromotionStage.SHADOW, http=http, ui=ui, authorized=None)

    assert ui.asked == []
    assert run.steps[0].medium is Medium.NETWORK
    assert run.steps[0].disposition is StepDisposition.WITHHELD, (
        "the write never went out, so there was no failure to escalate from"
    )


async def test_a_missing_session_is_not_escalated_to_a_browser() -> None:
    """The policy refuses this one: a browser cannot invent a session either."""
    uow, vault = FakeUnitOfWork(), FakeCredentialVault()
    http, ui = FakeHttpCaller(), FakeUiDriver()
    version = f.skill_version(steps=(_step(),))
    skill = f.skill(versions=0)
    skill.add_version(version)
    for stage in (PromotionStage.SHADOW, PromotionStage.ASSISTED):
        version.promote(stage, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)

    run = await ExecuteSkill(uow, http, vault, FakeClock(), FakeIdFactory(), ui).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"shipment_id": "555"},
            authorized_by="supervisor",
        ),
    )

    assert ui.asked == [], "the vault is empty; a browser would fail the same way"
    assert run.steps[0].disposition is StepDisposition.FAILED


async def test_a_control_that_cannot_be_found_says_so_and_stops() -> None:
    http, ui = FakeHttpCaller(), FakeUiDriver()
    http.answer(status_code=404, text="{}")
    ui.will_not_find()

    run = await _run(stage=PromotionStage.ASSISTED, http=http, ui=ui)

    step = run.steps[0]
    assert step.disposition is StepDisposition.PERFORMED  # the call was made; it answered 404
    assert step.escalated_from is Medium.NETWORK
    assert "no control matched" in (step.detail or "")
    assert run.status is RunStatus.FAILED


async def test_no_browser_configured_is_recorded_rather_than_hidden() -> None:
    http, ui = FakeHttpCaller(), FakeUiDriver(available=False)
    http.answer(status_code=404, text="{}")

    run = await _run(stage=PromotionStage.ASSISTED, http=http, ui=ui)

    assert "no browser" in (run.steps[0].detail or "")
    assert run.status is RunStatus.FAILED


async def test_a_task_run_in_the_browser_is_driven_step_by_step() -> None:
    """The whole task at L2, chosen when the run is requested."""
    uow, vault = FakeUnitOfWork(), FakeCredentialVault()
    http, ui = FakeHttpCaller(), FakeUiDriver()
    ui.will_find(LocatorStrategy.COMPONENT)

    version = f.skill_version(steps=(_step(),))
    skill = f.skill(versions=0)
    skill.add_version(version)
    for stage in (PromotionStage.SHADOW, PromotionStage.ASSISTED):
        version.promote(stage, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)

    run = await ExecuteSkill(uow, http, vault, FakeClock(), FakeIdFactory(), ui).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"shipment_id": "555"},
            authorized_by="supervisor",
            medium=Medium.UI,
        ),
    )

    assert http.sent == [], "a UI run does not also replay the calls"
    assert run.steps[0].medium is Medium.UI
    assert run.steps[0].disposition is StepDisposition.PERFORMED
    assert run.status is RunStatus.SUCCEEDED


async def test_a_shadow_run_in_the_browser_withholds_the_gesture() -> None:
    """A click is indistinguishable from a call once it has happened."""
    uow, vault = FakeUnitOfWork(), FakeCredentialVault()
    http, ui = FakeHttpCaller(), FakeUiDriver()

    version = f.skill_version(steps=(_step(),))
    skill = f.skill(versions=0)
    skill.add_version(version)
    version.promote(PromotionStage.SHADOW, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)

    run = await ExecuteSkill(uow, http, vault, FakeClock(), FakeIdFactory(), ui).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"), parameters={"shipment_id": "555"}, medium=Medium.UI
        ),
    )

    assert ui.asked == []
    assert run.steps[0].disposition is StepDisposition.WITHHELD
    assert "wm-adjust-window button#finishButton" in (run.steps[0].detail or "")


async def test_a_control_that_has_vanished_escalates_to_vision() -> None:
    """L2 knew where the control was; L3 is asked what is on the screen instead."""
    from sro.application.execution.vision_step import PerformWithVision
    from sro.application.ports.vision import ProposedGesture
    from sro.domain.recording.events import ActionKind as Kind
    from tests.unit.fakes import FakeVisionDriver

    uow, vault = FakeUnitOfWork(), FakeCredentialVault()
    await vault.store(SCOPED, "session=live")
    http, ui = FakeHttpCaller(), FakeUiDriver()
    http.answer(status_code=404, text="{}")
    ui.will_not_find()

    model = FakeVisionDriver(
        ProposedGesture(action=Kind.CLICK, x=120, y=340, reasoning="the button moved")
    )
    vision = PerformWithVision(ui, model, FakeClock(), egress_enabled=True, model="fake-vision")

    version = f.skill_version(steps=(_step(),))
    skill = f.skill(versions=0)
    skill.add_version(version)
    for stage in (PromotionStage.SHADOW, PromotionStage.ASSISTED):
        version.promote(stage, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)

    run = await ExecuteSkill(
        uow, http, vault, FakeClock(), FakeIdFactory(), ui, None, vision
    ).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"shipment_id": "555"},
            authorized_by="supervisor",
        ),
    )

    step = run.steps[0]
    assert step.medium is Medium.VISION
    assert step.disposition is StepDisposition.PERFORMED
    assert step.matched_by == "vision"
    assert uow.model_calls.calls, "what was sent to the model is part of the run's record"
    assert uow.model_calls.calls[0].run_id == run.id


async def test_vision_is_not_reached_when_the_deployment_has_no_rung_for_it() -> None:
    http, ui = FakeHttpCaller(), FakeUiDriver()
    http.answer(status_code=404, text="{}")
    ui.will_not_find()

    run = await _run(stage=PromotionStage.ASSISTED, http=http, ui=ui)

    assert run.steps[0].medium is Medium.NETWORK
    assert "no control matched" in (run.steps[0].detail or "")


async def test_vision_looks_at_the_browser_the_run_is_being_performed_in() -> None:
    """A run bound to a device is performed in somebody's own Chrome.

    Escalating held the deployment's driver, so the rung that looks photographed
    a different browser -- signed in as somebody else, on a page nobody
    demonstrated -- and clicked on what it saw there. `_ui_for` documents the
    rule that a device-bound run never falls back to the deployment's browser;
    this is the path that ignored it.
    """
    from sro.application.execution.vision_step import PerformWithVision
    from sro.application.ports.vision import ProposedGesture
    from sro.domain.recording.events import ActionKind as Kind
    from sro.domain.shared.identifiers import DeviceId
    from tests.unit.fakes import FakeAgentDrivers, FakeVisionDriver

    uow, vault = FakeUnitOfWork(), FakeCredentialVault()
    await vault.store(SCOPED, "session=live")
    http = FakeHttpCaller()
    http.answer(status_code=404, text="{}")

    ours, theirs = FakeUiDriver(), FakeUiDriver()
    ours.will_not_find()
    theirs.will_not_find()
    # A run bound to a device sends its calls from that browser too, so the
    # failure that starts the climb has to be queued there.
    their_calls = FakeHttpCaller()
    their_calls.answer(status_code=404, text="{}")
    agents = FakeAgentDrivers(ui=theirs, http=their_calls)

    model = FakeVisionDriver(
        ProposedGesture(action=Kind.CLICK, x=120, y=340, reasoning="the button moved")
    )
    vision = PerformWithVision(ours, model, FakeClock(), egress_enabled=True, model="fake-vision")

    version = f.skill_version(steps=(_step(),))
    skill = f.skill(versions=0)
    skill.add_version(version)
    for stage in (PromotionStage.SHADOW, PromotionStage.ASSISTED):
        version.promote(stage, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)

    await ExecuteSkill(
        uow, http, vault, FakeClock(), FakeIdFactory(), ours, None, vision, agents=agents
    ).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"shipment_id": "555"},
            authorized_by="supervisor",
            # The network rung, which is what escalates: a run asked for as
            # `ui` performs there and stops, and only L1 climbs the ladder.
            device_id=DeviceId("dev-1"),
        ),
    )

    assert theirs.captures, "vision never looked at the browser the run was performed in"
    assert ours.captures == 0, (
        "vision photographed the deployment's own browser for a run bound to a device"
    )
