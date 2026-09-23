"""What an operator's browser saw, arriving in batches.

Both doors here take an authenticated but *operator-controlled* payload: an
extension on somebody's laptop decides how much to send. So both wear the rig's
size belts (`new_agent_arch/src/rig/api.py:374`, `:379`), with the rig's
measurements kept beside the numbers in `sro.config`.

**413 and not 422.** Pydantic's `max_length` on the event list would answer 422
for free, and 422 says the body is malformed. These bodies are not malformed;
they are too big, which is a different thing a sender acts on differently -- a
422 is retried never, a 413 is retried in two halves. So the bound is an
explicit check that raises the status the meaning demands, and not a constraint
whose status would then need translating back.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from sro.domain.recording.artifact import ArtifactKind
from sro.domain.shared.identifiers import BatchId, DeviceId, RecordingId
from sro.interface.http.deps import ContainerDep, ContextDep, DeviceSecretDep
from sro.interface.http.schemas import (
    TOO_LARGE,
    ForgottenResponse,
    ObservationAcceptedResponse,
    ObservationArtifactResponse,
    ObservationBatchRequest,
    RejectedEventModel,
)

router = APIRouter(prefix="/observations", tags=["observations"])


@router.post("", status_code=status.HTTP_202_ACCEPTED, responses=TOO_LARGE)
async def ingest_observations(
    body: ObservationBatchRequest,
    container: ContainerDep,
    ctx: ContextDep,
    x_device_secret: DeviceSecretDep = "",
) -> ObservationAcceptedResponse:
    """Accepted, not processed: the evidence is stored and read later.

    Rejections come back on this response rather than going to a log. A malformed
    event is a bug in a version of the extension, and it has to be found on the
    day it ships rather than in a mining run three weeks later that quietly saw
    fewer tasks than happened.
    """
    if len(body.events) > container.settings.observation_batch_events:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=(
                f"{len(body.events)} events in one batch; "
                f"at most {container.settings.observation_batch_events}"
            ),
        )
    ingested = await container.ingest_observation().execute(
        ctx,
        device_id=DeviceId(body.device_id),
        secret=x_device_secret,
        batch_id=BatchId(body.batch_id),
        started_at=body.started_at,
        ended_at=body.ended_at,
        mode=body.mode,
        events=body.events,
        recording_id=RecordingId(body.recording_id) if body.recording_id else None,
    )
    return ObservationAcceptedResponse(
        batch_id=ingested.batch_id.value,
        accepted=ingested.accepted,
        rejected=len(ingested.rejected),
        problems=[RejectedEventModel.of(rejected) for rejected in ingested.rejected],
        stored_at=ingested.stored_at,
        already_had_it=ingested.already_had_it,
        snapshots_ignored=ingested.snapshots_ignored,
    )


@router.post("/artifacts", status_code=status.HTTP_201_CREATED, responses=TOO_LARGE)
async def store_artifact(
    container: ContainerDep,
    ctx: ContextDep,
    device_id: Annotated[str, Form()],
    batch_id: Annotated[str, Form()],
    kind: Annotated[ArtifactKind, Form()],
    file: Annotated[UploadFile, File()],
    frame_index: Annotated[int | None, Form()] = None,
    label: Annotated[str | None, Form()] = None,
    x_device_secret: DeviceSecretDep = "",
) -> ObservationArtifactResponse:
    """Screenshots and oversized bodies. No row: the key says which batch and
    which frame, so a miner finds them by prefix and a retention rule expires
    them with the evidence they illustrate."""
    data = await file.read(container.settings.observation_artifact_bytes + 1)
    if len(data) > container.settings.observation_artifact_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"an artifact is at most {container.settings.observation_artifact_bytes} bytes",
        )
    stored = await container.store_observation_artifact().execute(
        ctx,
        device_id=DeviceId(device_id),
        secret=x_device_secret,
        batch_id=BatchId(batch_id),
        kind=kind,
        data=data,
        content_type=file.content_type or "application/octet-stream",
        frame_index=frame_index,
        label=label,
    )
    return ObservationArtifactResponse(uri=stored.uri, size_bytes=stored.size_bytes)


@router.delete("")
async def forget_observations(
    container: ContainerDep,
    ctx: ContextDep,
    since: Annotated[datetime, Query(description="Delete everything captured after this.")],
) -> ForgottenResponse:
    """The operator deleting their own evidence, and meaning it.

    Scoped to the principal on the credential: one operator does not get to
    erase another's day.
    """
    forgotten = await container.forget_observations().execute(ctx, since=since)
    return ForgottenResponse(
        batches=forgotten.batches, events=forgotten.events, artifacts=forgotten.artifacts
    )
