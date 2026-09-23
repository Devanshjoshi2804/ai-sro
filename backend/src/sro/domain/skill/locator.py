from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sro.domain.shared.errors import InvariantViolation
from sro.domain.skill.template import Template


class LocatorStrategy(StrEnum):
    COMPONENT = "component"

    TEST_ID = "test_id"
    ROLE_AND_NAME = "role_and_name"

    TEXT = "text"

    CSS_PATH = "css_path"


@dataclass(frozen=True, slots=True)
class ControlLocator:
    strategy: LocatorStrategy
    query: Template

    within: str | None = None

    visible_only: bool = True

    def __post_init__(self) -> None:
        if not self.query.raw.strip():
            raise InvariantViolation(f"{self.strategy} locator needs a query")

    @property
    def placeholders(self) -> frozenset[str]:
        return self.query.placeholders

    def describe(self) -> str:
        inside = f" within {self.within}" if self.within else ""
        return f"{self.strategy}: {self.query.raw}{inside}"
