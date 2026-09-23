from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.ports.blob import BlobStore
from sro.application.recording.attach_artifact import AttachArtifact
from sro.application.recording.ingest_capture_events import IngestCaptureEvents
from sro.domain.recording.artifact import ArtifactKind
from sro.domain.shared.identifiers import RecordingId
from sro.infrastructure.steel.capture import CaptureBatch, CaptureSession

logger = logging.getLogger(__name__)


@dataclass
class _Running:
    session: CaptureSession
    task: asyncio.Task[None]


class CaptureSupervisor:
    def __init__(
        self,
        *,
        blobs: BlobStore,
        ingest: Callable[[], IngestCaptureEvents],
        artifacts: Callable[[], AttachArtifact],
        drain_interval_seconds: float = 5.0,
        inline_body_limit_bytes: int = 256 * 1024,
        screenshot_per_gesture: bool = True,
        video: bool = True,
        video_fps: int = 2,
        redact_secrets: bool = True,
    ) -> None:
        self._blobs = blobs
        self._ingest = ingest
        self._artifacts = artifacts
        self._interval = drain_interval_seconds
        self._inline_limit = inline_body_limit_bytes
        self._screenshot = screenshot_per_gesture
        self._video = video
        self._video_fps = video_fps
        self._redact_secrets = redact_secrets
        self._running: dict[str, _Running] = {}

    async def start(
        self,
        ctx: RequestContext,
        *,
        recording_id: RecordingId,
        debugger_url: str,
        start_url: str | None = None,
        session_cookies: tuple[dict[str, object], ...] = (),
    ) -> None:
        session = CaptureSession(
            blob_store=self._blobs,
            key_prefix=f"{ctx.tenant_id}/{recording_id}",
            inline_body_limit_bytes=self._inline_limit,
            screenshot_per_gesture=self._screenshot,
            video=self._video,
            video_fps=self._video_fps,
            redact_secrets=self._redact_secrets,
        )
        await session.attach(debugger_url)
        if session_cookies:
            await session.restore_cookies([dict(cookie) for cookie in session_cookies])
        if start_url:
            await session.open_at(start_url)

        task = asyncio.create_task(self._pump(ctx, recording_id, session))
        self._running[recording_id.value] = _Running(session=session, task=task)

    async def stop(self, ctx: RequestContext, *, recording_id: RecordingId) -> None:
        running = self._running.pop(recording_id.value, None)
        if running is None:
            return

        running.task.cancel()
        await asyncio.gather(running.task, return_exceptions=True)
        try:
            running.session.flush_incomplete()
            await self._flush(ctx, recording_id, running.session.drain())
            await self._store_video(ctx, recording_id, running.session)
        finally:
            await running.session.detach()

    async def snapshot_cookies(self, recording_id: RecordingId) -> list[dict[str, object]]:
        running = self._running.get(recording_id.value)
        if running is None:
            return []
        return await running.session.snapshot_cookies()

    async def stop_all(self) -> None:
        for key in list(self._running):
            running = self._running.pop(key)
            running.task.cancel()
            await asyncio.gather(running.task, return_exceptions=True)
            await running.session.detach()

    async def _store_video(
        self, ctx: RequestContext, recording_id: RecordingId, session: CaptureSession
    ) -> None:
        recorded = session.stop_video()
        if recorded is None:
            return

        try:
            data = recorded.path.read_bytes()
            uri = await self._blobs.put(
                f"{ctx.tenant_id}/{recording_id}/video.mp4", data, content_type="video/mp4"
            )
            await self._artifacts().record_stored_blob(
                ctx,
                recording_id=recording_id,
                kind=ArtifactKind.VIDEO,
                uri=uri,
                content_type="video/mp4",
                size_bytes=len(data),
                duration_ms=recorded.duration_ms,
            )
            logger.info(
                "stored video: recording=%s frames=%d duration=%dms bytes=%d",
                recording_id,
                recorded.frame_count,
                recorded.duration_ms,
                len(data),
            )
        except Exception:
            logger.exception("could not store the video for %s", recording_id)
        finally:
            recorded.path.unlink(missing_ok=True)

    async def _pump(
        self, ctx: RequestContext, recording_id: RecordingId, session: CaptureSession
    ) -> None:
        while True:
            await asyncio.sleep(self._interval)
            try:
                await self._flush(ctx, recording_id, session.drain())
            except Exception:
                logger.exception("capture drain failed for recording %s", recording_id)

    async def _flush(
        self, ctx: RequestContext, recording_id: RecordingId, batch: CaptureBatch
    ) -> None:
        if batch.events:
            result = await self._ingest().execute(
                ctx, recording_id=recording_id, events=batch.events
            )
            logger.info(
                "capture drain: recording=%s events=%d frames=+%d (%d total) "
                "absorbed=%d orphaned=%d artifacts=%d",
                recording_id,
                len(batch.events),
                result.frames_added,
                result.total_frames,
                result.absorbed_requests,
                result.orphaned_requests,
                len(batch.artifacts),
            )

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
