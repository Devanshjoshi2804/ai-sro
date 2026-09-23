# Notes for `backend/src/sro/interface/http/asking.py`

Comments and docstrings moved out of [`backend/src/sro/interface/http/asking.py`](../../../../../../../backend/src/sro/interface/http/asking.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `asking_device`, [line 53](../../../../../../../backend/src/sro/interface/http/asking.py#L53): Comment

Code: `if not (device_id or "").strip():`

> Blanked, never rewritten. `?device_id=%20` reached `DeviceId(" ")`; an id
> the domain refuses to build is a 422 telling a caller their query string
> was interesting, out of the one function whose promise is that nothing
> here is told apart. So an id that is nothing but space becomes "no
> browser named". (`?device_id=` never got that far on its own: an empty
> string is falsy and takes one of the two branches below.)
>
> And nothing else. `device_id.strip()` would read the same and quietly
> rewrite every PADDED id on its way to `DeviceId`, at the one seam whose
> whole job is which browser was named: ` dev-1` would authenticate as
> `dev-1`. There is no caller that needs that and no test that wanted it.

## `asking_device`, [line 56](../../../../../../../backend/src/sro/interface/http/asking.py#L56): Comment

Code: `return None`

> No browser named, so no browser is asking -- whether or not a secret
> came along. This is the tenant, and it is not a downgrade: there is
> nothing to downgrade FROM, because a secret on its own names nobody.
>
> It used to be a 404, and that cost this deployment every tenant door
> the extension has. The browser sends `X-Device-Secret` on every call
> by design -- it goes to the same backend either way, and a list of
> which endpoints may see it is a list that goes stale -- so every
> tenant-only door it asked answered "device  was not found": `/v1/ask`
> on every sentence an operator typed into the panel, and `/v1/chat`,
> `/v1/mine` and `/v1/spend` behind it. The panel looked broken because
> it was, and the worker's own `catch` read the 404 as "nothing to
> offer".
>
> The rule the 404 exists for is the other half-pair: a caller naming a
> browser without proving it. That one still refuses, because it is a
> caller asking whether a browser exists.

## `asking_device`, [line 67](../../../../../../../backend/src/sro/interface/http/asking.py#L67): Comment

Code: `attribute(device=named.value)`

> After it has proved itself, never before. A device id in the query string
> is a caller's claim; this is the first point it is a fact, and a log line
> attributing work to a browser that failed to prove it is worse than one
> attributing it to nobody.
