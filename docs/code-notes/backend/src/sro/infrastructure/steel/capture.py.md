# Notes for `backend/src/sro/infrastructure/steel/capture.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/steel/capture.py`](../../../../../../../backend/src/sro/infrastructure/steel/capture.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L1): Docstring

> Attach to a Steel session over CDP and record everything it does.
>
> Subscribes to every capture domain at once: ``Network`` for the exchange,
> ``Runtime`` for console output, ``Page`` for navigation and dialogs, the
> accessibility tree and a screenshot on each human gesture, and the injected
> page recorder for the gestures themselves.
>
> Buffering is deliberate. CDP delivers on the browser's schedule; the use case
> wants batches. ``drain`` hands over what has accumulated and clears, so an
> ingest failure loses at most one interval rather than the session.

## `_recorder_script`, [line 43](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L43): Docstring

> The page script, with the one list of credential words put into it.
>
> Loudly rather than silently: a script still carrying the marker would run,
> redact nothing, and keep every password an operator typed.

## `PendingArtifact`, [line 53](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L53): Docstring

> A blob written during capture, waiting to be attached to a frame.

## `_PendingRequest`, [line 72](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L72): Docstring

> A request between ``requestWillBeSent`` and ``loadingFinished``.

## `CaptureSession`, [line 94](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L94): Docstring

> One attached CDP session. Not reusable across browser sessions.

## `_addressed`, [line 606](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L606): Docstring

> Give a stored cookie the URL it came from.
>
> ``Network.setCookies`` derives the source scheme from the URL. Without one a
> cookie marked ``secure`` is treated as arriving over plain HTTP and is
> dropped -- silently, in a batch the command still reports as successful.
> The identity-provider cookies are exactly the ones marked secure, so the
> session restored without them looks complete and is not.

## `_as_text`, [line 616](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L616): Docstring

> A base64 body read back as text, or ``None`` when it is really binary.
>
> CDP base64-encodes whatever it cannot hand back as a UTF-8 string, which is
> a screenshot *and* a JSON document served with a charset it would not guess
> at. The second kind has field names in it, and a credential in one was
> stored verbatim and reported as nothing removed.

## `CaptureSession._install_recorder`, [line 142](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L142): Docstring

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

## `CaptureSession._reinstall_recorder`, [line 153](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L153): Docstring

> Install into every frame, not just the main one.
>
> A DOM event does not cross a frame boundary, so a recorder living only
> in the top document sees nothing an operator does inside an embedded
> application. Blue Yonder's portal attaches one iframe per screen, which
> puts every gesture that matters in a child frame -- capture ran against
> it and recorded zero steps while the operator worked.

## `CaptureSession.snapshot_cookies`, [line 197](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L197): Docstring

> Every cookie the browser holds, for the vault.
>
> The one place cookie *values* are read deliberately. They are a bearer
> credential — whoever holds them is the operator until they expire — so
> they go straight to the vault and never into a frame.

## `CaptureSession.restore_cookies`, [line 209](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L209): Docstring

> Start a session already logged in. Returns whether anything was set.

## `CaptureSession.open_at`, [line 233](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L233): Docstring

> Put the session on the page the operator asked to start from.
>
> Steel accepts a ``startUrl`` when a session is created and does not act
> on it for an attached browser, so the navigation happens here -- after
> the recorder is installed, which also means the first page load is
> captured rather than missed.

## `CaptureSession.flush_incomplete`, [line 242](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L242): Docstring

> Emit exchanges still in flight, with whatever was observed.
>
> A request that never reaches ``loadingFinished`` -- the tab closed, the
> session ended, the socket dropped -- would otherwise sit in ``_pending``
> until the process forgets it. The method, URL, headers and initiator are
> already known, and that is most of what a skill is built from, so an
> incomplete exchange is recorded as incomplete rather than discarded.

## `CaptureSession._on_gesture`, [line 296](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L296): Docstring

> Called from the page by ``recorder.js``.
>
> A gesture is the only moment the page state is worth a full snapshot:
> it is the boundary of an action frame.

## `CaptureSession._on_request_extra`, [line 405](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L405): Docstring

> Headers the browser adds after the page hands over -- cookies included.

## `CaptureSession._safe_cookies`, [line 436](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L436): Docstring

> Cookies without their values.
>
> A session cookie is a credential in the same sense a password is: anyone
> who reads the recording can be that operator until it expires. The name,
> domain, flags and expiry are the evidence — they say what the session
> looked like — and the value is the key, which belongs in the vault.

## `CaptureSession._video_loop`, [line 543](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L543): Docstring

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

## `CaptureSession.stop_video`, [line 570](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L570): Docstring

