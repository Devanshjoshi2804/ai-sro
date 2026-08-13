"""Strings with ``$name`` placeholders. See docs/07-adr/004-diff-parameterisation.md."""

from __future__ import annotations

from dataclasses import dataclass
from string import Template as _StdTemplate


@dataclass(frozen=True, slots=True)
class Template:
    # `$name` rather than `{name}` because recorded payloads are JSON: a
    # brace syntax needs every captured body escaped, and one missed escape
    # turns a literal into a phantom parameter.
    raw: str

    @property
    def placeholders(self) -> frozenset[str]:
        return frozenset(_StdTemplate(self.raw).get_identifiers())

    @property
    def is_literal(self) -> bool:
        return not self.placeholders

    def render(self, values: dict[str, str]) -> str:
        """Substitute values. Raises ``KeyError`` on a missing one."""
        return _StdTemplate(self.raw).substitute(values)

    def __str__(self) -> str:
        return self.raw
