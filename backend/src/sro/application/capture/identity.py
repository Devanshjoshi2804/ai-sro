"""What a demonstration was about, read off what it did.

The operator types a URL and nothing else, so the objective key comes from the
evidence: the call the task ended on names the entity and the verb, and the query
parameter every call carried names the facility. Same rule as parameter naming --
the captured traffic already uses the vocabulary of the system being automated.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from urllib.parse import urlsplit

from sro.application.induction.naming import snake_case
from sro.application.induction.sites import url_path_segments, url_query_pairs
from sro.domain.connection.connection import Connection
from sro.domain.recording.events import ActionFrame
from sro.domain.recording.network import CapturedRequest
from sro.domain.shared.objective import Direction, ObjectiveKey

_ROUTING_SEGMENTS = frozenset(
    {"data", "api", "rest", "ws", "v1", "v2", "v3", "services", "service", "wm", "app", "web"}
)
"""Segments that say how the server is wired, not what the task acted on."""

_FACILITY_KEYS = ("siteid", "site_id", "site", "facility", "warehouse", "whseid", "dcid")
_INBOUND = ("receiv", "inbound", "asn", "putaway")
_OUTBOUND = ("ship", "outbound", "pick", "wave", "load")
_VERB = {"POST": "create", "PUT": "update", "PATCH": "update", "DELETE": "delete", "GET": "view"}

_UNKNOWN_FACILITY = "default"
"""Used when no call named one. A wrong guess would split one task into two
objectives that never pair, so the honest answer is a single stated placeholder."""


def derive_objective_key(
    frames: tuple[ActionFrame, ...],
    *,
    system: str | None = None,
    start_url: str | None = None,
) -> ObjectiveKey | None:
    """The key this demonstration earned, or ``None`` if it asked the server nothing.

    ``system`` comes from the connection the operator taught through; without one
    the host is used, which is at least stable per deployment.
    """
    calls = _calls(frames)
    if not calls:
        return None

    # The write is what the task is about; the reads around it are how the
    # operator got there and how they checked afterwards.
    mutations = [call for call in calls if call.is_mutation]
    subject = mutations[-1] if mutations else calls[-1]

    named = _named_segments(subject.url)
    if not named:
        return None

    entity = named[0]
    objective = named[-1] if len(named) > 1 else _VERB.get(subject.method.upper(), "perform")
    if objective == entity:
        objective = _VERB.get(subject.method.upper(), "perform")

    return ObjectiveKey(
        objective_type=objective,
        target_system=system or _system_from(subject.url, start_url),
        entity_type=entity,
        facility=_facility(calls),
        direction=_direction(subject.url),
    )


def system_of(connections: Iterable[Connection], *urls: str | None) -> str | None:
    """The system name the operator gave when they connected this host.

    Preferred over anything read off the URL: `blue_yonder` is what the skill,
    the vault scope and the knowledge base all call it, and the hostname
    (`bf56-kms-wms-web-np2.jdadelivers.com`) is not.
    """
    hosts = {_host(url) for url in urls if _host(url)}
    return next(
        (
            connection.target_system
            for connection in connections
            if _host(connection.base_url) in hosts
        ),
        None,
    )


def _host(url: str | None) -> str:
    return urlsplit(url or "").hostname or ""


def _calls(frames: tuple[ActionFrame, ...]) -> list[CapturedRequest]:
    """One call per step, background traffic already excluded by the frame."""
    return [
        frame.primary_request
        for frame in frames
        if frame.primary_request is not None and frame.primary_request.succeeded
    ]


def _named_segments(url: str) -> list[str]:
    return [
        snake_case(_singular(segment))
        for segment in url_path_segments(url)
        if segment.lower() not in _ROUTING_SEGMENTS and not _is_record_id(segment)
    ]


def _is_record_id(segment: str) -> bool:
    """A record's id names the record, never the task."""
    return any(character.isdigit() for character in segment) or len(segment) > 24


def _singular(word: str) -> str:
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


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
    host = _host(url) or _host(start_url)
    labels = [label for label in host.split(".") if label not in ("www", "com", "net", "org")]
    return snake_case(labels[-1]) if labels else "unknown"
