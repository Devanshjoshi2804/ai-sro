"""One installed extension, in one browser profile, belonging to one operator."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import DeviceId, PrincipalId, TenantId


@dataclass(eq=False)
class AgentDevice:
    """What a command channel addresses and what a batch was uploaded by.

    It holds no policy of its own. Policy is the tenant's, so a device cannot
    grant itself more than the tenant agreed to -- and ``paused`` here is the
    administrator's switch, separate from the operator's own pause, which lives
    in the browser and is theirs to hold.
    """

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

    def seen(self, at: datetime, *, queued_events: int = 0, queued_bytes: int = 0) -> None:
        """A heartbeat. Backlog is recorded because a device whose queue only
        grows is a device that cannot reach us, and that is worth seeing on a
        screen before an operator's day of work is lost to a retention window."""
        self._require_later(at)
        self.last_seen_at = at
        self.queued_events = max(0, queued_events)
        self.queued_bytes = max(0, queued_bytes)

    def uploaded(self, at: datetime) -> None:
        self._require_later(at)
        self.last_seen_at = at
        self.uploads += 1

    def pause(self, at: datetime, *, by: str) -> None:
        """The administrator's kill switch, delivered on the next heartbeat."""
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
