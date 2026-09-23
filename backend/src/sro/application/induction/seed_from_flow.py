from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta

from sro.application.capture.assemble import assemble_frames
from sro.application.capture.events import CaptureEvent, InputEvent, RequestEvent
from sro.application.capture.identity import derive_objective_key
from sro.application.context import RequestContext
from sro.application.induction.errors import InductionFailed
from sro.application.induction.jsonutil import JsonValue, as_text, leaves
from sro.application.induction.sites import parse_json, url_path_segments, url_query_pairs
from sro.application.induction.understand import UnderstandRecording
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.recording.element import ElementFingerprint
from sro.domain.recording.events import ActionKind, InputAction
from sro.domain.recording.network import Body, CapturedRequest
from sro.domain.recording.recording import Recording
from sro.domain.shared.identifiers import RecordingId, SkillId


def _addressable_values(request: CapturedRequest) -> set[str]:
    values = set(url_path_segments(request.url))
    values.update(value for _, value in url_query_pairs(request.url))
    document = parse_json(request.request_text)
    if document is not None:
        values.update(as_text(leaf) for _, leaf in leaves(document))
    return values


def flow_to_events(flow: Mapping[str, JsonValue], *, base_time: datetime) -> list[CaptureEvent]:
    calls = flow.get("calls") or []
    if not all(
        isinstance(call.get("request"), Mapping) and call["request"].get("url") for call in calls
    ):
        return []

    applied = {
        name: value
        for name, value in (flow.get("applied") or {}).items()
        if isinstance(value, str) and value.strip()
    }
    claimed: set[str] = set()
    events: list[CaptureEvent] = []

    for index, call in enumerate(calls):
        request = call.get("request") or {}
        response = call.get("response") or {}
        at = base_time + timedelta(seconds=index)
        captured = _captured_request(
            request, response, index=index, at=at + timedelta(milliseconds=1)
        )
        addressable = _addressable_values(captured)
        typed_field = next(
            (
                name
                for name, value in applied.items()
                if name not in claimed and value in addressable
            ),
            None,
        )
        if typed_field is not None:
            claimed.add(typed_field)
            action = InputAction(
                kind=ActionKind.TYPE,
                target=ElementFingerprint(accessible_name=typed_field),
                value=applied[typed_field],
            )
        else:
            action = InputAction(
                kind=ActionKind.NAVIGATE, value=call.get("endpoint") or captured.url
            )
        events.append(InputEvent(at=at, action=action))
        events.append(RequestEvent(request=captured))
    return events


def _captured_request(
    request: Mapping[str, JsonValue], response: Mapping[str, JsonValue], *, index: int, at: datetime
) -> CapturedRequest:
    request_headers = request.get("headers") or {}
    response_headers = response.get("headers") or {}
    return CapturedRequest(
        request_id=f"flow-{index}",
        method=str(request.get("method") or "GET"),
        url=str(request.get("url") or ""),
        resource_type="xhr",
        started_at=at,
        request_headers=request_headers,
        request_body=_body(request.get("body"), request_headers),
        status=response.get("status"),
        response_headers=response_headers,
        response_body=_body(response.get("body"), response_headers),
    )


def _body(text: object, headers: Mapping[str, str]) -> Body | None:
    if not isinstance(text, str):
        return None
    return Body(text=text, size_bytes=len(text.encode()), mime_type=headers.get("content-type"))


@dataclass(frozen=True, slots=True)
class Seeded:
    skill_id: SkillId | None
    recording_id: RecordingId | None
    skipped: str | None = None


class SeedSkillFromFlow:
    def __init__(
        self, uow: UnitOfWork, clock: Clock, ids: IdFactory, understand: UnderstandRecording
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._ids = ids
        self._understand = understand

    async def execute(
        self,
        ctx: RequestContext,
        *,
        flow: Mapping[str, JsonValue],
        system: str,
        label: str | None = None,
    ) -> Seeded:
        now = self._clock.now()
        assembled = assemble_frames(flow_to_events(flow, base_time=now))
        if not assembled.frames:
            return Seeded(skill_id=None, recording_id=None, skipped="this flow has no calls")

        objective = derive_objective_key(assembled.frames, system=system)
        if objective is None:
            return Seeded(
                skill_id=None,
                recording_id=None,
                skipped="nothing in this flow says what task it was",
            )

        async with self._uow as uow:
            existing = await uow.skills.find_by_objective(ctx.tenant_id, objective)
        if existing is not None:
            return Seeded(skill_id=existing.id, recording_id=None, skipped="already seeded")

        recording = Recording(
            id=self._ids.new_recording_id(),
            tenant_id=ctx.tenant_id,
            demonstrator=ctx.principal_id,
            started_at=now,
            label=label or str(flow.get("resource") or flow.get("spec") or "seeded flow"),
        )
        for frame in assembled.frames:
            recording.append_frame(frame)
        recording.name_objective(objective)
        recording.seal(now)

        async with self._uow as uow:
            await uow.recordings.add(recording)
            await uow.commit()

        try:
            understood = await self._understand.execute(
                ctx, recording_id=recording.id, name=recording.label
            )
        except InductionFailed as thin:
            return Seeded(skill_id=None, recording_id=recording.id, skipped=str(thin))

        return Seeded(skill_id=understood.skill_id, recording_id=recording.id)
