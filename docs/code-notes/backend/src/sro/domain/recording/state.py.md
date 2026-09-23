# Notes for `backend/src/sro/domain/recording/state.py`

Comments and docstrings moved out of [`backend/src/sro/domain/recording/state.py`](../../../../../../../backend/src/sro/domain/recording/state.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/recording/state.py#L1): Docstring

> Browser state and out-of-band events. See docs/11-capture-completeness.md.

## `ConsoleMessage`, [line 20](../../../../../../../backend/src/sro/domain/recording/state.py#L20): Docstring

> A console entry with its stack.
>
> Kept because a WMS that logs a validation failure is stating why a branch was
> taken -- the cheapest 'why' signal in the whole capture.

## `PageEvent`, [line 49](../../../../../../../backend/src/sro/domain/recording/state.py#L49): Note on the line above

Code: `detail: str | None = None`

> Dialog text, download filename, frame id -- whatever the kind carries.
