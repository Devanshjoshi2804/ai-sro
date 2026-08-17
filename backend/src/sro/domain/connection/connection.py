"""A system this tenant can reach. See docs/06-glossary.md#connection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from urllib.parse import urlsplit

from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import Identifier, TenantId


class ConnectionId(Identifier): ...


class ConnectionStatus(StrEnum):
    PENDING = "pending"
    """Created; nobody has logged in yet."""

    CONNECTED = "connected"
    """A session was captured and is believed usable."""

    EXPIRED = "expired"
    """The session was rejected. A human logs in again, or the login is replayed."""


@dataclass(eq=False)
class Connection:
    """A WMS the tenant has authenticated to.

    Holds no secret. The session and the login credentials live in the vault; a
    connection holds the *key* to them, so the row is safe to read, log and back
    up. That separation is what lets a recording be kept and a skill be shared.
    """

    id: ConnectionId
    tenant_id: TenantId
    name: str
    target_system: str
    base_url: str
    created_at: datetime
    status: ConnectionStatus = ConnectionStatus.PENDING
    authenticated_at: datetime | None = None
    last_error: str | None = None

    failures_acknowledged_at: datetime | None = None
    """When somebody looked at this system's recent failures and said to carry on.

    The circuit breaker asks for a person and, without this, gave them nothing
    to do: every run was refused until the window aged out, including the run
    that would have shown the fault was already fixed. Failures before this
    moment stop counting."""

    acknowledged_by: str | None = None
    acknowledgement_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvariantViolation("Connection requires a name")
        if not self.target_system.strip():
            raise InvariantViolation("Connection requires a target system")
        parts = urlsplit(self.base_url)
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            raise InvariantViolation(
                f"{self.base_url!r} is not an absolute http(s) URL; a connection has to say "
                "which host it reaches"
            )
        if self.created_at.tzinfo is None:
            raise InvariantViolation("Connection.created_at must be timezone-aware")

    def acknowledge_failures(self, at: datetime, by: str, reason: str) -> None:
        """Close the breaker by a named decision rather than by waiting.

        Recorded rather than silent: a breaker that anybody can clear without
        leaving their name is a breaker that stops meaning anything.
        """
        if not reason.strip():
            raise InvariantViolation(
                "clearing a breaker needs a reason: the next person to read this "
                "is deciding whether to trust it"
            )
        self.failures_acknowledged_at = at
        self.acknowledged_by = by
        self.acknowledgement_reason = reason.strip()

    @property
    def cookie_key(self) -> str:
        """Where the executor looks for this system's cookie header.

        Facility-less: a login is to a system, not to a site, and a skill that
        names `<system>/<facility>/cookie` falls back to this when its site has
        no session of its own."""
        return f"{self.tenant_id}/{self.target_system}/cookie"

    @property
    def session_key(self) -> str:
        """Vault key holding the captured browser session."""
        return f"{self.tenant_id}/{self.target_system}/session"

    def credential_key(self, field: str) -> str:
        """Vault key for one credential of this system, scoped per tenant."""
        return f"{self.tenant_id}/{self.target_system}/{field.lower()}"

    @property
    def is_usable(self) -> bool:
        return self.status is ConnectionStatus.CONNECTED

    def authenticated(self, at: datetime) -> None:
        if at.tzinfo is None:
            raise InvariantViolation("timestamps must be timezone-aware")
        self.status = ConnectionStatus.CONNECTED
        self.authenticated_at = at
        self.last_error = None

    def rejected(self, reason: str) -> None:
        """The stored session no longer works.

        Kept as a state rather than deleted: the connection still knows which
        system it is and which vault keys belong to it, and re-authenticating is
        a login, not a re-setup.
        """
        self.status = ConnectionStatus.EXPIRED
        self.last_error = reason
