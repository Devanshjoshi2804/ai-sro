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
from sro.domain.recording.events import ActionFrame, ActionKind
from sro.domain.recording.network import CapturedRequest

_NOT_A_STEP = frozenset({ActionKind.SCROLL, ActionKind.HOVER})
"""Gestures that move attention rather than change anything."""


@dataclass(frozen=True, slots=True)
class AssemblyResult:
    frames: tuple[ActionFrame, ...]

    unattached_requests: tuple[CapturedRequest, ...]
    """Traffic with no preceding action *in this batch*.

    Two very different causes, and the caller can tell them apart because it
    knows whether the recording already has frames:

    - page-load noise before the first human action, which is genuinely orphaned
    - the tail of the previous action, when a response finished after the last
      drain. Those belong to the frame that is already stored; dropping them
      would silently cost that step its network plan, which is the part a skill
      is actually built from.
    """

    orphaned_snapshots: int

    sources: tuple[InputEvent, ...] = ()
    """The gesture each frame was opened by, in frame order.

    Which events survive to become frames is this module's rule -- a scroll is
    dropped, an input at the same instant as its effects sorts before them --
    and a caller that needs to know where a frame came from must not restate
    that rule to find out. A screenshot is joined to its gesture through here,
    by identity rather than by matching a timestamp that two gestures could
    share.
    """

    @property
    def unattached_count(self) -> int:
        return len(self.unattached_requests)


@dataclass
class _OpenFrame:
    event: InputEvent
    snapshot: AxGraph | None = None
    requests: list[CapturedRequest] = field(default_factory=list)


def assemble_frames(events: list[CaptureEvent]) -> AssemblyResult:
    """Fold events into frames: an input opens one, its effects attach to it."""
    open_frames: list[_OpenFrame] = []
    unattached: list[CapturedRequest] = []
    orphaned_snapshots = 0

    for event in sorted(events, key=_sort_key):
        match event:
            case InputEvent() if event.action.kind in _NOT_A_STEP:
                # Moving the viewport is not a step, and treating it as one
                # costs the step before it its own evidence: a scroll between a
                # click and its responses opens a frame that absorbs them. Two
                # runs then attribute the same calls to different steps and the
                # diff calls that a divergence.
                continue
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
    # CDP does not order across domains. At an identical timestamp the input is
    # the cause, so it must sort before the effects it produced.
    priority = 0 if isinstance(event, InputEvent) else 1
    return (event.at.timestamp(), priority)
