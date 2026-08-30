"""Connectors this tenant configured, and the tools they offer.

The other half of `infrastructure/mcp/server.py`. That one hands this system's
skills to somebody else's agent; this one calls somebody else's tools from a
skill's own step -- which is what makes a mail step a call rather than a click,
and a click is the one thing that can never be clean.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol


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


class ToolCaller(Protocol):
    @property
    def available(self) -> bool:
        """Whether this deployment has connectors configured at all.

        Asked before a mapping screen offers anything, so an operator is not
        invited to map a step onto a connector nobody set up."""
        ...

    async def list_tools(self, server: str) -> Sequence[ToolOffered]:
        """What this connector offers, now. Raises `ToolsUnavailable`."""
        ...

    async def call(self, server: str, tool: str, arguments: Mapping[str, str]) -> ToolResult:
        """Call it and return what it said. Raises `ToolsUnavailable`.

        No idempotency key here, deliberately. Whether this call may happen at
        all is decided before the port is reached -- a provider that promises
        to deduplicate is a promise this system cannot check, and the one call
        worth protecting is the one whose reply never arrived.
        """
        ...
