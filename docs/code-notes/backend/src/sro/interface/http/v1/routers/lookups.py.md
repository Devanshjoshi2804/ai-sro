# Notes for `backend/src/sro/interface/http/v1/routers/lookups.py`

Comments and docstrings moved out of [`backend/src/sro/interface/http/v1/routers/lookups.py`](../../../../../../../../../backend/src/sro/interface/http/v1/routers/lookups.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `look`, [line 51](../../../../../../../../../backend/src/sro/interface/http/v1/routers/lookups.py#L51): Comment

Code: `return LookupResponse.of(planned)`

> A plan that stops on an open question, or one that was refused, has
> nothing to execute -- and executing "no lookups" would say a question
> was answered by nobody rather than that it was never asked.
