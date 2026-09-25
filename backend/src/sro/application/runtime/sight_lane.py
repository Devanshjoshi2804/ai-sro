from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from dataclasses import dataclass, field

from sro.application.ports.page import PageDriver
from sro.application.ports.vision import VisionDriver
from sro.application.runtime.step import Held, LaneContext, Stopped
from sro.application.runtime.ui_lane import K_UI_WAIT_S, same_call
from sro.domain.execution.belts import expected_statuses
from sro.domain.execution.evidence import READ_METHODS, primary_gesture, recorded_call, writes
from sro.domain.execution.lanes import (
    K_SIGHT_ACTIONS,
    Lane,
    StepResult,
    fingerprint_of,
    write_confirmed,
)
from sro.domain.execution.records import made_by, names_in
from sro.domain.execution.secrets import needs_a_secret
from sro.domain.observation.trim import path_shape
from sro.domain.recording.events import ActionKind
from sro.domain.shared.hosts import origin_of
from sro.domain.skill.workflow import Step
from sro.whose import about

ALLOWED = (ActionKind.CLICK, ActionKind.TYPE, ActionKind.PRESS, ActionKind.SCROLL, ActionKind.HOVER)
_LEFT = "the page left the system"


@dataclass(slots=True)
class _Tried:
    pointed: int = 0
    why: str = ""
    learned: dict[str, str] = field(default_factory=dict)


class SightLane:
    lane = Lane.SIGHT

    def __init__(
        self,
        driver: PageDriver,
        flash: VisionDriver | None,
        pro: VisionDriver | None,
        *,
        wait_s: float = K_UI_WAIT_S,
    ) -> None:
        self._driver = driver
        self._models = tuple(model for model in (flash, pro) if model is not None)
        self._wait_s = wait_s

    async def execute(self, step: Step, values: Mapping[str, str], ctx: LaneContext) -> StepResult:
        held = ctx.held
        primary = primary_gesture(step, ctx.by_id)
        if held is None or primary is None or not self._models:
            return _refused("sight has no page or no model", "no_evidence")
        if any(needs_a_secret(ctx.by_id[one]) for one in step.cites if one in ctx.by_id):
            return _refused("sight never types a credential", "secret")
        home = origin_of(step.system or primary.url or "")
        writing = writes(step, ctx.by_id)
        mark = await self._driver.mark(held.session, held.target_id)
        tried = _Tried()
        try:
            await self._drive(step, values, ctx, held, home, writing, tried)
            return await self._settle(step, ctx, held, mark, writing, tried)
        except (Stopped, asyncio.CancelledError):
            raise
        except Exception as exc:
            if writing and tried.pointed:
                return StepResult("unknown", Lane.SIGHT, f"the write's outcome was lost: {exc}")
            raise

    async def _drive(
        self,
        step: Step,
        values: Mapping[str, str],
        ctx: LaneContext,
        held: Held,
        home: str,
        writing: bool,
        tried: _Tried,
    ) -> None:
        goal = _goal(step, values)
        for model in self._models:
            history: list[str] = []
            for _ in range(K_SIGHT_ACTIONS):
                ctx.check_stop()
                if not await self._at_home(held, home):
                    tried.why = _LEFT
                    return
                screen = await self._driver.screenshot(held.session, held.target_id)
                with about(tenant=str(ctx.tenant_id), workflow=ctx.workflow.id, step=step.order):
                    proposed = await model.propose(
                        goal=goal, screen=screen, allowed=ALLOWED, history=tuple(history)
                    )
                del screen
                if proposed.done:
                    return
                if proposed.wait:
                    history.append("waited")
                    continue
                if proposed.refusal or proposed.x is None or proposed.y is None:
                    tried.why = proposed.refusal or "the model named no point"
                    break
                if not await self._at_home(held, home):
                    tried.why = _LEFT
                    return
                hit = await self._driver.hit_test(
                    held.session, held.target_id, proposed.x, proposed.y
                )
                if writing and not tried.pointed:
                    await ctx.about_to_write()
                await self._driver.point(
                    held.session,
                    held.target_id,
                    proposed.action,
                    proposed.x,
                    proposed.y,
                    proposed.value,
                )
                tried.pointed += 1
                tried.learned = _taught(hit)
                history.append(f"{proposed.action.value} at {proposed.x},{proposed.y}")
        tried.why = tried.why or "sight could not finish the step"

    async def _at_home(self, held: Held, home: str) -> bool:
        return (
            bool(home)
            and origin_of(await self._driver.url_of(held.session, held.target_id)) == home
        )

    async def _settle(
        self, step: Step, ctx: LaneContext, held: Held, mark: int, writing: bool, tried: _Tried
    ) -> StepResult:
        if not tried.pointed:
            return _refused(tried.why or "sight never acted", "gave_up", step.says)
        recorded = recorded_call(step, ctx.by_id)
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
        own = [one for one in calls if recorded is not None and same_call(one, recorded)]
        if writing:
            verdict = write_confirmed(
                recorded=recorded, wanted=expected_statuses(step, ctx.by_id), calls=own
            )
            if verdict == "failed":
                return StepResult(
                    "failed",
                    Lane.SIGHT,
                    "the system rejected the write",
                    calls=calls,
                    fingerprint=fingerprint_of(Lane.SIGHT, "rejected", str(recorded)),
                )
            if verdict == "done":
                made = next(
                    filter(
                        None, (made_by({"status": one.status, "body": one.body}) for one in own)
                    ),
                    {},
                )
                return StepResult("done", Lane.SIGHT, read=made, calls=calls, learned=tried.learned)
            return StepResult(
                "unknown", Lane.SIGHT, tried.why or "no call confirmed the write", calls=calls
            )
        got = next(
            (
                one
                for one in reversed(own)
                if one.method.upper() in READ_METHODS
                and one.status is not None
                and 200 <= one.status < 300
            ),
            None,
        )
        if got is not None:
            return StepResult(
                "read", Lane.SIGHT, read=names_in(got.body), calls=calls, learned=tried.learned
            )
        return StepResult(
            "unknown", Lane.SIGHT, tried.why or "only the model says the step is done", calls=calls
        )


def _refused(why: str, kind: str, evidence: str = "") -> StepResult:
    return StepResult(
        "failed",
        Lane.SIGHT,
        why,
        never_left=True,
        fingerprint=fingerprint_of(Lane.SIGHT, kind, evidence),
    )


def _taught(hit: Mapping[str, object] | None) -> dict[str, str]:
    if not hit or hit.get("unreachable"):
        return {}
    strategy, query, frame_path = hit.get("strategy"), hit.get("query"), hit.get("frame_path")
    if not (isinstance(strategy, str) and strategy and isinstance(query, str) and query):
        return {}
    if not isinstance(frame_path, list):
        return {}
    return {"strategy": strategy, "query": query, "frame_path": json.dumps(frame_path)}


def _goal(step: Step, values: Mapping[str, str]) -> str:
    given = ", ".join(f"{name} = {value}" for name, value in values.items() if value.strip())
    return f"{step.says}." + (f" Values: {given}." if given else "")
