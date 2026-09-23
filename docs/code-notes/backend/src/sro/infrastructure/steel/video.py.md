# Notes for `backend/src/sro/infrastructure/steel/video.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/steel/video.py`](../../../../../../../backend/src/sro/infrastructure/steel/video.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/steel/video.py#L1): Docstring

> Screencast frames to a playable video file.
>
> CDP delivers a JPEG whenever the page changes, at whatever rate it changes. That
> is not a video, and holding a demonstration's worth of JPEGs in memory to make
> one later is how a long session takes the API process down with it.
>
> So frames are encoded as they arrive, into a temporary file, at their real
> timing. Memory stays flat, and what comes out is an ordinary H.264 file any
> browser plays without a custom player.

## module, [line 14](../../../../../../../backend/src/sro/infrastructure/steel/video.py#L14): Note on the line above

Code: `_TIMEBASE = fractions.Fraction(1, 1000)`

> Milliseconds: fine enough for a human gesture, coarse enough to stay exact.

## `Recorded`, [line 22](../../../../../../../backend/src/sro/infrastructure/steel/video.py#L22): Note on the line above

Code: `frame_count: int`

> Frames written to the file.
>
> Not a promise about how many a decoder will yield: a screencast changes
> resolution when the page does, and the encoder resolves that its own way.
> Treat it as a size signal, not as a frame index.

## `ScreencastRecorder`, [line 25](../../../../../../../backend/src/sro/infrastructure/steel/video.py#L25): Docstring

> Encodes on the fly. Not thread-safe; one per capture session.

## `ScreencastRecorder.add_frame`, [line 37](../../../../../../../backend/src/sro/infrastructure/steel/video.py#L37): Docstring

> One screencast frame. Failures disable video, never capture.

## `ScreencastRecorder.close`, [line 90](../../../../../../../backend/src/sro/infrastructure/steel/video.py#L90): Docstring

> Flush and hand over the file. ``None`` when nothing was recorded.

## `ScreencastRecorder.add_frame`, [line 43](../../../../../../../backend/src/sro/infrastructure/steel/video.py#L43): Comment

Code: `logger.exception("screencast encoding failed; video disabled for this session")`

> Video is the least important of the capture channels: losing it
> must not cost the network, accessibility or input evidence.

## `ScreencastRecorder._add`, [line 59](../../../../../../../backend/src/sro/infrastructure/steel/video.py#L59): Comment

Code: `pts = max(pts, self._last_pts + 1)`

> A screencast can repeat a timestamp when the page changes twice
> within a millisecond; a non-monotonic pts makes the file unplayable.

## `ScreencastRecorder._add`, [line 67](../../../../../../../backend/src/sro/infrastructure/steel/video.py#L67): Comment

Code: `self._frames += 1`

> Counted per muxed packet, not per frame handed to the encoder:
> x264 buffers, and what the reviewer can actually play is what
> reached the file.

## `ScreencastRecorder._open`, [line 70](../../../../../../../backend/src/sro/infrastructure/steel/video.py#L70): Comment

Code: `if width < 2 or height < 2:`

> A screencast of a page that has not laid out yet can arrive one pixel
> wide; rounding that to even gives zero, and the encoder rejects the
> stream with a bare EINVAL that says nothing about why.

## `ScreencastRecorder._open`, [line 73](../../../../../../../backend/src/sro/infrastructure/steel/video.py#L73): Comment

Code: `descriptor, name = tempfile.mkstemp(suffix=".mp4")`

> mkstemp rather than NamedTemporaryFile: the file outlives this scope
> deliberately -- the supervisor uploads it after the session detaches.

## `ScreencastRecorder._open`, [line 79](../../../../../../../backend/src/sro/infrastructure/steel/video.py#L79): Comment

Code: `stream.width = width - (width % 2)`

> H.264 requires even dimensions; the browser window is whatever the
> operator's is, so round down rather than refuse to record.

## `ScreencastRecorder._open`, [line 82](../../../../../../../backend/src/sro/infrastructure/steel/video.py#L82): Comment

Code: `stream.codec_context.time_base = _TIMEBASE`

> Both, and the codec one is the load-bearing half: without it libx264
> has no timebase, buffers everything, and fails the final flush with a
> bare EINVAL -- losing whatever frames were still in the encoder.
