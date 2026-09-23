from __future__ import annotations

from dataclasses import dataclass

from sro.domain.execution.evidence import recorded_call
from sro.domain.observation.gesture import Gesture
from sro.domain.observation.trim import path_shape
from sro.domain.shared.errors import InvariantViolation
from sro.domain.skill.workflow import Workflow

K_MOST_ITEMS = 25


@dataclass(frozen=True, slots=True)
class Repeat:
    first_step: int
    last_step: int

    def __post_init__(self) -> None:
        if self.first_step < 0:
            raise InvariantViolation("a repeated block starts at a step that exists")
        if self.last_step < self.first_step:
            raise InvariantViolation("a repeated block ends before it begins")

    def covers(self, order: int) -> bool:
        return self.first_step <= order <= self.last_step

    @property
    def steps(self) -> int:
        return self.last_step - self.first_step + 1


K_CREATED = 201

K_SETTLE_S = 120.0


def detect(workflow: Workflow, gestures: dict[str, Gesture]) -> Repeat | None:
    steps = sorted(workflow.steps, key=lambda step: step.order)
    creates = [
        (step, call)
        for step in steps
        if (call := recorded_call(step, gestures)) is not None and call.status == K_CREATED
    ]
    if not creates:
        return None
    made, call = creates[-1]
    cited = [gestures[one] for step in steps for one in step.cites if one in gestures]
    if not cited:
        return None

    wanted = f"{call.method.upper()} {path_shape(call.url)}"
    bodies = [
        request.request_body
        for gesture in _the_doing(cited, gestures)
        for request in gesture.requests
        if request.status == K_CREATED
        and f"{request.method.upper()} {path_shape(request.url)}" == wanted
    ]
    if len(bodies) < 2 or len({str(body) for body in bodies}) < 2:
        return None

    first = made.order
    for step in reversed([one for one in steps if one.order < made.order]):
        if step.system != made.system:
            break
        first = step.order
    return Repeat(first_step=first, last_step=made.order)


def _the_doing(cited: list[Gesture], gestures: dict[str, Gesture]) -> list[Gesture]:
    systems = {one.system for one in cited}
    on_hand = sorted(
        (one for one in gestures.values() if one.system in systems), key=lambda one: one.at
    )
    mine = {one.id for one in cited}
    doing: list[Gesture] = []
    for gesture in on_hand:
        if doing and gesture.at - doing[-1].at > K_SETTLE_S:
            if any(one.id in mine for one in doing):
                return doing
            doing = []
        doing.append(gesture)
    return doing if any(one.id in mine for one in doing) else []
