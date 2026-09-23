"""Recording endpoints: start a demonstration, attach media, end it."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from sro.application.recording.start_recording import NoSessionForSystem
from sro.domain.recording.artifact import ArtifactKind
from sro.domain.shared.identifiers import DeviceId, RecordingId
from sro.domain.shared.objective import Direction, ObjectiveKey
from sro.interface.http.deps import ContainerDep, ContextDep, DeviceSecretDep
from sro.interface.http.schemas import (
    ArtifactModel,
    FinishRecordingRequest,
    LiveViewResponse,
    MediaModel,
    RecordingDetail,
    RecordingSummary,
    StartRecordingRequest,
    StartRecordingResponse,
)

router = APIRouter(prefix="/recordings", tags=["recordings"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def start_recording(
    body: StartRecordingRequest,
    container: ContainerDep,
    ctx: ContextDep,
    x_device_secret: DeviceSecretDep = "",
) -> StartRecordingResponse:
    objective = body.objective_key.to_domain() if body.objective_key else None

    if body.device_id:
        started = await container.start_recording().execute(
            ctx,
            objective_key=objective,
            label=body.label,
            device_id=DeviceId(body.device_id),
            device_secret=x_device_secret,
        )
        return StartRecordingResponse(
            recording_id=started.recording_id.value, live_view_url=started.live_view_url
        )

    if not body.attach_to:
        await container.ensure_signed_in().for_url(ctx, body.start_url)
    started = await container.start_recording().execute(
        ctx,
        objective_key=objective,
        start_url=body.start_url,
        label=body.label,
        attach_to=body.attach_to,
    )
    session_cookies = (
        ()
        if body.attach_to or not started.target_system
        else await container.load_session().execute(ctx, target_system=started.target_system)
    )
    if started.target_system and not body.attach_to and not session_cookies:
        await container.finish_recording().abandon(
            ctx,
            recording_id=started.recording_id,
            reason=f"nobody is signed in to {started.target_system}",
        )
        raise NoSessionForSystem(
            f"nobody is signed in to {started.target_system}. Connect it once and every "
            "teaching session after that starts already signed in."
        )

    await container.capture.start(
        ctx,
        recording_id=started.recording_id,
        debugger_url=started.debugger_url,
        start_url=body.start_url if not body.attach_to else None,
        session_cookies=session_cookies,
    )
    if started.browser_session_id is not None:
        await container.durable.watch_recording(
            ctx,
            recording_id=started.recording_id,
            browser_session_id=started.browser_session_id,
            timeout_seconds=container.settings.steel_session_timeout_seconds,
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

    recordings = await container.list_recordings().execute(
        ctx, objective_key=objective, limit=limit, offset=offset
    )
    return [RecordingSummary.of(r) for r in recordings]


@router.get("/{recording_id}")
async def get_recording(
    recording_id: str, container: ContainerDep, ctx: ContextDep
) -> RecordingDetail:
    recording = await container.get_recording().execute(ctx, recording_id=RecordingId(recording_id))
    return RecordingDetail.of_recording(recording)


@router.get("/{recording_id}/live-view")
async def get_live_view(
    recording_id: str, container: ContainerDep, ctx: ContextDep
) -> LiveViewResponse:
    """Null when the demonstration is over or the provider has reaped it."""
    url = await container.get_live_view().execute(ctx, recording_id=RecordingId(recording_id))
    return LiveViewResponse(live_view_url=url)


@router.get("/{recording_id}/media")
async def get_media(
    recording_id: str, container: ContainerDep, ctx: ContextDep
) -> list[MediaModel]:
    """Playback links, minted per request and short-lived."""
    media = await container.get_recording_media().execute(
        ctx, recording_id=RecordingId(recording_id)
    )
    return [
        MediaModel(
            kind=item.kind.value,
            url=item.url,
            content_type=item.content_type,
            size_bytes=item.size_bytes,
            duration_ms=item.duration_ms,
            frame_index=item.frame_index,
        )
        for item in media
    ]


@router.post("/{recording_id}/artifacts", status_code=status.HTTP_201_CREATED)
async def attach_artifact(
    recording_id: str,
    container: ContainerDep,
    ctx: ContextDep,
    kind: Annotated[ArtifactKind, Form()],
    file: Annotated[UploadFile, File()],
    duration_ms: Annotated[int | None, Form()] = None,
    recorded_from: Annotated[datetime | None, Form()] = None,
) -> ArtifactModel:
    """``recorded_from`` is when the microphone started, for audio.

    Without it a transcript's offsets cannot be placed against the frames, and
    narration attaches to the wrong steps -- which is worse than none.
    """
    data = await file.read()
    result = await container.attach_artifact().execute(
        ctx,
        recording_id=RecordingId(recording_id),
        kind=kind,
        data=data,
        content_type=file.content_type or "application/octet-stream",
        duration_ms=duration_ms,
        recorded_from=recorded_from,
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
    demonstration = await container.get_recording().execute(
        ctx, recording_id=RecordingId(recording_id)
    )

    if demonstration.device_id is not None:
        if not body.abandon_reason:
            await container.assemble_demonstration().execute(
                ctx, recording_id=RecordingId(recording_id)
            )
    else:
        await container.refresh_session().execute(
            ctx, cookies=await container.capture.snapshot_cookies(RecordingId(recording_id))
        )

        await container.capture.stop(ctx, recording_id=RecordingId(recording_id))

    await container.durable.recording_finished(ctx, recording_id=RecordingId(recording_id))

    use_case = container.finish_recording()
    recording = (
        await use_case.abandon(
            ctx, recording_id=RecordingId(recording_id), reason=body.abandon_reason
        )
        if body.abandon_reason
        else await use_case.seal(
            ctx,
            recording_id=RecordingId(recording_id),
            objective_key=body.objective_key.to_domain() if body.objective_key else None,
        )
    )
    return RecordingSummary.of(recording)
