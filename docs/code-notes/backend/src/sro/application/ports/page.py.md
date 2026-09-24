# Notes for `backend/src/sro/application/ports/page.py`

Comments and docstrings moved out of [`backend/src/sro/application/ports/page.py`](../../../../../../../backend/src/sro/application/ports/page.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `SessionRef`, [line 8](../../../../../../../backend/src/sro/application/ports/page.py#L8): Docstring

> One account's browser: \`context_id\` is the browser context the pool made
> for the account (the lease's \`context_id\`), and \`cdp_url\` is the CDP
> endpoint of the container that holds it (the pool's \`cdp_url\`). The first
> version named the first field \`steel_session_id\`; S7 filled it with the
> lease's Steel session id, which is shared by every account on the
> container and is not a browser context, so every call was \`PageGone\`
> (S5 review I4).

## \`PageDriver.aclose\`, [line 32](../../../../../../../backend/src/sro/application/ports/page.py#L32): Docstring

> The driver holds connections for the life of the process; whoever built
> the container closes them on the way down.
