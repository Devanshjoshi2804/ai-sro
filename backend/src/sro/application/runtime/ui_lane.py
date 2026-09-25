from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict

from sro.application.ports.page import PageAnswer, PageDriver, PageUnsettled
from sro.application.runtime.step import Held, LaneContext
from sro.domain.execution.belts import expected_statuses
from sro.domain.execution.evidence import READ_METHODS, primary_gesture, recorded_call, writes
from sro.domain.execution.lanes import Lane, StepResult, fingerprint_of, write_confirmed
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.execution.planning import value_for
from sro.domain.execution.records import made_by, names_in
from sro.domain.execution.secrets import needs_a_secret
from sro.domain.observation.gesture import AfterState, Gesture
from sro.domain.observation.trim import path_shape
from sro.domain.skill.signing_in import expired
from sro.domain.skill.workflow import Step

K_UI_WAIT_S = 15.0


def ui_payload(
    step: Step,
    gesture: Gesture,
    value: str | None,
    learned: LearnedStep | None,
    by_id: Mapping[str, Gesture],
) -> dict[str, object]:
    target = gesture.action.target
    payload: dict[str, object] = {
        "action": gesture.action.kind,
        "value": value,
        "target": {} if target is None else asdict(target),
        "learned": None
        if learned is None or not learned.usable
        else {"strategy": learned.strategy, "query": learned.query},
        "frame_path": None
        if gesture.action.frame_path is None
        else [asdict(hop) for hop in gesture.action.frame_path],
    }
    if not writes(step, by_id):
        payload["write"] = False
    return payload


class UiLane:
    lane = Lane.UI

    def __init__(self, driver: PageDriver, *, wait_s: float = K_UI_WAIT_S) -> None:
        self._driver = driver
        self._wait_s = wait_s

    async def execute(self, step: Step, values: Mapping[str, str], ctx: LaneContext) -> StepResult:
        held = ctx.held
        given = {name for name, value in values.items() if value.strip()}
        primary = primary_gesture(step, ctx.by_id, given)
        if held is None or primary is None or primary.action.target is None:
            return StepResult(
                "failed",
                Lane.UI,
                "no recorded control to act on",
                fingerprint=fingerprint_of(Lane.UI, "no_evidence"),
            )
        value = ctx.secret if needs_a_secret(primary) else value_for(step, primary, values, None)
        payload = ui_payload(step, primary, value, ctx.learned.get(step.order), ctx.by_id)
        writing = writes(step, ctx.by_id)
        recorded = recorded_call(step, ctx.by_id)
        ctx.check_stop()
        if writing:
            await ctx.about_to_write()
        mark = await self._driver.mark(held.session, held.target_id)
        answer = await self._driver.act(held.session, held.target_id, payload)
        if not answer.ok:
            try:
                signals = await self._driver.signals(held.session, held.target_id)
            except PageUnsettled:
                if writing:
                    return StepResult("unknown", Lane.UI, "the page did not settle")
                return StepResult("failed", Lane.UI, "the page did not settle", never_left=True)
            return StepResult(
                "failed",
                Lane.UI,
                answer.detail or str(answer.error_kind),
                expired=expired(signals, primary.page_url or primary.url),
                fingerprint=fingerprint_of(Lane.UI, str(answer.error_kind), str(payload["target"])),
            )
        if recorded is not None:
            await self._driver.wait_for_call(
                held.session,
                held.target_id,
                method=recorded.method.upper(),
                shape=path_shape(recorded.url),
                since=mark,
                deadline_s=self._wait_s,
            )
        calls = await self._driver.calls_since(held.session, held.target_id, mark)
        after = primary.action.after
        if writing:
            verdict = write_confirmed(
                recorded=recorded, wanted=expected_statuses(step, ctx.by_id), calls=calls
            )
            if verdict is None and after is not None:
                held_ok = await self._holds(held, answer, payload, after, value)
                if held_ok and not answer.repaired:
                    verdict = "done"
            if verdict == "failed":
                return StepResult(
                    "failed",
                    Lane.UI,
                    "the system rejected the write",
                    calls=calls,
                    fingerprint=fingerprint_of(Lane.UI, "rejected", str(recorded)),
                )
            made = next(
                (
                    made_by({"status": one.status, "body": one.body})
                    for one in calls
                    if one.status == 201
                ),
                {},
            )
            return StepResult(verdict or "unknown", Lane.UI, read=made, calls=calls)
        if recorded is not None and recorded.method.upper() in READ_METHODS:
            got = next(
                (
                    one
                    for one in reversed(calls)
                    if one.status is not None and 200 <= one.status < 300
                ),
                None,
            )
            if got is not None:
                return StepResult("read", Lane.UI, read=names_in(got.body), calls=calls)
        if after is not None:
            held_ok = await self._holds(held, answer, payload, after, value)
            if not held_ok or answer.repaired:
                return StepResult(
                    "failed",
                    Lane.UI,
                    "the control did not end up as recorded",
                    fingerprint=fingerprint_of(Lane.UI, "after_state", str(after)),
                )
        return StepResult("done", Lane.UI, calls=calls)

    async def _holds(
        self,
        held: Held,
        answer: PageAnswer,
        payload: Mapping[str, object],
        after: AfterState,
        value: str | None,
    ) -> bool:
        expect = {
            "value": value if value is not None else after.value,
            "visible": after.visible,
            "enabled": after.enabled,
        }
        return await self._driver.wait_for(
            held.session,
            held.target_id,
            {**payload, "pin": answer.pin, "expect": expect},
            self._wait_s,
        )
