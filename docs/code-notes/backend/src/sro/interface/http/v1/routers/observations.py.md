# Notes for `backend/src/sro/interface/http/v1/routers/observations.py`

Comments and docstrings moved out of [`backend/src/sro/interface/http/v1/routers/observations.py`](../../../../../../../../../backend/src/sro/interface/http/v1/routers/observations.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `ingest_observations`, [line 52](../../../../../../../../../backend/src/sro/interface/http/v1/routers/observations.py#L52): Comment

Code: `if len(body.events) > container.settings.observation_batch_events:`

> Counted before a single event is parsed, so a payload past the belt costs
> a length and not a domain parse of every event in it -- and refused whole,
> naming the count that would have been taken, so the sender can split.
>
> What this closes is exactly what the rig's closes and no more: pydantic
> has already turned the JSON into Python objects by the time this runs, so
> the saving is `_as_wire_batch`, not the JSON parse. Bounding the *bytes*
> before anything looks at them is a body-size middleware, which neither
> this system nor the rig has.

## `store_artifact`, [line 97](../../../../../../../../../backend/src/sro/interface/http/v1/routers/observations.py#L97): Comment

Code: `data = await file.read(container.settings.observation_artifact_bytes + 1)`

> `+ 1`, and not a length check after `await file.read()`. Reading one byte
> past the bound is what makes this a *bound on memory* rather than a
> measurement taken afterwards: a caller cannot make this process hold a
> gigabyte in order to be told the file was too big. Do not "simplify" it.
>
> It bounds what this process holds and hands to the blob store. The request
> body itself was already spooled by the multipart parser -- that is the
> rig's position too, and bounding the wire needs middleware.
