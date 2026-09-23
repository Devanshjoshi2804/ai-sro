from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Sequence
from urllib.parse import urlsplit

from sro.application.induction.naming import singular, snake_case
from sro.application.induction.sites import url_path_segments, url_query_pairs
from sro.domain.connection.connection import Connection
from sro.domain.recording.background import is_background_traffic
from sro.domain.recording.events import ActionFrame
from sro.domain.recording.network import CapturedRequest
from sro.domain.recording.recording import Recording
from sro.domain.shared.objective import Direction, ObjectiveKey

_ROUTING_SEGMENTS = frozenset(
    {"data", "api", "rest", "ws", "v1", "v2", "v3", "services", "service", "wm", "app", "web"}
)

_FACILITY_KEYS = ("siteid", "site_id", "site", "facility", "warehouse", "whseid", "dcid")
_INBOUND = ("receiv", "inbound", "asn", "putaway")
_OUTBOUND = ("ship", "outbound", "pick", "wave", "load")
_VERB = {"POST": "create", "PUT": "update", "PATCH": "update", "DELETE": "delete", "GET": "view"}

_WORDS = re.compile(r"[A-Za-z][A-Za-z0-9]*")

_UNKNOWN_FACILITY = "default"


def derive_objective_key(
    frames: tuple[ActionFrame, ...],
    *,
    system: str | None = None,
    start_url: str | None = None,
) -> ObjectiveKey | None:
    calls = _calls(frames)
    if not calls:
        return None

    mutations = [call for call in calls if call.is_mutation]
    created = [call for call in mutations if call.method.upper() == "POST"]

    named = _screen_words(frames)
    on_screen = [call for call in created if _entity_of(call) in named]
    subject = (on_screen or created or mutations or calls)[-1]

    segments = _named_segments(subject.url)
    if not segments:
        return None

    entity = segments[0]
    objective = segments[-1] if len(segments) > 1 else _VERB.get(subject.method.upper(), "perform")
    if objective == entity:
        objective = _VERB.get(subject.method.upper(), "perform")

    return ObjectiveKey(
        objective_type=objective,
        target_system=system or _system_from(subject.url, start_url),
        entity_type=entity,
        facility=_facility(calls),
        direction=_direction(subject.url),
    )


def system_named(connections: Iterable[Connection], url: str | None) -> str:
    return system_of(connections, url) or _system_from(url or "", None)


def systems_touched(connections: Sequence[Connection], *recordings: Recording) -> tuple[str, ...]:
    found: list[tuple[str, str | None, str]] = []
    for recording in recordings:
        for frame in recording.frames:
            for request in frame.requests:
                host = host_of(request.url)
                if not host or any(host == known for known, _, _ in found):
                    continue
                found.append(
                    (host, system_of(connections, request.url), _system_from(request.url, None))
                )

    connected = {label for _, label, _ in found if label}
    names: list[str] = []
    for host, label, derived in found:
        chosen = label or (host if derived in connected else derived)
        if chosen and chosen not in names:
            names.append(chosen)
    return tuple(names)


def system_of(connections: Iterable[Connection], *urls: str | None) -> str | None:
    hosts = {host_of(url) for url in urls if host_of(url)}
    return next(
        (
            connection.target_system
            for connection in connections
            if host_of(connection.base_url) in hosts
        ),
        None,
    )


def host_of(url: str | None) -> str:
    return urlsplit(url or "").hostname or ""


_LABEL_LIMIT = 40


def _screen_words(frames: tuple[ActionFrame, ...]) -> set[str]:
    found: set[str] = set()
    for frame in frames:
        target = frame.action.target
        if target is None:
            continue
        for label in (target.accessible_name, target.text):
            if not label or len(label) > _LABEL_LIMIT:
                continue
            found.update(snake_case(singular(word)) for word in _WORDS.findall(label))
    return found


def _entity_of(call: CapturedRequest) -> str:
    segments = _named_segments(call.url)
    return segments[0] if segments else ""


def _calls(frames: tuple[ActionFrame, ...]) -> list[CapturedRequest]:
    return [
        request
        for frame in frames
        for request in frame.requests
        if request.succeeded and not is_background_traffic(request.url)
    ]


def _named_segments(url: str) -> list[str]:
    return [
        snake_case(singular(segment))
        for segment in url_path_segments(url)
        if segment.lower() not in _ROUTING_SEGMENTS and not _is_record_id(segment)
    ]


def _is_record_id(segment: str) -> bool:
    return any(character.isdigit() for character in segment) or len(segment) > 24


def _facility(calls: list[CapturedRequest]) -> str:
    values = Counter(
        value
        for call in calls
        for key, value in url_query_pairs(call.url)
        if key.lower() in _FACILITY_KEYS and value.strip()
    )
    return values.most_common(1)[0][0] if values else _UNKNOWN_FACILITY


def _direction(url: str) -> Direction:
    path = url.lower()
    if any(marker in path for marker in _INBOUND):
        return Direction.INBOUND
    if any(marker in path for marker in _OUTBOUND):
        return Direction.OUTBOUND
    return Direction.INTERNAL


def _system_from(url: str, start_url: str | None) -> str:
    host = host_of(url) or host_of(start_url)
    labels = [label for label in host.split(".") if label not in ("www", "com", "net", "org")]
    return snake_case(labels[-1]) if labels else "unknown"
