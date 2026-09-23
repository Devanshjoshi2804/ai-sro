# Notes for `backend/src/sro/application/ports/token.py`

Comments and docstrings moved out of [`backend/src/sro/application/ports/token.py`](../../../../../../../backend/src/sro/application/ports/token.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/ports/token.py#L1): Docstring

> A credential that was built to be held, rather than one built to expire.
>
> Everything before this replayed a human's browser session: cookies lifted out
> of a window somebody signed into, plus the anti-forgery token the page mints.
> It worked, and it kept dying -- because that is what a browser session is for.
> Keycloak binds it to an SSO session with an idle limit and an absolute one, and
> it expires whether or not anything here is well built.
>
> An offline token is the opposite kind of thing. It is issued once, stored
> persistently by the identity provider, and deliberately *not* bound to an SSO
> session, so it survives the operator logging out, going home, and the session
> they created being reaped. Refreshed on a schedule it lasts indefinitely.
>
> The port is narrow on purpose: whoever holds this can act as the operator until
> it is revoked, so there is exactly one place that turns it into an access token
> and exactly one place that stores it.

## `TokenRefused`, [line 12](../../../../../../../backend/src/sro/application/ports/token.py#L12): Docstring

> The identity provider would not issue or refresh. Not a ``DomainError``:
> the request was fine, the credential is not -- revoked, expired past its
> idle window, or a password that has since changed.

## `TokenSource.establish`, [line 7](../../../../../../../backend/src/sro/application/ports/token.py#L7): Docstring

> Exchange a login for an offline token, once. Returns what it is for.
>
> The password is used here and nowhere else, and is not what gets kept:
> what is stored is the offline token, which the identity provider can
> revoke without changing anybody's password.

## `TokenSource.access_token`, [line 9](../../../../../../../backend/src/sro/application/ports/token.py#L9): Docstring

> A live access token, refreshed from the offline one as needed.
>
> None when this system has no offline token, which is a fact worth
> having rather than an error: it means the executor falls back to the
> session cookies, and the run says which credential it used.
