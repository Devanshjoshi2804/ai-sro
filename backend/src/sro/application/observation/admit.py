from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from urllib.parse import urlsplit

from sro.config import _DEFAULT_PORTS
from sro.domain.observation.batch import RejectedEvent
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.observation.seen import effect_kept

Event = Mapping[str, object]

KINDS = ("gesture", "request", "snapshot", "page", "effect")

_REF = re.compile(r"[A-Za-z0-9_.-]{1,64}")

_SIGNALS = ("role", "name", "text", "testId", "cssPath", "xpath")


@dataclass(frozen=True, slots=True)
class Admission:
    accepted: tuple[Event, ...]
    rejected: tuple[RejectedEvent, ...]

    @property
    def accepted_count(self) -> int:
        return len(self.accepted)


def admit(
    events: Sequence[Event],
    policy: ObservationPolicy,
    granted: frozenset[str] = frozenset(),
    ours: frozenset[tuple[str, str]] = frozenset(),
) -> Admission:
    kept: list[Event] = []
    refused: list[RejectedEvent] = []
    for index, event in enumerate(events):
        reason = _why_not(event, policy, granted, ours)
        if reason is None:
            kept.append(event)
        else:
            refused.append(RejectedEvent(index=index, reason=reason))
    return Admission(accepted=tuple(kept), rejected=tuple(refused))


def _why_not(
    event: Event,
    policy: ObservationPolicy,
    granted: frozenset[str],
    ours: frozenset[tuple[str, str]],
) -> str | None:
    kind = event.get("kind")
    if kind not in KINDS:
        return f"the protocol declares no event kind {kind!r}"

    if kind == "gesture":
        gesture = _mapping(event.get("gesture"))
        if gesture is None:
            return "a gesture event with no gesture in it"
        if not gesture.get("kind"):
            return "a gesture that does not say what it was"
        if gesture.get("at") is None:
            return "a gesture with no time on it cannot be put in order"
        target = _mapping(gesture.get("target"))
        if target is not None and not any(target.get(signal) for signal in _SIGNALS):
            return "the element carries no signal it could be found by again"
        return _url_refusal(gesture.get("url"), policy, granted, ours)

    if kind == "request":
        request = _mapping(event.get("request"))
        if request is None:
            return "a request event with no request in it"
        if not request.get("method"):
            return "a request with no method"
        if request.get("started_at") is None:
            return "a request with no start time cannot be attributed to an action"
        return _url_refusal(request.get("url"), policy, granted, ours)

    if kind == "snapshot":
        if _mapping(event.get("snapshot")) is None:
            return "a snapshot event with no snapshot in it"
        if event.get("taken_at") is None:
            return "a snapshot with no time on it"
        return _url_refusal(event.get("url"), policy, granted, ours)

    if kind == "effect":
        of = event.get("of")
        if not isinstance(of, str) or not _REF.fullmatch(of):
            return "an effect that does not say which gesture it followed"
        of_at = event.get("of_at")
        if isinstance(of_at, bool) or not isinstance(of_at, int | float) or not isfinite(of_at):
            return "an effect with no gesture time cannot be joined to its gesture"
        if effect_kept(event.get("effect")) is None:
            return "an effect event with nothing in it that can be kept"
        return _url_refusal(event.get("url"), policy, granted, ours)

    if not event.get("page_kind"):
        return "a page event that does not say what happened"
    if event.get("at") is None:
        return "a page event with no time on it"
    return _url_refusal(event.get("url"), policy, granted, ours)


def _url_refusal(
    url: object,
    policy: ObservationPolicy,
    granted: frozenset[str],
    ours: frozenset[tuple[str, str]],
) -> str | None:
    if not isinstance(url, str) or not url.strip():
        return "an event with no URL cannot be checked against the policy"
    if _is_ours(url, ours):
        return "this is the recording apparatus, not the work it records"
    if not policy.allows(url, granted):
        return "this page is outside what the tenant agreed to observe"
    return None


def _is_ours(url: str, ours: frozenset[tuple[str, str]]) -> bool:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").rstrip(".")
    if not host:
        return False
    if ":" in host:
        host = f"[{host}]"
    try:
        port = str(parsed.port) if parsed.port else ""
    except ValueError:
        return False
    if port and port == _DEFAULT_PORTS.get(parsed.scheme.lower()):
        port = ""
    mine = f"{host}:{port}" if port else host
    path = parsed.path or "/"
    return any(
        mine == theirs and (prefix == "/" or path == prefix or path.startswith(f"{prefix}/"))
        for theirs, prefix in ours
    )


def _mapping(value: object) -> Event | None:
    return value if isinstance(value, Mapping) else None
