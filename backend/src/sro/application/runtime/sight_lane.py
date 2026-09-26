from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from urllib.parse import urlparse, urlsplit

from sro.application.ports.page import PageDriver, PageUnsettled
from sro.application.ports.vision import VisionDriver
from sro.application.runtime.step import Held, LaneContext, Stopped
from sro.application.runtime.ui_lane import K_UI_WAIT_S, confirming, same_call, ui_payload
from sro.domain.execution.belts import expected_statuses
from sro.domain.execution.compose import Adding
from sro.domain.execution.evidence import READ_METHODS, primary_gesture, recorded_call, writes
from sro.domain.execution.lanes import (
    K_SIGHT_ACTIONS,
    Lane,
    StepResult,
    fingerprint_of,
    write_confirmed,
)
from sro.domain.execution.planning import shown_after, value_for
from sro.domain.execution.records import made_by, names_in
from sro.domain.execution.secrets import needs_a_secret
from sro.domain.observation.gesture import Call, Gesture
from sro.domain.observation.trim import looks_like_an_id, path_shape
from sro.domain.recording.events import ActionKind
from sro.domain.shared.hosts import system_of
from sro.domain.skill.workflow import Step
from sro.whose import about

ALLOWED = (ActionKind.CLICK, ActionKind.TYPE, ActionKind.PRESS, ActionKind.SCROLL, ActionKind.HOVER)
_LEFT = "the page left the system"


