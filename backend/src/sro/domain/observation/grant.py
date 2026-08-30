"""An operator saying, in their own browser, that this one page may be watched.

The exclusion list is what a tenant agreed to *by default*: webmail and sign-in
pages are never observed, because continuous capture of somebody's mailbox is
the thing that needs a DPIA and that employee consent cannot make lawful.

A grant is a different act, and the difference is the whole justification. It is
one host, chosen by the person whose browser it is, in the tab in front of them,
visible in the panel for as long as it lasts, revoked by closing the tab. That
is not monitoring somebody; it is somebody showing you something. Without it the
mail half of a task can never be demonstrated at all -- press teach in a mailbox
today and the recording comes back empty.

Two limits keep it from becoming the exclusion list's undoing. It expires, so a
browser that crashed cannot leave a mailbox standing open; and it widens
``exclude_hosts`` only, never ``include_hosts`` -- an administrator who named
the only hosts that may be observed made a decision an operator does not get to
overrule from a side panel.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import PrincipalId

LONGEST = timedelta(hours=12)
"""How long a grant may last, however long the tab does.

The extension revokes on `chrome.tabs.onRemoved`, so in the ordinary case a
grant ends when the operator closes the tab. This is what happens when the
ordinary case does not: a crashed browser, a killed worker, a laptop that
slept. A standing grant nobody remembers giving is the thing the exclusion list
exists to prevent.
"""


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
            # Compared against a URL's hostname, which is already lowercase.
            # Normalised here rather than at every read, so a grant on
            # `Mail.Google.com` cannot silently never match.
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
