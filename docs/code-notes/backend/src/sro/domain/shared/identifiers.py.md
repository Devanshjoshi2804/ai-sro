# Notes for `backend/src/sro/domain/shared/identifiers.py`

Comments and docstrings moved out of [`backend/src/sro/domain/shared/identifiers.py`](../../../../../../../backend/src/sro/domain/shared/identifiers.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/shared/identifiers.py#L1): Docstring

> Typed identifiers. See docs/01-architecture.md#tenancy.

## `DeviceId`, [line 32](../../../../../../../backend/src/sro/domain/shared/identifiers.py#L32): Docstring

> One installed extension in one browser profile.

## `BatchId`, [line 35](../../../../../../../backend/src/sro/domain/shared/identifiers.py#L35): Docstring

> Minted by the extension, not here: a retried upload must be recognised as
> the same batch rather than stored twice.

## `CandidateId`, [line 38](../../../../../../../backend/src/sro/domain/shared/identifiers.py#L38): Docstring

> A task somebody keeps doing, noticed rather than reported.

## `TriggerId`, [line 41](../../../../../../../backend/src/sro/domain/shared/identifiers.py#L41): Docstring

> What starts a run when nobody typed a sentence.

## `ConfirmationId`, [line 44](../../../../../../../backend/src/sro/domain/shared/identifiers.py#L44): Docstring

> A fire waiting for somebody to say yes.

## `BrowserSessionId`, [line 47](../../../../../../../backend/src/sro/domain/shared/identifiers.py#L47): Docstring

> Session in the browser provider. Owned by them, referenced by us.

## `TenantId`, [line 20](../../../../../../../backend/src/sro/domain/shared/identifiers.py#L20): Comment

Code: `class TenantId(Identifier): ...`

> Subclasses exist so mypy rejects a SkillId where a RecordingId belongs, and so
> ids of different kinds never compare equal at runtime.
