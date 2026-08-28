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


def is_empty(value: object) -> bool:
    """Whether this leaf is a field somebody left alone.

    A form sends its whole record: what the operator skipped arrives as `null`,
    or as `""` from a text control that was never focused. Both are absence
    wearing the type the application chose for it.
    """
    return value is None or value == ""


def same_shape(a: JsonValue, b: JsonValue) -> bool:
    """Whether two bodies are the same request with different values in it.

    Stricter than it looks. Every key must be in both -- a key one run did not
    send is a different request, and the pair is refused. What is allowed is a
    leaf that is empty on one side: the same field, filled once and skipped
    once, which is the ordinary way two people fill one form.
    """
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same_shape(a[key], b[key]) for key in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same_shape(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, dict | list) or isinstance(b, dict | list):
        # A group emptied on one side is still one request with a different
        # value in it, so it is the same shape. Whether the *diff* can express
        # it is a separate question, answered no: `_diff_body` refuses the pair
        # rather than handing the group's absent form to each leaf inside it.
        # `is_empty` of a dict or list is always False, so this only fires when
        # the *other* side is the one left empty.
        return is_empty(a) or is_empty(b)
    return is_empty(a) or is_empty(b) or type(a) is type(b)
