"""Recording endpoints: start a demonstration, end it."""

from __future__ import annotations

from fastapi import APIRouter, status

from sro.application.recording.start_recording import NoSessionForSystem
from sro.domain.shared.identifiers import RecordingId
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import (
    FinishRecordingRequest,
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
) -> StartRecordingResponse:
    objective = body.objective_key.to_domain() if body.objective_key else None

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


@router.post("/{recording_id}/finish")
async def finish_recording(
    recording_id: str,
    body: FinishRecordingRequest,
    container: ContainerDep,
    ctx: ContextDep,
) -> RecordingSummary:
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
