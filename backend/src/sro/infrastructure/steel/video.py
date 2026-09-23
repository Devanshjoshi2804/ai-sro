from __future__ import annotations

import fractions
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import av

logger = logging.getLogger(__name__)

_TIMEBASE = fractions.Fraction(1, 1000)


@dataclass(frozen=True, slots=True)
class Recorded:
    path: Path
    duration_ms: int

    frame_count: int


class ScreencastRecorder:
    def __init__(self, *, fps_hint: int = 30) -> None:
        self._fps_hint = fps_hint
        self._container: av.container.OutputContainer | None = None
        self._stream: av.video.stream.VideoStream | None = None
        self._decoder = av.CodecContext.create("mjpeg", "r")
        self._path: Path | None = None
        self._first_ms: float | None = None
        self._last_pts = -1
        self._frames = 0
        self._broken = False

    def add_frame(self, jpeg: bytes, *, at_ms: float) -> None:
        if self._broken:
            return
        try:
            self._add(jpeg, at_ms)
        except Exception:
            logger.exception("screencast encoding failed; video disabled for this session")
            self._broken = True

    def _add(self, jpeg: bytes, at_ms: float) -> None:
        for frame in self._decoder.decode(av.Packet(jpeg)):
            if self._container is None:
                self._open(frame.width, frame.height)
            if self._first_ms is None:
                self._first_ms = at_ms

            stream = self._stream
            container = self._container
            if stream is None or container is None:  # pragma: no cover - set by _open
                return

            pts = int(at_ms - self._first_ms)
            pts = max(pts, self._last_pts + 1)
            self._last_pts = pts

            encodable = frame.reformat(width=stream.width, height=stream.height, format="yuv420p")
            encodable.pts = pts
            encodable.time_base = _TIMEBASE
            for packet in stream.encode(encodable):
                container.mux(packet)
                self._frames += 1

    def _open(self, width: int, height: int) -> None:
        if width < 2 or height < 2:
            raise ValueError(f"screencast frame is too small to encode: {width}x{height}")

        descriptor, name = tempfile.mkstemp(suffix=".mp4")
        os.close(descriptor)
        self._path = Path(name)

        container = av.open(str(self._path), "w")
        stream = container.add_stream("libx264", rate=self._fps_hint)
        stream.width = width - (width % 2)
        stream.height = height - (height % 2)
        stream.pix_fmt = "yuv420p"
        stream.codec_context.time_base = _TIMEBASE
        stream.time_base = _TIMEBASE
        stream.options = {"crf": "28", "preset": "veryfast"}

        self._container = container
        self._stream = stream
        logger.info("recording video at %dx%d", stream.width, stream.height)

    def close(self) -> Recorded | None:
        container, stream = self._container, self._stream
        self._container, self._stream = None, None
        if container is None or stream is None or self._path is None:
            return None

        try:
            for packet in stream.encode():
                container.mux(packet)
                self._frames += 1
        except Exception:
            logger.exception("could not flush the screencast encoder")
        finally:
            container.close()

        if self._frames == 0 or not self._path.exists():
            return None
        return Recorded(
            path=self._path,
            duration_ms=max(self._last_pts, 0),
            frame_count=self._frames,
        )
