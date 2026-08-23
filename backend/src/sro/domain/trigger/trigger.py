"""What starts a run when nobody typed a sentence."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sro.domain.execution.run import Medium, RunId
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import DeviceId, PrincipalId, SkillId, TenantId, TriggerId
from sro.domain.trigger.cron import why_not


class TriggerKind(StrEnum):
    MANUAL = "manual"
    """A button. Kept as a kind so a trigger record exists for it: the run's
    parameters and its standing authorisation are then the same object whether
    a person or a clock started it."""

    SCHEDULE = "schedule"
    INBOUND = "inbound"
    """A mail or a chat message. Not built; named so that the shape it will take
    is decided once rather than invented under time pressure."""


@dataclass(eq=False)
class Trigger:
    """A skill, the values to run it with, and the authority to do so.

    The authority is the part that matters. A scheduled write happens with
    nobody watching, so the name on it has to have been written down in advance
    -- and this is where. ``Run`` refuses an above-shadow write with no
    authoriser; a trigger that could not name one is refused at creation, which
    is hours or weeks before the first time it would have gone off.
    """

    id: TriggerId
    tenant_id: TenantId
    skill_id: SkillId
    kind: TriggerKind
    created_by: PrincipalId
    created_at: datetime

    parameters: Mapping[str, str] = field(default_factory=dict)
    cron: str | None = None
    timezone: str = "UTC"

    device_id: DeviceId | None = None
    """Run it in this operator's own browser. A scheduled run that names one
    happens only while that browser is connected, which is a property of a
    laptop and not a fault."""

    medium: Medium = Medium.NETWORK

    enabled: bool = True
    writes: bool = False
    """Whether the skill changes the system. Copied at creation rather than
    joined, for the same reason a run copies its stage: a skill re-induced into
    something that writes must not silently make an old trigger a writing one.
    """

    authorized_by: PrincipalId | None = None
    requires_confirmation: bool = True
    """A fire becomes a card somebody presses. False is auto-approve, and it is
    a per-trigger decision made by a named person -- never a global setting, and
    never a default for anything that writes."""

    may_take_focus: bool = False
    """Whether a run may pull the operator's tab to the front. Off, because
    stealing focus from somebody mid-sentence is how an extension gets
    uninstalled."""

    last_fired_at: datetime | None = None
    last_run_id: RunId | None = None
    disabled_reason: str | None = None

    def __post_init__(self) -> None:
        if self.created_at.tzinfo is None:
            raise InvariantViolation("Trigger.created_at must be timezone-aware")

        if self.kind is TriggerKind.SCHEDULE:
            if not self.cron:
                raise InvariantViolation("a scheduled trigger needs a cron expression")
            reason = why_not(self.cron)
            if reason is not None:
                raise InvariantViolation(reason)
            try:
                ZoneInfo(self.timezone)
            except (ZoneInfoNotFoundError, ValueError) as unknown:
                raise InvariantViolation(f"{self.timezone!r} is not a time zone") from unknown
        elif self.cron:
            raise InvariantViolation(f"a {self.kind} trigger does not run on a schedule")

        if self.writes and self.authorized_by is None:
            # The whole point of the record. Refused here, weeks before it
            # would have written to a warehouse with nobody's name on it.
            raise InvariantViolation(
                "a trigger for a skill that changes the system must name who authorised it"
            )
        if not self.writes and not self.requires_confirmation:
            # Not a rule about safety -- a read needs no confirming -- but about
            # the field meaning one thing.
            self.requires_confirmation = False

        self.parameters = MappingProxyType(dict(self.parameters))

    @property
    def is_scheduled(self) -> bool:
        return self.kind is TriggerKind.SCHEDULE and self.enabled

    @property
    def auto_approves(self) -> bool:
        return self.writes and not self.requires_confirmation

    def fired(self, at: datetime, run_id: RunId) -> None:
        if at.tzinfo is None:
            raise InvariantViolation("every timestamp is timezone-aware")
        self.last_fired_at = at
        self.last_run_id = run_id

    def disable(self, reason: str) -> None:
        """Stopped, with the reason attached. A trigger that was switched off
        and nobody remembers why gets switched back on."""
        if not reason.strip():
            raise InvariantViolation("a trigger disabled for no reason cannot be judged later")
        self.enabled = False
        self.disabled_reason = reason

    def enable(self) -> None:
        self.enabled = True
        self.disabled_reason = None

    def authorise(self, by: PrincipalId) -> None:
        self.authorized_by = by
