from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import BatchId, DeviceId, PrincipalId, RecordingId, TenantId


class CaptureMode(StrEnum):
    PASSIVE = "passive"


@dataclass(frozen=True, slots=True)
class RejectedEvent:
    index: int
    reason: str

    def __post_init__(self) -> None:
        if self.index < 0:
            raise InvariantViolation("an event's index counts from zero")
        if not self.reason.strip():
            raise InvariantViolation("a rejection with no reason cannot be fixed")


def check_times(started_at: datetime, ended_at: datetime, received_at: datetime) -> None:
    for name, at in (
        ("started_at", started_at),
        ("ended_at", ended_at),
        ("received_at", received_at),
    ):
        if at.tzinfo is None:
            raise InvariantViolation(f"{name} must be timezone-aware")
    if ended_at < started_at:
        raise InvariantViolation("a batch cannot end before it started")


@dataclass(frozen=True, slots=True)
class ObservationBatch:
    id: BatchId
    tenant_id: TenantId
    device_id: DeviceId
    principal_id: PrincipalId
    mode: CaptureMode
    started_at: datetime
    ended_at: datetime
    received_at: datetime
    uri: str
    event_count: int
    byte_count: int
    rejected: tuple[RejectedEvent, ...] = ()

    recording_id: RecordingId | None = None

    def __post_init__(self) -> None:
        check_times(self.started_at, self.ended_at, self.received_at)
        if not self.uri.strip():
            raise InvariantViolation("a batch whose evidence has no address is not evidence")
        for name, count in (
            ("event_count", self.event_count),
            ("byte_count", self.byte_count),
        ):
            if count < 0:
                raise InvariantViolation(f"{name} cannot be negative")

    @property
    def rejected_count(self) -> int:
        return len(self.rejected)

    @property
    def spans_seconds(self) -> float:
        return (self.ended_at - self.started_at).total_seconds()
