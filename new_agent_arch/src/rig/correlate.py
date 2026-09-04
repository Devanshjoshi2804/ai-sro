"""A1 — a request belongs to the gesture that caused it, or to nobody.

The existing pipeline learned this against a real browser: a request arriving
after a drain belongs to the previous action, and only traffic with no owning
gesture at all is an orphan. Orphans are stored, not discarded — a background
poll is evidence that a background poll happened.
"""

from datetime import datetime
from urllib.parse import urlparse

from rig.records import Gesture, new_gesture_id
from rig.wire import Batch, GestureEvent, PageEvent, RequestEvent, SnapshotEvent

ATTRIBUTION_SECONDS = 10.0


def system_of(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _epoch(rfc3339: str) -> float:
    return datetime.fromisoformat(rfc3339).timestamp()


def correlate(
    batch: Batch, tenant: str
) -> tuple[list[Gesture], list[RequestEvent], list[PageEvent], int]:
    """Returns (gestures, orphan requests, orphan pages, snapshots ignored).

    Accessibility-tree snapshots are deliberately out of scope for this plan
    -- there is nowhere in the schema to put one -- but silently dropping
    them is not the same as never having received them. The count is the
    difference: it says a batch had snapshots even though nothing stores them.
    """
    gestures: list[Gesture] = []
    requests: list[RequestEvent] = []
    pages: list[tuple[float, PageEvent]] = []
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
                    gesture=event.gesture,
                    page_url=event.page_url,
                )
            )
        elif isinstance(event, RequestEvent):
            requests.append(event)
        elif isinstance(event, PageEvent):
            pages.append((_epoch(event.at), event))

    gestures.sort(key=lambda gesture: gesture.at)

    orphan_requests: list[RequestEvent] = []
    for request_event in sorted(requests, key=lambda e: _epoch(e.request.started_at)):
        when = _epoch(request_event.request.started_at)
        owner = _owner(gestures, when, request_event.tab_id)
        if owner is None:
            orphan_requests.append(request_event)
        else:
            owner.requests.append(request_event.request)

    orphan_pages: list[PageEvent] = []
    for when, page in sorted(pages, key=lambda pair: pair[0]):
        owner = _nearest_owner(gestures, when, page.tab_id)
        if owner is None:
            orphan_pages.append(page)
        else:
            owner.page_events.append(page)

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
