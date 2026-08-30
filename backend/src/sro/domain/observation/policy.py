"""What an extension may capture, decided per tenant.

Off until somebody turns it on. Passive observation of every tab an operator
opens is monitoring, and ADR 008 makes it a contract conversation rather than a
default -- so the absent policy is the refusing one, not the permissive one.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from urllib.parse import urlsplit

from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.hosts import domain_matches

DEFAULT_EXCLUSIONS: tuple[str, ...] = (
    "mail.google.com",
    "outlook.live.com",
    "outlook.office.com",
    "outlook.office365.com",
    "outlook.cloud.microsoft",
    "mail.yahoo.com",
    "accounts.google.com",
    "login.microsoftonline.com",
)
"""Webmail and the identity providers in front of it.

Deliberately short. Finance, health and HR are the categories that matter most
and they are named differently at every customer, so they are supplied by the
tenant when observation is switched on. A guessed list would read as coverage
and provide none.

The Microsoft 365 mailbox hosts are here because the consumer ones were and
they were not, which is the wrong way round: `outlook.office.com` is corporate
mail, `outlook.live.com` is somebody's holiday photos. `domain_matches` is a
host-or-subdomain test, so excluding `login.microsoftonline.com` protected the
sign-in page and not the mailbox behind it -- and a tenant that switched
observation on with the defaults was recording message bodies, recipients and a
screenshot of the open message every gesture, for thirty days.

This list is still the wrong shape for anything nobody predicted, and no list of
hosts is ever complete. `only()` turns the policy into an allow-list, which is
the form that survives a mail client this file has never heard of.
"""


@dataclass(frozen=True, slots=True)
class ObservationPolicy:
    version: int = 0
    """Bumped on every change. The extension holds it and asks for a new policy
    only when the number moves, so a heartbeat costs one integer."""

    capture_enabled: bool = False
    exclude_hosts: tuple[str, ...] = DEFAULT_EXCLUSIONS
    include_hosts: tuple[str, ...] = ()
    """Empty means everything not excluded. A non-empty list narrows capture to
    those hosts and their subdomains."""

    capture_screenshots: bool = True
    screenshot_max_per_minute: int = 20
    capture_response_bodies: bool = True
    max_body_bytes: int = 256 * 1024
    daily_budget_bytes: int = 500 * 1024 * 1024
    retention_days: int = 30

    def __post_init__(self) -> None:
        if self.version < 0:
            raise InvariantViolation("a policy version counts up from zero")
        if self.retention_days < 1:
            raise InvariantViolation("evidence kept for less than a day is evidence discarded")
        for name, value in (
            ("screenshot_max_per_minute", self.screenshot_max_per_minute),
            ("max_body_bytes", self.max_body_bytes),
            ("daily_budget_bytes", self.daily_budget_bytes),
        ):
            if value < 0:
                raise InvariantViolation(f"{name} cannot be negative")

    def allows(self, url: str, granted: frozenset[str] = frozenset()) -> bool:
        """Whether a page at this URL may be observed.

        The extension enforces this by not registering a content script on an
        excluded host, so an excluded page is never touched. This is the second
        check: an extension that is wrong, old or lying does not get to write
        into the evidence plane anyway.

        ``granted`` are hosts the operator chose in their own panel, for a tab
        in front of them (`domain/observation/grant.py`). They widen the
        exclusion list and nothing else, which is where the three answers
        below differ:

        - ``capture_enabled`` is the tenant's agreement that any of this
          happens. No operator's button overrides it.
        - ``exclude_hosts`` is what the tenant agreed to *by default*, and a
          default is the kind of thing the person in front of the screen may
          decide otherwise about for one page.
        - ``include_hosts`` is an administrator naming the only hosts that may
          ever be observed. That is not a default, and an operator does not get
          to widen it from a side panel.
        """
        if not self.capture_enabled:
            return False
        host = urlsplit(url).hostname or ""
        if not host:
            return False
        excluded_by_default = any(domain_matches(host, excluded) for excluded in self.exclude_hosts)
        # Exactly the host, never a subdomain of it: a grant is what somebody
        # pressed a button about while looking at one page, and reading it as
        # a whole domain would let a click on one mailbox admit every host
        # under it.
        if excluded_by_default and host not in granted:
            return False
        if not self.include_hosts:
            return True
        return any(domain_matches(host, included) for included in self.include_hosts)

    def enabled(self) -> ObservationPolicy:
        """Observation on for this tenant. A contract conversation happened;
        this is where it is recorded."""
        return replace(self, version=self.version + 1, capture_enabled=True)

    def disabled(self) -> ObservationPolicy:
        return replace(self, version=self.version + 1, capture_enabled=False)

    def excluding(self, hosts: tuple[str, ...]) -> ObservationPolicy:
        """Replaces the list rather than adding to it: an exclusion somebody
        thought they had removed is worse than one they have to retype."""
        return replace(self, version=self.version + 1, exclude_hosts=hosts)

    def only(self, hosts: tuple[str, ...]) -> ObservationPolicy:
        return replace(self, version=self.version + 1, include_hosts=hosts)

    def keeping_for(self, days: int) -> ObservationPolicy:
        return replace(self, version=self.version + 1, retention_days=days)
