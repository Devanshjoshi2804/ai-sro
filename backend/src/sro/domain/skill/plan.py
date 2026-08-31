"""The two ways to perform a step. See docs/07-adr/005-dual-recipe.md."""

from __future__ import annotations

from dataclasses import dataclass, field

from sro.domain.recording.element import ElementFingerprint
from sro.domain.recording.events import ActionKind
from sro.domain.recording.sensitivity import Sensitivity
from sro.domain.shared.errors import InvariantViolation
from sro.domain.skill.locator import ControlLocator
from sro.domain.skill.template import Template

_ACTIONS_NEEDING_TARGET = frozenset({"click", "type", "select", "upload"})


@dataclass(frozen=True, slots=True)
class HeaderPlan:
    """One header the call carried, and how to produce it again.

    Every observed header is recorded. What differs is where the value comes
    from: a literal template for semantic headers, a vault reference for
    credentials, a fresh mint for CSRF and trace ids.
    """

    name: str
    sensitivity: Sensitivity
    value: Template | None = None
    """Literal or templated value. ``None`` when the value is resolved at run time."""

    credential_ref: str | None = None
    """Vault key for AUTH and SESSION headers. Resolved by the executor, so the
    real credential is used without being copied into a shared artifact."""

    mint: bool = False
    """True for CSRF and trace headers: the captured value is stale by design and
    a fresh one must be obtained from the live session."""

    managed: bool = False
    """True when the HTTP client owns the value: Host, Content-Length, Referer,
    Origin, the sec-* family. The header is recorded because it was observed,
    but the captured value describes the browser that made the demonstration,
    not the call. Replaying a stale Referer is misleading; replaying a captured
    Content-Length is actively harmful."""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvariantViolation("HeaderPlan requires a name")
        if (
            self.value is None
            and self.credential_ref is None
            and not self.mint
            and not self.managed
        ):
            raise InvariantViolation(
                f"header {self.name!r} has no value, no credential reference and no "
                "mint strategy; the executor could not reproduce it"
            )
        if self.managed and self.value is not None:
            raise InvariantViolation(
                f"header {self.name!r} is client-managed, so carrying a captured "
                "value would invite an executor to replay it"
            )


@dataclass(frozen=True, slots=True)
class NetworkPlan:
    """Replay of the call the demonstrated action produced."""

    method: str
    url: Template
    headers: tuple[HeaderPlan, ...] = ()
    body: Template | None = None
    body_blob_uri: str | None = None
    """Set when the captured body was too large to inline. Still replayable."""

    expected_status: int | None = None
    content_type: str | None = None

    replayable: bool = True
    """False when a template alone cannot reproduce the call -- a client-minted
    signature, a nonce, a websocket frame. Kept as documentation of the step."""

    unreplayable_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.method.strip():
            raise InvariantViolation("NetworkPlan requires an HTTP method")
        if not self.replayable and not self.unreplayable_reason:
            raise InvariantViolation(
                "a plan marked unreplayable must say why; an unexplained dead end "
                "is indistinguishable from a capture bug"
            )

    @property
    def is_mutation(self) -> bool:
        """Whether replaying this changes the target system.

        The same question `CapturedRequest.is_mutation` answers about the call
        that was recorded, spelled out by hand in eight places before this --
        each of them a chance for one of them to disagree about which methods
        are safe.
        """
        return self.method.upper() not in {"GET", "HEAD", "OPTIONS"}

    @property
    def placeholders(self) -> frozenset[str]:
        names = set(self.url.placeholders)
        for header in self.headers:
            if header.value is not None:
                names |= header.value.placeholders
        if self.body is not None:
            names |= self.body.placeholders
        return frozenset(names)

    @property
    def required_credentials(self) -> frozenset[str]:
        """Vault keys the executor must resolve before this call can be made."""
        return frozenset(h.credential_ref for h in self.headers if h.credential_ref)


@dataclass(frozen=True, slots=True)
class ToolPlan:
    """Perform this step by calling a tool on a connector the tenant configured.

    The one kind of plan no demonstration produces. Induction reads recordings
    and a recording holds gestures and the calls they made, so a tool step is
    always somebody's decision: this click on Send is `send_message` on that
    server. Recorded as a decision with a name on it, never inferred -- which
    is ADR 004's rule about identity applied to the thing performing the step
    rather than to the values it carries.
    """

    server: str
    """The connector, by the name the tenant gave it. Resolved to a URL and a
    credential the same way `target_system` is: this is the vocabulary a
    reviewer reads, and the address is configuration."""

    tool: str
    arguments: tuple[tuple[str, Template], ...] = ()
    """Argument name to what goes in it, in the order the mapping named them.
    A tuple of pairs rather than a mapping so two versions of one skill are
    comparable and a document round-trips byte for byte."""

    writes: bool = False
    """Whether calling this changes something outside this system.

    Said by whoever mapped the step, because nothing else can say it. MCP tools
    do not declare it, a name is not a promise, and a system that guessed would
    guess wrong in the direction of sending a mail nobody approved. It is what
    `changes_the_system` reads, so it decides whether a run may send this at
    all below the assisted rung.
    """

    def __post_init__(self) -> None:
        if not self.server.strip():
            raise InvariantViolation("a tool plan names the connector it calls")
        if not self.tool.strip():
            raise InvariantViolation("a tool plan names the tool it calls")
        seen = [name for name, _ in self.arguments]
        if len(seen) != len(set(seen)):
            raise InvariantViolation("a tool plan gives each argument once")

    @property
    def placeholders(self) -> frozenset[str]:
        found: frozenset[str] = frozenset()
        for _, value in self.arguments:
            found |= value.placeholders
        return found


@dataclass(frozen=True, slots=True)
class UiPlan:
    """Drive the interface the way the human did."""

    action: ActionKind
    target: ElementFingerprint | None = None
    value: Template | None = None
    wait_for: ElementFingerprint | None = field(default=None)
    target_path: str | None = None
    """Ancestry of the target within the AX graph, e.g.
    ``dialog “Release” > form > button “Confirm”``. Disambiguates the third Save
    button on a page, which an accessible name alone cannot."""

    locators: tuple[ControlLocator, ...] = ()
    """How to find the control again, strongest strategy first.

    Separate from ``target`` on purpose: the fingerprint is evidence about one
    moment, and a locator is a decision about what will still be true later.
    Empty means the demonstration produced nothing worth replaying by -- which
    is a fact about that step, not a reason to guess."""

    def __post_init__(self) -> None:
        if self.action in _ACTIONS_NEEDING_TARGET and self.target is None:
            raise InvariantViolation(f"UiPlan for {self.action} requires a target element")

    @property
    def replayable(self) -> bool:
        """Whether a driver could act on this step at all."""
        return self.action not in _ACTIONS_NEEDING_TARGET or bool(self.locators)

    @property
    def placeholders(self) -> frozenset[str]:
        names = self.value.placeholders if self.value is not None else frozenset()
        for locator in self.locators:
            names |= locator.placeholders
        return frozenset(names)
