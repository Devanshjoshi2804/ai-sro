from __future__ import annotations

from dataclasses import dataclass
from string import Template as _StdTemplate


@dataclass(frozen=True, slots=True)
class Template:
    raw: str

    @property
    def placeholders(self) -> frozenset[str]:
        return frozenset(_StdTemplate(self.raw).get_identifiers())

    @property
    def is_literal(self) -> bool:
        return not self.placeholders

    def render(self, values: dict[str, str]) -> str:
        return _StdTemplate(self.raw).substitute(values)

    def __str__(self) -> str:
        return self.raw
