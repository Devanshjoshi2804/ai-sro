"""Connectors a tenant has connected, and the tools they offer.

The other half of `infrastructure/mcp/server.py`. That one hands this system's
skills to somebody else's agent; this one calls somebody else's tools from a
skill's own step -- which is what makes a mail step a call rather than a click,
and a click is the one thing that can never be clean.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from sro.domain.shared.identifiers import PrincipalId, TenantId


@dataclass(frozen=True, slots=True)
class ToolOffered:
    """One tool a connector says it has.

    Read when somebody maps a step onto it, so a person choosing is choosing
    from what the server actually offers rather than typing a name and finding
    out at run time.
    """

    name: str
    description: str = ""
    arguments: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ToolResult:
    """What a tool answered.

    ``text`` is the body an assertion is checked against, exactly as a network
    step's response body is. ``failed`` is the tool saying no, which is
    different from this system failing to ask -- the first is an answer and
    goes in the run record as one.
    """

    text: str
    failed: bool = False
    detail: str = ""


class ToolsUnavailable(Exception):
    """No connector by that name, or it will not answer.

    Its own exception rather than an empty result, because "the tool said no"
    and "there was nothing to ask" are different facts and the escalation table
    answers them differently.
    """

    code = "tools_unavailable"


class NotConnected(ToolsUnavailable):
    """This operator has not connected this server.

    A subclass rather than a bare `ToolsUnavailable` so a console can tell "you
    have not connected Gmail yet" -- which a person can fix in one click --
    from "the connector is down", which they cannot. Both are still "there was
    nothing to ask", which is why the escalation table needs no new entry.
    """

    code = "not_connected"


class ToolCaller(Protocol):
    """Somebody else's tools, called with THIS tenant's credential.

    Every method takes the tenant AND the operator, and that is the whole of
    the security property: a connector is reached with a bearer read from the
    vault under `connector_key`, so an operator with no grant cannot reach one
    and an operator with a grant reaches only their own mailbox.

    Per operator rather than per tenant because each reads their own mail. A
    key without the person in it would have one operator's inbox answering for
    everybody in the tenant -- the same bug one scope smaller, and worth saying
    because the first version of this change had exactly that.

    It was not always so. Until 2026-09-16 neither the port nor the adapter had
    a tenant on it and the bearer was one string in deployment config, so a
    skill run for any tenant reached the same connector holding the same
    person's Google grant. Nothing had noticed because nothing had called it:
    MCP was unreachable from a mined-workflow run, and the one path that did
    use it was a single-tenant deployment. This is the door shut before
    anything leaned on it.
    """

    @property
    def available(self) -> bool:
        """Whether this deployment has connectors configured at all.

        Asked before a mapping screen offers anything, so an operator is not
        invited to map a step onto a connector nobody set up."""
        ...

    async def list_tools(
        self, tenant_id: TenantId, principal_id: PrincipalId, server: str
    ) -> Sequence[ToolOffered]:
        """What this connector offers this operator, now. Raises `ToolsUnavailable`.

        Who first, and on every method, because a connector is reached with a
        credential and a credential belongs to one person. The port carried
        neither until 2026-09-16 and neither did the adapter, so every step of
        every tenant reached the same mailbox with the same grant.
        """
        ...

    async def call(
        self,
        tenant_id: TenantId,
        principal_id: PrincipalId,
        server: str,
        tool: str,
        arguments: Mapping[str, str],
    ) -> ToolResult:
        """Call it and return what it said. Raises `ToolsUnavailable`.

        No idempotency key here, deliberately. Whether this call may happen at
        all is decided before the port is reached -- a provider that promises
        to deduplicate is a promise this system cannot check, and the one call
        worth protecting is the one whose reply never arrived.
        """
        ...
