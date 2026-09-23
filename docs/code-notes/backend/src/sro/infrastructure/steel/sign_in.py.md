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

## module, [line 34](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L34): Note on the line above

Code: `_ROUNDS: Final = 6`

> Identifier page, password page, consent, and slack. A login that has not
> finished in six is stuck, and looping harder on a stuck login only delays
> telling somebody.

## `_settle`, [line 272](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L272): Docstring

> Give the page the moment it needs, without making it a deadline.
>
> Identity providers redirect through several documents, some of which never
> go quiet -- so a timeout here is normal and means "carry on", not "failed".
>
> Never longer than what is left of the caller's timeout; `_ms` floors every
> Playwright timeout at a millisecond because Playwright reads 0 as "wait
> forever".
> Waiting for quiet does not make the next probe safe: on the chain measured
> 2026-09-23 no page went quiet, so this always ran out and the probe after it
> met a page mid-navigation. That is handled where the page is read, in
> `_walk`, not here.

## `_filled`, [line 291](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L291): Docstring

> Fill the first visible match, and say whether there was one.
>
> Fills only an empty box: an identity provider that carries the username
> across its own pages would otherwise have it typed twice.

## `_submit`, [line 300](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L300): Docstring

> Press the button, or the key that stands in for it.

## `_chose`, [line 311](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L311): Docstring

> Click the identity provider a demonstration showed us choosing.
>
> Matched on the text somebody was recorded clicking rather than on anything
> this code believes about tenants: "Local WMS users (bf56-001-eus2) (SSO)"
> means nothing to anyone who has not seen this deployment.
>
> ``taken`` is what has already been clicked this attempt. Without it the
> same link is clicked every round, because an identity provider that carries
> its branding onto the next page still shows text that matches.

## `_on_offer`, [line 340](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L340): Docstring

> The clickable text on the page, for a failure somebody has to diagnose.

## `_round`, [line 228](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L228): Comment

Code: `if picked := await _chose(page, login.choose, login.deadline, login.taken):`

> What a person was recorded clicking, before anything this
> code infers from the shape of the page. Keycloak shows its
> own username box beside the link to the identity provider
> that actually holds the account, so a driver that fills
> whatever box it finds signs in to the wrong realm -- which
> is what it did, six rounds in a row.

## `_round`, [line 233](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L233): Comment

Code: `named = await _filled(page, _IDENTIFIER, login.username, login.deadline)`

> Both, before submitting either. Keycloak puts the
> username and the password on one form, and a driver that
> filled whichever it found first submitted a password with
> no username -- five times, because the page came back
> empty and it did the same thing again.

## `_walk`, [line 199](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L199): Comment

Code: `raise SignInFailed(`

> What the page was offering, because "it did not finish" is not
> something anybody can act on. The options are what a recorded
> login would have matched against, so seeing them names the fix.

## `_chose`, [line 323](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L323): Comment

Code: `logger.debug("an option would not describe itself: %s", _brief(why, ()))`

> A chooser redraws itself as it is read. Not the option.

## module, [line 36](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L36): Note on the line above

Code: `_QUIET_S: Final = 8.0`

> The longest one round waits for the network to go quiet before reading the
> page. Unchanged from before the redirect-chain fix; it is a courtesy to a
> page still rendering its form, not a promise that the page has stopped
> moving.

## module, [line 38](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L38): Note on the line above

Code: `_PROBE_S: Final = 1.0`

> How long to wait before reading a page again when it offered nothing to do
> or moved while it was being read. Probing once a second is what completed
> the real portal -> chooser -> identity provider -> system chain on
> 2026-09-23 (about 50 s end to end) after the old loop had crashed on it.

## module, [line 40](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L40): Note on the line above

Code: `_STILL: Final = 5`

> How many further probes a page may stay the same document -- same address,
> no main-frame navigation, no error -- with nothing to fill or press before
> it is read as a dead end rather than a hand-over. A hop moves; a locked
> account or an access-denied page does not, and without this it was waited
> on until the whole timeout ran out and then reported without saying what it
> showed. Five is a judgement, not a measurement: roughly five seconds on a
> page that has gone quiet, longer on one that never does (each probe waits
> for quiet first).

## module, [line 42](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L42): Note on the line above

Code: `_SHOWN: Final = 240`

> How much of a page's visible text goes into a failure. Enough to carry "your
> account is locked" or "invalid password", short enough to read in a log.

## `PlaywrightSignIn.sign_in`, [line 74](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L74): Comment

Code: `except PlaywrightError as why:`

> Every Playwright error leaves this driver as a `SignInFailed` carrying only
> the error's type and the first line of its message, with the original
> dropped (`from None`), never chained. Playwright appends a call log to its
> messages, and the call log of a `fill` names the value being filled -- the
> password. A chained exception prints in full wherever the failure is logged.

## `_drive`, [line 103](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L103): Docstring

> The whole attempt against a page already chosen, so the loop can be tested
> against a fake page. Same rule as `PlaywrightSignIn.sign_in`: nothing
> Playwright raised leaves here except as a secret-free `SignInFailed`.

## `_walk`, [line 142](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L142): Note on the line above

