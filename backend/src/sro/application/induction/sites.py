from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sro.application.induction import jsonutil
from sro.domain.skill.template import Template


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
class TextBodySite: ...


@dataclass(frozen=True, slots=True)
class HeaderSite:
    name: str


@dataclass(frozen=True, slots=True)
class ActionValueSite: ...


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
    if body is None:
        return None
    try:
        return json.loads(body)
    except (ValueError, TypeError):
        return None


_RECENT_MILLIS = range(1_600_000_000_000, 4_000_000_000_000)


def without_clocks(url: str) -> str:
    parts = urlsplit(url)
    kept = [
        (key, value)
        for key, value in url_query_pairs(url)
        if not (value.isdigit() and int(value) in _RECENT_MILLIS)
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment))


def as_a_filter(
    url: str, column: str, placeholder: str, shape: dict[str, str] | None = None
) -> str | None:
    parts = urlsplit(url)
    rebuilt: list[tuple[str, str]] = []
    found = False
    written = False
    for key, value in url_query_pairs(url):
        terms = _filter_terms(value)
        if terms is None:
            if key.lower() not in {"offset", "start", "page"}:
                rebuilt.append((key, value))
            continue
        found = True
        term = terms[0] if terms else shape
        if term is None:
            continue
        written = True
        rebuilt.append(
            (
                key,
                json.dumps(
                    [{**term, "column": column, "value": placeholder}], separators=(",", ":")
                ),
            )
        )
    if not found or not written:
        return None
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(rebuilt, safe="${}"), parts.fragment)
    )


def without_filter(url: str) -> str:
    parts = urlsplit(url)
    kept = [
        (key, value)
        for key, value in url_query_pairs(url)
        if _filter_terms(value) is None and key.lower() not in {"offset", "start", "page"}
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment))


def filter_terms_of(url: str) -> list[dict[str, str]]:
    return [term for _, value in url_query_pairs(url) for term in (_filter_terms(value) or [])]


def _filter_terms(value: str) -> list[dict[str, str]] | None:
    parsed = parse_json(value)
    if not isinstance(parsed, list):
        return None
    terms = [term for term in parsed if isinstance(term, dict) and "column" in term]
    if parsed and not terms:
        return None
    return [{str(k): str(v) for k, v in term.items()} for term in terms]


def substitute_url(url: str, replacements: dict[Site, str]) -> str:
    parts = urlsplit(url)
    segments = url_path_segments(url)

    for site, placeholder in replacements.items():
        if isinstance(site, UrlPathSite) and 0 <= site.index < len(segments):
            segments[site.index] = placeholder

    query = [
        (key, replacements.get(UrlQuerySite(key), value)) for key, value in url_query_pairs(url)
    ]

    path = "/" + "/".join(segments) if segments else parts.path
    return urlunsplit(
        (parts.scheme, parts.netloc, path, urlencode(query, safe="${}"), parts.fragment)
    )


_IN_PATH = str.maketrans({c: f"%{ord(c):02X}" for c in "/?#"})

_IN_QUERY = str.maketrans({c: f"%{ord(c):02X}" for c in "%&=+;#"})


def render_url(url: Template, values: dict[str, str]) -> str:
    path, mark, query = url.raw.partition("?")
    return (
        Template(path).render({name: v.translate(_IN_PATH) for name, v in values.items()})
        + mark
        + Template(query).render({name: v.translate(_IN_QUERY) for name, v in values.items()})
    )


def substitute_body(
    body: str, replacements: dict[Site, str], *, unquoted: frozenset[Site] = frozenset()
) -> str:
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

    markers: dict[str, str] = {}
    for pointer, placeholder in pointers.items():
        if JsonBodySite(pointer) in unquoted:
            marker = f"\x00{pointer}\x00"
            markers[marker] = placeholder
            jsonutil.set_value(document, pointer, marker)
        else:
            jsonutil.set_value(document, pointer, placeholder)
    text = json.dumps(document, separators=(",", ":"))
    for marker, placeholder in markers.items():
        text = text.replace(json.dumps(marker), placeholder)
    return text
