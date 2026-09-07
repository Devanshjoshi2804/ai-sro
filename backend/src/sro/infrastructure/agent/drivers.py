"""The two ports execution already has, performed in somebody else's browser.

Nothing here decides anything. A gesture is proposed by the same code that
proposes it for a browser on the server, and what comes back is the same
``UiOutcome`` or ``HttpResponse``. The only new fact is that this browser can
close, and that arrives as the unavailability execution already records.
"""

from __future__ import annotations

import base64
from collections.abc import Mapping

from sro.application.ports.agent import AgentDrivers, DeviceUnreachable
from sro.application.ports.http import HttpCaller, HttpResponse, TargetUnreachable
from sro.application.ports.ui import ResolvedLocator, UiDriver, UiOutcome, UiUnavailable
from sro.application.ports.vision import Screen
from sro.domain.recording.events import ActionKind
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.skill.locator import LocatorStrategy
from sro.infrastructure.agent.sockets import Answer, DeviceSockets

_NO_BROWSER = (
    "timeout",
    "no_tab_for_system",
    "no_tab_for_origin",
    "focus_not_permitted",
    "aborted",
)
"""Failures that mean there was no browser to act in, rather than facts about
the page. A page whose control moved is a skill that has drifted; a laptop that
closed is not, and counting the second as the first would demote a skill for
somebody going to lunch."""


class RemoteAgents(AgentDrivers):
    def __init__(self, sockets: DeviceSockets) -> None:
        self._sockets = sockets

    def ui(
        self,
        tenant_id: TenantId,
        device_id: DeviceId,
        origin: str | None = None,
        may_take_focus: bool = False,
        starts_on: str | None = None,
        doing: str = "",
        step: int | None = None,
        of: int | None = None,
    ) -> UiDriver:
        return RemoteUiDriver(
            self._sockets,
            tenant_id,
            device_id,
            origin,
            may_take_focus,
            starts_on,
            doing,
            step,
            of,
        )

    def http(self, tenant_id: TenantId, device_id: DeviceId) -> HttpCaller:
        return RemoteHttpCaller(self._sockets, tenant_id, device_id)

    async def online(self, tenant_id: TenantId) -> tuple[DeviceId, ...]:
        return self._sockets.online(tenant_id)

    def drop(self, tenant_id: TenantId, device_id: DeviceId) -> bool:
        return self._sockets.drop(tenant_id, device_id)

    async def held_for(self, tenant_id: TenantId, device_id: DeviceId) -> float | None:
        return self._sockets.held_for(tenant_id, device_id)


class RemoteUiDriver(UiDriver):
    def __init__(
        self,
        sockets: DeviceSockets,
        tenant_id: TenantId,
        device_id: DeviceId,
        origin: str | None = None,
        may_take_focus: bool = False,
        starts_on: str | None = None,
        doing: str = "",
        step: int | None = None,
        of: int | None = None,
    ) -> None:
        self._sockets = sockets
        self._tenant_id = tenant_id
        self._device_id = device_id
        self._origin = origin
        self._may_take_focus = may_take_focus
        self._starts_on = starts_on
        self._doing = doing
        self._step = step
        self._of = of

    async def perform(
        self,
        *,
        action: ActionKind,
        locators: tuple[ResolvedLocator, ...],
        value: str | None = None,
    ) -> UiOutcome:
        answer = await self._ask(
            "ui.perform",
            {
                "action": action.value,
                "value": value,
                "locators": [
                    {
                        "strategy": locator.strategy.value,
                        "query": locator.query,
                        "within": locator.within,
                        "visible_only": locator.visible_only,
                    }
                    for locator in locators
                ],
            },
        )
        return _outcome(answer)

    async def perform_at(
        self, *, action: ActionKind, x: int, y: int, value: str | None = None
    ) -> UiOutcome:
        answer = await self._ask(
            "ui.perform_at", {"action": action.value, "x": x, "y": y, "value": value}
        )
        return _outcome(answer)

    async def current_url(self) -> str | None:
        answer = await self._ask("ui.url", {})
        url = answer.result.get("url") if answer.ok else None
        return str(url) if url else None

    async def capture(self) -> Screen:
        """Inline, not an artifact: this picture is being looked at now, and a
        round trip through object storage to read back what we just asked for
        would be two more places for it to be delayed or lost."""
        answer = await self._ask("screenshot", {"inline": True}, timeout_s=30.0)
        if not answer.ok:
            raise UiUnavailable(answer.detail or "the browser did not send a screen")
        encoded = str(answer.result.get("image_base64", ""))
        if not encoded:
            raise UiUnavailable("the browser answered with no image")
        return Screen(
            image=base64.b64decode(encoded),
            mime_type=str(answer.result.get("mime_type", "image/png")),
            width=_int(answer.result.get("width")),
            height=_int(answer.result.get("height")),
            text_digest=str(answer.result.get("text_digest", "")),
        )

    def for_session(self, debugger_url: str) -> UiDriver:
        """Itself. A device is one browser and there is no other to point at;
        the deployment does not own it and cannot open a second."""
        return self

    async def _ask(
        self, kind: str, payload: Mapping[str, object], *, timeout_s: float | None = None
    ) -> Answer:
        # Named on every command rather than once at connect: a device holds one
        # channel and may be asked to act for several runs against different
        # systems, so which page a command belongs to is a fact about the
        # command.
        if self._origin:
            payload = {**payload, "origin": self._origin}
        # Sent only when it is true. A payload carrying `allow_focus: false`
        # says the same thing as one that omits it, and the omission is the
        # safer default to have in a protocol: a browser reading a field it
        # does not understand takes nobody's screen.
        if self._may_take_focus:
            payload = {**payload, "allow_focus": True}
        # The screen the task was demonstrated on. Without it a run could only
        # be performed by an operator who had already navigated there, and one
        # who had not got a page of `control_not_found` that said nothing about
        # being on the wrong screen.
        if self._starts_on:
            payload = {**payload, "starts_on": self._starts_on}
        # What the page says about itself while this is happening. The operator
        # whose browser is being driven is watching the page, not the panel,
        # and "AI-SRO is doing X, step 4 of 13" is the difference between an
        # application behaving oddly and a task somebody can see and stop.
        if self._doing:
            payload = {**payload, "skill": self._doing}
        if self._step is not None:
            payload = {**payload, "step": self._step}
        if self._of is not None:
            payload = {**payload, "of": self._of}
        try:
            return await self._sockets.send(
                self._tenant_id, self._device_id, kind=kind, payload=payload, timeout_s=timeout_s
            )
        except DeviceUnreachable as gone:
            # Never a fall back to a browser on the server: that one is signed
            # in as somebody else, on a screen nobody demonstrated.
            raise UiUnavailable(str(gone)) from gone


