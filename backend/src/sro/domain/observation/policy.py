from __future__ import annotations

from dataclasses import dataclass, replace
from urllib.parse import urlsplit

from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.hosts import domain_matches

DEFAULT_EXCLUSIONS: tuple[str, ...] = (
    "accounts.google.com",
    "login.microsoftonline.com",
    "b2clogin.com",
)


@dataclass(frozen=True, slots=True)
class ObservationPolicy:
    version: int = 0

    capture_enabled: bool = False
    exclude_hosts: tuple[str, ...] = DEFAULT_EXCLUSIONS
    include_hosts: tuple[str, ...] = ()

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
        if not self.capture_enabled:
            return False
        host = urlsplit(url).hostname or ""
        if not host:
            return False
        excluded_by_default = any(domain_matches(host, excluded) for excluded in self.exclude_hosts)
        if excluded_by_default and host not in granted:
            return False
        if not self.include_hosts:
            return True
        return any(domain_matches(host, included) for included in self.include_hosts)

    def enabled(self) -> ObservationPolicy:
        return replace(self, version=self.version + 1, capture_enabled=True)

    def disabled(self) -> ObservationPolicy:
        return replace(self, version=self.version + 1, capture_enabled=False)

    def excluding(self, hosts: tuple[str, ...]) -> ObservationPolicy:
        return replace(self, version=self.version + 1, exclude_hosts=hosts)

    def only(self, hosts: tuple[str, ...]) -> ObservationPolicy:
        return replace(self, version=self.version + 1, include_hosts=hosts)

    def keeping_for(self, days: int) -> ObservationPolicy:
        return replace(self, version=self.version + 1, retention_days=days)
