from __future__ import annotations

from dataclasses import dataclass, field

from sro.application.capture.events import (
    CaptureEvent,
    InputEvent,
    RequestEvent,
    SnapshotEvent,
)
from sro.domain.recording.axgraph import AxGraph
from sro.domain.recording.events import ActionFrame, ActionKind
from sro.domain.recording.network import CapturedRequest

_NOT_A_STEP = frozenset({ActionKind.SCROLL, ActionKind.HOVER})


@dataclass(frozen=True, slots=True)
class AssemblyResult:
    frames: tuple[ActionFrame, ...]

    unattached_requests: tuple[CapturedRequest, ...]

    orphaned_snapshots: int

    sources: tuple[InputEvent, ...] = ()

    @property
    def unattached_count(self) -> int:
        return len(self.unattached_requests)


@dataclass
class _OpenFrame:
    event: InputEvent
    snapshot: AxGraph | None = None
    requests: list[CapturedRequest] = field(default_factory=list)


def assemble_frames(events: list[CaptureEvent]) -> AssemblyResult:
    open_frames: list[_OpenFrame] = []
    unattached: list[CapturedRequest] = []
    orphaned_snapshots = 0

    for event in sorted(events, key=_sort_key):
        match event:
            case InputEvent() if event.action.kind in _NOT_A_STEP:
                continue
            case InputEvent():
                open_frames.append(_OpenFrame(event=event))
            case SnapshotEvent():
                if not open_frames:
                    orphaned_snapshots += 1
                elif open_frames[-1].snapshot is None:
                    open_frames[-1].snapshot = event.snapshot
            case RequestEvent():
                if not open_frames:
                    unattached.append(event.request)
                else:
                    open_frames[-1].requests.append(event.request)

    frames = tuple(
        ActionFrame(
            index=index,
            occurred_at=open_frame.event.at,
            action=open_frame.event.action,
            page_url=open_frame.event.page_url,
            ax_graph=open_frame.snapshot,
            requests=tuple(open_frame.requests),
        )
        for index, open_frame in enumerate(open_frames)
    )
    return AssemblyResult(
        frames=frames,
        unattached_requests=tuple(unattached),
        orphaned_snapshots=orphaned_snapshots,
        sources=tuple(open_frame.event for open_frame in open_frames),
    )


def _sort_key(event: CaptureEvent) -> tuple[float, int]:
    priority = 0 if isinstance(event, InputEvent) else 1
    return (event.at.timestamp(), priority)
