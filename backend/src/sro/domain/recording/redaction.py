from __future__ import annotations

import json
import re
from urllib.parse import parse_qsl, urlencode

from sro.domain.recording.sensitivity import REDACTED as REDACTED
from sro.domain.recording.sensitivity import is_secret_field, redact_shapes, shapes_in


def redact_body(text: str, *, content_type: str | None) -> tuple[str, tuple[str, ...]]:
    cleaned, removed = _redact_named(text, content_type)
    shaped = shapes_in(cleaned)
    if not shaped:
        return cleaned, removed
    return redact_shapes(cleaned), removed + tuple(f"«shape: {shape}»" for shape in shaped)


def _redact_named(text: str, content_type: str | None) -> tuple[str, tuple[str, ...]]:
    kind = (content_type or "").lower()
    if "json" in kind or text.lstrip().startswith(("{", "[")):
        return _redact_json(text)
    if "xml" in kind or text.lstrip().startswith("<"):
        return _redact_xml(text)
    if "multipart" in kind:
        return _redact_multipart(text)
    if "x-www-form-urlencoded" in kind or ("=" in text and "\n" not in text):
        return _redact_form(text)
    return text, ()


def _redact_json(text: str) -> tuple[str, tuple[str, ...]]:
    try:
        document = json.loads(text)
    except ValueError:
        return text, ()

    removed: list[str] = []

    def walk(node: object) -> object:
        if isinstance(node, dict):
            cleaned: dict[str, object] = {}
            for key, value in node.items():
                if is_secret_field(str(key)):
                    removed.append(str(key))
                    cleaned[key] = REDACTED
                else:
                    cleaned[key] = walk(value)
            return cleaned
        if isinstance(node, list):
            return [walk(item) for item in node]
        return node

    cleaned_document = walk(document)
    return (json.dumps(cleaned_document, ensure_ascii=False) if removed else text), tuple(
        dict.fromkeys(removed)
    )


def _redact_form(text: str) -> tuple[str, tuple[str, ...]]:
    pairs = parse_qsl(text, keep_blank_values=True)
    if not pairs:
        return text, ()
    removed = [key for key, _ in pairs if is_secret_field(key)]
    if not removed:
        return text, ()
    cleaned = [(key, REDACTED if is_secret_field(key) else value) for key, value in pairs]
    return urlencode(cleaned), tuple(dict.fromkeys(removed))


_XML_FIELD = re.compile(r"<([A-Za-z_][\w.:-]*)([^>]*)>([^<]*)</\1>")
_XML_ATTR = re.compile(r'([A-Za-z_][\w.:-]*)\s*=\s*"([^"]*)"')


def _redact_xml(text: str) -> tuple[str, tuple[str, ...]]:
    removed: list[str] = []

    def element(match: re.Match[str]) -> str:
        name, attributes = match.group(1), match.group(2)
        if is_secret_field(name.split(":")[-1]):
            removed.append(name)
            return f"<{name}{attributes}>{REDACTED}</{name}>"
        return match.group(0)

    def attribute(match: re.Match[str]) -> str:
        name = match.group(1)
        if is_secret_field(name.split(":")[-1]):
            removed.append(name)
            return f'{name}="{REDACTED}"'
        return match.group(0)

    cleaned = _XML_FIELD.sub(element, text)
    cleaned = _XML_ATTR.sub(attribute, cleaned)
    return (cleaned if removed else text), tuple(dict.fromkeys(removed))


_PART_NAME = re.compile(r'name="([^"]+)"')


def _redact_multipart(text: str) -> tuple[str, tuple[str, ...]]:
    lines = text.splitlines(keepends=True)
    boundary = lines[0].strip() if lines and lines[0].startswith("--") else ""
    if not boundary:
        return text, ()

    removed: list[str] = []
    out: list[str] = []
    secret_part = False
    in_headers = False
    for line in lines:
        if line.strip() == boundary or line.strip() == f"{boundary}--":
            secret_part, in_headers = False, True
            out.append(line)
            continue
        if in_headers:
            if (found := _PART_NAME.search(line)) and is_secret_field(found.group(1)):
                secret_part = True
                removed.append(found.group(1))
            if not line.strip():
                in_headers = False
                out.append(line)
                if secret_part:
                    out.append(REDACTED + "\r\n")
                continue
            out.append(line)
            continue
        if secret_part:
            continue
        out.append(line)
    return ("".join(out) if removed else text), tuple(dict.fromkeys(removed))
