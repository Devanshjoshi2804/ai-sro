from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlsplit

from sro.application.connection.browsers import Browsers
from sro.application.connection.cookies import belongs_to
from sro.application.context import RequestContext
from sro.application.execution.egress import EgressRefused, prepare
from sro.application.execution.execute_skill import refuse_if_breaker_is_open
from sro.application.induction.errors import InductionFailed
from sro.application.induction.understand import UnderstandRecording
from sro.application.intent.pursue import Goal
from sro.application.ports.browser import BrowserProvider, BrowserSession, BrowserUnavailable
from sro.application.ports.capture import CaptureController
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.ports.ui import UiDriver, UiUnavailable
from sro.application.ports.vault import CredentialVault
from sro.application.ports.vision import Screen, VisionDriver, VisionUnavailable
from sro.application.recording.finish_recording import FinishRecording
from sro.application.recording.start_recording import StartRecording
from sro.domain.connection.connection import Connection
from sro.domain.recording.events import ActionKind
from sro.domain.shared.errors import DomainError
from sro.domain.shared.identifiers import RecordingId

logger = logging.getLogger(__name__)

GESTURE_BUDGET = 12

_WAIT_SECONDS = 5

_STUCK = 3

_ALLOWED = (
    ActionKind.CLICK,
    ActionKind.TYPE,
    ActionKind.SELECT,
    ActionKind.SCROLL,
    ActionKind.HOVER,
)


class Unauthorised(DomainError):
    code = "unauthorised"


@dataclass(frozen=True, slots=True)
class Pursued:
    goal: str
    reached: bool

    gestures: tuple[str, ...]
    landed_at: str
    detail: str

    recording_id: str = ""

    skill_id: str = ""

    authorized_by: str = ""


