"""The call a mined gesture caused, as a plan a run can replay.

`from_rig` builds the gesture half of a step and `version_from_rig` assembles
those into a version. Both stop at the screen. This is the other recipe -- see
ADR 005 -- and it is the difference between a skill that can climb the ladder
and one that cannot: `SkillVersion.needs_a_person` is true of any version with
a step carrying no network plan, `judge` makes every run of one DEGRADED, and
DEGRADED resets the clean streak. Measured before this existed: all eight
workflows mined from the real corpus needed a person on all 165 steps, so not
one of them could ever have reached the top of the ladder, however many times
it ran perfectly.

The rig stores the requests each gesture caused, so the evidence was already
there. What was missing was the reading.

**Which call a gesture is about** is `network.primary_of`, called rather than
restated -- the induction path's rule, with its reasoning about analytics
noise, keep-alives and the path-before-time ordering that stopped two runs of
one task looking like they diverged. The rig captures no `initiator`, so a rig
request degrades from the rule's first rung to its second: a successful
mutation, just not one known to have come from a click handler.

**What this cannot supply, on this corpus.** Measured over all 291 stored
requests: the only `authorization` header anywhere is on twelve `localhost`
calls, which are the rig talking to its own ingest. Every business call to the
real WMS authenticates by cookie, and the rig captures no cookies -- so no
plan built from this evidence carries a credential reference, because no
credential was observed. A replay therefore depends on the executor's own
session. That is a fact about the capture rather than a decision here, and
inventing a SESSION header to hang a vault key on would be worse than the gap:
it would make an unauthenticated plan look authenticated.

The 544 CSRF headers ARE handled, and they are the ones that matter for a
write: stale by construction, minted live, and the plan records that the call
requires one.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from sro.application.induction.headers import build_header_plans
from sro.domain.recording.network import Body, CapturedRequest, RedirectHop, primary_of
from sro.domain.skill.plan import NetworkPlan
from sro.domain.skill.template import Template

_UNREPLAYABLE_RESOURCE_TYPES = frozenset({"websocket"})


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _when(value: object) -> datetime | None:
    """A stored ISO timestamp, or None when it is not one.

    `CapturedRequest` refuses a naive datetime, and the rig writes `Z`, which
    `fromisoformat` reads only from 3.11 on. Nothing here guesses a timezone:
    a request with no readable time keeps its place by list order instead,
    which is what `primary_of`'s path-before-time ordering already prefers.
    """
    text = _text(value)
    if text is None:
        return None
    try:
        when = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return when if when.tzinfo is not None else None


def _sequence(value: object) -> Sequence[object]:
    """A stored list, or nothing. A JSON null where a list belongs is not a list."""
    return value if isinstance(value, list) else ()


def _epoch(value: object) -> datetime | None:
    """A stored epoch-seconds clock, which is how the rig writes a gesture's."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    try:
        return datetime.fromtimestamp(value, tz=UTC)
    except (OSError, OverflowError, ValueError):
        return None


def _headers(value: object) -> dict[str, str]:
    return {
        name: text
        for name, raw in _mapping(value).items()
        if isinstance(name, str) and name.strip() and (text := _text(raw)) is not None
    }


def _body(value: object) -> Body | None:
    """A stored body, which the rig keeps as a dict beside its own metadata."""
    found = _mapping(value)
    if not found:
        return None
    text = _text(found.get("text"))
    if text is None:
        return None
    return Body(
        text=text,
        size_bytes=_int(found.get("size_bytes")) or len(text),
        mime_type=_text(found.get("mime_type")),
        encoding=_text(found.get("encoding")),
    )


def request_from_rig(stored: Mapping[str, object], *, at: datetime) -> CapturedRequest | None:
    """One stored exchange as the domain's, or None where it is not one.

    `at` is the fallback timestamp -- the gesture's own -- for a request whose
    stored `started_at` cannot be read. A CapturedRequest must have an aware
    one, and the alternative to a fallback is dropping real evidence over a
    clock format.
    """
    method, url = _text(stored.get("method")), _text(stored.get("url"))
    if not method or not url:
        return None
    return CapturedRequest(
        request_id=_text(stored.get("request_id")) or url,
        method=method,
        url=url,
        resource_type=_text(stored.get("resource_type")) or "xhr",
        started_at=_when(stored.get("started_at")) or at,
        request_headers=_headers(stored.get("request_headers")),
        request_body=_body(stored.get("request_body")),
        status=_int(stored.get("status")),
        status_text=_text(stored.get("status_text")),
        response_headers=_headers(stored.get("response_headers")),
        response_body=_body(stored.get("response_body")),
        redirect_chain=tuple(
            RedirectHop(
                url=hop_url,
                status=_int(hop.get("status")) or 0,
                location=_text(hop.get("location")),
            )
            for hop in _sequence(stored.get("redirect_chain"))
            if isinstance(hop, Mapping) and (hop_url := _text(hop.get("url")))
        ),
        duration_ms=_int(stored.get("duration_ms")),
        from_cache=stored.get("from_cache") is True,
        failure_reason=_text(stored.get("failure_reason")),
        blocked_reason=_text(stored.get("blocked_reason")),
    )


