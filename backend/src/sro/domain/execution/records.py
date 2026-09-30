from __future__ import annotations

import json
from collections.abc import Mapping

from sro.domain.recording.redaction import redact_body

K_IDENTIFIES = ("id", "code", "name", "number", "key")

K_NAMED = 6


K_CREATED = 201


def made_by(call: Mapping[str, object]) -> dict[str, str]:
    if call.get("status") != K_CREATED:
        return {}
    text = call.get("body")
    return names_in(text if isinstance(text, str) else None)


def names_in(text: str | None) -> dict[str, str]:
    if not isinstance(text, str) or not text.strip():
        return {}
    try:
        parsed = json.loads(text)
    except ValueError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    inner = parsed.get("data")
    if isinstance(inner, dict):
        parsed = inner
    named: dict[str, str] = {}
    for key, value in parsed.items():
        if not isinstance(key, str) or not isinstance(value, str | int):
            continue
        if not key.lower().endswith(K_IDENTIFIES):
            continue
        said = str(value).strip()
        if said and len(said) <= 64:
            named[key] = said
        if len(named) == K_NAMED:
            break
    return named


K_TOLD = 300

K_SAYS = ("message", "error", "detail", "reason", "title", "description")


def told_by(status: int, text: str, content_type: str | None = None) -> dict[str, str]:
    scrubbed = redact_body(text, content_type=content_type)[0] if text.strip() else ""
    return {"status": str(status), "said": _plain(scrubbed)[:K_TOLD]}


def _plain(text: str) -> str:
    try:
        parsed = json.loads(text)
    except ValueError:
        return " ".join(text.split())
    said: list[str] = []

    def walk(node: object, key: str = "") -> None:
        if isinstance(node, dict):
            for name, value in node.items():
                walk(value, str(name))
        elif isinstance(node, list):
            for value in node:
                walk(value, key)
        elif isinstance(node, str) and key.lower().endswith(K_SAYS) and node.strip():
            said.append(" ".join(node.split()))

    walk(parsed)
    return "; ".join(dict.fromkeys(said)) or " ".join(text.split())


__all__ = ["K_CREATED", "K_IDENTIFIES", "K_NAMED", "made_by", "told_by"]
