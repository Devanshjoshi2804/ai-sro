"""Credential removal, at every point of capture.

Everything a demonstration does is evidence and is kept verbatim -- with one
exception. A password is not evidence of what happened; it is a key to the
customer's system, and keeping it would turn the evidence store into a
credential store with none of the handling that implies.

So credentials are removed here, before a body is ever written, rather than
filtered on the way out. Matched by field name, because a name is a decision the
target system already made; guessing from values would redact real business
data. What is kept is the field name, so a reviewer sees what was removed.

Domain rather than ``infrastructure.steel``, where this lived while Steel was
the only thing that captured a body. It is not: the observation ingest path
takes bodies straight from an operator's own browser, and the layering rule --
application never imports an adapter -- meant the one body redactor in the
codebase was unreachable from the one path that was storing bodies unredacted.
Stdlib only, so the move is a relocation and not a rewrite.
"""

from __future__ import annotations

import json
import re
from urllib.parse import parse_qsl, urlencode

from sro.domain.recording.sensitivity import REDACTED as REDACTED
from sro.domain.recording.sensitivity import is_secret_field, redact_shapes, shapes_in

# ^ Re-exported deliberately: capture.py imports the marker from here, and
# there is one marker for every path that writes it.


def redact_body(text: str, *, content_type: str | None) -> tuple[str, tuple[str, ...]]:
    """Return the body with credential values removed, and what removed them.

    Two rules, and a value goes if EITHER fires. The name rule below is the
    secondary one and has to be: a field name is chosen by whoever wrote the
    vendor's API, an open vocabulary guessed at forever. The shape rule needs
    no name, so it runs last and over whatever the parsers produced -- reaching
    a credential in a field nobody thought to list, and through a body no
    parser here fitted at all.

    A shape is reported as `«shape: jwt»` rather than as a field name, because
    "we removed this because it looked like a JWT" is a different fact from
    "we removed this because it was called password". The marker left in the
    text is the same either way, so nothing downstream learns a second
    convention.
    """
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
        # Before the form heuristic below, which is "has an = and one line" --
        # true of every one-line XML document with an attribute in it.
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
                    # Whatever shape it is. This used to require a scalar, so
                    # ``{"password": ["hunter2"]}`` was written to the evidence
                    # store verbatim and reported as nothing removed -- and a
                    # list is exactly what an HTML form with a repeated field
                    # produces.
                    removed.append(str(key))
                    cleaned[key] = REDACTED
                else:
                    cleaned[key] = walk(value)
            return cleaned
        if isinstance(node, list):
            return [walk(item) for item in node]
        return node

    cleaned_document = walk(document)
    # ``ensure_ascii=False`` because the default escapes the marker this very
    # function just wrote to ``\u00abredacted\u00bb``, along with any the
    # browser had already put in the same body -- and then a reviewer grepping
    # the evidence store for «redacted» finds neither. Measured over the 395
    # stored batches: 15 bodies came back with escaped markers.
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
"""Leaf elements only -- the ones with a value in them rather than more
elements. Matching containers as well would have the outermost match eat the
whole document and never reach the field inside it."""
_XML_ATTR = re.compile(r'([A-Za-z_][\w.:-]*)\s*=\s*"([^"]*)"')


def _redact_xml(text: str) -> tuple[str, tuple[str, ...]]:
    """Elements and attributes whose name says credential.

    SOAP is not a museum piece in this trade -- a WMS that speaks it puts the
    password in ``<Password>`` -- and nothing here looked at XML at all, so
    those bodies were stored exactly as sent.

    Textual rather than parsed on purpose: a captured body may be truncated or
    malformed, and a parser that refuses it would redact nothing at all.
    """
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
    """A part whose ``name=`` says credential loses its content.

    Boundary-agnostic: the boundary is whatever the first line says it is, and
    a body whose parts cannot be told apart is left alone rather than mangled.
    """
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
