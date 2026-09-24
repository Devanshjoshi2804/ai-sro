# Notes for `backend/src/sro/application/ports/page.py`

Comments and docstrings moved out of [`backend/src/sro/application/ports/page.py`](../../../../../../../backend/src/sro/application/ports/page.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `SessionRef`, [line 13](../../../../../../../backend/src/sro/application/ports/page.py#L13): Docstring

> Pre-created for X3's `application.runtime.step.Held`, which names one on
> every lease it holds. S5 owns this file and this type -- the shape here
> (`steel_session_id`, `cdp_url`) is copied verbatim from S5's own brief, not
> designed here, so S5 lands the rest of it (`PageDriver`, `PageGone`) on
> top of a type already in its final shape rather than choosing between two
> definitions.

## `PageAnswer`, [line 19](../../../../../../../backend/src/sro/application/ports/page.py#L19): Docstring

> `pin` and `repaired` are not in X4's brief's own sketch of this type; they
> are the X2 review's binding amendment ("pass the pin from `act`'s answer
> into `holds`"; "treat `repaired: true` as UNCONFIRMED"), which the page
> code (`page-code.js#L896-908`) already implements: `act` mints a `pin` and
> pins the matched element to it, and both `act` and `holds` echo whether that
> match came from snapshot repair. Carrying both on the answer is what lets
> `UiLane._holds` re-check the SAME element `act` touched (never `holds`
> re-resolving and repairing a second time) and refuse to call a repaired
> write `done` on verification alone.

## `PageDriver`, [line 30](../../../../../../../backend/src/sro/application/ports/page.py#L30): Docstring

> S5 owns this file and this Protocol; only the five methods X4 needs to
> drive the recorded frame are here (`act`, `mark`, `calls_since`,
> `wait_for_call`, `wait_for`) plus `signals` (S6's, needed to tell an
> expired session from a genuinely missing control). S5 lands its own seven
> tab-lifecycle methods (`open_tab`, `close_tab`, `goto`, `url_of`,
> `storage_state`, `restore_state`, `forget`) and `PageGone` on top; a
> `Protocol` has no body to conflict over, so the two additions merge as a
> plain union of methods.
