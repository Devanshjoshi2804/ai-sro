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
K_STAMP_CALLS = 5
K_STAMP_SKEW_MS = 5000
K_SCOPE_PATHS = 2


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


def address_for(lookup: Lookup, gestures: Iterable[Gesture], now: float = 0.0) -> Address | None:
    """`now` (epoch seconds) is what a request-time stamp param is replayed with."""
    seen = list(gestures)
    if lookup.how == "call":
        return _call_address(lookup, seen, now)
    return _screen_address(lookup, seen)


def _call_address(lookup: Lookup, gestures: list[Gesture], now: float) -> Address | None:
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
    proven: dict[str, tuple[frozenset[tuple[str, str]], frozenset[str]]] = {}

    def narrowing(url: str) -> tuple[str, ...]:
        origin = origin_of(url)
        if origin not in proven:
            proven[origin] = _proven_params(origin, lookup, gestures)
        return _narrowing(url, lookup, *proven[origin])

    gesture, call = max(
        worked, key=lambda one: (-len(narrowing(one[1].url)), one[1].started_at or 0.0)
    )
    struck_out = [name for name, value in call.request_headers.items() if REDACTED in value]
    return Address(
        url=_with_params(
            call.url, {**_stamped(call.url, proven[origin_of(call.url)][1], now), **lookup.params}
        ),
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


def _narrowing(
    url: str, lookup: Lookup, scope: frozenset[tuple[str, str]], stamps: frozenset[str]
) -> tuple[str, ...]:
    """What the replayed read filters by besides the key asked for: a param the planner named
    is that search only when its value is the key and nothing else (status=ACTIVE reads a subset;
    a JSON filter, a longer code or a second value could narrow, so it reads as could-not-tell).
    A scope pair or a stamp name the system's own calls prove (`_proven_params`) is no filter."""
    key = lookup.find.casefold() if lookup.find else None
    return tuple(
        name
        for name, value in parse_qsl(
            urlsplit(_with_params(url, lookup.params)).query, keep_blank_values=True
        )
        if value.strip() not in K_EMPTY
        and (name, value) not in scope
        and name not in stamps
        and not (name in lookup.params and key and _is_the_key(value, key))
    )


def _proven_params(
    origin: str, lookup: Lookup, gestures: list[Gesture]
) -> tuple[frozenset[tuple[str, str]], frozenset[str]]:
    """What the recorded calls of this system prove is no filter: (scope pairs, stamp names).
    Scope: a successful write to each of at least two endpoint paths carried the same
    (name, value), so it is session-wide context (siteId=SG), not one write's field
    (status=ACTIVE). A value the operator typed (or the key asked for) is record content, never
    proof. Stamp: on every recorded call carrying the name (at least K_STAMP_CALLS) the value is
    that call's own started_at in epoch milliseconds, give or take K_STAMP_SKEW_MS (_dc).
    Anything else stays a filter."""
    typed = {
        gesture.action.value.casefold()
        for gesture in gestures
        if gesture.action.value and not gesture.action.secret
    } | {lookup.find.casefold()}
    calls = [
        call for gesture in gestures for call in gesture.requests if origin_of(call.url) == origin
    ]
    wrote: dict[tuple[str, str], set[str]] = {}
    carried: dict[str, list[bool]] = {}
    for call in calls:
        for name, value in _params(call.url):
            carried.setdefault(name, []).append(_is_its_time(value, call.started_at))
            if (
                call.method.upper() != "GET"
                and call.status is not None
                and 200 <= call.status < 300
            ):
                wrote.setdefault((name, value), set()).add(urlsplit(call.url).path)
    scope = frozenset(
        pair
        for pair, paths in wrote.items()
        if len(paths) >= K_SCOPE_PATHS and pair[1].casefold() not in typed
    )
    stamps = frozenset(name for name, ok in carried.items() if len(ok) >= K_STAMP_CALLS and all(ok))
    return scope, stamps


def _is_its_time(value: str, started_at: float | None) -> bool:
    return (
        started_at is not None
        and value.isdigit()
        and abs(int(value) - started_at * 1000) <= K_STAMP_SKEW_MS
    )


def _stamped(url: str, stamps: frozenset[str], now: float) -> dict[str, str]:
    return {name: str(int(now * 1000)) for name, _ in _params(url) if name in stamps}


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
