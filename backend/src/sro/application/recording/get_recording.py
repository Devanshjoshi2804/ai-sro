from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.domain.recording.recording import Recording
from sro.domain.shared.identifiers import RecordingId


class GetRecording:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext, *, recording_id: RecordingId) -> Recording:
        async with self._uow as uow:
            return await uow.recordings.get(ctx.tenant_id, recording_id)
