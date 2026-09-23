# Notes for `backend/src/sro/application/ports/capture.py`

Comments and docstrings moved out of [`backend/src/sro/application/ports/capture.py`](../../../../../../../backend/src/sro/application/ports/capture.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/ports/capture.py#L1): Docstring

> Control of a live capture session.
>
> The session itself is a socket bound to one process, so it cannot be modelled as
> a repository or a workflow. What the interface layer needs from it is only this:
> start collecting for a recording, and stop collecting for a recording.

## `CaptureController.stop`, [line 20](../../../../../../../backend/src/sro/application/ports/capture.py#L20): Docstring

> Flush what is buffered, then release the session. Idempotent.

## `CaptureController.snapshot_cookies`, [line 22](../../../../../../../backend/src/sro/application/ports/capture.py#L22): Docstring

> The live session's cookies, for the vault.
>
> On this port rather than the browser one because only the capture
> session holds an attached CDP connection to read them through.

## `CaptureController.stop_all`, [line 24](../../../../../../../backend/src/sro/application/ports/capture.py#L24): Docstring

> Shutdown. Sessions outlive requests, so something has to end them.
