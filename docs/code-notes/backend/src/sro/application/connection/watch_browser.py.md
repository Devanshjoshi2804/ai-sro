# Notes for `backend/src/sro/application/connection/watch_browser.py`

Comments and docstrings moved out of [`backend/src/sro/application/connection/watch_browser.py`](../../../../../../../backend/src/sro/application/connection/watch_browser.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/connection/watch_browser.py#L1): Docstring

> Where to watch, when this system is driving a browser.
>
> The system signs itself in, replays a screen and pursues a goal in a browser
> nobody can see. That is the right default for something running at 3am and the
> wrong one for a person waiting: "it did not finish" is a sentence, and a window
> they can watch is evidence. Every provider we use has a live view already --
> this only says which sessions are open and where to look at them.
>
> Deployment-wide and deliberately tenant-blind, which is why nothing a caller
> reaches serves it any more: the stray sweep has to see browsers nobody claimed,
> and that is the whole set. Ask ``Browsers.mine(ctx)`` for a person's browsers.

## `OpenBrowser`, [line 11](../../../../../../../backend/src/sro/application/connection/watch_browser.py#L11): Note on the line above

Code: `live_view_url: str | None`

> ``None`` when the provider has no viewer for it. Still worth reporting:
> a session nobody can watch is still a session holding the only slot.

## `WatchBrowsers.all_in_deployment`, [line 18](../../../../../../../backend/src/sro/application/connection/watch_browser.py#L18): Docstring

> Every browser open right now, whoever it belongs to. Empty when the provider is down --
> which is a fact about the provider, not something to raise over.
