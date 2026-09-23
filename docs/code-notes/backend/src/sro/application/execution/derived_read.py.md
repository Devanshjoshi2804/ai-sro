# Notes for `backend/src/sro/application/execution/derived_read.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/derived_read.py`](../../../../../../../backend/src/sro/application/execution/derived_read.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/derived_read.py#L1): Docstring

> Sending a request this system composed, and reading what comes back.
>
> A taught skill is replayed by the executor, with a run, a stage and a track
> record behind it. A derived read has none of that: nobody demonstrated it, so
> there is nothing to promote and nothing to verify against. What it has instead
> is provenance -- the endpoint, the session and the filter dialect all come from
> a demonstration that did happen -- and the rule that it may only ever read.
>
> That rule is the whole safety story here and it is enforced by construction:
> this sends GET, and there is no branch that sends anything else.

## `Asked`, [line 20](../../../../../../../backend/src/sro/application/execution/derived_read.py#L20): Note on the line above

Code: `detail: str = ""`

> Why there is no answer, where there is none.

## `_headers_of`, [line 91](../../../../../../../backend/src/sro/application/execution/derived_read.py#L91): Docstring

> The header plans of the skill's own read.
>
> Borrowed rather than rebuilt: the session cookie, the site parameters and
> the anti-forgery header are what make a request authentic to this system,
> and a composed request without them is a request to a login page.

## `AskTheSystem.execute`, [line 29](../../../../../../../backend/src/sro/application/execution/derived_read.py#L29): Docstring

> Send this read with the session the skill's own calls use.

## `AskTheSystem._rest_of`, [line 66](../../../../../../../backend/src/sro/application/execution/derived_read.py#L66): Docstring

> Follow the paging, so "which ones" is answered with all of them.

## `AskTheSystem.execute`, [line 58](../../../../../../../backend/src/sro/application/execution/derived_read.py#L58): Comment

Code: `return Asked(None, url, "the system asked us to sign in again")`

> A redirect here is the identity provider taking over. Treated as
> success it produced "the answer had no records in it", which
> reads as "there are none" for a session that had simply expired.
