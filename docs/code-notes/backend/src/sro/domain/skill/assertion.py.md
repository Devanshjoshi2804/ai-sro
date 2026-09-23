# Notes for `backend/src/sro/domain/skill/assertion.py`

Comments and docstrings moved out of [`backend/src/sro/domain/skill/assertion.py`](../../../../../../../backend/src/sro/domain/skill/assertion.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/skill/assertion.py#L1): Docstring

> Post-conditions extracted from what the demonstrator checked.

## `Assertion`, [line 29](../../../../../../../backend/src/sro/domain/skill/assertion.py#L29): Note on the line above

Code: `written_by: PrincipalId | None = None`

> The person who wrote this, where a person did.
>
> ``None`` means induction derived it from the recordings the version cites:
> two demonstrations answered the same status, or agreed on a field of the
> response. That is evidence.
>
> A name means somebody decided what counts as success -- which is the only
> way a step nobody demonstrated can have a post-condition at all, and a
> different kind of thing. A reviewer reading a version has to be able to
> tell the two apart, and a system that could not would present a guess and
> a measurement in the same words.
