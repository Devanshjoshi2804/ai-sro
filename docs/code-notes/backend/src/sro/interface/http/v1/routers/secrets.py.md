# Notes for `backend/src/sro/interface/http/v1/routers/secrets.py`

Comments and docstrings moved out of [`backend/src/sro/interface/http/v1/routers/secrets.py`](../../../../../../../../../backend/src/sro/interface/http/v1/routers/secrets.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `store_secret`, [line 65](../../../../../../../../../backend/src/sro/interface/http/v1/routers/secrets.py#L65): Comment

Code: `raise unusable`

> Deliberately not a 500. A deployment with no key configured is a
> deployment that cannot keep a secret, and the honest answer is that
> it refused rather than that something broke.