class PursueGoal:
    def __init__(
        self,
        uow: UnitOfWork,
        vault: CredentialVault,
        browser: BrowserProvider,
        ui: UiDriver | None,
        vision: VisionDriver | None,
        clock: Clock,
        capture: CaptureController,
        start_recording: StartRecording,
        finish_recording: FinishRecording,
        understand: UnderstandRecording,
        browsers: Browsers,
        *,
        egress_enabled: bool,
        model: str = "",
    ) -> None:
        self._uow = uow
        self._vault = vault
        self._browser = browser
        self._ui = ui
        self._vision = vision
        self._clock = clock
        self._capture = capture
        self._start_recording = start_recording
        self._finish_recording = finish_recording
        self._understand = understand
        self._browsers = browsers
        self._egress_enabled = egress_enabled
        self._model = model

    async def execute(
        self,
        ctx: RequestContext,
        *,
        goal: Goal,
        target_system: str,
        values: dict[str, str],
        authorized_by: str | None = None,
        watching: Callable[[str], None] | None = None,
        using: Callable[[str], None] | None = None,
    ) -> Pursued:
        if goal.changes_the_system and not authorized_by:
            raise Unauthorised(
                "this would change the warehouse and nobody confirmed it. A pursuit has no "
                "demonstration behind it, so the confirmation is the only thing standing "
                "between a model's reading of a screen and a real write"
            )

        if self._vision is None or self._ui is None:
            raise VisionUnavailable(
                "this deployment has no rung that can look at a screen, so a task nobody "
                "has demonstrated cannot be attempted"
            )

        now = self._clock.now()
        async with self._uow as uow:
            connection = await uow.connections.find_by_system(ctx.tenant_id, target_system)
            await refuse_if_breaker_is_open(uow, ctx, target_system, now)
        if connection is None:
            raise BrowserUnavailable(f"{target_system} is not connected")

        start = goal.start_url or connection.base_url
        host = urlsplit(connection.base_url).hostname or ""
        if (urlsplit(start).hostname or host) != host:
            start = connection.base_url

        gestures: list[str] = []
        seen_before = ""
        repeated = 0
        reached = False
        detail = "the budget ran out before the screen showed the result"

        session, borrowed = await self._browser_for(ctx, connection)
        if using is not None:
            using(str(session.id))
        ui = self._ui.for_session(session.debugger_url)
        recording_id = ""
        skill_id = ""
        try:
            if not borrowed:
                await self._browser.restore(session.id, await self._session_of(connection))

            started = await self._start_recording.execute(
                ctx,
                label=f"pursued: {goal.intent}"[:120],
                attach_to=session.debugger_url,
            )
            recording_id = started.recording_id.value
            await self._capture.start(
                ctx, recording_id=started.recording_id, debugger_url=session.debugger_url
            )

            await self._browser.navigate(session.id, start)
            if (landed := await _arrived(ui, start)) is not None:
                detail = landed
                return Pursued(
                    goal=goal.intent,
                    reached=False,
                    detail=detail,
                    gestures=tuple(gestures),
                    landed_at="",
                    recording_id=recording_id,
                    skill_id=skill_id,
                )

            for _ in range(GESTURE_BUDGET):
                screen = await ui.capture()
                try:
                    shown = prepare(screen, enabled=self._egress_enabled).screen
                except EgressRefused as refusal:
                    detail = str(refusal)
                    break

                proposed = await self._vision.propose(
                    goal=self._brief(goal, values),
                    screen=shown,
                    allowed=_ALLOWED,
                    history=tuple(gestures),
                )

                if proposed.refusal:
                    detail = f"the model declined: {proposed.refusal}"
                    break
                if proposed.done:
                    reached = True
                    detail = proposed.reasoning or "the model said the screen showed the result"
                    break
                if proposed.wait:
                    gesture = "waited — " + (proposed.reasoning or "letting the screen finish")
                    gestures.append(gesture)
                    if watching is not None:
                        watching(gesture)
                    await asyncio.sleep(_WAIT_SECONDS)
                    continue

                outcome = await ui.perform_at(
                    action=proposed.action,
                    x=proposed.x or 0,
                    y=proposed.y or 0,
                    value=proposed.value,
                )
                after = await _settled(ui, seen_before)
                changed = after.text_digest != seen_before
                repeated = 0 if changed else repeated + 1
                seen_before = after.text_digest

                gesture = (
                    f"{proposed.action.value} at ({proposed.x}, {proposed.y})"
                    + (f" = {proposed.value}" if proposed.value else "")
                    + (
                        ""
                        if not outcome.performed
                        else " — the screen changed"
                        if changed
                        else " — the screen did not change"
                    )
                    + ("" if outcome.performed else " — nothing happened")
                )
                gestures.append(gesture)
                if watching is not None:
                    watching(gesture)
                if not outcome.performed:
                    detail = "the screen did not respond to what was proposed"
                    break

                if repeated >= _STUCK:
                    detail = (
                        f"the screen did not change after {repeated} gestures; "
                        "the goal may need a screen this one cannot reach"
                    )
                    break

            landed = await ui.current_url() or start
        except UiUnavailable as error:
            raise BrowserUnavailable(str(error)) from error
        finally:
            if recording_id:
                skill_id = await self._keep(ctx, RecordingId(recording_id), reached=reached)
            if not borrowed:
                await self._browser.close(session.id)

        return Pursued(
            goal=goal.intent,
            reached=reached,
            gestures=tuple(gestures),
            landed_at=landed,
            detail=detail,
            recording_id=recording_id,
            skill_id=skill_id,
            authorized_by=authorized_by or "",
        )

    async def _keep(self, ctx: RequestContext, recording_id: RecordingId, *, reached: bool) -> str:
        await self._capture.stop(ctx, recording_id=recording_id)
        if not reached:
            await self._finish_recording.abandon(
                ctx, recording_id=recording_id, reason="the goal was not reached"
            )
            return ""

        try:
            await self._finish_recording.seal(ctx, recording_id=recording_id)
            understood = await self._understand.execute(ctx, recording_id=recording_id)
        except (DomainError, InductionFailed) as refusal:
            logger.info("pursuit %s left nothing to induce: %s", recording_id, refusal)
            return ""
        return understood.skill_id.value

    async def _browser_for(
        self, ctx: RequestContext, connection: Connection
    ) -> tuple[BrowserSession, bool]:
        try:
            for session in await self._browsers.mine(ctx):
                cookies = await self._browser.session_cookies(session.id)
                if _holds_a_session(cookies, connection.base_url):
                    return session, True
        except BrowserUnavailable:
            logger.info("could not look for a signed-in browser; opening one")
        return await self._browsers.open(ctx), False

    def _brief(self, goal: Goal, values: dict[str, str]) -> str:
        if not values:
            return goal.brief()
        given = "\n".join(f"- {name}: {value}" for name, value in values.items() if value)
        return f"{goal.brief()}\nUse exactly these values:\n{given}"

    async def _session_of(self, connection: Connection) -> list[dict[str, object]]:
        stored = await self._vault.get(connection.session_key)
        if not stored:
            return []
        cookies: list[dict[str, object]] = json.loads(stored).get("cookies", [])
        return cookies


_SETTLE_SECONDS = 1.0
_SETTLE_TRIES = 8


_SETTLE_TICKS = 4


async def _settled(ui: UiDriver, before: str) -> Screen:
    screen = await ui.capture()
    for _ in range(_SETTLE_TICKS):
        if screen.text_digest != before:
            return screen
        await asyncio.sleep(1.0)
        screen = await ui.capture()
    return screen


async def _arrived(ui: UiDriver, wanted: str) -> str | None:
    host = urlsplit(wanted).hostname or ""
    where = ""
    for _ in range(_SETTLE_TRIES):
        where = await ui.current_url() or ""
        if (urlsplit(where).hostname or "") == host:
            return None
        await asyncio.sleep(_SETTLE_SECONDS)

    if not where or where.startswith("about:"):
        return (
            f"the browser never left {where or 'a blank page'} — it is not showing "
            f"{host}, so there was nothing to work on"
        )
    return (
        f"the browser is on {urlsplit(where).hostname}, not {host} — another session may be "
        "driving it, or the sign-in did not complete"
    )


def _holds_a_session(cookies: tuple[dict[str, object], ...], base_url: str) -> bool:
    return any(belongs_to(cookie, base_url) for cookie in cookies)
