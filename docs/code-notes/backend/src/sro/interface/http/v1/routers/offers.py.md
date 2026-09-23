# Notes for `backend/src/sro/interface/http/v1/routers/offers.py`

Comments and docstrings moved out of [`backend/src/sro/interface/http/v1/routers/offers.py`](../../../../../../../../../backend/src/sro/interface/http/v1/routers/offers.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `record_offer`, [line 66](../../../../../../../../../backend/src/sro/interface/http/v1/routers/offers.py#L66): Comment

Code: `at=body.at.isoformat() if body.at else None,`

> The browser's reading, as it wrote it, for `clamped` to hold against
> the server's. Passed on and never defaulted here: which day an offer
> falls on decides when its job comes back, and a route that read a
> clock would decide that.
