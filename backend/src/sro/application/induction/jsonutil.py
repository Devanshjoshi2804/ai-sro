"""Minimal JSON Pointer (RFC 6901) support.

Three operations are all this codebase needs, so it is a few lines rather than a
dependency. Reach for ``jsonpointer`` if that stops being true.
"""

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
    """Yield ``(pointer, scalar)`` depth first. Containers are not yielded --
    "the object changed" is never actionable on its own."""
    if isinstance(value, dict):
        for key, child in value.items():
            yield from leaves(child, f"{prefix}/{escape(str(key))}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from leaves(child, f"{prefix}/{index}")
    else:
        yield prefix, value


def as_text(value: JsonValue) -> str:
    """One rendering of a JSON scalar, used by whoever writes an expectation and
    by whoever checks it.

    Python's ``str`` renders JSON ``true`` as ``"True"``. Induction wrote that
    into an assertion and the executor read the live response back as ``"true"``,
    so a run that did exactly the right thing reported a mismatch against
    itself. The rendering has to be the same rule on both sides, so it is one
    function.
    """
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
    """Mutate in place. Caller owns the copy."""
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


def structure(value: JsonValue) -> object:
    """Hashable shape of a document, ignoring scalar values.

    Two runs of one task share a shape. A different shape means the flows
    diverged, which is a re-record rather than a diff.
    """
    if isinstance(value, dict):
        return ("object", tuple(sorted((k, structure(v)) for k, v in value.items())))
    if isinstance(value, list):
        return ("array", tuple(structure(item) for item in value))
    return ("scalar", type(value).__name__)
