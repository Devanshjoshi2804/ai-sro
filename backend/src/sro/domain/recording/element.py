from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from sro.domain.shared.errors import InvariantViolation


@dataclass(frozen=True, slots=True)
class Bounds:
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True, slots=True)
class ComponentIdentity:
    framework: str
    query: str
    xtype: str | None = None
    item_id: str | None = None
    name: str | None = None
    field_label: str | None = None
    text: str | None = None
    required: bool | None = None

    chain: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.framework.strip() or not self.query.strip():
            raise InvariantViolation("ComponentIdentity needs a framework and a query")


@dataclass(frozen=True, slots=True)
class ElementFingerprint:
    node_id: str | None = None

    parent_id: str | None = None
    child_ids: tuple[str, ...] = ()

    role: str | None = None
    accessible_name: str | None = None
    description: str | None = None
    value: str | None = None
    text: str | None = None
    test_id: str | None = None
    css_path: str | None = None
    xpath: str | None = None
    required: bool | None = None

    tag: str | None = None

    states: frozenset[str] = frozenset()

    component: ComponentIdentity | None = None

    bounds: Bounds | None = None
    attributes: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not any(
            (self.role, self.accessible_name, self.text, self.test_id, self.css_path, self.node_id)
        ):
            raise InvariantViolation(
                "ElementFingerprint needs at least one identifying signal; "
                "structural noise alone cannot be healed or replayed"
            )
        object.__setattr__(self, "attributes", MappingProxyType(dict(self.attributes)))

    @property
    def is_interactive(self) -> bool:
        return self.role in {
            "button",
            "link",
            "textbox",
            "combobox",
            "checkbox",
            "radio",
            "menuitem",
            "tab",
            "switch",
            "searchbox",
            "spinbutton",
            "slider",
        }

    def describe(self) -> str:
        if self.accessible_name and self.role:
            return f"{self.role} “{self.accessible_name}”"
        return (
            self.accessible_name
            or self.text
            or self.test_id
            or self.css_path
            or self.role
            or "<element>"
        )
