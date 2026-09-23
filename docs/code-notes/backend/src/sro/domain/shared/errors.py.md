# Notes for `backend/src/sro/domain/shared/errors.py`

Comments and docstrings moved out of [`backend/src/sro/domain/shared/errors.py`](../../../../../../../backend/src/sro/domain/shared/errors.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/shared/errors.py#L1): Docstring

> Error types raised by the domain and application layers.

## `InvariantViolation`, [line 8](../../../../../../../backend/src/sro/domain/shared/errors.py#L8): Docstring

> An operation would leave an entity in a state it forbids.

## `NotFound`, [line 12](../../../../../../../backend/src/sro/domain/shared/errors.py#L12): Docstring

> Entity does not exist, or belongs to another tenant.
>
> The two cases are deliberately indistinguishable: distinguishing them would
> confirm that an id exists in some other tenant.

## `Conflict`, [line 16](../../../../../../../backend/src/sro/domain/shared/errors.py#L16): Docstring

> Valid request that conflicts with current state.
