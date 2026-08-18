"""Signing a browser in, without a human at the keyboard.

Kept behind a port for the same reason as everything else that touches a
browser, and for one more: this is the only code in the system that handles a
password. Naming it in one small interface means there is exactly one place to
audit, and the answer to "where do credentials go" is a file, not a search.

The driver types them into the system's own login page. They are never logged,
never returned, never written to a recording, and never sent anywhere but the
host the connection names.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SignInResult:
    landed_at: str
    """Where the browser finished. The evidence that the login worked -- being
    on the system's own host rather than the identity provider's."""

    steps: tuple[str, ...]
    """What the driver did, in order, with no values. Enough to debug a login
    that stalled without recording what was typed."""


class SignInDriver(Protocol):
    async def sign_in(
        self,
        *,
        debugger_url: str,
        url: str,
        username: str,
        password: str,
        choose: tuple[str, ...] = (),
        timeout_s: float = 90.0,
    ) -> SignInResult:
        """Drive this browser from ``url`` to signed in, or raise.

        ``choose`` names the identity provider options to click when a page
        offers a choice rather than a form. Taken from a demonstration of this
        system's own login, because which of six tenants an operator belongs to
        is not something to guess at.
        """
        ...


class SignInFailed(Exception):
    """The login did not complete, and the reason names no secret.

    Not a ``DomainError``: nothing about the request was wrong. The password may
    be stale, the identity provider may want a second factor, or the page may
    have changed shape -- all of which a human resolves by signing in once.
    """
