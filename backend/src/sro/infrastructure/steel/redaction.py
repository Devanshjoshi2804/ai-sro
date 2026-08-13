"""Credential removal, at the point of capture.

Everything a demonstration does is evidence and is kept verbatim -- with one
exception. A password is not evidence of what happened; it is a key to the
customer's system, and keeping it would turn the evidence store into a
credential store with none of the handling that implies.

So credentials are removed here, before a body is ever written, rather than
filtered on the way out. Matched by field name, because a name is a decision the
target system already made; guessing from values would redact real business
data. What is kept is the field name, so a reviewer sees what was removed.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qsl, urlencode

from sro.domain.recording.sensitivity import is_secret_field

REDACTED = "«redacted»"


def redact_body(text: str, *, content_type: str | None) -> tuple[str, tuple[str, ...]]:
    """Return the body with credential values removed, and their field names."""
    kind = (content_type or "").lower()
    if "json" in kind or text.lstrip().startswith(("{", "[")):
        return _redact_json(text)
    if "x-www-form-urlencoded" in kind or ("=" in text and "\n" not in text):
        return _redact_form(text)
    return text, ()


def _redact_json(text: str) -> tuple[str, tuple[str, ...]]:
    try:
        document = json.loads(text)
    except ValueError:
        return text, ()

    removed: list[str] = []

    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            cleaned: dict[str, Any] = {}
            for key, value in node.items():
                if is_secret_field(str(key)) and _scalar(value):
                    removed.append(str(key))
                    cleaned[key] = REDACTED
                else:
                    cleaned[key] = walk(value)
            return cleaned
        if isinstance(node, list):
            return [walk(item) for item in node]
        return node

    cleaned_document = walk(document)
    return (json.dumps(cleaned_document) if removed else text), tuple(dict.fromkeys(removed))


def _scalar(value: Any) -> bool:
    return not isinstance(value, dict | list)


def _redact_form(text: str) -> tuple[str, tuple[str, ...]]:
    pairs = parse_qsl(text, keep_blank_values=True)
    if not pairs:
        return text, ()
    removed = [key for key, _ in pairs if is_secret_field(key)]
    if not removed:
        return text, ()
    cleaned = [(key, REDACTED if is_secret_field(key) else value) for key, value in pairs]
    return urlencode(cleaned), tuple(dict.fromkeys(removed))
