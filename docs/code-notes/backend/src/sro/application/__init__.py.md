# Notes for `backend/src/sro/application/__init__.py`

Comments and docstrings moved out of [`backend/src/sro/application/__init__.py`](../../../../../../backend/src/sro/application/__init__.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../backend/src/sro/application/__init__.py#L1): Docstring

> Application layer: use cases and the ports they depend on.
>
> Orchestration only -- rules belong in ``domain``. Importing ``infrastructure``
> from here fails CI. See docs/01-architecture.md.
