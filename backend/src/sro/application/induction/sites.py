"""Addresses of values inside a step, and substitution at those addresses.

Addressing rather than string-replacing is what stops a quantity of ``3`` being
substituted where a page number happens to share the value.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sro.application.induction import jsonutil


@dataclass(frozen=True, slots=True)
class UrlPathSite:
    index: int


@dataclass(frozen=True, slots=True)
class UrlQuerySite:
    key: str


@dataclass(frozen=True, slots=True)
class JsonBodySite:
    pointer: str


@dataclass(frozen=True, slots=True)
class TextBodySite:
    """Whole body, when it is not JSON and differs between runs."""


@dataclass(frozen=True, slots=True)
class HeaderSite:
    """A request header whose value varied between runs.

    Only headers the domain calls replayable reach here. A trace id differs on
    every run and a cookie differs on every session; treating those as varying
    inputs would turn session noise into parameters the operator is asked for.
    """

    name: str


@dataclass(frozen=True, slots=True)
class ActionValueSite:
    """Text the human typed, or the option they selected."""


Site = UrlPathSite | UrlQuerySite | JsonBodySite | TextBodySite | HeaderSite | ActionValueSite


def describe(site: Site) -> str:
    match site:
        case UrlPathSite(index):
            return f"url path segment {index}"
        case UrlQuerySite(key):
            return f"query parameter {key!r}"
        case JsonBodySite(pointer):
            return f"body {pointer}"
        case TextBodySite():
            return "request body"
        case HeaderSite(name):
            return f"header {name!r}"
        case ActionValueSite():
            return "typed value"


def url_path_segments(url: str) -> list[str]:
    return [segment for segment in urlsplit(url).path.split("/") if segment != ""]


def url_query_pairs(url: str) -> list[tuple[str, str]]:
    return parse_qsl(urlsplit(url).query, keep_blank_values=True)


def parse_json(body: str | None) -> jsonutil.JsonValue | None:
    """Parse as JSON, or ``None`` for form-encoded and plain-text bodies."""
    if body is None:
        return None
    try:
        return json.loads(body)
    except (ValueError, TypeError):
        return None


def substitute_url(url: str, replacements: dict[Site, str]) -> str:
    """Rebuild a URL with placeholders at the given sites.

    Scheme and host are never parameterised: which host a system lives on is a
    deployment fact, not a per-run value.
    """
    parts = urlsplit(url)
    segments = url_path_segments(url)

    for site, placeholder in replacements.items():
        if isinstance(site, UrlPathSite) and 0 <= site.index < len(segments):
            segments[site.index] = placeholder

    query = [
        (key, replacements.get(UrlQuerySite(key), value)) for key, value in url_query_pairs(url)
    ]

    path = "/" + "/".join(segments) if segments else parts.path
    # safe="${}" keeps placeholders readable instead of percent-encoded, because
    # a human reviews these templates.
    return urlunsplit(
        (parts.scheme, parts.netloc, path, urlencode(query, safe="${}"), parts.fragment)
    )


def substitute_body(body: str, replacements: dict[Site, str]) -> str:
    if any(isinstance(site, TextBodySite) for site in replacements):
        return next(value for site, value in replacements.items() if isinstance(site, TextBodySite))

    pointers = {
        site.pointer: placeholder
        for site, placeholder in replacements.items()
        if isinstance(site, JsonBodySite)
    }
    if not pointers:
        return body

    document = parse_json(body)
    if document is None:  # pragma: no cover - callers only pass JSON here
        return body

    for pointer, placeholder in pointers.items():
        # ponytail: a numeric leaf becomes the string "${name}". Harmless while
        # nothing executes; typed substitution is a change to render, not here.
        jsonutil.set_value(document, pointer, placeholder)
    return json.dumps(document, separators=(",", ":"))
