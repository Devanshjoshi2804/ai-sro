from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import asdict
from urllib.parse import urlsplit

from sro.application.ports.page import PageAnswer, PageDriver
from sro.application.runtime.step import Held, LaneContext, Stopped
from sro.domain.execution.belts import expected_statuses
from sro.domain.execution.evidence import READ_METHODS, primary_gesture, recorded_call, writes
from sro.domain.execution.lanes import (
    Lane,
    SeenCall,
    StepResult,
    fingerprint_of,
    write_confirmed,
)
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.execution.planning import value_for
from sro.domain.execution.records import made_by, names_in
from sro.domain.execution.secrets import needs_a_secret
from sro.domain.observation.gesture import AfterState, Body, Call, Gesture
from sro.domain.observation.trim import body_key_set, path_shape
from sro.domain.skill.signing_in import a_sign_in_page
from sro.domain.skill.workflow import Step

K_UI_WAIT_S = 15.0
_NOTHING_SENT = frozenset({"control_not_found", "frame_not_found", "frame_ambiguous"})


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
        ctx.check_stop()
        if not writes(step, ctx.by_id):
            return await self._perform(step, primary, value, payload, held, ctx)
        await ctx.about_to_write()
        try:
            return await self._perform(step, primary, value, payload, held, ctx)
        except (Stopped, asyncio.CancelledError):
            raise
        except Exception as exc:
            return StepResult("unknown", Lane.UI, f"the write's outcome was lost: {exc}")

    async def _perform(
        self,
        step: Step,
        primary: Gesture,
        value: str | None,
        payload: Mapping[str, object],
        held: Held,
        ctx: LaneContext,
    ) -> StepResult:
        recorded = recorded_call(step, ctx.by_id)
        mark = await self._driver.mark(held.session, held.target_id)
        answer = await self._driver.act(held.session, held.target_id, payload)
        if not answer.ok:
            expired = a_sign_in_page(await self._driver.signals(held.session, held.target_id))
            return StepResult(
                "failed",
                Lane.UI,
                answer.detail or str(answer.error_kind),
                never_left=answer.error_kind in _NOTHING_SENT,
                expired=expired,
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
        own = [one for one in calls if recorded is not None and _same_call(one, recorded)]
        after = primary.action.after
        if writes(step, ctx.by_id):
            verdict = write_confirmed(
                recorded=recorded, wanted=expected_statuses(step, ctx.by_id), calls=own
            )
            if verdict == "failed":
                return StepResult(
                    "failed",
                    Lane.UI,
                    "the system rejected the write",
                    calls=calls,
                    fingerprint=fingerprint_of(Lane.UI, "rejected", str(recorded)),
                )
            if verdict == "done" and (
                answer.repaired
                or (
                    after is not None and not await self._holds(held, answer, payload, after, value)
                )
            ):
                verdict = "unknown"
            made = next(
                filter(None, (made_by({"status": one.status, "body": one.body}) for one in own)),
                {},
            )
            return StepResult(verdict or "unknown", Lane.UI, read=made, calls=calls)
        if recorded is not None and recorded.method.upper() in READ_METHODS:
            got = next(
                (
                    one
                    for one in reversed(own)
                    if one.status is not None and 200 <= one.status < 300
                ),
                None,
            )
            if got is not None:
                return StepResult("read", Lane.UI, read=names_in(got.body), calls=calls)
        if after is not None and not await self._holds(held, answer, payload, after, value):
            return StepResult(
                "failed",
                Lane.UI,
                "the control did not end up as recorded",
                fingerprint=fingerprint_of(Lane.UI, "after_state", str(after)),
            )
        if answer.repaired:
            return StepResult(
                "unknown", Lane.UI, "a repaired match is never confirmed", calls=calls
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


def _same_call(seen: SeenCall, recorded: Call) -> bool:
    if not (
        seen.own_frame
        and seen.method.upper() == recorded.method.upper()
        and path_shape(seen.url) == path_shape(recorded.url)
        and urlsplit(seen.url).netloc == urlsplit(recorded.url).netloc
    ):
        return False
    wanted = body_key_set(recorded.request_body)
    if wanted is None:
        return True
    seen_body = (
        Body(text=seen.request_body, mime_type=seen.request_content_type)
        if seen.request_body is not None
        else None
    )
    return body_key_set(seen_body) == wanted
