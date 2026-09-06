"""A1 — a request belongs to the gesture that caused it, or to nobody.

The existing pipeline learned this against a real browser: a request arriving
after a drain belongs to the previous action, and only traffic with no owning
gesture at all is an orphan. Orphans are stored, not discarded — a background
poll is evidence that a background poll happened.
"""

from __future__ import annotations

from datetime import datetime

from sro.application.capture.rig_wire import Batch, GestureEvent, RequestEvent, SnapshotEvent
from sro.application.capture.rig_wire import Body as WireBody
from sro.application.capture.rig_wire import Gesture as WireGesture
from sro.application.capture.rig_wire import PageEvent as WirePageEvent
from sro.application.capture.rig_wire import Request as WireRequest
from sro.domain.observation.gesture import (
    Action,
    Body,
    Call,
    Component,
    Gesture,
    PageMark,
    Target,
    new_gesture_id,
)
from sro.domain.shared.hosts import system_of

__all__ = [
    "ATTRIBUTION_SECONDS",
    "as_action",
    "as_body",
    "as_call",
    "as_mark",
    "correlate",
    "system_of",
]

ATTRIBUTION_SECONDS = 10.0


def _epoch(rfc3339: str) -> float:
    return datetime.fromisoformat(rfc3339).timestamp()


def correlate(batch: Batch, tenant: str) -> tuple[list[Gesture], list[Call], list[PageMark], int]:
    """Returns (gestures, orphan requests, orphan pages, snapshots ignored).

    Accessibility-tree snapshots are deliberately out of scope for this plan
    -- there is nowhere in the schema to put one -- but silently dropping
    them is not the same as never having received them. The count is the
    difference: it says a batch had snapshots even though nothing stores them.
    """
    gestures: list[Gesture] = []
    requests: list[RequestEvent] = []
    pages: list[tuple[float, WirePageEvent]] = []
    snapshots_ignored = 0

    for event in batch.events:
        if isinstance(event, SnapshotEvent):
            snapshots_ignored += 1
        elif isinstance(event, GestureEvent):
            gestures.append(
                Gesture(
                    id=new_gesture_id(),
                    tenant=tenant,
                    stream_id=batch.device_id,
                    batch_id=batch.batch_id,
                    at=event.gesture.at,
                    url=event.gesture.url,
                    system=system_of(event.gesture.url),
                    tab_id=event.tab_id,
                    frame_url=event.frame_url,
                    action=as_action(event.gesture),
                    page_url=event.page_url,
                )
            )
        elif isinstance(event, RequestEvent):
            requests.append(event)
        elif isinstance(event, WirePageEvent):
            pages.append((_epoch(event.at), event))

    gestures.sort(key=lambda gesture: gesture.at)

    orphan_requests: list[Call] = []
    for request_event in sorted(requests, key=lambda e: _epoch(e.request.started_at)):
        when = _epoch(request_event.request.started_at)
        owner = _owner(gestures, when, request_event.tab_id)
        call = as_call(request_event.request)
        if owner is None:
            orphan_requests.append(call)
        else:
            owner.requests.append(call)

    orphan_pages: list[PageMark] = []
    for when, page in sorted(pages, key=lambda pair: pair[0]):
        owner = _nearest_owner(gestures, when, page.tab_id)
        mark = as_mark(page)
        if owner is None:
            orphan_pages.append(mark)
        else:
            owner.page_events.append(mark)

    return gestures, orphan_requests, orphan_pages, snapshots_ignored


def _owner(gestures: list[Gesture], when: float, tab_id: int | None) -> Gesture | None:
    """The last gesture in the same tab, within the attribution window.

    Tab matching is strict equality: a request whose tab we cannot establish
    (tab_id is None) is orphaned on purpose, never guessed at — missing
    evidence means "I cannot prove this belongs to that gesture", not
    "attach it to the nearest one".
    """
    best: Gesture | None = None
    for gesture in gestures:
        if gesture.at > when:
            break
        if gesture.tab_id != tab_id:
            continue
        if when - gesture.at > ATTRIBUTION_SECONDS:
            continue
        best = gesture
    return best


def _nearest_owner(gestures: list[Gesture], when: float, tab_id: int | None) -> Gesture | None:
    """The closest gesture in time, in the same tab, within the window.

    Requests attach backwards only: a call is caused by the gesture before
    it. A page event is different in kind — a navigation typically lands
    *before* the gesture it gives context to (the operator arrives, then
    acts) — so it may attach to a gesture on either side, whichever is
    nearer in time.
    """
    best: Gesture | None = None
    best_distance: float | None = None
    for gesture in gestures:
        if gesture.tab_id != tab_id:
            continue
        distance = abs(gesture.at - when)
        if distance > ATTRIBUTION_SECONDS:
            continue
        if best_distance is None or distance < best_distance:
            best = gesture
            best_distance = distance
    return best


def as_action(wire: WireGesture) -> Action:
    """The wire gesture as the domain sees it: the fields the arithmetic
    reads, and nothing the recorder might add next week."""
    target = wire.target
    component = target.component if target else None
    return Action(
        kind=wire.kind,
        value=wire.value,
        secret=wire.secret,
        at=wire.at,
        url=wire.url,
        target=None
        if target is None
        else Target(
            tag=target.tag,
            role=target.role,
            name=target.name,
            secret=target.secret,
            text=target.text,
            test_id=target.testId,
            css_path=target.cssPath,
            xpath=target.xpath,
            component=None
            if component is None
            else Component(
                item_id=component.itemId,
                query=component.query,
                field_label=component.fieldLabel,
                name=component.name,
                xtype=component.xtype,
            ),
        ),
    )


def as_body(body: WireBody | None) -> Body | None:
    """A wire body as the domain sees it: no encoding field, nothing the
    belts don't read."""
    if body is None:
        return None
    return Body(
        text=body.text,
        size_bytes=body.size_bytes,
        mime_type=body.mime_type,
        redacted_fields=tuple(body.redacted_fields),
        blob_uri=body.blob_uri,
    )


def as_call(request: WireRequest) -> Call:
    """A wire request as the domain sees it: never the tab it arrived on,
    the id it was minted with, or anything else only the wire event carried."""
    return Call(
        method=request.method,
        url=request.url,
        request_headers=dict(request.request_headers),
        request_body=as_body(request.request_body),
        status=request.status,
        response_body=as_body(request.response_body),
    )


def as_mark(event: WirePageEvent) -> PageMark:
    """A wire page event as the domain sees it."""
    return PageMark(
        at=_epoch(event.at),
        page_kind=event.page_kind,
        url=event.url,
        detail=event.detail,
    )
