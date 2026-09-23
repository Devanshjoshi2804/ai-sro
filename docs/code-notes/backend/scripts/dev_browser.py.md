# Notes for `backend/scripts/dev_browser.py`

Comments and docstrings moved out of [`backend/scripts/dev_browser.py`](../../../../backend/scripts/dev_browser.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/dev_browser.py#L1): Docstring

> A browser with the extension loaded, for working on this by hand.
>
> Chrome under an enterprise policy refuses an unpacked extension — the whole
> point of the policy — so this uses the Chromium that Playwright already
> installed for the browser tests, which no policy governs. Same launch the tests
> do, with two differences: it is headed, and the profile lives somewhere durable
> so a WMS login and the extension's settings survive a restart.
>
>     make dev-browser
>
> Nothing here is part of the product. It is a way to hold it.

## `_extension_id`, [line 84](../../../../backend/scripts/dev_browser.py#L84): Docstring

> The id Chrome gave the unpacked extension, once its worker is up.

## `main`, [line 23](../../../../backend/scripts/dev_browser.py#L23): Comment

Code: `also = [`

> Chromium takes a comma-separated list, and a second extension is the only
> way one window can both capture and be driven: the recorder has to be in
> the same browser as whatever is clicking, or the automation happens in a
> window this extension never sees. Opt-in by path, because the paths are
> per-machine -- e.g. SRO_ALSO_LOAD="$HOME/Library/Application Support/
> Google/Chrome/Profile 1/Extensions/<id>/<version>".

## `main`, [line 50](../../../../backend/scripts/dev_browser.py#L50): Comment

Code: `ident = _extension_id(context)`

> The extension's pages are addressed by an id Chrome assigns at load,
> and the service worker is where it appears first. It starts a moment
> after the window does.

## `main`, [line 54](../../../../backend/scripts/dev_browser.py#L54): Comment

Code: `options = context.new_page()`

> Signed in rather than typed, and through the message the options
> form sends rather than by writing storage: registering the device,
> clearing whatever the last credential left, and starting the
> command channel all hang off that message. Storage alone would
> leave a browser that holds a token and is not a device.
