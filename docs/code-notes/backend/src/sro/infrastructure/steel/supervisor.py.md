# Notes for `backend/src/sro/infrastructure/steel/supervisor.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/steel/supervisor.py`](../../../../../../../backend/src/sro/infrastructure/steel/supervisor.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/steel/supervisor.py#L1): Docstring

> Keeps a capture session running for the life of a recording.
>
> A `CaptureSession` is a live object bound to a socket and to this process; it
> cannot live in a Temporal workflow, and the operator is driving the browser
> themselves, so nothing else is going to pump it. This is the loop that does:
> attach on start, drain on an interval, drain once more and detach on finish.
>
> Draining on an interval rather than at the end is what makes a crashed API
> process cost one interval instead of the whole demonstration.

## `CaptureSupervisor`, [line 25](../../../../../../../backend/src/sro/infrastructure/steel/supervisor.py#L25): Docstring

> Use cases are built per call, never shared.
>
> A unit of work owns a database session; handing the same one to two
> concurrent demonstrations would interleave their transactions.

## `CaptureSupervisor.stop`, [line 77](../../../../../../../backend/src/sro/infrastructure/steel/supervisor.py#L77): Docstring

> Final drain, then detach. Safe to call for a recording never started.

## `CaptureSupervisor.snapshot_cookies`, [line 91](../../../../../../../backend/src/sro/infrastructure/steel/supervisor.py#L91): Docstring

> Session cookies from a live capture, for the vault.

## `CaptureSupervisor._store_video`, [line 104](../../../../../../../backend/src/sro/infrastructure/steel/supervisor.py#L104): Docstring

> Upload the screencast, then remove the local file.
>
> Last of the capture channels to be stored and the only one that can be
> skipped: a recording without video is still reviewable, so a failure
> here is logged rather than raised.

## `CaptureSupervisor.start`, [line 69](../../../../../../../backend/src/sro/infrastructure/steel/supervisor.py#L69): Comment

Code: `if session_cookies:`

> Cookies before navigation: restoring them afterwards means the first
> page load is the login screen, and the demonstration starts with a
> step nobody wants in the skill.

## `CaptureSupervisor.stop`, [line 85](../../../../../../../backend/src/sro/infrastructure/steel/supervisor.py#L85): Comment

Code: `running.session.flush_incomplete()`

> Strand nothing: in-flight exchanges become part of the batch
> before the final drain, not after it.

## `CaptureSupervisor._pump`, [line 145](../../../../../../../backend/src/sro/infrastructure/steel/supervisor.py#L145): Comment

Code: `logger.exception("capture drain failed for recording %s", recording_id)`

> One bad batch must not end the capture: the operator is still
> demonstrating, and the next drain is five seconds away.

## `CaptureSupervisor._flush`, [line 154](../../../../../../../backend/src/sro/infrastructure/steel/supervisor.py#L154): Comment

Code: `logger.info(`

> A recording that ends up thin is diagnosed here or not at all: by
> review time the only evidence left is what survived.

## `CaptureSupervisor._flush`, [line 166](../../../../../../../backend/src/sro/infrastructure/steel/supervisor.py#L166): Comment

Code: `for artifact in batch.artifacts:`

> Artifacts after events, so the frame a screenshot points at exists.