@dataclass(slots=True)
class _Tried:
    mark: int | None = None
    at_mark: str = ""
    warned: bool = False
    why: str = ""
    points: list[tuple[str, Mapping[str, object] | None]] = field(default_factory=list)


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
        given = {name for name, value in values.items() if value.strip()}
        primary = primary_gesture(step, ctx.by_id, given)
        if held is None or primary is None or not self._models:
            return _refused("sight has no page or no model", "no_evidence")
        if any(needs_a_secret(ctx.by_id[one]) for one in step.cites if one in ctx.by_id):
            return _refused("sight never types a credential", "secret")
        watched = recorded_call(step, ctx.by_id) if writes(step, ctx.by_id) else None

        async def settle(tried: _Tried) -> StepResult:
            return await self._settle(step, values, ctx, held, primary, tried)

        return await self._guarded(
            _goal(step, values, primary),
            step.order,
            primary,
            watched,
            recorded_call(step, ctx.by_id),
            ctx,
            held,
            settle,
        )

    async def fill(
        self, says: str, write: Step, ctx: LaneContext, check: Mapping[str, object]
    ) -> StepResult:
        held = ctx.held
        primary = primary_gesture(write, ctx.by_id)
        if held is None or primary is None or not self._models:
            return _refused("sight has no page or no model", "no_evidence")
        watched = recorded_call(write, ctx.by_id)

        async def settle(tried: _Tried) -> StepResult:
            if await self._sent(held, watched, tried):
                return StepResult("unknown", Lane.SIGHT, "the write was sent while filling a field")
            hit = tried.points[-1][1] if tried.points else None
            pin = hit.get("pin") if hit else None
            if not (isinstance(pin, str) and pin and _taught(hit)):
                return StepResult(
                    "unknown", Lane.SIGHT, tried.why or "sight never reached the field"
                )
            if await self._driver.wait_for(
                held.session, held.target_id, {**check, "pin": pin}, self._wait_s
            ):
                return StepResult("done", Lane.SIGHT, learned=_taught(hit))
            return StepResult("unknown", Lane.SIGHT, "the field sight set does not hold the value")

        return await self._guarded(
            says, write.order, primary, watched, watched, ctx, held, settle, writing=False
        )

    async def _guarded(
        self,
        goal: str,
        order: int,
        primary: Gesture,
        watched: Call | None,
        awaited: Call | None,
        ctx: LaneContext,
        held: Held,
        settle: Callable[[_Tried], Awaitable[StepResult]],
        *,
        writing: bool = True,
    ) -> StepResult:
        tried = _Tried()
        try:
            await self._drive(goal, order, primary, watched, ctx, held, tried, writing=writing)
            if awaited is not None and tried.points and tried.mark is not None:
                await self._driver.wait_for_call(
                    held.session,
                    held.target_id,
                    method=awaited.method.upper(),
                    shape=path_shape(awaited.url),
                    since=tried.mark,
                    deadline_s=self._wait_s,
                )
            return await settle(tried)
        except (Stopped, asyncio.CancelledError):
            raise
        except Exception as exc:
            if tried.warned or (watched is not None and tried.mark is not None):
                return StepResult("unknown", Lane.SIGHT, f"the write may have gone: {exc}")
            raise

    async def _drive(
        self,
        goal: str,
        order: int,
        primary: Gesture,
        watched: Call | None,
        ctx: LaneContext,
        held: Held,
        tried: _Tried,
        *,
        writing: bool = True,
    ) -> None:
        home = system_of(primary.url)
        for model in self._models:
            history: list[str] = []
            for _ in range(K_SIGHT_ACTIONS):
                ctx.check_stop()
                if await self._sent(held, watched, tried):
                    return
                if not await self._at_home(held, home):
                    tried.why = _LEFT
                    return
                screen = await self._driver.screenshot(held.session, held.target_id)
                with about(tenant=str(ctx.tenant_id), workflow=ctx.workflow.id, step=order):
                    proposed = await model.propose(
                        goal=goal, screen=screen, allowed=ALLOWED, history=tuple(history)
                    )
                del screen
                if proposed.done:
                    return
                if proposed.wait:
                    history.append("waited")
                    try:
                        await self._driver.signals(held.session, held.target_id)
                    except PageUnsettled:
                        tried.why = "the page did not settle"
                        break
                    continue
                if proposed.refusal or proposed.x is None or proposed.y is None:
                    tried.why = proposed.refusal or "the model named no point"
                    break
                if await self._sent(held, watched, tried):
                    return
                if not await self._at_home(held, home):
                    tried.why = _LEFT
                    return
                if tried.mark is None:
                    tried.mark = await self._driver.mark(held.session, held.target_id)
                    tried.at_mark = await self._driver.url_of(held.session, held.target_id)
                hit = await self._driver.hit_test(
                    held.session, held.target_id, proposed.x, proposed.y
                )
                if hit and hit.get("unreachable"):
                    tried.why = "the point lands in a frame of another origin"
                    break
                if writing and watched is not None and not tried.warned:
                    await ctx.about_to_write(self.lane)
                    tried.warned = True
                hops = hit.get("frame_path") if hit else None
                await self._driver.point(
                    held.session,
                    held.target_id,
                    proposed.action,
                    proposed.x,
                    proposed.y,
                    proposed.value,
                    hops if isinstance(hops, list) else None,
                )
                tried.points.append((proposed.action.value, hit))
                tried.why = ""
                history.append(f"{proposed.action.value} at {proposed.x},{proposed.y}")
        tried.why = tried.why or "sight could not finish the step"

    async def _sent(self, held: Held, watched: Call | None, tried: _Tried) -> bool:
        if watched is None or tried.mark is None:
            return False
        method, shape = watched.method.upper(), path_shape(watched.url)
        return any(
            one.method.upper() == method and path_shape(one.url) == shape
            for one in await self._driver.calls_since(held.session, held.target_id, tried.mark)
        )

    async def _at_home(self, held: Held, home: str | None) -> bool:
        return (
            bool(home)
            and system_of(await self._driver.url_of(held.session, held.target_id)) == home
        )

    async def _settle(
        self,
        step: Step,
        values: Mapping[str, str],
        ctx: LaneContext,
        held: Held,
        primary: Gesture,
        tried: _Tried,
    ) -> StepResult:
        if not tried.points or tried.mark is None:
            return _refused(tried.why or "sight never acted", "gave_up", step.says)
        mark = tried.mark
        recorded = recorded_call(step, ctx.by_id)
        calls = await self._driver.calls_since(held.session, held.target_id, mark)
        adding = ctx.adding.get(step.order, Adding())
        found = [
            (one, keys)
            for one in calls
            if recorded is not None and (keys := same_call(one, recorded, adding)) is not None
        ]
        own = [one for one, _ in found]
        if writes(step, ctx.by_id):
            wanted = expected_statuses(step, ctx.by_id)
            verdict = write_confirmed(recorded=recorded, wanted=wanted, calls=own)
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
                kind, hit = tried.points[-1]
                learned = _taught(hit) if kind == primary.action.kind else {}
                return StepResult(
                    "done",
                    Lane.SIGHT,
                    read=made,
                    calls=calls,
                    learned=learned,
                    keyed=confirming(found, wanted),
                )
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
            return StepResult("read", Lane.SIGHT, read=names_in(got.body), calls=calls)
        going = _next_page(primary)
        if going is not None:
            now = await self._driver.url_of(held.session, held.target_id)
            if _reached(now, going, tried.at_mark, values):
                return StepResult("done", Lane.SIGHT, calls=calls)
        else:
            hit = next(
                (hit for kind, hit in reversed(tried.points) if kind == primary.action.kind), None
            )
            if await self._holds(step, values, ctx, held, primary, hit):
                return StepResult("done", Lane.SIGHT, calls=calls, learned=_taught(hit))
        return StepResult(
            "unknown", Lane.SIGHT, tried.why or "only the model says the step is done", calls=calls
        )

    async def _holds(
        self,
        step: Step,
        values: Mapping[str, str],
        ctx: LaneContext,
        held: Held,
        primary: Gesture,
        hit: Mapping[str, object] | None,
    ) -> bool:
        pin = hit.get("pin") if hit else None
        if not (isinstance(pin, str) and pin and _taught(hit)):
            return False
        value = value_for(step, primary, values, None)
        after = primary.action.after
        payload = ui_payload(step, primary, value, None, ctx.by_id)
        payload.pop("write", None)
        expect = {
            "value": shown_after(step, primary, value),
            "visible": None if after is None else after.visible,
            "enabled": None if after is None else after.enabled,
        }
        return await self._driver.wait_for(
            held.session, held.target_id, {**payload, "pin": pin, "expect": expect}, self._wait_s
        )


