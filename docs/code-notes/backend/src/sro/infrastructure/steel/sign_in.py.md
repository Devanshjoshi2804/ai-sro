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

## module, [line 30](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L30): Note on the line above

Code: `_ROUNDS: Final = 6`

> Identifier page, password page, consent, and slack. A login that has not
> finished in six is stuck, and looping harder on a stuck login only delays
> telling somebody.

## `_settle`, [line 102](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L102): Docstring

> Give the page the moment it needs, without making it a deadline.
>
> Identity providers redirect through several documents, some of which never
> go quiet -- so a timeout here is normal and means "carry on", not "failed".

## `_filled`, [line 114](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L114): Docstring

> Fill the first visible match, and say whether there was one.
>
> Fills only an empty box: an identity provider that carries the username
> across its own pages would otherwise have it typed twice.

## `_submit`, [line 123](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L123): Docstring

> Press the button, or the key that stands in for it.

## `_chose`, [line 134](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L134): Docstring

> Click the identity provider a demonstration showed us choosing.
>
> Matched on the text somebody was recorded clicking rather than on anything
> this code believes about tenants: "Local WMS users (bf56-001-eus2) (SSO)"
> means nothing to anyone who has not seen this deployment.
>
> ``taken`` is what has already been clicked this attempt. Without it the
> same link is clicked every round, because an identity provider that carries
> its branding onto the next page still shows text that matches.

## `_on_offer`, [line 154](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L154): Docstring

> The clickable text on the page, for a failure somebody has to diagnose.

## `PlaywrightSignIn.sign_in`, [line 62](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L62): Comment

Code: `if picked := await _chose(page, choose, taken):`

> What a person was recorded clicking, before anything this
> code infers from the shape of the page. Keycloak shows its
> own username box beside the link to the identity provider
> that actually holds the account, so a driver that fills
> whatever box it finds signs in to the wrong realm -- which
> is what it did, six rounds in a row.

## `PlaywrightSignIn.sign_in`, [line 67](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L67): Comment

Code: `named = await _filled(page, _IDENTIFIER, username)`

> Both, before submitting either. Keycloak puts the
> username and the password on one form, and a driver that
> filled whichever it found first submitted a password with
> no username -- five times, because the page came back
> empty and it did the same thing again.

## `PlaywrightSignIn.sign_in`, [line 57](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L57): Comment

Code: `raise SignInFailed(`

> What the page was offering, because "it did not finish" is not
> something anybody can act on. The options are what a recorded
> login would have matched against, so seeing them names the fix.

## `_chose`, [line 146](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L146): Comment

Code: `logger.debug("an option would not describe itself", exc_info=True)`

> A chooser redraws itself as it is read. Not the option.
