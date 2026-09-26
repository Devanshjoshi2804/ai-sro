# Notes for `backend/src/sro/application/shared/asking.py`

Comments and docstrings moved out of [`backend/src/sro/application/shared/asking.py`](../../../../../../../backend/src/sro/application/shared/asking.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `ask`, [line 14](../../../../../../../backend/src/sro/application/shared/asking.py#L14): Docstring

> The one way a prompt record is sent. The record decides the model, the
> thinking, the instructions and the schema; the caller decides only what the
> model is shown, split into `trusted` (JSON the system built) and
> `untrusted` (text somebody outside the system wrote, each fenced).
>
> The model comes from the record, not from a setting: a model change is a
> prompt change, and a prompt change bumps the record's version and goes
> through the eval gate (Global Constraint 9). A setting could move it
> silently.
>
> An answer that does not match the record's schema comes back with no data
> and an error naming the record and its version, and keeps what it cost: the
> call was made and billed, and a caller reads "no data" as unsure, never as
> an answer (Global Constraint 10).
