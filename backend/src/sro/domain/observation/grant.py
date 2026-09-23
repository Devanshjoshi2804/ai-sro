from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import PrincipalId

LONGEST = timedelta(hours=12)


@dataclass(frozen=True, slots=True)
class HostGrant:
    host: str
    granted_by: PrincipalId
    granted_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        if not self.host.strip():
            raise InvariantViolation("a grant names the host it is for")
        if self.host != self.host.strip().lower():
            raise InvariantViolation(f"{self.host!r} is not a normalised hostname")
        for name, at in (("granted_at", self.granted_at), ("expires_at", self.expires_at)):
            if at.tzinfo is None:
                raise InvariantViolation(f"HostGrant.{name} must be timezone-aware")
        if self.expires_at <= self.granted_at:
            raise InvariantViolation("a grant that has already expired grants nothing")
        if self.expires_at - self.granted_at > LONGEST:
            raise InvariantViolation(
                f"a grant may last at most {LONGEST}, so that a browser which "
                "stopped without revoking cannot leave a page observed forever"
            )

    def live_at(self, now: datetime) -> bool:
        return now < self.expires_at
