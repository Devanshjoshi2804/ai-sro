# Notes for `backend/scripts/create_by_api.py`

Comments and docstrings moved out of [`backend/scripts/create_by_api.py`](../../../../backend/scripts/create_by_api.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/create_by_api.py#L1): Docstring

> Create a record straight through the API, in the operator's own session.
>
> The question this answers: the job was demonstrated by clicking through a form,
> and the same record can be made with one call -- so make it with one call, with
> values somebody chose rather than the ones the recording happened to carry.
>
>     uv run python scripts/create_by_api.py new workAreas         --set workArea=APITEST1 --set workAreaDescription="made by api"
>     ... --send        # actually send it
>
> **Nothing is replayed from the recording but the SHAPE.** Blue Yonder signs
> every write with a `CSRF-ENCRYPT-TOKEN` that the recorder strikes out at the
> boundary, so a byte-for-byte replay is refused before it is routed. The
> extension fetches that header off the live page instead and sends the call from
> inside the tab the operator is signed into -- `credentials: "include"` -- which
> is why this needs a connected browser and not a credential in a file.
>
> Two gates, and neither is this script's to relax:
>
> **The ledger.** `verified_write_for` refuses a `(method, path)` this deployment
> has not individually watched succeed -- edit, verify on a separate read,
> revert. `knowledge-base/index/write-endpoints.json` is that record.
>
> **The browser.** The call goes out through the extension's `http.send`, so it
> is the operator's own session doing it, from a page they are already on.
>
> Dry by default, and the dry run prints the whole request: url, headers, the
> body with the values substituted, and which headers the extension will fill in
> live. A write to a warehouse is not something to send on a flag somebody typed
> by accident.

## `_newest`, [line 17](../../../../backend/scripts/create_by_api.py#L17): Docstring

> The most recent create of this resource that the system answered 2xx.
>
> Newest because a form changes: the last one that worked is the one whose
> body has the fields the system wants today.

## `_make`, [line 89](../../../../backend/scripts/create_by_api.py#L89): Comment

Code: `print(`

> Not "no browser is connected" -- one may well be, and `/v1/agents`
> will say `online: true` while this prints. The socket is held by
> whichever process the extension connected to, which is the API, and
> this script is not that process. The same wall the Temporal worker
> hit: it asks the API through `RunDispatcher` rather than reaching for
> a browser it cannot see.
>
> There is no equivalent door for a bare command, on purpose.
> `docs/14-extension-protocol.md`: an internal "send this browser a
> command" route would be a way to drive somebody's signed-in session
> anywhere, which no taught skill may do. A command reaches a browser
> as part of a RUN or not at all.
