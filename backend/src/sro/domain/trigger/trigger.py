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
from sro.domain.trigger.arrival import Arrival
from sro.domain.trigger.cron import why_not
from sro.domain.trigger.watch import QUESTION, Watch


class TriggerKind(StrEnum):
    MANUAL = "manual"

    SCHEDULE = "schedule"
    INBOUND = "inbound"

    ARRIVAL = "arrival"

    WATCH = "watch"


@dataclass(eq=False)
class Trigger:
    id: TriggerId
    tenant_id: TenantId
    kind: TriggerKind
    created_by: PrincipalId
    created_at: datetime

    skill_id: SkillId | None = None

    workflow_id: str | None = None

    parameters: Mapping[str, str] = field(default_factory=dict)
    from_message: tuple[str, ...] = ()

    asks: bool = False

    arrival: Arrival | None = None

    watch: Watch | None = None

    cron: str | None = None
    timezone: str = "UTC"

    device_id: DeviceId | None = None

    medium: Medium = Medium.NETWORK

    enabled: bool = True
    writes: bool = False

    authorized_by: PrincipalId | None = None
    requires_confirmation: bool = True

    may_take_focus: bool = False

    last_fired_at: datetime | None = None
    last_run_id: RunId | None = None
    disabled_reason: str | None = None

    inbound_token: str | None = None

    def __post_init__(self) -> None:
        if self.created_at.tzinfo is None:
            raise InvariantViolation("Trigger.created_at must be timezone-aware")

        named = [name for name in (self.skill_id, self.workflow_id) if name]
        if self.asks:
            if named:
                raise InvariantViolation(
                    "a trigger that asks a question runs nothing: name neither"
                )
            if self.kind is not TriggerKind.WATCH:
                raise InvariantViolation(f"a {self.kind} trigger has no question to ask")
            if self.writes:
                raise InvariantViolation("a question writes nothing")
        elif len(named) != 1:
            raise InvariantViolation(
                "a trigger runs one thing: name a skill or a job, not "
                + ("both" if named else "neither")
            )

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

        if self.kind is TriggerKind.INBOUND:
            if not self.inbound_token:
                raise InvariantViolation("an inbound trigger needs a token to be reached by")
        elif self.inbound_token is not None:
            raise InvariantViolation(f"a {self.kind} trigger is not reached by a token")

        if self.kind is TriggerKind.ARRIVAL:
            if self.arrival is None:
                raise InvariantViolation("an arrival trigger needs a page to fire on")
            if self.device_id is None:
                raise InvariantViolation("an arrival with no browser sees nobody arrive")
        elif self.arrival is not None:
            raise InvariantViolation(f"a {self.kind} trigger has no page to arrive on")

        if self.kind is TriggerKind.WATCH:
            if self.watch is None:
                raise InvariantViolation("a watch trigger needs something to watch for")
            if self.device_id is None:
                raise InvariantViolation("a watch with no browser watches nothing: name a device")
            if self.from_message:
                raise InvariantViolation(
                    "a watch names its values by where it reads them; there is no second list"
                )
            if self.asks and not any(value.name == QUESTION for value in self.watch.values):
                raise InvariantViolation(
                    f"a watch that asks needs a {QUESTION!r} value: where in the mail the "
                    "question is"
                )
        elif self.watch is not None:
            raise InvariantViolation(f"a {self.kind} trigger has nothing to watch for")

        if self.from_message and self.kind is not TriggerKind.INBOUND:
            raise InvariantViolation(
                f"a {self.kind} trigger fires with the values it was created with; "
                "only an inbound one is told anything"
            )
        if self.watch is not None:
            self.from_message = self.watch.reads

        if self.writes and self.authorized_by is None:
            raise InvariantViolation(
                "a trigger for something that changes the system must name who authorised it"
            )
        if not self.writes and not self.requires_confirmation:
            self.requires_confirmation = False

        self.parameters = MappingProxyType(dict(self.parameters))

    @property
    def runs(self) -> str:
        return (self.skill_id.value if self.skill_id else None) or str(self.workflow_id)

    def values_from(self, message: Mapping[str, str]) -> dict[str, str]:
        told = {name: value for name, value in message.items() if name in self.from_message}
        return {**dict(self.parameters), **told}

    @property
    def is_scheduled(self) -> bool:
        return self.kind is TriggerKind.SCHEDULE and self.enabled

    @property
    def auto_approves(self) -> bool:
        return self.writes and not self.requires_confirmation

    def fired(self, at: datetime, run_id: RunId | None = None) -> None:
        if at.tzinfo is None:
            raise InvariantViolation("every timestamp is timezone-aware")
        self.last_fired_at = at
        self.last_run_id = run_id

    def disable(self, reason: str) -> None:
        if not reason.strip():
            raise InvariantViolation("a trigger disabled for no reason cannot be judged later")
        self.enabled = False
        self.disabled_reason = reason

    def enable(self) -> None:
        self.enabled = True
        self.disabled_reason = None

    def authorise(self, by: PrincipalId) -> None:
        self.authorized_by = by
