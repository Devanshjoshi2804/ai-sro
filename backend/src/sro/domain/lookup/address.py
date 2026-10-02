from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sro.domain.execution.planning import LIVE_FETCHABLE_HEADERS
from sro.domain.lookup.plan import Lookup
from sro.domain.observation.gesture import Gesture
from sro.domain.observation.trim import path_shape
from sro.domain.shared.hosts import REDACTED, headers_without_markers

K_EMPTY = ("", "[]", "{}", "null")


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
    gesture, call = max(
        worked,
        key=lambda one: (-len(_narrowing(one[1].url, lookup)), one[1].started_at or 0.0),
    )
    struck_out = [name for name, value in call.request_headers.items() if REDACTED in value]
    return Address(
        url=_with_params(call.url, lookup.params),
        headers=headers_without_markers(call.request_headers),
        live_headers=tuple(n for n in struck_out if n.lower() in LIVE_FETCHABLE_HEADERS),
        struck=tuple(n for n in struck_out if n.lower() not in LIVE_FETCHABLE_HEADERS),
        seen_at=call.started_at,
        page=gesture.page_url or gesture.url or "",
        narrowed=_narrowing(call.url, lookup),
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


def _narrowing(url: str, lookup: Lookup) -> tuple[str, ...]:
    """What the replayed read filters by besides the key asked for: a param the planner named
    is that search only when its value carries the key (status=ACTIVE reads a subset)."""
    key = lookup.find.casefold() if lookup.find else None
    return tuple(
        name
        for name, value in parse_qsl(
            urlsplit(_with_params(url, lookup.params)).query, keep_blank_values=True
        )
        if value.strip() not in K_EMPTY
        and not (name in lookup.params and key and key in value.casefold())
    )


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
