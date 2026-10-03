from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime

from sro.application.capture.rig_wire import (
    Batch,
    EffectEvent,
    GestureEvent,
    RequestEvent,
    SnapshotEvent,
)
from sro.application.capture.rig_wire import Body as WireBody
from sro.application.capture.rig_wire import FrameHop as WireFrameHop
from sro.application.capture.rig_wire import Gesture as WireGesture
from sro.application.capture.rig_wire import PageEvent as WirePageEvent
from sro.application.capture.rig_wire import Request as WireRequest
from sro.domain.observation.gesture import (
    Action,
    AfterState,
    Body,
    Call,
    Component,
    FrameHop,
    Gesture,
    Landmark,
    Outline,
    OutlineField,
    OutlineMessage,
    PageMark,
    Target,
    new_gesture_id,
)
from sro.domain.observation.seen import choice_from, cookies_from, effect_from, place_from
from sro.domain.shared.hosts import system_of

__all__ = [
    "ATTRIBUTION_SECONDS",
    "as_action",
    "as_body",
    "as_call",
    "as_mark",
    "correlate",
    "correlate_with_effects",
    "system_of",
]

ATTRIBUTION_SECONDS = 10.0

logger = logging.getLogger(__name__)

_Made = tuple[int | None, tuple[FrameHop, ...] | None, str]


def _epoch(rfc3339: str) -> float:
    return datetime.fromisoformat(rfc3339).timestamp()


def _hops(frame_path: list[WireFrameHop] | None) -> tuple[FrameHop, ...] | None:
    return (
        None
        if frame_path is None
        else tuple(FrameHop(index=hop.index, url=hop.url) for hop in frame_path)
    )


def correlate(batch: Batch, tenant: str) -> tuple[list[Gesture], list[Call], list[PageMark], int]:
    gestures, orphans, marks, snapshots, _, _ = correlate_with_effects(batch, tenant)
    return gestures, orphans, marks, snapshots


def correlate_with_effects(
    batch: Batch, tenant: str
) -> tuple[list[Gesture], list[Call], list[PageMark], int, list[EffectEvent], int]:
    gestures: list[Gesture] = []
    effects: list[EffectEvent] = []
    by_moment: dict[tuple[_Made, float], list[Gesture]] = {}
    placed: set[tuple[int | None, tuple[FrameHop, ...] | None, float]] = set()
    requests: list[RequestEvent] = []
    pages: list[tuple[float, WirePageEvent]] = []
    snapshots_ignored = 0
    made: dict[_Made, Gesture] = {}
    priors: list[tuple[_Made, AfterState]] = []

    for event in batch.events:
        if isinstance(event, SnapshotEvent):
            snapshots_ignored += 1
        elif isinstance(event, GestureEvent):
            gesture = Gesture(
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
            gestures.append(gesture)
            frame = (event.tab_id, gesture.action.frame_path)
            placed.add((*frame, gesture.at))
            if event.gesture.ref is not None:
                made[(*frame, event.gesture.ref)] = gesture
                by_moment.setdefault(((*frame, event.gesture.ref), event.gesture.at), []).append(
                    gesture
                )
            prior = event.gesture.prior
            if prior is not None and event.gesture.prior_of is not None:
                after = AfterState(prior.value, prior.visible, prior.enabled)
                priors.append(((*frame, event.gesture.prior_of), after))
        elif isinstance(event, RequestEvent):
            requests.append(event)
        elif isinstance(event, WirePageEvent):
            pages.append((_epoch(event.at), event))
        elif isinstance(event, EffectEvent):
            effects.append(event)

    for key, after in priors:
        before = made.get(key)
        if before is not None:
            before.action = replace(before.action, after=after)
    left: list[EffectEvent] = []
    dropped = 0
    for one in effects:
        place = (one.tab_id, _hops(one.frame_path))
        owners = by_moment.get(((*place, one.of), one.of_at))
        effect = effect_from(one.effect.model_dump())
        if owners is None and (*place, one.of_at) not in placed:
            left.append(one)
        elif (
            owners is None
            or len(owners) != 1
            or effect is None
            or owners[0].action.effect is not None
        ):
            logger.info(
                "%s: an effect of %s was dropped, no single gesture to take it",
                batch.batch_id,
                one.of,
            )
            dropped += 1
        else:
            owners[0].action = replace(owners[0].action, effect=effect)
    gestures.sort(key=lambda gesture: gesture.at)

    orphan_requests: list[Call] = []
    for request_event in sorted(requests, key=lambda e: _epoch(e.request.started_at)):
        when = _epoch(request_event.request.started_at)
        owner = _owner(gestures, when, request_event.tab_id)
        call = as_call(request_event.request, request_event.tab_id)
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

    return gestures, orphan_requests, orphan_pages, snapshots_ignored, left, dropped


def _owner(gestures: list[Gesture], when: float, tab_id: int | None) -> Gesture | None:
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
            required=target.required,
            component=None
            if component is None
            else Component(
                item_id=component.itemId,
                query=component.query,
                field_label=component.fieldLabel,
                name=component.name,
                xtype=component.xtype,
                required=component.required,
                chain=tuple(component.chain),
            ),
            bounds=dict(target.bounds),
            attributes=dict(target.attributes),
            landmarks=tuple(Landmark(role=one.role, name=one.name) for one in target.landmarks),
            label_text=target.labelText,
            sibling_index=target.siblingIndex,
            sibling_count=target.siblingCount,
            full_name=target.fullName,
        ),
        modifiers=tuple(wire.modifiers),
        frame_path=None
        if wire.frame_path is None
        else tuple(FrameHop(index=hop.index, url=hop.url) for hop in wire.frame_path),
        detail=wire.detail,
        trusted=wire.trusted,
        outlines=tuple(
            Outline(
                headings=tuple(one.headings),
                landmarks=tuple(Landmark(role=mark.role, name=mark.name) for mark in one.landmarks),
                fields=tuple(
                    OutlineField(
                        field.role,
                        field.label,
                        field.required,
                        None if field.options is None else tuple(field.options),
                    )
                    for field in one.fields
                ),
                buttons=tuple(one.buttons),
                messages=tuple(OutlineMessage(said.role) for said in one.messages),
            )
            for one in wire.outlines
        ),
        place=None if wire.place is None else place_from(wire.place.model_dump()),
        choice=None if wire.choice is None else choice_from(wire.choice.model_dump()),
        ref=wire.ref,
    )


def as_body(body: WireBody | None) -> Body | None:
    if body is None:
        return None
    return Body(
        text=body.text,
        size_bytes=body.size_bytes,
        mime_type=body.mime_type,
        redacted_fields=tuple(body.redacted_fields),
        blob_uri=body.blob_uri,
    )


def as_call(request: WireRequest, tab_id: int | None) -> Call:
    return Call(
        method=request.method,
        url=request.url,
        request_id=request.request_id,
        started_at=_epoch(request.started_at),
        request_headers=dict(request.request_headers),
        request_body=as_body(request.request_body),
        status=request.status,
        response_body=as_body(request.response_body),
        failure_reason=request.failure_reason,
        blocked_reason=request.blocked_reason,
        tab_id=tab_id,
    )


def as_mark(event: WirePageEvent) -> PageMark:
    return PageMark(
        at=_epoch(event.at),
        page_kind=event.page_kind,
        url=event.url,
        detail=event.detail,
        tab_id=event.tab_id,
        opener_tab_id=event.opener_tab_id,
        cookies=cookies_from([one.model_dump() for one in event.cookies]),
        mail_thread=event.mail_thread,
    )
