"""What a demonstration was about, read off what it did.

The operator types a URL and nothing else, so the objective key comes from the
evidence: the call the task ended on names the entity and the verb, and the query
parameter every call carried names the facility. Same rule as parameter naming --
the captured traffic already uses the vocabulary of the system being automated.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from urllib.parse import urlsplit

from sro.application.induction.naming import singular, snake_case
from sro.application.induction.sites import url_path_segments, url_query_pairs
from sro.domain.connection.connection import Connection
from sro.domain.recording.background import is_background_traffic
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

_WORDS = re.compile(r"[A-Za-z][A-Za-z0-9]*")

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
    # operator got there and how they checked afterwards. Where one gesture
    # wrote twice -- Save creating a supplier and setting its address -- the
    # creation names the task, because that is what the operator would call it
    # and what nobody else can do by editing an existing record.
    mutations = [call for call in calls if call.is_mutation]
    created = [call for call in mutations if call.method.upper() == "POST"]

    # Where one Save wrote several records, the last one is not the task. A
    # client creation posts an address, then the client, then its warehouse
    # link, then a packing configuration -- and taking the last named that
    # demonstration `create packing_configuration`, which is a child row of the
    # thing the operator actually did. The screen says which: they were on
    # Clients, and clicked a control that says so. That is evidence in the
    # recording, not an inference about what they meant.
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
    """What to call the system this URL belongs to.

    The connection's own label where somebody has connected it, and a label made
    from the host where nobody has. Both are what `target_system` holds, which
    is what matters: a system name and a hostname sitting side by side in the
    same field is how a circuit breaker ends up protecting a system that does
    not exist.
    """
    return system_of(connections, url) or _system_from(url or "", None)


def system_of(connections: Iterable[Connection], *urls: str | None) -> str | None:
    """The system name the operator gave when they connected this host.

    Preferred over anything read off the URL: `blue_yonder` is what the skill,
    the vault scope and the knowledge base all call it, and the hostname
    (`bf56-kms-wms-web-np2.jdadelivers.com`) is not.
    """
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
    """The hostname of a URL, or "" when it has none."""
    return urlsplit(url or "").hostname or ""


_LABEL_LIMIT = 40
"""Longest text treated as a control's name. A button says "Clients"; the
paragraph explaining what a client is says every warehouse noun there is, and
letting that vote would name the task after whatever the operator read."""


def _screen_words(frames: tuple[ActionFrame, ...]) -> set[str]:
    """What the operator's own gestures named, as entity words.

    Only labels: the accessible name a control reports, or its visible text.
    """
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
    """The entity this call is about, by the same rule the key uses."""
    segments = _named_segments(call.url)
    return segments[0] if segments else ""


def _calls(frames: tuple[ActionFrame, ...]) -> list[CapturedRequest]:
    """Every call the demonstration made, in order.

    Not one per step: a single Save can create a record and then address it, and
    reading only the step's "primary" call named the task after the second of
    those -- an update of an address, for a task that creates a supplier.
    """
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
    """A record's id names the record, never the task."""
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
