"""Group capture events into ordered ActionFrames.

Grouping rules and their known limits: docs/03-backend-walkthrough.md#frame-assembly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sro.application.capture.events import (
    CaptureEvent,
    InputEvent,
    RequestEvent,
    SnapshotEvent,
)
from sro.domain.recording.axgraph import AxGraph
from sro.domain.recording.events import ActionFrame
from sro.domain.recording.network import CapturedRequest


@dataclass(frozen=True, slots=True)
class AssemblyResult:
    frames: tuple[ActionFrame, ...]
    orphaned_requests: int
    """Traffic before the first human action. A high count means capture
    attached to CDP late and the recording is missing its opening steps."""

    orphaned_snapshots: int


@dataclass
class _OpenFrame:
    event: InputEvent
    snapshot: AxGraph | None = None
    requests: list[CapturedRequest] = field(default_factory=list)


def assemble_frames(events: list[CaptureEvent]) -> AssemblyResult:
    """Fold events into frames: an input opens one, its effects attach to it."""
    open_frames: list[_OpenFrame] = []
    orphaned_requests = 0
    orphaned_snapshots = 0

    for event in sorted(events, key=_sort_key):
        match event:
            case InputEvent():
                open_frames.append(_OpenFrame(event=event))
            case SnapshotEvent():
                if not open_frames:
                    orphaned_snapshots += 1
                elif open_frames[-1].snapshot is None:
                    # Keep the first: it was taken at action time, which is the
                    # state the human was looking at when they decided to act.
                    open_frames[-1].snapshot = event.snapshot
            case RequestEvent():
                if not open_frames:
                    orphaned_requests += 1
                else:
                    open_frames[-1].requests.append(event.request)

    frames = tuple(
        ActionFrame(
            index=index,
            occurred_at=open_frame.event.at,
            action=open_frame.event.action,
            ax_graph=open_frame.snapshot,
            requests=tuple(open_frame.requests),
        )
        for index, open_frame in enumerate(open_frames)
    )
    return AssemblyResult(
        frames=frames,
        orphaned_requests=orphaned_requests,
        orphaned_snapshots=orphaned_snapshots,
    )


def _sort_key(event: CaptureEvent) -> tuple[float, int]:
    # CDP does not order across domains. At an identical timestamp the input is
    # the cause, so it must sort before the effects it produced.
    priority = 0 if isinstance(event, InputEvent) else 1
    return (event.at.timestamp(), priority)
