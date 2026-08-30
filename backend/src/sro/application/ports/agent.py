"""Driving the browser an operator is sitting in front of.

The extension is not a second executor. It implements the two ports execution
already has -- one gesture at a time, one request at a time -- so the promotion
ladder, the circuit breaker, blast radius, step dispositions and verdicts all
apply to a run performed in somebody's own Chrome exactly as they do to one
performed in a browser this deployment owns. ADR 009.

What is different is that this browser can close. A device that is not there is
``UiUnavailable`` or ``TargetUnreachable`` -- the failures execution already
knows how to record -- and never a silent fall back to a browser on the server,
which would drive the wrong Chrome under somebody else's session.
"""

from __future__ import annotations

from typing import Protocol

from sro.application.ports.http import HttpCaller
from sro.application.ports.ui import UiDriver
from sro.domain.shared.identifiers import DeviceId, TenantId


class AgentDrivers(Protocol):
    def ui(
        self,
        tenant_id: TenantId,
        device_id: DeviceId,
        origin: str | None = None,
        may_take_focus: bool = False,
    ) -> UiDriver:
        """A driver that performs its gestures in that device's browser.

        ``origin`` is the system the skill was taught on, so the browser can
        pick the tab that is on it. Without it the extension is guessing --
        the frontmost page, whatever that happens to be -- and a run that
        guesses wrong acts on somebody's email.

        ``may_take_focus`` is the trigger's decision about whether that tab may
        be brought to the front. It is never the browser's to make: the
        extension refuses rather than deciding for itself, and this is what
        tells it the operator asked for this and is watching.
        """
        ...

    def http(self, tenant_id: TenantId, device_id: DeviceId) -> HttpCaller:
        """A caller that sends from that device's page context.

        Which is the point of it: the request carries the operator's own
        session, so a skill can be replayed against a system this deployment
        holds no credentials for.
        """
        ...

    async def online(self, tenant_id: TenantId) -> tuple[DeviceId, ...]:
        """Devices of this tenant with a channel open right now."""
        ...

    async def held_for(self, tenant_id: TenantId, device_id: DeviceId) -> float | None:
        """Seconds this browser has asked to be left alone, or `None`.

        The operator is typing. The extension says so unprompted and the backend
        holds its commands for a moment, and until now that politeness happened
        entirely out of sight -- a run simply appeared to stall. It is the one
        state that shows the machine deferring to the person, which is worth
        more on screen than most of what the run reports.

        Absence is not a claim that nobody is typing: a tenant with capture
        switched off has a channel that never says it is busy.
        """
        ...


class DeviceUnreachable(Exception):
    """No channel to that browser. Not a ``DomainError``: the plan was fine.

    A laptop was closed, or the extension was never connected. The answer is a
    person, or a later run -- never another browser.
    """
