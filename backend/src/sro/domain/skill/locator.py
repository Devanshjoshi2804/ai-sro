"""How to find a control again, tomorrow, on a page that has been re-rendered.

An element fingerprint records everything observed about a control at one
moment. A locator is the other half: a statement about which of those signals is
worth trusting later, ordered, so a driver tries the strongest first and can say
which one it fell back to.

The ordering is not cosmetic. Measured on this WMS: the accessibility tree
carries no `button` role on three of four screens and never carries the field's
payload key, while the DOM ids are assigned in render order -- `ext-gen4443` is
a different control after a reload. The component model is the only view that is
stable and the only one the application itself uses.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sro.domain.shared.errors import InvariantViolation
from sro.domain.skill.template import Template


class LocatorStrategy(StrEnum):
    COMPONENT = "component"
    """A query in the page's own component language, e.g. ExtJS
    ``rpFilterableViews rpFilterComboBox#filterComboBox``. Strongest where it
    exists: it is what the application's own code uses to find the control."""

    TEST_ID = "test_id"
    ROLE_AND_NAME = "role_and_name"
    """The accessible way. Correct when the roles are there, and this WMS shows
    how often they are not."""

    TEXT = "text"
    """Visible text. Fine for a menu item, dangerous for a grid cell whose text
    is the record being worked on -- so the text may be a template."""

    CSS_PATH = "css_path"
    """Last resort, kept because it is occasionally the only thing left."""


@dataclass(frozen=True, slots=True)
class ControlLocator:
    strategy: LocatorStrategy
    query: Template
    """Strategy-specific: a component query, a test id, a role/name pair joined
    by ``|``, a text, a CSS path. A template because a locator may name the very
    record the run is about -- clicking the row for *this* LPN."""

    within: str | None = None
    """Component query the match must sit inside. The same screen is often
    loaded several times over in this SPA and only one instance is visible."""

    visible_only: bool = True
    """A driver acting on a hidden control has found the wrong one. The SPA
    keeps every screen it has ever shown, so the hidden matches outnumber the
    real one."""

    def __post_init__(self) -> None:
        if not self.query.raw.strip():
            raise InvariantViolation(f"{self.strategy} locator needs a query")

    @property
    def placeholders(self) -> frozenset[str]:
        return self.query.placeholders

    def describe(self) -> str:
        inside = f" within {self.within}" if self.within else ""
        return f"{self.strategy}: {self.query.raw}{inside}"
