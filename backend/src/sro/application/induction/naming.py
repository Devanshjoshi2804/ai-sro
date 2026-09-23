from __future__ import annotations

import re

from sro.application.induction import jsonutil
from sro.application.induction.sites import (
    ActionValueSite,
    HeaderSite,
    JsonBodySite,
    Site,
    TextBodySite,
    UrlPathSite,
    UrlQuerySite,
    url_path_segments,
)

CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_IDENTIFIER = re.compile(r"[^0-9a-zA-Z]+")


def snake_case(text: str) -> str:
    spaced = CAMEL_BOUNDARY.sub("_", text)
    cleaned = _NON_IDENTIFIER.sub("_", spaced).strip("_").lower()
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"value_{cleaned}" if cleaned else "value"
    return cleaned


def _singular(word: str) -> str:
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def suggest_name(site: Site, *, url: str = "", field_label: str | None = None) -> str:
    match site:
        case JsonBodySite(pointer):
            tokens = [token for token in jsonutil.parse(pointer) if not token.isdigit()]
            return snake_case(tokens[-1]) if tokens else "body_value"

        case UrlQuerySite(key):
            return snake_case(key)

        case UrlPathSite(index):
            segments = url_path_segments(url)
            if index > 0 and index - 1 < len(segments):
                return f"{snake_case(_singular(segments[index - 1]))}_id"
            return f"path_{index}"

        case HeaderSite(name):
            cleaned = name[2:] if name.lower().startswith("x-") else name
            return snake_case(cleaned)

        case ActionValueSite():
            return snake_case(field_label) if field_label else "input_value"

        case TextBodySite():
            return "request_body"


def singular(word: str) -> str:
    lowered = word
    if len(lowered) > 3 and lowered.endswith("ies"):
        return f"{lowered[:-3]}y"
    if (
        len(lowered) > 4
        and lowered.endswith("es")
        and lowered[:-2].endswith(("s", "x", "z", "ch", "sh"))
    ):
        return lowered[:-2]
    if len(lowered) > 3 and lowered.endswith("s") and not lowered.endswith(("ss", "us", "is")):
        return lowered[:-1]
    return lowered


def deduplicate(preferred: str, taken: set[str]) -> str:
    if preferred not in taken:
        return preferred
    suffix = 2
    while f"{preferred}_{suffix}" in taken:
        suffix += 1
    return f"{preferred}_{suffix}"
