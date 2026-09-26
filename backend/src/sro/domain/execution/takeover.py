from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sro.domain.execution.belts import carries_every, expected_statuses
from sro.domain.execution.compose import Adding
from sro.domain.execution.evidence import recorded_call, writes
from sro.domain.execution.lanes import SeenCall, same_call, write_confirmed
from sro.domain.execution.progress import Progress
from sro.domain.execution.write_plan import seen_values, wanted_by
from sro.domain.observation.gesture import Call, Gesture
from sro.domain.shared.errors import InvariantViolation
from sro.domain.skill.shape import cited_pairs, walkable
from sro.domain.skill.workflow import Step, Workflow

OPERATOR = "operator"


@dataclass(frozen=True, slots=True)
class Took:
    tab_id: int
    since: float
    through: float
    newest: float

    def __post_init__(self) -> None:
        if self.since > self.through:
            raise InvariantViolation("a takeover's gestures cannot end before they begin")
        if self.newest < self.through:
            raise InvariantViolation("a takeover's newest gesture cannot precede its last one")


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
    values: Mapping[str, str],
) -> Takeover:
    reached = {gesture.id for gesture, _ in walkable(cited_pairs(workflow, by_id))[:matched]}
    since = [one for one in seen if one.at >= took.since]
    uploaded = any(one.at >= took.through for one in since)
    calls = [
        (_seen(call), uploaded and one.tab_id == took.tab_id and one.at <= took.through)
        for one in since
        for call in one.requests
    ]
    ordered = sorted(workflow.steps, key=lambda step: step.order)
    written = [step for step in ordered if writes(step, by_id)]
    wanted = seen_values(workflow)
    claims = [
        {step.order for step in written if _its_own(step, by_id, values, wanted, call)}
        for call, _ in calls
    ]
    done: list[int] = []
    doubt: list[int] = []
    for step in written:
        recorded, statuses = recorded_call(step, by_id), expected_statuses(step, by_id)
        could = [
            (_status(recorded, statuses, call), spanned and step.order in owners, owners)
            for (call, spanned), owners in zip(calls, claims, strict=True)
            if _same_shape(call, recorded) and (step.order in owners or not owners)
        ]
        refused = [one for one in could if one[1] and one[0] == "failed"]
        if any(
            proven and said == "done" and owners == {step.order} for said, proven, owners in could
        ):
            done.append(step.order)
        elif len(could) > len(refused) or (reached & _writers(step, by_id) and not refused):
            doubt.append(step.order)
    replay_from = 0
    for n, step in enumerate(ordered):
        if step in written and step.order not in done:
            break
        if step.order in done:
            replay_from = n + 1
    return Takeover(replay_from, tuple(done), tuple(doubt))


def _seen(call: Call) -> SeenCall:
    body = call.request_body
    return SeenCall(
        call.method,
        call.url,
        call.status,
        request_body=body.text if body else None,
        request_content_type=body.mime_type if body else None,
    )


def _status(recorded: Call | None, statuses: set[int], call: SeenCall) -> str | None:
    return write_confirmed(recorded=recorded, wanted=statuses, calls=[call])


def _same_shape(call: SeenCall, recorded: Call | None) -> bool:
    return recorded is not None and same_call(call, recorded, Adding()) is not None


def _its_own(
    step: Step,
    by_id: Mapping[str, Gesture],
    values: Mapping[str, str],
    wanted: Mapping[str, frozenset[str]],
    call: SeenCall,
) -> bool:
    carried = {name: values.get(name, "") for name in wanted_by(step, by_id, wanted)}
    return (
        bool(carried)
        and all(carried.values())
        and _same_shape(call, recorded_call(step, by_id))
        and carries_every(call.request_body or "", carried)
    )


def _writers(step: Step, by_id: Mapping[str, Gesture]) -> set[str]:
    call = recorded_call(step, by_id)
    return {one for one in step.cites if one in by_id and call in by_id[one].requests}
