# Notes for `backend/src/sro/infrastructure/steel/ui_driver.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/steel/ui_driver.py`](../../../../../../../backend/src/sro/infrastructure/steel/ui_driver.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/steel/ui_driver.py#L1): Docstring

> Drive a real browser over CDP, one gesture at a time.
>
> Two things here are not incidental.
>
> **The frame.** This WMS attaches one iframe per screen it has ever shown and
> never releases them, so "the page" is a dozen documents of which one is the
> screen the operator is looking at. Every lookup runs against the visible one.
>
> **The component query.** ExtJS renders controls as nested `<div>`s with ids
> assigned in render order, so a recorded CSS path finds a different control after
> a reload. `Ext.ComponentQuery` is what the application's own code uses, and it
> is answered by the framework rather than by the DOM -- which is also why it has
> to run as script rather than as a selector.

## module, [line 15](../../../../../../../backend/src/sro/infrastructure/steel/ui_driver.py#L15): Note on the line above

Code: `_TEXT_DIGEST = r"""(page) => {`

> Visible controls, with where they are. Names come from the DOM rather than
> from the picture: the redaction step can only reason about text, and a control's
> own name beats one inferred from pixels.
>
> Raw, and it has to be: without the ``r`` Python turns the ``
> `` in the final
> ``join`` into a real newline, JS receives an unterminated string literal, and
> every call raised ``SyntaxError`` into an ``except`` that answered with an empty
> digest. The rung that is meant to prefer exact names over pixels had been
> running on pixels alone since it was written.

## module, [line 38](../../../../../../../backend/src/sro/infrastructure/steel/ui_driver.py#L38): Note on the line above

Code: `_TYPE_DELAY_MS = 60`

> Typed rather than set. ExtJS combo boxes filter on keystrokes, and a value
> assigned straight into the input leaves the picker closed and the field
> unvalidated -- which is how a replay silently fills a form nobody accepts.

## `PlaywrightUiDriver`, [line 41](../../../../../../../backend/src/sro/infrastructure/steel/ui_driver.py#L41): Docstring

> Attaches to a browser that is already signed in.
>
> The browser is a resource the driver borrows rather than owns: a run must
> never be the thing that logs a warehouse operator out.

## `_AttachedPage`, [line 147](../../../../../../../backend/src/sro/infrastructure/steel/ui_driver.py#L147): Docstring

> Connect, hand over the page the operator is on, disconnect.
>
> Per gesture on purpose: holding a CDP connection open across a run means a
> worker restart leaves a browser wondering, and the connection costs
> milliseconds against a gesture that takes a second.

## `_offset_of`, [line 173](../../../../../../../backend/src/sro/infrastructure/steel/ui_driver.py#L173): Docstring

> Where this frame sits inside the page it is part of.
>
> The screenshot is of the page. A control described in the coordinates of an
> iframe that begins 90 pixels down is described 90 pixels wrong.

## `_screen_size`, [line 185](../../../../../../../backend/src/sro/infrastructure/steel/ui_driver.py#L185): Docstring

> How big the screen really is, measured rather than assumed.
>
> This is the number every proposed gesture is scaled by: the model answers in
> a normalised space and the caller multiplies by this to get a pixel. Guessed
> wrong, every click lands somewhere else -- ``viewport_size`` is None for a
> page attached over CDP, so the fallback of 1280x800 was used against a real
> screen of 800x600 and every gesture landed 1.6 times too far right. The
> model was aiming correctly at a menu and clicking the space beneath it,
> twelve times, and reporting that the screen would not respond.

## `_device_pixel_ratio`, [line 204](../../../../../../../backend/src/sro/infrastructure/steel/ui_driver.py#L204): Docstring

> How many device pixels the screenshot spends per CSS pixel. 1.0 when the
> page cannot be asked -- the same assumption as measuring nothing at all.

## `_visible_screen`, [line 213](../../../../../../../backend/src/sro/infrastructure/steel/ui_driver.py#L213): Docstring

> The frame holding the screen in front of the operator.
>
> Chosen by component count rather than by URL or title: this SPA updates both
> of those while leaving the previous screen's DOM in place, so neither says
> which document is live.

## `_resolve`, [line 229](../../../../../../../backend/src/sro/infrastructure/steel/ui_driver.py#L229): Docstring

> A CSS selector for the control, and how many candidates it came from.

## `_resolve_component`, [line 249](../../../../../../../backend/src/sro/infrastructure/steel/ui_driver.py#L249): Docstring

> Ask ExtJS, then hand the answer back as a plain id selector.
>
> The component is turned into `#its-dom-id` so the gesture itself is a real
> Playwright click on a real element -- with its actionability checks and its
> trusted event -- rather than a `fireEvent` the application may not believe.

## `PlaywrightUiDriver.for_session`, [line 45](../../../../../../../backend/src/sro/infrastructure/steel/ui_driver.py#L45): Docstring

> A driver bound to one browser, rather than to the configured one.
>
> A pursuit opens its own browser and must look at that one. Pointed at
> the deployment's default instead, it navigated one Chrome and
> screenshotted another -- so the model was shown a blank page and clicked
> the same corner of it until the budget ran out.

## `PlaywrightUiDriver.capture`, [line 86](../../../../../../../backend/src/sro/infrastructure/steel/ui_driver.py#L86): Docstring

> A screenshot and the page's visible text, for the rung that looks.
>
> The text digest is gathered alongside the image because it is exact and
> the image is not: a control's name read out of the DOM beats the same
> name inferred from pixels, and the redaction step can only reason about
> text.

## `PlaywrightUiDriver.perform_at`, [line 111](../../../../../../../backend/src/sro/infrastructure/steel/ui_driver.py#L111): Docstring

> Act at a point, because the gesture came from pixels.
>
> Deliberately separate from ``perform``: a coordinate is not a control
> the demonstration identified, and the run's record should never be able
> to confuse the two.

## `_AttachedPage.for_session`, [line 151](../../../../../../../backend/src/sro/infrastructure/steel/ui_driver.py#L151): Docstring

> A driver bound to one browser, rather than to the configured one.
>
> A pursuit opens its own browser and must look at that one. Pointed at
> the deployment's default instead, it navigated one Chrome and
> screenshotted another -- so the model was shown a blank page and clicked
> the same corner of it until the budget ran out.

## `PlaywrightUiDriver.perform_at`, [line 131](../../../../../../../backend/src/sro/infrastructure/steel/ui_driver.py#L131): Inline

Code: `pass`

> the move above is the hover

## `_screen_size`, [line 195](../../../../../../../backend/src/sro/infrastructure/steel/ui_driver.py#L195): Comment

Code: `marker = image.find(b"IHDR")`

> The image itself, which is the thing the model actually looked at. A PNG
> says its own size in the eight bytes after the IHDR marker.
>
> In device pixels, though, and the branch above answers in CSS pixels --
> the units every caller scales by. At deviceScaleFactor 2 that is the same
> doubling that had every gesture landing off-screen, reintroduced in the
> path taken exactly when the page will not answer.

## `_visible_screen`, [line 222](../../../../../../../backend/src/sro/infrastructure/steel/ui_driver.py#L222): Comment

Code: `logger.debug("frame %s did not answer", frame.url[:80], exc_info=True)`

> A frame detaches while it is being asked about, constantly, in an
> app that keeps a dozen of them. It is not the visible one.
