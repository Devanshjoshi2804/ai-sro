# Notes for `backend/src/sro/application/ports/system.py`

Comments and docstrings moved out of [`backend/src/sro/application/ports/system.py`](../../../../../../../backend/src/sro/application/ports/system.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/ports/system.py#L1): Docstring

> Ambient effects: time and id generation.

## `Clock.now`, [line 20](../../../../../../../backend/src/sro/application/ports/system.py#L20): Docstring

> Current time. Must be timezone-aware; entities reject naive datetimes.
