from __future__ import annotations

import re
from dataclasses import replace

from evals.model import Case
from sro.domain.execution.mail_job import addresses_in

_KEPT = re.compile(r"[a-z]+|(?:ges|wfl)_[0-9a-f]{32}")
_TOKEN = re.compile(r"[\w@.+-]+|[^\w@.+-]+")


def shape(value: str) -> str:
    return "".join(
        "A" if one.isupper() else "a" if one.isalpha() else "9" if one.isdigit() else one
        for one in value
    )


class _Shapes:
    def __init__(self) -> None:
        self.given: dict[str, str] = {}
        self.taken: dict[str, str] = {}

    def of(self, value: str) -> str:
        if value not in self.given:
            base = shape(value)
            name, n = base, 1
            while name in self.taken and self.taken[name] != value:
                n += 1
                name = f"{base}~{n}"
            self.given[value], self.taken[name] = name, value
        return self.given[value]

    def text(self, text: str) -> str:
        addresses = addresses_in([text])
        out = []
        for token in _TOKEN.findall(text):
            kept = _KEPT.fullmatch(token) and token.lower() not in addresses
            out.append(token if kept or not re.search(r"\w", token) else self.of(token))
        return "".join(out)

    def walk(self, value: object) -> object:
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, list):
            return [self.walk(one) for one in value]
        if isinstance(value, dict):
            return {
                k if _KEPT.fullmatch(str(k)) else self.text(str(k)): self.walk(v)
                for k, v in value.items()
            }
        return value


def redacted(case: Case) -> Case:
    shapes = _Shapes()
    return replace(
        case,
        input=shapes.walk(case.input),  # type: ignore[arg-type]
        expected=shapes.walk(case.expected),  # type: ignore[arg-type]
        answer=None if case.answer is None else shapes.walk(case.answer),  # type: ignore[arg-type]
    )
