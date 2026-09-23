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

    CONNECTED = "connected"

    EXPIRED = "expired"


@dataclass(eq=False)
class Connection:
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
        return f"{self.tenant_id}/{self.target_system}/cookie"

    @property
    def session_key(self) -> str:
        return f"{self.tenant_id}/{self.target_system}/session"

    def credential_key(self, field: str) -> str:
        return f"{self.tenant_id}/{self.target_system}/{field.lower()}"

    def authenticated(self, at: datetime) -> None:
        if at.tzinfo is None:
            raise InvariantViolation("timestamps must be timezone-aware")
        self.status = ConnectionStatus.CONNECTED
        self.authenticated_at = at
        self.last_error = None

    def rejected(self, reason: str) -> None:
        self.status = ConnectionStatus.EXPIRED
        self.last_error = reason
