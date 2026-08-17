"""A credential that was built to be held, rather than one built to expire.

Everything before this replayed a human's browser session: cookies lifted out
of a window somebody signed into, plus the anti-forgery token the page mints.
It worked, and it kept dying -- because that is what a browser session is for.
Keycloak binds it to an SSO session with an idle limit and an absolute one, and
it expires whether or not anything here is well built.

An offline token is the opposite kind of thing. It is issued once, stored
persistently by the identity provider, and deliberately *not* bound to an SSO
session, so it survives the operator logging out, going home, and the session
they created being reaped. Refreshed on a schedule it lasts indefinitely.

The port is narrow on purpose: whoever holds this can act as the operator until
it is revoked, so there is exactly one place that turns it into an access token
and exactly one place that stores it.
"""

from __future__ import annotations

from typing import Protocol


class TokenSource(Protocol):
    async def establish(self, *, tenant: str, system: str, username: str, password: str) -> str:
        """Exchange a login for an offline token, once. Returns what it is for.

        The password is used here and nowhere else, and is not what gets kept:
        what is stored is the offline token, which the identity provider can
        revoke without changing anybody's password.
        """
        ...

    async def access_token(self, *, tenant: str, system: str) -> str | None:
        """A live access token, refreshed from the offline one as needed.

        None when this system has no offline token, which is a fact worth
        having rather than an error: it means the executor falls back to the
        session cookies, and the run says which credential it used.
        """
        ...

    async def has_token(self, *, tenant: str, system: str) -> bool: ...


class TokenRefused(Exception):
    """The identity provider would not issue or refresh. Not a ``DomainError``:
    the request was fine, the credential is not -- revoked, expired past its
    idle window, or a password that has since changed."""
