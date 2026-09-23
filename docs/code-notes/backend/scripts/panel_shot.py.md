# Notes for `backend/scripts/panel_shot.py`

Comments and docstrings moved out of [`backend/scripts/panel_shot.py`](../../../../backend/scripts/panel_shot.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/panel_shot.py#L1): Docstring

> A picture of the side panel, for working on how it looks.
>
> The panel is an extension page, so it cannot be opened by URL in an ordinary
> browser and cannot be seen without loading the extension. This loads it the way
> the tests do, signs it in against whatever is running locally, opens the panel
> at the width Chrome gives it, and writes a PNG.
>
>     make panel-shot            # /tmp/panel.png
>     make panel-shot at=here    # a tab on `here` first, so the panel has a host

## `main`, [line 22](../../../../backend/scripts/panel_shot.py#L22): Comment

Code: `tempfile.mkdtemp(prefix="sro-panel-"),`

> A profile of its own each time: storage persists, so a shot of
> the unconnected state taken in yesterday's profile is a shot of
> yesterday's sign-in.

## `main`, [line 28](../../../../backend/scripts/panel_shot.py#L28): Comment

Code: `ident = ""`

> The worker starts when something asks it to. A page on the extension's
> own origin is enough, and its id is the one thing not known yet -- so
> the worker is waited for, and then woken by opening a tab if it has
> not started on its own.

## `main`, [line 37](../../../../backend/scripts/panel_shot.py#L37): Comment

Code: `page = context.new_page()`

> Chrome lists it even when it has not been woken.

## `main`, [line 62](../../../../backend/scripts/panel_shot.py#L62): Comment

Code: `beside = context.new_page()`

> A demonstration in progress: the state with the most to show and
> the most tedious to reach by hand.
