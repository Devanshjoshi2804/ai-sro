"""Work a goal out on the screen, when nobody has demonstrated it.

The rung below this replays what somebody proved. This one has nothing to
replay: it opens the screen the catalogue names, looks at it, and proposes one
gesture at a time until the goal is met or the budget runs out.

Everything that makes the other rungs safe applies here and matters more,
because nothing about this was demonstrated:

- **A budget.** A fixed number of gestures. A model that has not finished in
  that many is not about to, and an unbounded loop of a vision model driving a
  live warehouse is not a thing that should exist.
- **One system.** The browser starts on the connection's own host and any
  gesture proposed against another is refused. A model that wandered off the
  WMS would be acting with the operator's session somewhere nobody agreed to.
- **The operator said go.** A pursuit that changes anything carries their
  confirmation, exactly as an assisted run does.
- **The model never decides it worked.** ``done`` is a claim, recorded as one.
  What the run reports is what the screen showed afterwards.

And every gesture and call is captured, so a task worked out once can be
induced into a skill and replayed over the API the next time. The slow rung
exists to make itself unnecessary.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlsplit

from sro.application.context import RequestContext
from sro.application.execution.egress import EgressRefused, prepare
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
"""Enough to open a screen, fill a short form and save. Chosen to be obviously
finite rather than tuned: the number that matters is that there is one."""

_WAIT_SECONDS = 5
"""What the model means by "wait": time for a screen that is still loading to
finish, not a gesture at whatever coordinates an absent x/y defaulted to."""

_STUCK = 3
"""Gestures in a row that change nothing before giving up.

Watching the first live pursuit, the model clicked within a few pixels of the
same point eight times. Nothing told it the screen had not moved, so nothing
made it try something else."""

_ALLOWED = (
    ActionKind.CLICK,
    ActionKind.TYPE,
    ActionKind.SELECT,
    ActionKind.SCROLL,
    ActionKind.HOVER,
)
"""No navigation. The screen is chosen from the catalogue before anything opens;
a model that could navigate could take the operator's session anywhere."""


