"""Which of an upload's events may be kept, and why the rest were not.

Screening, not parsing. The evidence plane keeps what arrived verbatim, so this
answers one question per event -- is this a thing we agreed to record, in a
shape the domain can read later -- and says why when the answer is no. Turning
an event into an ``InputAction`` happens when something needs one.

A rejection is a bug in the extension, reported back on the same response so it
is found on the day it is introduced rather than in a mining run three weeks
later that quietly saw fewer tasks than happened.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sro.domain.observation.batch import RejectedEvent
from sro.domain.observation.policy import ObservationPolicy

Event = Mapping[str, object]

KINDS = ("gesture", "request", "snapshot", "page")

_SIGNALS = ("role", "name", "text", "testId", "cssPath", "xpath")
"""What an element fingerprint may be found by. ``ElementFingerprint`` refuses
one carrying none of these, so an event with such a target is evidence that
cannot be replayed, aligned or matched. Kept out here rather than discovered by
a miner months later."""


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
) -> Admission:
    kept: list[Event] = []
    refused: list[RejectedEvent] = []
    for index, event in enumerate(events):
        reason = _why_not(event, policy, granted)
        if reason is None:
            kept.append(event)
        else:
            refused.append(RejectedEvent(index=index, reason=reason))
    return Admission(accepted=tuple(kept), rejected=tuple(refused))


def _why_not(event: Event, policy: ObservationPolicy, granted: frozenset[str]) -> str | None:
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
        return _url_refusal(gesture.get("url"), policy, granted)

    if kind == "request":
        request = _mapping(event.get("request"))
        if request is None:
            return "a request event with no request in it"
        if not request.get("method"):
            return "a request with no method"
        if request.get("started_at") is None:
            return "a request with no start time cannot be attributed to an action"
        return _url_refusal(request.get("url"), policy, granted)

    if kind == "snapshot":
        if _mapping(event.get("snapshot")) is None:
            return "a snapshot event with no snapshot in it"
        if event.get("taken_at") is None:
            return "a snapshot with no time on it"
        return _url_refusal(event.get("url"), policy, granted)

    if not event.get("page_kind"):
        return "a page event that does not say what happened"
    if event.get("at") is None:
        return "a page event with no time on it"
    return _url_refusal(event.get("url"), policy, granted)


def _url_refusal(url: object, policy: ObservationPolicy, granted: frozenset[str]) -> str | None:
    if not isinstance(url, str) or not url.strip():
        return "an event with no URL cannot be checked against the policy"
    if not policy.allows(url, granted):
        # Never the URL itself: this refusal is logged and read, and the point
        # of an exclusion is that the excluded page leaves no trace here.
        return "this page is outside what the tenant agreed to observe"
    return None


def _mapping(value: object) -> Event | None:
    return value if isinstance(value, Mapping) else None
