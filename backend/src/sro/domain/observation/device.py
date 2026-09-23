from __future__ import annotations

import hmac
from dataclasses import dataclass
from datetime import datetime

from sro.domain.observation.grant import HostGrant
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import DeviceId, PrincipalId, TenantId


@dataclass(eq=False)
class AgentDevice:
    id: DeviceId
    tenant_id: TenantId
    principal_id: PrincipalId
    label: str
    extension_version: str
    registered_at: datetime
    last_seen_at: datetime
    paused: bool = False
    paused_by: str | None = None
    queued_events: int = 0
    queued_bytes: int = 0
    uploads: int = 0

    grants: tuple[HostGrant, ...] = ()

    secret: str | None = None

    revoked_at: str | None = None

    @property
    def revoked(self) -> bool:
        return self.revoked_at is not None

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise InvariantViolation("a device with no label cannot be told from another")
        for name, at in (
            ("registered_at", self.registered_at),
            ("last_seen_at", self.last_seen_at),
        ):
            if at.tzinfo is None:
                raise InvariantViolation(f"{name} must be timezone-aware")
        if self.last_seen_at < self.registered_at:
            raise InvariantViolation("a device cannot have been seen before it registered")

    def proves_itself(self, presented: str) -> bool:
        if self.secret is None:
            return False
        return hmac.compare_digest(self.secret.encode(), presented.encode())

    def granted_hosts(self, now: datetime) -> frozenset[str]:
        return frozenset(grant.host for grant in self.grants if grant.live_at(now))

    def grant(self, host: str, *, by: PrincipalId, at: datetime, until: datetime) -> None:
        self.revoke(host)
        self.grants = (
            *self.grants,
            HostGrant(host=host, granted_by=by, granted_at=at, expires_at=until),
        )

    def revoke(self, host: str) -> None:
        self.grants = tuple(grant for grant in self.grants if grant.host != host)

    def seen(self, at: datetime, *, queued_events: int = 0, queued_bytes: int = 0) -> None:
        self._require_later(at)
        self.last_seen_at = at
        self.queued_events = max(0, queued_events)
        self.queued_bytes = max(0, queued_bytes)

    def uploaded(self, at: datetime) -> None:
        self._require_later(at)
        self.last_seen_at = at
        self.uploads += 1

    def pause(self, at: datetime, *, by: str) -> None:
        if not by.strip():
            raise InvariantViolation("a pause nobody signed is a pause nobody can undo")
        self._require_later(at)
        self.paused, self.paused_by, self.last_seen_at = True, by, max(at, self.last_seen_at)

    def resume(self, at: datetime) -> None:
        self._require_later(at)
        self.paused, self.paused_by = False, None
        self.last_seen_at = max(at, self.last_seen_at)

    def _require_later(self, at: datetime) -> None:
        if at.tzinfo is None:
            raise InvariantViolation("every timestamp is timezone-aware")
        if at < self.registered_at:
            raise InvariantViolation("a device cannot act before it registered")
