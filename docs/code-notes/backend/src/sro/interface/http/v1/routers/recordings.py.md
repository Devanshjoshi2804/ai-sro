# Notes for `backend/src/sro/interface/http/v1/routers/recordings.py`

Comments and docstrings moved out of [`backend/src/sro/interface/http/v1/routers/recordings.py`](../../../../../../../../../backend/src/sro/interface/http/v1/routers/recordings.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `start_recording`, [line 50](../../../../../../../../../backend/src/sro/interface/http/v1/routers/recordings.py#L50): Comment

Code: `if not body.attach_to:`

> Before the browser opens, not after: a system whose session has expired
> signs itself back in here, so the operator types a URL and gets a
> demonstration rather than a login page. Silent when the session is fine,
> which is the common case and must stay free.

## `start_recording`, [line 59](../../../../../../../../../backend/src/sro/interface/http/v1/routers/recordings.py#L59): Comment

Code: `session_cookies = (`

> A stored session, if this system has one. Without it the demonstration
> opens on a login page and the operator teaches signing in, which is a
> different task from the one they meant to teach. A first demonstration has
> not named its system yet, so the URL it starts at stands in.

## `start_recording`, [line 65](../../../../../../../../../backend/src/sro/interface/http/v1/routers/recordings.py#L65): Comment

Code: `await container.finish_recording().abandon(`

> Said now, not discovered three clicks into a demonstration.

## `start_recording`, [line 75](../../../../../../../../../backend/src/sro/interface/http/v1/routers/recordings.py#L75): Comment

Code: `await container.capture.start(`

> Capture starts only once the recording is durable: attaching first would
> leave a live CDP session with nowhere to put what it records.

## `start_recording`, [line 82](../../../../../../../../../backend/src/sro/interface/http/v1/routers/recordings.py#L82): Comment

Code: `if started.browser_session_id is not None:`

> Best effort by design -- see DurableExecution.watch_recording. A scheduler
> outage costs this session its deadline, never the demonstration.

## `finish_recording`, [line 216](../../../../../../../../../backend/src/sro/interface/http/v1/routers/recordings.py#L216): Comment

Code: `await container.refresh_session().execute(`

> The browser is signed in right now and about to be thrown away. Taking
> its cookies first is what keeps "connect it once" true a month later.

## `finish_recording`, [line 220](../../../../../../../../../backend/src/sro/interface/http/v1/routers/recordings.py#L220): Comment

Code: `await container.capture.stop(ctx, recording_id=RecordingId(recording_id))`

> Drain and detach before sealing: a sealed recording rejects appends, so
> anything still buffered would be lost with no error to show for it.
