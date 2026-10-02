from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sro.domain.execution.planning import LIVE_FETCHABLE_HEADERS
from sro.domain.lookup.plan import Lookup
from sro.domain.observation.gesture import Gesture
from sro.domain.observation.trim import path_shape
from sro.domain.shared.hosts import REDACTED, headers_without_markers, origin_of

K_EMPTY = ("", "[]", "{}", "null")
K_TIMESTAMP_DIGITS = 10


@dataclass(frozen=True, slots=True)
class Address:
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    live_headers: tuple[str, ...] = ()

    struck: tuple[str, ...] = ()

    seen_at: float | None = None

    page: str = ""

    reads: tuple[str, ...] = ()

    narrowed: tuple[str, ...] = ()


def address_for(lookup: Lookup, gestures: Iterable[Gesture]) -> Address | None:
    seen = list(gestures)
    if lookup.how == "call":
        return _call_address(lookup, seen)
    return _screen_address(lookup, seen)


def _call_address(lookup: Lookup, gestures: list[Gesture]) -> Address | None:
    worked = [
        (gesture, call)
        for gesture in gestures
        for call in gesture.requests
        if call.method.upper() == "GET"
        and urlsplit(call.url).path == lookup.target
        and call.status is not None
        and 200 <= call.status < 300
        and not call.failure_reason
    ]
    if not worked:
        return None
    proven: dict[str, frozenset[tuple[str, str]]] = {}

    def narrowing(url: str) -> tuple[str, ...]:
        origin = origin_of(url)
        if origin not in proven:
            proven[origin] = _proven_params(origin, lookup, gestures)
        return _narrowing(url, lookup, proven[origin])

    gesture, call = max(
        worked, key=lambda one: (-len(narrowing(one[1].url)), one[1].started_at or 0.0)
    )
    struck_out = [name for name, value in call.request_headers.items() if REDACTED in value]
    return Address(
        url=_with_params(call.url, lookup.params),
        headers=headers_without_markers(call.request_headers),
        live_headers=tuple(n for n in struck_out if n.lower() in LIVE_FETCHABLE_HEADERS),
        struck=tuple(n for n in struck_out if n.lower() not in LIVE_FETCHABLE_HEADERS),
        seen_at=call.started_at,
        page=gesture.page_url or gesture.url or "",
        narrowed=narrowing(call.url),
    )


def _screen_address(lookup: Lookup, gestures: list[Gesture]) -> Address | None:
    wanted = _route_name(lookup.target)
    if not wanted:
        return None
    on_it = [
        gesture
        for gesture in gestures
        if gesture.url and _route_name(urlsplit(gesture.url).fragment) == wanted
    ]
    if not on_it:
        return None
    seen = max(on_it, key=lambda gesture: gesture.at)
    made = Counter(
        shape
        for gesture in on_it
        for shape in dict.fromkeys(
            path_shape(call.url)
            for call in gesture.requests
            if call.method.upper() == "GET"
            and call.status is not None
            and 200 <= call.status < 300
            and not call.failure_reason
        )
    )
    return Address(
        url=seen.url or "", seen_at=seen.at, reads=tuple(shape for shape, _ in made.most_common())
    )


def _narrowing(url: str, lookup: Lookup, proven: frozenset[tuple[str, str]]) -> tuple[str, ...]:
    """What the replayed read filters by besides the key asked for: a param the planner named
    is that search only when its value is the key and nothing else (status=ACTIVE reads a subset;
    a JSON filter, a longer code or a second value could narrow, so it reads as could-not-tell).
    A (name, value) the system's own writes prove (`_proven_params`) is scope, not a filter."""
    key = lookup.find.casefold() if lookup.find else None
    return tuple(
        name
        for name, value in parse_qsl(
            urlsplit(_with_params(url, lookup.params)).query, keep_blank_values=True
        )
        if value.strip() not in K_EMPTY
        and (name, value) not in proven
        and not (name in lookup.params and key and _is_the_key(value, key))
    )


def _proven_params(
    origin: str, lookup: Lookup, gestures: list[Gesture]
) -> frozenset[tuple[str, str]]:
    """The (name, value) pairs on this system that are no filter, proven by what was recorded.
    Scope: a successful write carried the same pair, so the place records are made is the place
    read (siteId=SG). Cache-buster: the name's values are all distinct timestamp-sized numbers
    over every recorded call, none was ever typed, and a write carried it too. A value the
    operator typed (or the key asked for) is record content, never proof.
    Anything else stays a filter."""
    typed = {
        gesture.action.value.casefold()
        for gesture in gestures
        if gesture.action.value and not gesture.action.secret
    } | {lookup.find.casefold()}
    calls = [
        call for gesture in gestures for call in gesture.requests if origin_of(call.url) == origin
    ]
    carried = [(call, _params(call.url)) for call in calls]
    wrote = {
        pair
        for call, pairs in carried
        if call.method.upper() != "GET" and call.status is not None and 200 <= call.status < 300
        for pair in pairs
    }
    seen = Counter(pair for _, pairs in carried for pair in pairs)
    names: dict[str, list[str]] = {}
    for name, value in seen:
        names.setdefault(name, []).append(value)
    busters = {
        name
        for name, values in names.items()
        if all(seen[(name, value)] == 1 and _a_timestamp(value) for value in values)
        and not typed.intersection(value.casefold() for value in values)
        and any(pair[0] == name for pair in wrote)
    }
    return frozenset(
        pair
        for pair in seen
        if pair[1].casefold() not in typed and (pair in wrote or pair[0] in busters)
    )


def _a_timestamp(value: str) -> bool:
    return value.isdigit() and len(value) >= K_TIMESTAMP_DIGITS


def _params(url: str) -> set[tuple[str, str]]:
    return set(parse_qsl(urlsplit(url).query, keep_blank_values=True))


def _is_the_key(value: str, key: str) -> bool:
    text = value.strip().casefold()
    return (
        key in text
        and text[:1] not in "[{"
        and not any(char.isalnum() for char in text.replace(key, "", 1).translate(_WILDCARDS))
    )


_WILDCARDS = str.maketrans("", "", "*%?")


def _route_name(route: str) -> str:
    segments = [part.strip() for part in route.lstrip("#").split("/") if part.strip()]
    return segments[-1].lower() if segments else ""


def _with_params(url: str, params: dict[str, str]) -> str:
    if not params:
        return url
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update(params)
    return urlunsplit(parts._replace(query=urlencode(query)))
