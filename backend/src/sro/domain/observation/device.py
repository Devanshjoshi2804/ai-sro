"""One installed extension, in one browser profile, belonging to one operator."""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from datetime import datetime

from sro.domain.observation.grant import HostGrant
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

    grants: tuple[HostGrant, ...] = ()
    """Pages this operator said, in this browser, may be watched after all.

    Held on the device rather than on the tenant because that is what a grant
    is: one person's decision about one of their own tabs, not a change to what
    the tenant agreed to. It also costs nothing to check -- ingest reads this
    device already.
    """

    secret: str | None = None
    """What this browser proves it is itself with, minted at registration.

    The tenant credential says which tenant is asking and cannot say which
    browser: every device-scoped path is ``/v1/agents/{device_id}/...``, so
    without this a device id is a namespace rather than a credential and any
    colleague's extension could fire another operator's watch in a live
    warehouse. Same instinct as a trigger's ``inbound_token`` -- a caller with
    no principal behind it carries a per-thing secret -- and the same rule
    about what a wrong one is allowed to reveal.

    ``None`` only for a device registered before this existed. Such a device
    proves nothing and is refused everywhere; its browser re-registers on its
    next heartbeat, which is idempotent on the label and hands it one.
    """

    revoked_at: str | None = None
    """When this browser's authority was taken away, ISO, or ``None``.

    Separate from ``secret`` rather than clearing it: an administrator revoking
    a browser is answering "this one stops acting", and a device whose secret
    was blanked cannot be told from one registered before secrets existed. It
    is also the record of *when*, which an audit of what a browser was allowed
    to do needs and a missing secret cannot give.

    Nothing a browser does moves it. `save` deliberately never writes this
    column, so a heartbeat that loaded the device before the revocation and
    saved it after cannot undo one; and registration is idempotent and returns
    the same secret, so re-registering leaves the revocation standing. A browser
    cut off stays cut off -- every device-scoped path refuses it at
    `refuse_unless_itself`.

    The way back is an administrator, not the browser: `DeviceRepository.restore`
    and `POST /v1/devices/{device}/restore`. It has to be its own repository
    call precisely because `save` does not write this column -- clearing it
    through the record would mean letting every heartbeat write it too.
    """

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
        """Is this the browser that registered?

        On bytes, in constant time, for `ReceiveInbound`'s reasons: the caller
        is guessing or it is not, and a comparison that returns early tells it
        how close it got. ``hmac.compare_digest`` raises ``TypeError`` for a
        non-ASCII ``str`` and Starlette decodes header values through latin-1,
        so a header byte >= 0x80 arrives as one -- encoding both sides first is
        what keeps a 404 from becoming a 500 an unauthenticated caller can read.

        A device with no secret answers no. It cannot be told from one that
        never existed, which is the point.
        """
        if self.secret is None:
            return False
        return hmac.compare_digest(self.secret.encode(), presented.encode())

    def granted_hosts(self, now: datetime) -> frozenset[str]:
        """The hosts this browser may watch beyond the tenant's default.

        Expiry is applied on read rather than by a sweep: a grant that has run
        out must stop admitting the moment it does, and a job that has not run
        yet is not a thing to base that on.
        """
        return frozenset(grant.host for grant in self.grants if grant.live_at(now))

    def grant(self, host: str, *, by: PrincipalId, at: datetime, until: datetime) -> None:
        """Watch this host too, until it expires or the tab closes.

        Re-granting replaces rather than adds: the operator pressing the button
        again means "keep watching", and a device that accumulated one row per
        press would expire on the oldest.
        """
        self.revoke(host)
        self.grants = (
            *self.grants,
            HostGrant(host=host, granted_by=by, granted_at=at, expires_at=until),
        )

    def revoke(self, host: str) -> None:
        self.grants = tuple(grant for grant in self.grants if grant.host != host)

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
