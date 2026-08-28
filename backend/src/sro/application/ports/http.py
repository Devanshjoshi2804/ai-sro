"""The call the executor makes. Deliberately narrow.

Nothing here follows redirects, retries, or reads a cookie jar. An executor that
quietly retried a `PUT` would double a warehouse adjustment, and one that kept a
cookie jar between runs would carry a session it was never given. Both are the
caller's decisions, made where they can be recorded.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status_code: int
    headers: Mapping[str, str]
    text: str

    @property
    def succeeded(self) -> bool:
        return 200 <= self.status_code < 300


class HttpCaller(Protocol):
    async def send(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: str | None = None,
        timeout_s: float = 30.0,
    ) -> HttpResponse:
        """Send exactly this, once."""
        ...


class TargetUnreachable(Exception):
    """The system did not answer. Not a ``DomainError``: the plan was fine.

    Distinguished from an error status on purpose. A 422 proves the call
    arrived; a timeout leaves a mutation in an unknown state, and only the
    caller knows whether that is safe to retry.
    """


class MalformedRequest(TargetUnreachable):
    """Nothing was sent, and the reason is this end rather than the far one.

    A URL a template rendered into something that is not a URL, a scheme no
    client speaks, a request the protocol will not frame. The system never had
    the chance to answer, but that is not a fact about the system: it is a fact
    about the skill, and a run that fails this way is evidence the recipe has
    drifted from what it was taught on.

    A subclass, so every caller that only wants "it did not answer" keeps
    working unchanged. Execution asks the narrower question in exactly one
    place -- where the difference decides whether the skill is marked down.
    """