class RemoteHttpCaller(HttpCaller):
    """Sends from the operator's own page context, so the call carries their
    session. It is why a skill can be replayed against a system this deployment
    holds no credentials for at all."""

    def __init__(self, sockets: DeviceSockets, tenant_id: TenantId, device_id: DeviceId) -> None:
        self._sockets = sockets
        self._tenant_id = tenant_id
        self._device_id = device_id

    async def send(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: str | None = None,
        timeout_s: float = 30.0,
    ) -> HttpResponse:
        try:
            answer = await self._sockets.send(
                self._tenant_id,
                self._device_id,
                kind="http.send",
                payload={"method": method, "url": url, "headers": dict(headers), "body": body},
                timeout_s=timeout_s,
            )
        except DeviceUnreachable as gone:
            raise TargetUnreachable(str(gone)) from gone

        if not answer.ok:
            # Including the timeout: a mutation whose answer never came back is
            # in an unknown state, and TargetUnreachable is how the executor is
            # told not to retry it without looking.
            raise TargetUnreachable(answer.detail or "the browser did not send the request")

        raw = answer.result.get("headers")
        return HttpResponse(
            status_code=_int(answer.result.get("status")),
            headers={str(k): str(v) for k, v in (raw or {}).items()}
            if isinstance(raw, Mapping)
            else {},
            text=str(answer.result.get("body", "")),
        )


def _outcome(answer: Answer) -> UiOutcome:
    if not answer.ok and answer.error_kind in _NO_BROWSER:
        raise UiUnavailable(answer.detail or "the browser could not be driven")
    if not answer.ok:
        return UiOutcome(performed=False, detail=answer.detail or "control not found")

    matched = answer.result.get("matched_by")
    return UiOutcome(
        performed=bool(answer.result.get("performed")),
        matched_by=_locator(matched),
        candidates=_int(answer.result.get("candidates")),
        detail=str(answer.result["detail"]) if answer.result.get("detail") else None,
    )


def _locator(value: object) -> LocatorStrategy | None:
    """Which of the five known strategies matched, or none.

    An operator's extension is a different build than this deployment's own
    code, unlike the local Playwright driver which only ever produces a
    strategy it constructed itself -- version drift here is a fact about the
    reply, not a reason a whole run's outcome should raise instead of just
    losing this one diagnostic field.
    """
    if not value:
        return None
    try:
        return LocatorStrategy(str(value))
    except ValueError:
        return None


def _int(value: object) -> int:
    """JSON from a browser, so a number may arrive as one, as a float, or as
    the string somebody's template produced."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    return 0
