"""What an operator's browser saw, arriving in batches."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from sro.domain.recording.artifact import ArtifactKind
from sro.domain.shared.identifiers import BatchId, DeviceId, RecordingId
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import (
    ForgottenResponse,
    ObservationAcceptedResponse,
    ObservationArtifactResponse,
    ObservationBatchRequest,
    RejectedEventModel,
)

router = APIRouter(prefix="/observations", tags=["observations"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def ingest_observations(
    body: ObservationBatchRequest, container: ContainerDep, ctx: ContextDep
) -> ObservationAcceptedResponse:
    """Accepted, not processed: the evidence is stored and read later.

    Rejections come back on this response rather than going to a log. A malformed
    event is a bug in a version of the extension, and it has to be found on the
    day it ships rather than in a mining run three weeks later that quietly saw
    fewer tasks than happened.
    """
    ingested = await container.ingest_observation().execute(
        ctx,
        device_id=DeviceId(body.device_id),
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
    )


@router.post("/artifacts", status_code=status.HTTP_201_CREATED)
async def store_artifact(
    container: ContainerDep,
    ctx: ContextDep,
    device_id: Annotated[str, Form()],
    batch_id: Annotated[str, Form()],
    kind: Annotated[ArtifactKind, Form()],
    file: Annotated[UploadFile, File()],
    frame_index: Annotated[int | None, Form()] = None,
    label: Annotated[str | None, Form()] = None,
) -> ObservationArtifactResponse:
    """Screenshots and oversized bodies. No row: the key says which batch and
    which frame, so a miner finds them by prefix and a retention rule expires
    them with the evidence they illustrate."""
    stored = await container.store_observation_artifact().execute(
        ctx,
        device_id=DeviceId(device_id),
        batch_id=BatchId(batch_id),
        kind=kind,
        data=await file.read(),
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
