from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sro.application.execution.egress import EgressRefused, prepare
from sro.application.ports.system import Clock
from sro.application.ports.ui import UiDriver, UiUnavailable
from sro.application.ports.vision import ProposedGesture, VisionDriver, VisionUnavailable
from sro.domain.execution.model_call import ModelCall
from sro.domain.execution.run import Medium, Run, StepDisposition, StepOutcome
from sro.domain.recording.events import ActionKind
from sro.domain.skill.skill import SkillStep

GESTURE_BUDGET = 5

_REACHING = (ActionKind.SCROLL, ActionKind.HOVER)


@dataclass(frozen=True, slots=True)
class VisionResult:
    outcome: StepOutcome
    calls: tuple[ModelCall, ...]


class PerformWithVision:
    def __init__(
        self,
        ui: UiDriver | None,
        vision: VisionDriver | None,
        clock: Clock,
        *,
        egress_enabled: bool,
        destination: str = "vision",
        model: str = "",
    ) -> None:
        self._ui = ui
        self._vision = vision
        self._clock = clock
        self._egress_enabled = egress_enabled
        self._destination = destination
        self._model = model

    async def execute(self, run: Run, step: SkillStep, ui: UiDriver | None = None) -> VisionResult:
        driver = ui if ui is not None else self._ui
        if driver is None or self._vision is None:
            return self._stopped(run, step, "no vision rung is configured for this deployment")
        if not run.performs_writes:
            return self._stopped(
                run,
                step,
                f"{run.stage} does not drive the interface; a click cannot be withheld once made",
            )

        allowed = _allowed(step)
        calls: list[ModelCall] = []
        history: list[str] = []

        for attempt in range(GESTURE_BUDGET):
            try:
                screen = await driver.capture()
            except UiUnavailable as error:
                return self._stopped(run, step, str(error), calls)

            started = self._clock.now()
            try:
                redacted = prepare(screen, enabled=self._egress_enabled)
            except EgressRefused as refusal:
                calls.append(
                    self._record(
                        run,
                        step,
                        started,
                        sent=0,
                        image=False,
                        outcome=str(refusal),
                        failed=True,
                        redacted=(),
                    )
                )
                return self._stopped(run, step, str(refusal), calls)

            try:
                gesture = await self._vision.propose(
                    goal=step.intent,
                    screen=redacted.screen,
                    allowed=allowed,
                    history=tuple(history),
                )
            except VisionUnavailable as error:
                calls.append(
                    self._record(
                        run,
                        step,
                        started,
                        sent=len(redacted.screen.image),
                        image=True,
                        outcome=str(error),
                        failed=True,
                        redacted=redacted.removed,
                    )
                )
                return self._stopped(run, step, str(error), calls)

            calls.append(
                self._record(
                    run,
                    step,
                    started,
                    sent=len(redacted.screen.image) + len(redacted.screen.text_digest),
                    image=True,
                    outcome=_describe(gesture),
                    failed=gesture.refusal is not None,
                    redacted=redacted.removed,
                )
            )

            if gesture.refusal is not None:
                return self._stopped(run, step, f"the model declined: {gesture.refusal}", calls)

            if gesture.done:
                return VisionResult(
                    outcome=StepOutcome(
                        index=step.index,
                        medium=Medium.VISION,
                        disposition=StepDisposition.PERFORMED,
                        intent=step.intent,
                        escalated_from=Medium.UI,
                        idempotency_key=f"{run.id}:{step.index}",
                        detail=f"the model believes this was already done: {gesture.reasoning}",
                    ),
                    calls=tuple(calls),
                )

            if gesture.x is None or gesture.y is None:
                history.append(f"{gesture.action} with no coordinates — ignored")
                continue

            result = await driver.perform_at(
                action=gesture.action, x=gesture.x, y=gesture.y, value=gesture.value
            )
            history.append(
                f"attempt {attempt + 1}: {gesture.action} at ({gesture.x},{gesture.y})"
                f" — {'done' if result.performed else result.detail}"
            )
            if result.performed:
                return VisionResult(
                    outcome=StepOutcome(
                        index=step.index,
                        medium=Medium.VISION,
                        disposition=StepDisposition.PERFORMED,
                        intent=step.intent,
                        escalated_from=Medium.UI,
                        idempotency_key=f"{run.id}:{step.index}",
                        matched_by="vision",
                        detail=(
                            f"{gesture.action} at ({gesture.x},{gesture.y}): {gesture.reasoning}"
                        ),
                    ),
                    calls=tuple(calls),
                )

        return self._stopped(run, step, f"{GESTURE_BUDGET} gestures did not finish the step", calls)

    def _stopped(
        self,
        run: Run,
        step: SkillStep,
        detail: str,
        calls: list[ModelCall] | None = None,
    ) -> VisionResult:
        return VisionResult(
            outcome=StepOutcome(
                index=step.index,
                medium=Medium.VISION,
                disposition=StepDisposition.FAILED,
                intent=step.intent,
                escalated_from=Medium.UI,
                detail=detail,
            ),
            calls=tuple(calls or ()),
        )

    def _record(
        self,
        run: Run,
        step: SkillStep,
        started: datetime,
        *,
        sent: int,
        image: bool,
        outcome: str,
        failed: bool,
        redacted: tuple[str, ...],
    ) -> ModelCall:
        now = self._clock.now()
        return ModelCall(
            id=f"{run.id}:{step.index}:{len(outcome)}:{now.timestamp()}",
            tenant_id=run.tenant_id,
            run_id=run.id,
            step_index=step.index,
            purpose="propose_gesture",
            destination=self._destination,
            model=self._model,
            started_at=started,
            duration_ms=int((now - started).total_seconds() * 1000),
            sent_bytes=sent,
            image_sent=image,
            redacted_fields=redacted,
            outcome=outcome[:400],
            failed=failed,
        )


def _allowed(step: SkillStep) -> tuple[ActionKind, ...]:
    own = step.ui_plan.action if step.ui_plan is not None else ActionKind.CLICK
    return (own, *_REACHING)


def _describe(gesture: ProposedGesture) -> str:
    if gesture.refusal:
        return f"refused: {gesture.refusal}"
    if gesture.done:
        return f"claims done: {gesture.reasoning}"
    return f"{gesture.action} at ({gesture.x},{gesture.y}): {gesture.reasoning}"
