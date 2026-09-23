# Notes for `backend/src/sro/application/connection/session_headers.py`

Comments and docstrings moved out of [`backend/src/sro/application/connection/session_headers.py`](../../../../../../../backend/src/sro/application/connection/session_headers.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/connection/session_headers.py#L1): Docstring

> Give the executor the session headers a browser sends and cannot explain.
>
> A cookie is easy: the browser hands it over and the connect flow already keeps
> it. The rest are not. Blue Yonder sends `CSRF-ENCRYPT-TOKEN` on every write, the
> value is issued at login, and no page, cookie or storage key exposes it -- only
> the requests the application itself makes carry it.
>
> So the value is supplied here, once per session, by whoever can read one: an
> operator with dev tools open, or the capture adapter, which sees every request
> header of the session it is attached to. Storing it beside the cookie is
> consistent with what it is -- a bearer credential for the same session -- and
> keeps it out of the skill, which is the plane that must hold no secret.
>
> The honest limit: these expire with the session, and a run whose header has
> expired fails at the first write rather than silently doing half a task.

## `StoreSessionHeaders.execute`, [line 15](../../../../../../../backend/src/sro/application/connection/session_headers.py#L15): Docstring

> Returns the key names written, never the values.