Code: `deadline=clock.time() + timeout_s,`

> `timeout_s` was accepted and ignored until 2026-09-23; the loop was bounded
> only by `_ROUNDS`, and each goto, fill and click by Playwright's own 30 s
> default. Once a page with nothing to do stopped meaning "give up", something
> had to end a login that is genuinely stuck, so the caller's timeout is now
> the deadline for everything: the connect, the goto, every fill, click and
> read, and the loop itself.

## `_walk`, [line 150](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L150): Note on the line above

Code: `page.on("framenavigated", moved)`

> Counts documents the main frame has moved to. A hop that posts itself to
> its own address changes no URL, so "the page has not moved" is judged on
> this count as well as the address.

## `_walk`, [line 158](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L158): Note on the line above

Code: `if acted >= _ROUNDS:`

> `_ROUNDS` counts things the driver did -- a choice, a form submitted, a
> button pressed -- not times it looked. Waiting on a hand-over costs nothing
> against it. Checked after `_settle`, so the page the last action led to has
> had its moment before anyone reads where the browser ended up.

## `_walk`, [line 162](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L162): Comment

Code: `except PlaywrightError as why:`

> A navigation in flight is a normal state of a redirect chain, not an error.
> Any probe of the page -- is it visible, fill it, click it, press submit --
> can meet a document being replaced, and Playwright reports that as
> "Execution context was destroyed" or similar depending on which call lost
> the race. The round is abandoned and the next one reads whatever document
> is there by then.
>
> Every Playwright error is treated that way rather than matching those
> messages, because their wording is the library's and changes with it. What
> is not retried is a closed page: nothing will load into it again. The last
> one is kept -- type and first line only, see `_brief` -- so a login that
> runs out of time says what kept going wrong instead of failing silently.
>
> Measured 2026-09-23 on QA: the real chain crashed here (inside `_visible`)
> while the page was redirecting. `tests/browser/test_a_sign_in_through_a_redirect_chain.py`
> reproduces the same error from the same line with a local chain, and
> `tests/unit/infrastructure/test_the_sign_in_driver.py` pins the retry with a
> fake page.

## `_walk`, [line 168](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L168): Note on the line above

Code: `await asyncio.sleep(_PROBE_S)`

> Not a Playwright wait: those go through the page, and the page is the thing
> that may be between documents.

## `_walk`, [line 173](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L173): Comment

Code: `raise SignInFailed(`

> Refused credentials end the attempt at once. Retyping a password the
> system just rejected is how an account gets locked, and this runs
> unattended -- the old loop refilled and resubmitted up to six times.

## `_walk`, [line 186](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L186): Comment

Code: `if still >= _STILL:`

> A dead end, said with what the page shows, because "did not finish" names
> no cause and the page usually does.

## `_Round`, [line 80](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L80): Class

> What one look at the page came to: the system's own host with nothing left
> to fill (landed), something done (acted), nothing to do yet (waiting), or
> the sign-in form back empty after credentials went in (refused).

## `_Login`, [line 88](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L88): Class

> One attempt's state. `typed` is whether the password has been submitted;
> from then on nothing is filled again.

## `_round`, [line 216](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L216): Comment

Code: `if login.typed:`

> After the password went in, the only questions are whether it was refused,
> whether the browser arrived, and whether there is a consent-style button to
> press. An empty password box means refused -- checked before arrival, so a
> system whose login lives on its own host is not mistaken for signed in. A
> filled one is the old form still on screen while the submit is in flight, so
> the driver waits rather than pressing submit a second time. Nothing is
> filled after this point, so a wrong password is submitted exactly once.

## `_round`, [line 239](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L239): Note on the line above

Code: `login.typed = True`

> Before the submit, not after: a click that triggers a navigation can raise
> after it has clicked, and treating that as "not submitted" is what would
> submit the credentials twice.

## `_round`, [line 245](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L245): Note on the line above

Code: `return _Round.WAITING`

> Off the system's host with nothing to fill and nothing to press used to end
> the login as a failure. On a real chain that page is usually a hand-over
> still in flight -- a document that posts itself onward a moment after it
> loads -- so it now means "look again". `_STILL` decides when it has stopped
> being one.

## `_brief`, [line 260](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L260): Docstring

> An error, safe to log or to show: its type and the first line of its
> message, with the username and password replaced. Never the rest:
> Playwright's call log follows the first line and names the value a `fill`
> was typing. Every log line and failure in this driver goes through here;
> none uses `exc_info`.

## `_redacted`, [line 265](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L265): Docstring

> The username and password taken out of text leaving the driver -- page text
> in particular, which may well say "account operator is locked".

## `_empty`, [line 284](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L284): Docstring

> Whether the page shows an empty box of this kind -- after a submit, the sign
> of a form that came back.

## `_shown`, [line 331](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L331): Docstring

> The page's visible text, collapsed and cut short, for a failure somebody has
> to act on.

## `_on_offer`, [line 346](../../../../../../../backend/src/sro/infrastructure/steel/sign_in.py#L346): Comment

Code: `except PlaywrightError as why:`

> Called only to describe a failure. A page that moves while it is described
> describes nothing rather than replacing the real failure with a navigation
> error.
