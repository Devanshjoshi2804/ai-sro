# Notes for `backend/src/sro/application/ports/page.py`

Comments and docstrings moved out of [`backend/src/sro/application/ports/page.py`](../../../../../../../backend/src/sro/application/ports/page.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `SessionRef`, [line 15](../../../../../../../backend/src/sro/application/ports/page.py#L15): Docstring

> One account's browser: `context_id` is the browser context the pool made
> for the account (the lease's `context_id`), and `cdp_url` is the CDP
> endpoint of the container that holds it (the pool's `cdp_url`). The first
> version named the first field `steel_session_id`; S7 filled it with the
> lease's Steel session id, which is shared by every account on the
> container and is not a browser context, so every call was `PageGone`
> (S5 review I4).

## `PageAnswer`, [line 21](../../../../../../../backend/src/sro/application/ports/page.py#L21): Docstring

> `pin` and `repaired` are not in X4's brief's own sketch of this type; they
> are the X2 review's binding amendment ("pass the pin from `act`'s answer
> into `holds`"; "treat `repaired: true` as UNCONFIRMED"), which the page
> code (`page-code.js#L896-908`) already implements: `act` mints a `pin` and
> pins the matched element to it, and both `act` and `holds` echo whether that
> match came from snapshot repair. Carrying both on the answer is what lets
> `UiLane._holds` re-check the SAME element `act` touched (never `holds`
> re-resolving and repairing a second time) and refuse to call a repaired
> write `done` on verification alone.

## `PageDriver`, [line 40](../../../../../../../backend/src/sro/application/ports/page.py#L40): Docstring

> S5 owns this file and this Protocol; the five methods X4 needs to drive
> the recorded frame are here (`act`, `mark`, `calls_since`, `wait_for_call`,
> `wait_for`) plus `signals` (S6's, needed to tell an expired session from a
> genuinely missing control), reconciled onto S5's own seven tab-lifecycle
> methods (`open_tab`, `close_tab`, `goto`, `url_of`, `storage_state`,
> `restore_state`, `forget`) and `aclose`; a `Protocol` has no body to
> conflict over, so the two additions merge as a plain union of methods.

## `PageDriver.aclose`, [line 113](../../../../../../../backend/src/sro/application/ports/page.py#L113): Docstring

> The driver holds connections for the life of the process; whoever built
> the container closes them on the way down.

## `PageDriver.forget_calls`, [line 111](../../../../../../../backend/src/sro/application/ports/page.py#L111): Docstring

> Drops a tab's call log, request bodies included. The broker calls it on
> the probe tab before handing it to the first run, so the sign-in POST,
> whose body carries the password, does not outlive the sign-in (S7
> review, M2). Later marks start a fresh log.
