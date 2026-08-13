"""Recording endpoints: start a demonstration, attach media, end it."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from sro.domain.recording.artifact import ArtifactKind
from sro.domain.shared.identifiers import RecordingId
from sro.domain.shared.objective import Direction, ObjectiveKey
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import (
    ArtifactModel,
    FinishRecordingRequest,
    RecordingDetail,
    RecordingSummary,
    StartRecordingRequest,
    StartRecordingResponse,
)

router = APIRouter(prefix="/recordings", tags=["recordings"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def start_recording(
    body: StartRecordingRequest, container: ContainerDep, ctx: ContextDep
) -> StartRecordingResponse:
    started = await container.start_recording().execute(
        ctx,
        objective_key=ObjectiveKey(
            objective_type=body.objective_key.objective_type,
            target_system=body.objective_key.target_system,
            entity_type=body.objective_key.entity_type,
            facility=body.objective_key.facility,
            direction=body.objective_key.direction,
        ),
        start_url=body.start_url,
        label=body.label,
    )
    # Capture starts only once the recording is durable: attaching first would
    # leave a live CDP session with nowhere to put what it records.
    await container.capture.start(
        ctx, recording_id=started.recording_id, debugger_url=started.debugger_url
    )
    return StartRecordingResponse(
        recording_id=started.recording_id.value,
        live_view_url=started.live_view_url,
    )


@router.get("")
async def list_recordings(
    container: ContainerDep,
    ctx: ContextDep,
    objective_type: Annotated[str | None, Query()] = None,
    target_system: Annotated[str | None, Query()] = None,
    entity_type: Annotated[str | None, Query()] = None,
    facility: Annotated[str | None, Query()] = None,
    direction: Annotated[Direction | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[RecordingSummary]:
    parts = (objective_type, target_system, entity_type, facility, direction)
    # An objective key is all five fields or none: a partial filter would silently
    # match the wrong demonstrations, which is worse than refusing to filter.
    objective = (
        ObjectiveKey(
            objective_type=objective_type or "",
            target_system=target_system or "",
            entity_type=entity_type or "",
            facility=facility or "",
            direction=direction or Direction.OUTBOUND,
        )
        if all(part is not None for part in parts)
        else None
    )

    uow = container.unit_of_work()
    async with uow as unit:
        recordings = await unit.recordings.list_for_tenant(
            ctx.tenant_id, objective_key=objective, limit=limit, offset=offset
        )
    return [RecordingSummary.of(r) for r in recordings]


@router.get("/{recording_id}")
async def get_recording(
    recording_id: str, container: ContainerDep, ctx: ContextDep
) -> RecordingDetail:
    uow = container.unit_of_work()
    async with uow as unit:
        recording = await unit.recordings.get(ctx.tenant_id, RecordingId(recording_id))
    return RecordingDetail.of_recording(recording)


@router.post("/{recording_id}/artifacts", status_code=status.HTTP_201_CREATED)
async def attach_artifact(
    recording_id: str,
    container: ContainerDep,
    ctx: ContextDep,
    kind: Annotated[ArtifactKind, Form()],
    file: Annotated[UploadFile, File()],
    duration_ms: Annotated[int | None, Form()] = None,
) -> ArtifactModel:
    data = await file.read()
    result = await container.attach_artifact().execute(
        ctx,
        recording_id=RecordingId(recording_id),
        kind=kind,
        data=data,
        content_type=file.content_type or "application/octet-stream",
        duration_ms=duration_ms,
    )
    return ArtifactModel(
        kind=kind.value,
        uri=result.uri,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(data),
        frame_index=None,
        label=None,
    )


@router.post("/{recording_id}/finish")
async def finish_recording(
    recording_id: str,
    body: FinishRecordingRequest,
    container: ContainerDep,
    ctx: ContextDep,
) -> RecordingSummary:
    # Drain and detach before sealing: a sealed recording rejects appends, so
    # anything still buffered would be lost with no error to show for it.
    await container.capture.stop(ctx, recording_id=RecordingId(recording_id))

    use_case = container.finish_recording()
    recording = (
        await use_case.abandon(
            ctx, recording_id=RecordingId(recording_id), reason=body.abandon_reason
        )
        if body.abandon_reason
        else await use_case.seal(ctx, recording_id=RecordingId(recording_id))
    )
    return RecordingSummary.of(recording)