> Finish the recording and hand over the file, if there is one.

## `CaptureSession.page`, [line 592](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L592): Docstring

> The attached page. Tests drive it; production leaves it to the human.

## `CaptureSession._install_in`, [line 166](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L166): Comment

Code: `logger.debug("no recorder in frame %s", frame.url[:80], exc_info=True)`

> A frame being torn down, or one from an origin we cannot reach.
> Neither is worth failing a recording over.

## `CaptureSession.restore_cookies`, [line 222](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L222): Comment

Code: `refused = [`

> Silence here is what used to send an operator to a login page: the
> command succeeds, some cookies never land, and the identity provider
> is the first thing that notices.

## `CaptureSession.open_at`, [line 240](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L240): Comment

Code: `logger.warning("could not open the session at %s", url, exc_info=True)`

> A bad start URL is the operator's to fix in the live view; it must
> not fail the recording that already exists.

## `CaptureSession.detach`, [line 271](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L271): Comment

Code: `self.flush_incomplete()`

> Before tearing anything down: whatever is still in flight is evidence.

## `CaptureSession.detach`, [line 273](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L273): Comment

Code: `self._recorder.close()`

> Normally the supervisor takes the file first; this is the crash
> path, where closing the encoder matters more than keeping it.

## `CaptureSession._on_gesture`, [line 296](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L296): Comment

Code: `async def _on_gesture(self, _source: object, raw: str) -> None:`

> -- gestures -------------------------------------------------------

## `CaptureSession._capture_screenshot`, [line 345](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L345): Comment (debt)

Code: `frame_index=index,`

> ponytail: gestures arrive in order, so this matches the frame
> index the assembler will assign. Revisit if frames ever merge.

## `CaptureSession._on_request`, [line 358](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L358): Comment

Code: `def _on_request(self, payload: CdpPayload) -> None:`

> -- network --------------------------------------------------------

## `CaptureSession._response_body`, [line 478](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L478): Comment

Code: `redacted: tuple[str, ...] = ()`

> Before the size branch, not inside it. A body too large to inline was
> written to object storage exactly as it arrived, so the one response
> big enough to be interesting was the one whose credentials were kept
> -- and a response CDP had base64-encoded skipped redaction outright,
> then reported no fields removed, which reads as "there were none".

## `CaptureSession._response_body`, [line 484](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L484): Comment

Code: `text, raw, base64_encoded = cleaned, cleaned.encode(), False`

> Rewritten, so it is text now whatever it arrived as.
> Nothing is gained by re-encoding a document we have just
> had to parse, and a reviewer can read this one.

## `CaptureSession._video_frame`, [line 562](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L562): Comment

Code: `logger.debug("skipped a video frame", exc_info=True)`

> A navigating or closing page cannot be photographed. Logged at
> debug because it is expected on every navigation; the next tick
> finds the page again, and video is never worth failing over.

## `CaptureSession._on_console`, [line 574](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L574): Comment

Code: `def _on_console(self, payload: CdpPayload) -> None:`

> -- console and page ------------------------------------------------

## `CaptureSession._spawn`, [line 586](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L586): Comment

Code: `def _spawn(self, coro: Any) -> None:`

> -- plumbing --------------------------------------------------------

## `CaptureSession._on_gesture`, [line 304](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L304): Comment

Code: `if self._signing_in():`

> Spec §5.6 in Steel's own capture: a gesture on a sign-in page keeps what was
> acted on and nothing typed (the recorder already dropped it; `to_input_action`
> drops it again for a marked payload), and no tree or screenshot is taken.
> The recorder marks a page holding a password or one-time-code field; the flow
> is followed here, from the main frame's document requests.

## `CaptureSession._navigating`, [line 352](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L352): Docstring

> A main-frame document request moves the tab: its OAuth/OIDC flow is followed
> with the same `SignInFlow` the ingest uses, and a page the recorder marked is
> left behind. Document requests rather than committed navigations, because an
> authorize request the provider answers with a redirect never commits at its
> own URL.

## `CaptureSession._on_request`, [line 361](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L361): Comment

Code: `signing_in = self._signing_in()`

> Judged before the navigation this request may be: the form post that submits
> a password leaves the sign-in page, and it is the one call whose body most
> needs dropping. Judged after it as well, so the authorize request itself and
> every hop inside the flow are held too.

## `CaptureSession._video_frame`, [line 552](../../../../../../../backend/src/sro/infrastructure/steel/capture.py#L552): Docstring

> One frame of the session's video, unless the page is a sign-in page: a video
> frame is a screenshot, and §5.6 takes no screenshot of a sign-in page.
