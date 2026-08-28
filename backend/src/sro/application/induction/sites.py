"""Addresses of values inside a step, and substitution at those addresses.

Addressing rather than string-replacing is what stops a quantity of ``3`` being
substituted where a page number happens to share the value.
"""

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


_RECENT_MILLIS = range(1_600_000_000_000, 4_000_000_000_000)
"""2020 to 2096, in milliseconds. What a cache-buster's value looks like."""


def without_clocks(url: str) -> str:
    """The same address, minus the parameters that only mean "now".

    Ext JS appends `_dc=<epoch millis>` to defeat caching and jQuery's `_` does
    the same. Replaying yesterday's "now" is at best meaningless; dropping the
    whole query instead is worse, because a site-scoped collection needs its
    site parameter and answers nothing without it.
    """
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
    """The same query, asking the server for one column instead of the other.

    The demonstration searched for what its operator was looking for -- ten rows
    where the name contained an "h" -- and replaying that searches for their
    record, not this one. But it also proves how this system is asked: the
    filter's own shape, in its own vocabulary, with a real 200 behind it.

    So the query is kept and its terms are replaced: same parameter, same
    dialect, this run's value. ``None`` when nothing here looks like a filter,
    because inventing one for an API that never showed us one is a guess.
    """
    parts = urlsplit(url)
    rebuilt: list[tuple[str, str]] = []
    found = False
    written = False
    for key, value in url_query_pairs(url):
        terms = _filter_terms(value)
        if terms is None:
            # Offsets belong to the page somebody was looking at, not to a
            # search for one record.
            if key.lower() not in {"offset", "start", "page"}:
                rebuilt.append((key, value))
            continue
        found = True
        # An empty list is a filter slot: the endpoint takes this parameter and
        # was sent nothing in it. What a term looks like then has to come from
        # somewhere this system has been seen filling one in -- never from a
        # shape invented here.
        term = terms[0] if terms else shape
        if term is None:
            # An empty slot and no proven shape to fill it with. Composing the
            # request without the filter would ask for everything, which is a
            # different question from the one that was asked.
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
    """The same address with nobody's search on it.

    A dropdown opening for the first time should show what is there, not what
    the operator who taught the task was looking for that afternoon.
    """
    parts = urlsplit(url)
    kept = [
        (key, value)
        for key, value in url_query_pairs(url)
        if _filter_terms(value) is None and key.lower() not in {"offset", "start", "page"}
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment))


def filter_terms_of(url: str) -> list[dict[str, str]]:
    """Every filter term this address carries, across its query parameters."""
    return [term for _, value in url_query_pairs(url) for term in (_filter_terms(value) or [])]


def _filter_terms(value: str) -> list[dict[str, str]] | None:
    """The filter this query parameter carried, or ``None`` if it is not one.

    An empty list is a filter -- an empty one. The distinction matters: it says
    this endpoint accepts a filter here, which is the difference between
    composing a narrower request and inventing a parameter.
    """
    parsed = parse_json(value)
    if not isinstance(parsed, list):
        return None
    terms = [term for term in parsed if isinstance(term, dict) and "column" in term]
    if parsed and not terms:
        return None
    return [{str(k): str(v) for k, v in term.items()} for term in terms]


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


_IN_PATH = str.maketrans({c: f"%{ord(c):02X}" for c in "/?#"})
"""What a value cannot carry into a path segment without ending it.

Only these three, because a path segment is stored the way the demonstration
sent it -- `url_path_segments` never unquotes -- so the text in one is already
percent-encoded and everything else in it has to be left exactly alone.
Encoding the `%` of an `ATTN%20ALI` again gives `ATTN%2520ALI`, the
double-encoding `choices._searched` already carries a warning about. These
three are safe to touch anyway: an already-encoded segment spells them `%2F`,
`%3F` and `%23`, never bare, since a bare `/` would have made it two segments
in the recording."""

_IN_QUERY = str.maketrans({c: f"%{ord(c):02X}" for c in "%&=+;#"})
"""What a value cannot carry into a query parameter without ending it.

More than the path's set, and that asymmetry is the point: a query value is
held *decoded* -- `url_query_pairs` reads it through `parse_qsl` -- so a `%`
here is a percent sign somebody typed and encoding it is restoring what the
demonstration itself put on the wire, not doubling it. The set is
form-urlencoding's own delimiters, because that is the syntax this value is
read back out of; `+` and `;` are in it because a reader that means "space"
by one and "separator" by the other is a reader we do not control."""


def render_url(url: Template, values: dict[str, str]) -> str:
    """Substitute values into a URL template, encoded for the slot each lands in.

    A value is text, and text in a URL is structure: `X&limit=9999` supplied
    for a search term used to render `?name=X&limit=9999&limit=25`, asking the
    server a question nobody demonstrated. Same defect as the JSON body's, and
    the same answer -- encode rather than refuse, so an operator searching for
    `Smith & Sons` still gets to.

    Split at the first `?` so each half encodes in its own syntax, and rendered
    with the same `Template` both halves came from rather than a second
    substitution syntax written here. Nothing outside a placeholder is touched,
    so a template renders byte-for-byte as it did before wherever the values
    going into it carry none of these characters.
    """
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

    # A field whose absent form is not itself a JSON string -- `null` for a
    # number the form nulls -- must send that form unrendered: a quoted
    # `"null"` is a string, and a form expecting a number rejects it. Such a
    # leaf gets a `\x00pointer\x00` sentinel instead of its placeholder here,
    # so the later unquoting step can find exactly this leaf and nothing else
    # -- a `\x00` byte is not something a form control lets an operator type,
    # and `json.dumps` always escapes one to `\u0000`, so the marker's quoted
    # form can only occur in the output where this function itself put it.
    # Doing this with the placeholder text directly, `${name}`, would unquote
    # any other field whose own value happened to read that.
    #
    # Keyed on the site rather than the parameter's name, because which leaves
    # lose their quotes is a fact about those leaves: one parameter can fill a
    # body number here and a URL segment there, and the name says nothing about
    # which is which.
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
