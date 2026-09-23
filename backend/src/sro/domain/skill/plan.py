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
    name: str
    sensitivity: Sensitivity
    value: Template | None = None

    credential_ref: str | None = None

    mint: bool = False

    managed: bool = False

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
    method: str
    url: Template
    headers: tuple[HeaderPlan, ...] = ()
    body: Template | None = None
    body_blob_uri: str | None = None

    expected_status: int | None = None
    content_type: str | None = None

    replayable: bool = True

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
        return frozenset(h.credential_ref for h in self.headers if h.credential_ref)


@dataclass(frozen=True, slots=True)
class ToolPlan:
    server: str

    tool: str
    arguments: tuple[tuple[str, Template], ...] = ()

    writes: bool = False

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
    action: ActionKind
    target: ElementFingerprint | None = None
    value: Template | None = None
    wait_for: ElementFingerprint | None = field(default=None)
    target_path: str | None = None

    locators: tuple[ControlLocator, ...] = ()

    def __post_init__(self) -> None:
        if self.action in _ACTIONS_NEEDING_TARGET and self.target is None:
            raise InvariantViolation(f"UiPlan for {self.action} requires a target element")

    @property
    def replayable(self) -> bool:
        return self.action not in _ACTIONS_NEEDING_TARGET or bool(self.locators)

    @property
    def placeholders(self) -> frozenset[str]:
        names = self.value.placeholders if self.value is not None else frozenset()
        for locator in self.locators:
            names |= locator.placeholders
        return frozenset(names)
