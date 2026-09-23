from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

WAS_OUR_OWN_DRIVING = "this browser was performing a run"


def was_our_own_driving(intent: object) -> bool:
    return getattr(intent, "why", None) == WAS_OUR_OWN_DRIVING


LONGEST = timedelta(minutes=30)


@dataclass(frozen=True, slots=True)
class Driving:
    device_id: str
    started_at: datetime
    finished_at: datetime | None

    def held(self, at: datetime) -> bool:
        if at < self.started_at:
            return False
        end = self.finished_at or (self.started_at + LONGEST)
        return at <= end


@dataclass(frozen=True, slots=True)
class Uploaded:
    device_id: str
    ended_at: datetime | None
    received_at: datetime | None

    @property
    def skew(self) -> timedelta | None:
        if self.ended_at is None or self.received_at is None:
            return None
        return self.received_at - self.ended_at


def our_own_driving(
    gestures: Sequence[tuple[str, str, float]],
    batches: Mapping[str, Uploaded],
    runs: Iterable[Driving],
) -> frozenset[str]:
    by_device: dict[str, list[Driving]] = {}
    for run in runs:
        by_device.setdefault(run.device_id, []).append(run)
    if not by_device:
        return frozenset()

    ours: set[str] = set()
    for gesture_id, batch_id, at in gestures:
        batch = batches.get(batch_id)
        if batch is None:
            continue
        skew = batch.skew
        if skew is None:
            continue
        held = by_device.get(batch.device_id)
        if not held:
            continue
        when = datetime.fromtimestamp(at, tz=UTC) + skew
        if any(run.held(when) for run in held):
            ours.add(gesture_id)
    return frozenset(ours)


__all__ = [
    "LONGEST",
    "WAS_OUR_OWN_DRIVING",
    "Driving",
    "Uploaded",
    "our_own_driving",
    "was_our_own_driving",
]
