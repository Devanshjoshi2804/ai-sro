# Notes for `backend/src/sro/infrastructure/steel/sign_in.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/steel/sign_in.py`](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L1): Docstring

> Sign a hosted browser in by filling the system's own login page.
>
> Written against the shape of a login rather than against one vendor's markup:
> a page with a password box wants a password, a page with only a text box wants
> an identifier, and an identity provider that asks for them on separate pages is
> the same loop run twice. That covers Keycloak, Azure B2C and the ordinary
> single-form login without a per-system script.
>
> What it will not do is a second factor. A code sent to a phone has no answer in
> the vault, and pretending otherwise would leave an operator watching a browser
> time out. Those systems are told plainly to connect by hand.

## module, [line 33](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L33): Note on the line above

Code: `_ROUNDS: Final = 6`

> Identifier page, password page, consent, and slack. A login that has not
> finished in six is stuck, and looping harder on a stuck login only delays
> telling somebody.

## `_settle`, [line 144](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L144): Docstring

> Give the page the moment it needs, without making it a deadline.
>
> Identity providers redirect through several documents, some of which never
> go quiet -- so a timeout here is normal and means "carry on", not "failed".
>
> Never longer than what is left of the caller's timeout, and floored at a
> millisecond because Playwright reads a timeout of 0 as "wait forever".
> Waiting for quiet does not make the next probe safe: on the chain measured
> 2026-09-23 no page went quiet, so this always ran out and the probe after it
> met a page mid-navigation. That is handled where the page is read, in
> `PlaywrightSignIn.sign_in`, not here.

## `_filled`, [line 158](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L158): Docstring

> Fill the first visible match, and say whether there was one.
>
> Fills only an empty box: an identity provider that carries the username
> across its own pages would otherwise have it typed twice.

## `_submit`, [line 167](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L167): Docstring

> Press the button, or the key that stands in for it.

## `_chose`, [line 178](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L178): Docstring

> Click the identity provider a demonstration showed us choosing.
>
> Matched on the text somebody was recorded clicking rather than on anything
> this code believes about tenants: "Local WMS users (bf56-001-eus2) (SSO)"
> means nothing to anyone who has not seen this deployment.
>
> ``taken`` is what has already been clicked this attempt. Without it the
> same link is clicked every round, because an identity provider that carries
> its branding onto the next page still shows text that matches.

## `_on_offer`, [line 198](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L198): Docstring

> The clickable text on the page, for a failure somebody has to diagnose.

## `_round`, [line 117](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L117): Comment

Code: `if picked := await _chose(page, choose, taken):`

> What a person was recorded clicking, before anything this
> code infers from the shape of the page. Keycloak shows its
> own username box beside the link to the identity provider
> that actually holds the account, so a driver that fills
> whatever box it finds signs in to the wrong realm -- which
> is what it did, six rounds in a row.

## `_round`, [line 122](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L122): Comment

Code: `named = await _filled(page, _IDENTIFIER, username)`

> Both, before submitting either. Keycloak puts the
> username and the password on one form, and a driver that
> filled whichever it found first submitted a password with
> no username -- five times, because the page came back
> empty and it did the same thing again.

## `PlaywrightSignIn.sign_in`, [line 87](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L87): Comment

Code: `raise SignInFailed(`

> What the page was offering, because "it did not finish" is not
> something anybody can act on. The options are what a recorded
> login would have matched against, so seeing them names the fix.

## `_chose`, [line 190](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L190): Comment

Code: `logger.debug("an option would not describe itself", exc_info=True)`

> A chooser redraws itself as it is read. Not the option.

## module, [line 35](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L35): Note on the line above

Code: `_QUIET_S: Final = 8.0`

> The longest one round waits for the network to go quiet before reading the
> page. Unchanged from before the redirect-chain fix; it is a courtesy to a
> page still rendering its form, not a promise that the page has stopped
> moving.

## module, [line 37](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L37): Note on the line above

Code: `_PROBE_S: Final = 1.0`

> How long to wait before reading a page again when it offered nothing to do
> or moved while it was being read. Probing once a second is what completed
> the real portal -> chooser -> identity provider -> system chain on
> 2026-09-23 (about 50 s end to end) after the old loop had crashed on it.

## `PlaywrightSignIn.sign_in`, [line 54](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L54): Note on the line above

Code: `deadline = clock.time() + timeout_s`

> `timeout_s` was accepted and ignored until 2026-09-23; the loop was bounded
> only by `_ROUNDS`. Once a page with nothing to do stopped meaning "give up",
> something had to end a login that is genuinely stuck, and the caller's
> timeout is the bound it already promised.

## `PlaywrightSignIn.sign_in`, [line 66](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L66): Note on the line above

Code: `if acted >= _ROUNDS:`

> `_ROUNDS` now counts things the driver did -- a choice, a form submitted, a
> button pressed -- not times it looked. Waiting on a hand-over costs nothing
> against it. Checked after `_settle`, so the page the last action led to has
> had its moment before anyone reads where the browser ended up.

## `PlaywrightSignIn.sign_in`, [line 70](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L70): Note on the line above

Code: `except PlaywrightError:`

> A navigation in flight is a normal state of a redirect chain, not an error.
> Any probe of the page -- is it visible, fill it, click it, press submit --
> can meet a document being replaced, and Playwright reports that as
> "Execution context was destroyed", "Element is not attached to the DOM" or
> similar depending on which call lost the race. The round is abandoned and
> the next one reads whatever document is there by then.
>
> Every Playwright error is treated that way rather than matching those
> messages, because their wording is the library's and changes with it. What
> is not retried is a closed page: nothing will load into it again.
>
> Measured 2026-09-23 on QA: the real chain crashed here (inside `_visible`)
> while the page was redirecting. `tests/browser/test_a_sign_in_through_a_redirect_chain.py`
> reproduces the same error from the same line with a local chain.

## `PlaywrightSignIn.sign_in`, [line 80](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L80): Note on the line above

Code: `await asyncio.sleep(_PROBE_S)`

> Not a Playwright wait: those go through the page, and the page is the thing
> that may be between documents.

## `_Round`, [line 96](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L96): Class

> What one look at the page came to: the system's own host with nothing left
> to fill (landed), something done (acted), or nothing to do yet (waiting).

## `_round`, [line 133](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L133): Note on the line above

Code: `return _Round.WAITING`

> Off the system's host with nothing to fill and nothing to press used to end
> the login as a failure. On a real chain that page is usually a hand-over
> still in flight -- a document that posts itself onward a moment after it
> loads -- so it now means "look again", and only the caller's timeout turns
> it into a failure.

## `_on_offer`, [line 204](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L204): Note on the line above

Code: `except PlaywrightError:`

> Called once the loop is over, only to describe a failure. A page that moves
> while it is described describes nothing rather than replacing the real
> failure with a navigation error.
