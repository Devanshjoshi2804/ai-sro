# Notes for `backend/src/sro/application/recording/start_recording.py`

Comments and docstrings moved out of [`backend/src/sro/application/recording/start_recording.py`](../../../../../../../backend/src/sro/application/recording/start_recording.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/recording/start_recording.py#L1): Docstring

> Open a browser session and the Recording that will collect its frames.

## `BrowserNotAttachable`, [line 19](../../../../../../../backend/src/sro/application/recording/start_recording.py#L19): Docstring

> The debugger URL points somewhere this deployment will not connect.
>
> ``attach_to`` arrives in the request body and is dialled by the backend, so
> without a bound it reaches anything the backend can: another tenant's
> container, an internal service, a cloud metadata endpoint. The browser being
> attached to is the operator's own, which is on this machine.

## `NoSessionForSystem`, [line 23](../../../../../../../backend/src/sro/application/recording/start_recording.py#L23): Docstring

> This system is known but nobody is signed in to it.
>
> Raised before a browser opens, because the alternative is what used to
> happen: the operator gets a login page inside a live recording and teaches
> signing in, which is a different task from the one they meant to teach.

## `StartedRecording`, [line 32](../../../../../../../backend/src/sro/application/recording/start_recording.py#L32): Note on the line above

Code: `debugger_url: str = ""`

> CDP endpoint for the capture adapter. Never put on the wire.

## `StartedRecording`, [line 36](../../../../../../../backend/src/sro/application/recording/start_recording.py#L36): Note on the line above

Code: `target_system: str | None = None`

> The connected system this URL belongs to, if any -- which is how a
> demonstration that names nothing still starts already signed in.

## `StartRecording._in_their_own_browser`, [line 114](../../../../../../../backend/src/sro/application/recording/start_recording.py#L114): Docstring

> A demonstration this deployment does not drive.
>
> No browser is opened and no session is restored: the operator is
> already signed in to the system, in front of it, and about to do the
> task. The recording is an empty vessel until their extension uploads
> the teaching batches that fill it, and there is no live view because
> there is nothing to watch that they are not already looking at.

## `StartRecording._refuse_unless_allowed`, [line 148](../../../../../../../backend/src/sro/application/recording/start_recording.py#L148): Docstring

> Scheme and host, checked before anything dials it.
>
> The scheme matters as much as the host: ``file:`` and ``gopher:`` are
> not debugger endpoints, and neither is anything else a URL library will
> happily open on our behalf.

## `StartRecording.execute`, [line 86](../../../../../../../backend/src/sro/application/recording/start_recording.py#L86): Comment

Code: `session = (`

> Browser first: if it fails nothing is written, so we never accumulate
> recordings that can only ever be abandoned.
> Opened blank on purpose. Handing the provider a start URL makes it
> navigate the moment the session exists -- before the stored session
> cookies have been restored -- so the operator lands on the identity
> provider's login page and teaches signing in instead of the task.
> Capture navigates after restoring them.

## `StartRecording._in_their_own_browser`, [line 125](../../../../../../../backend/src/sro/application/recording/start_recording.py#L125): Comment

Code: `refuse_unless_itself(device, secret, device_id)`

> A demonstration is the strongest evidence this system has -- it is
> what a skill is induced from -- so naming somebody else's browser as
> the one about to perform it is refused the way every device-scoped
> path refuses it.

## `StartRecording._in_their_own_browser`, [line 143](../../../../../../../backend/src/sro/application/recording/start_recording.py#L143): Comment

Code: `live_view_url="",`

> Nothing to watch that the operator is not already looking at.
