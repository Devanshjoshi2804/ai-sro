"""Keeps a capture session running for the life of a recording.

A `CaptureSession` is a live object bound to a socket and to this process; it
cannot live in a Temporal workflow, and the operator is driving the browser
themselves, so nothing else is going to pump it. This is the loop that does:
attach on start, drain on an interval, drain once more and detach on finish.

Draining on an interval rather than at the end is what makes a crashed API
process cost one interval instead of the whole demonstration.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.ports.blob import BlobStore
from sro.application.recording.attach_artifact import AttachArtifact
from sro.application.recording.ingest_capture_events import IngestCaptureEvents
from sro.domain.shared.identifiers import RecordingId
from sro.infrastructure.steel.capture import CaptureBatch, CaptureSession

logger = logging.getLogger(__name__)


@dataclass
class _Running:
    session: CaptureSession
    task: asyncio.Task[None]


class CaptureSupervisor:
    """Use cases are built per call, never shared.

    A unit of work owns a database session; handing the same one to two
    concurrent demonstrations would interleave their transactions.
    """

    def __init__(
        self,
        *,
        blobs: BlobStore,
        ingest: Callable[[], IngestCaptureEvents],
        artifacts: Callable[[], AttachArtifact],
        drain_interval_seconds: float = 5.0,
        inline_body_limit_bytes: int = 256 * 1024,
        screenshot_per_gesture: bool = True,
    ) -> None:
        self._blobs = blobs
        self._ingest = ingest
        self._artifacts = artifacts
        self._interval = drain_interval_seconds
        self._inline_limit = inline_body_limit_bytes
        self._screenshot = screenshot_per_gesture
        self._running: dict[str, _Running] = {}

    async def start(
        self, ctx: RequestContext, *, recording_id: RecordingId, debugger_url: str
    ) -> None:
        session = CaptureSession(
            blob_store=self._blobs,
            key_prefix=f"{ctx.tenant_id}/{recording_id}",
            inline_body_limit_bytes=self._inline_limit,
            screenshot_per_gesture=self._screenshot,
        )
        await session.attach(debugger_url)

        task = asyncio.create_task(self._pump(ctx, recording_id, session))
        self._running[recording_id.value] = _Running(session=session, task=task)

    async def stop(self, ctx: RequestContext, *, recording_id: RecordingId) -> None:
        """Final drain, then detach. Safe to call for a recording never started."""
        running = self._running.pop(recording_id.value, None)
        if running is None:
            return

        running.task.cancel()
        await asyncio.gather(running.task, return_exceptions=True)
        try:
            await self._flush(ctx, recording_id, running.session.drain())
        finally:
            await running.session.detach()

    async def stop_all(self) -> None:
        for key in list(self._running):
            running = self._running.pop(key)
            running.task.cancel()
            await asyncio.gather(running.task, return_exceptions=True)
            await running.session.detach()

    async def _pump(
        self, ctx: RequestContext, recording_id: RecordingId, session: CaptureSession
    ) -> None:
        while True:
            await asyncio.sleep(self._interval)
            try:
                await self._flush(ctx, recording_id, session.drain())
            except Exception:
                # One bad batch must not end the capture: the operator is still
                # demonstrating, and the next drain is five seconds away.
                logger.exception("capture drain failed for recording %s", recording_id)

    async def _flush(
        self, ctx: RequestContext, recording_id: RecordingId, batch: CaptureBatch
    ) -> None:
        if batch.events:
            await self._ingest().execute(ctx, recording_id=recording_id, events=batch.events)

        # Artifacts after events, so the frame a screenshot points at exists.
        for artifact in batch.artifacts:
            await self._artifacts().record_stored_blob(
                ctx,
                recording_id=recording_id,
                kind=artifact.kind,
                uri=artifact.uri,
                content_type=artifact.content_type,
                size_bytes=artifact.size_bytes,
                frame_index=artifact.frame_index,
                label=artifact.label,
            )
