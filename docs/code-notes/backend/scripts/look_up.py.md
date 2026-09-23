# Notes for `backend/scripts/look_up.py`

Comments and docstrings moved out of [`backend/scripts/look_up.py`](../../../../backend/scripts/look_up.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/look_up.py#L1): Docstring

> Ask one question of every system this deployment knows about.
>
>     uv run python scripts/look_up.py new "which suppliers are set up at SG"
>     ... --send          # actually go and look, through a connected browser
>
> Dry by default, and the dry run is the whole plan: which system, a call or a
> screen, the exact target, and the knowledge each lookup was built from. A
> question that reaches a warehouse is not something to send on a flag somebody
> typed by accident -- even a read opens a tab in somebody's browser.
>
> `--send` needs a connected browser and will not find one from here: the socket
> is held by whichever process the extension dialled, which is the API. See
> `create_by_api.py` for the same wall and the same reason. What this prints
> instead is the address each lookup resolved to, which is the part worth
> reading before anything goes out.
