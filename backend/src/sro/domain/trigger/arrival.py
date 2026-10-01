from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.hosts import route_of

MAX_PAGE = 300


@dataclass(frozen=True, slots=True)
class Arrival:
    page: str

    def __post_init__(self) -> None:
        if not self.page.strip():
            raise InvariantViolation("an arrival with no page fires on every page there is")
        if len(self.page) > MAX_PAGE:
            raise InvariantViolation(f"a page rule is at most {MAX_PAGE} characters")
        if (
            "://" in self.page
            or "?" in self.page
            or ("#" in self.page and page_of(self.page) != self.page.lower())
        ):
            raise InvariantViolation(
                "an arrival names a page as host/path#route: no scheme, no query, "
                "no fragment but the screen's route"
            )
        if self.page != self.page.lower():
            raise InvariantViolation("a page rule is lowercase; use `page_of` to make one")

    def matches(self, url: str) -> bool:
        return page_of(url) == self.page


def page_of(url: str) -> str:
    parsed = urlsplit(url if "://" in url else f"https://{url}")
    if parsed.scheme not in ("http", "https"):
        return ""
    host = (parsed.hostname or "").rstrip(".")
    if not host:
        return ""
    port = ""
    try:
        # An explicit default port is the same page as none (the browser's
        # `URL.host` drops it).
        default = 443 if parsed.scheme == "https" else 80
        port = f":{parsed.port}" if parsed.port and parsed.port != default else ""
    except ValueError:
        return ""
    path = parsed.path.rstrip("/")
    route = route_of(parsed.fragment)
    where = f"{host}{port}{path}".lower()
    return f"{where}#{route}" if route else where
