"""A recorded call cascade, taught without anyone demonstrating it again.

Blue Yonder gives this system no API docs and no tools of its own -- what stands
in for them is `knowledge-base/http/flows/*.json`, built by driving the real
application once and keeping the exchange. A flow is shaped enough like a
demonstration that it does not need a second induction path: one synthetic
frame per recorded call, fed to the same `UnderstandRecording` a single live
teach already goes through. What it produces is trusted the same amount a
single demonstration always was -- shadow, proposed parameters, every write
withheld until somebody reviews it -- never promoted further just for having
come from evidence instead of a click.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta

from sro.application.capture.assemble import assemble_frames
from sro.application.capture.events import CaptureEvent, InputEvent, RequestEvent
from sro.application.capture.identity import derive_objective_key
from sro.application.context import RequestContext
from sro.application.induction.errors import InductionFailed
from sro.application.induction.jsonutil import JsonValue
from sro.application.induction.understand import UnderstandRecording
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.recording.element import ElementFingerprint
from sro.domain.recording.events import ActionKind, InputAction
from sro.domain.recording.network import Body, CapturedRequest
from sro.domain.recording.recording import Recording
from sro.domain.shared.identifiers import RecordingId, SkillId


def flow_to_events(flow: Mapping[str, JsonValue], *, base_time: datetime) -> list[CaptureEvent]:
    """One demonstration's worth of events, read out of a recorded cascade.

    One frame per call, never one more: a frame with a typed value and no
    request of its own still becomes a step, and a step with no network plan
    wants a live browser to replay -- exactly what this exists to avoid. So the
    call that first carries an ``applied`` field's value *is* the typing of it,
    the same self-referential frame the single-demonstration path already
    proves out: `typed_values()` finds its own action's value in its own
    request and recovers the parameter without a second, separate step.
    """
    applied = {
        name: value
        for name, value in (flow.get("applied") or {}).items()
        if isinstance(value, str) and value.strip()
    }
    claimed: set[str] = set()
    events: list[CaptureEvent] = []

    for index, call in enumerate(flow.get("calls") or []):
        request = call.get("request") or {}
        response = call.get("response") or {}
        at = base_time + timedelta(seconds=index)
        captured = _captured_request(
            request, response, index=index, at=at + timedelta(milliseconds=1)
        )
        haystack = f"{captured.url} {captured.request_text or ''}"
        typed_field = next(
            (name for name, value in applied.items() if name not in claimed and value in haystack),
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
    """Why nothing was seeded. Not an error: a flow already claimed by a skill,
    or one with nothing a task could be named from, is ordinary -- a sweep that
    treated either as a failure would log a wall of noise for a corpus that
    grows a file at a time."""


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
