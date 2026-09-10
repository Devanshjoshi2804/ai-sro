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
    "accounts.google.com",
    "login.microsoftonline.com",
    "b2clogin.com",
)
"""The identity providers. Sign-in pages, and nothing else.

Deliberately short. Finance, health and HR are the categories that matter most
and they are named differently at every customer, so they are supplied by the
tenant when observation is switched on. A guessed list would read as coverage
and provide none.

**Webmail was here and is not any more, deliberately.** `mail.google.com`, the
four Outlook hosts and `mail.yahoo.com` were excluded by default; the work that
starts in a mailbox -- a mail arrives, somebody reads it, and what it says
decides what they then do in the WMS -- could not be recorded without an
operator granting the host by hand on every tab. That is a real workflow this
product exists to learn, and a default that hides half of it teaches half a
task. Mail is now observed like any other host: only in a tab somebody pressed
Watch on, only while `capture_enabled`, and only until they close it.

What that costs is written down rather than argued away, because it happened.
`domain_matches` is a host-or-subdomain test, so excluding
`login.microsoftonline.com` protected the sign-in page and not the mailbox
behind it -- and a tenant that switched observation on with the older defaults
was recording message bodies, recipients and a screenshot of the open message
every gesture, for thirty days. That is now the documented consequence of
pressing Watch on a mailbox, not an accident of a list being wrong. A tenant
that does not want it says so: `excluding(...)` puts any of these back for that
tenant alone, and `only()` turns the policy into an allow-list, which is the
form that survives a mail client this file has never heard of.

The identity hosts stay, and they are a different question from mail. A
sign-in page is where somebody types a password; there is no task to learn
there and nothing on it anybody wants in evidence. `b2clogin.com` is the same
family as `login.microsoftonline.com`: Azure AD B2C, where the host is always
`<tenant>.b2clogin.com`. It is here rather than in one customer's policy
because it is Microsoft's host, not theirs -- this deployment captured a real
sign-in on `blueyonderalphaus.b2clogin.com` and closed it by editing that
tenant's stored list, which left the next tenant exactly where this one
started. Nothing but sign-in is served from b2clogin.com, so excluding the
domain costs no evidence anybody wanted.

A customer's OWN identity host stays out. This deployment also excluded a
Keycloak at `keycloak-…-wms-keycloak-prod.us.live.external.byp.ai`, and that
name belongs to one warehouse rather than to a vendor -- guessing at those is
the "coverage that provides none" this list exists to avoid.
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

    capture_snapshots: bool = False
    """Accessibility trees while nobody is deliberately teaching.

    The tree is the one view that says what a control *is* rather than where it
    happens to sit today, and induction builds a locator from it. Without one, a
    skill has only what the DOM offers -- a css path of framework ids assigned
    in render order, different on the next page load. So every skill that
    arrived the way this product intends -- watch, notice the repetition, offer
    it back -- got the weaker ladder, and the good locators were reserved for
    the path an operator has to remember to press.

    Off by default, and this is the only capture setting that is, because it is
    the only one an operator can see. Trees come from `chrome.debugger` and
    Chrome shows "AI-SRO is debugging this browser" for as long as anything is
    attached. An extension force-installed by enterprise policy
    (`ExtensionInstallForcelist`) raises no banner at all, which is the
    deployment this is for; an unpacked development copy does, and no extension
    can suppress it from inside. Turning this on is therefore an administrator's
    decision about a browser they manage, which is why it is written here rather
    than defaulted on and discovered by somebody working.

    It also costs the tab's debugger, and Chrome allows one. An operator who
    opens DevTools takes it and keeps it until they close them; capture carries
    on without trees rather than fighting them for it."""

    snapshot_max_per_minute: int = 20
    """Its own budget, not the screenshots'. A tree is a round trip and some
    JSON, a picture is a PNG, and one shared counter would have whichever
    happened first spend the other's allowance."""
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
            ("snapshot_max_per_minute", self.snapshot_max_per_minute),
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

    def reading_structure(self, on: bool) -> ObservationPolicy:
        """Accessibility trees while nobody is deliberately teaching.

        Its own method rather than a field somebody edits, because turning it on
        is a decision about a browser an administrator manages: on an install
        that is not force-installed by policy, Chrome puts a debugging banner on
        every watched tab for as long as this is on."""
        return replace(self, version=self.version + 1, capture_snapshots=on)
