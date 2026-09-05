"""Complete record of one network exchange. See docs/11-capture-completeness.md."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType

from sro.domain.recording.background import is_background_traffic
from sro.domain.shared.errors import InvariantViolation


class InitiatorKind(StrEnum):
    """Why the browser made this call. The 'why' half of the capture."""

    PARSER = "parser"
    SCRIPT = "script"
    PRELOAD = "preload"
    SIGNED_EXCHANGE = "signed_exchange"
    REDIRECT = "redirect"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class StackFrame:
    function: str
    url: str
    line: int
    column: int


@dataclass(frozen=True, slots=True)
class Initiator:
    """CDP initiator information.

    The JS stack is what turns "a click and then some requests happened" into
    "this handler issued this call", which is how a step's causality survives
    into the recipe.
    """

    kind: InitiatorKind
    url: str | None = None
    line: int | None = None
    stack: tuple[StackFrame, ...] = ()
    parent_request_id: str | None = None
    """Set for redirects and for calls chained from another request."""


@dataclass(frozen=True, slots=True)
class ResourceTiming:
    dns_ms: float | None = None
    connect_ms: float | None = None
    tls_ms: float | None = None
    send_ms: float | None = None
    wait_ms: float | None = None
    receive_ms: float | None = None


@dataclass(frozen=True, slots=True)
class Cookie:
    name: str
    value: str
    domain: str
    path: str = "/"
    secure: bool = False
    http_only: bool = False
    same_site: str | None = None
    expires: datetime | None = None
    session: bool = True


@dataclass(frozen=True, slots=True)
class Body:
    """A request or response payload.

    Payloads over the inline threshold are written to object storage and the
    ``blob_uri`` is kept. Nothing is truncated away -- see
    docs/11-capture-completeness.md.
    """

    text: str | None = None
    blob_uri: str | None = None
    size_bytes: int = 0
    mime_type: str | None = None
    encoding: str | None = None
    """``base64`` when the payload is binary."""

    redacted_fields: tuple[str, ...] = ()
    """Fields whose values were replaced before the body was ever stored.

    Only credentials, matched by field name. Recorded so a reviewer can see that
    something was removed and what it was called -- a silent redaction is
    indistinguishable from a capture bug.
    """

    def __post_init__(self) -> None:
        if self.text is None and self.blob_uri is None and self.size_bytes > 0:
            raise InvariantViolation(
                "a non-empty Body must be inline or point at a blob; "
                "capture never discards a payload"
            )


@dataclass(frozen=True, slots=True)
class RedirectHop:
    url: str
    status: int
    location: str | None = None


@dataclass(frozen=True)
class CapturedRequest:
    """One complete exchange: what was sent, what came back, and why it happened."""

    request_id: str
    method: str
    url: str
    resource_type: str
    started_at: datetime

    request_headers: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    request_body: Body | None = None
    cookies_sent: tuple[Cookie, ...] = ()

    status: int | None = None
    status_text: str | None = None
    response_headers: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    response_body: Body | None = None
    cookies_set: tuple[Cookie, ...] = ()

    initiator: Initiator | None = None
    redirect_chain: tuple[RedirectHop, ...] = ()
    timing: ResourceTiming | None = None
    duration_ms: int | None = None

    protocol: str | None = None
    remote_address: str | None = None
    from_cache: bool = False
    failure_reason: str | None = None
    blocked_reason: str | None = None

    def __post_init__(self) -> None:
        if self.started_at.tzinfo is None:
            raise InvariantViolation("CapturedRequest.started_at must be timezone-aware")
        if not self.method.strip() or not self.url.strip():
            raise InvariantViolation("CapturedRequest needs a method and a url")
        object.__setattr__(self, "request_headers", MappingProxyType(dict(self.request_headers)))
        object.__setattr__(self, "response_headers", MappingProxyType(dict(self.response_headers)))

    @property
    def succeeded(self) -> bool:
        return self.status is not None and 200 <= self.status < 300

    @property
    def failed(self) -> bool:
        return self.failure_reason is not None or self.blocked_reason is not None

    @property
    def is_mutation(self) -> bool:
        return self.method.upper() not in {"GET", "HEAD", "OPTIONS"}

    @property
    def request_text(self) -> str | None:
        return self.request_body.text if self.request_body else None

    @property
    def response_text(self) -> str | None:
        return self.response_body.text if self.response_body else None

    def header(self, name: str) -> str | None:
        """Case-insensitive lookup. HTTP/2 lowercases; HTTP/1.1 does not."""
        target = name.lower()
        for key, value in self.request_headers.items():
            if key.lower() == target:
                return value
        return None


def primary_of(requests: Sequence[CapturedRequest]) -> CapturedRequest | None:
    """The call a gesture is about, out of the analytics and prefetch noise.

    Preference order: a successful mutation whose initiator is a script (the
    click handler), then any successful mutation, then any success, then the
    first call at all. Script-initiated is the strongest signal available -- it
    is the one the human's click actually caused. A source with no initiator
    information degrades to the second rung rather than losing the ranking.

    Background traffic is excluded outright rather than ranked last. A
    keep-alive fires on a timer, so it lands on whichever step happens to be
    open; letting it stand as a step's primary call makes two runs of one task
    look like they diverged, and induction refuses the pair. The evidence keeps
    it -- this is about which call the step is *about*.

    A function rather than only a property on ActionFrame, because a second
    source of captured requests now needs the identical rule and two copies of
    it would be two rules the day one of them is edited.
    """
    caused = tuple(request for request in requests if not is_background_traffic(request.url))
    if not caused:
        return None

    def rank(request: CapturedRequest) -> int:
        initiator = request.initiator
        script = initiator is not None and initiator.kind is InitiatorKind.SCRIPT
        if request.succeeded and request.is_mutation and script:
            return 0
        if request.succeeded and request.is_mutation:
            return 1
        if request.succeeded:
            return 2
        return 3

    def order(request: CapturedRequest) -> tuple[int, str, float]:
        # Path before time on purpose. One gesture on a grid screen fires
        # several reads at once, and which of them starts first is a race: the
        # same demonstration twice picked `inventoryItems` in one run and
        # `inventoryLocations` in the other, and the diff read that as two
        # different steps. Ranking by path makes the choice a property of what
        # the step did rather than of how the network went that day.
        return (rank(request), request.url.split("?", 1)[0], request.started_at.timestamp())

    best: CapturedRequest = min(caused, key=order)
    return best
