# Notes for `backend/src/sro/infrastructure/steel/capture.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/steel/capture.py`](../../../../../../../backend/src/sro/infrastructure/steel/capture.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L1): Docstring

> Attach to a Steel session over CDP and record everything it does.
>
> Subscribes to every capture domain at once: ``Network`` for the exchange,
> ``Runtime`` for console output, ``Page`` for navigation and dialogs, a
> screenshot on each human gesture, and the injected page recorder for the
> gestures themselves. No longer the accessibility tree: the screen outline
> (spec §4.6) replaced it.
>
> Buffering is deliberate. CDP delivers on the browser's schedule; the use case
> wants batches. ``drain`` hands over what has accumulated and clears, so an
> ingest failure loses at most one interval rather than the session.

## `_page_readers`, [line 46](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L46): Docstring

> page-code.js's `readers` block, cut out by its own first and last lines, to
> be spliced into the recorder. One text for how a control is named and
> placed, so what the recorder records is what page-code.js resolves against.
> Loud when the block is missing: a recorder without its readers would throw
> on the first gesture.

## `_recorder_script`, [line 55](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L55): Docstring

> The page script, with page-code.js's `readers` spliced into it. The
> credential-field rule (`isSecretField`, with the one list of credential words
> generated into page-code.js by `make gen-recorder`) arrives through those
> readers, so the recorder and the page code cannot disagree about what a
> secret field is (X10a re-review N1).
>
> Loudly rather than silently: a script still carrying the marker would run
> without the page's readers and could not tell a credential field at all.

## `PendingArtifact`, [line 63](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L63): Docstring

> A blob written during capture, waiting to be attached to a frame.

## `_PendingRequest`, [line 82](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L82): Docstring

> A request between ``requestWillBeSent`` and ``loadingFinished``.

## `CaptureSession`, [line 103](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L103): Docstring

> One attached CDP session. Not reusable across browser sessions.

## `addressed`, [line 566](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L566): Docstring

> Give a stored cookie the URL it came from.
>
> ``Network.setCookies`` derives the source scheme from the URL. Without one a
> cookie marked ``secure`` is treated as arriving over plain HTTP and is
> dropped -- silently, in a batch the command still reports as successful.
> The identity-provider cookies are exactly the ones marked secure, so the
> session restored without them looks complete and is not.

## `_as_text`, [line 576](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L576): Docstring

> A base64 body read back as text, or ``None`` when it is really binary.
>
> CDP base64-encodes whatever it cannot hand back as a UTF-8 string, which is
> a screenshot *and* a JSON document served with a charset it would not guess
> at. The second kind has field names in it, and a credential in one was
> stored verbatim and reported as nothing removed.

## `CaptureSession._install_recorder`, [line 148](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L148): Docstring

> Install the page recorder, and keep it installed.
>
> Three paths, because one is not enough:
>
> - ``add_init_script`` covers navigation, and runs before page scripts.
> - an immediate ``evaluate`` covers the document that already exists at
>   the moment we attach.
> - re-injecting on every ``domcontentloaded`` covers a page that replaces
>   its document without navigating. ``document.open()`` unregisters every
>   listener on the window and no init script re-runs, so without this the
>   recorder goes quiet for the rest of the session and the recording
>   silently loses its remaining steps.
>
> The script's own guard makes re-injection a no-op when it is not needed.

## `CaptureSession._reinstall_recorder`, [line 159](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L159): Docstring

> Install into every frame, not just the main one.
>
> A DOM event does not cross a frame boundary, so a recorder living only
> in the top document sees nothing an operator does inside an embedded
> application. Blue Yonder's portal attaches one iframe per screen, which
> puts every gesture that matters in a child frame -- capture ran against
> it and recorded zero steps while the operator worked.

## `CaptureSession.snapshot_cookies`, [line 199](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L199): Docstring

> Every cookie the browser holds, for the vault.
>
> The one place cookie *values* are read deliberately. They are a bearer
> credential — whoever holds them is the operator until they expire — so
> they go straight to the vault and never into a frame.

## `CaptureSession.restore_cookies`, [line 211](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L211): Docstring

> Start a session already logged in. Returns whether anything was set.

## `CaptureSession.open_at`, [line 235](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L235): Docstring

> Put the session on the page the operator asked to start from.
>
> Steel accepts a ``startUrl`` when a session is created and does not act
> on it for an attached browser, so the navigation happens here -- after
> the recorder is installed, which also means the first page load is
> captured rather than missed.

## `CaptureSession.flush_incomplete`, [line 244](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L244): Docstring

> Emit exchanges still in flight, with whatever was observed.
>
> A request that never reaches ``loadingFinished`` -- the tab closed, the
> session ended, the socket dropped -- would otherwise sit in ``_pending``
> until the process forgets it. The method, URL, headers and initiator are
> already known, and that is most of what a skill is built from, so an
> incomplete exchange is recorded as incomplete rather than discarded.