def _next_page(primary: Gesture) -> str | None:
    went = [mark.url for mark in primary.page_events if mark.url and mark.at >= primary.at]
    if not went or path_shape(went[-1]) == path_shape(primary.url or ""):
        return None
    return went[-1]


def _reached(now: str, going: str, at_mark: str, values: Mapping[str, str]) -> bool:
    if system_of(now) != system_of(going) or path_shape(now) != path_shape(going):
        return False
    if system_of(at_mark) == system_of(going) and path_shape(at_mark) == path_shape(going):
        return False
    given = {value for value in values.values() if value.strip()}
    return all(
        mine in (given or {recorded})
        for mine, recorded in zip(
            urlsplit(now).path.split("/"), urlsplit(going).path.split("/"), strict=True
        )
        if looks_like_an_id(recorded)
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
    if not isinstance(frame_path, list) or not all(isinstance(hop, dict) for hop in frame_path):
        return {}
    hops = [
        {
            "index": hop.get("index"),
            "url": urlparse(url).path if isinstance(url := hop.get("url"), str) else None,
        }
        for hop in frame_path
    ]
    return {"strategy": strategy, "query": query, "frame_path": json.dumps(hops)}


def _goal(step: Step, values: Mapping[str, str], primary: Gesture) -> str:
    given = ", ".join(f"{name} = {value}" for name, value in values.items() if value.strip())
    after = primary.action.after
    value = value_for(step, primary, values, None)
    shown = shown_after(step, primary, value)
    wanted = f" Afterwards the control should show {shown!r}." if after and shown else ""
    return f"{step.says}.{wanted}" + (f" Values: {given}." if given else "")
