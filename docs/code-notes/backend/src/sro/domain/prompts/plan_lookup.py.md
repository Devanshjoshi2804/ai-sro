# Notes for `backend/src/sro/domain/prompts/plan_lookup.py`

Comments and docstrings moved out of [`backend/src/sro/domain/prompts/plan_lookup.py`](../../../../../../../backend/src/sro/domain/prompts/plan_lookup.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 41](../../../../../../../backend/src/sro/domain/prompts/plan_lookup.py#L41): Comment

Code: `"properties": {`

> `why` first for `READ_GESTURE`'s schema's reason: a structured answer is
> written left to right, so a model asked for the reason first has to name
> the evidence before it commits to a target. Asked for the target first it
> picks an endpoint and then writes the sentence that defends it.
