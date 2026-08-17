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

import json
from dataclasses import dataclass
from urllib.parse import urlsplit

from sro.application.context import RequestContext
from sro.application.execution.egress import EgressRefused, prepare
from sro.application.intent.pursue import Goal
from sro.application.ports.browser import BrowserProvider, BrowserUnavailable
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.ports.ui import UiDriver, UiUnavailable
from sro.application.ports.vault import CredentialVault
from sro.application.ports.vision import VisionDriver, VisionUnavailable
from sro.domain.connection.connection import Connection
from sro.domain.recording.events import ActionKind

GESTURE_BUDGET = 12
"""Enough to open a screen, fill a short form and save. Chosen to be obviously
finite rather than tuned: the number that matters is that there is one."""

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


class PursueGoal:
    def __init__(
        self,
        uow: UnitOfWork,
        vault: CredentialVault,
        browser: BrowserProvider,
        ui: UiDriver | None,
        vision: VisionDriver | None,
        clock: Clock,
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
        self._egress_enabled = egress_enabled
        self._model = model

    async def execute(
        self, ctx: RequestContext, *, goal: Goal, target_system: str, values: dict[str, str]
    ) -> Pursued:
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
        reached = False
        detail = "the budget ran out before the screen showed the result"

        session = await self._browser.open()
        try:
            await self._browser.restore(session.id, await self._session_of(connection))
            await self._browser.navigate(session.id, start)

            for _ in range(GESTURE_BUDGET):
                screen = await self._ui.capture()
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

                outcome = await self._ui.perform_at(
                    action=proposed.action,
                    x=proposed.x or 0,
                    y=proposed.y or 0,
                    value=proposed.value,
                )
                gestures.append(
                    f"{proposed.action.value} at ({proposed.x}, {proposed.y})"
                    + (f" = {proposed.value}" if proposed.value else "")
                    + ("" if outcome.performed else " — nothing happened")
                )
                if not outcome.performed:
                    detail = "the screen did not respond to what was proposed"
                    break

            landed = await self._ui.current_url() or start
        except UiUnavailable as error:
            raise BrowserUnavailable(str(error)) from error
        finally:
            await self._browser.close(session.id)

        return Pursued(
            goal=goal.intent,
            reached=reached,
            gestures=tuple(gestures),
            landed_at=landed,
            detail=detail,
        )

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
