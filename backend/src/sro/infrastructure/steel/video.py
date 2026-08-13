"""Screencast frames to a playable video file.

CDP delivers a JPEG whenever the page changes, at whatever rate it changes. That
is not a video, and holding a demonstration's worth of JPEGs in memory to make
one later is how a long session takes the API process down with it.

So frames are encoded as they arrive, into a temporary file, at their real
timing. Memory stays flat, and what comes out is an ordinary H.264 file any
browser plays without a custom player.
"""

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
"""Milliseconds: fine enough for a human gesture, coarse enough to stay exact."""


@dataclass(frozen=True, slots=True)
class Recorded:
    path: Path
    duration_ms: int

    frame_count: int
    """Frames written to the file.

    Not a promise about how many a decoder will yield: a screencast changes
    resolution when the page does, and the encoder resolves that its own way.
    Treat it as a size signal, not as a frame index.
    """


class ScreencastRecorder:
    """Encodes on the fly. Not thread-safe; one per capture session."""

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
        """One screencast frame. Failures disable video, never capture."""
        if self._broken:
            return
        try:
            self._add(jpeg, at_ms)
        except Exception:
            # Video is the least important of the capture channels: losing it
            # must not cost the network, accessibility or input evidence.
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
            # A screencast can repeat a timestamp when the page changes twice
            # within a millisecond; a non-monotonic pts makes the file unplayable.
            pts = max(pts, self._last_pts + 1)
            self._last_pts = pts

            encodable = frame.reformat(width=stream.width, height=stream.height, format="yuv420p")
            encodable.pts = pts
            encodable.time_base = _TIMEBASE
            for packet in stream.encode(encodable):
                container.mux(packet)
                # Counted per muxed packet, not per frame handed to the encoder:
                # x264 buffers, and what the reviewer can actually play is what
                # reached the file.
                self._frames += 1

    def _open(self, width: int, height: int) -> None:
        # A screencast of a page that has not laid out yet can arrive one pixel
        # wide; rounding that to even gives zero, and the encoder rejects the
        # stream with a bare EINVAL that says nothing about why.
        if width < 2 or height < 2:
            raise ValueError(f"screencast frame is too small to encode: {width}x{height}")

        # mkstemp rather than NamedTemporaryFile: the file outlives this scope
        # deliberately -- the supervisor uploads it after the session detaches.
        descriptor, name = tempfile.mkstemp(suffix=".mp4")
        os.close(descriptor)
        self._path = Path(name)

        container = av.open(str(self._path), "w")
        stream = container.add_stream("libx264", rate=self._fps_hint)
        # H.264 requires even dimensions; the browser window is whatever the
        # operator's is, so round down rather than refuse to record.
        stream.width = width - (width % 2)
        stream.height = height - (height % 2)
        stream.pix_fmt = "yuv420p"
        # Both, and the codec one is the load-bearing half: without it libx264
        # has no timebase, buffers everything, and fails the final flush with a
        # bare EINVAL -- losing whatever frames were still in the encoder.
        stream.codec_context.time_base = _TIMEBASE
        stream.time_base = _TIMEBASE
        stream.options = {"crf": "28", "preset": "veryfast"}

        self._container = container
        self._stream = stream
        logger.info("recording video at %dx%d", stream.width, stream.height)

    def close(self) -> Recorded | None:
        """Flush and hand over the file. ``None`` when nothing was recorded."""
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
