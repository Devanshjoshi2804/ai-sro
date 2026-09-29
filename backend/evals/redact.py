from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import replace

from evals.model import Case

_ID = re.compile(r"(?:ges|wfl|pas)_[0-9a-f]{32}")
_URL = re.compile(r"[a-z][a-z0-9+.-]*://[^\s\"'<>]+", re.I)
_TOKEN = re.compile(r"[\w@.+-]+|[^\w@.+-]+")
_PART = re.compile(r"\w+")
_WORD = re.compile(r"[a-z]+")
_VALUE_KEYS = frozenset(
    {"value", "values", "seen_values", "seen", "options", "system", "systems", "host"}
    | {"tenant", "query"}
    | {"shape_key", "body_keys", "response_keys"}
)
_URL_KEYS = frozenset({"url", "path", "page_url", "frame_url"})

On = Callable[[str, str], str]


def shape(value: str) -> str:
    return "".join(
        "A" if one.isupper() else "a" if one.isalpha() else "9" if one.isdigit() else one
        for one in value
    )


def _child(key: str, role: str) -> str:
    if role in ("crossings", "labels"):
        return "value"
    if role != "prose":
        return role
    return "url" if key in _URL_KEYS else "value" if key in _VALUE_KEYS else "prose"


def _key(key: str, role: str, on: On) -> str:
    if role == "crossings":
        return on(key, "value")
    return on(key, "prose") if role == "labels" else key


def _visit(value: object, role: str, on: On) -> object:
    if isinstance(value, str):
        return on(value, role)
    if isinstance(value, list):
        return [_visit(one, role, on) for one in value]
    if isinstance(value, dict):
        return {_key(k, role, on): _visit(v, _child(k, role), on) for k, v in value.items()}
    return value


class _Shapes:
    def __init__(self, tenant: str) -> None:
        self.secret = {tenant.lower()} - {""}
        self.given: dict[str, str] = {}
        self.taken: dict[str, str] = {}

    def of(self, value: str) -> str:
        if _ID.fullmatch(value) or not re.search(r"\w", value):
            return value
        if value not in self.given:
            base = shape(value)
            name, n = base, 1
            while name in self.taken and self.taken[name] != value:
                n += 1
                name = f"{base}~{n}"
            self.given[value], self.taken[name] = name, value
        return self.given[value]

    def learn(self, text: str, role: str) -> str:
        found = _PART.findall(text) if role != "prose" else []
        found += [one for url in _URL.findall(text) for one in _PART.findall(url)]
        self.secret |= {one.lower() for one in found}
        return text

    def parts(self, text: str) -> str:
        return _PART.sub(lambda m: self.of(m.group()), text)

    def url(self, text: str) -> str:
        scheme, _, rest = text.partition("://")
        return f"{scheme}://{self.parts(rest)}" if rest else self.parts(text)

    def words(self, text: str) -> str:
        return "".join(
            token
            if _ID.fullmatch(token) or (_WORD.fullmatch(token) and token not in self.secret)
            else self.of(token)
            for token in _TOKEN.findall(text)
        )

    def prose(self, text: str) -> str:
        out, at = [], 0
        for found in _URL.finditer(text):
            out += [self.words(text[at : found.start()]), self.url(found.group())]
            at = found.end()
        return "".join([*out, self.words(text[at:])])

    def shaped(self, text: str, role: str) -> str:
        if role == "prose":
            return self.prose(text)
        if role == "url" or _URL.fullmatch(text):
            return self.url(text)
        return self.of(text)


def _roots(case: Case) -> dict[str, tuple[object, str]]:
    values = case.expected.get("values")
    return {
        "input": ({k: v for k, v in case.input.items() if k != "crossings"}, "prose"),
        "crossings": (case.input.get("crossings", {}), "crossings"),
        "expected": ({k: v for k, v in case.expected.items() if k != "values"}, "prose"),
        "values": (values, "labels" if isinstance(values, dict) else "value"),
        "answer": (case.answer, "prose"),
    }


def redacted(case: Case, *, tenant: str = "") -> Case:
    shapes = _Shapes(tenant)
    for value, role in _roots(case).values():
        _visit(value, role, shapes.learn)
    done = {
        name: _visit(value, role, shapes.shaped) for name, (value, role) in _roots(case).items()
    }
    crossings = {"crossings": done["crossings"]} if "crossings" in case.input else {}
    values = {"values": done["values"]} if "values" in case.expected else {}
    return replace(
        case,
        input=done["input"] | crossings,  # type: ignore[operator]
        expected=done["expected"] | values,  # type: ignore[operator]
        answer=done["answer"],  # type: ignore[arg-type]
    )
