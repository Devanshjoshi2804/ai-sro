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
    def ui(self, tenant_id: TenantId, device_id: DeviceId) -> UiDriver:
        """A driver that performs its gestures in that device's browser."""
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


class DeviceUnreachable(Exception):
    """No channel to that browser. Not a ``DomainError``: the plan was fine.

    A laptop was closed, or the extension was never connected. The answer is a
    person, or a later run -- never another browser.
    """
