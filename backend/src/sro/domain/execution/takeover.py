from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sro.domain.execution.belts import expected_statuses
from sro.domain.execution.evidence import recorded_call, writes
from sro.domain.execution.lanes import SeenCall, write_confirmed
from sro.domain.execution.progress import Progress
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.errors import InvariantViolation
from sro.domain.skill.shape import cited_pairs, walkable
from sro.domain.skill.workflow import Step, Workflow

OPERATOR = "operator"


@dataclass(frozen=True, slots=True)
class Took:
    tab_id: int
    since: float
    through: float

    def __post_init__(self) -> None:
        if self.since > self.through:
            raise InvariantViolation("a takeover's gestures cannot end before they begin")


@dataclass(frozen=True, slots=True)
class Takeover:
    replay_from: int
    done: tuple[int, ...] = ()
    in_doubt: tuple[int, ...] = ()

    def progress(self) -> Progress:
        progress = Progress(step=self.replay_from)
        for order in (*self.done, *self.in_doubt):
            progress.sending(order, OPERATOR)
        for order in self.done:
            progress.settle(order, lane=OPERATOR, verdict="done")
        return progress


def take_over(
    workflow: Workflow,
    by_id: Mapping[str, Gesture],
    *,
    matched: int,
    took: Took,
    seen: Sequence[Gesture],
) -> Takeover:
    reached = {gesture.id for gesture, _ in walkable(cited_pairs(workflow, by_id))[:matched]}
    theirs = sorted(
        (one for one in seen if one.tab_id == took.tab_id and one.at >= took.since),
        key=lambda one: one.at,
    )
    uploaded = any(one.at >= took.through for one in theirs)
    calls = [
        SeenCall(call.method, call.url, call.status)
        for one in theirs
        for call in one.requests
        if uploaded
    ]
    ordered = sorted(workflow.steps, key=lambda step: step.order)
    done: list[int] = []
    doubt: list[int] = []
    for step in ordered:
        if not reached & _writers(step, by_id):
            continue
        recorded, wanted = recorded_call(step, by_id), expected_statuses(step, by_id)
        mine = next(
            (
                call
                for call in calls
                if write_confirmed(recorded=recorded, wanted=wanted, calls=[call]) == "done"
            ),
            None,
        )
        if mine is None:
            doubt.append(step.order)
        else:
            calls.remove(mine)
            done.append(step.order)
    replay_from = 0
    for n, step in enumerate(ordered):
        if step.order in doubt:
            break
        if step.order in done:
            replay_from = n + 1
    return Takeover(replay_from, tuple(done), tuple(doubt))


def _writers(step: Step, by_id: Mapping[str, Gesture]) -> set[str]:
    if not writes(step, by_id):
        return set()
    call = recorded_call(step, by_id)
    return {one for one in step.cites if one in by_id and call in by_id[one].requests}
