"""A1 — a request belongs to the gesture that caused it, or to nobody.

The existing pipeline learned this against a real browser: a request arriving
after a drain belongs to the previous action, and only traffic with no owning
gesture at all is an orphan. Orphans are stored, not discarded — a background
poll is evidence that a background poll happened.
"""

from datetime import datetime
from urllib.parse import urlparse

from rig.records import Gesture, new_gesture_id
from rig.wire import Batch, GestureEvent, PageEvent, Request, RequestEvent

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


def correlate(batch: Batch, tenant: str) -> tuple[list[Gesture], list[Request]]:
    gestures: list[Gesture] = []
    requests: list[tuple[float, int | None, Request]] = []
    pages: list[tuple[float, PageEvent]] = []

    for event in batch.events:
        if isinstance(event, GestureEvent):
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
                )
            )
        elif isinstance(event, RequestEvent):
            requests.append((_epoch(event.request.started_at), event.tab_id, event.request))
        elif isinstance(event, PageEvent):
            pages.append((_epoch(event.at), event))

    gestures.sort(key=lambda gesture: gesture.at)

    orphans: list[Request] = []
    for when, tab_id, request in sorted(requests, key=lambda triple: triple[0]):
        owner = _owner(gestures, when, tab_id)
        if owner is None:
            orphans.append(request)
        else:
            owner.requests.append(request)

    for when, page in sorted(pages, key=lambda pair: pair[0]):
        owner = _owner(gestures, when, page.tab_id)
        if owner is not None:
            owner.page_events.append(page)

    return gestures, orphans


def _owner(gestures: list[Gesture], when: float, tab_id: int | None) -> Gesture | None:
    """The last gesture in the same tab, within the attribution window."""
    best: Gesture | None = None
    for gesture in gestures:
        if gesture.at > when:
            break
        if tab_id is not None and gesture.tab_id != tab_id:
            continue
        if when - gesture.at > ATTRIBUTION_SECONDS:
            continue
        best = gesture
    return best