def network_plan_for_gesture(
    gesture: Mapping[str, object],
    requests: Sequence[object],
    *,
    target_system: str,
    facility: str,
    bindings: Mapping[str, frozenset[str]] | None = None,
) -> NetworkPlan | None:
    """The call this gesture caused, as a plan, or None where it caused none.

    `requests` is `Sequence[object]` rather than a sequence of mappings because
    that is what it is: rows off `json.loads`, out of a column, shaped by
    whatever wrote them. Promising a narrower type here would make the guard
    below unreachable to a type checker and reachable to a real payload.

    None is the ordinary answer and not a failure: most gestures are a click
    that moved focus. Measured on the real corpus, 78 of 387 gestures carry any
    request at all.
    """
    # The gesture's own clock, where it has a readable one. It is only ever a
    # FALLBACK for a request that stored no usable time of its own, so a
    # gesture with no clock costs nothing as long as its requests have theirs.
    # Refusing the whole gesture on a missing `at` threw away every call it
    # caused over a field none of them needed.
    at = _when(gesture.get("at")) or _epoch(gesture.get("at"))

    captured = []
    for stored in requests:
        if not isinstance(stored, Mapping):
            continue
        when = _when(stored.get("started_at")) or at
        if when is None:
            # Neither clock is readable. `CapturedRequest` refuses a naive
            # datetime and inventing one would order this call against the
            # others by a time nobody observed.
            continue
        request = request_from_rig(stored, at=when)
        if request is not None:
            captured.append(request)
    primary = primary_of(captured)
    if primary is None:
        return None

    body = primary.request_body
    return NetworkPlan(
        method=primary.method.upper(),
        url=Template(raw=_bind(primary.url, bindings)),
        headers=build_header_plans(primary, target_system=target_system, facility=facility),
        body=Template(raw=_bind(body.text, bindings)) if body and body.text else None,
        expected_status=primary.status,
        content_type=primary.request_headers.get("Content-Type")
        or primary.request_headers.get("content-type"),
        replayable=primary.resource_type.lower() not in _UNREPLAYABLE_RESOURCE_TYPES,
    )


def _bind(raw: str, bindings: Mapping[str, frozenset[str]] | None) -> str:
    """Values the job is known to vary, as the names it varies under.

    A JSON body is where the rig's parameters actually land -- the two the rig
    derived from the SCREEN, `workArea` and `workAreaDescription`, are two keys
    of the POST that creates a work area -- so this substitutes by KEY and never
    by scanning the text. A blind string replacement would rewrite the same
    characters wherever else they appeared, and a work area named `SG` would
    have rewritten the site id sitting beside it in the same body.

    Everything not bound is escaped, because `Template` is `string.Template`:
    a literal `$` in a captured body would otherwise report itself as a
    parameter the plan needs and either raise on render or substitute something
    nobody typed. The placeholders are written through a sentinel so the escape
    pass cannot eat the very `$` this is trying to produce.
    """
    if not bindings:
        return raw.replace("$", "$$")
    try:
        loaded = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return raw.replace("$", "$$")
    if not isinstance(loaded, dict):
        return raw.replace("$", "$$")

    # A printable token, because `json.dumps` escapes a control character --
    # `\x00` came back as the six characters `\u0000` and the swap below found
    # nothing, leaving the sentinel in the body. Checked against the text
    # first: a body that already contains it is left alone rather than
    # corrupted, which costs a binding and never a payload.
    sentinel = "@@SRO-PARAM-{}@@"
    if "@@SRO-PARAM-" in raw:
        return raw.replace("$", "$$")
    bound: dict[str, object] = {}
    named: list[str] = []
    for key, value in loaded.items():
        if isinstance(value, str) and value in bindings.get(key, frozenset()):
            bound[key] = sentinel.format(len(named))
            named.append(key)
        else:
            bound[key] = value
    text = json.dumps(bound, ensure_ascii=False).replace("$", "$$")
    for index, key in enumerate(named):
        text = text.replace(sentinel.format(index), f"${key}")
    return text
