from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

JsonValue = Any


def escape(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def unescape(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def parse(pointer: str) -> list[str]:
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise ValueError(f"JSON Pointer must start with '/': {pointer!r}")
    return [unescape(token) for token in pointer[1:].split("/")]


def build(tokens: list[str]) -> str:
    return "".join(f"/{escape(token)}" for token in tokens)


def leaves(value: JsonValue, prefix: str = "") -> Iterator[tuple[str, JsonValue]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from leaves(child, f"{prefix}/{escape(str(key))}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from leaves(child, f"{prefix}/{index}")
    else:
        yield prefix, value


def as_text(value: JsonValue) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return value if isinstance(value, str) else json.dumps(value)


def get(document: JsonValue, pointer: str) -> JsonValue:
    current = document
    for token in parse(pointer):
        current = current[int(token)] if isinstance(current, list) else current[token]
    return current


def set_value(document: JsonValue, pointer: str, new_value: JsonValue) -> None:
    tokens = parse(pointer)
    if not tokens:
        raise ValueError("cannot replace the document root")
    parent = document
    for token in tokens[:-1]:
        parent = parent[int(token)] if isinstance(parent, list) else parent[token]
    last = tokens[-1]
    if isinstance(parent, list):
        parent[int(last)] = new_value
    else:
        parent[last] = new_value


def is_empty(value: object) -> bool:
    return value is None or value == ""


def same_shape(a: JsonValue, b: JsonValue) -> bool:
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same_shape(a[key], b[key]) for key in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same_shape(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, dict | list) or isinstance(b, dict | list):
        return is_empty(a) or is_empty(b)
    return is_empty(a) or is_empty(b) or type(a) is type(b)