## `CaptureSession._on_gesture`, [line 298](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L298): Docstring

> Called from the page by ``recorder.js``. It is the boundary of an action
> frame.
>
> No longer takes a CDP accessibility-tree snapshot here: the screen outline
> (spec §4.6, `outline.py`) replaced it, taken by the page itself rather than
> by a full-tree CDP round trip per gesture.

## `CaptureSession._on_request_extra`, [line 374](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L374): Docstring

> Headers the browser adds after the page hands over -- cookies included.

## `CaptureSession._safe_cookies`, [line 405](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L405): Docstring

> Cookies without their values.
>
> A session cookie is a credential in the same sense a password is: anyone
> who reads the recording can be that operator until it expires. The name,
> domain, flags and expiry are the evidence — they say what the session
> looked like — and the value is the key, which belongs in the vault.

## `CaptureSession._video_loop`, [line 509](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L509): Docstring

> Frames for the video, taken rather than streamed.
>
> ``Page.startScreencast`` is the obvious way to do this and it is the
> wrong one: Chrome allows a single screencast consumer per page and the
> newest one wins. Steel's live view is a screencast consumer, so
> subscribing here silently freezes the browser the operator is driving --
> proved by attaching two clients and watching the first receive nothing.
>
> ``Page.captureScreenshot`` is request/response, so it takes nothing away
> from anyone. The cost is sampling rather than repaint-accurate frames,
> which for reviewing a demonstration is not a cost worth the breakage.

## `CaptureSession.stop_video`, [line 530](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L530): Docstring

> Finish the recording and hand over the file, if there is one.

## `CaptureSession.page`, [line 552](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L552): Docstring

> The attached page. Tests drive it; production leaves it to the human.

## `CaptureSession._install_in`, [line 170](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L170): Comment

Code: `logger.debug("no recorder in frame %s", frame.url[:80], exc_info=True)`

> A frame being torn down, or one from an origin we cannot reach.
> Neither is worth failing a recording over.

## `CaptureSession.restore_cookies`, [line 224](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L224): Comment

Code: `refused = [`

> Silence here is what used to send an operator to a login page: the
> command succeeds, some cookies never land, and the identity provider
> is the first thing that notices.

## `CaptureSession.open_at`, [line 242](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L242): Comment

Code: `logger.warning("could not open the session at %s", url, exc_info=True)`

> A bad start URL is the operator's to fix in the live view; it must
> not fail the recording that already exists.

## `CaptureSession.detach`, [line 273](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L273): Comment

Code: `self.flush_incomplete()`

> Before tearing anything down: whatever is still in flight is evidence.

## `CaptureSession.detach`, [line 275](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L275): Comment

Code: `self._recorder.close()`

> Normally the supervisor takes the file first; this is the crash
> path, where closing the encoder matters more than keeping it.

## `CaptureSession._on_gesture`, [line 298](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L298): Comment

Code: `async def _on_gesture(self, _source: object, raw: str) -> None:`

> -- gestures -------------------------------------------------------

## `CaptureSession._capture_screenshot`, [line 327](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L327): Comment (debt)

Code: `frame_index=index,`

> ponytail: gestures arrive in order, so this matches the frame
> index the assembler will assign. Revisit if frames ever merge.

## `CaptureSession._on_request`, [line 331](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L331): Comment

Code: `def _on_request(self, payload: CdpPayload) -> None:`

> -- network --------------------------------------------------------

## `CaptureSession._response_body`, [line 444](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L444): Comment

Code: `redacted: tuple[str, ...] = ()`

> Before the size branch, not inside it. A body too large to inline was
> written to object storage exactly as it arrived, so the one response
> big enough to be interesting was the one whose credentials were kept
> -- and a response CDP had base64-encoded skipped redaction outright,
> then reported no fields removed, which reads as "there were none".

## `CaptureSession._response_body`, [line 450](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L450): Comment

Code: `text, raw, base64_encoded = cleaned, cleaned.encode(), False`

> Rewritten, so it is text now whatever it arrived as.
> Nothing is gained by re-encoding a document we have just
> had to parse, and a reviewer can read this one.

## `CaptureSession._video_loop`, [line 522](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L522): Comment

Code: `logger.debug("skipped a video frame", exc_info=True)`

> A navigating or closing page cannot be photographed. Logged at
> debug because it is expected on every navigation; the next tick
> finds the page again, and video is never worth failing over.

## `CaptureSession._on_console`, [line 534](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L534): Comment

Code: `def _on_console(self, payload: CdpPayload) -> None:`

> -- console and page ------------------------------------------------

## `CaptureSession._spawn`, [line 546](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L546): Comment

Code: `def _spawn(self, coro: Any) -> None:`

> -- plumbing --------------------------------------------------------