@dataclass(frozen=True, slots=True)
class Pursued:
    goal: str
    reached: bool
    """What the model claimed. Never what the system confirms -- that is the
    screen's job, and a pursuit has no demonstration to assert against."""

    gestures: tuple[str, ...]
    landed_at: str
    detail: str

    recording_id: str = ""
    """The demonstration this pursuit left behind. A task worked out on screen
    is evidence exactly as a taught one is -- the same gestures, the same calls,
    the same capture -- which is what lets the slow rung make itself
    unnecessary."""

    skill_id: str = ""
    """The skill induced from it, when it reached the goal and the recording
    carried enough to build one."""


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
        self._egress_enabled = egress_enabled
        self._model = model

    async def execute(
        self,
        ctx: RequestContext,
        *,
        goal: Goal,
        target_system: str,
        values: dict[str, str],
        watching: Callable[[str], None] | None = None,
        using: Callable[[str], None] | None = None,
    ) -> Pursued:
        """``watching`` is told each gesture as it happens.

        A browser being driven on somebody's behalf with nothing on screen for
        two minutes is indistinguishable from a hang.

        ``using`` is told which browser this took, so whoever is watching can
        say so -- and so the reaper that releases forgotten sessions can tell
        this one is not forgotten.
        """
        if self._vision is None or self._ui is None:
            raise VisionUnavailable(
                "this deployment has no rung that can look at a screen, so a task nobody "
                "has demonstrated cannot be attempted"
            )

        async with self._uow as uow:
            connection = await uow.connections.find_by_system(ctx.tenant_id, target_system)
        if connection is None:
            raise BrowserUnavailable(f"{target_system} is not connected")

        start = goal.start_url or connection.base_url
        host = urlsplit(connection.base_url).hostname or ""
        if (urlsplit(start).hostname or host) != host:
            # The catalogue named a screen on another host. That is a bad entry,
            # not an instruction.
            start = connection.base_url

        gestures: list[str] = []
        seen_before = ""
        repeated = 0
        reached = False
        detail = "the budget ran out before the screen showed the result"

        # A browser somebody is already signed into, before opening one that is
        # not. Restoring cookies into a fresh browser lands on the identity
        # provider here -- the WMS does not accept a transplanted session -- so
        # a pursuit that opens its own browser spends its whole budget clicking
        # a login page, which is exactly what it did.
        session, borrowed = await self._browser_for(connection)
        # Claimed, so the reaper leaves it alone: a browser being driven and a
        # browser somebody forgot about look identical from outside.
        if using is not None:
            using(str(session.id))
        ui = self._ui.for_session(session.debugger_url)
        recording_id = ""
        skill_id = ""
        try:
            if not borrowed:
                await self._browser.restore(session.id, await self._session_of(connection))

            # Recorded exactly as a demonstration is, and before the first
            # gesture: what a pursuit does on screen is evidence of the same
            # kind an operator's hands produce, and a task worked out once
            # should never have to be worked out again.
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
                # Nothing to look at. Twelve screenshots of a blank page cost a
                # model call each and end in "the screen did not change", which
                # reads as the task being impossible -- it was the browser.
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
                    # A claim, not a verification. A pursuit has no demonstration
                    # to assert against, so what it reports is what it was told.
                    reached = True
                    detail = proposed.reasoning or "the model said the screen showed the result"
                    break
                if proposed.wait:
                    # Not a gesture: nothing was clicked, so nothing about the
                    # screen not changing afterwards means the model is stuck.
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
                # What changed, not only what was attempted. The model was
                # being handed its own past coordinates and nothing else, so it
                # clicked the same place eight times without ever learning that
                # the screen had not moved.
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
                    # Three gestures, nothing moved. A model that has not
                    # affected the screen in three tries is not about to, and
                    # spending the rest of the budget proves it slowly.
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
            # Never close a browser we did not open: it belongs to whoever
            # signed into it, and closing it logs a warehouse operator out.
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
        )

    async def _keep(self, ctx: RequestContext, recording_id: RecordingId, *, reached: bool) -> str:
        """Seal what was recorded, and induce a skill when it proved something.

        Only when the goal was reached. A pursuit that ran out of budget half
        way through a form recorded a half-filled form, and inducing a skill
        from that would teach the system to do the wrong thing quickly.
        """
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
            # A pursuit that reached its goal without leaving evidence a skill
            # can be built from is still a success; it just cannot be repeated
            # cheaply yet, and saying so beats a skill nobody can trust.
            logger.info("pursuit %s left nothing to induce: %s", recording_id, refusal)
            return ""
        return understood.skill_id.value

    async def _browser_for(self, connection: Connection) -> tuple[BrowserSession, bool]:
        """A signed-in browser if one is open, otherwise a new one.

        Returns whether it was borrowed, because a borrowed browser is not ours
        to close and its session is not ours to overwrite.
        """
        try:
            for session_id in await self._browser.live_sessions():
                cookies = await self._browser.session_cookies(session_id)
                if _holds_a_session(cookies, connection.base_url):
                    return (
                        BrowserSession(
                            id=session_id,
                            live_view_url=await self._browser.live_view_url(session_id) or "",
                            debugger_url=await self._browser.debugger_url(session_id),
                        ),
                        True,
                    )
        except BrowserUnavailable:
            logger.info("could not look for a signed-in browser; opening one")
        return await self._browser.open(), False

    def _brief(self, goal: Goal, values: dict[str, str]) -> str:
        """The goal, plus the values the operator gave for it.

        Given rather than guessed. A model asked to work out a transport mode
        code on screen will invent one, and it will look plausible.
        """
        if not values:
            return goal.brief()
        given = "\n".join(f"- {name}: {value}" for name, value in values.items() if value)
        return f"{goal.brief()}\nUse exactly these values:\n{given}"

    async def _session_of(self, connection: Connection) -> list[dict[str, object]]:
        """The stored session, so the browser starts signed in.

        A blank browser sent at a WMS lands on a login page, and a model asked
        to reach a goal from there will try to sign in.
        """
        stored = await self._vault.get(connection.session_key)
        if not stored:
            return []
        cookies: list[dict[str, object]] = json.loads(stored).get("cookies", [])
        return cookies


_SETTLE_SECONDS = 1.0
_SETTLE_TRIES = 8
"""How long the screen is given to arrive. A WMS portal redirects twice through
an identity provider before it renders, so the first read after `navigate` is
regularly still `about:blank`."""


_SETTLE_TICKS = 4
"""How many times a screen is re-read before it is called unchanged.

The driver already waits after acting, and against this application that wait
was not enough: an ExtJS panel swap took longer than it, so the read came back
identical and the gesture was recorded as having changed nothing. The model was
then told its correct click had done nothing, three times, and gave up on a
screen that had in fact moved every time.

Polled rather than lengthened, because most gestures do land inside the wait
and paying the slowest case on every one of twelve is most of a minute.
"""


async def _settled(ui: UiDriver, before: str) -> Screen:
    """The screen once it has finished reacting, or as it is after long enough."""
    screen = await ui.capture()
    for _ in range(_SETTLE_TICKS):
        if screen.text_digest != before:
            return screen
        await asyncio.sleep(1.0)
        screen = await ui.capture()
    return screen


async def _arrived(ui: UiDriver, wanted: str) -> str | None:
    """``None`` once the screen is really there; otherwise why it is not.

    Checked because a pursuit is expensive and a blank page is indistinguishable
    from a hard task: self-hosted Steel hands every session the same Chrome, and
    a pursuit handed one sitting on `about:blank` spent its whole budget
    clicking a page that was never loaded.
    """
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
    """Whether this browser carries the application's own cookie.

    The identity provider's cookies are set before anybody signs in, so their
    presence proves nothing. The application's do not exist until a login
    finished.
    """
    host = urlsplit(base_url).hostname or ""
    return any(
        host.endswith(str(cookie.get("domain", "")).lstrip("."))
        or str(cookie.get("domain", "")).lstrip(".") in host
        for cookie in cookies
    )
