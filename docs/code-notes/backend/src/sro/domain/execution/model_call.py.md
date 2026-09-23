# Notes for `backend/src/sro/domain/execution/model_call.py`

Comments and docstrings moved out of [`backend/src/sro/domain/execution/model_call.py`](../../../../../../../backend/src/sro/domain/execution/model_call.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/execution/model_call.py#L1): Docstring

> One call to a hosted model, recorded whether or not it worked.
>
> Written for the incident review that has not happened yet: which run, which
> step, what left the deployment, what came back, and what was removed first. A
> model call with no such record is a hole in the audit trail exactly where
> somebody will look.

## `ModelCall`, [line 17](../../../../../../../backend/src/sro/domain/execution/model_call.py#L17): Note on the line above

Code: `purpose: str`

> What it was asked for -- ``propose_gesture``, ``transcribe`` -- not a prompt.

## `ModelCall`, [line 26](../../../../../../../backend/src/sro/domain/execution/model_call.py#L26): Note on the line above

Code: `redacted_fields: tuple[str, ...] = ()`

> Field names removed before sending. Never their values.

## `ModelCall`, [line 28](../../../../../../../backend/src/sro/domain/execution/model_call.py#L28): Note on the line above

Code: `outcome: str = ""`

> What came back, in one line: the proposed gesture, a refusal, or an error.
