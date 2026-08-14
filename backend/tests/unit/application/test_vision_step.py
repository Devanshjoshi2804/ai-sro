"""L3: the model proposes, the driver acts, and everything is bounded.

This is the least predictable thing in the system pointed at a live warehouse,
so most of these tests are about what it is *not* allowed to do.
"""

from __future__ import annotations

from sro.application.execution.vision_step import GESTURE_BUDGET, PerformWithVision
from sro.application.ports.ui import UiOutcome
from sro.application.ports.vision import ProposedGesture
from sro.domain.execution.run import Medium, Run, RunId, StepDisposition
from sro.domain.recording.events import ActionKind
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.promotion import PromotionStage
from tests import factories as f
from tests.unit.fakes import FakeClock, FakeUiDriver, FakeVisionDriver

CLICK_FINISH = ProposedGesture(
    action=ActionKind.CLICK, x=500, y=400, reasoning="the Finish button is here"
)


def _run(stage: PromotionStage = PromotionStage.ASSISTED) -> Run:
    return Run(
        id=RunId("run-1"),
        tenant_id=f.TENANT,
        skill_id=SkillId("skill-1"),
        skill_version=1,
        stage=stage,
        parameters={},
        requested_by=f.OPERATOR,
        started_at=f.at(0),
        authorized_by=f.OPERATOR if stage.rung > PromotionStage.SHADOW.rung else None,
        medium=Medium.VISION,
    )


def _vision(ui: FakeUiDriver, model: FakeVisionDriver, *, egress: bool = True) -> PerformWithVision:
    return PerformWithVision(ui, model, FakeClock(), egress_enabled=egress, model="fake-vision")


async def test_a_proposed_gesture_is_performed_by_the_driver_not_the_model() -> None:
    ui, model = FakeUiDriver(), FakeVisionDriver(CLICK_FINISH)

    result = await _vision(ui, model).execute(_run(), f.step())

    assert result.outcome.disposition is StepDisposition.PERFORMED
    assert result.outcome.medium is Medium.VISION
    assert result.outcome.escalated_from is Medium.UI
    assert ui.asked[0]["at"] == (500, 400), "the driver clicked; the model only said where"


async def test_every_call_is_recorded_whether_or_not_it_helped() -> None:
    ui, model = FakeUiDriver(), FakeVisionDriver(CLICK_FINISH)

    result = await _vision(ui, model).execute(_run(), f.step())

    call = result.calls[0]
    assert call.purpose == "propose_gesture"
    assert call.image_sent and call.sent_bytes > 0
    assert "click" in call.outcome


async def test_a_shadow_run_never_reaches_for_the_model() -> None:
    """A click cannot be withheld once it has been made."""
    ui, model = FakeUiDriver(), FakeVisionDriver(CLICK_FINISH)

    result = await _vision(ui, model).execute(_run(PromotionStage.SHADOW), f.step())

    assert result.calls == () and model.asked == []
    assert result.outcome.disposition is StepDisposition.FAILED
    assert "does not drive the interface" in (result.outcome.detail or "")


async def test_a_screen_showing_a_credential_field_is_never_sent() -> None:
    ui = FakeUiDriver(digest="Password: 10,20\nSign in: 10,60")
    model = FakeVisionDriver(CLICK_FINISH)

    result = await _vision(ui, model).execute(_run(), f.step())

    assert model.asked == [], "nothing left the deployment"
    assert result.calls[0].failed and not result.calls[0].image_sent
    assert "credential" in (result.outcome.detail or "")


async def test_egress_switched_off_fails_with_the_reason_rather_than_silently() -> None:
    ui, model = FakeUiDriver(), FakeVisionDriver(CLICK_FINISH)

    result = await _vision(ui, model, egress=False).execute(_run(), f.step())

    assert model.asked == []
    assert "egress is switched off" in (result.outcome.detail or "")
    assert result.calls[0].failed


async def test_a_secret_field_is_stripped_from_what_is_sent() -> None:
    ui = FakeUiDriver(digest="LPN: 10,20\napi_key: 10,40\nFinish: 10,60")
    model = FakeVisionDriver(CLICK_FINISH)

    result = await _vision(ui, model).execute(_run(), f.step())

    sent = model.asked[0]["screen"]
    assert "api_key" not in sent.text_digest  # type: ignore[union-attr]
    assert "api_key" in result.calls[0].redacted_fields


async def test_the_model_cannot_propose_an_action_the_step_never_used() -> None:
    """Allowed actions are the step's own gesture plus what it takes to reach a
    control. A demonstrated click cannot become a navigation."""
    ui, model = FakeUiDriver(), FakeVisionDriver(CLICK_FINISH)

    await _vision(ui, model).execute(_run(), f.step())

    allowed = model.asked[0]["allowed"]
    assert ActionKind.NAVIGATE not in allowed  # type: ignore[operator]
    assert ActionKind.CLICK in allowed  # type: ignore[operator]


async def test_a_refusal_stops_the_step_and_says_why() -> None:
    ui = FakeUiDriver()
    model = FakeVisionDriver(
        ProposedGesture(action=ActionKind.HOVER, refusal="I cannot see the Finish button")
    )

    result = await _vision(ui, model).execute(_run(), f.step())

    assert result.outcome.disposition is StepDisposition.FAILED
    assert "cannot see the Finish button" in (result.outcome.detail or "")
    assert ui.asked == [], "a refusal is an outcome, not an excuse to act anyway"


async def test_the_model_saying_it_is_done_is_a_claim_not_a_verification() -> None:
    ui = FakeUiDriver()
    model = FakeVisionDriver(
        ProposedGesture(action=ActionKind.HOVER, done=True, reasoning="the count already shows 48")
    )

    result = await _vision(ui, model).execute(_run(), f.step())

    assert result.outcome.disposition is StepDisposition.PERFORMED
    assert "believes" in (result.outcome.detail or ""), (
        "recorded as what the model thinks; the step's assertions are what decide"
    )


async def test_the_loop_is_bounded_rather_than_hopeful() -> None:
    ui = FakeUiDriver()
    for _ in range(GESTURE_BUDGET + 2):
        ui.will_not_find()
    model = FakeVisionDriver(*[CLICK_FINISH] * (GESTURE_BUDGET + 2))

    result = await _vision(ui, model).execute(_run(), f.step())

    assert len(model.asked) == GESTURE_BUDGET
    assert result.outcome.disposition is StepDisposition.FAILED
    assert f"{GESTURE_BUDGET} gestures" in (result.outcome.detail or "")


async def test_what_was_already_tried_is_told_to_the_next_attempt() -> None:
    ui = FakeUiDriver()
    ui.outcomes.append(UiOutcome(performed=False, detail="nothing there"))
    model = FakeVisionDriver(CLICK_FINISH, CLICK_FINISH)

    await _vision(ui, model).execute(_run(), f.step())

    assert model.asked[1]["history"], "a second guess with no memory is the same guess"


async def test_no_vision_configured_is_a_recorded_reason_not_a_crash() -> None:
    result = await PerformWithVision(
        FakeUiDriver(), None, FakeClock(), egress_enabled=True
    ).execute(_run(), f.step())

    assert result.outcome.disposition is StepDisposition.FAILED
    assert "no vision rung" in (result.outcome.detail or "")
