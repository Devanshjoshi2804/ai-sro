"""What one upload from one device was, and where its evidence went."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import BatchId, DeviceId, PrincipalId, RecordingId, TenantId


class CaptureMode(StrEnum):
    PASSIVE = "passive"
    """Nobody said "watch this". The stream an operator's ordinary day produces."""

    TEACHING = "teaching"
    """An operator asked to be recorded, with the debugger attached. Richer
    evidence, and the tier a candidate falls back to when passive evidence is
    too thin to induce from."""


@dataclass(frozen=True, slots=True)
class RejectedEvent:
    index: int
    reason: str

    def __post_init__(self) -> None:
        if self.index < 0:
            raise InvariantViolation("an event's index counts from zero")
        if not self.reason.strip():
            raise InvariantViolation("a rejection with no reason cannot be fixed")


@dataclass(frozen=True, slots=True)
class ObservationBatch:
    """The row. The events themselves are one object in the blob store.

    A day of capture is millions of events and none of them is queried by id --
    they are read whole, by a miner, over a window. Putting them in a column
    would make the row that says "this arrived" as expensive to read as the
    evidence it points at.

    Not `observation.gesture.GestureBatch`, which is the miner's own tally of an
    upload whose gestures were stored row by row. Separate tables, and one
    upload can be described by both.
    """

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
    """The demonstration this batch is part of, for teaching capture.

    A teaching batch without one is evidence nobody can attribute: the operator
    was asked to show the system a task, and what came back cannot be told from
    an ordinary morning's browsing. A passive batch with one would be the
    opposite mistake -- ordinary work filed as a deliberate demonstration."""

    def __post_init__(self) -> None:
        for name, at in (
            ("started_at", self.started_at),
            ("ended_at", self.ended_at),
            ("received_at", self.received_at),
        ):
            if at.tzinfo is None:
                raise InvariantViolation(f"{name} must be timezone-aware")
        if self.ended_at < self.started_at:
            raise InvariantViolation("a batch cannot end before it started")
        if not self.uri.strip():
            raise InvariantViolation("a batch whose evidence has no address is not evidence")
        if self.mode is CaptureMode.TEACHING and self.recording_id is None:
            raise InvariantViolation("a teaching batch must name the demonstration it belongs to")
        if self.mode is not CaptureMode.TEACHING and self.recording_id is not None:
            raise InvariantViolation(
                "a passive batch is ordinary work and cannot name a demonstration"
            )
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
